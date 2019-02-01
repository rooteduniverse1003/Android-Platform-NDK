def run_broken(test, device):
    is_lp64 = test.config.abi in ('arm64-v8a', 'x86_64')
    if device.version < 26 and is_lp64 and test.case_name == 'stold.pass':
        return f'android-{device.version}', 'http://b/31101647'
    if not is_lp64 and test.case_name == 'stof.pass':
        return 'all', 'http://b/34739876'
    return None, None
