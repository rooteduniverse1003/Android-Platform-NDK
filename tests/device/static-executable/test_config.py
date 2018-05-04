def extra_cmake_flags():
    # Match the ndk-build test. Using libc++ here would require us to target a
    # newer API level since static executables and libandroid_support don't
    # mix.
    return ['-DANDROID_STL=system']
