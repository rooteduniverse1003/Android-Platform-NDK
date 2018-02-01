def run_unsupported(_abi, device_api, _subtest):
    if device_api < 19:
        return device_api
    return None


def run_broken(abi, _device_api, _subtest):
    if abi == 'x86_64':
        return abi, 'http://b/72816091'
    return None, None
