def build_broken(test):
    if (
        test.case_name == "const_correctness.fail"
        or test.case_name == "not_copy_constructible.fail"
    ):
        # This is XFAIL: clang and libc++ are out of sync.
        return "all", "https://github.com/android/ndk/issues/1530"
    return None, None
