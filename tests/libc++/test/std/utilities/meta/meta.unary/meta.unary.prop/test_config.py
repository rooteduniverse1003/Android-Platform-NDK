from ndk.test.buildtest.case import XunitResult


def build_broken(test: XunitResult) -> tuple[str, str] | tuple[None, None]:
    if test.case_name == "is_constructible.pass":
        return "clang/libc++ desync", "https://github.com/android/ndk/issues/1842"
    return None, None
