#!/usr/bin/env python
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
"""Generates Make-importable code from meta/abis.json."""
from __future__ import print_function

import make  # pylint: disable=relative-import


def metadata_to_make_vars(meta):
    default_abis = []
    deprecated_abis = []
    lp32_abis = []
    lp64_abis = []
    for abi, abi_data in meta.items():
        bitness = abi_data['bitness']
        if bitness == 32:
            lp32_abis.append(abi)
        elif bitness == 64:
            lp64_abis.append(abi)
        else:
            raise ValueError('{} bitness is unsupported value: {}'.format(
                abi, bitness))

        if abi_data['default']:
            default_abis.append(abi)

        if abi_data['deprecated']:
            deprecated_abis.append(abi)

    abi_vars = {
        'NDK_DEFAULT_ABIS': ' '.join(sorted(default_abis)),
        'NDK_DEPRECATED_ABIS': ' '.join(sorted(deprecated_abis)),
        'NDK_KNOWN_DEVICE_ABI32S': ' '.join(sorted(lp32_abis)),
        'NDK_KNOWN_DEVICE_ABI64S': ' '.join(sorted(lp64_abis)),
    }

    return abi_vars


if __name__ == '__main__':
    make.metadata_to_make(metadata_to_make_vars)
