#!/usr/bin/env python
#
# Copyright (C) 2017 The Android Open Source Project
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
"""Runs the tests built by make_tests.py."""
from __future__ import absolute_import
from __future__ import print_function

import argparse
import collections
import datetime
import json
import logging
import os
import posixpath
import random
import shlex
import site
import subprocess
import sys
import time
import traceback
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Union,
)

from ndk.abis import Abi
import ndk.ansi
import ndk.ext.subprocess
import ndk.notify
import ndk.paths
import ndk.test.builder
from ndk.test.config import DeviceTestConfig, LibcxxTestConfig
from ndk.test.devices import (
    Device,
    DeviceFleet,
    DeviceShardingGroup,
    find_devices,
)
from ndk.test.filters import TestFilter
from ndk.test.printers import Printer, StdoutPrinter
from ndk.test.report import Report
from ndk.test.result import (
    ExpectedFailure,
    Failure,
    Skipped,
    Success,
    TestResult,
    UnexpectedSuccess,
)
from ndk.test.spec import BuildConfiguration
import ndk.test.types
import ndk.test.ui
from ndk.timer import Timer
import ndk.ui
from ndk.workqueue import ShardingWorkQueue, Worker, WorkQueue


DEVICE_TEST_BASE_DIR = '/data/local/tmp/tests'


def logger() -> logging.Logger:
    """Returns the module logger."""
    return logging.getLogger(__name__)


def shell_nocheck_wrap_errors(device: Device,
                              cmd: Sequence[str]) -> Tuple[int, str, str]:
    """Invokes device.shell_nocheck and wraps exceptions as failed commands."""
    try:
        return device.shell_nocheck(cmd)
    except RuntimeError:
        return 1, shlex.join(cmd), traceback.format_exc()


# TODO: Extract a common interface from this and ndk.test.types.Test for the
# printer.
class TestCase:
    """A test case found in the dist directory.

    The test directory is structured as tests/dist/$CONFIG/$BUILD_SYTEM/...
    What follows depends on the type of test case. Each discovered test case
    will have a name, a build configuration, a build system, and a device
    directory.
    """

    def __init__(self, name: str, test_src_dir: str,
                 config: BuildConfiguration, build_system: str,
                 device_dir: str) -> None:
        self.name = name
        self.test_src_dir = test_src_dir
        self.config = config
        self.build_system = build_system
        self.device_dir = device_dir

    def check_unsupported(self, device: Device) -> Optional[str]:
        raise NotImplementedError

    def check_broken(
            self, device: Device) -> Union[Tuple[None, None], Tuple[str, str]]:
        raise NotImplementedError

    def run(self, device: Device) -> Tuple[int, str, str]:
        raise NotImplementedError


class BasicTestCase(TestCase):
    """A test case for the standard NDK test builder.

    These tests were written specifically for the NDK and thus follow the
    layout we expect. In each test configuration directory, we have
    $TEST_SUITE/$ABI/$TEST_FILES. $TEST_FILES includes both the shared
    libraries for the test and the test executables.
    """

    def __init__(self, suite: str, executable: str, test_src_dir: str,
                 config: BuildConfiguration, build_system: str,
                 device_dir: str) -> None:
        name = '.'.join([suite, executable])
        super().__init__(name, test_src_dir, config, build_system, device_dir)

        self.suite = suite
        self.executable = executable

    def get_test_config(self) -> DeviceTestConfig:
        # We don't run anything in tests/build, and the libc++ tests are
        # handled by a different LibcxxTest. We can safely assume that anything
        # here is in tests/device.
        test_dir = os.path.join(self.test_src_dir, 'device', self.suite)
        return DeviceTestConfig.from_test_dir(test_dir)

    def check_unsupported(self, device: Device) -> Optional[str]:
        return self.get_test_config().run_unsupported(self, device)

    def check_broken(
            self, device: Device) -> Union[Tuple[None, None], Tuple[str, str]]:
        return self.get_test_config().run_broken(self, device)

    def run(self, device: Device) -> Tuple[int, str, str]:
        cmd = 'cd {} && LD_LIBRARY_PATH={} ./{} 2>&1'.format(
            self.device_dir, self.device_dir, self.executable)
        logger().info('%s: shell_nocheck "%s"', device.name, cmd)
        return shell_nocheck_wrap_errors(device, [cmd])


