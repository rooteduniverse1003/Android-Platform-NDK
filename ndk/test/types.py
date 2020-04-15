#
# Copyright (C) 2015 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import fnmatch
import imp
import logging
import multiprocessing
import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import (
    List,
    Optional,
    TextIO,
    Tuple,
    Union,
)
import xml.etree.ElementTree

from ndk.abis import Abi
import ndk.ansi
import ndk.ext.os
import ndk.ext.shutil
import ndk.ext.subprocess
import ndk.hosts
import ndk.ndkbuild
import ndk.paths
from ndk.test.config import LibcxxTestConfig, TestConfig
from ndk.test.filters import TestFilter
from ndk.test.spec import BuildConfiguration
from ndk.test.result import Failure, Skipped, Success, TestResult
from ndk.toolchains import LinkerOption


def logger() -> logging.Logger:
    """Return the logger for this module."""
    return logging.getLogger(__name__)


def _get_jobs_args() -> List[str]:
    cpus = multiprocessing.cpu_count()
    return [f'-j{cpus}', f'-l{cpus}']


def _prep_build_dir(src_dir: str, out_dir: str) -> None:
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    shutil.copytree(src_dir, out_dir)


class Test:
    def __init__(self, name: str, test_dir: str, config: BuildConfiguration,
                 ndk_path: str) -> None:
        self.name = name
        self.test_dir = test_dir
        self.config = config
        self.ndk_path = ndk_path

    def get_test_config(self) -> TestConfig:
        return TestConfig.from_test_dir(self.test_dir)

    def run(self, obj_dir: str, dist_dir: str,
            test_filters: TestFilter) -> Tuple[TestResult, List['Test']]:
        raise NotImplementedError

    def is_negative_test(self) -> bool:
        raise NotImplementedError

    def check_broken(self) -> Union[Tuple[None, None], Tuple[str, str]]:
        return self.get_test_config().build_broken(self)

    def check_unsupported(self) -> Optional[str]:
        return self.get_test_config().build_unsupported(self)

    def get_build_dir(self, out_dir: str) -> str:
        raise NotImplementedError

    def __str__(self) -> str:
        return f'{self.name} [{self.config}]'


class BuildTest(Test):
    def __init__(self, name: str, test_dir: str, config: BuildConfiguration,
                 ndk_path: str) -> None:
        super().__init__(name, test_dir, config, ndk_path)

        if self.api is None:
            raise ValueError

    @property
    def abi(self) -> Abi:
        return self.config.abi

    @property
    def api(self) -> Optional[int]:
        return self.config.api

    @property
    def platform(self) -> Optional[int]:
        return self.api

    @property
    def ndk_build_flags(self) -> List[str]:
        flags = self.config.get_extra_ndk_build_flags()
        if flags is None:
            flags = []
        return flags + self.get_extra_ndk_build_flags()

    @property
    def cmake_flags(self) -> List[str]:
        flags = self.config.get_extra_cmake_flags()
        if flags is None:
            flags = []
        return flags + self.get_extra_cmake_flags()

    def run(self, obj_dir: str, dist_dir: str,
            _test_filters: TestFilter) -> Tuple[TestResult, List[Test]]:
        raise NotImplementedError

    def check_broken(self) -> Union[Tuple[None, None], Tuple[str, str]]:
        return self.get_test_config().build_broken(self)

    def check_unsupported(self) -> Optional[str]:
        return self.get_test_config().build_unsupported(self)

    def is_negative_test(self) -> bool:
        return self.get_test_config().is_negative_test()

    def get_extra_cmake_flags(self) -> List[str]:
        return self.get_test_config().extra_cmake_flags()

    def get_extra_ndk_build_flags(self) -> List[str]:
        return self.get_test_config().extra_ndk_build_flags()


