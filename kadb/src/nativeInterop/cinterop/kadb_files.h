#ifndef KADB_FILES_H
#define KADB_FILES_H

#include <fcntl.h>
#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>

/* Keep the exclusive create and close-on-exec flag in one system call.
 * Linux's platform.posix KLIB does not expose mkostemp, but its fixed glibc
 * sysroot does. Darwin provides it from macOS 10.12 / iOS 10.0 onward. */
static inline int kadb_create_private_temp(char *path) {
    return mkostemp(path, O_CLOEXEC);
}

static inline int kadb_commit_private_temp(char *path, const char *destination) {
    return rename(path, destination);
}

static inline int kadb_remove_private_temp(char *path) {
    return unlink(path);
}

#endif
