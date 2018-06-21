def run_unsupported(_abi, _api, name):
    if name == 'pbump2gig.pass':
        # This test attempts to allocate 2GiB of 'a', which doesn't work on a
        # mobile device.
        return 'all'
    return None
