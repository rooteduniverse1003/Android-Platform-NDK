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
"""APIs for enumerating and building NDK tests."""
from __future__ import absolute_import

import json
import logging
import multiprocessing
import os
import pickle
import random
import shutil
import sys
import traceback

import ndk.abis
import ndk.test.filters
import ndk.test.report
import ndk.test.scanner
import ndk.test.spec
import ndk.test.suites
import ndk.test.ui
import ndk.workqueue


def logger():
    """Returns the module logger."""
    return logging.getLogger(__name__)


def test_spec_from_config(test_config):
    """Returns a TestSpec based on the test config file."""
    abis = test_config.get('abis', ndk.abis.ALL_ABIS)
    suites = test_config.get('suites', ndk.test.suites.ALL_SUITES)

    return ndk.test.spec.TestSpec(abis, suites)


def write_build_report(build_report, results):
    with open(build_report, 'w') as build_report_file:
        pickle.dump(results, build_report_file)


def scan_test_suite(suite_dir, test_scanner):
    tests = []
    for dentry in os.listdir(suite_dir):
        path = os.path.join(suite_dir, dentry)
        if os.path.isdir(path):
            test_name = os.path.basename(path)
            tests.extend(test_scanner.find_tests(path, test_name))
    return tests


def _fixup_expected_failure(result, config, bug):
    if isinstance(result, ndk.test.result.Failure):
        return ndk.test.result.ExpectedFailure(result.test, config, bug)
    elif isinstance(result, ndk.test.result.Success):
        return ndk.test.result.UnexpectedSuccess(result.test, config, bug)
    else:  # Skipped, UnexpectedSuccess, or ExpectedFailure.
        return result


def _fixup_negative_test(result):
    if isinstance(result, ndk.test.result.Failure):
        return ndk.test.result.Success(result.test)
    elif isinstance(result, ndk.test.result.Success):
        return ndk.test.result.Failure(
            result.test, 'negative test case succeeded')
    else:  # Skipped, UnexpectedSuccess, or ExpectedFailure.
        return result


def _run_test(worker, suite, test, obj_dir, dist_dir, test_filters):
    """Runs a given test according to the given filters.

    Args:
        worker: The worker that invoked this task.
        suite: Name of the test suite the test belongs to.
        test: The test to be run.
        obj_dir: Out directory for intermediate build artifacts.
        dist_dir: Out directory for build artifacts needed for running.
        test_filters: Filters to apply when running tests.

    Returns: Tuple of (suite, TestResult, [Test]). The [Test] element is a list
             of additional tests to be run.
    """
    worker.status = 'Building {}'.format(test)

    config = test.check_unsupported()
    if config is not None:
        message = 'test unsupported for {}'.format(config)
        return suite, ndk.test.result.Skipped(test, message), []

    try:
        result, additional_tests = test.run(obj_dir, dist_dir, test_filters)
        if test.is_negative_test():
            result = _fixup_negative_test(result)
        config, bug = test.check_broken()
        if config is not None:
            # We need to check change each pass/fail to either an
            # ExpectedFailure or an UnexpectedSuccess as necessary.
            result = _fixup_expected_failure(result, config, bug)
    except Exception:  # pylint: disable=broad-except
        result = ndk.test.result.Failure(test, traceback.format_exc())
        additional_tests = []
    return suite, result, additional_tests


