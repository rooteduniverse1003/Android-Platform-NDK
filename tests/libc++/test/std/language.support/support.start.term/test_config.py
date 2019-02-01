def build_broken(test):
    if test.case_name == 'quick_exit.pass' and test.config.api < 21:
        return f'android-{test.config.api}', 'http://b/34719339'
    return None, None
