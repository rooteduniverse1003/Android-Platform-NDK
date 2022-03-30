def build_broken(test):
    if (
        test.case_name == "dereference.runtime.fail"
        or test.case_name == "op_arrow.runtime.fail"
    ):
        # This is XFAIL: clang and libc++ are out of sync.
        return "all", "https://github.com/android/ndk/issues/1530"
    return None, None
