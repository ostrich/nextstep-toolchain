#!/bin/sh
if test -x /private/tmp/perl-test/timestamp-math-tests; then
    payload=/private/tmp/perl-test
elif test -x /ssh-test/timestamp-math-tests; then
    payload=/ssh-test
else
    payload=/port-test
fi
cd "$payload" || exit 90
./timestamp-math-tests
r=$?
echo PERL-SMOKE-SUITE "$r"
exit "$r"
