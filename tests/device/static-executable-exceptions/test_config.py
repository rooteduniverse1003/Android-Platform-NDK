def build_unsupported(test):
    # Static executables with libc++ require targeting a new enough API level
    # to not need libandroid_support.
    if test.config.api < 21:
        return f"android-{test.config.api}"

    return None
