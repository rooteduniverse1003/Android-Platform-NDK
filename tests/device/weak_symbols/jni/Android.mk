LOCAL_PATH := $(call my-dir)

include $(CLEAR_VARS)
LOCAL_MODULE := unconditional
LOCAL_SRC_FILES := unconditional.cpp
LOCAL_STATIC_LIBRARIES := googletest_main
LOCAL_CFLAGS := -D__ANDROID_UNAVAILABLE_SYMBOLS_ARE_WEAK__
LOCAL_LDLIBS := -landroid
include $(BUILD_EXECUTABLE)

$(call import-module,third_party/googletest)