class PythonBuildTest(BuildTest):
    """A test that is implemented by test.py.

    A test.py test has a test.py file in its root directory. This module
    contains a run_test function which returns a tuple of `(boolean_success,
    string_failure_message)` and takes the following kwargs (all of which
    default to None):

    abi: ABI to test as a string.
    platform: Platform to build against as a string.
    ndk_build_flags: Additional build flags that should be passed to ndk-build
                     if invoked as a list of strings.
    """

    def __init__(self, name: str, test_dir: str, config: BuildConfiguration,
                 ndk_path: str) -> None:
        api = config.api
        if api is None:
            api = ndk.abis.min_api_for_abi(config.abi)
        config = ndk.test.spec.BuildConfiguration(config.abi, api,
                                                  config.linker)
        super().__init__(name, test_dir, config, ndk_path)

        if self.abi not in ndk.abis.ALL_ABIS:
            raise ValueError('{} is not a valid ABI'.format(self.abi))

        try:
            assert self.api is not None
            int(self.api)
        except ValueError:
            raise ValueError(f'{self.api} is not a valid API number')

        # Not a ValueError for this one because it should be impossible. This
        # is actually a computed result from the config we're passed.
        assert self.ndk_build_flags is not None

    def get_build_dir(self, out_dir: str) -> str:
        return os.path.join(out_dir, str(self.config), 'test.py', self.name)

    def run(self, obj_dir: str, _dist_dir: str,
            _test_filters: TestFilter) -> Tuple[TestResult, List[Test]]:
        build_dir = self.get_build_dir(obj_dir)
        logger().info('Building test: %s', self.name)
        _prep_build_dir(self.test_dir, build_dir)
        with ndk.ext.os.cd(build_dir):
            module = imp.load_source('test', 'test.py')
            assert self.platform is not None
            success, failure_message = module.run_test(  # type: ignore
                self.ndk_path, self.abi, self.platform, self.config.linker, self.ndk_build_flags)
            if success:
                return Success(self), []
            else:
                return Failure(self, failure_message), []


class ShellBuildTest(BuildTest):
    def __init__(self, name: str, test_dir: str, config: BuildConfiguration,
                 ndk_path: str) -> None:
        api = config.api
        if api is None:
            api = ndk.abis.min_api_for_abi(config.abi)
        config = ndk.test.spec.BuildConfiguration(config.abi, api,
                                                  config.linker)
        super().__init__(name, test_dir, config, ndk_path)

    def get_build_dir(self, out_dir: str) -> str:
        return os.path.join(out_dir, str(self.config), 'build.sh', self.name)

    def run(self, obj_dir: str, _dist_dir: str,
            _test_filters: TestFilter) -> Tuple[TestResult, List[Test]]:
        build_dir = self.get_build_dir(obj_dir)
        logger().info('Building test: %s', self.name)
        if os.name == 'nt':
            reason = 'build.sh tests are not supported on Windows'
            return Skipped(self, reason), []
        else:
            assert self.api is not None
            result = _run_build_sh_test(self, build_dir, self.test_dir,
                                        self.ndk_path, self.ndk_build_flags,
                                        self.abi, self.api, self.config.linker)
            return result, []


def _run_build_sh_test(test: ShellBuildTest, build_dir: str, test_dir: str,
                       ndk_path: str, ndk_build_flags: List[str], abi: Abi,
                       platform: int, linker: LinkerOption) -> TestResult:
    _prep_build_dir(test_dir, build_dir)
    with ndk.ext.os.cd(build_dir):
        build_cmd = ['bash', 'build.sh'] + _get_jobs_args() + ndk_build_flags
        test_env = dict(os.environ)
        test_env['NDK'] = ndk_path
        if abi is not None:
            test_env['APP_ABI'] = abi
        test_env['APP_PLATFORM'] = f'android-{platform}'
        test_env['APP_LD'] = linker.value
        rc, out = ndk.ext.subprocess.call_output(
            build_cmd, env=test_env, encoding='utf-8')
        if rc == 0:
            return Success(test)
        else:
            return Failure(test, out)


