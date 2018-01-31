def build_unsupported(abi, platform):
    if platform < 21:
        return platform
    return None