class TestBuilder(object):
    def __init__(self, test_spec, test_options, printer):
        self.printer = printer
        self.tests = {}
        self.build_dirs = {}

        self.test_options = test_options

        self.obj_dir = os.path.join(self.test_options.out_dir, 'obj')
        self.dist_dir = os.path.join(self.test_options.out_dir, 'dist')

        self.find_tests(test_spec)

    def find_tests(self, test_spec):
        scanner = ndk.test.scanner.BuildTestScanner(self.test_options.ndk_path)
        nodist_scanner = ndk.test.scanner.BuildTestScanner(
            self.test_options.ndk_path, dist=False)
        libcxx_scanner = ndk.test.scanner.LibcxxTestScanner(
            self.test_options.ndk_path)
        for abi in test_spec.abis:
            build_api_level = None  # Always use the default.

            scanner.add_build_configuration(abi, build_api_level)
            nodist_scanner.add_build_configuration(abi, build_api_level)
            libcxx_scanner.add_build_configuration(abi, build_api_level)

        if 'build' in test_spec.suites:
            test_src = os.path.join(self.test_options.src_dir, 'build')
            self.add_suite('build', test_src, nodist_scanner)
        if 'device' in test_spec.suites:
            test_src = os.path.join(self.test_options.src_dir, 'device')
            self.add_suite('device', test_src, scanner)
        if 'libc++' in test_spec.suites:
            test_src = os.path.join(self.test_options.src_dir, 'libc++')
            self.add_suite('libc++', test_src, libcxx_scanner)

    @classmethod
    def from_config_file(cls, config_path, test_options, printer):
        with open(config_path) as test_config_file:
            test_config = json.load(test_config_file)
        spec = test_spec_from_config(test_config)
        return cls(spec, test_options, printer)

    def add_suite(self, name, path, test_scanner):
        if name in self.tests:
            raise KeyError('suite {} already exists'.format(name))
        new_tests = scan_test_suite(path, test_scanner)
        self.check_no_overlapping_build_dirs(name, new_tests)
        self.tests[name] = new_tests

    def check_no_overlapping_build_dirs(self, suite, new_tests):
        for test in new_tests:
            build_dir = test.get_build_dir('')
            if build_dir in self.build_dirs:
                dup_suite, dup_test = self.build_dirs[build_dir]
                raise RuntimeError(
                    'Found duplicate build directory:\n{} {}\n{} {}'.format(
                        dup_suite, dup_test, suite, test))
            self.build_dirs[build_dir] = (suite, test)

    def make_out_dirs(self):
        if not os.path.exists(self.obj_dir):
            os.makedirs(self.obj_dir)
        if not os.path.exists(self.dist_dir):
            os.makedirs(self.dist_dir)

    def clean_out_dir(self):
        if os.path.exists(self.test_options.out_dir):
            shutil.rmtree(self.test_options.out_dir)

    def build(self):
        if self.test_options.clean:
            self.clean_out_dir()
        self.make_out_dirs()

        test_filters = ndk.test.filters.TestFilter.from_string(
            self.test_options.test_filter)
        result = self.do_build(test_filters)
        if self.test_options.build_report:
            write_build_report(self.test_options.build_report, result)
        return result

    def do_build(self, test_filters):
        workqueue = ndk.test.builder.LoadRestrictingWorkQueue()
        try:
            for suite, tests in self.tests.items():
                # Each test configuration was expanded when each test was
                # discovered, so the current order has all the largest tests
                # right next to each other. Spread them out to try to avoid
                # having too many heavy builds happening simultaneously.
                random.shuffle(tests)
                for test in tests:
                    if not test_filters.filter(test.name):
                        continue

                    if test.name == 'libc++':
                        workqueue.add_load_restricted_task(
                            _run_test, suite, test, self.obj_dir,
                            self.dist_dir, test_filters)
                    else:
                        workqueue.add_task(
                            _run_test, suite, test, self.obj_dir,
                            self.dist_dir, test_filters)

            report = ndk.test.report.Report()
            self.wait_for_results(report, workqueue, test_filters)

            return report
        finally:
            workqueue.terminate()
            workqueue.join()

    def wait_for_results(self, report, workqueue, test_filters):
        console = ndk.ansi.get_console()
        ui = ndk.test.ui.get_test_build_progress_ui(console, workqueue)
        with ndk.ansi.disable_terminal_echo(sys.stdin):
            with console.cursor_hide_context():
                while not workqueue.finished():
                    suite, result, additional_tests = workqueue.get_result()
                    # Filtered test. Skip them entirely to avoid polluting
                    # --show-all results.
                    if result is None:
                        assert not additional_tests
                        ui.draw()
                        continue

                    assert result.passed() or not additional_tests
                    for test in additional_tests:
                        workqueue.add_task(
                            _run_test, suite, test, self.obj_dir,
                            self.dist_dir, test_filters)
                    if logger().isEnabledFor(logging.INFO):
                        ui.clear()
                        self.printer.print_result(result)
                    elif result.failed():
                        ui.clear()
                        self.printer.print_result(result)
                    report.add_result(suite, result)
                    ui.draw()
                ui.clear()


class LoadRestrictingWorkQueue(object):
    """Specialized work queue for building tests.

    Building the libc++ tests is very demanding and we should not be running
    more than one libc++ build at a time. The LoadRestrictingWorkQueue has a
    normal task queue as well as a task queue served by only one worker.
    """

    def __init__(self, num_workers=multiprocessing.cpu_count()):
        self.manager = multiprocessing.Manager()
        self.result_queue = self.manager.Queue()

        assert num_workers >= 2

        self.main_task_queue = self.manager.Queue()
        self.restricted_task_queue = self.manager.Queue()

        self.main_work_queue = ndk.workqueue.WorkQueue(
            num_workers - 1, task_queue=self.main_task_queue,
            result_queue=self.result_queue)

        self.restricted_work_queue = ndk.workqueue.WorkQueue(
            1, task_queue=self.restricted_task_queue,
            result_queue=self.result_queue)

        self.num_tasks = 0

    def add_task(self, func, *args, **kwargs):
        self.main_task_queue.put(ndk.workqueue.Task(func, args, kwargs))
        self.num_tasks += 1

    def add_load_restricted_task(self, func, *args, **kwargs):
        self.restricted_task_queue.put(ndk.workqueue.Task(func, args, kwargs))
        self.num_tasks += 1

    def get_result(self):
        """Gets a result from the queue, blocking until one is available."""
        result = self.result_queue.get()
        if isinstance(result, ndk.workqueue.TaskError):
            raise result
        self.num_tasks -= 1
        return result

    def terminate(self):
        self.main_work_queue.terminate()
        self.restricted_work_queue.terminate()

    def join(self):
        self.main_work_queue.join()
        self.restricted_work_queue.join()

    def finished(self):
        """Returns True if all tasks have completed execution."""
        return self.num_tasks == 0