def _platform_from_application_mk(test_dir: str) -> Optional[int]:
    """Determine target API level from a test's Application.mk.

    Args:
        test_dir: Directory of the test to read.

    Returns:
        Integer portion of APP_PLATFORM if found, else None.

    Raises:
        ValueError: Found an unexpected value for APP_PLATFORM.
    """
    application_mk = os.path.join(test_dir, 'jni/Application.mk')
    if not os.path.exists(application_mk):
        return None

    with open(application_mk) as application_mk_file:
        for line in application_mk_file:
            if line.startswith('APP_PLATFORM'):
                _, platform_str = line.split(':=')
                break
        else:
            return None

    platform_str = platform_str.strip()
    if not platform_str.startswith('android-'):
        raise ValueError(platform_str)

    _, api_level_str = platform_str.split('-')
    return int(api_level_str)


def _get_or_infer_app_platform(platform_from_user: Optional[int],
                               test_dir: str, abi: Abi) -> int:
    """Determines the platform level to use for a test using ndk-build.

    Choose the platform level from, in order of preference:
    1. Value given as argument.
    2. APP_PLATFORM from jni/Application.mk.
    3. Default value for the target ABI.

    Args:
        platform_from_user: A user provided platform level or None.
        test_dir: The directory containing the ndk-build project.
        abi: The ABI being targeted.

    Returns:
        The platform version the test should build against.
    """
    if platform_from_user is not None:
        return platform_from_user

    minimum_version = ndk.abis.min_api_for_abi(abi)
    platform_from_application_mk = _platform_from_application_mk(test_dir)
    if platform_from_application_mk is not None:
        if platform_from_application_mk >= minimum_version:
            return platform_from_application_mk

    return minimum_version


class NdkBuildTest(BuildTest):
    def __init__(self, name: str, test_dir: str, config: BuildConfiguration,
                 ndk_path: str, dist: bool) -> None:
        api = _get_or_infer_app_platform(config.api, test_dir, config.abi)
        config = ndk.test.spec.BuildConfiguration(config.abi, api,
                                                  config.linker)
        super().__init__(name, test_dir, config, ndk_path)
        self.dist = dist

    def get_dist_dir(self, obj_dir: str, dist_dir: str) -> str:
        if self.dist:
            return self.get_build_dir(dist_dir)
        else:
            return os.path.join(self.get_build_dir(obj_dir), 'dist')

    def get_build_dir(self, out_dir: str) -> str:
        return os.path.join(out_dir, str(self.config), 'ndk-build', self.name)

    def run(self, obj_dir: str, dist_dir: str,
            _test_filters: TestFilter) -> Tuple[TestResult, List[Test]]:
        logger().info('Building test: %s', self.name)
        obj_dir = self.get_build_dir(obj_dir)
        dist_dir = self.get_dist_dir(obj_dir, dist_dir)
        assert self.api is not None
        result = _run_ndk_build_test(self, obj_dir, dist_dir, self.test_dir,
                                     self.ndk_path, self.ndk_build_flags,
                                     self.abi, self.api, self.config.linker)
        return result, []


def _run_ndk_build_test(test: NdkBuildTest, obj_dir: str, dist_dir: str,
                        test_dir: str, ndk_path: str,
                        ndk_build_flags: List[str], abi: Abi,
                        platform: int, linker: LinkerOption) -> TestResult:
    _prep_build_dir(test_dir, obj_dir)
    with ndk.ext.os.cd(obj_dir):
        args = [
            f'APP_ABI={abi}',
            f'APP_PLATFORM=android-{platform}',
            f'APP_LD={linker.value}',
            f'NDK_LIBS_OUT={dist_dir}',
        ] + _get_jobs_args()
        rc, out = ndk.ndkbuild.build(ndk_path, args + ndk_build_flags)
        if rc == 0:
            return Success(test)
        else:
            return Failure(test, out)


