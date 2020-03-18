# Changelog

Report issues to [GitHub].

For Android Studio issues, follow the docs on the [Android Studio site].

[GitHub]: https://github.com/android-ndk/ndk/issues
[Android Studio site]: http://tools.android.com/filing-bugs

## Announcements

* [LLD](https://lld.llvm.org/) is now the default linker. Gold and BFD will
  likely be removed in the next LTS release (Q3-Q4 2020). See the Changes
  section below for more information.

* [Issue 843]: Build system maintainers should begin testing with LLVM's
  binutils. Android has switched to using these by default (with the exception
  of llvm-ar, as we're still investigating some issues on macOS), and GNU
  binutils will likely be removed in the next LTS release (Q3-Q4 2020).

## Changes

* [Issue 843]: `llvm-strip` is now used instead of `strip` to avoid breaking
   RelRO with LLD. Note that the Android Gradle Plugin performs its own
   stripping, so most users will need to upgrade to Android Gradle Plugin
   version 4.0 or newer to get the fix.

* [Issue 1139]: `native_app_glue` now hooks up the `APP_CMD_WINDOW_RESIZED`,
  `APP_CMD_WINDOW_REDRAW_NEEDED`, and `APP_CMD_CONTENT_RECT_CHANGED` messages.

* The deprecated `<NDK>/platforms` and `<NDK>/sysroot` directories have been
  removed. These directories were merged and relocated into the toolchain during
  r19. The location of these contents should not be relevant to anyone,
  including build systems, since the toolchain handles them implicitly. If you
  are using a build system that hasn't adapted to the changes introduced in NDK
  r19, file a bug with your build system maintainer. See the [Build System
  Maintainers Guide] for information on using the NDK in your own build system.

* LLD is now used by default. If your build is not yet compatible with LLD, you
  can continue using the deprecated linkers, set `APP_LD=deprecated` for
  ndk-build, `ANDROID_LD=deprecated` for CMake, or use an explicit
  `-fuse-ld=gold` or `-fuse-ld=bfd` in your custom build system. If you
  encounter issues be sure to file a bug, because this will not be an option in
  a subsequent release.

  Note that [Issue 843] will affect builds using LLD with binutils strip and
  objcopy as opposed to llvm-strip and llvm-objcopy.

[Build System Maintainers Guide]: https://android.googlesource.com/platform/ndk/+/master/docs/BuildSystemMaintainers.md

## Known Issues

* This is not intended to be a comprehensive list of all outstanding bugs.
* [Issue 360]: `thread_local` variables with non-trivial destructors will cause
  segfaults if the containing library is `dlclose`ed on devices running M or
  newer, or devices before M when using a static STL. The simple workaround is
  to not call `dlclose`.
* [Issue 70838247]: Gold emits broken debug information for AArch64. AArch64
  still uses BFD by default.
* [Issue 906]: Clang does not pass `-march=armv7-a` to the assembler when using
  `-fno-integrated-as`. This results in the assembler generating ARMv5
  instructions. Note that by default Clang uses the integrated assembler which
  does not have this problem. To workaround this issue, explicitly use
  `-march=armv7-a` when building for 32-bit ARM with the non-integrated
  assembler, or use the integrated assembler. ndk-build and CMake already
  contain these workarounds.
* [Issue 906]: Clang does not pass `-march=armv7-a` to the assembler when using
  `-fno-integrated-as`. This results in the assembler generating ARMv5
  instructions. Note that by default Clang uses the integrated assembler which
  does not have this problem. To workaround this issue, explicitly use
  `-march=armv7-a` when building for 32-bit ARM with the non-integrated
  assembler, or use the integrated assembler. ndk-build and CMake already
  contain these workarounds.
* [Issue 988]: Exception handling when using ASan via wrap.sh can crash. To
  workaround this issue when using libc++_shared, ensure that your
  application's libc++_shared.so is in `LD_PRELOAD` in your `wrap.sh` as in the
  following example:

  ```bash
  #!/system/bin/sh
  HERE="$(cd "$(dirname "$0")" && pwd)"
  export ASAN_OPTIONS=log_to_syslog=false,allow_user_segv_handler=1
  ASAN_LIB=$(ls $HERE/libclang_rt.asan-*-android.so)
  if [ -f "$HERE/libc++_shared.so" ]; then
      # Workaround for https://github.com/android-ndk/ndk/issues/988.
      export LD_PRELOAD="$ASAN_LIB $HERE/libc++_shared.so"
  else
      export LD_PRELOAD="$ASAN_LIB"
  fi
  "$@"
   ```

  There is no known workaround for libc++_static.

  Note that because this is a platform bug rather than an NDK bug this
  workaround will be necessary for this use case to work on all devices until
  at least Android R.
* This version of the NDK is incompatible with the Android Gradle plugin
  version 3.0 or older. If you see an error like
  `No toolchains found in the NDK toolchains folder for ABI with prefix: mips64el-linux-android`,
  update your project file to [use plugin version 3.1 or newer]. You will also
  need to upgrade to Android Studio 3.1 or newer.
* [Issue 843]: Using LLD with binutils `strip` or `objcopy` breaks RelRO. Use
   `llvm-strip` and `llvm-objcopy` instead. This issue has been resolved in
   Android Gradle Plugin version 4.0 (for non-Gradle users, the fix is also in
   ndk-build and our CMake toolchain file), but may affect other build systems.

[Issue 360]: https://github.com/android-ndk/ndk/issues/360
[Issue 70838247]: https://issuetracker.google.com/70838247
[Issue 843]: https://github.com/android-ndk/ndk/issues/843
[Issue 906]: https://github.com/android-ndk/ndk/issues/906
[Issue 988]: https://github.com/android-ndk/ndk/issues/988
[Issue 1139]: https://github.com/android-ndk/ndk/issues/1139
[use plugin version 3.1 or newer]: https://developer.android.com/studio/releases/gradle-plugin#updating-plugin
