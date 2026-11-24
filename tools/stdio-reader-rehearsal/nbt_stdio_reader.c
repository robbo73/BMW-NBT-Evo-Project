/* Inert C-only stdio reader. Fixed dummy alias/text, no XML/plugin/HMI calls. */
#include <stdio.h>
#include <signal.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

static const char body[] = "nbt-endpoint-rehearsal\n";

static int parse_pid(const char *text, unsigned long *value)
{
    unsigned long number = 0;
    const unsigned char *p = (const unsigned char *)text;
    if (!p || *p < '1' || *p > '9') return 0;
    do {
        unsigned long digit;
        if (*p < '0' || *p > '9') return 0;
        digit = (unsigned long)(*p - '0');
        if (number > (2147483647UL - digit) / 10UL) return 0;
        number = number * 10UL + digit;
    } while (*++p);
    if (number <= 1UL) return 0;
    *value = number;
    return 1;
}

static void usage(const char *name)
{
    printf("Usage: %s --read-alias SHELL_PID\n", name);
    puts("Revision: stdio-reader-1; default/help performs no file reads.");
    puts("Reads only the fixed dummy-discovery.txt RAM alias; no XML/plugin/HMI operation.");
}

int main(int argc, char **argv)
{
    unsigned long pid;
    char parent[128], path[160], buffer[sizeof(body)];
    struct stat info;
    FILE *stream = NULL;
    long length = -1;
    int count, result = 1;

    if (argc == 1 || (argc == 2 && strcmp(argv[1], "--help") == 0)) {
        usage(argv[0]); return 0;
    }
    if (argc != 3 || strcmp(argv[1], "--read-alias") != 0 ||
        !parse_pid(argv[2], &pid)) {
        usage(argv[0]); return 2;
    }
    count = snprintf(parent, sizeof(parent), "/ramdisk/mm/.nbt-endpoint-alias.%lu", pid);
    if (count < 0 || (size_t)count >= sizeof(parent)) return 1;
    count = snprintf(path, sizeof(path), "%s/dummy-discovery.txt", parent);
    if (count < 0 || (size_t)count >= sizeof(path)) return 1;
    /* Only this disposable reader receives the default five-second alarm. */
    if (signal(SIGALRM, SIG_DFL) == SIG_ERR) { perror("signal"); return 1; }
    alarm(5);
    if (lstat(parent, &info) != 0 || !S_ISDIR(info.st_mode)) {
        fputs("STOP: dummy parent is missing, linked or not a directory\n", stderr);
        goto done;
    }
    if (lstat(path, &info) != 0 || !S_ISLNK(info.st_mode)) {
        fputs("STOP: dummy alias is missing or not a symlink\n", stderr);
        goto done;
    }
    if (stat(path, &info) != 0 || !S_ISREG(info.st_mode) ||
        info.st_size != (off_t)(sizeof(body) - 1)) {
        fputs("STOP: followed dummy alias has wrong type or size\n", stderr);
        goto done;
    }
    stream = fopen(path, "rb");
    if (!stream) { perror("fopen"); goto done; }
    if (fseek(stream, 0, SEEK_END) != 0) { perror("fseek end"); goto done; }
    length = ftell(stream);
    if (length != (long)(sizeof(body) - 1)) {
        fputs("STOP: ftell did not return the expected 23 bytes\n", stderr);
        goto done;
    }
    if (fseek(stream, 0, SEEK_SET) != 0) { perror("fseek start"); goto done; }
    if (fread(buffer, (size_t)length, 1, stream) != 1) {
        fputs("STOP: full-file fread did not return one item\n", stderr);
        goto done;
    }
    if (memcmp(buffer, body, sizeof(body) - 1) != 0) {
        fputs("STOP: unexpected dummy bytes\n", stderr);
        goto done;
    }
    if (fclose(stream) != 0) {
        stream = NULL;
        perror("fclose"); goto done;
    }
    stream = NULL;
    result = 0;
done:
    if (stream && fclose(stream) != 0) { perror("fclose cleanup"); result = 1; }
    alarm(0);
    if (result == 0) {
        printf("PASS: stdio-reader-1; bytes=%ld items=1; seek-end/tell/rewind/read/close\n", length);
    }
    return result;
}
