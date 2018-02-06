def build_unsupported(_abi, api):
    if api >= 21:
        return 'android-{}'.format(api)
    return None
