def build_unsupported(abi, _platform):
    if abi == 'x86':
        return abi
    return None


def run_unsupported(_abi, device_api, _subtest):
    if device_api < 19:
        return device_api
    return None


def run_broken(abi, _device_api, _subtest):
    if abi == 'x86':
        return abi, 'http://b.android.com/230369'
    return None, None
