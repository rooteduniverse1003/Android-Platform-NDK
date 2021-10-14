# Changelog

Report issues to [GitHub].

For Android Studio issues, follow the docs on the [Android Studio site].

[GitHub]: https://github.com/android/ndk/issues
[Android Studio site]: http://tools.android.com/filing-bugs

## Announcements

* The GNU Assembler (GAS), has been removed. If you were building with
  `-fno-integrated-as` you'll need to remove that flag. See
  [Clang Migration Notes] for advice on making assembly compatible with LLVM.

* GDB has been removed. Use LLDB instead. Note that `ndk-gdb` uses LLDB by
  default, and Android Studio has only ever supported LLDB.

* Jelly Bean (APIs 16, 17, and 18) is no longer supported. The minimum OS
  supported by the NDK is KitKat (API level 19).

* Non-Neon devices are no longer supported. A very small number of very old
  devices do not support Neon so most apps will not notice aside from the
  performance improvement.

* RenderScript build support has been removed. RenderScript was
  [deprecated](https://developer.android.com/about/versions/12/deprecations#renderscript)
  in Android 12. If you have not finished migrating your apps away from
  RenderScript, NDK r23 LTS can be used.

[Clang Migration Notes]: ClangMigration.md

## Changes

* Includes Android 12.1 APIs.
* Updated LLVM to clang-r433403, based on LLVM 13 development.
  * [Issue 1590]: Fix LLDB help crash.
* [Issue 1559]: Added `LOCAL_ALLOW_MISSING_PREBUILT` option to
  `PREBUILT_SHARED_LIBRARY` and `PREBUILT_STATIC_LIBRARY` which defers failures
  for missing prebuilts to build time. This enables use cases within AGP where
  one module provides "pre" built libraries to another module.

[Issue 1559]: https://github.com/android/ndk/issues/1559
[Issue 1590]: https://github.com/android/ndk/issues/1590

## Known Issues

This is not intended to be a comprehensive list of all outstanding bugs.

* [Issue 360]: `thread_local` variables with non-trivial destructors will cause
  segfaults if the containing library is `dlclose`ed. This was fixed in API 28,
  but code running on devices older than API 28 will need a workaround. The
  simplest fix is to **stop calling `dlclose`**. If you absolutely must continue
  calling `dlclose`, see the following table:

  |                   | Pre-API 23           |  APIs 23-27   | API 28+ |
  | ----------------- | -------------------- | ------------- | ------- |
  | No workarounds    | Works for static STL | Broken        | Works   |
  | `-Wl,-z,nodelete` | Works for static STL | Works         | Works   |
  | No `dlclose`      | Works                | Works         | Works   |

  If your code must run on devices older than M (API 23) and you cannot use the
  static STL (common), **the only fix is to not call `dlclose`**, or to stop
  using `thread_local` variables with non-trivial destructors.

  If your code does not need to run on devices older than API 23 you can link
  with `-Wl,-z,nodelete`, which instructs the linker to ignore `dlclose` for
  that library. You can backport this behavior by not calling `dlclose`.

  The fix in API 28 is the standardized inhibition of `dlclose`, so you can
  backport the fix to older versions by not calling `dlclose`.

* [Issue 988]: Exception handling when using ASan via wrap.sh can crash. To
  workaround this issue when using libc++_shared, ensure that your application's
  libc++_shared.so is in `LD_PRELOAD` in your `wrap.sh` as in the following
  example:

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

  Note that because this is a platform bug rather than an NDK bug this cannot be
  fixed with an NDK update. This workaround will be necessary for code running
  on devices that do not contain the fix, and the bug has not been fixed even in
  the latest release of Android.

[Issue 360]: https://github.com/android/ndk/issues/360
[Issue 988]: https://github.com/android/ndk/issues/988
