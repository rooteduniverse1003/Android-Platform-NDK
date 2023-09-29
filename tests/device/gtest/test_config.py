from ndk.test.devices import Device
from ndk.test.devicetest.case import BasicTestCase


def run_unsupported(test: BasicTestCase, device: Device) -> str | None:
    # The tested behavior fails reliably on API 16, but it's flaky on 24, so
    # skip the test until 26 where it appears reliable.
    if test.executable == "googletest-death-test-test" and device.version < 26:
        bug = "https://github.com/android-ndk/ndk/issues/795"
        return f"android-{device.version} ({bug})"
    return None


def run_broken(
    test: BasicTestCase, device: Device
) -> tuple[str, str] | tuple[None, None]:
    if test.executable == "googletest-port-test" and device.version >= 34:
        return f"android-{device.version}", "https://github.com/android/ndk/issues/1944"
    return None, None