class CMakeBuildTest(BuildTest):
    def __init__(self, name: str, test_dir: str, config: BuildConfiguration,
                 ndk_path: str, dist: bool) -> None:
        api = _get_or_infer_app_platform(config.api, test_dir, config.abi)
        config = ndk.test.spec.BuildConfiguration(config.abi, api,
                                                  config.linker)
        super().__init__(name, test_dir, config, ndk_path)
        self.dist = dist

    def get_dist_dir(self, obj_dir: str, dist_dir: str) -> str:
        if self.dist:
            return self.get_build_dir(dist_dir)
        else:
            return os.path.join(self.get_build_dir(obj_dir), 'dist')

    def get_build_dir(self, out_dir: str) -> str:
        return os.path.join(out_dir, str(self.config), 'cmake', self.name)

    def run(self, obj_dir: str, dist_dir: str,
            _test_filters: TestFilter) -> Tuple[TestResult, List[Test]]:
        obj_dir = self.get_build_dir(obj_dir)
        dist_dir = self.get_dist_dir(obj_dir, dist_dir)
        logger().info('Building test: %s', self.name)
        assert self.api is not None
        result = _run_cmake_build_test(self, obj_dir, dist_dir, self.test_dir,
                                       self.ndk_path, self.cmake_flags,
                                       self.abi, self.api, self.config.linker)
        return result, []


def _run_cmake_build_test(test: CMakeBuildTest, obj_dir: str, dist_dir: str,
                          test_dir: str, ndk_path: str, cmake_flags: List[str],
                          abi: str, platform: int,
                          linker: LinkerOption) -> TestResult:
    _prep_build_dir(test_dir, obj_dir)

    # Add prebuilts to PATH.
    prebuilts_host_tag = ndk.hosts.get_default_host().value + '-x86'
    cmake_bin = ndk.paths.android_path(
        'prebuilts', 'cmake', prebuilts_host_tag, 'bin', 'cmake')
    ninja_bin = ndk.paths.android_path(
        'prebuilts', 'ninja', prebuilts_host_tag, 'ninja')

    toolchain_file = os.path.join(ndk_path, 'build', 'cmake',
                                  'android.toolchain.cmake')
    abi_obj_dir = os.path.join(obj_dir, abi)
    abi_lib_dir = os.path.join(dist_dir, abi)
    args = [
        f'-H{obj_dir}',
        f'-B{abi_obj_dir}',
        f'-DCMAKE_TOOLCHAIN_FILE={toolchain_file}',
        f'-DANDROID_ABI={abi}',
        f'-DANDROID_LD={linker.value}',
        f'-DCMAKE_RUNTIME_OUTPUT_DIRECTORY={abi_lib_dir}',
        f'-DCMAKE_LIBRARY_OUTPUT_DIRECTORY={abi_lib_dir}',
        '-GNinja',
        f'-DCMAKE_MAKE_PROGRAM={ninja_bin}',
    ]
    if platform is not None:
        args.append('-DANDROID_PLATFORM=android-{}'.format(platform))
    rc, out = ndk.ext.subprocess.call_output(
        [cmake_bin] + cmake_flags + args, encoding='utf-8')
    if rc != 0:
        return Failure(test, out)
    rc, out = ndk.ext.subprocess.call_output(
        [cmake_bin, '--build', abi_obj_dir, '--'] + _get_jobs_args(),
        encoding='utf-8')
    if rc != 0:
        return Failure(test, out)
    return Success(test)


