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
"""Configuration objects for describing test runs."""
from __future__ import annotations

from dataclasses import dataclass
import enum
from typing import Iterable, List, Optional

from ndk.abis import Abi, LP32_ABIS, LP64_ABIS


@enum.unique
class CMakeToolchainFile(enum.Enum):
    Legacy = 'legacy'
    Default = 'new'


class TestOptions:
    """Configuration for how tests should be run."""

    def __init__(self,
                 src_dir: str,
                 ndk_path: str,
                 out_dir: str,
                 test_filter: str = None,
                 clean: bool = True,
                 build_report: str = None) -> None:
        """Initializes a TestOptions object.

        Args:
            src_dir: Path to the tests.
            ndk_path: Path to the NDK to use to build the tests.
            out_dir: Test output directory.
            test_filter: Test filter string.
            clean: True if the out directory should be cleaned before building.
            build_report: Path to write a build report to, if any.
        """
        self.src_dir = src_dir
        self.ndk_path = ndk_path
        self.out_dir = out_dir
        self.test_filter = test_filter
        self.clean = clean
        self.build_report = build_report


class TestSpec:
    """Configuration for which tests should be run."""

    def __init__(self, abis: Iterable[Abi], suites: Iterable[str]) -> None:
        self.abis = abis
        self.suites = suites


@dataclass(frozen=True)
class BuildConfiguration:
    """A configuration for a single test build.

    A TestSpec describes which BuildConfigurations should be included in a test
    run.
    """

    abi: Abi
    api: Optional[int]
    toolchain_file: CMakeToolchainFile

    def with_api(self, api: int) -> BuildConfiguration:
        """Creates a copy of this BuildConfiguration with a new API level.

        Args:
            api: The API level used by the new BuildConfiguration.

        Returns:
            A copy of this BuildConfiguration with the new API level.
        """
        return BuildConfiguration(abi=self.abi,
                                  api=api,
                                  toolchain_file=self.toolchain_file)

    def __str__(self) -> str:
        return '-'.join([
            self.abi,
            str(self.api),
            self.toolchain_file.value,
        ])

    @property
    def is_lp32(self) -> bool:
        return self.abi in LP32_ABIS

    @property
    def is_lp64(self) -> bool:
        return self.abi in LP64_ABIS

    @staticmethod
    def from_string(config_string: str) -> BuildConfiguration:
        """Converts a string into a BuildConfiguration.

        Args:
            config_string: The string format of the test spec.

        Returns:
            TestSpec matching the given string.

        Raises:
            ValueError: The given string could not be matched to a TestSpec.
        """
        abi, _, rest = config_string.partition('-')
        if abi == 'armeabi' and rest.startswith('v7a-'):
            abi += '-v7a'
            _, _, rest = rest.partition('-')
        elif abi == 'arm64' and rest.startswith('v8a-'):
            abi += '-v8a'
            _, _, rest = rest.partition('-')

        api_str, toolchain_file_str = rest.split('-')
        api = int(api_str)
        toolchain_file = CMakeToolchainFile(toolchain_file_str)

        return BuildConfiguration(Abi(abi), api, toolchain_file)

    def get_extra_ndk_build_flags(self) -> List[str]:
        extra_flags = []
        extra_flags.append('V=1')
        return extra_flags

    def get_extra_cmake_flags(self) -> List[str]:
        extra_flags = []
        extra_flags.append('-DCMAKE_VERBOSE_MAKEFILE=ON')
        return extra_flags
