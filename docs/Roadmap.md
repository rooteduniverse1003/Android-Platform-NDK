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

## NDK r18

Estimated release: Q3 2018

### Remove non-libc++ STLs

libc++ has been the default for a release and has proven to be stable. It is a
strict improvement over the other STLs (more features, better Clang
compatibility, Apache licensed, most reliable). The fact that the NDK supports
multiple STLs is a common pain point for users (it's confusing for newcomers,
and it makes sharing libraries difficult because they must all use the same
STL).

Now that we have a good choice for a single STL, we'll remove the others. We'll
most likely move the source we have for these along with building instructions
to a separate project so that people that need these for ABI compatibility
reasons can continue using them, but support for these will end completely.

### Remove GCC

GCC is still in the NDK today because some of gnustl's C++11 features were
written such that they do not work with Clang (threading and atomics, mostly).
Now that libc++ is the best choice of STL, this is no longer blocking, so GCC
can be removed.

### Bugfix Release

The updated clang and libc++ in r18 address many outstanding issues.


## NDK r19

Estimated release: Q4 2018

### Make standalone toolchains obsolete

Now that the NDK is down to a single compiler and STL, if we just taught the
Clang driver to emit `-D__ANDROID_API__=foo` and to link libc.so.18 instead of
libc.so, standalone toolchains would be obsolete because the compiler would
already be a standalone toolchain. The NDK toolchain would Just Work regardless
of build system, and the logic contained in each build system could be greatly
reduced.

Related to this (but maybe occurring in a later release), we'll want to
switch from `libgcc` to `libcompiler-rt` and our own unwinder.

## NDK r20

Estimated release: Q4 2018

To be decided...

---

## Future work

### Better code-completion support

NDK r17 added names for all function arguments, but tools such as vim
and Visual Studio Code need a `compile_commands.json` file.

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

vim is ready, Android Studio is almost ready bar one bug
(https://issuetracker.google.com/110556794), and Visual Studio Code
has nothing but feature requests.

### Better samples

The samples are low-quality and don't necessarily cover
interesting/difficult topics.

### Better tools for improving code quality.

The NDK has long included `gtest` and clang supports various sanitiziers,
but there are things we can do to improve the state of testing/code quality:

 * Test coverage support.
 * Make the [GTest-as-JUnit] wrapper available to developers so developers can
   integrate their C++ tests into Studio.

[GTest-as-JUnit]: https://android-review.googlesource.com/c/platform/cts/+/683355

### Easier access to common open-source libraries

There are many other commonly-used libraries (such as Curl and BoringSSL)
that are currently difficult to build/package, let alone keep updated. We
should investigate using something like [cdep] to simplify this.

[cdep]: https://github.com/jomof/cdep

### lld linker

We should make lld available in the NDK, with a view to making it the
default (as it already is in the platform), and long-term towards shipping
lld as our _only_ linker. https://github.com/android-ndk/ndk/issues/683

### lldb debugger

We should make lldb available in the NDK. It's currently shipped as part
of Studio.

### Modules

Are modules useful and is the clang implementation complete enough? How do
we test? Is this only useful for libc/libm/libdl or for the NDK API too?

### NDK API header-only C++ wrappers

NDK APIs are C-only for ABI stability reasons. We should offer header-only
C++ wrappers for NDK APIs, even if only to offer the benefits of RAII.

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

### Unify CMake NDK Support Implementations

CMake added their own NDK support about the same time we added our
toolchain file. The two often conflict with each other, and a toolchain
file is a messy way to implement this support. However, fully switching to
the integrated support puts NDK policy deicisions (default options, NDK
layout, etc) fully into the hands of CMake, which makes them impossible
to update without the user also updating their CMake version.

We should send patches to the CMake implementation that will load as much
information about the NDK as possible from tables we provide in the NDK.

---

## Historical releases

Full [history] is available, but this section summarizes major changes
in recent releases.

[history]: https://developer.android.com/ndk/downloads/revision_history.html

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
