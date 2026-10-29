#!/bin/sh
cd /port-test || exit 80
./watchdog 60 /bin/cc -O2 layout.c check.c -o native > native-build.txt 2>&1
result=$?
cat native-build.txt
test "$result" = 0 || exit 81
failed=0
for variant in native old disabled fixed; do
 ./watchdog 10 "./$variant" > "$variant.log" 2>&1
 result=$?
 echo COMPILER-CASE "$variant" EXIT "$result"
 cat "$variant.log"
 case "$variant" in
 old)
  if test "$result" != 1; then failed=1; fi
  grep '^FLOAT-FRAME-SUITE failures=[1-4] checks=4$' "$variant.log" >/dev/null || failed=1
  ;;
 *)
  if test "$result" != 0; then failed=1; fi
  grep '^FLOAT-FRAME-SUITE failures=0 checks=4$' "$variant.log" >/dev/null || failed=1
  ;;
 esac
done
if test "$failed" = 0; then echo PORTS-SUITE 0; fi
exit "$failed"
