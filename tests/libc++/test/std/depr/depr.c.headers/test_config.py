def build_broken(test):
    if test.case_name == "math_h_isnan.pass":
        return "all", "http://b/34724220"
    if test.case_name == "math_h_isinf.pass" and test.config.api >= 21:
        return f"android-{test.config.api}", "http://b/34724220"
    return None, None
