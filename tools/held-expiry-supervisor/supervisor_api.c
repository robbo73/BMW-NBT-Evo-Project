/* SDK declaration/ABI capture only; compile/preprocess, never execute. */
#include <sys/types.h>
#include <sys/wait.h>
#include <dirent.h>
#include <fcntl.h>
#include <signal.h>
#include <time.h>
#include <unistd.h>
char nbt_size_timer_t[sizeof(timer_t)];
char nbt_size_sig_atomic_t[sizeof(sig_atomic_t)];
char nbt_size_sigevent[sizeof(struct sigevent)];
char nbt_size_itimerspec[sizeof(struct itimerspec)];
char nbt_size_off_t[sizeof(off_t)];
char nbt_size_pid_t[sizeof(pid_t)];
char nbt_offset_sigev_notify[__builtin_offsetof(struct sigevent,sigev_notify)+1];
char nbt_offset_sigev_signo[__builtin_offsetof(struct sigevent,sigev_signo)+1];
char nbt_value_sigev_signal[SIGEV_SIGNAL+1];
char nbt_value_sigkill[SIGKILL+1];
char nbt_value_wnohang[WNOHANG+1];
static int (*const create_signature)(clockid_t,struct sigevent *,timer_t *)=timer_create;
static int (*const overrun_signature)(timer_t)=timer_getoverrun;
static int (*const set_signature)(timer_t,int,const struct itimerspec *,struct itimerspec *)=timer_settime;
static pid_t (*const wait_signature)(pid_t,int *,int)=waitpid;
int nbt_api_typecheck(void) {
    return create_signature != 0 && overrun_signature != 0 &&
           set_signature != 0 && wait_signature != 0;
}
