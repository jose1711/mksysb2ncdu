#!/bin/sh
# Run the test suite: convert the sample AIX backup and compare it with
# the `restore -Tvqf` listing captured on AIX 7.3 and with the expected JSON.
set -e
cd "$(dirname "$0")"
out=$(mktemp)
trap 'rm -f "$out"' EXIT
python3 ../mksysb2ncdu -q -e sample.backup -o "$out"
python3 compare_restore.py "$out" sample.restore-T
# stdin must give the same result as a seekable file
python3 ../mksysb2ncdu -q -e < sample.backup | cmp - "$out"
cmp "$out" sample.ncdu.json
# without -e: ncdu 1.x compatible, sizes only
python3 ../mksysb2ncdu -q sample.backup | grep -q '"uid"\|"mode"' && { echo "uid/mode without -e"; exit 1; }
echo "OK"
