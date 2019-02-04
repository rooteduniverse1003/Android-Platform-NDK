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

## NDK r20

Estimated release: Q1 2019

### Iterate on r19 toolchain improvements

r19 covers the bulk of the work, but there are still a handful of flags required
for building Android that should be lifted into the Clang driver. See [Issue
812] for more information.

[Issue 812]: https://github.com/android-ndk/ndk/issues/812

### Default to lld (tentative)

NDK r18 [made lld available](https://github.com/android-ndk/ndk/issues/683), r19
encourages its use, and r20 will make it the default assuming there are no
unresolved issues turned up in r19.

### Bugs

See the [r20 hotlist](https://github.com/android-ndk/ndk/milestone/16).

## NDK r21

Estimated release: Q2 2019

### Remove gold and bfd (tentative)

If r20 was able to switch the default to lld and no major unresolved issues
remained, we should remove gold and bfd.

### Bugs

See the [r21 hotlist](https://github.com/android-ndk/ndk/milestone/20).

---

## Future work

The following projects are listed in order of their current priority.

Note that some of these projects do not actually affect the contents of the NDK
package.  The samples, cdep, documentation, etc are all NDK work but are
separate from the NDK package. As such they will not appear in any specific
release, but are noted here to show where the team's time is being spent.

### Easier access to common open-source libraries

There are many other commonly-used libraries (such as Curl and BoringSSL)
that are currently difficult to build/package, let alone keep updated. We
should offer (a) a tool to build open source projects, (b) a repository
of prebuilts, (c) a command-line tool to add prebuilts to an ndk-build/cmake
project, and (d) Studio integration to add prebuilts via a GUI.

We currently have [cdep](https://github.com/google/cdep), but it doesn't have a
very large corpus and could use some build system integration polish. If not
cdep, adding support for exposing native libraries from AARs would be an
alternative.

### C++ File System API

[Issue 609](https://github.com/android-ndk/ndk/issues/609)

We don't currently build, test, or ship libc++'s std::filesystem. Until recently
this API wasn't final, but now is at least a stable API (though it sounds like
the ABI will change in the near future).

There's a fair amount of work involved in getting these tests running, but
that's something we should do.

### CMake

CMake added their own NDK support about the same time we added our
toolchain file. The two often conflict with each other, and a toolchain
file is a messy way to implement this support. However, fully switching to
the integrated support puts NDK policy decisions (default options, NDK layout,
etc) fully into the hands of CMake, which makes them impossible to update
without the user also updating their CMake version.

We will reorganize our toolchain file to match the typical implementation of a
CMake platform integration (like `$CMAKE/Modules/Platform/Android-*.cmake`) and
CMake will be modified to load the implementation from the NDK rather than its
own.

See [Issue 463](https://github.com/android-ndk/ndk/issues/463) for discussion.

### Weak symbols for API additions

iOS developers are used to using weak symbols to refer to function that
may be present in their equivalent of `targetSdkVersion` but not in their
`minSdkVersion`. They use a run-time null check to decide whether the
new function is available or not. Apparently clang also has some support
for emitting a warning if you dereference one of these symbols without
a corresponding null check.

This seems like a more convenient option than is currently available
on Android, especially since no currently shipping version of Android
includes a function to check which version of Android you're running on.

We might not want to make this the default (because it's such a break
with historical practice, and might be surprising), but we should offer
this as an option.

An interesting technical problem here will be dealing with the `DT_NEEDED`
situation for "I need this library (but it might not exist yet)".

### C++ Modules

By Q2 2019 Clang may have a complete enough implementation of the modules TS and
Android may have a Clang with those changes available.

At least for the current spec (which is in the process of merging with the Clang
implementation, so could change), the NDK will need to:

 1. Support compiling module interfaces.
 2. Support either automated discovery (currently very messy) or specification
    of module dependencies.
 3. Begin creating module interfaces for system libraries. Frameworks, libc,
    libc++, etc.

---

## Unscheduled Work

The following projects are things we intend to do, but have not yet been
sheduled into the sections above.

### Better documentation

We should probably add basic doc comments to the bionic headers:

  * One-sentence summary.
  * One paragraph listing any Android differences. (Perhaps worth
    upstreaming this to man7.org too.)
  * Explain any "flags" arguments (at least giving some idea of which flags)?
  * Explain the return value: what does a `char*` point to? Who owns
    it? Are errors -1 (as for most functions) or `<errno.h>` values (for
    `pthread_mutex_lock`)?
  * A "See also" pointing to man7.org?

Should these be in the NDK API reference too? If so, how will we keep
them from swamping the "real" NDK API?

vim is ready, Android Studio now supports doxygen comments (but seems
to have gained a new man page viewer that takes precedence),
and Visual Studio Code has nothing but feature requests.

### Better samples

The samples are low-quality and don't necessarily cover interesting/difficult
topics.

### Better tools for improving code quality.

The NDK has long included `gtest` and clang supports various sanitiziers,
but there are things we can do to improve the state of testing/code quality:

 * Test coverage support.
 * Add `gmock`.
 * Make [GTestJNI] available to developers via some some package manager so
   developers can integrate their C++ tests into Studio.

[GTestJNI]: https://github.com/danalbert/GTestJNI

### lldb debugger

We should make lldb available in the NDK. It's currently shipped as part
of Studio. Medium-term we should have Studio ship our lldb. Long-term Studio
should probably use the NDK lldb directly.

### NDK API header-only C++ wrappers

NDK APIs are C-only for ABI stability reasons. We should offer header-only
C++ wrappers for NDK APIs, even if only to offer the benefits of RAII.
Examples include [Bitmap](https://github.com/android-ndk/ndk/issues/822),
[ATrace](https://github.com/android-ndk/ndk/issues/821), and
[ASharedMemory](https://github.com/android-ndk/ndk/issues/820).

### NDK C++ header-only JNI helpers

Complaints about basic JNI handling are common. We should make libnativehelper
or something similar available to developers.

### NDK icu4c wrapper

For serious i18n, `icu4c` is too big too bundle, and non-trivial to use
the platform. We have a C API wrapper prototype, but we need to make it
easily available for NDK users.

### More automated libc++ updates

We still need to update libc++ twice: once for the platform, and once
for the NDK. We also still have two separate test runners.

---

## Historical releases

Full [history] is available, but this section summarizes major changes
in recent releases.

[history]: https://developer.android.com/ndk/downloads/revision_history.html

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
