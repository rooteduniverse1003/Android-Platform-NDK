def is_negative_test():
    return True


def extra_cmake_flags():
    return ['-DANDROID_PLATFORM=android-21']


def build_unsupported(abi, _api):
    if '64' in abi:
        return abi
    return None
