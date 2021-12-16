def build_broken(test):
    if test.case_name == "cmath_isnan.pass":
        return "all", "http://b/34724220"
    if test.case_name == "cmath_isinf.pass" and test.config.api >= 21:
        return f"android-{test.config.api}", "http://b/34724220"
    if test.case_name == "abs.fail" and test.config.api < 19:
        bug = "https://github.com/android/ndk/issues/1237"
        return f"android-{test.config.api}", bug
    return None, None