class LibcxxTestCase(TestCase):
    """A libc++ test case built by LIT.

    LIT's test structure doesn't map cleanly to ours; they have a hierarchical
    test structure. The top level contains a single "libc++" directory. In that
    directory is where shared libraries common to all tests are placed. That
    directory and any under it may contain test executables (always suffixed
    with ".exe") or test data (always suffixed with ".dat").
    """

    def __init__(self, suite: str, executable: str, test_src_dir: str,
                 config: BuildConfiguration, device_dir: str) -> None:
        # Tests in the top level don't need any mangling to match the filters.
        if suite == 'libc++':
            filter_name = executable
        else:
            filter_name = os.path.join(suite[len('libc++/'):], executable)

        # The executable name ends with .exe. Remove that so it matches the
        # filter that would be used to build the test.
        name = '.'.join(['libc++', filter_name[:-4]])
        super().__init__(name, test_src_dir, config, 'libc++', device_dir)
        self.suite = suite
        self.executable = executable

    @property
    def case_name(self) -> str:
        # Executable is foo.pass.cpp.exe, we want foo.pass.
        return os.path.splitext(os.path.splitext(self.executable)[0])[0]

    def get_test_config(self) -> DeviceTestConfig:
        _, _, test_subdir = self.suite.partition('/')
        test_dir = os.path.join(self.test_src_dir, 'libc++/test', test_subdir)
        return LibcxxTestConfig.from_test_dir(test_dir)

    def check_unsupported(self, device: Device) -> Optional[str]:
        config = self.get_test_config().run_unsupported(self, device)
        if config is not None:
            return config
        return None

    def check_broken(
            self, device: Device) -> Union[Tuple[None, None], Tuple[str, str]]:
        config, bug = self.get_test_config().run_broken(self, device)
        if config is not None:
            return config, bug
        return None, None

    def run(self, device: Device) -> Tuple[int, str, str]:
        libcxx_so_dir = posixpath.join(
            DEVICE_TEST_BASE_DIR, str(self.config), 'libcxx/libc++')
        cmd = 'cd {} && LD_LIBRARY_PATH={} ./{} 2>&1'.format(
            self.device_dir, libcxx_so_dir, self.executable)
        logger().info('%s: shell_nocheck "%s"', device.name, cmd)
        return shell_nocheck_wrap_errors(device, [cmd])


class TestRun:
    """A test case mapped to the device group it will run on."""

    def __init__(self, test_case: TestCase,
                 device_group: DeviceShardingGroup) -> None:
        self.test_case = test_case
        self.device_group = device_group

    @property
    def name(self) -> str:
        return self.test_case.name

    @property
    def build_system(self) -> str:
        return self.test_case.build_system

    @property
    def config(self) -> BuildConfiguration:
        return self.test_case.config

    def make_result(self, adb_result_tuple: Tuple[int, str, str],
                    device: Device) -> TestResult:
        status, out, _ = adb_result_tuple
        result: TestResult
        if status == 0:
            result = Success(self)
        else:
            out = '\n'.join([str(device), out])
            result = Failure(self, out)
        return self.fixup_xfail(result, device)

    def fixup_xfail(self, result: TestResult, device: Device) -> TestResult:
        config, bug = self.test_case.check_broken(device)
        if config is not None:
            assert bug is not None
            if result.failed():
                return ExpectedFailure(self, config, bug)
            elif result.passed():
                return UnexpectedSuccess(self, config, bug)
            raise ValueError('Test result must have either failed or passed.')
        return result

    def run(self, device: Device) -> TestResult:
        config = self.test_case.check_unsupported(device)
        if config is not None:
            return Skipped(self, f'test unsupported for {config}')
        return self.make_result(self.test_case.run(device), device)


def build_tests(test_src_dir: str, ndk_dir: str, out_dir: str, clean: bool,
                printer: Printer, config: Dict[Any, Any],
                test_filter: str) -> Report:
    test_options = ndk.test.spec.TestOptions(
        test_src_dir, ndk_dir, out_dir, test_filter=test_filter, clean=clean)

    test_spec = ndk.test.builder.test_spec_from_config(config)
    builder = ndk.test.builder.TestBuilder(test_spec, test_options, printer)

    return builder.build()


