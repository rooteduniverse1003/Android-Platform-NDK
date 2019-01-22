def build_unsupported(test):
    # Major build time regression.
    return True
    # pylint: disable=unreachable

    # Vulkan support wasn't added until android-24
    if test.config.api < 24:
        return test.config.api

    return None