def get_xunit_reports(xunit_file: Path, test_base_dir: str,
                      config: BuildConfiguration, ndk_path: str) -> List[Test]:
    tree = xml.etree.ElementTree.parse(str(xunit_file))
    root = tree.getroot()
    cases = root.findall('.//testcase')

    reports: List[Test] = []
    for test_case in cases:
        mangled_test_dir = test_case.get('classname')

        # The classname is the path from the root of the libc++ test directory
        # to the directory containing the test (prefixed with 'libc++.')...
        mangled_path = '/'.join([mangled_test_dir, test_case.get('name')])

        # ... that has had '.' in its path replaced with '_' because xunit.
        test_matches = find_original_libcxx_test(mangled_path)
        if not test_matches:
            raise RuntimeError('Found no matches for test ' + mangled_path)
        if len(test_matches) > 1:
            raise RuntimeError('Found multiple matches for test {}: {}'.format(
                mangled_path, test_matches))
        assert len(test_matches) == 1

        # We found a unique path matching the xunit class/test name.
        name = test_matches[0]
        test_dir = os.path.dirname(name)[len('libc++.'):]

        failure_nodes = test_case.findall('failure')
        if not failure_nodes:
            reports.append(XunitSuccess(
                name, test_base_dir, test_dir, config, ndk_path))
            continue

        if len(failure_nodes) != 1:
            msg = ('Could not parse XUnit output: test case does not have a '
                   'unique failure node: {}'.format(name))
            raise RuntimeError(msg)

        failure_node = failure_nodes[0]
        failure_text = failure_node.text
        assert failure_text is not None
        reports.append(XunitFailure(
            name, test_base_dir, test_dir, failure_text, config, ndk_path))
    return reports


def get_lit_cmd() -> Optional[List[str]]:
    # The build server doesn't install lit to a virtualenv, so use it from the
    # source location if possible.
    lit_path = ndk.paths.android_path('external/llvm/utils/lit/lit.py')
    if os.path.exists(lit_path):
        return ['python', lit_path]
    elif shutil.which('lit'):
        return ['lit']
    return None


def find_original_libcxx_test(name: str) -> List[str]:
    """Finds the original libc++ test file given the xunit test name.

    LIT mangles test names to replace all periods with underscores because
    xunit. This returns all tests that could possibly match the xunit test
    name.
    """

    name = ndk.paths.to_posix_path(name)

    # LIT special cases tests in the root of the test directory (such as
    # test/nothing_to_do.pass.cpp) as "libc++.libc++/$TEST_FILE.pass.cpp" for
    # some reason. Strip it off so we can find the tests.
    if name.startswith('libc++.libc++/'):
        name = 'libc++.' + name[len('libc++.libc++/'):]

    test_prefix = 'libc++.'
    if not name.startswith(test_prefix):
        raise ValueError('libc++ test name must begin with "libc++."')

    name = name[len(test_prefix):]
    test_pattern = name.replace('_', '?')
    matches = []

    # On Windows, a multiprocessing worker process does not inherit ALL_TESTS,
    # so we must scan libc++ tests in each worker.

    # ndk.test.scanner is not explicitly imported, which messes with mypy, but
    # works. We can't add the import because then there's a cyclic dependency
    # between this module and ndk.test.scanner. We'll need to refactor to fix
    # that.
    ndk.test.scanner.LibcxxTestScanner.find_all_libcxx_tests()  # type: ignore

    all_libcxx_tests = ndk.test.scanner.LibcxxTestScanner.ALL_TESTS  # type: ignore
    for match in fnmatch.filter(all_libcxx_tests, test_pattern):
        matches.append(test_prefix + match)
    return matches


