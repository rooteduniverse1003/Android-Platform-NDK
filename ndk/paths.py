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
"""Helper functions for NDK build and test paths."""
from __future__ import absolute_import

import contextlib
import os
from pathlib import Path
import shutil
import sys
from typing import Generator, Optional

import ndk.abis
import ndk.config
import ndk.hosts


ANDROID_DIR = Path(__file__).resolve().parents[2]
NDK_DIR = ANDROID_DIR / 'ndk'


def android_path(*args: str) -> str:
    """Returns the absolute path rooted within the top level source tree."""
    return str(ANDROID_DIR.joinpath(*args))


def ndk_path(*args: str) -> str:
    """Returns the absolute path rooted within the NDK source tree."""
    return android_path('ndk', *args)


def sysroot_path(toolchain: ndk.abis.Toolchain) -> str:
    """Returns the path to the prebuilt sysroot for the given toolchain."""
    arch = ndk.abis.toolchain_to_arch(toolchain)
    # Only ARM has more than one ABI, and they both have the same minimum
    # platform level.
    abi = ndk.abis.arch_to_abis(arch)[0]
    version = ndk.abis.min_api_for_abi(abi)

    prebuilt_ndk = 'prebuilts/ndk/current'
    sysroot_subpath = 'platforms/android-{}/arch-{}'.format(version, arch)
    return android_path(prebuilt_ndk, sysroot_subpath)


def toolchain_path(*args: str) -> str:
    """Returns a path within the toolchain subdirectory."""
    return android_path('toolchain', *args)


def _get_dir_from_env(default: str, env_var: str) -> str:
    """Returns the path to a directory specified by the environment.

    If the environment variable is not set, the default will be used. The
    directory is created if it does not exist.

    Args:
        default: The path used if the environment variable is not set.
        env_var: The environment variable that contains the path, if any.

    Returns:
        The absolute path to the directory.
    """
    path = os.path.realpath(os.getenv(env_var, default))
    if not os.path.isdir(path):
        os.makedirs(path)
    return path


def get_out_dir() -> str:
    """Returns the out directory."""
    return _get_dir_from_env(android_path('out'), 'OUT_DIR')


def get_dist_dir(out_dir) -> str:
    """Returns the distribution directory.

    The contents of the distribution directory are archived on the build
    servers. Suitable for build logs and final artifacts.
    """
    return _get_dir_from_env(os.path.join(out_dir, 'dist'), 'DIST_DIR')


def path_in_out(dirname: str, out_dir: Optional[str] = None) -> str:
    """Returns a path within the out directory."

    Args:
        dirname: Name of the directory.
        out_dir: Optional base out directory. Inferred from $OUT_DIR if not
                 supplied. If None and $OUT_DIR is not set, will use ../out
                 relative to the NDK git project.

    Returns:
        Absolute path within the out directory.
    """
    if out_dir is None:
        out_dir = get_out_dir()
    return os.path.join(out_dir, dirname)


def get_install_path(out_dir: Optional[str] = None,
                     host: Optional[ndk.hosts.Host] = None) -> str:
    """Returns the built NDK install path.

    Note that the path returned might not actually contain the NDK. The NDK may
    not actually be present if:

    * The NDK hasn't been built yet.
    * The name of the release has changed since the NDK was built.
    * out_dir is not consistent with the build.

    Args:
        out_dir: Optional base out directory. Inferred from $OUT_DIR if not
                 supplied.
        host: Returns the install path for th given host.

    Returns:
        Directory that the built NDK should be installed to.
    """
    if host is None:
        host = ndk.hosts.get_default_host()
    release_name = f'android-ndk-{ndk.config.release}'
    return path_in_out(os.path.join(host.value, release_name), out_dir)


@contextlib.contextmanager
def temp_dir_in_out(dirname: str, out_dir: Optional[str] = None) -> Generator:
    """Creates a well named temporary directory within the out directory.

    If the directory exists on context entry, RuntimeError will be raised. The
    directory is removed on context exit.

    Args:
        dirname: Name of the temporary directory.
        out_dir: Optional base out directory. Inferred from $OUT_DIR if not
                 supplied. If None and $OUT_DIR is not set, will use ../out
                 relative to the NDK git project.

    Returns:
        Absolute path to the created directory.

    Raises:
        RuntimeError: The requested directory already exists.
    """
    path = path_in_out(dirname, out_dir)
    if os.path.exists(path):
        raise RuntimeError('Directory already exists: ' + path)

    os.makedirs(path)
    try:
        abspath = os.path.abspath(path)
        yield abspath
    finally:
        shutil.rmtree(abspath)


def to_posix_path(path: str) -> str:
    """Replaces backslashes with forward slashes on Windows."""
    if sys.platform == 'win32':
        return path.replace('\\', '/')
    else:
        return path
