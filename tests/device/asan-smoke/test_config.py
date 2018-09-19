def run_unsupported(abi, device_api, _subtest):
    if device_api < 19:
        return device_api
    if (device_api, abi) == (28, 'x86_64'):
        # ASAN is flaky with 28 x86_64. It still works with 32-bit or with
        # older platforms.
        return 'ASAN is flaky on 28 x86_64 (http://b/37130178)'
    return None
