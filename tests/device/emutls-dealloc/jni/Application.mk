APP_STL := c++_static

# Turn on ASAN to help detect use-after-free. The test is still useful without
# ASAN.
APP_CFLAGS := -fsanitize=address
APP_LDFLAGS := -fsanitize=address
