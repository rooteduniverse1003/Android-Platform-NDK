#include <android/trace.h>

int main(int, char**) {
  ATrace_beginAsyncSection("ndk::asyncBeginEndSection", 0);
  return 0;
}