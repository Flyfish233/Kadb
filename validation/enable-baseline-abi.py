#!/usr/bin/env python3
"""Enable compiler ABI inventories without modifying frozen product sources."""
import sys
from pathlib import Path

root = Path(sys.argv[1])
for module in ("kadb", "kadb-mdns"):
    path = root / module / "build.gradle.kts"
    text = path.read_text()
    if "abiValidation" in text:
        raise SystemExit(f"Refusing to alter existing ABI configuration: {path}")
    path.write_text(text + '''
// Validation instrumentation only; production sources remain frozen.
kotlin {
    @OptIn(org.jetbrains.kotlin.gradle.dsl.abi.ExperimentalAbiValidation::class)
    abiValidation()
}
''')
