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
from __future__ import print_function

import os
import sys
from typing import Optional, TextIO

import ndk.termcolor
from ndk.test.report import Report
from ndk.test.result import TestResult


def format_stats_str(report: Report, use_color: bool) -> str:
    pass_label = ndk.termcolor.maybe_color('PASS', 'green', use_color)
    fail_label = ndk.termcolor.maybe_color('FAIL', 'red', use_color)
    skip_label = ndk.termcolor.maybe_color('SKIP', 'yellow', use_color)
    return '{pl} {p}/{t} {fl} {f}/{t} {sl} {s}/{t}'.format(
        pl=pass_label, p=report.num_passed,
        fl=fail_label, f=report.num_failed,
        sl=skip_label, s=report.num_skipped,
        t=report.num_tests)


class Printer:
    def print_result(self, result: TestResult) -> None:
        raise NotImplementedError

    def print_summary(self, report: Report) -> None:
        raise NotImplementedError


class FilePrinter(Printer):
    def __init__(self,
                 to_file: TextIO,
                 use_color: Optional[bool] = None,
                 show_all: bool = False,
                 quiet: bool = False) -> None:
        self.file = to_file
        self.show_all = show_all
        self.quiet = quiet

        if use_color is None:
            self.use_color = to_file.isatty() and os.name != 'nt'
        else:
            self.use_color = use_color

    def print_result(self, result: TestResult) -> None:
        if self.quiet and not result.failed():
            return
        print(result.to_string(colored=self.use_color), file=self.file)

    def print_summary(self, report: Report) -> None:
        print(file=self.file)
        formatted = format_stats_str(report, self.use_color)
        print(formatted, file=self.file)
        for suite, suite_report in report.by_suite().items():
            stats_str = format_stats_str(suite_report, self.use_color)
            print(file=self.file)
            print('{}: {}'.format(suite, stats_str), file=self.file)
            for test_report in suite_report.reports:
                if self.show_all or test_report.result.failed():
                    print(test_report.result.to_string(colored=self.use_color),
                          file=self.file)


class StdoutPrinter(FilePrinter):
    def __init__(self,
                 use_color: Optional[bool] = None,
                 show_all: bool = False,
                 quiet: bool = False) -> None:
        super().__init__(sys.stdout, use_color, show_all, quiet)
