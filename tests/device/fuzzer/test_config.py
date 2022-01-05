from typing import Optional

from ndk.test.devices import Device
from ndk.test.types import Test


def run_unsupported(test: Test, _device: Device) -> Optional[str]:
    if test.name == "fuzzer.fuzz_test":
        return "not a real test"
    return None
