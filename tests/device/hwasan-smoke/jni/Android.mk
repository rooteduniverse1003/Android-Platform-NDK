LOCAL_PATH := $(call my-dir)

include $(CLEAR_VARS)
LOCAL_MODULE := hwasan_smoke
LOCAL_CPP_EXTENSION := .cc
LOCAL_SRC_FILES := hwasan_oob_test.cc
LOCAL_CFLAGS := -fsanitize=hwaddress -fno-omit-frame-pointer
# Remove -Wl,-dynamic-linker once https://reviews.llvm.org/D151388 makes it into NDK
LOCAL_LDFLAGS := -fsanitize=hwaddress -Wl,-dynamic-linker,/system/bin/linker_hwasan64
LOCAL_STATIC_LIBRARIES := googletest_main
include $(BUILD_EXECUTABLE)

$(call import-module,third_party/googletest)
