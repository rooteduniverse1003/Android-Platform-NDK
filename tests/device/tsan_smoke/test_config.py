from ndk.test.devices import Device
from ndk.test.devicetest.case import TestCase


def build_unsupported(test):
    if test.config.is_lp32:
        return test.config.abi
    return None


def run_unsupported(test: TestCase, device: Device) -> str | None:
    return "runs indefinitely with latest clang"


def run_broken(test, device):
    return "all", "https://github.com/android/ndk/issues/1171"
