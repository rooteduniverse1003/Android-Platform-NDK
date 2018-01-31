def build_unsupported(abi, _platform):
    if abi != 'armeabi-v7a':
        return abi
    return 'clang'
