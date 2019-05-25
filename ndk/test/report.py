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
"""Defines the format of test results from the test runner."""
from typing import Callable, Dict, List

from ndk.test.result import TestResult


class SingleResultReport:
    """Stores the result of a single test with its config info."""
    def __init__(self, suite: str, result: TestResult) -> None:
        self.suite = suite
        self.result = result


class Report:
    """Stores details of a test run.

    A "test run" means any number of tests run in any number of (unique)
    configurations.
    """
    def __init__(self) -> None:
        self.reports: List[SingleResultReport] = []

    def add_result(self, suite: str, result: TestResult) -> None:
        self.reports.append(SingleResultReport(suite, result))

    def by_suite(self) -> Dict[str, 'Report']:
        suite_reports: Dict[str, 'Report'] = {}
        for report in self.reports:
            if report.suite not in suite_reports:
                suite_reports[report.suite] = Report()
            suite_reports[report.suite].add_result(report.suite, report.result)
        return suite_reports

    @property
    def successful(self) -> bool:
        return self.num_failed == 0

    @property
    def num_tests(self) -> int:
        return len(self.reports)

    @property
    def num_failed(self) -> int:
        return len(self.all_failed)

    @property
    def num_passed(self) -> int:
        return len(self.all_passed)

    @property
    def num_skipped(self) -> int:
        return len(self.all_skipped)

    @property
    def all_failed(self) -> List[SingleResultReport]:
        failures: List[SingleResultReport] = []
        for report in self.reports:
            if report.result.failed():
                failures.append(report)
        return failures

    @property
    def all_passed(self) -> List[SingleResultReport]:
        passes: List[SingleResultReport] = []
        for report in self.reports:
            if report.result.passed():
                passes.append(report)
        return passes

    @property
    def all_skipped(self) -> List[SingleResultReport]:
        skips: List[SingleResultReport] = []
        for report in self.reports:
            if not report.result.passed() and not report.result.failed():
                skips.append(report)
        return skips

    def remove_all_failing_flaky(self,
                                 flake_filter: Callable[[TestResult], bool]
                                 ) -> List[SingleResultReport]:
        """Splits out the flaky tests that failed so they can be rerun.

        Any failing tests that are known flaky are removed from the list of
        reports and returned to the caller to be rerun.
        """
        new_list = []
        flaky = []
        for report in self.reports:
            if report.result.failed() and flake_filter(report.result):
                flaky.append(report)
            else:
                new_list.append(report)
        self.reports = new_list
        return flaky
