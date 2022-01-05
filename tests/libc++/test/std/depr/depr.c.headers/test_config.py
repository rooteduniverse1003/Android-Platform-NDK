def build_broken(test):
    if test.case_name == "math_h_isnan.pass":
        return "all", "http://b/34724220"
    if test.case_name == "math_h_isinf.pass" and test.config.api >= 21:
        return f"android-{test.config.api}", "http://b/34724220"
    if test.case_name == "stdlib_h.pass" and test.config.api < 21:
        return "pre API 21", "https://github.com/android/ndk/issues/1108"
    return None, None
