LOCAL_PATH := $(call my-dir)

include $(CLEAR_VARS)
LOCAL_MODULE := foo_solib
LOCAL_SRC_FILES := foo.cpp
include $(BUILD_SHARED_LIBRARY)

include $(CLEAR_VARS)
LOCAL_MODULE := foo_exe
LOCAL_SRC_FILES := foo.cpp
include $(BUILD_EXECUTABLE)

include $(CLEAR_VARS)
LOCAL_MODULE := foo_static_exe
LOCAL_SRC_FILES := foo.cpp
LOCAL_LDFLAGS := -static
include $(BUILD_EXECUTABLE)
