#!/usr/bin/env bash
set -euo pipefail

# Build host-only C bridge tests with the same verified BoringSSL source used by
# Gradle. Pass an absolute source path and an optional output directory.
repository=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
boringssl_source=${1:?Usage: test-native-c.sh BORINGSSL_SOURCE [BUILD_DIRECTORY]}
build_directory=${2:-"$repository/kadb/build/native/host-tests"}
cmake_command=${CMAKE:-cmake}
"$cmake_command" -S "$repository/kadb/src/nativeInterop" -B "$build_directory" \
  -DBORINGSSL_SOURCE="$boringssl_source" -DCMAKE_BUILD_TYPE=Release -DKADB_NATIVE_TESTS=ON
"$cmake_command" --build "$build_directory" --target kadb_transport_test --parallel 2
ctest_command=${CTEST:-"$(dirname -- "$(command -v "$cmake_command")")/ctest"}
"$ctest_command" --test-dir "$build_directory" --verbose

if [[ ${KADB_SANITIZE:-0} == 1 ]]; then
  sanitizer_directory="$build_directory/sanitizers"
  mkdir -p "$sanitizer_directory"
  for source in cpp/kadb_transport.c tests/transport_test.c; do
    object="$sanitizer_directory/$(basename "$source").o"
    "${CC:-cc}" -std=c11 -D_GNU_SOURCE -DBORINGSSL_PREFIX=KADB_BSSL \
      -UNDEBUG -Wall -Wextra -Werror -fsanitize=address,undefined \
      -fno-omit-frame-pointer -g -O1 \
      -I "$repository/kadb/src/nativeInterop/cinterop" -I "$boringssl_source/include" \
      -c "$repository/kadb/src/nativeInterop/$source" -o "$object"
  done
  "${CXX:-c++}" -fsanitize=address,undefined \
    "$sanitizer_directory/kadb_transport.c.o" "$sanitizer_directory/transport_test.c.o" \
    "$build_directory/lib/libssl.a" "$build_directory/lib/libcrypto.a" \
    -lpthread -o "$sanitizer_directory/transport_test"
  ASAN_OPTIONS=detect_leaks=1:abort_on_error=1 "$sanitizer_directory/transport_test"
fi
