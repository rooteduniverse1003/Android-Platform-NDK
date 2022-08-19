def run_broken(test, device):
    is_lp64 = test.config.abi in ("arm64-v8a", "x86_64")
    failing_tests = ("get_long_double.pass",)
    if is_lp64 and device.version < 26 and test.case_name in failing_tests:
        return f"android-{device.version}", "http://b/31101647"

    if test.case_name == "get_float.pass" and device.version < 21:
        return test.config.abi, "https://github.com/android-ndk/ndk/issues/415"

    percent_a_tests = (
        "get_double.pass",
        "get_long_double.pass",
    )
    if test.case_name in percent_a_tests and device.version < 21:
        bug = "https://github.com/android-ndk/ndk/issues/437"
        return f"android-{device.version}", bug

    return None, None
