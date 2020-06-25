from typing import Optional

from ndk.test.types import Test
from ndk.toolchains import LinkerOption


def build_unsupported(test: Test) -> Optional[str]:
    if test.config.linker == LinkerOption.Deprecated:
        return 'test is LLD only'
    return None
