from typing import Optional

from ndk.test.devices import Device
from ndk.test.types import Test


def run_unsupported(test: Test, device: Device) -> Optional[str]:
    if test.config.api is not None and test.config.api < 17:
        return f'__memset_chk not available in android-{test.config.api}'
    return None
