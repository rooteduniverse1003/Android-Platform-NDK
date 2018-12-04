# Android Native Development Kit (NDK)

The latest version of this document is available at
https://android.googlesource.com/platform/ndk/+/master/README.md.

**Note:** This document is for developers _of_ the NDK, not developers that use
the NDK.

The NDK allows Android application developers to include native code in their
Android application packages, compiled as JNI shared libraries.

This page provides an overview of what is contained in the NDK. For
information on building or testing the NDK, the roadmap, or other information,
see the navigation bar at the top of this page, or the [docs directory].

[docs directory]: docs/

[TOC]

## Other Resources

 * User documentation is available on the [Android Developer website].
 * Discussions related to the Android NDK happen on the [android-ndk Google
   Group].
 * Announcements such as releases are posted to the [android-ndk-announce Google
   Group].
 * File bugs against the NDK at https://github.com/android-ndk/ndk/issues.

[Android Developer website]: https://developer.android.com/ndk/index.html
[android-ndk Google Group]: http://groups.google.com/group/android-ndk
[android-ndk-announce Google Group]: http://groups.google.com/group/android-ndk-announce

## Components

The NDK components can be loosely grouped into host toolchains, target
prebuilts, build systems, and support libraries.

For more information, see the [Build System Maintainers] guide.

[Build System Maintainers]: docs/BuildSystemMaintainers.md

### Build Systems

While the NDK is primarily a toolchain for building Android code, the package
also includes some build system support.

First, `$NDK/build/core` contains ndk-build. This is the NDK's home grown build
system. The entry point for this build system is `$NDK/build/ndk-build` (or
`$NDK/build/ndk-build.cmd`).

A CMake toolchain file is included at
`$NDK/build/cmake/android.toolchain.cmake`. This is separate from CMake's own
support for the NDK.

`$NDK/build/tools/make_standalone_toolchain.py` is a tool which can create a
redistributable toolchain that targets a single Android ABI and API level. As of
NDK r19 it is necessary, as the installed toolchain may be invoked directly, but
it remains for compatibility.

Since the Android Gradle plugin is responsible for both Java and native code, is
not included as part of the NDK.

### Support Libraries

`sources/android` and `sources/third_party` contain modules that can be used in
apps (gtest, cpufeatures, native\_app\_glue, etc) via `$(call
import-module,$MODULE)` in ndk-build. CMake modules are not yet available.
