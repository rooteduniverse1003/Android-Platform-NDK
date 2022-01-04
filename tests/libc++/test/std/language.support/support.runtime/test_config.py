from typing import Optional

from ndk.test.types import Test


def build_broken(test: Test) -> tuple[Optional[str], Optional[str]]:
    if test.case_name == 'cstdlib.pass' and test.config.api < 21:
        return 'pre API 21', 'https://github.com/android/ndk/issues/1108'
    return None, None
