def is_negative_test():
    return True


def extra_cmake_flags():
    return ['-DANDROID_PLATFORM=android-19']


def build_unsupported(test):
    if '64' in test.config.abi:
        return test.config.abi
    return None