def enumerate_basic_tests(out_dir_base: str, test_src_dir: str,
                          build_cfg: BuildConfiguration, build_system: str,
                          test_filter: TestFilter) -> List[TestCase]:
    tests: List[TestCase] = []
    tests_dir = os.path.join(out_dir_base, str(build_cfg), build_system)
    if not os.path.exists(tests_dir):
        return tests

    for test_subdir in os.listdir(tests_dir):
        test_dir = os.path.join(tests_dir, test_subdir)
        out_dir = os.path.join(test_dir, build_cfg.abi)
        test_relpath = os.path.relpath(out_dir, out_dir_base)
        device_dir = posixpath.join(
            DEVICE_TEST_BASE_DIR, ndk.paths.to_posix_path(test_relpath))
        for test_file in os.listdir(out_dir):
            if test_file.endswith('.so'):
                continue
            if test_file.endswith('.sh'):
                continue
            name = '.'.join([test_subdir, test_file])
            if not test_filter.filter(name):
                continue
            tests.append(BasicTestCase(
                test_subdir, test_file, test_src_dir, build_cfg, build_system,
                device_dir))
    return tests


def enumerate_libcxx_tests(out_dir_base: str, test_src_dir: str,
                           build_cfg: BuildConfiguration, build_system: str,
                           test_filter: TestFilter) -> List[TestCase]:
    tests: List[TestCase] = []
    tests_dir = os.path.join(out_dir_base, str(build_cfg), build_system)
    if not os.path.exists(tests_dir):
        return tests

    for root, _, files in os.walk(tests_dir):
        for test_file in files:
            if not test_file.endswith('.exe'):
                continue
            test_relpath = os.path.relpath(root, out_dir_base)
            device_dir = posixpath.join(
                DEVICE_TEST_BASE_DIR, ndk.paths.to_posix_path(test_relpath))
            suite_name = ndk.paths.to_posix_path(
                os.path.relpath(root, tests_dir))

            # Our file has a .exe extension, but the name should match the
            # source file for the filters to work.
            test_name = test_file[:-4]

            # Tests in the top level don't need any mangling to match the
            # filters.
            if suite_name != 'libc++':
                if not suite_name.startswith('libc++/'):
                    raise ValueError(suite_name)
                # According to the test runner, these are all part of the
                # "libc++" test, and the rest of the data is the subtest name.
                # i.e.  libc++/foo/bar/baz.cpp.exe is actually
                # libc++.foo/bar/baz.cpp.  Matching this expectation here
                # allows us to use the same filter string for running the tests
                # as for building the tests.
                test_path = suite_name[len('libc++/'):]
                test_name = '/'.join([test_path, test_name])

            filter_name = '.'.join(['libc++', test_name])
            if not test_filter.filter(filter_name):
                continue
            tests.append(LibcxxTestCase(
                suite_name, test_file, test_src_dir, build_cfg, device_dir))
    return tests


class ConfigFilter:
    def __init__(self, test_config: Dict[Any, Any]) -> None:
        test_spec = ndk.test.builder.test_spec_from_config(test_config)
        self.spec = test_spec

    def filter(self, build_config: BuildConfiguration) -> bool:
        return build_config.abi in self.spec.abis


def enumerate_tests(
        test_dir: str, test_src_dir: str, test_filter: TestFilter,
        config_filter: ConfigFilter
) -> Dict[BuildConfiguration, List[TestCase]]:
    tests: Dict[BuildConfiguration, List[TestCase]] = {}

    # The tests directory has a directory for each type of test. For example:
    #
    #  * build.sh
    #  * cmake
    #  * libcxx
    #  * ndk-build
    #  * test.py
    #
    # We need to handle some of these differently. The test.py and build.sh
    # type tests are build only, so we don't need to run them. The libc++ tests
    # are built by a test runner we don't control, so its output doesn't quite
    # match what we expect.
    test_subdir_class_map: Dict[str, Callable[
        [str, str, BuildConfiguration, str, TestFilter], List[TestCase]]] = {
            'cmake': enumerate_basic_tests,
            'libcxx': enumerate_libcxx_tests,
            'ndk-build': enumerate_basic_tests,
        }

    for build_cfg_str in os.listdir(test_dir):
        build_cfg = BuildConfiguration.from_string(build_cfg_str)
        if not config_filter.filter(build_cfg):
            continue

        if build_cfg not in tests:
            tests[build_cfg] = []

        for test_type, scan_for_tests in test_subdir_class_map.items():
            tests[build_cfg].extend(scan_for_tests(
                test_dir, test_src_dir, build_cfg, test_type, test_filter))

    return tests


