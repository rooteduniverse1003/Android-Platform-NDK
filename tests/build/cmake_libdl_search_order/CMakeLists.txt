# https://github.com/android/ndk/issues/929
# Tests that the first libdl found by find_library is the shared library rather
# than the static library.
cmake_minimum_required(VERSION 3.6.0)
project(cmake_libdl_search_order)

find_library(LIBDL dl)
if(LIBDL MATCHES ".a$")
  message(FATAL_ERROR "found libdl.a")
endif()
