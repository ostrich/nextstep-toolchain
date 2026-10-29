/* Single-byte contract checks. Host builds use -fshort-wchar and no aliases.
   SPDX-License-Identifier: 0BSD */
#include <wchar.h>
#include <wctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <errno.h>
#include <limits.h>
static unsigned long checks;
#define CHECK(x)                                                               \
    do {                                                                       \
        ++checks;                                                              \
        if (!(x)) {                                                            \
            fprintf(stderr, "singlebyte failure line %d: %s\n", __LINE__, #x); \
            return 1;                                                          \
        }                                                                      \
    } while (0)
_Static_assert(sizeof(wchar_t) == 2, "preserve NeXT wide ABI");
_Static_assert(sizeof(wint_t) == 4, "WEOF distinct from all wide code units");
_Static_assert(sizeof(mbstate_t) == 16, "reserved conversion state ABI");

static int conversion(void)
{
    unsigned c;
    mbstate_t state = {0};
    wchar_t wc;
    char out;
    const char *p;
    const wchar_t *q;
    CHECK(mbsinit(0));
    CHECK(mbsinit(&state));
    CHECK(ns33_mb_cur_max() == 1);
    state.reserved[2] = 1;
    CHECK(!mbsinit(&state));
    CHECK(mbrtowc(0, 0, 0, &state) == 0);
    CHECK(mbsinit(&state));
    for (c = 0; c < 256; ++c) {
        char bytes[2] = {(char)c, 0};
        wc = 0x4321;
        out = 42;
        errno = 71;
        CHECK(mbrtowc(&wc, bytes, 0, &state) == (size_t)-2);
        CHECK(wc == 0x4321 && errno == 71 && mbsinit(&state));
        CHECK(mbrtowc(&wc, bytes, 1, &state) == (c ? 1 : 0));
        CHECK(wc == c);
        CHECK(mbrtowc(0, bytes, 1, 0) == (c ? 1 : 0));
        CHECK(mbrlen(bytes, 1, 0) == (c ? 1 : 0));
        CHECK(wcrtomb(&out, (wchar_t)c, &state) == 1);
        CHECK((unsigned char)out == c);
        CHECK(btowc((int)c) == c && wctob(c) == (int)c);
        wc = 0x4321;
        CHECK(ns33_mbtowc(&wc, bytes, 1) == (c ? 1 : 0));
        CHECK(wc == c);
        CHECK(ns33_mblen(bytes, 1) == (c ? 1 : 0));
        out = 42;
        CHECK(ns33_wctomb(&out, (wchar_t)c) == 1 && (unsigned char)out == c);
    }
    for (c = 256; c <= 65535; ++c) {
        out = 42;
        errno = 0;
        CHECK(wcrtomb(&out, (wchar_t)c, &state) == (size_t)-1);
        CHECK(out == 42 && errno == EILSEQ && mbsinit(&state));
        CHECK(wctob(c) == EOF);
    }
    CHECK(btowc(EOF) == WEOF && btowc(256) == WEOF);
    CHECK(wctob(WEOF) == EOF);
    CHECK(wcrtomb(0, (wchar_t)0xffff, &state) == 1);
    CHECK(ns33_wctomb(0, (wchar_t)0xffff) == 0);
    CHECK(ns33_mblen(0, 0) == 0 && ns33_mbtowc(0, 0, 0) == 0);
    errno = 0;
    CHECK(ns33_mblen("x", 0) == -1 && errno == EILSEQ);
    wc = 42;
    errno = 0;
    CHECK(ns33_mbtowc(&wc, "x", 0) == -1 && errno == EILSEQ && wc == 42);
    {
        wchar_t invalid[] = {'a', 256, 0};
        char dest[5] = {42, 42, 42, 42, 42};
        q = invalid;
        errno = 0;
        CHECK(wcsrtombs(dest, &q, 5, &state) == (size_t)-1);
        CHECK(q == invalid + 1 && dest[0] == 'a' && dest[1] == 42 &&
              errno == EILSEQ);
        q = invalid;
        errno = 0;
        CHECK(wcsrtombs(0, &q, 0, &state) == (size_t)-1 && q == invalid &&
              errno == EILSEQ);
        q = invalid;
        CHECK(wcsnrtombs(dest, &q, 1, 5, &state) == 1 && q == invalid + 1);
        q = invalid + 1;
        CHECK(wcsrtombs(dest, &q, 0, &state) == 0 && q == invalid + 1);
        q = invalid + 1;
        CHECK(wcsnrtombs(dest, &q, 0, 5, &state) == 0 && q == invalid + 1);
    }
    {
        char bytes[] = {(char)0x80, (char)0xff, 0};
        wchar_t dest[4] = {42, 42, 42, 42};
        p = bytes;
        CHECK(mbsrtowcs(dest, &p, 4, &state) == 2 && p == 0);
        CHECK(dest[0] == 128 && dest[1] == 255 && dest[2] == 0 &&
              dest[3] == 42);
    }
    return 0;
}
static int arrays(void)
{
    unsigned length, bound, limit, i;
    for (length = 0; length < 10; ++length)
        for (bound = 0; bound < 12; ++bound)
            for (limit = 0; limit < 12; ++limit) {
                char bytes[16], encoded[16];
                wchar_t wide[16], decoded[16];
                const char *p;
                const wchar_t *q;
                size_t n = length < bound ? length : bound,
                       count = n < limit ? n : limit;
                int terminated = length < bound && length < limit;
                mbstate_t state = {0};
                for (i = 0; i < 16; ++i) {
                    bytes[i] = (char)(128 + i);
                    wide[i] = 128 + i;
                    decoded[i] = 0x5555;
                    encoded[i] = 42;
                }
                bytes[length] = 0;
                wide[length] = 0;
                p = bytes;
                CHECK(mbsnrtowcs(decoded, &p, bound, limit, &state) == count);
                CHECK(p == (terminated ? 0 : bytes + count));
                q = wide;
                CHECK(wcsnrtombs(encoded, &q, bound, limit, &state) == count);
                CHECK(q == (terminated ? 0 : wide + count));
                for (i = 0; i < count; ++i)
                    CHECK(decoded[i] == (unsigned char)bytes[i] &&
                          (unsigned char)encoded[i] == wide[i]);
                CHECK(decoded[count] == (terminated ? 0 : 0x5555));
                CHECK(encoded[count] == (terminated ? 0 : 42));
                CHECK(decoded[count + 1] == 0x5555 && encoded[count + 1] == 42);
                p = bytes;
                q = wide;
                CHECK(mbsnrtowcs(0, &p, bound, limit, &state) == n &&
                      p == bytes);
                CHECK(wcsnrtombs(0, &q, bound, limit, &state) == n &&
                      q == wide);
                CHECK(ns33_mbstowcs(0, bytes, 0) == length);
                CHECK(ns33_wcstombs(0, wide, 0) == length);
                CHECK(mbsinit(&state));
            }
    return 0;
}
static int character_types(void)
{
    static const char *const names[] = {"alnum", "alpha", "blank", "cntrl",
                                        "digit", "graph", "lower", "print",
                                        "punct", "space", "upper", "xdigit"};
    int (*functions[])(wint_t) = {iswalnum, iswalpha, iswblank, iswcntrl,
                                  iswdigit, iswgraph, iswlower, iswprint,
                                  iswpunct, iswspace, iswupper, iswxdigit};
    unsigned c, i;
    for (c = 0; c <= 65535; ++c) {
        int expected[12] = {0};
        if (c < 256) {
            expected[0] = !!isalnum(c);
            expected[1] = !!isalpha(c);
            expected[2] = c == ' ' || c == '\t';
            expected[3] = !!iscntrl(c);
            expected[4] = !!isdigit(c);
            expected[5] = !!isgraph(c);
            expected[6] = !!islower(c);
            expected[7] = !!isprint(c);
            expected[8] = !!ispunct(c);
            expected[9] = !!isspace(c);
            expected[10] = !!isupper(c);
            expected[11] = !!isxdigit(c);
        }
        for (i = 0; i < 12; ++i) {
            CHECK(functions[i](c) == expected[i]);
            CHECK(iswctype(c, wctype(names[i])) == expected[i]);
        }
        CHECK(towlower(c) == (c < 256 ? (wint_t)tolower(c) : c));
        CHECK(towupper(c) == (c < 256 ? (wint_t)toupper(c) : c));
        CHECK(wcwidth((wchar_t)c) == (c == 0 ? 0 : expected[7] ? 1 : -1));
    }
    CHECK(wctype("nonsense") == 0 && wctype("") == 0);
    CHECK(wctrans("nonsense") == 0 && wctrans("") == 0);
    CHECK(towctrans('A', wctrans("tolower")) == 'a');
    CHECK(towctrans('a', wctrans("toupper")) == 'A');
    CHECK(towctrans('A', 0) == 'A');
    CHECK(towlower(WEOF) == WEOF && towupper(WEOF) == WEOF);
    for (i = 0; i < 12; ++i)
        CHECK(functions[i](WEOF) == 0);
    CHECK(iswctype('A', 0) == 0);
    CHECK(wcswidth(L"abc", 3) == 3 && wcswidth(L"a\tb", 3) == -1);
    CHECK(wcswidth(L"abc", 0) == 0 && wcswidth(L"abc", 2) == 2);
    return 0;
}
static int strings(void)
{
    wchar_t a[32], b[32], expected[32], *p, *save = 0;
    unsigned start, dest, n, i;
    CHECK(wcslen(L"abc") == 3 && wcsnlen(L"abc", 2) == 2);
    CHECK(wcsncmp(L"a", L"abcd", 1) == 0 && wcsncmp(L"a", L"abcd", 2) < 0);
    CHECK(wcscmp(L"a", L"b") < 0 && wcscoll(L"abc", L"abc") == 0);
    wcscpy(a, L"abca");
    CHECK(wcschr(a, L'a') == a && wcsrchr(a, L'a') == a + 3);
    CHECK(wcschr(a, 0) == a + 4 && wcsrchr(a, 0) == a + 4);
    CHECK(wcsstr(a, L"bc") == a + 1 && wcsstr(a, L"") == a &&
          !wcsstr(a, L"abcab"));
    CHECK(wcspbrk(a, L"cx") == a + 2 && !wcspbrk(a, L"xy"));
    CHECK(wcsspn(a, L"ab") == 2 && wcscspn(a, L"ca") == 0);
    wmemset(b, 42, 32);
    wcsncpy(b, L"abc", 5);
    CHECK(b[0] == 'a' && b[2] == 'c' && b[3] == 0 && b[4] == 0 && b[5] == 42);
    CHECK(wcsncpy(b, L"long", 0) == b && b[0] == 'a');
    wcscpy(b, L"a");
    wcscat(b, L"b");
    wcsncat(b, L"cdef", 2);
    CHECK(!wcscmp(b, L"abcd"));
    p = wcsdup(b);
    CHECK(p && !wcscmp(p, b));
    free(p);
    wmemset(b, 42, 32);
    CHECK(wcsxfrm(b, L"abc", 3) == 3 && b[0] == 42);
    CHECK(wcsxfrm(b, L"abc", 4) == 3 && !wcscmp(b, L"abc"));
    CHECK(wcsxfrm(0, L"abc", 0) == 3);
    wcscpy(a, L",,one;two,,");
    p = wcstok(a, L",;", &save);
    CHECK(p && !wcscmp(p, L"one"));
    p = wcstok(0, L",;", &save);
    CHECK(p && !wcscmp(p, L"two"));
    CHECK(!wcstok(0, L",;", &save));
    CHECK(!wcstok(0, L",;", &save));
    for (start = 0; start < 12; ++start)
        for (dest = 0; dest < 12; ++dest)
            for (n = 0; n < 12; ++n) {
                for (i = 0; i < 32; ++i)
                    a[i] = expected[i] = (wchar_t)(0x100 + i);
                memcpy(b, expected + start, n * sizeof(wchar_t));
                memcpy(expected + dest, b, n * sizeof(wchar_t));
                CHECK(wmemmove(a + dest, a + start, n) == a + dest);
                CHECK(!memcmp(a, expected, sizeof(a)));
            }
    wmemset(a, 0x1234, 32);
    wmemcpy(b, a, 32);
    CHECK(!wmemcmp(a, b, 32));
    b[10] = 0xabcd;
    CHECK(wmemcmp(a, b, 32) < 0 && wmemchr(b, 0xabcd, 32) == b + 10);
    CHECK(wmemchr(b, 0xabcd, 10) == 0 && wmemcmp(a, b, 0) == 0);
    return 0;
}
int main(void)
{
    if (conversion() || arrays() || character_types() || strings())
        return 1;
#ifdef __NeXT__
    {
        mbstate_t state = {0};
        wchar_t w = 0;
        char c = 0;
        const char *s = "A";
        CHECK(MB_CUR_MAX == 1);
        CHECK(mbrtowc(&w, s, 1, &state) == 1 && w == 'A');
        CHECK(wcrtomb(&c, w, &state) == 1 && c == 'A');
        CHECK(iswalpha(w) && towlower(w) == 'a');
        CHECK(wcslen(L"abc") == 3 && mbsinit(&state));
        CHECK(mbtowc(&w, "\377", 1) == 1 && w == 255);
        CHECK(wctomb(&c, 256) == -1);
    }
#endif
    printf("singlebyte: %lu checks passed\n", checks);
    return 0;
}
