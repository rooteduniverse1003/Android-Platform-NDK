def build_broken(test):
    if test.case_name == 'version_cuchar.pass':
        return 'all', 'http://b/63679176'
    return None, None
