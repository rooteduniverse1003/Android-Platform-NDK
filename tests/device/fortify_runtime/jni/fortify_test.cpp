#include <memory.h>

#include <android/api-level.h>

#include "gtest/gtest.h"
#include "gtest/gtest-death-test.h"

static const char* expected_stderr() {
  if (android_get_device_api_level() == 19) {
    // The program is still halted and logcat includes the message on kitkat,
    // but that message doesn't reach stderr. I'm not sure when that was fixed,
    // so for now this check is for exactly API 19. May need revising when we
    // move to min of 21.
    return "";
  } else {
    return "memset: prevented 5-byte write into 4-byte buffer";
  }
}

TEST(fortify, smoke) {
  char cs[4];
  char* p = cs;
  ASSERT_DEATH(memset(p, 0, 5), expected_stderr());
}
