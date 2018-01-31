def build_unsupported(abi, platform):
    # Vulkan support wasn't added until android-24
    if platform < 24:
        return platform

    return None
