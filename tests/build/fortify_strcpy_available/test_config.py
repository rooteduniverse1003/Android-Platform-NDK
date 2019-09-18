from typing import Optional

from ndk.test.types import Test


def build_unsupported(test: Test) -> Optional[str]:
    if test.config.api is not None and test.config.api < 17:
        return f'__strcpy_chk not available in android-{test.config.api}'
    return None


def is_negative_test() -> bool:
    return True
