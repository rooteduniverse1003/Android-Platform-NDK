def run_unsupported(abi, device_api, name):
    # The tested behavior fails reliably on API 16, but it's flaky on 24, so
    # skip the test until 26 where it appears reliable.
    if name == 'googletest-death-test-test' and device_api < 26:
        return 'android-{} (https://github.com/android-ndk/ndk/issues/795)'.format(device_api)


def run_broken(_abi, device_api, name):
    if name == 'googletest-printers-test' and device_api <= 16:
        return ('android-{}'.format(device_api),
                'https://github.com/android-ndk/ndk/issues/771')
    return None, None
