# API coverage

C library and selected POSIX inventory. This is not a conformance claim.

D/L = declaration/link availability: Y present, N probe failed. A failed
probe needs diagnostic review; a successful link does not validate its ABI.
Native mode retains compiler runtime and SDK syntax repairs, but excludes
NextStepCompat headers and libraries. Compiler built-ins are disabled.

## Availability

| Interface | Standard | i386 native / compat | m68k native / compat | sparc native / compat | hppa native / compat |
| --- | --- | --- | --- | --- | --- |
| `memcpy` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `memmove` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `memset` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `memcmp` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `memchr` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `strcpy` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `strncpy` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `strcat` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `strncat` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `strcmp` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `strncmp` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `strchr` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `strrchr` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `strspn` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `strcspn` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `strpbrk` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `strstr` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `strtok` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `strlen` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `strerror` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `strcoll` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `strxfrm` | C90 | Y/N ; Y/Y | Y/N ; Y/Y | Y/N ; Y/Y | Y/N ; Y/Y |
| `strdup` | POSIX.1-2008 | N/N ; N/N | N/N ; N/N | N/N ; N/N | N/N ; N/N |
| `strndup` | POSIX.1-2008 | N/N ; N/N | N/N ; N/N | N/N ; N/N | N/N ; N/N |
| `strnlen` | POSIX.1-2008 | N/N ; N/N | N/N ; N/N | N/N ; N/N | N/N ; N/N |
| `strtok_r` | POSIX.1-2008 | N/N ; N/N | N/N ; N/N | N/N ; N/N | N/N ; N/N |
| `strerror_r` | POSIX.1-2008 | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y |
| `atoi` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `atol` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `strtol` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `strtoul` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `strtod` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `atoll` | C99 | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y |
| `strtoll` | C99 | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y |
| `strtoull` | C99 | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y |
| `strtof` | C99 | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y |
| `strtold` | C99 | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y |
| `strtoimax` | C99 | N/N ; N/N | N/N ; N/N | N/N ; N/N | N/N ; N/N |
| `strtoumax` | C99 | N/N ; N/N | N/N ; N/N | N/N ; N/N | N/N ; N/N |
| `imaxabs` | C99 | N/N ; N/N | N/N ; N/N | N/N ; N/N | N/N ; N/N |
| `imaxdiv` | C99 | N/N ; N/N | N/N ; N/N | N/N ; N/N | N/N ; N/N |
| `malloc` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `calloc` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `realloc` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `free` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `abort` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `exit` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `atexit` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `getenv` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `system` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `bsearch` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `qsort` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `_Exit` | C99 | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y |
| `posix_memalign` | POSIX.1-2008 | N/N ; N/N | N/N ; N/N | N/N ; N/N | N/N ; N/N |
| `setenv` | POSIX.1-2008 | N/N ; N/N | N/N ; N/N | N/N ; N/N | N/N ; N/N |
| `unsetenv` | POSIX.1-2008 | N/N ; N/N | N/N ; N/N | N/N ; N/N | N/N ; N/N |
| `realpath` | POSIX.1-2008 | N/Y ; Y/Y | N/Y ; Y/Y | N/Y ; Y/Y | N/Y ; Y/Y |
| `mkstemp` | POSIX.1-2008 | N/Y ; N/Y | N/Y ; N/Y | N/Y ; N/Y | N/Y ; N/Y |
| `printf` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `fprintf` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `sprintf` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `vprintf` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `vfprintf` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `vsprintf` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `scanf` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `fscanf` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `sscanf` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `fopen` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `fclose` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `fflush` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `fread` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `fwrite` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `fseek` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `ftell` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `tmpfile` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `remove` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `rename` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `ungetc` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `snprintf` | C99 | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y |
| `vsnprintf` | C99 | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y |
| `vscanf` | C99 | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y |
| `vfscanf` | C99 | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y |
| `vsscanf` | C99 | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y |
| `getline` | POSIX.1-2008 | N/N ; N/N | N/N ; N/N | N/N ; N/N | N/N ; N/N |
| `getdelim` | POSIX.1-2008 | N/N ; N/N | N/N ; N/N | N/N ; N/N | N/N ; N/N |
| `fseeko` | POSIX.1-2008 | N/N ; N/N | N/N ; N/N | N/N ; N/N | N/N ; N/N |
| `ftello` | POSIX.1-2008 | N/N ; N/N | N/N ; N/N | N/N ; N/N | N/N ; N/N |
| `fdopen` | POSIX.1-2008 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `fileno` | POSIX.1-2008 | Y/N (macro) ; Y/N (macro) | Y/N (macro) ; Y/N (macro) | Y/N (macro) ; Y/N (macro) | Y/N (macro) ; Y/N (macro) |
| `mbrlen` | C95/C99 | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y |
| `mbrtowc` | C95/C99 | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y |
| `wcrtomb` | C95/C99 | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y |
| `mbsrtowcs` | C95/C99 | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y |
| `wcsrtombs` | C95/C99 | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y |
| `mbsinit` | C95/C99 | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y |
| `wcslen` | C95/C99 | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y |
| `wcscmp` | C95/C99 | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y |
| `wcscpy` | C95/C99 | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y |
| `wcschr` | C95/C99 | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y |
| `wmemcpy` | C95/C99 | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y |
| `wmemmove` | C95/C99 | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y |
| `wmemcmp` | C95/C99 | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y |
| `wmemset` | C95/C99 | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y |
| `wcstol` | C95/C99 | N/N ; N/N | N/N ; N/N | N/N ; N/N | N/N ; N/N |
| `wcstoul` | C95/C99 | N/N ; N/N | N/N ; N/N | N/N ; N/N | N/N ; N/N |
| `wcstoll` | C95/C99 | N/N ; N/N | N/N ; N/N | N/N ; N/N | N/N ; N/N |
| `wcstoull` | C95/C99 | N/N ; N/N | N/N ; N/N | N/N ; N/N | N/N ; N/N |
| `wcstod` | C95/C99 | N/N ; N/N | N/N ; N/N | N/N ; N/N | N/N ; N/N |
| `wcstof` | C95/C99 | N/N ; N/N | N/N ; N/N | N/N ; N/N | N/N ; N/N |
| `wcstold` | C95/C99 | N/N ; N/N | N/N ; N/N | N/N ; N/N | N/N ; N/N |
| `iswalpha` | C95/C99 | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y |
| `iswspace` | C95/C99 | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y |
| `towlower` | C95/C99 | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y |
| `towupper` | C95/C99 | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y |
| `sigemptyset` | POSIX.1-2008 | Y/N ; Y/Y | Y/N ; Y/Y | Y/N ; Y/Y | Y/N ; Y/Y |
| `sigfillset` | POSIX.1-2008 | Y/N ; Y/Y | Y/N ; Y/Y | Y/N ; Y/Y | Y/N ; Y/Y |
| `sigaddset` | POSIX.1-2008 | Y/N ; Y/Y | Y/N ; Y/Y | Y/N ; Y/Y | Y/N ; Y/Y |
| `sigdelset` | POSIX.1-2008 | Y/N ; Y/Y | Y/N ; Y/Y | Y/N ; Y/Y | Y/N ; Y/Y |
| `sigismember` | POSIX.1-2008 | Y/N ; Y/Y | Y/N ; Y/Y | Y/N ; Y/Y | Y/N ; Y/Y |
| `sigaction` | POSIX.1-2008 | Y/N ; Y/Y | Y/N ; Y/Y | Y/N ; Y/Y | Y/N ; Y/Y |
| `sigprocmask` | POSIX.1-2008 | Y/N ; Y/Y | Y/N ; Y/Y | Y/N ; Y/Y | Y/N ; Y/Y |
| `sigpending` | POSIX.1-2008 | Y/N ; Y/Y | Y/N ; Y/Y | Y/N ; Y/Y | Y/N ; Y/Y |
| `sigsuspend` | POSIX.1-2008 | Y/N ; Y/Y | Y/N ; Y/Y | Y/N ; Y/Y | Y/N ; Y/Y |
| `stat` | POSIX.1-2008 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `lstat` | POSIX.1-2008 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `fstat` | POSIX.1-2008 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `mkdir` | POSIX.1-2008 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `mkfifo` | POSIX.1-2008 | Y/N ; Y/Y | Y/N ; Y/Y | Y/N ; Y/Y | Y/N ; Y/Y |
| `chmod` | POSIX.1-2008 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `fchmod` | POSIX.1-2008 | N/Y ; N/Y | N/Y ; N/Y | N/Y ; N/Y | N/Y ; N/Y |
| `access` | POSIX.1-2008 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `read` | POSIX.1-2008 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `write` | POSIX.1-2008 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `close` | POSIX.1-2008 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `unlink` | POSIX.1-2008 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `rmdir` | POSIX.1-2008 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `readlink` | POSIX.1-2008 | N/Y ; N/Y | N/Y ; N/Y | N/Y ; N/Y | N/Y ; N/Y |
| `symlink` | POSIX.1-2008 | N/Y ; N/Y | N/Y ; N/Y | N/Y ; N/Y | N/Y ; N/Y |
| `link` | POSIX.1-2008 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `fsync` | POSIX.1-2008 | N/Y ; N/Y | N/Y ; N/Y | N/Y ; N/Y | N/Y ; N/Y |
| `ftruncate` | POSIX.1-2008 | N/Y ; N/Y | N/Y ; N/Y | N/Y ; N/Y | N/Y ; N/Y |
| `pread` | POSIX.1-2008 | N/N ; N/N | N/N ; N/N | N/N ; N/N | N/N ; N/N |
| `pwrite` | POSIX.1-2008 | N/N ; N/N | N/N ; N/N | N/N ; N/N | N/N ; N/N |
| `opendir` | POSIX.1-2008 | N/Y ; Y/Y | N/Y ; Y/Y | N/Y ; Y/Y | N/Y ; Y/Y |
| `readdir` | POSIX.1-2008 | N/Y ; Y/Y | N/Y ; Y/Y | N/Y ; Y/Y | N/Y ; Y/Y |
| `closedir` | POSIX.1-2008 | N/Y ; Y/Y | N/Y ; Y/Y | N/Y ; Y/Y | N/Y ; Y/Y |
| `rewinddir` | POSIX.1-2008 | N/N ; Y/N | N/N ; Y/N | N/N ; Y/N | N/N ; Y/N |
| `dirfd` | POSIX.1-2008 | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y |
| `fork` | POSIX.1-2008 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `execve` | POSIX.1-2008 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `getpid` | POSIX.1-2008 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `getuid` | POSIX.1-2008 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `getgid` | POSIX.1-2008 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `getgroups` | POSIX.1-2008 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `sysconf` | POSIX.1-2008 | Y/N ; Y/N | Y/N ; Y/N | Y/N ; Y/N | Y/N ; Y/N |
| `time` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `clock` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `difftime` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `mktime` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `localtime` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `gmtime` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `strftime` | C90 | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y | Y/Y ; Y/Y |
| `localtime_r` | POSIX.1-2008 | N/N ; N/N | N/N ; N/N | N/N ; N/N | N/N ; N/N |
| `gmtime_r` | POSIX.1-2008 | N/N ; N/N | N/N ; N/N | N/N ; N/N | N/N ; N/N |
| `clock_gettime` | POSIX.1-2008 | N/N ; N/N | N/N ; N/N | N/N ; N/N | N/N ; N/N |
| `clock_getres` | POSIX.1-2008 | N/N ; N/N | N/N ; N/N | N/N ; N/N | N/N ; N/N |
| `nanosleep` | POSIX.1-2008 | N/N ; N/N | N/N ; N/N | N/N ; N/N | N/N ; N/N |
| `regcomp` | POSIX.1-2008 | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y |
| `regexec` | POSIX.1-2008 | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y |
| `regerror` | POSIX.1-2008 | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y |
| `regfree` | POSIX.1-2008 | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y | N/N ; Y/Y |

