LOCAL_PATH := $(call my-dir)

include $(CLEAR_VARS)
LOCAL_MODULE := pthread_test
LOCAL_SRC_FILES := pthread_test.cpp
LOCAL_STATIC_LIBRARIES := googletest_main
include $(BUILD_EXECUTABLE)

include $(CLEAR_VARS)
LOCAL_MODULE := tls_var
LOCAL_SRC_FILES := tls_var.cpp
LOCAL_STATIC_LIBRARIES := googletest_main
include $(BUILD_EXECUTABLE)

$(call import-module,third_party/googletest)
