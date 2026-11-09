# cmake toolchain for the cross-compilation to IBM i PASE (AIX) from LINUXBUILD.
# No AIX linker on Linux: compiler checks produce a static library
# instead of an executable.
set(CMAKE_SYSTEM_NAME AIX)
set(CMAKE_SYSTEM_PROCESSOR powerpc64)
set(CMAKE_C_COMPILER $ENV{CROSS_DIR}/cc-aix)   # CROSS_DIR: exported by cross-env.sh
set(CMAKE_CXX_COMPILER $ENV{HOME}/v8aix/clang/bin/clang++)
set(CMAKE_AR $ENV{HOME}/v8aix/bin/ar-aix CACHE FILEPATH "" FORCE)
set(CMAKE_C_COMPILER_TARGET powerpc64-ibm-aix7.2)
set(CMAKE_CXX_COMPILER_TARGET powerpc64-ibm-aix7.2)
set(CMAKE_SYSROOT $ENV{HOME}/v8aix/sysroot)
set(CMAKE_TRY_COMPILE_TARGET_TYPE STATIC_LIBRARY)
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
# Compiler checks still fail at link time (no AIX ld here): skip them
set(CMAKE_C_COMPILER_WORKS 1)
set(CMAKE_CXX_COMPILER_WORKS 1)
