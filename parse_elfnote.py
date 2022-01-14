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

#
# Dump the contents of the .note.android.ident section, a NOTE section
# embedded into Android binaries. See here:
#  - master: ndk/sources/crt/crtbrand.S
#  - master: bionic/libc/arch-common/bionic/crtbrand.S
#  - NDK before r14: development/ndk/platforms/common/src/crtbrand.c
#
# Note sections can also be dumped with `readelf -n`.
#

from __future__ import division, print_function
import argparse
import logging
import struct
import subprocess
import sys


SEC_NAME = ".note.android.ident"
NDK_RESERVED_SIZE = 64


def logger():
    """Returns the module logger."""
    return logging.getLogger(__name__)


def round_up_to_nearest(val, step):
    """Round an integer, val, to the next multiple of a positive integer,
    step."""
    return (val + (step - 1)) // step * step


class StructParser:
    def __init__(self, buf):
        self.buf = buf
        self.pos = 0

    @property
    def remaining(self):
        return len(self.buf) - self.pos

    @property
    def empty(self):
        return self.remaining == 0

    def read(self, read_len):
        buf = self.buf[self.pos : read_len + self.pos]
        self.pos += read_len
        return buf

    def read_struct(self, fmt, kind):
        fmt = struct.Struct(fmt)
        if self.remaining < fmt.size:
            sys.exit("error: {} was truncated".format(kind))
        return fmt.unpack(self.read(fmt.size))


def iterate_notes(sec_data):
    sec_data = StructParser(sec_data)
    while not sec_data.empty:
        (namesz, descsz, kind) = sec_data.read_struct("<III", "note header")
        (name, desc) = sec_data.read_struct(
            "{}s{}s".format(
                round_up_to_nearest(namesz, 4), round_up_to_nearest(descsz, 4)
            ),
            "note body",
        )
        name = name[:namesz]
        if len(name) > 0:
            if name[-1:] == b"\0":
                name = name[:-1]
            else:
                logger().warning("note name %s isn't NUL-terminated", name)
        yield name, kind, desc[:descsz]


def dump_android_ident_note(note):
    note = StructParser(note)
    (android_api,) = note.read_struct("<I", "note descriptor")
    print("ABI_ANDROID_API: {}".format(android_api))
    if note.empty:
        return
    # Binaries generated by NDK r14 and later have these extra fields. Platform
    # binaries and binaries generated by older NDKs don't.
    ndk_version, ndk_build_number = note.read_struct(
        "{sz}s{sz}s".format(sz=NDK_RESERVED_SIZE), "note descriptor"
    )
    ndk_version = ndk_version.decode("utf-8")
    ndk_build_number = ndk_build_number.decode("utf-8")
    print("ABI_NDK_VERSION: {}".format(ndk_version.rstrip("\0")))
    print("ABI_NDK_BUILD_NUMBER: {}".format(ndk_build_number.rstrip("\0")))
    if not note.empty:
        logger().warning("excess data at end of descriptor")


# Get the offset to a section from the output of readelf
def get_section_pos(sec_name, file_path):
    cmd = ["readelf", "--sections", "-W", file_path]
    output = subprocess.check_output(cmd)
    lines = output.decode("utf-8").splitlines()
    for line in lines:
        logger().debug('Checking line for "%s": %s', sec_name, line)
        # Looking for a line like the following (all whitespace of unknown
        # width).
        #
        #   [ 8] .note.android.ident NOTE 00000000 0000ec 000098 00 A 0 0 4
        #
        # The only column that might have internal whitespace is the first one.
        # Since we don't care about it, remove the head of the string until the
        # closing bracket, then split.
        if "]" not in line:
            continue
        line = line[line.index("]") + 1 :]

        sections = line.split()
        if len(sections) < 5 or sec_name != sections[0]:
            continue
        off = int(sections[3], 16)
        size = int(sections[4], 16)
        return (off, size)
    sys.exit("error: failed to find section: {}".format(sec_name))


def parse_args():
    """Parses command line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("file_path", help="path of the ELF file with embedded ABI tags")
    parser.add_argument(
        "-v",
        "--verbose",
        dest="verbosity",
        action="count",
        default=0,
        help="Increase logging verbosity.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    if args.verbosity == 1:
        logging.basicConfig(level=logging.INFO)
    elif args.verbosity >= 2:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig()

    file_path = args.file_path

    with open(file_path, "rb") as obj_file:
        (sec_off, sec_size) = get_section_pos(SEC_NAME, file_path)

        obj_file.seek(sec_off)
        sec_data = obj_file.read(sec_size)
        if len(sec_data) != sec_size:
            sys.exit("error: could not read {} section".format(SEC_NAME))

        print("----------ABI INFO----------")
        if len(sec_data) == 0:
            logger().warning("%s section is empty", SEC_NAME)
        for (name, kind, desc) in iterate_notes(sec_data):
            if (name, kind) == (b"Android", 1):
                dump_android_ident_note(desc)
            else:
                logger().warning(
                    "unrecognized note (name %s, type %d)", repr(name), kind
                )


if __name__ == "__main__":
    main()
