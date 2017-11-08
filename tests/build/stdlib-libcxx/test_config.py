def extra_cmake_flags():
    return ['-DANDROID_STL=c++_static']


def build_unsupported(_abi, _api, toolchain):
    # -stdlib is a Clang specific argument.
    if toolchain != 'clang':
        return toolchain
    return None
