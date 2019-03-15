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
"""APIs for accessing toolchains."""
from pathlib import Path
from typing import List

from ndk.hosts import Host, get_default_host
import ndk.paths


CLANG_VERSION = 'clang-r349610b'


HOST_TRIPLE_MAP = {
    Host.Darwin: 'x86_64-apple-darwin',
    Host.Linux: 'x86_64-linux-gnu',
    Host.Windows: 'i686-w64-mingw32',
    Host.Windows64: 'x86_64-w64-mingw32',
}


class Toolchain:
    """A compiler toolchain.

    Describes the directories, executables, and default flags needed to use a
    toolchain.
    """

    def __init__(self, target: Host, host: Host = get_default_host()) -> None:
        if host.is_windows:
            raise NotImplementedError
        self.host = host
        self.target = target

    @property
    def ar(self) -> Path:
        """The path to the archiver."""
        raise NotImplementedError

    @property
    def asm(self) -> Path:
        """The path to the assembler."""
        raise NotImplementedError

    @property
    def bin_paths(self) -> List[Path]:
        """The path to the toolchain binary directories for use with PATH."""
        raise NotImplementedError

    @property
    def cc(self) -> Path:
        """The path to the C compiler."""
        raise NotImplementedError

    @property
    def cxx(self) -> Path:
        """The path to the C++ compiler."""
        raise NotImplementedError

    @property
    def flags(self) -> List[str]:
        """The default flags to be used with the compiler."""
        raise NotImplementedError

    @property
    def ld(self) -> Path:
        """The path to the linker."""
        raise NotImplementedError

    @property
    def nm(self) -> Path:
        """The path to nm."""
        raise NotImplementedError

    @property
    def path(self) -> Path:
        """The path to the top level toolchain directory."""
        raise NotImplementedError

    @property
    def ranlib(self) -> Path:
        """The path to ranlib."""
        raise NotImplementedError

    @property
    def rescomp(self) -> Path:
        """The path to the resource compiler."""
        raise NotImplementedError

    @property
    def strip(self) -> Path:
        """The path to strip."""
        raise NotImplementedError

    @property
    def strings(self) -> Path:
        """The path to strings."""
        raise NotImplementedError


class GccToolchain(Toolchain):
    """A GCC compiler toolchain."""

    def gcc_tool(self, tool_name: str) -> Path:
        """Returns the path to the GCC tool targeting the given host."""
        return self.path / 'bin' / f'{self.triple}-{tool_name}'

    @property
    def ar(self) -> Path:
        """The path to the archiver."""
        return self.gcc_tool('ar')

    @property
    def asm(self) -> Path:
        """The path to the assembler."""
        return self.gcc_tool('as')

    @property
    def bin_paths(self) -> List[Path]:
        """The path to the toolchain binary directories for use with PATH."""
        return [self.path / 'bin']

    @property
    def cc(self) -> Path:
        """The path to the C compiler."""
        return self.gcc_tool('gcc')

    @property
    def cxx(self) -> Path:
        """The path to the C++ compiler."""
        return self.gcc_tool('g++')

    @property
    def flags(self) -> List[str]:
        """The default flags to be used with the compiler."""
        return ['-m32'] if self.target == Host.Windows else []

    @property
    def ld(self) -> Path:
        """The path to the linker."""
        return self.gcc_tool('ld')

    @property
    def lib_dirs(self) -> List[Path]:
        """Returns the paths to the GCC library directories for the given host.

        The GCC library directory contains libgcc and other compiler runtime
        libraries. These may be split across multiple directories.
        """
        lib_dirs = [self.path / {
            Host.Darwin: 'lib/gcc/i686-apple-darwin11/4.2.1',
            Host.Linux: 'lib/gcc/x86_64-linux/4.8',
            Host.Windows: 'lib/gcc/x86_64-w64-mingw32/4.8.3/32',
            Host.Windows64: 'lib/gcc/x86_64-w64-mingw32/4.8.3',
        }[self.target]]
        if self.target != Host.Darwin:
            libdir = 'lib32' if self.target == Host.Windows else 'lib64'
            lib_dirs.append(self.path / self.triple / libdir)
        return lib_dirs

    @property
    def nm(self) -> Path:
        """The path to nm."""
        return self.gcc_tool('nm')

    @property
    def path(self) -> Path:
        """Returns the path to the top level toolchain directory."""
        if self.target == Host.Darwin:
            return (ndk.paths.ANDROID_DIR /
                    'prebuilts/gcc/darwin-x86/host/i686-apple-darwin-4.2.1')
        elif self.target == Host.Linux:
            return (ndk.paths.ANDROID_DIR /
                    'prebuilts/gcc/linux-x86/host/x86_64-linux-glibc2.15-4.8')
        else:
            return (ndk.paths.ANDROID_DIR /
                    'prebuilts/gcc/linux-x86/host/x86_64-w64-mingw32-4.8')

    @property
    def ranlib(self) -> Path:
        """The path to ranlib."""
        return self.gcc_tool('ranlib')

    @property
    def rescomp(self) -> Path:
        """The path to the resource compiler."""
        if not self.target.is_windows:
            raise NotImplementedError
        return self.gcc_tool('windres')

    @property
    def strip(self) -> Path:
        """The path to strip."""
        return self.gcc_tool('strip')

    @property
    def strings(self) -> Path:
        """The path to strings."""
        return self.gcc_tool('strings')

    @property
    def sysroot(self) -> Path:
        """The path to the GCC sysroot."""
        if self.target == Host.Linux:
            return self.path / 'sysroot'
        return self.path / self.triple

    @property
    def triple(self) -> str:
        """Returns the GCC triple for the host toolchain."""
        return {
            Host.Darwin: 'x86_64-apple-darwin11',
            Host.Linux: 'x86_64-linux',
            Host.Windows: 'x86_64-w64-mingw32',
            Host.Windows64: 'x86_64-w64-mingw32',
        }[self.target]


