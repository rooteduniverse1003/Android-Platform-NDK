def build_unsupported(abi, platform):
    if abi != 'arm64-v8a':
        return abi
    return None