def clear_test_directory(_worker: Worker, device: Device) -> None:
    print(f'Clearing test directory on {device}')
    cmd = ['rm', '-r', DEVICE_TEST_BASE_DIR]
    logger().info('%s: shell_nocheck "%s"', device.name, cmd)
    device.shell_nocheck(cmd)


def clear_test_directories(workqueue: WorkQueue, fleet: DeviceFleet) -> None:
    for group in fleet.get_unique_device_groups():
        for device in group.devices:
            workqueue.add_task(clear_test_directory, device)

    while not workqueue.finished():
        workqueue.get_result()


def adb_has_feature(feature: str) -> bool:
    cmd = ['adb', 'host-features']
    logger().info('check_output "%s"', ' '.join(cmd))
    output = subprocess.check_output(cmd).decode('utf-8')
    features_line = output.splitlines()[-1]
    features = features_line.split(',')
    return feature in features


def push_tests_to_device(worker: Worker, src_dir: str, dest_dir: str,
                         config: BuildConfiguration, device: Device,
                         use_sync: bool) -> None:
    """Pushes a directory to the given device.

    Creates the parent directory on the device if needed.

    Args:
        worker: The worker performing the task.
        src_dir: The directory to push.
        dest_dir: The destination directory on the device. Note that when
                  pushing a directory, dest_dir will be the parent directory,
                  not the destination path.
        config: The build configuration for the tests being pushed.
        device: The device to push to.
        use_sync: True if `adb push --sync` is supported.
    """
    worker.status = f'Pushing {config} tests to {device}.'
    logger().info('%s: mkdir %s', device.name, dest_dir)
    device.shell_nocheck(['mkdir', dest_dir])
    logger().info(
        '%s: push%s %s %s', device.name, ' --sync' if use_sync else '',
        src_dir, dest_dir)
    device.push(src_dir, dest_dir, sync=use_sync)
    if sys.platform == 'win32':
        device.shell(['chmod', '-R', '777', dest_dir])


def finish_workqueue_with_ui(workqueue: WorkQueue) -> None:
    console = ndk.ansi.get_console()
    ui = ndk.ui.get_work_queue_ui(console, workqueue)
    with ndk.ansi.disable_terminal_echo(sys.stdin):
        with console.cursor_hide_context():
            ui.draw()
            while not workqueue.finished():
                workqueue.get_result()
                ui.draw()
            ui.clear()


def push_tests_to_devices(
        workqueue: WorkQueue, test_dir: str,
        groups_for_config: Mapping[BuildConfiguration,
                                   Iterable[DeviceShardingGroup]],
        use_sync: bool) -> None:
    dest_dir = DEVICE_TEST_BASE_DIR
    for config, groups in groups_for_config.items():
        src_dir = os.path.join(test_dir, str(config))
        for group in groups:
            for device in group.devices:
                workqueue.add_task(
                    push_tests_to_device, src_dir, dest_dir, config, device,
                    use_sync)

    finish_workqueue_with_ui(workqueue)
    print('Finished pushing tests')


def run_test(worker: Worker, test: TestRun) -> TestResult:
    device = worker.data[0]
    worker.status = f'Running {test.name}'
    return test.run(device)


def print_test_stats(
        test_groups: Mapping[BuildConfiguration, Iterable[TestCase]]) -> None:
    test_stats: Dict[BuildConfiguration, Dict[str, List[TestCase]]] = {}
    for config, tests in test_groups.items():
        test_stats[config] = {}
        for test in tests:
            if test.build_system not in test_stats[config]:
                test_stats[config][test.build_system] = []
            test_stats[config][test.build_system].append(test)

    for config, build_system_groups in test_stats.items():
        print(f'Config {config}:')
        for build_system, tests in build_system_groups.items():
            print(f'\t{build_system}: {len(tests)} tests')


def verify_have_all_requested_devices(fleet: DeviceFleet) -> bool:
    missing_configs = fleet.get_missing()
    if missing_configs:
        logger().warning(
            'Missing device configurations: %s', ', '.join(missing_configs))
        return False
    return True


