# Verify that an NDK binary can be linked with --warn-execstack without a
# warning. Regression test for https://github.com/android-ndk/ndk/issues/779.
#
# ndk-build implicitly passes -Wl,--fatal-warnings, so a warning fails the
# test.
#
# Gold is only linker to implement --warn-execstack. ld.bfd doesn't recognize
# --warn-execstack, and ld.lld *does* recognize the flag, but quietly discards
# it.

APP_LDFLAGS := -fuse-ld=gold -Wl,--warn-execstack
