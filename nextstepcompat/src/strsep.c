/* BSD delimiter splitter for callers using empty fields.
   SPDX-License-Identifier: 0BSD */
#include <stddef.h>
#include <string.h>

char *strsep(char **cursor, const char *delimiters)
{
    char *start = *cursor;
    char *end;
    if (!start) return NULL;
    end = start + strcspn(start, delimiters);
    if (*end) { *end = '\0'; *cursor = end + 1; }
    else *cursor = NULL;
    return start;
}
