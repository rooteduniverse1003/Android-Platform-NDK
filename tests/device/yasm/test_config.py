def build_unsupported(abi, platform):
    if abi not in ('x86', 'x86_64'):
        return abi
    return None
