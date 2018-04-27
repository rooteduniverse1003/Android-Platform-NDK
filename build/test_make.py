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
"""Tests for build.make."""
from __future__ import print_function

import unittest

import build.make


class MakeVarsTest(unittest.TestCase):
    def test_generate_make_vars(self):
        self.assertEqual(
            'foo := bar',
            build.make.generate_make_vars({'foo': 'bar'}))
        self.assertEqual(
            build.make.NEWLINE.join(['foo := bar', 'baz := qux']),
            build.make.generate_make_vars({'foo': 'bar', 'baz': 'qux'}))
