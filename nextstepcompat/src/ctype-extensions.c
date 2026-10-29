/* BSD ASCII extension function forms. SPDX-License-Identifier: 0BSD */
int ns33_isascii(int c) { return (unsigned int)c <= 127; }
int ns33_toascii(int c) { return c & 127; }