def find_configs_with_no_device(
        groups_for_config: Mapping[BuildConfiguration,
                                   Iterable[DeviceShardingGroup]]
) -> List[BuildConfiguration]:
    return [c for c, gs in groups_for_config.items() if not gs]


def match_configs_to_device_groups(
        fleet: DeviceFleet, configs: Iterable[BuildConfiguration]
) -> Dict[BuildConfiguration, List[DeviceShardingGroup]]:
    groups_for_config: Dict[BuildConfiguration, List[DeviceShardingGroup]] = {
        config: []
        for config in configs
    }
    for config in configs:
        for group in fleet.get_unique_device_groups():
            # All devices in the group are identical.
            device = group.devices[0]
            if not device.can_run_build_config(config):
                continue
            groups_for_config[config].append(group)

    return groups_for_config


def pair_test_runs(
        test_groups: Mapping[BuildConfiguration, Iterable[TestCase]],
        groups_for_config: Mapping[BuildConfiguration,
                                   Iterable[DeviceShardingGroup]]
) -> List[TestRun]:
    """Creates a TestRun object for each device/test case pairing."""
    test_runs = []
    for config, test_cases in test_groups.items():
        if not test_cases:
            continue

        for group in groups_for_config[config]:
            test_runs.extend([TestRun(tc, group) for tc in test_cases])
    return test_runs


def wait_for_results(report: Report, workqueue: ShardingWorkQueue,
                     printer: Printer) -> None:
    console = ndk.ansi.get_console()
    ui = ndk.test.ui.get_test_progress_ui(console, workqueue)
    with ndk.ansi.disable_terminal_echo(sys.stdin):
        with console.cursor_hide_context():
            while not workqueue.finished():
                results = workqueue.get_results()
                verbose = logger().isEnabledFor(logging.INFO)
                if verbose or any(r.failed() for r in results):
                    ui.clear()
                for result in results:
                    suite = result.test.build_system
                    report.add_result(suite, result)
                    if verbose or result.failed():
                        printer.print_result(result)
                ui.draw()
            ui.clear()


def flake_filter(result: TestResult) -> bool:
    if isinstance(result, UnexpectedSuccess):
        # There are no flaky successes.
        return False

    assert isinstance(result, Failure)

    # adb might return no text at all under high load.
    if 'Could not find exit status in shell output.' in result.message:
        return True

    # These libc++ tests expect to complete in a specific amount of time,
    # and commonly fail under high load.
    name = result.test.name
    if 'libc++.libcxx/thread' in name or 'libc++.std/thread' in name:
        return True

    return False


def restart_flaky_tests(report: Report, workqueue: ShardingWorkQueue) -> None:
    """Finds and restarts any failing flaky tests."""
    rerun_tests = report.remove_all_failing_flaky(flake_filter)
    if rerun_tests:
        cooldown = 10
        logger().warning(
            'Found %d flaky failures. Sleeping for %d seconds to let '
            'devices recover.', len(rerun_tests), cooldown)
        time.sleep(cooldown)

    for flaky_report in rerun_tests:
        logger().warning('Flaky test failure: %s', flaky_report.result)
        group = flaky_report.result.test.device_group
        workqueue.add_task(group, run_test, flaky_report.result.test)


def get_config_dict(config: str, abis: Iterable[Abi]) -> Dict[str, Any]:
    with open(config) as test_config_file:
        test_config = json.load(test_config_file)
    if abis is not None:
        test_config['abis'] = abis
    return test_config


def str_to_bool(s: str) -> bool:
    if s == 'true':
        return True
    elif s == 'false':
        return False
    raise ValueError(s)


