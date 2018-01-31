def run_broken(abi, platform, name):
    if abi == 'x86_64':
        return abi, 'http://b/38264489'
    return None, None
