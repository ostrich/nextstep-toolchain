/* Classification follows the native single-byte C tables, not Unicode.
   SPDX-License-Identifier: 0BSD */
#include <wctype.h>
#include <ctype.h>
#include <string.h>

enum {
    CLASS_ALNUM = 1,
    CLASS_ALPHA,
    CLASS_BLANK,
    CLASS_CNTRL,
    CLASS_DIGIT,
    CLASS_GRAPH,
    CLASS_LOWER,
    CLASS_PRINT,
    CLASS_PUNCT,
    CLASS_SPACE,
    CLASS_UPPER,
    CLASS_XDIGIT
};
static const char *const classes[] = {"alnum", "alpha", "blank", "cntrl",
                                      "digit", "graph", "lower", "print",
                                      "punct", "space", "upper", "xdigit"};

int iswctype(wint_t wc, wctype_t type)
{
    int c;
    if (wc > 255)
        return 0;
    c = (int)wc;
    switch (type) {
    case CLASS_ALNUM:
        return !!isalnum(c);
    case CLASS_ALPHA:
        return !!isalpha(c);
    case CLASS_BLANK:
        return c == ' ' || c == '\t';
    case CLASS_CNTRL:
        return !!iscntrl(c);
    case CLASS_DIGIT:
        return !!isdigit(c);
    case CLASS_GRAPH:
        return !!isgraph(c);
    case CLASS_LOWER:
        return !!islower(c);
    case CLASS_PRINT:
        return !!isprint(c);
    case CLASS_PUNCT:
        return !!ispunct(c);
    case CLASS_SPACE:
        return !!isspace(c);
    case CLASS_UPPER:
        return !!isupper(c);
    case CLASS_XDIGIT:
        return !!isxdigit(c);
    default:
        return 0;
    }
}
wctype_t wctype(const char *name)
{
    unsigned i;
    for (i = 0; i < sizeof(classes) / sizeof(classes[0]); ++i)
        if (!strcmp(name, classes[i]))
            return i + 1;
    return 0;
}
#define CLASSIFIER(name, code)                                                 \
    int isw##name(wint_t wc)                                                   \
    {                                                                          \
        return iswctype(wc, code);                                             \
    }
CLASSIFIER(alnum, CLASS_ALNUM)
CLASSIFIER(alpha, CLASS_ALPHA)
CLASSIFIER(blank, CLASS_BLANK)
CLASSIFIER(cntrl, CLASS_CNTRL)
CLASSIFIER(digit, CLASS_DIGIT)
CLASSIFIER(graph, CLASS_GRAPH)
CLASSIFIER(lower, CLASS_LOWER)
CLASSIFIER(print, CLASS_PRINT)
CLASSIFIER(punct, CLASS_PUNCT)
CLASSIFIER(space, CLASS_SPACE)
CLASSIFIER(upper, CLASS_UPPER)
CLASSIFIER(xdigit, CLASS_XDIGIT)
#undef CLASSIFIER
wint_t towlower(wint_t wc)
{
    return wc > 255 ? wc : (wint_t)tolower((int)wc);
}
wint_t towupper(wint_t wc)
{
    return wc > 255 ? wc : (wint_t)toupper((int)wc);
}
wctrans_t wctrans(const char *name)
{
    if (!strcmp(name, "tolower"))
        return 1;
    if (!strcmp(name, "toupper"))
        return 2;
    return 0;
}
wint_t towctrans(wint_t wc, wctrans_t type)
{
    return type == 1 ? towlower(wc) : type == 2 ? towupper(wc) : wc;
}