def parse_args() -> argparse.Namespace:
    doc = ('https://android.googlesource.com/platform/ndk/+/master/'
           'docs/Testing.md')
    parser = argparse.ArgumentParser(
        epilog='See {} for more information.'.format(doc))

    config_options = parser.add_argument_group('Test Configuration Options')
    config_options.add_argument(
        '--filter', help='Only run tests that match the given pattern.')
    config_options.add_argument(
        '--abi', action='append', choices=ndk.abis.ALL_ABIS,
        help='Test only the given APIs.')

    # The type ignore is needed because realpath is an overloaded function, and
    # mypy is bad at those (it doesn't satisfy Callable[[str], AnyStr]).
    config_options.add_argument(
        '--config',
        type=os.path.realpath,  # type: ignore
        default='qa_config.json',
        help='Path to the config file describing the test run.')

    build_options = parser.add_argument_group('Build Options')
    build_options.add_argument(
        '--build-report',
        type=os.path.realpath,  # type: ignore
        help='Write the build report to the given path.')

    build_exclusive_group = build_options.add_mutually_exclusive_group()
    build_exclusive_group.add_argument(
        '--rebuild', action='store_true',
        help='Build the tests before running.')
    build_exclusive_group.add_argument(
        '--build-only', action='store_true',
        help='Builds the tests and exits.')
    build_options.add_argument(
        '--clean', action='store_true',
        help='Remove the out directory before building.')

    run_options = parser.add_argument_group('Test Run Options')
    run_options.add_argument(
        '--clean-device', action='store_true',
        help='Clear the device directories before syncing.')
    run_options.add_argument(
        '--require-all-devices', action='store_true',
        help='Abort if any devices specified by the config are not available.')

    display_options = parser.add_argument_group('Display Options')
    display_options.add_argument(
        '--show-all', action='store_true',
        help='Show all test results, not just failures.')
    display_options.add_argument(
        '--show-test-stats', action='store_true',
        help='Print number of tests found for each configuration.')
    display_options.add_argument(
        '-v', '--verbose', action='count', default=0,
        help='Increase log level. Defaults to logging.WARNING.')

    parser.add_argument(
        '--ndk',
        type=os.path.realpath,  # type: ignore
        default=ndk.paths.get_install_path(),
        help='NDK to validate. Defaults to ../out/android-ndk-$RELEASE.')
    parser.add_argument(
        '--test-src',
        type=os.path.realpath,  # type: ignore
        help='Path to test source directory. Defaults to ./tests.')

    parser.add_argument(
        'test_dir',
        metavar='TEST_DIR',
        type=os.path.realpath,  # type: ignore
        nargs='?',
        default=ndk.paths.path_in_out('tests'),
        help='Directory containing built tests.')

    return parser.parse_args()


class Results:
    def __init__(self) -> None:
        self.success: Optional[bool] = None
        self.failure_message: Optional[str] = None
        self.times: Dict[str, datetime.timedelta] = collections.OrderedDict()

    def passed(self) -> None:
        if self.success is not None:
            raise ValueError
        self.success = True

    def failed(self, message: str = None) -> None:
        if self.success is not None:
            raise ValueError
        self.success = False
        self.failure_message = message

    def add_timing_report(self, label: str, timer: Timer) -> None:
        if label in self.times:
            raise ValueError
        assert timer.duration is not None
        self.times[label] = timer.duration


