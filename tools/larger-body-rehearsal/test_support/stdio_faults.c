/* GNU/Linux linker wrappers for error handling only. Never in the QNX build. */
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static int fault(const char *name)
{
    const char *value = getenv("NBT_STDIO_FAULT");
    return value && strcmp(value, name) == 0;
}
FILE *__real_fopen(const char *, const char *);
int __real_fseek(FILE *, long, int);
long __real_ftell(FILE *);
size_t __real_fread(void *, size_t, size_t, FILE *);
int __real_fclose(FILE *);
FILE *__wrap_fopen(const char *path, const char *mode)
{
    if (fault("open")) { errno = EIO; return NULL; }
    return __real_fopen(path, mode);
}
int __wrap_fseek(FILE *stream, long offset, int origin)
{
    if ((origin == SEEK_END && fault("seek_end")) ||
        (origin == SEEK_SET && fault("seek_start"))) { errno = EIO; return -1; }
    return __real_fseek(stream, offset, origin);
}
long __wrap_ftell(FILE *stream)
{
    if (fault("tell")) { errno = EIO; return -1; }
    return __real_ftell(stream);
}
size_t __wrap_fread(void *buffer, size_t size, size_t count, FILE *stream)
{
    if (fault("hang_read")) pause();
    if (fault("read")) { errno = EIO; return 0; }
    return __real_fread(buffer, size, count, stream);
}
int __wrap_fclose(FILE *stream)
{
    int result = __real_fclose(stream);
    if (fault("close")) { errno = EIO; return EOF; }
    return result;
}
