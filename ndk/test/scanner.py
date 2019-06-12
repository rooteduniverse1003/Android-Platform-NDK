#
# Copyright (C) 2018 The Android Open Source Project
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
from __future__ import absolute_import

import os
from typing import List, Optional, Set

from ndk.abis import Abi
import ndk.paths
from ndk.test.spec import BuildConfiguration
from ndk.test.types import (
    CMakeBuildTest,
    LibcxxTest,
    NdkBuildTest,
    PythonBuildTest,
    ShellBuildTest,
    Test,
)


class TestScanner:
    """Creates a Test objects for a given test directory.

    A test scanner is used to turn a test directory into a list of Tests for
    any of the test types found in the directory.
    """
    def find_tests(self, path: str, name: str) -> List[Test]:
        """Searches a directory for tests.

        Args:
            path: Path to the test directory.
            name: Name of the test.

        Returns: List of Tests, possibly empty.
        """
        raise NotImplementedError


class BuildTestScanner(TestScanner):
    def __init__(self, ndk_path: str, dist: bool = True) -> None:
        self.ndk_path = ndk_path
        self.dist = dist
        self.build_configurations: Set[BuildConfiguration] = set()

    def add_build_configuration(self, abi: Abi, api: Optional[int]) -> None:
        self.build_configurations.add(BuildConfiguration(abi, api))

    def find_tests(self, path: str, name: str) -> List[Test]:
        # If we have a build.sh, that takes precedence over the Android.mk.
        build_sh_path = os.path.join(path, 'build.sh')
        if os.path.exists(build_sh_path):
            return self.make_build_sh_tests(path, name)

        # Same for test.py
        build_sh_path = os.path.join(path, 'test.py')
        if os.path.exists(build_sh_path):
            return self.make_test_py_tests(path, name)

        # But we can have both ndk-build and cmake tests in the same directory.
        tests: List[Test] = []
        android_mk_path = os.path.join(path, 'jni/Android.mk')
        if os.path.exists(android_mk_path):
            tests.extend(self.make_ndk_build_tests(path, name))

        cmake_lists_path = os.path.join(path, 'CMakeLists.txt')
        if os.path.exists(cmake_lists_path):
            tests.extend(self.make_cmake_tests(path, name))
        return tests

    def make_build_sh_tests(self, path: str, name: str) -> List[Test]:
        return [
            ShellBuildTest(name, path, config, self.ndk_path)
            for config in self.build_configurations
        ]

    def make_test_py_tests(self, path: str, name: str) -> List[Test]:
        return [
            PythonBuildTest(name, path, config, self.ndk_path)
            for config in self.build_configurations
        ]

    def make_ndk_build_tests(self, path: str, name: str) -> List[Test]:
        return [
            NdkBuildTest(name, path, config, self.ndk_path, self.dist)
            for config in self.build_configurations
        ]

    def make_cmake_tests(self, path: str, name: str) -> List[Test]:
        return [
            CMakeBuildTest(name, path, config, self.ndk_path, self.dist)
            for config in self.build_configurations
        ]


class LibcxxTestScanner(TestScanner):
    ALL_TESTS: List[str] = []
    LIBCXX_SRC = ndk.paths.ANDROID_DIR / 'external/libcxx'

    def __init__(self, ndk_path: str) -> None:
        self.ndk_path = ndk_path
        self.build_configurations: Set[BuildConfiguration] = set()
        LibcxxTestScanner.find_all_libcxx_tests()

    def add_build_configuration(self, abi: Abi, api: Optional[int]) -> None:
        self.build_configurations.add(BuildConfiguration(abi, api))

    def find_tests(self, path: str, name: str) -> List[Test]:
        return [
            LibcxxTest('libc++', path, config, self.ndk_path)
            for config in self.build_configurations
        ]

    @classmethod
    def find_all_libcxx_tests(cls) -> None:
        # If we instantiate multiple LibcxxTestScanners, we still only need to
        # initialize this once. We only create these in the main thread, so
        # there's no risk of race.
        if cls.ALL_TESTS:
            return

        test_base_dir = os.path.join(cls.LIBCXX_SRC, 'test')

        for root, _dirs, files in os.walk(test_base_dir):
            for test_file in files:
                if test_file.endswith('.cpp'):
                    test_path = ndk.paths.to_posix_path(os.path.relpath(
                        os.path.join(root, test_file), test_base_dir))
                    cls.ALL_TESTS.append(test_path)
