LOCAL_PATH := $(call my-dir)

include $(CLEAR_VARS)
LOCAL_MODULE := foo
LOCAL_SRC_FILES := foo.cpp
ifeq ($(APP_LD),lld)
    LOCAL_LDFLAGS := -fuse-ld=bfd
else
    LOCAL_LDFLAGS := -fuse-ld=lld
endif
include $(BUILD_SHARED_LIBRARY)
