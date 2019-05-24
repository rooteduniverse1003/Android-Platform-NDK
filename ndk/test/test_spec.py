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
import unittest

import ndk.test.spec


class BuildConfigurationTest(unittest.TestCase):
    def test_from_string(self) -> None:
        config = ndk.test.spec.BuildConfiguration.from_string('armeabi-v7a-16')
        self.assertEqual('armeabi-v7a', config.abi)
        self.assertEqual(16, config.api)

        config = ndk.test.spec.BuildConfiguration.from_string('arm64-v8a-21')
        self.assertEqual('arm64-v8a', config.abi)
        self.assertEqual(21, config.api)

        config = ndk.test.spec.BuildConfiguration.from_string('x86-16')
        self.assertEqual('x86', config.abi)
        self.assertEqual(16, config.api)

        config = ndk.test.spec.BuildConfiguration.from_string('x86_64-21')
        self.assertEqual('x86_64', config.abi)
        self.assertEqual(21, config.api)
