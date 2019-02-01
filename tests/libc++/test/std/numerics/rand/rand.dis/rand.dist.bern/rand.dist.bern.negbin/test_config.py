def run_broken(test, device):
    if device.version < 21 and test.case_name == 'io.pass':
        bug = 'https://issuetracker.google.com/36988114'
        return f'android-{device.version}', bug
    return None, None
