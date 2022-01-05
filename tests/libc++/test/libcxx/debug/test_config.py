def run_unsupported(test, device):
    # Can't replace SIGABRT on old releases.
    if device.version < 21 and test.case_name == "debug_abort.pass":
        return device.version
    return None
