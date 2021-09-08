#!/usr/bin/env python3
#
# Copyright (C) 2021 The Android Open Source Project
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

"""Downloads a set of Kokoro artifacts and prepares commits updating prebuilts.

The script accepts a list of Kokoro build IDs (a list of UUIDs). It downloads
each build's main archive and extracts it into the appropriate place in an
ndk-kokoro-main repo/pore checkout. It automatically creates a branch and a
commit updating each prebuilt.

The script uses the `stubby` CLI tool to access the Kokoro API to retrieve build
details. This gives it the location of Kokoro builds (in placer) as well as
a list of Git-on-Borg SHAs. For the given set of build IDs, it verifies that no
two builds use different Git SHAs for a given repository, which guards against
accidentally updating two hosts to different versions.

The script uses `fileutil` to download artifacts from placer.

The script needs the google.protobuf Python module.
"""

import argparse
from dataclasses import dataclass
import glob
import logging
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import textwrap
from typing import Sequence
from uuid import UUID

try:
    import google.protobuf.text_format
    from kokoro_api_pb2 import BuildStatusResponse
except ImportError:
    print('error: could not import protobuf modules')
    print('Try "apt install python3-protobuf" or "pip install protobuf".\n')
    raise


THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parent.parent


@dataclass(frozen=True)
class KokoroPrebuilt:
    title: str
    extract_path: str
    artifact_glob: str


# A map from a Kokoro job name to the paths needed for downloading and
# extracting an archive.
KOKORO_PREBUILTS: dict[str, KokoroPrebuilt] = {
    'ndk/cmake/linux_continuous': KokoroPrebuilt(
        title='Linux CMake',
        extract_path='prebuilts/cmake/linux-x86',
        artifact_glob='cmake-linux-*-{build_id}.zip'
    ),
    'ndk/cmake/darwin_continuous': KokoroPrebuilt(
        title='Darwin CMake',
        extract_path='prebuilts/cmake/darwin-x86',
        artifact_glob='cmake-darwin-*-{build_id}.zip'
    ),
    'ndk/cmake/windows_continuous': KokoroPrebuilt(
        title='Windows CMake',
        extract_path='prebuilts/cmake/windows-x86',
        artifact_glob='cmake-windows-*-{build_id}.zip'
    ),
    'ndk/python3/linux_continuous': KokoroPrebuilt(
        title='Linux Python3',
        extract_path='prebuilts/python/linux-x86',
        artifact_glob='python3-linux-{build_id}.tar.bz2'
    ),
    'ndk/python3/darwin_continuous': KokoroPrebuilt(
        title='Darwin Python3',
        extract_path='prebuilts/python/darwin-x86',
        artifact_glob='python3-darwin-{build_id}.tar.bz2'
    ),
    'ndk/python3/windows_continuous': KokoroPrebuilt(
        title='Windows Python3',
        extract_path='prebuilts/python/windows-x86',
        artifact_glob='python3-windows-{build_id}.zip'
    ),
}


def logger() -> logging.Logger:
    """Returns the module logger."""
    return logging.getLogger(__name__)


def check_call(cmd: Sequence[str]) -> None:
    """subprocess.check_call with logging."""
    logger().info('check_call `%s`', shlex.join(cmd))
    subprocess.check_call(cmd)


def rmtree(path: Path) -> None:
    """shutil.rmtree with logging."""
    logger().info('rmtree %s', path)
    shutil.rmtree(path)


def makedirs(path: Path) -> None:
    """os.makedirs with logging."""
    logger().info('mkdir -p %s', path)
    path.mkdir(parents=True, exist_ok=True)


def in_pore_tree() -> bool:
    """Returns True if the tree is using pore instead of repo."""
    return (REPO_ROOT / '.pore').exists()


def parse_args() -> argparse.Namespace:
    """Parses and returns command line arguments."""
    parser = argparse.ArgumentParser(
        description='Downloads artifacts from Kokoro and prepares commits to '
                    'update prebuilts.')

    parser.add_argument(
        'build_id',
        metavar='BUILD_ID',
        type=UUID,
        nargs='+',
        help=('Kokoro build ID (a UUID)'))

    parser.add_argument(
        '-m',
        '--message',
        default='',
        help='Extra text to include in commit messsages.')

    parser.add_argument(
        '-b',
        '--bug',
        default='None',
        help='Bug URL for commit messages.')

    branch_group  = parser.add_mutually_exclusive_group()

    branch_group.add_argument(
        '--use-current-branch',
        action='store_true',
        help='Do not repo/pore start new branches for the update.')

    branch_group.add_argument(
        '--branch',
        default='update-kokoro-prebuilts',
        help='Name of branch to pass to repo/pore start.')

    parser.add_argument(
        '-v',
        '--verbose',
        action='store_true',
        help='Dump extra debugging information.')

    return parser.parse_args()


@dataclass(frozen=True)
class BuildStatus:
    job_name: str
    build_id: UUID
    placer_path: str
    # name -> sha. (e.g. 'external/cmake' -> '86d651ddf5a1ca0ec3e4823bda800b0cea32d253')
    repos: dict[str, str]


