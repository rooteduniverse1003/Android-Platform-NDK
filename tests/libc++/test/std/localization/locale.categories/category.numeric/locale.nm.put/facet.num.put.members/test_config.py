from typing import Optional

from ndk.test.devices import Device
from ndk.test.devicetest.case import LibcxxTestCase


def run_broken(
    test: LibcxxTestCase, device: Device
) -> tuple[Optional[str], Optional[str]]:
    if test.case_name == "put_long_double.pass" and device.version > 21:
        # libc++ expects only one format of positive nan. At some point this changed.
        # The API level above will likely need to be changed as we test on other old API
        # levels.
        return f"{test.config.abi} OS {device.version}", "http://b/34950416"
    percent_f_tests = ("put_double.pass", "put_long_double.pass")
    if test.case_name in percent_f_tests and device.version < 21:
        return f"android-{device.version}", "http://b/35764716"
    return None, None
