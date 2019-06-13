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
"""Constants and helper functions for NDK hosts."""
from __future__ import absolute_import

import enum
import os
import sys


@enum.unique
class Host(enum.Enum):
    """Enumeration of supported hosts."""

    Darwin = 'darwin'
    Linux = 'linux'
    # TODO: Just Windows now that we only have the one.
    Windows64 = 'windows64'

    # TODO: Remove.
    @property
    def is_windows(self) -> bool:
        """Returns True if the given host is Windows."""
        return self == Host.Windows64


ALL_HOSTS = list(Host)


def get_host_tag(ndk_path: str) -> str:
    """Returns the host tag used for testing on the current host.

    For Windows, the result depends on the NDK in question since a 64-bit host
    may be used to test the 32-bit NDK.
    """
    if sys.platform.startswith('linux'):
        return 'linux-x86_64'
    elif sys.platform == 'darwin':
        return 'darwin-x86_64'
    elif sys.platform == 'win32':
        host_tag = 'windows-x86_64'
        test_path = os.path.join(ndk_path, 'prebuilt', host_tag)
        if not os.path.exists(test_path):
            host_tag = 'windows'
        return host_tag
    raise ValueError('Unknown host: {}'.format(sys.platform))


def host_to_tag(host: Host) -> str:
    """Returns the host tag used for NDK prebuilt directories.

    >>> host_to_tag(Host.Darwin)
    'darwin-x86_64'
    >>> host_to_tag(Host.Linux)
    'linux-x86_64'
    >>> host_to_tag(Host.Windows64)
    'windows-x86_64'
    """
    # TODO: Clean up since this can all be + -x86_64 once we rename the windows
    # value.
    if not host.is_windows:
        return host.value + '-x86_64'
    elif host == Host.Windows64:
        return 'windows-x86_64'
    raise NotImplementedError


def get_default_host() -> Host:
    """Returns the Host matching the current machine."""
    if sys.platform in ('linux', 'linux2'):
        return Host.Linux
    elif sys.platform == 'darwin':
        return Host.Darwin
    elif sys.platform == 'win32':
        return Host.Windows64
    else:
        raise RuntimeError(f'Unsupported host: {sys.platform}')
