#include <memory.h>

#include "gtest/gtest.h"
#include "gtest/gtest-death-test.h"

TEST(fortify, smoke) {
  char cs[4];
  char* p = cs;
  ASSERT_DEATH(memset(p, 0, 5),
               "memset: prevented 5-byte write into 4-byte buffer");
}
