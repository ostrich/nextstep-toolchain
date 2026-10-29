/* Wide code-unit operations and native single-byte display widths.
   SPDX-License-Identifier: 0BSD */
#include <wchar.h>
#include <wctype.h>
#include <stdlib.h>
#include <stdint.h>
#include <errno.h>

size_t wcslen(const wchar_t *s)
{
    const wchar_t *p = s;
    while (*p)
        ++p;
    return p - s;
}
size_t wcsnlen(const wchar_t *s, size_t n)
{
    size_t i = 0;
    while (i < n && s[i])
        ++i;
    return i;
}
int wcscmp(const wchar_t *a, const wchar_t *b)
{
    while (*a && *a == *b) {
        ++a;
        ++b;
    }
    return (*a > *b) - (*a < *b);
}
int wcsncmp(const wchar_t *a, const wchar_t *b, size_t n)
{
    while (n) {
        if (*a != *b)
            return (*a > *b) - (*a < *b);
        if (!*a)
            return 0;
        ++a;
        ++b;
        --n;
    }
    return 0;
}
wchar_t *wcschr(const wchar_t *s, wchar_t c)
{
    for (;;) {
        if (*s == c)
            return (wchar_t *)s;
        if (!*s)
            return 0;
        ++s;
    }
}
wchar_t *wcsrchr(const wchar_t *s, wchar_t c)
{
    const wchar_t *last = 0;
    do {
        if (*s == c)
            last = s;
    } while (*s++);
    return (wchar_t *)last;
}
wchar_t *wcsstr(const wchar_t *s, const wchar_t *needle)
{
    size_t n = wcslen(needle);
    if (!n)
        return (wchar_t *)s;
    for (; *s; ++s)
        if (!wcsncmp(s, needle, n))
            return (wchar_t *)s;
    return 0;
}
wchar_t *wcspbrk(const wchar_t *s, const wchar_t *set)
{
    for (; *s; ++s)
        if (wcschr(set, *s))
            return (wchar_t *)s;
    return 0;
}
size_t wcsspn(const wchar_t *s, const wchar_t *set)
{
    size_t n = 0;
    while (s[n] && wcschr(set, s[n]))
        ++n;
    return n;
}
size_t wcscspn(const wchar_t *s, const wchar_t *set)
{
    size_t n = 0;
    while (s[n] && !wcschr(set, s[n]))
        ++n;
    return n;
}
wchar_t *wcscpy(wchar_t *d, const wchar_t *s)
{
    wchar_t *p = d;
    while ((*p++ = *s++)) {
    }
    return d;
}
wchar_t *wcsncpy(wchar_t *d, const wchar_t *s, size_t n)
{
    size_t i = 0;
    while (i < n && s[i]) {
        d[i] = s[i];
        ++i;
    }
    while (i < n)
        d[i++] = 0;
    return d;
}
wchar_t *wcscat(wchar_t *d, const wchar_t *s)
{
    wcscpy(d + wcslen(d), s);
    return d;
}
wchar_t *wcsncat(wchar_t *d, const wchar_t *s, size_t n)
{
    wchar_t *p = d + wcslen(d);
    size_t i = 0;
    while (i < n && s[i]) {
        p[i] = s[i];
        ++i;
    }
    p[i] = 0;
    return d;
}
wchar_t *wcsdup(const wchar_t *s)
{
    size_t n = wcslen(s);
    wchar_t *p;
    if (n >= (size_t)-1 / sizeof(*p)) {
        errno = ENOMEM;
        return 0;
    }
    p = malloc((n + 1) * sizeof(*p));
    if (p)
        wcscpy(p, s);
    return p;
}
wchar_t *wcstok(wchar_t *s, const wchar_t *delimiters, wchar_t **save)
{
    wchar_t *end;
    if (!s)
        s = *save;
    if (!s)
        return 0;
    s += wcsspn(s, delimiters);
    if (!*s) {
        *save = 0;
        return 0;
    }
    end = s + wcscspn(s, delimiters);
    if (*end) {
        *end = 0;
        *save = end + 1;
    } else
        *save = 0;
    return s;
}
wchar_t *wmemchr(const wchar_t *s, wchar_t c, size_t n)
{
    while (n--) {
        if (*s == c)
            return (wchar_t *)s;
        ++s;
    }
    return 0;
}
int wmemcmp(const wchar_t *a, const wchar_t *b, size_t n)
{
    while (n--) {
        if (*a != *b)
            return (*a > *b) - (*a < *b);
        ++a;
        ++b;
    }
    return 0;
}
wchar_t *wmemcpy(wchar_t *d, const wchar_t *s, size_t n)
{
    size_t i;
    for (i = 0; i < n; ++i)
        d[i] = s[i];
    return d;
}
wchar_t *wmemmove(wchar_t *d, const wchar_t *s, size_t n)
{
    size_t i;
    if ((uintptr_t)d <= (uintptr_t)s)
        for (i = 0; i < n; ++i)
            d[i] = s[i];
    else
        while (n) {
            --n;
            d[n] = s[n];
        }
    return d;
}
wchar_t *wmemset(wchar_t *d, wchar_t c, size_t n)
{
    size_t i;
    for (i = 0; i < n; ++i)
        d[i] = c;
    return d;
}
int wcscoll(const wchar_t *a, const wchar_t *b)
{
    return wcscmp(a, b);
}
size_t wcsxfrm(wchar_t *d, const wchar_t *s, size_t n)
{
    size_t count = wcslen(s);
    if (count < n)
        wcscpy(d, s);
    return count;
}
int wcwidth(wchar_t c)
{
    if (!c)
        return 0;
    return iswprint((wint_t)c) ? 1 : -1;
}
int wcswidth(const wchar_t *s, size_t n)
{
    size_t i;
    int width = 0;
    for (i = 0; i < n && s[i]; ++i) {
        int w = wcwidth(s[i]);
        if (w < 0)
            return -1;
        if (w && width == __INT_MAX__) {
            errno = EOVERFLOW;
            return -1;
        }
        width += w;
    }
    return width;
}
