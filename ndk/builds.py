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
"""Defines the NDK build system API.

Note: this isn't the ndk-build API, but the API for building the NDK itself.
"""
from __future__ import absolute_import

import ntpath
import os
import shutil
import stat
import subprocess
from typing import Iterable, Optional, Set

import ndk.abis
import ndk.ext.shutil
import ndk.packaging
import ndk.paths


class ModuleValidateError(RuntimeError):
    pass


class NoticeGroup:
    """An enum describing NOTICE file groupings.

    The NDK ships two NOTICE files: one for the toolchain, and one for
    everything else.
    """
    BASE = 1
    TOOLCHAIN = 2


class BuildContext:
    def __init__(self, out_dir, dist_dir, modules, host, arches, build_number):
        self.out_dir = out_dir
        self.dist_dir = dist_dir
        self.modules = {m.name: m for m in modules}
        self.host = host
        self.arches = arches
        self.build_number = build_number


class Module:
    name: Optional[str] = None
    path: Optional[str] = None
    deps: Set[str] = set()

    # Used to exclude a module from the build. If explicitly named it will
    # still be built, but it is not included by default.
    enabled = True

    # In most cases a module will have only one license file, so the common
    # interface is a single path, not a list. For the rare modules that have
    # multiple notice files (such as yasm), the notices property should be
    # overrided. By default this property will return `[self.notice]`.
    notice = None

    # Not all components need a notice (stub scripts, basic things like the
    # readme and changelog, etc), but this is opt-out.
    no_notice = False

    # Indicates which NOTICE file that should contain the license text for this
    # module. i.e. NoticeGroup.BASE will result in the license being included
    # in $NDK/NOTICE, whereas NoticeGroup.TOOLCHAIN will result in the license
    # text being included in NOTICE.toolchain.
    notice_group = NoticeGroup.BASE

    # If split_build_by_arch is set, one workqueue task will be created for
    # each architecture. The Module object will be cloned for each arch and
    # each will have build_arch set to the architecture that should be built by
    # that module. If build_arch is None, the module has not yet been split.
    split_build_by_arch = False
    build_arch = None

    def __init__(self):
        self.context = None
        if self.notice is None:
            self.notice = self.default_notice_path()
        self.validate()

    @property
    def notices(self):
        if self.no_notice:
            return []
        if self.notice is None:
            return []
        return [self.notice]

    def default_notice_path(self):  # pylint: disable=no-self-use
        return None

    def validate_error(self, msg):
        return ModuleValidateError('{}: {}'.format(self.name, msg))

    def validate(self):
        if self.name is None:
            raise ModuleValidateError('{} has no name'.format(self.__class__))
        if self.path is None:
            raise self.validate_error('path property not set')
        if self.notice_group not in (NoticeGroup.BASE, NoticeGroup.TOOLCHAIN):
            raise self.validate_error('invalid notice group')
        self.validate_notice()

    def validate_notice(self):
        if self.no_notice:
            return

        if not self.notices:
            raise self.validate_error('notice property not set')
        for notice in self.notices:
            if not os.path.exists(notice):
                raise self.validate_error(
                    'notice file {} does not exist'.format(notice))

    def get_dep(self, name):
        if name not in self.deps:
            raise KeyError
        return self.context.modules[name]

    def get_build_host_install(self, arch=None):
        return self.get_install_path(ndk.hosts.get_default_host(), arch)

    @property
    def out_dir(self):
        return self.context.out_dir

    @property
    def dist_dir(self):
        return self.context.dist_dir

    @property
    def host(self):
        return self.context.host

    @property
    def arches(self):
        return self.context.arches

    def build(self):
        raise NotImplementedError

    def install(self):
        package_installs = ndk.packaging.expand_packages(
            self.name, self.path, self.host, self.arches)

        install_base = ndk.paths.get_install_path(self.out_dir,
                                                  self.host)
        for package_name, package_install in package_installs:
            install_path = os.path.join(install_base, package_install)
            package = os.path.join(self.context.dist_dir, package_name)
            if os.path.exists(install_path):
                shutil.rmtree(install_path)
            ndk.packaging.extract_zip(package, install_path)

    def get_install_paths(self, host, arches):
        install_subdirs = ndk.packaging.expand_paths(self.path, host, arches)
        install_base = ndk.paths.get_install_path(self.out_dir, host)
        return [os.path.join(install_base, d) for d in install_subdirs]

    def get_install_path(self, host=None, arch=None):
        if host is None:
            host = self.host

        arch_dependent = False
        if ndk.packaging.package_varies_by(self.path, 'abi'):
            arch_dependent = True
        elif ndk.packaging.package_varies_by(self.path, 'arch'):
            arch_dependent = True
        elif ndk.packaging.package_varies_by(self.path, 'toolchain'):
            arch_dependent = True
        elif ndk.packaging.package_varies_by(self.path, 'triple'):
            arch_dependent = True

        arches = None
        if arch is not None:
            arches = [arch]
        elif self.build_arch is not None:
            arches = [self.build_arch]
        elif arch_dependent:
            raise ValueError(
                'get_install_path for {} requires valid arch'.format(arch))

        install_subdirs = self.get_install_paths(host, arches)

        if len(install_subdirs) != 1:
            raise RuntimeError(
                'non-unique install path for single arch: ' + self.path)

        return install_subdirs[0]

    def __str__(self):
        if self.split_build_by_arch and self.build_arch is not None:
            return '{} [{}]'.format(self.name, self.build_arch)
        return self.name

    def __hash__(self):
        # The string representation of each module must be unique. This is true
        # both pre- and post-arch split.
        return hash(str(self))

    def __eq__(self, other):
        # As with hash(), the str must be unique across all modules.
        return str(self) == str(other)

    @property
    def log_file(self):
        if self.split_build_by_arch and self.build_arch is not None:
            return '{}-{}.log'.format(self.name, self.build_arch)
        elif self.split_build_by_arch:
            raise RuntimeError('Called log_file on unsplit module')
        else:
            return '{}.log'.format(self.name)

    def log_path(self, log_dir):
        return os.path.join(log_dir, self.log_file)


