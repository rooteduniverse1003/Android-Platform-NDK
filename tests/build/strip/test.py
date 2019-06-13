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
"""Check for strip --strip-unneeded use."""
import os
import subprocess
import sys


def run_test(ndk_path, abi, api, linker, build_flags):
    """Checks ndk-build V=1 output for --strip-unneeded flag."""
    if build_flags is None:
        build_flags = []

    ndk_build = os.path.join(ndk_path, 'ndk-build')
    if sys.platform == 'win32':
        ndk_build += '.cmd'
    project_path = 'project'

    ndk_args = build_flags + [
        f'APP_ABI={abi}',
        f'APP_LD={linker.value}',
        f'APP_PLATFORM=android-{api}',
        'V=1',
    ]
    proc = subprocess.Popen([ndk_build, '-C', project_path] + ndk_args,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            encoding='utf-8')
    out, _ = proc.communicate()
    if proc.returncode != 0:
        return proc.returncode == 0, out

    out_words = out.split(' ')
    return '--strip-unneeded' in out_words, out
