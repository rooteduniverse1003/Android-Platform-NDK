def run_broken(abi, device_api, name):
    failing_tests = [
        'new_array_nothrow_replace.pass',
    ]
    if name in failing_tests and device_api < 18:
        return 'android-{}'.format(device_api), 'http://b/2643900'
    return None, None
