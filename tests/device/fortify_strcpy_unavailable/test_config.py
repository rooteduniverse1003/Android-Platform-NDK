from typing import Optional

from ndk.test.types import Test


def build_unsupported(test: Test) -> Optional[str]:
    if test.config.api is not None and test.config.api >= 21:
        return f'strcpy is caught at build time for android-{test.config.api}'
    return None
