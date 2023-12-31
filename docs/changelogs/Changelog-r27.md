# Changelog

Report issues to [GitHub].

For Android Studio issues, follow the docs on the [Android Studio site].

If you're a build system maintainer that needs to use the tools in the NDK
directly, see the [build system maintainers guide].

[GitHub]: https://github.com/android/ndk/issues
[Android Studio site]: http://tools.android.com/filing-bugs
[build system maintainers guide]: https://android.googlesource.com/platform/ndk/+/master/docs/BuildSystemMaintainers.md

## Announcements

## Changes

* Updated LLVM to clang-r498229b. See `AndroidVersion.txt` and
  `clang_source_info.md` in the toolchain directory for version information.
* A RISC-V sysroot (AKA riscv64, or rv64) has been added. It is **not**
  supported. It is present to aid bringup for OS vendors, but it's not yet a
  supported Android ABI. It will not be built by default.

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

[Issue 360]: https://github.com/android/ndk/issues/360
