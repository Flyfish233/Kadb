#!/usr/bin/env python3
"""Dump the real JAR/AAR's Kotlin-public ABI, without native target inference.

Uses JetBrains binary-compatibility-validator's public API. Tool dependencies
are version- and SHA256-pinned, separate from product runtime dependencies.
Raw javap inventory and external consumer checks complement this visibility-
aware inventory; none alone proves behavioral or source compatibility.
"""
import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
from urllib.request import urlopen
import zipfile

DEPENDENCIES = [
    ("org/jetbrains/kotlinx/binary-compatibility-validator/0.18.2/binary-compatibility-validator-0.18.2.jar", "c335b81b8bf0b66037520c82c1bd70b13bc9b617bdf32055d997100c96a97bca"),
    ("org/jetbrains/kotlin/kotlin-metadata-jvm/2.4.20/kotlin-metadata-jvm-2.4.20.jar", "98d9b1847908adfde7a8b2d4cc35708d7ddccae0698cec56bcb506bcf9392595"),
    ("org/jetbrains/kotlin/kotlin-stdlib/2.4.20/kotlin-stdlib-2.4.20.jar", "2226de463d309d4a5500a481320b3dea515a6981dcae1def531fbc158884e25f"),
    ("org/ow2/asm/asm/9.8/asm-9.8.jar", "876eab6a83daecad5ca67eb9fcabb063c97b5aeb8cf1fca7a989ecde17522051"),
    ("org/ow2/asm/asm-tree/9.8/asm-tree-9.8.jar", "14b7880cb7c85eed101e2710432fc3ffb83275532a6a894dc4c4095d49ad59f1"),
]
SOURCE = r'''
import java.util.Collections;
import java.util.jar.JarFile;
import kotlinx.validation.api.KotlinSignaturesLoadingKt;
public class DumpKotlinApi {
    public static void main(String[] args) throws Exception {
        try (var jar = new JarFile(args[0])) {
            var signatures = KotlinSignaturesLoadingKt.loadApiFromJvmClasses(jar, name -> true);
            var visible = KotlinSignaturesLoadingKt.filterOutNonPublic(
                signatures, Collections.emptyList(), Collections.emptyList());
            KotlinSignaturesLoadingKt.dump(visible, System.out);
        }
    }
}
'''


def capture(archive, output, cache):
    cache.mkdir(parents=True, exist_ok=True)
    jars = []
    for path, expected in DEPENDENCIES:
        local = cache / Path(path).name
        if not local.exists():
            with urlopen("https://repo.maven.apache.org/maven2/" + path, timeout=60) as response:
                data = response.read()
            if hashlib.sha256(data).hexdigest() != expected:
                raise RuntimeError("Dependency checksum mismatch: " + path)
            local.write_bytes(data)
        if hashlib.sha256(local.read_bytes()).hexdigest() != expected:
            raise RuntimeError("Cached dependency checksum mismatch: " + path)
        jars.append(str(local.resolve()))
    with tempfile.TemporaryDirectory(prefix="kadb-kotlin-abi-") as name:
        folder = Path(name)
        source = folder / "DumpKotlinApi.java"
        source.write_text(SOURCE)
        classpath = os.pathsep.join(jars)
        subprocess.run(["javac", "-cp", classpath, "-d", name, str(source)], check=True)
        jar = archive.resolve()
        if archive.suffix == ".aar":
            with zipfile.ZipFile(archive) as aar:
                jar = folder / "classes.jar"
                jar.write_bytes(aar.read("classes.jar"))
        raw = subprocess.check_output(["java", "-cp", classpath + os.pathsep + name,
                                       "DumpKotlinApi", str(jar)], text=True)
        if "com/flyfishxu/kadb/" not in raw or " class " not in raw:
            raise RuntimeError("No Kadb public ABI in " + str(archive))
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(raw.rstrip() + "\n")
        print(f"Captured {len(raw.splitlines())} Kotlin-public ABI lines from {archive.name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--cache", type=Path, default=Path(".gradle/kadb-abi-tools"))
    args = parser.parse_args()
    capture(args.archive, args.output, args.cache)
