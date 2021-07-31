# Changelog

Report issues to [GitHub].

For Android Studio issues, follow the docs on the [Android Studio site].

[GitHub]: https://github.com/android/ndk/issues
[Android Studio site]: http://tools.android.com/filing-bugs

## Announcements

* GNU binutils, excluding the GNU Assembler (GAS), has been removed. GAS will be
  removed in the next release. If you are building with `-fno-integrated-as`,
  file bugs if anything is preventing you from removing that flag.

* Support for GDB has ended. GDB will be removed from the next release. Use LLDB
  instead. Note that `ndk-gdb` uses LLDB by default.

* NDK r23 is the last release that will support non-Neon. Beginning with NDK
  r24, the armeabi-v7a libraries in the sysroot will be built with Neon. A very
  small number of very old devices do not support Neon so most apps will not
  notice aside from the performance improvement.

* Jelly Bean (APIs 16, 17, and 18) will not be supported in the next NDK
  release. The minimum OS supported by the NDK for r24 will be KitKat (API level
  19).

## Changes

* Includes Android 12 APIs.
* Updated LLVM to clang-r416183b, based on LLVM 12 development.
  * [Issue 1047]: Fixes crash when using ASan with the CFI unwinder.
  * [Issue 1096]: Includes support for [Polly]. Enable by adding `-mllvm -polly`
    to your cflags.
  * [Issue 1230]: LLVM's libunwind is now used instead of libgcc for all
    architectures rather than just 32-bit Arm.
  * [Issue 1231]: LLVM's libclang_rt.builtins is now used instead of libgcc.
  * [Issue 1406]: Fixes crash with Neon intrinsic.
* Vulkan validation layer source and binaries are no longer shipped in the NDK.
  The latest are now posted directly to [GitHub](https://github.com/KhronosGroup/Vulkan-ValidationLayers/releases).
* Vulkan tools source is also removed, specifically vulkan_wrapper.
  It should be downloaded upstream from [GitHub](https://github.com/KhronosGroup/Vulkan-Tools).
* The toolchain file (android.toolchain.cmake) is refactored to base on CMake's
  integrated Android support. This new toolchain file will be enabled by default
  for CMake 3.21 and newer. No user side change is expected. But if anything goes
  wrong, please file a bug and set `ANDROID_USE_LEGACY_TOOLCHAIN_FILE=ON` to
  restore the legacy behavior.
    * When using the new behavior (when using CMake 3.21+ and not explicitly
      selecting the legacy toolchain), **default build flags may change**. One
      of the primary goals was to reduce the behavior differences between our
      toolchain and CMake, and CMake's default flags do not always match the
      legacy toolchain file. Most notably, if using `CMAKE_BUILD_TYPE=Release`,
      your optimization type will likely be `-O3` instead of `-O2` or `-Oz`. See
      [Issue 1536] for more information.
* [Issue 929]: `find_library` now prefers shared libraries from the sysroot over
  static libraries.
* [Issue 1390]: ndk-build now warns when building a static executable with the
  wrong API level.
* [Issue 1452]: `NDK_ANALYZE=1` now sets `APP_CLANG_TIDY=true` rather than using
  scan-build. clang-tidy performs all the same checks by default, and scan-build
  was no longer working. See the bug for more details, but no user-side changes
  should be needed.

[Issue 929]: https://github.com/android/ndk/issues/929
[Issue 1047]: https://github.com/android/ndk/issues/1047
[Issue 1096]: https://github.com/android/ndk/issues/1096
[Issue 1230]: https://github.com/android/ndk/issues/1230
[Issue 1231]: https://github.com/android/ndk/issues/1231
[Issue 1390]: https://github.com/android/ndk/issues/1390
[Issue 1406]: https://github.com/android/ndk/issues/1406
[Issue 1452]: https://github.com/android/ndk/issues/1452
[Issue 1536]: https://github.com/android/ndk/issues/1536
[Polly]: https://polly.llvm.org/

## Known Issues

* This is not intended to be a comprehensive list of all outstanding bugs.
* [Issue 360]: `thread_local` variables with non-trivial destructors will cause
  segfaults if the containing library is `dlclose`ed on devices running M or
  newer, or devices before M when using a static STL. The simple workaround is
  to not call `dlclose`.
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
      # Workaround for https://github.com/android/ndk/issues/988.
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

[Issue 360]: https://github.com/android/ndk/issues/360
[Issue 906]: https://github.com/android/ndk/issues/906
[Issue 988]: https://github.com/android/ndk/issues/988