## Upstream behavior tests

Each cell is native / compat. Build failure and untested are distinct
from runtime failure. A failed multi-interface test does not establish
which interface is at fault. Passing is limited to the selected cases.

| Test | Host control | i386 | m68k | sparc | hppa |
| --- | --- | --- | --- | --- | --- |
| string | passed | build failed / build failed | build failed / build failed | build failed / build failed | build failed / build failed |
| string_strcspn | passed | passed / passed | passed / passed | passed / passed | passed / passed |
| string_strstr | passed | failed / passed | failed / passed | failed / passed | failed / passed |
| strtol | failed | build failed / passed | build failed / passed | build failed / passed | build failed / passed |
| strtod_simple | passed | build failed / passed | build failed / passed | build failed / passed | build failed / passed |
| snprintf | passed | build failed / passed | build failed / passed | build failed / passed | build failed / passed |
| sscanf | passed | failed / passed | failed / passed | failed / passed | failed / passed |
| ungetc | passed | failed / passed | failed / passed | failed / passed | failed / passed |
| strftime | failed | build failed / build failed | build failed / build failed | build failed / build failed | build failed / build failed |
| qsort | passed | passed / passed | passed / passed | passed / passed | passed / passed |
| regressions | guest-only | failed / passed | failed / passed | failed / passed | failed / passed |

