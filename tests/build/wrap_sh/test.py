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
"""Check for correct wrap.sh from ndk-build.
"""
import os
import subprocess
import sys
import textwrap
from typing import Tuple

from ndk.abis import Abi


def run_test(ndk_path: str, abi: Abi, api: int) -> Tuple[bool, str]:
    """Checks that the proper wrap.sh scripts were installed."""
    ndk_build = os.path.join(ndk_path, 'ndk-build')
    if sys.platform == 'win32':
        ndk_build += '.cmd'
    project_path = 'project'
    ndk_args = [
        f'APP_ABI={abi}',
        f'APP_PLATFORM=android-{api}',
    ]
    proc = subprocess.Popen([ndk_build, '-C', project_path] + ndk_args,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            encoding='utf-8')
    out, _ = proc.communicate()
    if proc.returncode != 0:
        return proc.returncode == 0, out

    wrap_sh = os.path.join(project_path, 'libs', abi, 'wrap.sh')
    if not os.path.exists(wrap_sh):
        return False, f'{wrap_sh} does not exist'

    with open(wrap_sh) as wrap_sh_file:
        contents = wrap_sh_file.read().strip()
    if contents != abi:
        return False, textwrap.dedent(f"""\
            wrap.sh file had wrong contents:
            Expected: {abi}
            Actual: {contents}""")

    return True, ''
