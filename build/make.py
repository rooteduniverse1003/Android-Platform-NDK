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
"""APIs for interfacing with make."""
from __future__ import absolute_import
from __future__ import print_function

import argparse
import json
import os


NEWLINE = '%NEWLINE%'


def generate_make_vars(abi_vars):
    lines = []
    for var, value in abi_vars.items():
        lines.append('{} := {}'.format(var, value))
    # https://www.gnu.org/software/make/manual/html_node/Shell-Function.html
    # Make's $(shell) function replaces real newlines with spaces. Use
    # something we can easily identify that's unlikely to appear in a variable
    # so we can replace it in make.
    return NEWLINE.join(lines)


def metadata_to_make(conversion_func):
    parser = argparse.ArgumentParser()

    parser.add_argument(
        'metadata_file', metavar='METADATA_FILE', type=os.path.abspath,
        help='Path to the metadata JSON file.')

    args = parser.parse_args()
    with open(args.metadata_file) as metadata_file:
        metadata = json.load(metadata_file)

    metadata_vars = conversion_func(metadata)
    print(generate_make_vars(metadata_vars))
