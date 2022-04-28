def build_unsupported(test):
    if test.config.is_lp32:
        return test.config.abi
    return None


def run_broken(test, device):
    return "all", "https://github.com/android/ndk/issues/1171"
