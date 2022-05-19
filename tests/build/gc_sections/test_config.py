from typing import Optional

from ndk.test.buildtest.case import Test


def build_broken(test: Test) -> tuple[Optional[str], Optional[str]]:
    return "all", "https://github.com/android/ndk/issues/1717"