class PackageModule(Module):
    src = None
    create_repo_prop = False

    def default_notice_path(self):
        return os.path.join(self.src, 'NOTICE')

    def validate(self):
        super(PackageModule, self).validate()

        if ndk.packaging.package_varies_by(self.path, 'abi'):
            raise self.validate_error(
                'PackageModule cannot vary by abi')
        if ndk.packaging.package_varies_by(self.path, 'arch'):
            raise self.validate_error(
                'PackageModule cannot vary by arch')
        if ndk.packaging.package_varies_by(self.path, 'toolchain'):
            raise self.validate_error(
                'PackageModule cannot vary by toolchain')
        if ndk.packaging.package_varies_by(self.path, 'triple'):
            raise self.validate_error(
                'PackageModule cannot vary by triple')

    def build(self):
        pass

    def install(self):
        install_paths = self.get_install_paths(self.host,
                                               ndk.abis.ALL_ARCHITECTURES)
        assert len(install_paths) == 1
        install_path = install_paths[0]
        install_directory(self.src, install_path)
        if self.create_repo_prop:
            make_repo_prop(install_path)


class InvokeExternalBuildModule(Module):
    script: Optional[str] = None
    arch_specific = False

    def build(self):
        build_args = common_build_args(self.out_dir, self.dist_dir, self.host)
        if self.split_build_by_arch:
            build_args.append('--arch={}'.format(self.build_arch))
        elif self.arch_specific and len(self.arches) == 1:
            build_args.append('--arch={}'.format(self.arches[0]))
        elif self.arches == ndk.abis.ALL_ARCHITECTURES:
            pass
        else:
            raise NotImplementedError(
                'Module {} can only build all architectures or none'.format(
                    self.name))
        script = self.get_script_path()
        invoke_external_build(script, build_args)

    def get_script_path(self):
        return ndk.paths.android_path(self.script)


class InvokeBuildModule(InvokeExternalBuildModule):
    def get_script_path(self):
        return ndk.paths.ndk_path('build/tools', self.script)


class FileModule(Module):
    src = None

    # Used for things like the readme and the changelog. No notice needed.
    no_notice = True

    def build(self):
        pass

    def install(self):
        shutil.copy2(self.src, self.get_install_path())


