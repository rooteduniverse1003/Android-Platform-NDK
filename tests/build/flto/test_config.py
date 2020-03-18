import sys
from typing import Tuple

from ndk.toolchains import LinkerOption
from ndk.test.types import Test


def build_broken(test: Test) -> Tuple[str, str]:
    if sys.platform == 'darwin':
        if test.config.linker == LinkerOption.Deprecated:
            bug = 'https://github.com/android/ndk/issues/1209'
            return 'Darwin LTO with deprecated linkers', bug
    return None, None
