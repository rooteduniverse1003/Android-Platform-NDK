def extra_cmake_flags():
    return ['-DANDROID_PLATFORM=android-24']


def build_unsupported(abi, _api):
    if '64' in abi:
        return abi
    return None