class MultiFileModule(Module):
    files: Iterable[str] = []

    def build(self):
        pass

    def install(self):
        install_dir = self.get_install_path()
        ndk.ext.shutil.create_directory(install_dir)
        for file_path in self.files:
            shutil.copy2(file_path, install_dir)


class ScriptShortcutModule(Module):
    script: Optional[str] = None
    windows_ext: Optional[str] = None

    # These are all trivial shell scripts that we generated. No notice needed.
    no_notice = True

    def validate(self):
        super(ScriptShortcutModule, self).validate()

        if ndk.packaging.package_varies_by(self.script, 'abi'):
            raise self.validate_error(
                'ScriptShortcutModule cannot vary by abi')
        if ndk.packaging.package_varies_by(self.script, 'arch'):
            raise self.validate_error(
                'ScriptShortcutModule cannot vary by arch')
        if ndk.packaging.package_varies_by(self.script, 'toolchain'):
            raise self.validate_error(
                'ScriptShortcutModule cannot vary by toolchain')
        if ndk.packaging.package_varies_by(self.script, 'triple'):
            raise self.validate_error(
                'ScriptShortcutModule cannot vary by triple')
        if self.windows_ext is None:
            raise self.validate_error(
                'ScriptShortcutModule requires windows_ext')

    def build(self):
        pass

    def install(self):
        if self.host.startswith('windows'):
            self.make_cmd_helper()
        else:
            self.make_sh_helper()

    def make_cmd_helper(self):
        script = self.get_script_path()
        full_path = ntpath.join(
            '%~dp0', ntpath.normpath(script) + self.windows_ext)

        install_path = self.get_install_path() + '.cmd'
        with open(os.path.join(install_path), 'w') as helper:
            helper.writelines([
                '@echo off\n',
                full_path + ' %*\n',
            ])

    def make_sh_helper(self):
        script = self.get_script_path()
        full_path = os.path.join('$DIR', script)

        install_path = self.get_install_path()
        with open(install_path, 'w') as helper:
            helper.writelines([
                '#!/bin/sh\n',
                'DIR="$(cd "$(dirname "$0")" && pwd)"\n',
                full_path + ' "$@"',
            ])
        mode = os.stat(install_path).st_mode
        os.chmod(install_path,
                 mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def get_script_path(self):
        scripts = ndk.packaging.expand_paths(
            self.script, self.host, ndk.abis.ALL_ARCHITECTURES)
        assert len(scripts) == 1
        return scripts[0]


class PythonPackage(Module):
    def default_notice_path(self):
        # Assume there's a NOTICE file in the same directory as the setup.py.
        return os.path.join(os.path.dirname(self.path), 'NOTICE')

    def build(self):
        cwd = os.path.dirname(self.path)
        subprocess.check_call(
            ['python', self.path, 'sdist', '-d', self.out_dir], cwd=cwd)

    def install(self):
        pass


def _invoke_build(script, args):
    if args is None:
        args = []
    subprocess.check_call([ndk.paths.android_path(script)] + args)


def invoke_build(script, args=None):
    script_path = os.path.join('build/tools', script)
    _invoke_build(ndk.paths.ndk_path(script_path), args)


def invoke_external_build(script, args=None):
    _invoke_build(ndk.paths.android_path(script), args)


def common_build_args(out_dir, dist_dir, host):
    return [
        '--out-dir={}'.format(os.path.join(out_dir, host)),
        '--dist-dir={}'.format(dist_dir),
        '--host={}'.format(host),
    ]


def install_directory(src, dst):
    if os.path.exists(dst):
        shutil.rmtree(dst)
    ignore_patterns = shutil.ignore_patterns(
        '*.pyc', '*.pyo', '*.swp', '*.git*')
    shutil.copytree(src, dst, ignore=ignore_patterns)


def make_repo_prop(out_dir):
    file_name = 'repo.prop'

    dist_dir = os.environ.get('DIST_DIR')
    if dist_dir is not None:
        dist_repo_prop = os.path.join(dist_dir, file_name)
        shutil.copy(dist_repo_prop, out_dir)
    else:
        out_file = os.path.join(out_dir, file_name)
        with open(out_file, 'w') as prop_file:
            cmd = [
                'repo', 'forall', '-c',
                'echo $REPO_PROJECT $(git rev-parse HEAD)',
            ]
            subprocess.check_call(cmd, stdout=prop_file)
