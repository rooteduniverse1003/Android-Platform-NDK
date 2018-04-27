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
"""Tests for import_abi_metadata.py."""
from __future__ import print_function

import unittest

import build.import_platforms_metadata


class ImportPlatformsMetadataTest(unittest.TestCase):
    def test_metadata_to_make_vars(self):
        make_vars = build.import_platforms_metadata.metadata_to_make_vars({
            'min': 16,
            'max': 28,
            'aliases': {
                '20': 19,
                'J': 16,
                'O': 26,
            },
        })

        self.assertDictEqual({
            'NDK_MIN_PLATFORM_LEVEL': 16,
            'NDK_MAX_PLATFORM_LEVEL': 28,
            'NDK_PLATFORM_ALIAS_20': 'android-19',
            'NDK_PLATFORM_ALIAS_J': 'android-16',
            'NDK_PLATFORM_ALIAS_O': 'android-26',
        }, make_vars)
