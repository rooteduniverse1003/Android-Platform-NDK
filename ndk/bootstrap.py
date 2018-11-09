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
"""Bootstraping tools for the NDK's build."""
from __future__ import absolute_import
from __future__ import print_function

import logging
import multiprocessing
import os
import pipes
import shutil
import subprocess
import sys

import ndk.hosts
import ndk.paths
import ndk.timer


def logger():
    """Returns the module level logger."""
    return logging.getLogger(__name__)


def log_failure_and_exit(output):
    """Logs the bootstrapping failure and exits.

    Args:
        output: Output of the failed command.
    """
    log_path = os.path.join(
        ndk.paths.get_dist_dir(ndk.paths.get_out_dir()),
        'logs/build_error.log')

    with open(log_path, 'w') as error_log:
        error_log.write('Bootstrapping failed!\n')
        error_log.write(output)

    logger().error(output)
    sys.exit('Bootstrapping failed!')


def check_output(cmd):
    """Logged version of subprocess.check_output.

    stderr is automatically forwarded to stdout.

    Args:
        cmd: argv style argument list for the process to be run.

    Returns:
        Output
    """
    logger().debug('Runnning: %s', ' '.join([pipes.quote(a) for a in cmd]))
    return subprocess.check_output(cmd, stderr=subprocess.STDOUT)


def build_python(install_dir, build_dir):
    """Builds and installs Python to the given directory.

    Args:
        install_dir: Install path for the built Python distribution.
        build_dir: Directory to use for building Python.
    """
    logger().info('Bootstrapping Python...')

    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)
    os.makedirs(build_dir)

    old_cwd = os.getcwd()
    try:
        os.chdir(build_dir)

        python_src = ndk.paths.android_path('external/python/cpython3')
        check_output([
            os.path.join(python_src, 'configure'),
            '--prefix=' + install_dir,

            # This enables PGO and requires running all the Python tests to
            # generate those profiles. If we end up repackaging this Python to
            # ship in the NDK we should do this, but for now it makes
            # bootstrapping take a lot longer and we don't need the perforance
            # since our build time is dominated by non-Python code anyway.
            # '--enable-optimizations',
        ])

        check_output([
            'make',
            '-j',
            str(multiprocessing.cpu_count()),
            'install',
        ])
    except subprocess.CalledProcessError as ex:
        log_failure_and_exit(ex.output)
    finally:
        os.chdir(old_cwd)


def bootstrap():
    """Bootstraps the NDK's build.

    Builds the Python distribution needed for building the NDK.

    Returns:
        Install directory for the built Python distribution.
    """
    install_dir = ndk.paths.path_in_out('bootstrap')
    build_dir = ndk.paths.path_in_out('bootstrap-build')

    bootstrap_completed_file = ndk.paths.path_in_out('.bootstrapped')
    if os.path.exists(bootstrap_completed_file):
        return install_dir

    timer = ndk.timer.Timer()
    with timer:
        build_python(install_dir, build_dir)
    # TODO: Install any desired site-packages?
    logger().info('Bootstrapping completed in %s', timer.duration)

    with open(bootstrap_completed_file, 'w'):
        pass

    return install_dir
