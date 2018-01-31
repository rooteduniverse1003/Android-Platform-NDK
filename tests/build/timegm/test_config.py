def build_unsupported(_abi, api):
    if api < 12:
        return api
    return None
