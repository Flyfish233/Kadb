#!/usr/bin/env bash
set -euo pipefail
framework=${1:?framework directory containing Kadb.framework}
output=${2:?output directory}
mkdir -p "$output"
case $(uname -m) in
  arm64) target=arm64-apple-macos12.0;;
  x86_64) target=x86_64-apple-macos12.0;;
  *) exit 2;;
esac
xcrun swiftc validation/swift/Consumer.swift -target "$target" \
  -F "$framework" -framework Kadb -framework Foundation -framework Security \
  -lresolv -Xlinker -dead_strip -Xlinker -map -Xlinker "$output/swift-consumer.map" \
  -o "$output/swift-consumer"
xcrun nm -u "$output/swift-consumer" > "$output/swift-consumer-imports.log"
xcrun otool -L "$output/swift-consumer" > "$output/swift-consumer-libraries.log"
"$output/swift-consumer" | tee "$output/swift-consumer.log"
grep -q '^SWIFT_CONSUMER_OK ' "$output/swift-consumer.log"
