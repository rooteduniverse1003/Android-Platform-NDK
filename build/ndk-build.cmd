@echo off
set NDK_ROOT=%~dp0\..
set PREBUILT_PATH=%NDK_ROOT%\prebuilt\windows-x86_64
"%PREBUILT_PATH%\bin\make.exe" -O -f "%NDK_ROOT%\build\core\build-local.mk" SHELL=cmd %*
