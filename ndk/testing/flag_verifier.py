#
# Copyright (C) 2020 The Android Open Source Project
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
"""Tools for verifying the presence or absence of flags in builds."""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
from typing import Optional

from ndk.hosts import Host
import ndk.paths
from ndk.test.spec import BuildConfiguration, CMakeToolchainFile


class FlagVerifierResult:
    """Base class for the result of FlagVerifier checks."""

    def __init__(self, error_message: Optional[str]) -> None:
        self.error_message = error_message

    def failed(self) -> bool:
        """Returns True if verification failed."""
        raise NotImplementedError

    def make_test_result_tuple(
        self, message_prefix: str | None = None
    ) -> tuple[bool, Optional[str]]:
        """Creates a test result tuple in the format expect by run_test."""
        if message_prefix is None:
            message = self.error_message
        else:
            message = f"{message_prefix}\n{self.error_message}"
        return not self.failed(), message


class FlagVerifierSuccess(FlagVerifierResult):
    """A successful flag verification result."""

    def __init__(self) -> None:
        super().__init__(error_message=None)

    def failed(self) -> bool:
        return False


class FlagVerifierFailure(FlagVerifierResult):
    """An unsuccessful flag verification result."""

    def __init__(self, error_message: str) -> None:
        super().__init__(error_message)

    def failed(self) -> bool:
        return True


class FlagVerifier:
    """Verifies that a build receives the expected flags."""

    def __init__(
        self, project: Path, ndk_path: Path, config: BuildConfiguration
    ) -> None:
        self.project = project
        self.ndk_path = ndk_path
        self.abi = config.abi
        self.api = config.api
        if config.toolchain_file is CMakeToolchainFile.Legacy:
            self.toolchain_mode = "ON"
        else:
            self.toolchain_mode = "OFF"
        self.expected_flags: list[str] = []
        self.not_expected_flags: list[str] = []

    def with_api(self, api: int) -> FlagVerifier:
        self.api = api
        return self

    def expect_flag(self, flag: str) -> None:
        """Verify that the given string is present in the build output.

        Args:
            flag: The literal string to search for in the output. Will be
                  matched against whole whitespace-separated words in the
                  output.
        """
        if flag in self.not_expected_flags:
            raise ValueError(f"Flag {flag} both expected and not expected")
        self.expected_flags.append(flag)

    def expect_not_flag(self, flag: str) -> None:
        """Verify that the given string is not present in the build output.

        Args:
            flag: The literal string to search for in the output. Will be
                  matched against whole whitespace-separated words in the
                  output.
        """
        if flag in self.expected_flags:
            raise ValueError(f"Flag {flag} both expected and not expected")
        self.not_expected_flags.append(flag)

    def _check_build(self, cmd: list[str]) -> FlagVerifierResult:
        result = subprocess.run(
            cmd,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
        )
        if result.returncode != 0:
            return FlagVerifierFailure(result.stdout)

        words = result.stdout.split(" ")
        missing_flags: list[str] = []
        wrong_flags: list[str] = []
        for expected in self.expected_flags:
            if expected not in words:
                missing_flags.append(expected)
        for not_expected in self.not_expected_flags:
            if not_expected in words:
                wrong_flags.append(not_expected)
        if missing_flags:
            return FlagVerifierFailure(
                "Expected flags were not present in the build output: "
                + ", ".join(missing_flags)
                + f"\n{result.stdout}"
            )
        if wrong_flags:
            return FlagVerifierFailure(
                "Unexpected flags were present in the build output: "
                + ", ".join(wrong_flags)
                + f"\n{result.stdout}"
            )
        return FlagVerifierSuccess()

    def verify(self) -> FlagVerifierResult:
        """Verifies that both ndk-build and CMake behave as specified.

        Returns:
            A FlagVerifierResult object describing the verification result.
        """
        result = self.verify_cmake()
        if result.failed():
            return result
        return self.verify_ndk_build()

    def verify_ndk_build(self) -> FlagVerifierResult:
        """Verifies that ndk-build behaves as specified.

        Returns:
            A FlagVerifierResult object describing the verification result.
        """
        ndk_build = self.ndk_path / "ndk-build"
        if Host.current() == Host.Windows64:
            ndk_build = ndk_build.with_suffix(".cmd")
        return self._check_build(
            [
                str(ndk_build),
                "-C",
                str(self.project),
                "-B",
                "V=1",
                f"APP_ABI={self.abi}",
                f"APP_PLATFORM=android-{self.api}",
            ]
        )

    def verify_cmake(
        self, cmake_flags: Optional[list[str]] = None
    ) -> FlagVerifierResult:
        """Verifies that CMake behaves as specified.

        Returns:
            A FlagVerifierResult object describing the verification result.
        """
        if cmake_flags is None:
            cmake_flags = []

        host = Host.current()
        if host == Host.Windows64:
            tag = "windows-x86"
        else:
            tag = f"{host.value}-x86"
        cmake = ndk.paths.ANDROID_DIR / f"prebuilts/cmake/{tag}/bin/cmake"
        ninja = ndk.paths.ANDROID_DIR / f"prebuilts/ninja/{tag}/ninja"
        if host == Host.Windows64:
            cmake = cmake.with_suffix(".exe")
            ninja = ninja.with_suffix(".exe")
        # PythonBuildTest ensures that we're cd'd into the test out directory.
        build_dir = Path("build")
        if build_dir.exists():
            shutil.rmtree(build_dir)
        build_dir.mkdir(parents=True)
        toolchain_file = self.ndk_path / "build/cmake/android.toolchain.cmake"
        cmd = [
            str(cmake),
            "-S",
            str(self.project),
            "-B",
            str(build_dir),
            f"-DCMAKE_TOOLCHAIN_FILE={toolchain_file}",
            f"-DANDROID_ABI={self.abi}",
            f"-DANDROID_PLATFORM=android-{self.api}",
            f"-DANDROID_USE_LEGACY_TOOLCHAIN_FILE={self.toolchain_mode}",
            "-GNinja",
            f"-DCMAKE_MAKE_PROGRAM={ninja}",
        ] + cmake_flags
        result = subprocess.run(
            cmd,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
        )
        if result.returncode != 0:
            return FlagVerifierFailure(result.stdout)
        return self._check_build([str(ninja), "-C", str(build_dir), "-v"])
