# Copyright (C) 2020 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This is a hook file that will be included by cmake at the beginning of
# Modules/Platform/Android/Determine-Compiler.cmake.

# Don't do anything if using legacy toolchain file.
if(CMAKE_SYSTEM_VERSION EQUAL 1)
  return()
endif()

# Point cmake to llvm binutils because the GNU ones take precedence.
set(CMAKE_AR
    "${CMAKE_ANDROID_NDK_TOOLCHAIN_UNIFIED}/bin/llvm-ar${ANDROID_TOOLCHAIN_SUFFIX}"
    CACHE FILEPATH "Archiver")
set(CMAKE_RANLIB
    "${CMAKE_ANDROID_NDK_TOOLCHAIN_UNIFIED}/bin/llvm-ranlib${ANDROID_TOOLCHAIN_SUFFIX}"
    CACHE FILEPATH "Ranlib")
set(CMAKE_STRIP
    "${CMAKE_ANDROID_NDK_TOOLCHAIN_UNIFIED}/bin/llvm-strip${ANDROID_TOOLCHAIN_SUFFIX}"
    CACHE FILEPATH "Strip")