class ClangToolchain(Toolchain):
    """A Clang compiler toolchain."""

    def __init__(self, target: Host, host: Host = get_default_host()) -> None:
        super().__init__(target, host=host)
        self.gcc_toolchain = GccToolchain(target, host=host)

    @staticmethod
    def path_for_host(host: Host) -> Path:
        """Returns the path to the Clang directory for the given host."""
        host_tag = {
            Host.Darwin: 'darwin-x86',
            Host.Linux: 'linux-x86',
            Host.Windows: 'windows-x86_32',
            Host.Windows64: 'windows-x86',
        }[host]
        return (ndk.paths.ANDROID_DIR / 'prebuilts/clang/host' / host_tag /
                CLANG_VERSION)

    @property
    def path(self) -> Path:
        """Returns the path to the top level toolchain directory."""
        return self.path_for_host(self.host)

    def clang_tool(self, tool_name: str) -> Path:
        """Returns the path to the Clang tool for the build host."""
        return self.path / 'bin' / tool_name

    @property
    def ar(self) -> Path:
        """The path to the archiver."""
        return self.gcc_toolchain.ar

    @property
    def asm(self) -> Path:
        """The path to the assembler."""
        return self.gcc_toolchain.asm

    @property
    def bin_paths(self) -> List[Path]:
        """The path to the toolchain binary directories for use with PATH."""
        return self.gcc_toolchain.bin_paths + [self.path / 'bin']

    @property
    def cc(self) -> Path:
        return self.clang_tool('clang')

    @property
    def cxx(self) -> Path:
        return self.clang_tool('clang++')

    @property
    def flags(self) -> List[str]:
        host_triple = HOST_TRIPLE_MAP[self.target]
        toolchain_bin = (
            self.gcc_toolchain.path / self.gcc_toolchain.triple / 'bin')
        flags = [
            f'--target={host_triple}',
            f'--sysroot={self.gcc_toolchain.sysroot}',
            f'-B{toolchain_bin}',
        ]

        for lib_dir in self.gcc_toolchain.lib_dirs:
            # Both -L and -B because Clang only searches for CRT
            # objects in -B directories.
            flags.extend([
                f'-L{lib_dir}',
                f'-B{lib_dir}',
            ])

        return flags

    @property
    def ld(self) -> Path:
        """The path to the linker."""
        return self.gcc_toolchain.ld

    @property
    def nm(self) -> Path:
        """The path to nm."""
        return self.gcc_toolchain.nm

    @property
    def ranlib(self) -> Path:
        """The path to ranlib."""
        return self.gcc_toolchain.ranlib

    @property
    def rescomp(self) -> Path:
        """The path to the resource compiler."""
        return self.gcc_toolchain.rescomp

    @property
    def strip(self) -> Path:
        """The path to strip."""
        return self.gcc_toolchain.strip

    @property
    def strings(self) -> Path:
        """The path to strings."""
        return self.gcc_toolchain.strings
