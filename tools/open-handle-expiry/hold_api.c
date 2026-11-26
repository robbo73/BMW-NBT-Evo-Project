/* Compile/preprocess only: capture the actual SDK declarations and sizes. */
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <signal.h>
#include <time.h>
#include <unistd.h>
/* Object sizes in readelf --symbols expose ABI sizes without ARM execution. */
char nbt_size_off_t[sizeof(off_t)];
char nbt_size_ssize_t[sizeof(ssize_t)];
char nbt_size_siginfo_t[sizeof(siginfo_t)];
char nbt_size_stat[sizeof(struct stat)];
char nbt_offset_siginfo_pid[__builtin_offsetof(siginfo_t, si_pid)+1];
char nbt_offset_stat_size[__builtin_offsetof(struct stat, st_size)+1];
static int (*const wait_signature)(const sigset_t *, siginfo_t *) = sigwaitinfo;
static off_t (*const seek_signature)(int, off_t, int) = lseek;
static ssize_t (*const read_signature)(int, void *, size_t) = read;
static int (*const mask_signature)(int, const sigset_t *, sigset_t *) = sigprocmask;
int nbt_declarations_typecheck(void) {
    return wait_signature != 0 && seek_signature != 0 &&
           read_signature != 0 && mask_signature != 0;
}
