def build_unsupported(abi, device):
    if abi != 'armeabi-v7a':
        return abi
    return None
