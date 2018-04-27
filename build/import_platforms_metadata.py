#!/usr/bin/env python
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
"""Generates Make-importable code from meta/platforms.json."""
from __future__ import print_function

import make  # pylint: disable=relative-import


def metadata_to_make_vars(meta):
    min_api = meta['min']
    max_api = meta['max']

    make_vars = {
        'NDK_MIN_PLATFORM_LEVEL': min_api,
        'NDK_MAX_PLATFORM_LEVEL': max_api,
    }

    for src, dst in meta['aliases'].items():
        name = 'NDK_PLATFORM_ALIAS_{}'.format(src)
        value = 'android-{}'.format(dst)
        make_vars[name] = value

    return make_vars


if __name__ == '__main__':
    make.metadata_to_make(metadata_to_make_vars)
