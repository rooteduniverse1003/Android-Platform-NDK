cmake_minimum_required(VERSION 3.22)
project(CMakeExportsTest C CXX)

if(NOT DEFINED CMAKE_C_COMPILER)
    message(FATAL_ERROR "CMAKE_C_COMPILER not set")
endif()

if(NOT DEFINED CMAKE_CXX_COMPILER)
    message(FATAL_ERROR "CMAKE_CXX_COMPILER not set")
endif()

if(NOT DEFINED CMAKE_AR)
    message(FATAL_ERROR "CMAKE_AR not set")
endif()

if(NOT DEFINED CMAKE_STRIP)
    message(FATAL_ERROR "CMAKE_STRIP not set")
endif()

if(NOT DEFINED CMAKE_RANLIB)
    message(FATAL_ERROR "CMAKE_RANLIB not set")
endif()