Upstream libc-test commit: `7b95dfa5f5d5ca4d949221e0228ccc290bacc14e`.
Machine-readable results and full diagnostics accompany this generated report.

## Reviewed behavior and next steps

These observations refer to the exact log hashes in fixes-triage.json.
New runs require review before inheriting a behavioral diagnosis.

- `strcspn`, `qsort`: Selected upstream cases pass on every target; not exhaustive conformance.
- `strstr`: Empty needle returns NULL for both empty and nonempty haystacks; required result is the haystack pointer.
- `strtol`: The native-only reduced control fails valid prefix/range/end-pointer cases. The invalid-base host divergence remains a separate policy issue.
- `sscanf`: Valid percent-i integer conversions do not recognize octal/hexadecimal prefixes. Additional failures need individual reduction and standards review.
- `fprintf`, `ungetc`: fprintf returns zero for a successful 13-byte write. A single ungetc after an unsuccessful scanset conversion fails; reduce the stream-state case before designing a fix.
- `strstr`: Pinned musl search passes the upstream cases, including empty needles.
- `strtol`, `strtoul`: Checked adapters pass upstream and reduced prefix, sign, range and end-pointer cases.
- `sscanf`, `vsscanf`, `fscanf`, `vfscanf`: Pinned musl scanner passes string and native-stream input cases; va_list implementations are exercised through the variadic entry points.
- `printf`, `fprintf`, `vfprintf`: Stream formatting and character counts pass; output errors set the native error indicator. The shared va_list implementation is exercised.
- `ungetc`: Pushback passes all 256 byte values after repeated EOF, beginning-of-buffer lookahead and caller-owned buffer boundaries.
- `strtod`, `snprintf`: Selected upstream conversion and bounded-format tests pass.

Classification counts (individual interfaces, not test assertions):

- i386 native: 5 broken, 77 missing, 1 partially supported, 86 untested, 2 working natively
- i386 compat: 31 missing, 1 partially supported, 124 untested, 2 working natively, 13 working with compatibility
- m68k native: 5 broken, 77 missing, 1 partially supported, 86 untested, 2 working natively
- m68k compat: 31 missing, 1 partially supported, 124 untested, 2 working natively, 13 working with compatibility
- sparc native: 5 broken, 77 missing, 1 partially supported, 86 untested, 2 working natively
- sparc compat: 31 missing, 1 partially supported, 124 untested, 2 working natively, 13 working with compatibility
- hppa native: 5 broken, 77 missing, 1 partially supported, 86 untested, 2 working natively
- hppa compat: 31 missing, 1 partially supported, 124 untested, 2 working natively, 13 working with compatibility

- Separate the mixed BSD string tests from the C string test body.
- Fill the remaining self-contained string and integer API gaps from reviewed implementations.
- Investigate filesystem/time wrappers against real kernel capabilities.
- Extend the inventory to omitted headers, math and locale interfaces.
