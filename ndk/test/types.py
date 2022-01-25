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
from importlib.abc import Loader
import importlib.util
import logging
import multiprocessing
import os
from pathlib import Path, PurePosixPath
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
from ndk.cmake import find_cmake, find_ninja
import ndk.ext.os
import ndk.ext.subprocess
import ndk.hosts
import ndk.ndkbuild
import ndk.paths
from ndk.test.config import LibcxxTestConfig, TestConfig
from ndk.test.filters import TestFilter
from ndk.test.spec import BuildConfiguration, CMakeToolchainFile
from ndk.test.result import Failure, Skipped, Success, TestResult


def logger() -> logging.Logger:
    """Return the logger for this module."""
    return logging.getLogger(__name__)


def _get_jobs_args() -> List[str]:
    cpus = multiprocessing.cpu_count()
    return [f"-j{cpus}", f"-l{cpus}"]


def _prep_build_dir(src_dir: Path, out_dir: Path) -> None:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    shutil.copytree(src_dir, out_dir)


class Test:
    def __init__(
        self, name: str, test_dir: Path, config: BuildConfiguration, ndk_path: Path
    ) -> None:
        self.name = name
        self.test_dir = test_dir
        self.config = config
        self.ndk_path = ndk_path

    def get_test_config(self) -> TestConfig:
        return TestConfig.from_test_dir(self.test_dir)

    def run(
        self, obj_dir: Path, dist_dir: Path, test_filters: TestFilter
    ) -> Tuple[TestResult, List["Test"]]:
        raise NotImplementedError

    def is_negative_test(self) -> bool:
        raise NotImplementedError

    def check_broken(self) -> Union[Tuple[None, None], Tuple[str, str]]:
        return self.get_test_config().build_broken(self)

    def check_unsupported(self) -> Optional[str]:
        return self.get_test_config().build_unsupported(self)

    def get_build_dir(self, out_dir: Path) -> Path:
        raise NotImplementedError

    def __str__(self) -> str:
        return f"{self.name} [{self.config}]"


