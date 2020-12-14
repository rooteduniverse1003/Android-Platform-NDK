#
# Copyright (C) 2016 The Android Open Source Project
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
"""Check for strip --strip-debug use."""
from pathlib import Path
from typing import Optional, Tuple

from ndk.abis import Abi
from ndk.testing.flag_verifier import FlagVerifier


def run_test(ndk_path: str, abi: Abi, api: int) -> Tuple[bool, Optional[str]]:
    """Checks ndk-build V=1 output for --strip-debug flag."""
    verifier = FlagVerifier(Path('project'), Path(ndk_path), abi, api)
    verifier.expect_flag('--strip-debug')
    verifier.expect_not_flag('--strip-unneeded')
    return verifier.verify_ndk_build().make_test_result_tuple()
