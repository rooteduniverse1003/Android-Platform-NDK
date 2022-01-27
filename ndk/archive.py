#
# Copyright (C) 2022 The Android Open Source Project
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
"""Helper functions for reading and writing .zip and .tar.bz2 archives."""
import os
from pathlib import Path
import shutil
import subprocess
from typing import List


def make_bztar(base_name: Path, root_dir: Path, base_dir: Path) -> None:
    """Create a compressed tarball.

    Arguments have the same name and meaning as shutil.make_archive.

    Args:
        base_name: Base name of archive to create. ".tar.bz2" will be appended.
        root_dir: Directory that's the root of the archive.
        base_dir: Directory relative to root_dir to archive.
    """
    if not root_dir.is_dir():
        raise RuntimeError(f"Not a directory: {root_dir}")
    if not (root_dir / base_dir).is_dir():
        raise RuntimeError(f"Not a directory: {root_dir}/{base_dir}")

    if os.name == "nt":
        shutil.make_archive(
            str(base_name),
            "bztar",
            str(root_dir),
            str(base_dir),
        )
    else:
        subprocess.check_call(
            [
                "tar",
                "-j"
                if shutil.which("pbzip2") is None
                else "--use-compress-prog=pbzip2",
                "-cf",
                str(base_name.with_suffix(".tar.bz2")),
                "-C",
                str(root_dir),
                str(base_dir),
            ]
        )


def make_zip(
    base_name: Path, root_dir: Path, paths: List[str], preserve_symlinks: bool
) -> Path:
    """Creates a zip package for distribution.

    Args:
        base_name: Path (without extension) to the output archive.
        root_dir: Path to the directory from which to perform the packaging
                  (identical to tar's -C).
        paths: Paths to files and directories to package, relative to root_dir.
        preserve_symlinks: Whether to preserve or flatten symlinks. Should be
            false when creating packages for Windows, but otherwise true.
    """
    if not root_dir.is_dir():
        raise RuntimeError(f"Not a directory: {root_dir}")
    if os.name == "nt":
        raise RuntimeError("Not supported on Windows")

    cwd = os.getcwd()
    zip_file = base_name.with_suffix(".zip")

    args = ["zip", "-9qr", str(zip_file)]
    if preserve_symlinks:
        args.append("--symlinks")
    args.extend(paths)
    os.chdir(root_dir)
    try:
        subprocess.check_call(args)
        return zip_file
    finally:
        os.chdir(cwd)


def unzip(zip_file: Path, dest_dir: Path) -> None:
    """Unzip zip_file into dest_dir."""
    if not zip_file.is_file() or zip_file.suffix != ".zip":
        raise RuntimeError(f"Not a .zip file: {zip_file}")
    if not dest_dir.is_dir():
        raise RuntimeError(f"Not a directory: {dest_dir}")

    # shutil.unpack_archive uses zipfile, which unfortunately does not
    # restore permissions, including the executable bit.
    # https://bugs.python.org/issue15795
    if os.name == "nt":
        # Recent versions of Windows have built-in support for unzipping files,
        # and with some cleverness you can access it from the command line.
        # I'm not that clever, and 7-Zip is pretty widely available.
        # https://superuser.com/questions/1314420/how-to-unzip-a-file-using-the-cmd
        subprocess.check_call(
            [
                "C:/Program Files/7-Zip/7z.exe",
                "x",
                str(zip_file),
                # Make 7-Zip more quiet. Unfortunately, we can't easily silence
                # it completely.
                "-bd",
                f"-o{dest_dir}",
            ]
        )
    else:
        # Unzip seems to be pretty universally available on posix systems.
        subprocess.check_call(["unzip", "-qq", str(zip_file), "-d", str(dest_dir)])
