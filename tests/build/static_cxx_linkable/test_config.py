"""Test for https://github.com/android/ndk/issues/1130."""
from typing import Optional, Tuple

from ndk.test.types import NdkBuildTest, Test
from ndk.toolchains import LinkerOption


def build_broken(test: Test) -> Tuple[Optional[str], Optional[str]]:
    is_ndk_build = isinstance(test, NdkBuildTest)
    not_lld = test.config.linker != LinkerOption.Lld
    assert test.config.api is not None
    if is_ndk_build and test.config.api < 21 and not_lld:
        # ndk-build manually links all the libc++ components because using the
        # linker script makes it possible for broken prebuilts to cause
        # exception unwinding issues on arm32, and ndk-build doesn't have good
        # ways to deal with cyclic dependencies.
        #
        # It does seem that LLD will research earlier libraries for missing
        # symbols so this builds fine there. It's also only an issue for builds
        # using libandroid_support, and beyond that we should be able to fix
        # the dependency ordering more generally once we no longer support API
        # 16 because the only reason for the cyclic dependency is because
        # posix_memalign isn't reliably available on API 16, and it's needed
        # by libc++abi.
        return 'ndk-build', 'https://github.com/android/ndk/issues/545'
    return None, None
