# NDK Roadmap

**Note**: If there's anything you want to see done in the NDK, [file a bug]!
Nothing here is set in stone, and if there's something that we haven't thought
of that would be of more use, we'd be happy to adjust our plans for that.

[file a bug]: https://github.com/android-ndk/ndk/issues

**Disclaimer**: Everything here is subject to change. The further the plans are
in the future, the less stable they will be. Things in the upcoming release are
fairly certain, and the second release is quite likely. Beyond that, anything
written here is what we would like to accomplish in that release assuming things
have gone according to plan until then.

**Note**: For release timing, see our [release schedule] on our wiki.

[release schedule]: https://github.com/android-ndk/ndk/wiki#release-schedule

---

## Regular maintenance

Every NDK release aims to include a new toolchain, new headers, and a new
version of libc++.

We also maintain [GitHub Projects](https://github.com/android/ndk/projects)
to track the bugs we intend to fix in any given NDK release.

### Toolchain updates

The NDK and the Android OS use the same toolchain. Android's toolchain team is
constantly working on updating to the latest upstream LLVM for the OS. It can
take a long time to investigate issues when compiling -- or issues that the
newer compiler finds in -- OS code or OEM code, for all 4 supported
architectures, so these updates usually take a few months.

Even then, a new OS toolchain may not be good enough for the NDK. In the OS, we
can work around compiler bugs by changing our code, but for the NDK we want to
make compiler updates cause as little disruption as possible. We also don't want
to perform a full compiler update late in the NDK release cycle for the sake of
stability.

The aim is that each NDK will have a new toolchain that's as up to date as
feasible without sacrificing stability, but we err on the side of stability when
we have to make a choice. If an NDK release doesn't include a new compiler, or
that compiler isn't as new as you'd hoped, trust us --- you wouldn't want
anything newer that we have just yet!

## Current work

Most of the team's work is currently focused outside the NDK proper, so while
the NDK release notes may seem a bit sparse, there are still plenty of
improvements coming for NDK users:

* Improving NDK and Android Gradle Plugin documentation.
* Improving the OS (in particular the linker).
* Working with the Android frameworks teams to get new NDK APIs.
* Improving tooling for third-party packages via ndkports:
  * Auto-update packages
  * Automated testing
  * More packages
* Workflow improvements to decrease the costs of regular maintenance.

### Apple M1

https://github.com/android/ndk/issues/1299

Migration of all the tools involved in an NDK build to be fat binaries will land
over the course of a few releases. LLVM was shipped as universal binaries in
r23b, and the rest of the tools are expected to move in r24. Further backports
to r23 are unclear because they may risk destabilizing the release.

### TSan

https://github.com/android/ndk/issues/1041

Port thread sanitizer for use with NDK apps, especially in unit/integration
tests.

### Testing tools

Add [GTestJNI] to Jetpack to allow exposing native tests to AGP as JUnit tests.

[GTestJNI]: https://github.com/danalbert/GTestJNI

### More automated libc++ updates

We still need to update libc++ twice: once for the platform, and once
for the NDK. We also still have two separate test runners. We're consolidating
all of these in one place (the toolchain) so that all LLVM updates include
libc++ updates.

### Jetpack

We're working with the Jetpack team to build the infrastructure needed to start
producing C++ Jetpack libraries. Once that's done we can start using Jetpack to
ship helper libraries like libnativehelper, or C++ wrappers for the platform's C
APIs. Wrappers for NDK APIs would also be able to, in some cases, backport
support for APIs to older releases.

## Future work

The following projects are listed in order of their current priority.

Note that some of these projects do not actually affect the contents of the NDK
package. The samples, documentation, etc are all NDK work but are separate from
the NDK package. As such they will not appear in any specific release, but are
noted here to show where the team's time is being spent.

---

## Unscheduled Work

The following projects are things we intend to do, but have not yet been
scheduled into the sections above.

### Improve automation in ndkports so we can take on more packages

Before we can take on maintenance for additional packages we need to improve the
tooling for ndkports. Automation for package updates, testing, and the release
process would make it possible to expand.

### Better documentation

We should probably add basic doc comments to the bionic headers:

* One-sentence summary.
* One paragraph listing any Android differences. (Perhaps worth upstreaming this
  to man7.org too.)
* Explain any "flags" arguments (at least giving some idea of which flags)?
* Explain the return value: what does a `char*` point to? Who owns it? Are
  errors -1 (as for most functions) or `<errno.h>` values (for
  `pthread_mutex_lock`)?
* A "See also" pointing to man7.org?

Should these be in the NDK API reference too? If so, how will we keep
them from swamping the "real" NDK API?

vim is ready, Android Studio now supports doxygen comments (but seems
to have gained a new man page viewer that takes precedence),
and Visual Studio Code has nothing but feature requests.

Beyond writing the documentation, we also should invest some time in improving
the presentation of the NDK API reference on developer.android.com.

### Better samples

The samples are low-quality and don't necessarily cover interesting/difficult
topics.

### Better tools for improving code quality

The NDK has long included `gtest` and clang supports various sanitiziers,
but there are things we can do to improve the state of testing/code quality:

* Test coverage support.

### C++ wrappers for NDK APIs

NDK APIs are C-only for ABI stability reasons.

We should offer C++ wrappers as part of an NDK support library (possibly as part
of Jetpack), even if only to offer the benefits of RAII.  Examples include
[Bitmap](https://github.com/android-ndk/ndk/issues/822),
[ATrace](https://github.com/android-ndk/ndk/issues/821), and
[ASharedMemory](https://github.com/android-ndk/ndk/issues/820).

### JNI helpers

Complaints about basic JNI handling are common. We should make libnativehelper
available as an AAR.

### NDK icu4c wrapper

For serious i18n, `icu4c` is too big too bundle, and non-trivial to use
the platform. We have a C API wrapper prototype, but we need to make it
easily available for NDK users.

### Weak symbols for API additions

iOS developers are used to using weak symbols to refer to function that
may be present in their equivalent of `targetSdkVersion` but not in their
`minSdkVersion`. We could potentially do something similar. See
[issue 1003](https://github.com/android-ndk/ndk/issues/1003).

### Make the sysroot a separately installable SDK package

The sysroot in the NDK is currently inherently a part of the NDK because it
includes libc++ as well as some versioned artifacts like the CRT objects (with
the ELF note identifying the NDK version that produced them) and
`android/ndk-version.h`. Moving libc++ to the toolchain solves that coupling,
and the others are probably tractable.

While we'd always include the latest stable sysroot in the NDK toolchain so that
it works out of the box, allowing the sysroot to be provided as a separate SDK
package makes it easier for users to get new APIs without getting a new
toolchain (via `compileSdkVersion` the same way it works for Java) and also
easier for us to ship sysroot updates for preview API levels because they would
no longer require a full NDK release.

### LSan

Leak sanitizer has not been ported for use with Android apps but would be
helpful to app developers in tracking down memory leaks.

### Portable NDK

The Linux NDK is currently dependent on the version of glibc it was built with.
To keep the NDK compatible with as many distributions as possible we build
against a very old version of glibc, but there are still distros that we are
incompatible with (especially distros that use an alternative libc!). We could
potentially solve this by statically linking all our dependencies and/or by
switching from glibc to musl. Not all binaries can be static executables because
they require dlopen for plugin interfaces (even if our toolchain doesn't
currently attempt to support user-provided compiler plugins, Polly is
distributed this way, and we may want to offer such support in the future) so
there are still some open questions.

### rr debugger

https://rr-project.org/ is a C/C++ debugger that supports replay debugging. We
should investigate what is required to support that for Android.

---

## Historical releases

Full [history] is available, but this section summarizes major changes
in recent releases.

[history]: https://developer.android.com/ndk/downloads/revision_history.html

### NDK r25

Significantly reduced the size of the NDK. Reverted to older CMake toolchain
behavior to improve build reliability.

### NDK r24

Neon is now enabled for all armeabi-v7a libraries, improving performance for
those apps, but dropping Tegra 2 support as a result. Removed support for
building RenderScript, which was deprecated in Android 12. Removed obsolete GNU
assembler and GDB. Minimum OS support raised to API 19.

### NDK r23

Migrated all ABIs from libgcc to the LLVM unwinder and libclang_rt. Finished
migration to LLVM binutils from GNU binutils (with the exception of `as`, which
remains for one more release). Integrated upstream and NDK CMake support.

### NDK r22

Updated toolchain and libc++. libc++ now supports `std::filesystem`. Make
updated to 4.3. LLDB included and usable (via `--lldb`) with ndk-gdb. Replaced
remaining GNU binutils tools with LLVM tools, deprecated GNU binutils. LLD is
now the default.

### Package management

We shipped [Prefab] and the accompanying support for the Android Gradle Plugin
to support native dependencies. AGP 4.0 includes the support for importing these
packages, and 4.1 includes the support for creating AARs that support them.

We also maintain a few packages as part of [ndkports]. Currently curl, OpenSSL,
JsonCpp, and GoogleTest (includes GoogleMock).

[Prefab]: https://github.com/google/prefab
[ndkports]: https://android.googlesource.com/platform/tools/ndkports/

### NDK r21 LTS

Updated Clang, LLD, libc++, make, and GDB. Much better LLD behavior on Windows.
32-bit Windows support removed. Neon by default for all API levels. OpenMP now
available as both a static and shared library.

### NDK r20

Updated Clang and libc++, added Q APIs. Improved out-of-the-box Clang behavior.

### NDK r19

Reorganized the toolchain packaging and modified Clang so that standalone
toolchains are now unnecessary. Clang can now be invoked directly from its
installed location in the NDK.

C++ compilation defaults to C++14.

### NDK r18

Removed GCC and gnustl/stlport. Added lld.

Added `compile_commands.json` for better tooling support.

### NDK r17

Defaulted to libc++.

Removed ARMv5 (armeabi), MIPS, and MIPS64.

### NDK r16

Fixed libandroid\_support, libc++ now the recommended STL (but still
not the default).

Removed non-unified headers.

### NDK r15

Defaulted to [unified headers] (opt-out).

Removed support for API levels lower than 14 (Android 4.0).

### NDK r14

Added [unified headers] (opt-in).

[unified headers]: https://android.googlesource.com/platform/ndk/+/master/docs/UnifiedHeaders.md

### NDK r13

Added [simpleperf].

[simpleperf]: https://developer.android.com/ndk/guides/simpleperf.html

### NDK r12

Removed [armeabi-v7a-hard].

Removed support for API levels lower than 9 (Android 2.3).

[armeabi-v7a-hard]: https://android.googlesource.com/platform/ndk/+/ndk-r12-release/docs/HardFloatAbi.md
