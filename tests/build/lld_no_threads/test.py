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
"""Check that Windows LLD does not use threads with ndk-build.

https://github.com/android-ndk/ndk/issues/855 reports that this sometimes hangs
on Windows.
"""
import os
import subprocess
import sys


def check_ndk_build(ndk_path, abi, platform, build_flags, use_lld):
    """Checks --no-threads behavior with ndk-build.

    If use_lld is used, the test will build the ndk-build project with
    APP_LDFLAGS=-fuse-ld=lld to force the project to use lld. In this case, we
    expect to see -Wl,--no-threads passed to the linker on Windows.
    """
    ndk_build = os.path.join(ndk_path, 'ndk-build')
    is_win = sys.platform == 'win32'
    if is_win:
        ndk_build += '.cmd'
    if use_lld:
        build_flags.append('APP_LDFLAGS=-fuse-ld=lld')
    project_path = 'project'
    ndk_args = build_flags + [
        'APP_ABI=' + abi,
        'APP_PLATFORM=android-{}'.format(platform),
        'V=1',
        '-B',
    ]
    proc = subprocess.Popen([ndk_build, '-C', project_path] + ndk_args,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out, _ = proc.communicate()
    out = out.decode('utf-8')
    if proc.returncode != 0:
        return proc.returncode == 0, out

    out_words = out.split(' ')
    if is_win and use_lld:
        result = '-Wl,--no-threads' in out_words
    else:
        result = '-Wl,--no-threads' not in out_words

    return result, out


def run_test(ndk_path, abi, platform, build_flags):
    """Checks --no-threads-behavior."""
    result, out = check_ndk_build(ndk_path, abi, platform, build_flags, False)
    if not result:
        return result, out
    return check_ndk_build(ndk_path, abi, platform, build_flags, True)
