#!/usr/bin/env python
#
# Copyright (C) 2019 The Android Open Source Project
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
"""System tests for ndk-stack.py"""

from __future__ import print_function

from io import StringIO
import os.path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, '../..')
ndk_stack = __import__('ndk-stack')

import ndk.hosts  # pylint:disable=wrong-import-position
import ndk.toolchains  # pylint:disable=wrong-import-position


class SystemTests(unittest.TestCase):
    """Complete system test of ndk-stack.py script."""

    def setUp(self):
        default_host = ndk.hosts.get_default_host()
        clang_toolchain = ndk.toolchains.ClangToolchain(default_host)

        # First try and use the normal functions, and if they fail, then
        # use hard-coded paths from the development locations.
        ndk_paths = ndk_stack.get_ndk_paths()
        self.readelf = ndk_stack.find_readelf(*ndk_paths)
        if not self.readelf:
            self.readelf = clang_toolchain.clang_tool('llvm-readelf')
        self.assertTrue(self.readelf)
        self.assertTrue(os.path.exists(self.readelf))

        try:
            self.llvm_symbolizer = ndk_stack.find_llvm_symbolizer(*ndk_paths)
        except OSError:
            self.llvm_symbolizer = str(
                clang_toolchain.clang_tool('llvm-symbolizer'))
        self.assertTrue(self.llvm_symbolizer)
        self.assertTrue(os.path.exists(self.llvm_symbolizer))

    @patch.object(ndk_stack, 'find_llvm_symbolizer')
    @patch.object(ndk_stack, 'find_readelf')
    def system_test(self, backtrace_file, expected_file, mock_readelf, mock_llvm_symbolizer):
        mock_readelf.return_value = self.readelf
        mock_llvm_symbolizer.return_value = self.llvm_symbolizer

        symbol_dir = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 'files')
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            ndk_stack.main([
                '-s', symbol_dir, '-i',
                os.path.join(symbol_dir, backtrace_file)
            ])

        # Read the expected output.
        file_name = os.path.join(symbol_dir, expected_file)
        with open(mode='r', file=file_name) as exp_file:
            expected = exp_file.read()
        expected = expected.replace('SYMBOL_DIR', symbol_dir)
        self.maxDiff = None
        self.assertEqual(expected, mock_stdout.getvalue())

    def test_all_stacks(self):
        self.system_test('backtrace.txt', 'expected.txt')

    def test_multiple_crashes(self):
        self.system_test('multiple.txt', 'expected_multiple.txt')

    def test_hwasan(self):
        self.system_test('hwasan.txt', 'expected_hwasan.txt')


if __name__ == '__main__':
    unittest.main()
