def build_broken(test):
    if test.case_name == "streaming.pass":
        # This is XFAIL: * upstream. No bug is filed.
        return "all", "upstream"
    return None, None
