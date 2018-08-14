def run_broken(_abi, device_api, name):
    if name == 'gtest-printers_test' and device_api <= 16:
        return ('android-{}'.format(device_api),
                'https://github.com/android-ndk/ndk/issues/771')
    return None, None
