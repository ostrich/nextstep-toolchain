# Time formatting

The C/POSIX-locale formatter and Gregorian helpers come from musl 1.2.6.
The release and pristine file hashes are pinned in sources.json. The patch
namespaces internal symbols, supplies C-locale names and patterns, and uses
the original NeXT struct tm fields for zone names and UTC offsets.

Only applications built with NextStepCompat select ns33_strftime. Other
LC_TIME locales are delegated to the original native strftime, preserving
their existing behavior rather than substituting English names. No modern
locale database or strftime_l interface is provided.

Formatting a struct tm does not require converting it to native time_t.
Expanded years and ISO weeks therefore work beyond the native 32-bit epoch
range. This does not extend time_t, mktime, localtime or kernel clock limits.

COPYRIGHT contains the upstream MIT license. The private adapter and locale
data are 0BSD. No installed system library is replaced.
