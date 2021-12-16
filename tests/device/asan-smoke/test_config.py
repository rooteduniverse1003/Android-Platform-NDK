def run_unsupported(test, device):
    if device.version < 19:
        return device.version
    if device.version >= 28 and test.config.abi == "x86_64":
        # ASAN is flaky with 28 x86_64. It still works with 32-bit or with
        # older platforms.
        return "ASAN is flaky on 28 x86_64 (http://b/37130178)"
    return None
