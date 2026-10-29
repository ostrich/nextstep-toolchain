/* Stateless byte-preserving conversion; no UTF-8 decoding.
   SPDX-License-Identifier: 0BSD */
#include <wchar.h>
#include <stdlib.h>
#include <errno.h>
#include <string.h>

static void initial(mbstate_t *state)
{
    if (state)
        memset(state, 0, sizeof(*state));
}

size_t ns33_mb_cur_max(void)
{
    return 1;
}
int mbsinit(const mbstate_t *state)
{
    unsigned i;
    if (!state)
        return 1;
    if (state->state)
        return 0;
    for (i = 0; i < 3; ++i)
        if (state->reserved[i])
            return 0;
    return 1;
}

size_t mbrtowc(wchar_t *out, const char *input, size_t n, mbstate_t *state)
{
    unsigned char byte;
    if (!input) {
        initial(state);
        return 0;
    }
    if (!n)
        return (size_t)-2;
    byte = (unsigned char)*input;
    if (out)
        *out = byte;
    initial(state);
    return byte ? 1 : 0;
}
size_t mbrlen(const char *input, size_t n, mbstate_t *state)
{
    return mbrtowc(0, input, n, state);
}
size_t wcrtomb(char *out, wchar_t wc, mbstate_t *state)
{
    if (!out) {
        initial(state);
        return 1;
    }
    if ((unsigned long)wc > 255) {
        errno = EILSEQ;
        return (size_t)-1;
    }
    *out = (char)(unsigned char)wc;
    initial(state);
    return 1;
}

size_t mbsnrtowcs(wchar_t *out, const char **source, size_t available,
                  size_t limit, mbstate_t *state)
{
    const unsigned char *input = (const unsigned char *)*source;
    size_t i = 0;
    if (!out) {
        while (i < available && input[i])
            ++i;
        return i;
    }
    while (i < available && i < limit) {
        out[i] = input[i];
        if (!input[i]) {
            *source = 0;
            initial(state);
            return i;
        }
        ++i;
    }
    *source = (const char *)input + i;
    if (i)
        initial(state);
    return i;
}
size_t mbsrtowcs(wchar_t *out, const char **source, size_t limit,
                 mbstate_t *state)
{
    return mbsnrtowcs(out, source, (size_t)-1, limit, state);
}
size_t wcsnrtombs(char *out, const wchar_t **source, size_t available,
                  size_t limit, mbstate_t *state)
{
    const wchar_t *input = *source;
    size_t i = 0;
    while (i < available && (!out || i < limit)) {
        if ((unsigned long)input[i] > 255) {
            if (out)
                *source = input + i;
            errno = EILSEQ;
            return (size_t)-1;
        }
        if (out)
            out[i] = (char)(unsigned char)input[i];
        if (!input[i]) {
            if (out) {
                *source = 0;
                initial(state);
            }
            return i;
        }
        ++i;
    }
    if (out) {
        *source = input + i;
        if (i)
            initial(state);
    }
    return i;
}
size_t wcsrtombs(char *out, const wchar_t **source, size_t limit,
                 mbstate_t *state)
{
    return wcsnrtombs(out, source, (size_t)-1, limit, state);
}
wint_t btowc(int byte)
{
    return byte < 0 || byte > 255 ? WEOF : (wint_t)byte;
}
int wctob(wint_t wc)
{
    return wc > 255 ? -1 : (int)wc;
}
int ns33_mblen(const char *s, size_t n)
{
    size_t result = mbrlen(s, n, 0);
    if (result == (size_t)-2) {
        errno = EILSEQ;
        return -1;
    }
    return (int)result;
}
int ns33_mbtowc(wchar_t *out, const char *s, size_t n)
{
    size_t result = mbrtowc(out, s, n, 0);
    if (result == (size_t)-2) {
        errno = EILSEQ;
        return -1;
    }
    return (int)result;
}
int ns33_wctomb(char *out, wchar_t wc)
{
    if (!out)
        return 0;
    return wcrtomb(out, wc, 0) == (size_t)-1 ? -1 : 1;
}
size_t ns33_mbstowcs(wchar_t *out, const char *s, size_t n)
{
    return mbsrtowcs(out, &s, n, 0);
}
size_t ns33_wcstombs(char *out, const wchar_t *s, size_t n)
{
    return wcsrtombs(out, &s, n, 0);
}
