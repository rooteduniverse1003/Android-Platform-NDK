def build_broken(test):
    return 'all', 'https://github.com/android/ndk/issues/1171'

def run_unsupported(test, device):
    if test.config.is_lp32:
        return test.config.abi
    return None