class LibcxxTest(Test):
    def __init__(self, name: str, test_dir: str, config: BuildConfiguration,
                 ndk_path: str) -> None:
        if config.api is None:
            config.api = ndk.abis.min_api_for_abi(config.abi)

        super().__init__(name, test_dir, config, ndk_path)

    @property
    def abi(self) -> Abi:
        return self.config.abi

    @property
    def api(self) -> Optional[int]:
        return self.config.api

    def get_build_dir(self, out_dir: str) -> str:
        return os.path.join(out_dir, str(self.config), 'libcxx', self.name)

    def run_lit(self, lit: List[str], ndk_path: Path, libcxx_src: Path,
                libcxx_install: Path, build_dir: str,
                filters: List[str]) -> None:
        device_dir = '/data/local/tmp/libcxx'

        arch = ndk.abis.abi_to_arch(self.abi)
        host_tag = ndk.hosts.get_host_tag(self.ndk_path)
        triple = ndk.abis.arch_to_triple(arch)
        toolchain = ndk.abis.arch_to_toolchain(arch)

        replacements = [
            ('abi', self.abi),
            ('api', self.api),
            ('arch', arch),
            ('host_tag', host_tag),
            ('libcxx_install', libcxx_install),
            ('libcxx_src', libcxx_src),
            ('linker', self.config.linker.value),
            ('ndk_path', ndk_path),
            ('toolchain', toolchain),
            ('triple', f'{triple}{self.api}'),
            ('build_dir', build_dir),
        ]
        lit_cfg_args = []
        for key, value in replacements:
            lit_cfg_args.append(f'--param={key}={value}')

        xunit_output = os.path.join(build_dir, 'xunit.xml')
        # Remove the xunit output so we don't wrongly report stale results when
        # the test runner itself is broken. We ignore the exit status of the
        # test runner since we handle test failure reporting ourselves, so if
        # there's an error in the test runner itself it will be ignored and the
        # previous report will be reused.
        if os.path.exists(xunit_output):
            os.remove(xunit_output)

        lit_args = lit + [
            '-sv',
            '--param=device_dir=' + device_dir,
            '--param=build_only=True',
            '--no-progress-bar',
            '--show-all',
            '--xunit-xml-output=' + xunit_output,
        ] + lit_cfg_args

        default_test_path = os.path.join(libcxx_src, 'test')
        test_paths = list(filters)
        if not test_paths:
            test_paths.append(default_test_path)
        for test_path in test_paths:
            lit_args.append(test_path)

        # Ignore the exit code. We do most XFAIL processing outside the test
        # runner so expected failures in the test runner will still cause a
        # non-zero exit status. This "test" only fails if we encounter a Python
        # exception. Exceptions raised from our code are already caught by the
        # test runner. If that happens in LIT, the xunit output will not be
        # valid and we'll fail get_xunit_reports and raise an exception anyway.
        with open(os.devnull, 'w') as dev_null:
            stdout: Optional[TextIO] = dev_null
            stderr: Optional[TextIO] = dev_null
            if logger().isEnabledFor(logging.INFO):
                stdout = None
                stderr = None
            subprocess.call(lit_args, stdout=stdout, stderr=stderr)

    def run(self, obj_dir: str, dist_dir: str,
            test_filters: TestFilter) -> Tuple[TestResult, List[Test]]:
        lit = get_lit_cmd()
        if lit is None:
            return Failure(self, 'Could not find lit'), []

        libcxx_src = ndk.paths.ANDROID_DIR / 'external/libcxx'
        if not libcxx_src.exists():
            return Failure(self,
                           f'Expected libc++ directory at {libcxx_src}'), []

        build_dir = self.get_build_dir(dist_dir)

        if not os.path.exists(build_dir):
            os.makedirs(build_dir)

        xunit_output = Path(build_dir) / 'xunit.xml'
        libcxx_test_path = libcxx_src / 'test'
        ndk_path = Path(self.ndk_path)
        libcxx_install = (ndk_path / 'sources/cxx-stl/llvm-libc++' / 'libs' /
                          str(self.config.abi))
        libcxx_so_path = libcxx_install / 'libc++_shared.so'
        shutil.copy2(str(libcxx_so_path), build_dir)

        # The libc++ test runner's filters are path based. Assemble the path to
        # the test based on the late_filters (early filters for a libc++ test
        # would be simply "libc++", so that's not interesting at this stage).
        filters = []
        for late_filter in test_filters.late_filters:
            filter_pattern = late_filter.pattern
            if not filter_pattern.startswith('libc++.'):
                continue

            _, _, path = filter_pattern.partition('.')
            if not os.path.isabs(path):
                path = os.path.join(libcxx_test_path, path)

            # If we have a filter like "libc++.std", we'll run everything in
            # std, but all our XunitReport "tests" will be filtered out.  Make
            # sure we have something usable.
            if path.endswith('*'):
                # But the libc++ test runner won't like that, so strip it.
                path = path[:-1]
            elif not os.path.isfile(path):
                raise RuntimeError(f'{path} does not exist')

            filters.append(path)
        self.run_lit(lit, ndk_path, libcxx_src, libcxx_install, build_dir,
                     filters)

        for root, _, files in os.walk(libcxx_test_path):
            for test_file in files:
                if not test_file.endswith('.dat'):
                    continue
                test_relpath = os.path.relpath(root, libcxx_test_path)
                dest_dir = os.path.join(build_dir, test_relpath)
                if not os.path.exists(dest_dir):
                    continue

                shutil.copy2(os.path.join(root, test_file), dest_dir)

        # We create a bunch of fake tests that report the status of each
        # individual test in the xunit report.
        test_reports = get_xunit_reports(
            xunit_output, self.test_dir, self.config, self.ndk_path)

        return Success(self), test_reports

    # pylint: disable=no-self-use
    def check_broken(self) -> Union[Tuple[None, None], Tuple[str, str]]:
        # Actual results are reported individually by pulling them out of the
        # xunit output. This just reports the status of the overall test run,
        # which should be passing.
        return None, None

    def check_unsupported(self) -> Optional[str]:
        return None

    def is_negative_test(self) -> bool:
        return False
    # pylint: enable=no-self-use


