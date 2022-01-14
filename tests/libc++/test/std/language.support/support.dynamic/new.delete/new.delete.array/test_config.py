def run_broken(test, device):
    failing_tests = [
        "delete_align_val_t_replace.pass",
        "new_align_val_t_nothrow_replace.pass",
        "new_array_nothrow_replace.pass",
        "new_array_replace.pass",
    ]
    if test.case_name in failing_tests and device.version < 18:
        return f"android-{device.version}", "http://b/2643900"
    return None, None