def run_tests(args: argparse.Namespace) -> Results:
    results = Results()

    if not os.path.exists(args.test_dir):
        if args.rebuild or args.build_only:
            os.makedirs(args.test_dir)
        else:
            sys.exit('Test output directory does not exist: {}'.format(
                args.test_dir))

    test_config = get_config_dict(args.config, args.abi)

    printer = StdoutPrinter(show_all=args.show_all)

    if args.test_src is None:
        args.test_src = os.path.realpath('tests')
        if not os.path.exists(args.test_src):
            sys.exit('Test source directory does not exist: {}'.format(
                args.test_src))

    if args.build_only or args.rebuild:
        build_timer = Timer()
        with build_timer:
            report = build_tests(
                args.test_src, args.ndk, args.test_dir, args.clean, printer,
                test_config, args.filter)

        results.add_timing_report('Build', build_timer)

        if report.num_tests == 0:
            results.failed('Found no tests for filter {}.'.format(args.filter))
            return results

        printer.print_summary(report)
        if not report.successful:
            results.failed()
            return results

    if args.build_only:
        results.passed()
        return results

    test_dist_dir = os.path.join(args.test_dir, 'dist')
    test_filter = TestFilter.from_string(args.filter)
    # dict of {BuildConfiguration: [Test]}
    config_filter = ConfigFilter(test_config)
    test_discovery_timer = Timer()
    with test_discovery_timer:
        test_groups = enumerate_tests(
            test_dist_dir, args.test_src, test_filter, config_filter)
    results.add_timing_report('Test discovery', test_discovery_timer)

    if sum([len(tests) for tests in test_groups.values()]) == 0:
        # As long as we *built* some tests, not having anything to run isn't a
        # failure.
        if args.rebuild:
            results.passed()
        else:
            results.failed('Found no tests in {} for filter {}.'.format(
                test_dist_dir, args.filter))
        return results

    if args.show_test_stats:
        print_test_stats(test_groups)

    # For finding devices, we have a list of devices we want to run on in our
    # config file. If we did away with this list, we could instead run every
    # test on every compatible device, but in the event of multiple similar
    # devices, that's a lot of duplication. The list keeps us from running
    # tests on android-24 and android-25, which don't have meaningful
    # differences.
    #
    # The list also makes sure we don't miss any devices that we expect to run
    # on.
    #
    # The other thing we need to verify is that each test we find is run at
    # least once.
    #
    # Get the list of all devices. Prune this by the requested device
    # configuration. For each requested configuration that was not found, print
    # a warning. Then compare that list of devices against all our tests and
    # make sure each test is claimed by at least one device. For each
    # configuration that is unclaimed, print a warning.
    workqueue = WorkQueue()
    try:
        device_discovery_timer = Timer()
        with device_discovery_timer:
            fleet = find_devices(test_config['devices'], workqueue)
        results.add_timing_report('Device discovery', device_discovery_timer)

        have_all_devices = verify_have_all_requested_devices(fleet)
        if args.require_all_devices and not have_all_devices:
            results.failed('Some requested devices were not available.')
            return results

        groups_for_config = match_configs_to_device_groups(
            fleet, test_groups.keys())
        for config in find_configs_with_no_device(groups_for_config):
            logger().warning('No device found for %s.', config)

        report = Report()
        clean_device_timer = Timer()
        if args.clean_device:
            with clean_device_timer:
                clear_test_directories(workqueue, fleet)
            results.add_timing_report('Clean device', clean_device_timer)

        can_use_sync = adb_has_feature('push_sync')
        push_timer = Timer()
        with push_timer:
            push_tests_to_devices(
                workqueue, test_dist_dir, groups_for_config, can_use_sync)
        results.add_timing_report('Push', push_timer)
    finally:
        workqueue.terminate()
        workqueue.join()

    shard_queue = ShardingWorkQueue(fleet.get_unique_device_groups(), 4)
    try:
        # Need an input queue per device group, a single result queue, and a
        # pool of threads per device.

        # Shuffle the test runs to distribute the load more evenly. These are
        # ordered by (build config, device, test), so most of the tests running
        # at any given point in time are all running on the same device.
        test_runs = pair_test_runs(test_groups, groups_for_config)
        random.shuffle(test_runs)
        test_run_timer = Timer()
        with test_run_timer:
            for test_run in test_runs:
                shard_queue.add_task(test_run.device_group, run_test, test_run)

            wait_for_results(report, shard_queue, printer)
            restart_flaky_tests(report, shard_queue)
            wait_for_results(report, shard_queue, printer)
        results.add_timing_report('Run', test_run_timer)

        printer.print_summary(report)
    finally:
        shard_queue.terminate()
        shard_queue.join()

    if report.successful:
        results.passed()
    else:
        results.failed()

    return results


def main() -> None:
    args = parse_args()

    log_levels = [logging.WARNING, logging.INFO, logging.DEBUG]
    verbosity = min(args.verbose, len(log_levels) - 1)
    log_level = log_levels[verbosity]
    logging.basicConfig(level=log_level)

    python_packages = os.path.join(args.ndk, 'python-packages')
    site.addsitedir(python_packages)

    total_timer = Timer()
    with total_timer:
        results = run_tests(args)

    if results.success is None:
        raise RuntimeError(
            'run_tests returned without indicating success or failure.')

    good = results.success
    print('Finished {}'.format('successfully' if good else 'unsuccessfully'))

    for timer, duration in results.times.items():
        print('{}: {}'.format(timer, duration))
    print('Total: {}'.format(total_timer.duration))

    subject = 'NDK Testing {}!'.format('Passed' if good else 'Failed')
    body = 'Testing finished in {}'.format(total_timer.duration)
    ndk.notify.toast(subject, body)

    sys.exit(not good)


if __name__ == '__main__':
    main()
