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
"""Tools for bootstrapping Python 3."""
import datetime
import logging
import multiprocessing
import os
import pipes
import shutil
import subprocess
import sys
import timeit


THIS_DIR = os.path.realpath(os.path.dirname(__file__))


def logger():
    """Returns the module level logger."""
    return logging.getLogger(__name__)


def android_path(*args):
    """Returns the absolute path rooted within the top level source tree."""
    return os.path.normpath(os.path.join(THIS_DIR, '../..', *args))


def _get_dir_from_env(default, env_var):
    """Returns the path to a directory specified by the environment.

    If the environment variable is not set, the default will be used. The
    directory is created if it does not exist.

    Args:
        default: The path used if the environment variable is not set.
        env_var: The environment variable that contains the path, if any.

    Returns:
        The absolute path to the directory.
    """
    path = os.path.realpath(os.getenv(env_var, default))
    if not os.path.isdir(path):
        os.makedirs(path)
    return path


def get_out_dir():
    """Returns the out directory."""
    return _get_dir_from_env(android_path('out'), 'OUT_DIR')


def get_dist_dir():
    """Returns the distribution directory.

    The contents of the distribution directory are archived on the build
    servers. Suitable for build logs and final artifacts.
    """
    return _get_dir_from_env(os.path.join(get_out_dir(), 'dist'), 'DIST_DIR')


def path_in_out(dirname):
    """Returns a path within the out directory."

    Args:
        dirname: Name of the directory.

    Returns:
        Absolute path within the out directory.
    """
    return os.path.join(get_out_dir(), dirname)


def log_failure_and_exit(output):
    """Logs the bootstrapping failure and exits.

    Args:
        output: Output of the failed command.
    """
    log_path = os.path.join(get_dist_dir(), 'logs/build_error.log')
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

        python_src = android_path('external/python/cpython3')
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


class Timer(object):  # pylint: disable=useless-object-inheritance
    """Execution timer.

    Can be used explicitly with stop/start, but preferably is used as a context
    manager:

    >>> timer = Timer()
    >>> with timer:
    >>>     do_something()
    >>> print('do_something() took {}'.format(timer.duration))
    """
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.duration = None

    def start(self):
        """Start the timer."""
        self.start_time = timeit.default_timer()

    def finish(self):
        """Stop the timer."""
        self.end_time = timeit.default_timer()

        # Not interested in partial seconds at this scale.
        seconds = int(self.end_time - self.start_time)
        self.duration = datetime.timedelta(seconds=seconds)

    def __enter__(self):
        self.start()

    def __exit__(self, _exc_type, _exc_value, _traceback):
        self.finish()


def bootstrap():
    """Creates a bootstrap Python 3 environment.

    Builds and installs Python 3 for use on the current host. After execution,
    the directory containing the python3 binary will be the first element in
    the PATH.
    """
    install_dir = path_in_out('bootstrap')
    build_dir = path_in_out('bootstrap-build')

    bootstrap_completed_file = path_in_out('.bootstrapped')
    if os.path.exists(bootstrap_completed_file):
        return

    timer = Timer()
    with timer:
        build_python(install_dir, build_dir)
    # TODO: Install any desired site-packages?
    logger().info('Bootstrapping completed in %s', timer.duration)

    with open(bootstrap_completed_file, 'w'):
        pass

    bootstrap_bin = os.path.join(install_dir, 'bin')
    os.environ['PATH'] = os.pathsep.join([bootstrap_bin, os.environ['PATH']])
