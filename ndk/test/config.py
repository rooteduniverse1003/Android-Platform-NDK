#
# Copyright (C) 2015 The Android Open Source Project
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
import imp
import os


class TestConfig(object):
    """Describes the status of a test.

    Each test directory can contain a "test_config.py" file that describes
    the configurations a test is not expected to pass for. Previously this
    information could be captured in one of two places: the Application.mk
    file, or a BROKEN_BUILD/BROKEN_RUN file.

    Application.mk was used to state that a test was only to be run for a
    specific platform version, specific toolchain, or a set of ABIs.
    Unfortunately Application.mk could only specify a single toolchain or
    platform, not a set.

    BROKEN_BUILD/BROKEN_RUN files were too general. An empty file meant the
    test should always be skipped regardless of configuration. Any change that
    would put a test in that situation should be reverted immediately. These
    also didn't make it clear if the test was actually broken (and thus should
    be fixed) or just not applicable.

    A test_config.py file is more flexible. It is a Python module that defines
    at least one function by the same name as one in TestConfig.NullTestConfig.
    If a function is not defined the null implementation (not broken,
    supported), will be used.
    """

    class NullTestConfig(object):
        def __init__(self):
            pass

        # pylint: disable=unused-argument
        @staticmethod
        def build_broken(abi, platform):
            """Tests if a given configuration is known broken.

            A broken test is a known failing test that should be fixed.

            Any test with a non-empty broken section requires a "bug" entry
            with a link to either an internal bug (http://b/BUG_NUMBER) or a
            public bug (http://b.android.com/BUG_NUMBER).

            These tests will still be built and run. If the test succeeds, it
            will be reported as an error.

            Returns: A tuple of (broken_configuration, bug) or (None, None).
            """
            return None, None

        @staticmethod
        def build_unsupported(abi, platform):
            """Tests if a given configuration is unsupported.

            An unsupported test is a test that do not make sense to run for a
            given configuration. Testing x86 assembler on MIPS, for example.

            These tests will not be built or run.

            Returns: The string unsupported_configuration or None.
            """
            return None

        @staticmethod
        def extra_cmake_flags():
            return []

        @staticmethod
        def extra_ndk_build_flags():
            """Returns extra flags that should be passed to ndk-build."""
            return []

        @staticmethod
        def is_negative_test():
            """Returns True if this test should pass if the build fails.

            Note that this is different from build_broken. Use build_broken to
            indicate a bug and use is_negative_test to indicate a test that
            should fail if things are working.

            Also note that check_broken and is_negative_test can be layered. If
            a build is expected to fail, but doesn't for armeabi, the
            test_config could contain:

                def is_negative_test():
                    return True


                def build_broken(abi, api):
                    if abi == 'armeabi':
                        return abi, bug_url
                    return None, None
            """
            return False
        # pylint: enable=unused-argument

    def __init__(self, file_path):
        # Note that this namespace isn't actually meaningful from our side;
        # it's only what the loaded module's __name__ gets set to.
        dirname = os.path.dirname(file_path)
        namespace = '.'.join([dirname, 'test_config'])

        try:
            self.module = imp.load_source(namespace, file_path)
        except IOError:
            self.module = None

        try:
            self.build_broken = self.module.build_broken
        except AttributeError:
            self.build_broken = self.NullTestConfig.build_broken

        try:
            self.build_unsupported = self.module.build_unsupported
        except AttributeError:
            self.build_unsupported = self.NullTestConfig.build_unsupported

        try:
            self.extra_cmake_flags = self.module.extra_cmake_flags
        except AttributeError:
            self.extra_cmake_flags = self.NullTestConfig.extra_cmake_flags

        try:
            self.extra_ndk_build_flags = self.module.extra_ndk_build_flags
        except AttributeError:
            ntc = self.NullTestConfig
            self.extra_ndk_build_flags = ntc.extra_ndk_build_flags

        try:
            self.is_negative_test = self.module.is_negative_test
        except AttributeError:
            self.is_negative_test = self.NullTestConfig.is_negative_test

    @classmethod
    def from_test_dir(cls, test_dir):
        path = os.path.join(test_dir, 'test_config.py')
        return cls(path)


class DeviceTestConfig(TestConfig):
    """Specialization of test_config.py that includes device API level.

    We need to mark some tests as broken or unsupported based on what device
    they are running on, as opposed to just what they were built for.
    """
    class NullTestConfig(TestConfig.NullTestConfig):
        # pylint: disable=unused-argument
        @staticmethod
        def run_broken(abi, device_api, subtest):
            return None, None

        @staticmethod
        def run_unsupported(abi, device_api, subtest):
            return None

        @staticmethod
        def extra_cmake_flags():
            return []
        # pylint: enable=unused-argument

    def __init__(self, file_path):
        super(DeviceTestConfig, self).__init__(file_path)

        try:
            self.run_broken = self.module.run_broken
        except AttributeError:
            self.run_broken = self.NullTestConfig.run_broken

        try:
            self.run_unsupported = self.module.run_unsupported
        except AttributeError:
            self.run_unsupported = self.NullTestConfig.run_unsupported

        if hasattr(self.module, 'is_negative_test'):
            # If the build is expected to fail, then it should just be a build
            # test since the test should never be run.
            #
            # If the run is expected to fail, just fix the test to pass for
            # thatr case. Gtest death tests can handle the more complicated
            # cases.
            raise RuntimeError('is_negative_test is invalid for device tests')


class LibcxxTestConfig(DeviceTestConfig):
    """Specialization of test_config.py for libc++.

    The libc++ tests have multiple tests in a single directory, so we need to
    pass the test name for build_broken too.
    """
    class NullTestConfig(TestConfig.NullTestConfig):
        # pylint: disable=unused-argument,arguments-differ
        @staticmethod
        def build_unsupported(abi, api, name):
            return None

        @staticmethod
        def build_broken(abi, api, name):
            return None, None

        @staticmethod
        def run_unsupported(abi, device_api, name):
            return None

        @staticmethod
        def run_broken(abi, device_api, name):
            return None, None
        # pylint: enable=unused-argument,arguments-differ
