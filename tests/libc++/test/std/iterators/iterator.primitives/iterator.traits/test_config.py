def build_broken(test):
    if test.case_name == "empty.fail":
        # Format of the diagnostic changed in clang and we don't have the
        # libc++ update to match (https://reviews.llvm.org/D92239).
        return "all", "https://github.com/android/ndk/issues/1454"
    return None, None
