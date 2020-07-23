#
# Copyright (C) 2020 The Android Open Source Project
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
"""APIs for dealing with cmake scripts."""

import os
from pathlib import Path
import pprint
import shlex
import shutil
import subprocess
from typing import Dict, List, Optional

from ndk.hosts import Host, get_default_host
import ndk.paths
import ndk.toolchains

SYSTEM_NAME_MAP = {
    Host.Darwin: 'Darwin',
    Host.Linux: 'Linux',
    Host.Windows64: 'Windows'
}

HOST_TRIPLE_MAP = {
    Host.Darwin: 'x86_64-apple-darwin',
    Host.Linux: 'x86_64-linux-gnu',
    Host.Windows64: 'x86_64-w64-mingw32',
}


class CMakeBuilder:
    """Builder for an cmake project."""

    toolchain: ndk.toolchains.Toolchain

    def __init__(self,
                 src_path: Path,
                 build_dir: Path,
                 host: Host,
                 additional_flags: List[str] = None,
                 additional_env: Optional[Dict[str, str]] = None) -> None:
        """Initializes an autoconf builder.

        Args:
            src_path: Path to the cmake project.
            build_dir: Directory to use for building. If the directory exists,
            it will be deleted and recreated to ensure the build is correct.
            host: Host to be used for the --host argument (the
                cross-compilation target).
            additional_flags: Additional flags to pass to the compiler.
            additional_env: Additional environment to set, used during
                configure, build, and install.
        """
        self.src_path = src_path
        self.build_directory = build_dir
        self.host = host
        self.additional_flags = additional_flags
        self.additional_env = additional_env

        self.working_directory = self.build_directory / 'build'
        self.install_directory = self.build_directory / 'install'

        self.toolchain = ndk.toolchains.ClangToolchain(self.host)

    @property
    def flags(self) -> List[str]:
        """Returns default cflags for the target."""
        # TODO: Are these the flags we want? These are what we've used
        # historically.
        flags = [
            '-Os',
            '-fomit-frame-pointer',
            '-s',
        ]
        if self.additional_flags:
            flags.extend(self.additional_flags)
        return flags

    def _run(self, cmd: List[str]) -> None:
        """Runs and logs execution of a subprocess."""
        subproc_env = dict(os.environ)
        if self.additional_env:
            subproc_env.update(self.additional_env)

        pp_cmd = shlex.join(cmd)
        if subproc_env != os.environ:
            pp_env = pprint.pformat(self.additional_env, indent=4)
            print('Running: {} with env:\n{}'.format(pp_cmd, pp_env))
        else:
            print('Running: {}'.format(pp_cmd))

        subprocess.check_call(cmd, env=subproc_env, cwd=self.working_directory)

    @property
    def _cmake(self) -> Path:
        return (ndk.paths.ANDROID_DIR / 'prebuilts' / 'cmake' /
                (get_default_host().value + '-x86') / 'bin' / 'cmake')

    @property
    def _ninja(self) -> Path:
        return (ndk.paths.ANDROID_DIR / 'prebuilts' / 'ninja' /
                (get_default_host().value + '-x86') / 'ninja')

    @property
    def cmake_defines(self) -> Dict[str, str]:
        """CMake defines."""
        flags = self.toolchain.flags + self.flags
        cflags = ' '.join(flags)
        cxxflags = ' '.join(flags + ['-stdlib=libc++'])
        defines: Dict[str, str] = {
            'CMAKE_C_COMPILER': str(self.toolchain.cc),
            'CMAKE_C_COMPILER_TARGET': HOST_TRIPLE_MAP[self.host],
            'CMAKE_CXX_COMPILER': str(self.toolchain.cxx),
            'CMAKE_CXX_COMPILER_TARGET': HOST_TRIPLE_MAP[self.host],
            'CMAKE_AR': str(self.toolchain.ar),
            'CMAKE_RANLIB': str(self.toolchain.ranlib),
            'CMAKE_NM': str(self.toolchain.nm),
            'CMAKE_STRIP': str(self.toolchain.strip),
            'CMAKE_LINKER': str(self.toolchain.ld),
            'CMAKE_ASM_FLAGS': cflags,
            'CMAKE_C_FLAGS': cflags,
            'CMAKE_CXX_FLAGS': cxxflags,
            'CMAKE_BUILD_TYPE': 'Release',
            'CMAKE_INSTALL_PREFIX': str(self.install_directory),
            'CMAKE_MAKE_PROGRAM': str(self._ninja),
            'CMAKE_SYSTEM_NAME': SYSTEM_NAME_MAP[self.host],
            'CMAKE_SYSTEM_PROCESSOR': 'x86_64',
            'CMAKE_FIND_ROOT_PATH_MODE_INCLUDE': 'ONLY',
            'CMAKE_FIND_ROOT_PATH_MODE_LIBRARY': 'ONLY',
            'CMAKE_FIND_ROOT_PATH_MODE_PACKAGE': 'ONLY',
            'CMAKE_FIND_ROOT_PATH_MODE_PROGRAM': 'NEVER',
        }
        if self.host.is_windows:
            defines['CMAKE_RC'] = str(self.toolchain.rescomp)
        return defines

    def clean(self) -> None:
        """Cleans output directory.

        If necessary, existing output directory will be removed. After
        removal, the inner directories (working directory, install directory,
        and toolchain directory) will be created.
        """
        if self.build_directory.exists():
            shutil.rmtree(self.build_directory)

        self.working_directory.mkdir(parents=True)
        self.install_directory.mkdir(parents=True)

    def configure(self, additional_defines: Dict[str, str]) -> None:
        """Invokes cmake configure."""
        cmake_cmd = [str(self._cmake), '-GNinja']
        defines = self.cmake_defines
        defines.update(additional_defines)
        cmake_cmd.extend(f'-D{key}={val}' for key, val in defines.items())
        cmake_cmd.append(str(self.src_path))

        self._run(cmake_cmd)

    def make(self) -> None:
        """Builds the project."""
        self._run([str(self._ninja)])

    def install(self) -> None:
        """Installs the project."""
        self._run([str(self._ninja), 'install'])

    def build(self,
              additional_defines: Optional[Dict[str, str]] = None) -> None:
        """Configures and builds an cmake project.

        Args:
            configure_args: List of arguments to be passed to configure. Does
                not need to include --prefix, --build, or --host. Those are set
                up automatically.
        """
        self.clean()
        self.configure(
            {} if additional_defines is None else additional_defines)
        self.make()
        self.install()
