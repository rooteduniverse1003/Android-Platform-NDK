def build_unsupported(test):
    if test.config.abi not in ('armeabi-v7a', 'x86'):
        return test.config.abi
    return None
