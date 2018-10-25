def build_unsupported(_abi, platform):
    # Major build time regression.
    return True
    # pylint: disable=unreachable

    # Vulkan support wasn't added until android-24
    if platform < 24:
        return platform

    return None
