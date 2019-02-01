def run_unsupported(test, _device):
    if test.case_name == 'pbump2gig.pass':
        # This test attempts to allocate 2GiB of 'a', which doesn't work on a
        # mobile device.
        return 'all'
    return None
