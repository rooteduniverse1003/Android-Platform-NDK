def build_unsupported(abi, platform):
    if abi == 'x86' and platform < 17:
        return abi
    return None
