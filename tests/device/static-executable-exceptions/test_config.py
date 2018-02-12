def build_unsupported(_abi, api):
    # Static executables with libc++ require targeting a new enough API level
    # to not need libandroid_support.
    if api < 21:
        return 'android-{}'.format(api)

    return None
