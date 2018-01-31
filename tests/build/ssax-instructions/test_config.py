def build_unsupported(abi, platform):
    if abi != 'armeabi-v7a':
        return abi
    return None
