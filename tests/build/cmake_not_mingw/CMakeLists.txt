cmake_minimum_required(VERSION 3.6)
project(CMakeNotMinGW ASM C CXX)

if(DEFINED MINGW)
  message(FATAL_ERROR "MINGW should not be defined")
endif()
