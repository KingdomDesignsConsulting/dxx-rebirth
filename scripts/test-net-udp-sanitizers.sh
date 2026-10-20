#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
CXX=${CXX:-clang++}
OUT=${TMPDIR:-/tmp}/dxx-net-udp-packet-safety
"$CXX" -std=c++20 -O1 -g -Wall -Wextra -Werror \
  -fsanitize=address,undefined -fno-omit-frame-pointer \
  -I"$ROOT/common/include" \
  "$ROOT/tests/net_udp_packet_safety_test.cpp" -o "$OUT"
LEAK_CHECK=1
# Apple ASan supports address checks but not LeakSanitizer.
if [ "$(uname -s)" = Darwin ]; then LEAK_CHECK=0; fi
ASAN_OPTIONS=detect_leaks=$LEAK_CHECK UBSAN_OPTIONS=halt_on_error=1 "$OUT"
printf '%s\n' 'net_udp malformed-packet ASan/UBSan tests passed'
