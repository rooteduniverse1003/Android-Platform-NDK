def run_broken(test, device):
    is_lp64 = test.config.abi in ('arm64-v8a', 'x86_64')
    if is_lp64 and test.case_name == 'put_long_double.pass':
        return test.config.abi, 'http://b/34950416'
    percent_f_tests = ('put_double.pass', 'put_long_double.pass')
    if test.case_name in percent_f_tests and device.version < 21:
        return f'android-{device.version}', 'http://b/35764716'
    if test.case_name == 'put_long_double.pass':
        return 'all?', 'http://b/63144639'
    return None, None
