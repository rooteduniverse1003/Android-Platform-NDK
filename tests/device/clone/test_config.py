def build_unsupported(test):
    if test.config.abi == "x86" and test.config.api < 17:
        return test.config.abi
    return None