class BuildTest(Test):
    def __init__(
        self, name: str, test_dir: Path, config: BuildConfiguration, ndk_path: Path
    ) -> None:
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
    def ndk_build_flags(self) -> List[str]:
        flags = self.config.get_extra_ndk_build_flags()
        return flags + self.get_extra_ndk_build_flags()

    @property
    def cmake_flags(self) -> List[str]:
        flags = self.config.get_extra_cmake_flags()
        return flags + self.get_extra_cmake_flags()

    def run(
        self, obj_dir: Path, dist_dir: Path, _test_filters: TestFilter
    ) -> Tuple[TestResult, List[Test]]:
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
    contains a run_test function which returns a Tuple[bool, Optional[str]] of
    the success status and, if applicable, an error message and takes the
    following kwargs:

    ndk_path: The path to the NDK under test.
    abi: The ABI being tested.
    api: The minSdkVersion being tested.
    linker: The LinkerOption option being.

    The test source directory will be copied into the test build directory for
    the given build configuration. The working directory will automatically be
    set to the root of the copied source test directory.
    """

    def __init__(
        self, name: str, test_dir: Path, config: BuildConfiguration, ndk_path: Path
    ) -> None:
        if config.api is None:
            config = config.with_api(ndk.abis.min_api_for_abi(config.abi))
        super().__init__(name, test_dir, config, ndk_path)

        if self.abi not in ndk.abis.ALL_ABIS:
            raise ValueError("{} is not a valid ABI".format(self.abi))

        try:
            assert self.api is not None
            int(self.api)
        except ValueError as ex:
            raise ValueError(f"{self.api} is not a valid API number") from ex

    def get_build_dir(self, out_dir: Path) -> Path:
        return out_dir / str(self.config) / "test.py" / self.name

    def run(
        self, obj_dir: Path, _dist_dir: Path, _test_filters: TestFilter
    ) -> Tuple[TestResult, List[Test]]:
        build_dir = self.get_build_dir(obj_dir)
        logger().info("Building test: %s", self.name)
        _prep_build_dir(self.test_dir, build_dir)
        with ndk.ext.os.cd(build_dir):
            spec = importlib.util.spec_from_file_location("test", "test.py")
            if spec is None or spec.loader is None:
                path = build_dir / "test.py"
                raise RuntimeError(f"Could not import {path}")
            module = importlib.util.module_from_spec(spec)
            # https://github.com/python/typeshed/issues/2793
            assert isinstance(spec.loader, Loader)
            spec.loader.exec_module(module)
            success, failure_message = module.run_test(  # type: ignore
                self.ndk_path, self.config
            )
            if success:
                return Success(self), []
            else:
                return Failure(self, failure_message), []


class ShellBuildTest(BuildTest):
    def __init__(
        self, name: str, test_dir: Path, config: BuildConfiguration, ndk_path: Path
    ) -> None:
        if config.api is None:
            config = config.with_api(ndk.abis.min_api_for_abi(config.abi))
        super().__init__(name, test_dir, config, ndk_path)

    def get_build_dir(self, out_dir: Path) -> Path:
        return out_dir / str(self.config) / "build.sh" / self.name

    def run(
        self, obj_dir: Path, _dist_dir: Path, _test_filters: TestFilter
    ) -> Tuple[TestResult, List[Test]]:
        build_dir = self.get_build_dir(obj_dir)
        logger().info("Building test: %s", self.name)
        if os.name == "nt":
            reason = "build.sh tests are not supported on Windows"
            return Skipped(self, reason), []
        else:
            assert self.api is not None
            result = _run_build_sh_test(
                self,
                build_dir,
                self.test_dir,
                self.ndk_path,
                self.ndk_build_flags,
                self.abi,
                self.api,
            )
            return result, []


def _run_build_sh_test(
    test: ShellBuildTest,
    build_dir: Path,
    test_dir: Path,
    ndk_path: Path,
    ndk_build_flags: List[str],
    abi: Abi,
    platform: int,
) -> TestResult:
    _prep_build_dir(test_dir, build_dir)
    with ndk.ext.os.cd(build_dir):
        build_cmd = ["bash", "build.sh"] + _get_jobs_args() + ndk_build_flags
        test_env = dict(os.environ)
        test_env["NDK"] = str(ndk_path)
        if abi is not None:
            test_env["APP_ABI"] = abi
        test_env["APP_PLATFORM"] = f"android-{platform}"
        rc, out = ndk.ext.subprocess.call_output(
            build_cmd, env=test_env, encoding="utf-8"
        )
        if rc == 0:
            return Success(test)
        else:
            return Failure(test, out)


def _platform_from_application_mk(test_dir: Path) -> Optional[int]:
    """Determine target API level from a test's Application.mk.

    Args:
        test_dir: Directory of the test to read.

    Returns:
        Integer portion of APP_PLATFORM if found, else None.

    Raises:
        ValueError: Found an unexpected value for APP_PLATFORM.
    """
    application_mk = test_dir / "jni" / "Application.mk"
    if not application_mk.exists():
        return None

    with open(application_mk) as application_mk_file:
        for line in application_mk_file:
            if line.startswith("APP_PLATFORM"):
                _, platform_str = line.split(":=")
                break
        else:
            return None

    platform_str = platform_str.strip()
    if not platform_str.startswith("android-"):
        raise ValueError(platform_str)

    _, api_level_str = platform_str.split("-")
    return int(api_level_str)


def _get_or_infer_app_platform(
    platform_from_user: Optional[int], test_dir: Path, abi: Abi
) -> int:
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
    def __init__(
        self,
        name: str,
        test_dir: Path,
        config: BuildConfiguration,
        ndk_path: Path,
        dist: bool,
    ) -> None:
        if config.api is None:
            config = config.with_api(
                _get_or_infer_app_platform(config.api, test_dir, config.abi)
            )
        super().__init__(name, test_dir, config, ndk_path)
        self.dist = dist

    def get_dist_dir(self, obj_dir: Path, dist_dir: Path) -> Path:
        if self.dist:
            return self.get_build_dir(dist_dir)
        else:
            return self.get_build_dir(obj_dir) / "dist"

    def get_build_dir(self, out_dir: Path) -> Path:
        return out_dir / str(self.config) / "ndk-build" / self.name

    def run(
        self, obj_dir: Path, dist_dir: Path, _test_filters: TestFilter
    ) -> Tuple[TestResult, List[Test]]:
        logger().info("Building test: %s", self.name)
        obj_dir = self.get_build_dir(obj_dir)
        dist_dir = self.get_dist_dir(obj_dir, dist_dir)
        assert self.api is not None
        result = _run_ndk_build_test(
            self,
            obj_dir,
            dist_dir,
            self.test_dir,
            self.ndk_path,
            self.ndk_build_flags,
            self.abi,
            self.api,
        )
        return result, []


def _run_ndk_build_test(
    test: NdkBuildTest,
    obj_dir: Path,
    dist_dir: Path,
    test_dir: Path,
    ndk_path: Path,
    ndk_build_flags: List[str],
    abi: Abi,
    platform: int,
) -> TestResult:
    _prep_build_dir(test_dir, obj_dir)
    with ndk.ext.os.cd(obj_dir):
        args = [
            f"APP_ABI={abi}",
            f"APP_PLATFORM=android-{platform}",
            f"NDK_LIBS_OUT={dist_dir}",
        ] + _get_jobs_args()
        rc, out = ndk.ndkbuild.build(ndk_path, args + ndk_build_flags)
        if rc == 0:
            return Success(test)
        else:
            return Failure(test, out)


class CMakeBuildTest(BuildTest):
    def __init__(
        self,
        name: str,
        test_dir: Path,
        config: BuildConfiguration,
        ndk_path: Path,
        dist: bool,
    ) -> None:
        if config.api is None:
            config = config.with_api(
                _get_or_infer_app_platform(config.api, test_dir, config.abi)
            )
        super().__init__(name, test_dir, config, ndk_path)
        self.dist = dist

    def get_dist_dir(self, obj_dir: Path, dist_dir: Path) -> Path:
        if self.dist:
            return self.get_build_dir(dist_dir)
        else:
            return self.get_build_dir(obj_dir) / "dist"

    def get_build_dir(self, out_dir: Path) -> Path:
        return out_dir / str(self.config) / "cmake" / self.name

    def run(
        self, obj_dir: Path, dist_dir: Path, _test_filters: TestFilter
    ) -> Tuple[TestResult, List[Test]]:
        obj_dir = self.get_build_dir(obj_dir)
        dist_dir = self.get_dist_dir(obj_dir, dist_dir)
        logger().info("Building test: %s", self.name)
        assert self.api is not None
        result = _run_cmake_build_test(
            self,
            obj_dir,
            dist_dir,
            self.test_dir,
            self.ndk_path,
            self.cmake_flags,
            self.abi,
            self.api,
            self.config.toolchain_file == CMakeToolchainFile.Legacy,
        )
        return result, []


def _run_cmake_build_test(
    test: CMakeBuildTest,
    obj_dir: Path,
    dist_dir: Path,
    test_dir: Path,
    ndk_path: Path,
    cmake_flags: List[str],
    abi: str,
    platform: int,
    use_legacy_toolchain_file: bool,
) -> TestResult:
    _prep_build_dir(test_dir, obj_dir)

    cmake_bin = find_cmake()
    ninja_bin = find_ninja()

    toolchain_file = ndk_path / "build" / "cmake" / "android.toolchain.cmake"
    abi_obj_dir = obj_dir / abi
    abi_lib_dir = dist_dir / abi
    args = [
        f"-H{obj_dir}",
        f"-B{abi_obj_dir}",
        f"-DCMAKE_TOOLCHAIN_FILE={toolchain_file}",
        f"-DANDROID_ABI={abi}",
        f"-DCMAKE_RUNTIME_OUTPUT_DIRECTORY={abi_lib_dir}",
        f"-DCMAKE_LIBRARY_OUTPUT_DIRECTORY={abi_lib_dir}",
        "-GNinja",
        f"-DCMAKE_MAKE_PROGRAM={ninja_bin}",
    ]
    if platform is not None:
        args.append("-DANDROID_PLATFORM=android-{}".format(platform))
    if use_legacy_toolchain_file:
        args.append("-DANDROID_USE_LEGACY_TOOLCHAIN_FILE=ON")
    else:
        args.append("-DANDROID_USE_LEGACY_TOOLCHAIN_FILE=OFF")
    rc, out = ndk.ext.subprocess.call_output(
        [str(cmake_bin)] + cmake_flags + args, encoding="utf-8"
    )
    if rc != 0:
        return Failure(test, out)
    rc, out = ndk.ext.subprocess.call_output(
        [str(cmake_bin), "--build", str(abi_obj_dir), "--"] + _get_jobs_args(),
        encoding="utf-8",
    )
    if rc != 0:
        return Failure(test, out)
    return Success(test)


def get_xunit_reports(
    xunit_file: Path, test_base_dir: Path, config: BuildConfiguration, ndk_path: Path
) -> List[Test]:
    tree = xml.etree.ElementTree.parse(str(xunit_file))
    root = tree.getroot()
    cases = root.findall(".//testcase")

    reports: List[Test] = []
    for test_case in cases:
        mangled_test_dir = test_case.get("classname")
        assert mangled_test_dir is not None

        case_name = test_case.get("name")
        assert case_name is not None

        # The classname is the path from the root of the libc++ test directory
        # to the directory containing the test (prefixed with 'libc++.')...
        mangled_path = "/".join([mangled_test_dir, case_name])

        # ... that has had '.' in its path replaced with '_' because xunit.
        test_matches = find_original_libcxx_test(mangled_path)
        if not test_matches:
            raise RuntimeError(f"Found no matches for test {mangled_path}")
        if len(test_matches) > 1:
            raise RuntimeError(
                "Found multiple matches for test {}: {}".format(
                    mangled_path, test_matches
                )
            )
        assert len(test_matches) == 1

        # We found a unique path matching the xunit class/test name.
        name = test_matches[0]
        test_dir = Path(os.path.dirname(name)[len("libc++.") :])

        failure_nodes = test_case.findall("failure")
        if not failure_nodes:
            reports.append(
                XunitSuccess(name, test_base_dir, test_dir, config, ndk_path)
            )
            continue

        if len(failure_nodes) != 1:
            msg = (
                "Could not parse XUnit output: test case does not have a "
                "unique failure node: {}".format(name)
            )
            raise RuntimeError(msg)

        failure_node = failure_nodes[0]
        failure_text = failure_node.text
        assert failure_text is not None
        reports.append(
            XunitFailure(name, test_base_dir, test_dir, failure_text, config, ndk_path)
        )
    return reports


def get_lit_cmd() -> Optional[List[str]]:
    # The build server doesn't install lit to a virtualenv, so use it from the
    # source location if possible.
    lit_path = ndk.paths.android_path("toolchain/llvm-project/llvm/utils/lit/lit.py")
    if lit_path.exists():
        return ["python", str(lit_path)]
    elif shutil.which("lit"):
        return ["lit"]
    return None


def find_original_libcxx_test(name: str) -> List[str]:
    """Finds the original libc++ test file given the xunit test name.

    LIT mangles test names to replace all periods with underscores because
    xunit. This returns all tests that could possibly match the xunit test
    name.
    """

    name = str(PurePosixPath(name))

    # LIT special cases tests in the root of the test directory (such as
    # test/nothing_to_do.pass.cpp) as "libc++.libc++/$TEST_FILE.pass.cpp" for
    # some reason. Strip it off so we can find the tests.
    if name.startswith("libc++.libc++/"):
        name = "libc++." + name[len("libc++.libc++/") :]

    test_prefix = "libc++."
    if not name.startswith(test_prefix):
        raise ValueError('libc++ test name must begin with "libc++."')

    name = name[len(test_prefix) :]
    test_pattern = name.replace("_", "?")
    matches = []

    # On Windows, a multiprocessing worker process does not inherit ALL_TESTS,
    # so we must scan libc++ tests in each worker.
    from ndk.test.scanner import (  # pylint: disable=import-outside-toplevel
        LibcxxTestScanner,
    )

    LibcxxTestScanner.find_all_libcxx_tests()
    all_libcxx_tests = LibcxxTestScanner.ALL_TESTS
    for match in fnmatch.filter(all_libcxx_tests, test_pattern):
        matches.append(test_prefix + match)
    return matches


class LibcxxTest(Test):
    def __init__(
        self, name: str, test_dir: Path, config: BuildConfiguration, ndk_path: Path
    ) -> None:
        if config.api is None:
            config = config.with_api(ndk.abis.min_api_for_abi(config.abi))
        super().__init__(name, test_dir, config, ndk_path)

    @property
    def abi(self) -> Abi:
        return self.config.abi

    @property
    def api(self) -> Optional[int]:
        return self.config.api

    def get_build_dir(self, out_dir: Path) -> Path:
        return out_dir / str(self.config) / "libcxx" / self.name

    def run_lit(
        self,
        lit: List[str],
        ndk_path: Path,
        libcxx_src: Path,
        libcxx_install: Path,
        build_dir: Path,
        filters: List[str],
    ) -> None:
        arch = ndk.abis.abi_to_arch(self.abi)
        host_tag = ndk.hosts.get_host_tag()
        target = ndk.abis.clang_target(arch, self.api)
        toolchain = ndk.abis.arch_to_toolchain(arch)

        replacements = [
            ("abi", self.abi),
            ("api", self.api),
            ("arch", arch),
            ("host_tag", host_tag),
            ("libcxx_install", libcxx_install),
            ("libcxx_src", libcxx_src),
            ("ndk_path", ndk_path),
            ("toolchain", toolchain),
            ("triple", target),
            ("build_dir", build_dir),
            # TODO(danalbert): Migrate to the new test format.
            ("use_old_format", "true"),
        ]
        lit_cfg_args = []
        for key, value in replacements:
            lit_cfg_args.append(f"--param={key}={value}")

        xunit_output = build_dir / "xunit.xml"
        # Remove the xunit output so we don't wrongly report stale results when
        # the test runner itself is broken. We ignore the exit status of the
        # test runner since we handle test failure reporting ourselves, so if
        # there's an error in the test runner itself it will be ignored and the
        # previous report will be reused.
        if xunit_output.exists():
            os.remove(xunit_output)

        lit_args = (
            lit
            + [
                "-sv",
                "--param=build_only=True",
                "--no-progress-bar",
                "--show-all",
                f"--xunit-xml-output={xunit_output}",
            ]
            + lit_cfg_args
        )

        default_test_path = libcxx_src / "test"
        test_paths = list(filters)
        if not test_paths:
            test_paths.append(str(default_test_path))
        for test_path in test_paths:
            lit_args.append(test_path)

        # Ignore the exit code. We do most XFAIL processing outside the test
        # runner so expected failures in the test runner will still cause a
        # non-zero exit status. This "test" only fails if we encounter a Python
        # exception. Exceptions raised from our code are already caught by the
        # test runner. If that happens in LIT, the xunit output will not be
        # valid and we'll fail get_xunit_reports and raise an exception anyway.
        with open(os.devnull, "w") as dev_null:
            stdout: Optional[TextIO] = dev_null
            stderr: Optional[TextIO] = dev_null
            if logger().isEnabledFor(logging.INFO):
                stdout = None
                stderr = None
            subprocess.call(lit_args, stdout=stdout, stderr=stderr)

    def run(
        self, obj_dir: Path, dist_dir: Path, test_filters: TestFilter
    ) -> Tuple[TestResult, List[Test]]:
        lit = get_lit_cmd()
        if lit is None:
            return Failure(self, "Could not find lit"), []

        libcxx_src = ndk.paths.ANDROID_DIR / "toolchain/llvm-project/libcxx"
        if not libcxx_src.exists():
            return Failure(self, f"Expected libc++ directory at {libcxx_src}"), []

        build_dir = self.get_build_dir(dist_dir)

        if not build_dir.exists():
            build_dir.mkdir(parents=True)

        xunit_output = Path(build_dir) / "xunit.xml"
        libcxx_test_path = libcxx_src / "test"
        ndk_path = Path(self.ndk_path)
        libcxx_install = (
            ndk_path / "sources/cxx-stl/llvm-libc++" / "libs" / str(self.config.abi)
        )
        libcxx_so_path = libcxx_install / "libc++_shared.so"
        shutil.copy2(str(libcxx_so_path), build_dir)

        # The libc++ test runner's filters are path based. Assemble the path to
        # the test based on the late_filters (early filters for a libc++ test
        # would be simply "libc++", so that's not interesting at this stage).
        filters = []
        for late_filter in test_filters.late_filters:
            filter_pattern = late_filter.pattern
            if not filter_pattern.startswith("libc++."):
                continue

            _, _, path = filter_pattern.partition(".")
            if not os.path.isabs(path):
                path = os.path.join(libcxx_test_path, path)

            # If we have a filter like "libc++.std", we'll run everything in
            # std, but all our XunitReport "tests" will be filtered out.  Make
            # sure we have something usable.
            if path.endswith("*"):
                # But the libc++ test runner won't like that, so strip it.
                path = path[:-1]
            elif not os.path.isfile(path):
                raise RuntimeError(f"{path} does not exist")

            filters.append(path)
        self.run_lit(lit, ndk_path, libcxx_src, libcxx_install, build_dir, filters)

        for root, _, files in os.walk(libcxx_test_path):
            for test_file in files:
                if not test_file.endswith(".dat"):
                    continue
                test_relpath = os.path.relpath(root, libcxx_test_path)
                dest_dir = build_dir / test_relpath
                if not dest_dir.exists():
                    continue

                shutil.copy2(str(Path(root) / test_file), dest_dir)

        # We create a bunch of fake tests that report the status of each
        # individual test in the xunit report.
        test_reports = get_xunit_reports(
            xunit_output, self.test_dir, self.config, self.ndk_path
        )

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

    def __init__(
        self,
        name: str,
        test_base_dir: Path,
        test_dir: Path,
        config: BuildConfiguration,
        ndk_path: Path,
    ) -> None:
        super().__init__(name, test_dir, config, ndk_path)
        self.test_base_dir = test_base_dir

    @property
    def case_name(self) -> str:
        return os.path.splitext(os.path.basename(self.name))[0]

    def run(
        self, _out_dir: Path, _dist_dir: Path, _test_filters: TestFilter
    ) -> Tuple[TestResult, List[Test]]:
        raise NotImplementedError

    def get_test_config(self) -> TestConfig:
        test_config_dir = self.test_base_dir / self.test_dir
        return LibcxxTestConfig.from_test_dir(test_config_dir)

    def check_broken(self) -> Union[Tuple[None, None], Tuple[str, str]]:
        config, bug = self.get_test_config().build_broken(self)
        if config is not None:
            assert bug is not None
            return config, bug
        return None, None

    # pylint: disable=no-self-use
    def check_unsupported(self) -> Optional[str]:
        return None

    def is_negative_test(self) -> bool:
        return False

    # pylint: enable=no-self-use


class XunitSuccess(XunitResult):
    def get_build_dir(self, out_dir: Path) -> Path:
        raise NotImplementedError

    def run(
        self, _out_dir: Path, _dist_dir: Path, _test_filters: TestFilter
    ) -> Tuple[TestResult, List[Test]]:
        return Success(self), []


class XunitFailure(XunitResult):
    def __init__(
        self,
        name: str,
        test_base_dir: Path,
        test_dir: Path,
        text: str,
        config: BuildConfiguration,
        ndk_path: Path,
    ) -> None:
        super().__init__(name, test_base_dir, test_dir, config, ndk_path)
        self.text = text

    def get_build_dir(self, out_dir: Path) -> Path:
        raise NotImplementedError

    def run(
        self, _out_dir: Path, _dist_dir: Path, _test_filters: TestFilter
    ) -> Tuple[TestResult, List[Test]]:
        return Failure(self, self.text), []