class XunitResult(Test):
    """Fake tests so we can show a result for each libc++ test.

    We create these by parsing the xunit XML output from the libc++ test
    runner. For each result, we create an XunitResult "test" that simply
    returns a result for the xunit status.

    We don't have an ExpectedFailure form of the XunitResult because that is
    already handled for us by the libc++ test runner.
    """

    def __init__(self, name: str, test_base_dir: str, test_dir: str,
                 config: BuildConfiguration, ndk_path: str) -> None:
        super().__init__(name, test_dir, config, ndk_path)
        self.test_base_dir = test_base_dir

    @property
    def case_name(self) -> str:
        return os.path.splitext(os.path.basename(self.name))[0]

    def run(self, _out_dir: str, _dist_dir: str,
            _test_filters: TestFilter) -> Tuple[TestResult, List[Test]]:
        raise NotImplementedError

    def get_test_config(self) -> TestConfig:
        test_config_dir = os.path.join(self.test_base_dir, self.test_dir)
        return LibcxxTestConfig.from_test_dir(test_config_dir)

    def check_broken(self) -> Union[Tuple[None, None], Tuple[str, str]]:
        config, bug = self.get_test_config().build_broken(self)
        if config is not None:
            return config, bug
        return None, None

    # pylint: disable=no-self-use
    def check_unsupported(self) -> Optional[str]:
        return None

    def is_negative_test(self) -> bool:
        return False
    # pylint: enable=no-self-use


class XunitSuccess(XunitResult):
    def get_build_dir(self, out_dir: str) -> str:
        raise NotImplementedError

    def run(self, _out_dir: str, _dist_dir: str,
            _test_filters: TestFilter) -> Tuple[TestResult, List[Test]]:
        return Success(self), []


class XunitFailure(XunitResult):
    def __init__(self, name: str, test_base_dir: str, test_dir: str, text: str,
                 config: BuildConfiguration, ndk_path: str) -> None:
        super().__init__(name, test_base_dir, test_dir, config, ndk_path)
        self.text = text

    def get_build_dir(self, out_dir: str) -> str:
        raise NotImplementedError

    def run(self, _out_dir: str, _dist_dir: str,
            _test_filters: TestFilter) -> Tuple[TestResult, List[Test]]:
        return Failure(self, self.text), []
