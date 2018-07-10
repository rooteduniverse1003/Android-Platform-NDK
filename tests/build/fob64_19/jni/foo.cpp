#define _FILE_OFFSET_BITS 64
#include <cstdio>

namespace {

// These should be unavailable before android-24, and available afterward.
using ::fgetpos;
using ::fsetpos;

}
