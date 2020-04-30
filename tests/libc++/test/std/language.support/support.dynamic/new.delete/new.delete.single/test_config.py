def run_broken(test, device):
    failing_tests = [
        'new_align_val_t_nothrow_replace.pass',
        'new_nothrow_replace.pass',
    ]
    if test.case_name in failing_tests and device.version < 18:
        return f'android-{device.version}', 'http://b/2643900'
    return None, None
