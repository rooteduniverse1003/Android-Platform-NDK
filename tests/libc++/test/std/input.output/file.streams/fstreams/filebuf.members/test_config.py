from typing import Optional

from ndk.test.devices import Device
from ndk.test.buildtest.case import Test


def run_broken(test: Test, device: Device) -> tuple[Optional[str], Optional[str]]:
    if test.case_name == "close.pass" and device.version >= 32:
        return (
            f"device API level {device.version}",
            "https://github.com/android/ndk/issues/1626",
        )
    return None, None
