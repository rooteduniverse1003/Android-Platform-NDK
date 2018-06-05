Changelog
=========

Report issues to [GitHub].

For Android Studio issues, follow the docs on the [Android Studio site].

[GitHub]: https://github.com/android-ndk/ndk/issues
[Android Studio site]: http://tools.android.com/filing-bugs

Announcements
-------------

 * GCC has been removed.

 * [LLD](https://lld.llvm.org/) is now available for testing. AOSP is in the
   process of switching to using LLD by default and the NDK will follow
   (timeline unknown). Test LLD in your app by passing `-fuse-ld=lld` when
   linking.

 * gnustl, gabi++, and stlport have been removed.

 * Support for ICS (android-14 and android-15) has been removed. Apps using
   executables no longer need to provide both a PIE and non-PIE executable.

 * The Play Store will require 64-bit support when uploading an APK beginning in
   August 2019. Start porting now to avoid surprises when the time comes. For
   more information, see [this blog post](https://android-developers.googleblog.com/2017/12/improving-app-security-and-performance.html).

Changes
-------

 * Updated Clang to build 475164, based on r328903.
 * Added support for clang-tidy to ndk-build.
     * Enable application-wide with `APP_CLANG_TIDY := true`, or per-module with
       `LOCAL_CLANG_TIDY := true`.
     * Pass specific clang-tidy flags such as `-checks` with
       `APP_CLANG_TIDY_FLAGS` or `LOCAL_CLANG_TIDY_FLAGS`.
     * As usual, module settings override application settings.
     * By default no flags are passed to clang-tidy, so only the checks enabled
       by default in clang-tidy will be enabled. View the default list with
       `clang-tidy -list-checks`.
     * By default clang-tidy warnings are not errors. This behavior can be
       changed with `-warnings-as-errors=*`.

[clang-tidy]: http://clang.llvm.org/extra/clang-tidy/

Known Issues
------------

 * This is not intended to be a comprehensive list of all outstanding bugs.
 * [Issue 360]: `thread_local` variables with non-trivial destructors will cause
   segfaults if the containing library is `dlclose`ed on devices running M or
   newer, or devices before M when using a static STL. The simple workaround is
   to not call `dlclose`.
 * [Issue 70838247]: Gold emits broken debug information for AArch64. AArch64
   still uses BFD by default.

[Issue 360]: https://github.com/android-ndk/ndk/issues/360
[Issue 70838247]: https://issuetracker.google.com/70838247
