from ndk.test.devices import Device
from ndk.test.devicetest.case import TestCase


def build_unsupported(test: TestCase) -> str | None:
    if test.config.abi != "arm64-v8a":
        return f"{test.config.abi}"
    return None


def run_unsupported(test: TestCase, device: Device) -> str | None:
    if device.version < 34:
        return f"{device.version}"
    return None


def run_broken(test: TestCase, device: Device) -> tuple[str | None, str | None]:
    return None, None