# References:
#  - https://g3doc.corp.google.com/devtools/kokoro/g3doc/userdocs/general/api.md#example-of-using-the-stubby-cli
#  - http://google3/devtools/kokoro/api/proto/kokoro_api.proto
def get_build_status(build_id_list: list[UUID]) -> list[BuildStatus]:
    """Use the stubby CLI to access the Kokoro API, to query build statuses of a
    list of build IDs.
    """
    stubby_request = '\n'.join([f'build_id: "{x}"\n' for x in build_id_list])
    logger().info('stubby_request="""%s"""', stubby_request)

    stubby_path = shutil.which('stubby')
    if not stubby_path:
        sys.exit('error: no "stubby" in PATH. Run on a corp machine and/or run '
                 '"apt install stubby-cli".')

    stubby_cmd = [stubby_path, 'call', 'blade:kokoro-api',
                  'KokoroApi.GetBuildStatus', '--batch', '--proto2']
    logger().info('check_output `%s`', shlex.join(stubby_cmd))
    stubby_out = subprocess.check_output(stubby_cmd, input=stubby_request,
                                         encoding='utf8')
    logger().debug('stubby_out="""%s"""', stubby_out)

    results = []

    # With --batch and text output, each BuildStatusResponse is separated by a
    # blank line.
    for response_txt in stubby_out.strip().split('\n\n'):
        response = BuildStatusResponse()
        google.protobuf.text_format.Parse(response_txt, response,
                                          allow_unknown_field=True)
        build_result = response.build_result
        job_name = build_result.env_vars['JOB_NAME']
        (placer_path,) = build_result.build_artifacts
        repos = {x.name: x.sha1 for x in build_result.multi_scm_revision.git_on_borg_scm_revision}
        build_id = UUID(response.build_id)
        result = BuildStatus(job_name, build_id, placer_path, repos)
        results.append(result)

    assert build_id_list == [x.build_id for x in results]
    return results


def validate_build_repos(builds: list[BuildStatus]) -> None:
    """Make sure that no two builds have different git SHAs for the same
    repository name."""
    repos = {}
    success = True
    for build in builds:
        for name, sha in build.repos.items():
            if name not in repos:
                repos[name] = (sha, build.build_id)
            else:
                if repos[name][0] != sha:
                    print(f'error: conflicting versions of {name} repo:')
                    print(f' - {repos[name][0]} in {repos[name][1]}')
                    print(f' - {sha} in {build.build_id}')
                    success = False
    if not success:
        sys.exit(1)

    # Print out a table of git SHAs and repository names.
    print('No conflicting repositories detected:')
    for name, (sha, _) in sorted(repos.items()):
        print(f'{sha} {name}')
    print()


def validate_job_names(builds: list[BuildStatus]) -> None:
    print('Kokoro builds to download:')
    for build in builds:
        print(f'{build.build_id} {build.job_name}')
    print()
    names = [build.job_name for build in builds]
    for name in names:
        if names.count(name) != 1:
            sys.exit(f'error: job {name} specified more than once')
        if name not in KOKORO_PREBUILTS:
            sys.exit(f'error: job {name} is not handled by this script')


def clean_dest_dir(parent: Path) -> None:
    """Remove the contents of the directory (whether tracked or untracked by
    git), but don't remove .git or .gitignore."""
    logger().info('clean_dest_dir %s', parent)
    for name in os.listdir(parent):
        if name == '.git':
            continue
        if name == '.gitignore':
            # The prebuilts/python/* directories have a .gitignore file that
            # isn't part of the Kokoro archive, but we want to preserve it when
            # updating prebuilts.
            continue
        path = parent / name
        if path.is_symlink() or path.is_file():
            os.unlink(path)
        else:
            shutil.rmtree(path)


def download_artifacts(builds: list[BuildStatus]) -> list[Path]:
    """Download each build's artifact.

    Return a list of absolute paths."""
    patterns = []
    for build in builds:
        prebuilt = KOKORO_PREBUILTS[build.job_name]
        patterns.append(build.placer_path + '/' +
            prebuilt.artifact_glob.format(build_id=build.build_id))

    tmp_dir = REPO_ROOT / 'placer_artifacts'
    if tmp_dir.exists():
        rmtree(tmp_dir)
    makedirs(tmp_dir)

    check_call(['fileutil', 'cp', '-parallelism', '4'] + patterns +
               [str(tmp_dir)])
    artifacts = []
    for pattern in patterns:
        (artifact,) = glob.glob(str(tmp_dir / os.path.basename(pattern)))
        artifacts.append(Path(artifact))

    return artifacts


def update_artifact(build: BuildStatus, archive_path: Path, extra_message: str,
                    bug: str, use_current_branch: bool,
                    branch_name: str) -> None:
    job_name = build.job_name
    prebuilt = KOKORO_PREBUILTS[job_name]
    dest_path = REPO_ROOT / prebuilt.extract_path

    os.chdir(dest_path)

    if not use_current_branch:
        repo_cmd = 'pore' if in_pore_tree() else 'repo'
        check_call([repo_cmd, 'start', branch_name])

    clean_dest_dir(dest_path)
    if archive_path.name.endswith('.tar.bz2'):
        check_call(['tar', '-xf', str(archive_path)])
    elif archive_path.name.endswith('.zip'):
        check_call(['unzip', '-q', str(archive_path)])
    else:
        sys.exit(f'error: unrecognized type of archive: {archive_path}')
    # Pass -f so that files from the archive are added even if they are listed
    # in .gitignore.
    check_call(['git', 'add', '-f', '.'])

    commit_msg = textwrap.dedent(
        f'''\
        Update {prebuilt.title} prebuilt

        Fusion2: http://fusion2/{build.build_id}
        Kokoro job: {job_name}
        Prebuilt updated using: {Path(__file__).resolve().relative_to(REPO_ROOT)}

        {extra_message}

        Test: Treehugger, Kokoro presubmit
        Bug: {bug}
        ''')

    check_call(['git', 'commit', '-m', commit_msg])


def main() -> None:
    args = parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    builds = get_build_status(args.build_id)
    validate_build_repos(builds)
    validate_job_names(builds)
    artifacts = download_artifacts(builds)

    for build, artifact in zip(builds, artifacts):
        update_artifact(build, artifact, args.message, args.bug,
                        args.use_current_branch, args.branch)


if __name__ == '__main__':
    main()
