#!/usr/bin/env python
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
"""NDK packaging APIs."""
from __future__ import absolute_import

import os
import shutil
import subprocess
import tempfile
from typing import Iterable, List, Optional, Set, Tuple

import ndk.abis
from ndk.hosts import Host, host_to_tag


PACKAGE_VARIANTS = (
    'abi',
    'arch',
    'host',
    'toolchain',
    'triple',
)


def expand_path(package: str, host: Host) -> str:
    """Expands package definition tuple into a package name.

    >>> expand_path('llvm-{host}', Host.Linux)
    'llvm-linux-x86_64'

    >>> expand_path('platforms', Host.Linux)
    'platforms'
    """
    host_tag = host_to_tag(host)
    return package.format(host=host_tag)


def package_varies_by(install_path: str, variant: str) -> bool:
    """Determines if a package varies by a given input.

    >>> package_varies_by('foo-{host}', 'host')
    True

    >>> package_varies_by('foo', 'host')
    False

    >>> package_varies_by('foo-{arch}', 'host')
    False
    """

    if variant not in PACKAGE_VARIANTS:
        raise ValueError

    variant_replacement_str = '{' + variant + '}'
    return variant_replacement_str in install_path


def expand_package(package: str, install_path: str,
                   host: Host) -> Tuple[str, str]:
    """Returns a tuple of `(package, install_path)`."""
    package_template = package
    for variant in PACKAGE_VARIANTS:
        if package_varies_by(install_path, variant):
            package_template += '-{' + variant + '}'

    expanded_packages = expand_path(package_template, host)
    expanded_installs = expand_path(install_path, host)
    return expanded_packages, expanded_installs


def extract_zip(package_path: str, install_path: str) -> None:
    """Extracts the contents of a zipfile to a directory.

    This behaves similar to the following shell commands (using tar instead of
    zip because `unzip` doesn't support `--strip-components`):

        mkdir -p $install_path
        tar xf $package_path -C $install_path --strip-components=1

    That is, the first directory in the package is stripped and the contents
    are placed in the install path.

    Args:
        package_path: Path to the zip file to extract.
        install_path: Directory in which to extract zip contents.

    Raises:
        RuntimeError: The zip file was not in the allowed format. i.e. the zip
                      had more than one top level directory or was empty.
    """
    package_name = os.path.basename(package_path)
    extract_dir = tempfile.mkdtemp()
    try:
        subprocess.check_call(
            ['unzip', '-q', package_path, '-d', extract_dir])
        dirs = os.listdir(extract_dir)
        if len(dirs) > 1:
            msg = 'Package has more than one root directory: ' + package_name
            raise RuntimeError(msg)
        if not dirs:
            raise RuntimeError('Package was empty: ' + package_name)
        parent_dir = os.path.dirname(install_path)
        if not os.path.exists(parent_dir):
            os.makedirs(parent_dir)
        shutil.move(os.path.join(extract_dir, dirs[0]), install_path)
    finally:
        shutil.rmtree(extract_dir)
