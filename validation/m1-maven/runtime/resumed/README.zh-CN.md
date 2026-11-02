# 本轮实际构建与执行证据

验证提交：`316c64a9761c16293d7f1f69adc7769393e7a705`。
记录时间：2026-11-02（Asia/Shanghai）。本目录只记录本轮实际执行，不借用旧 CI 的通过结果。

## 结果

| 项目 | 本轮结果 |
| --- | --- |
| Android 生产代码和 AAR 构建 | PASS；首次构建 1m55s，25 个任务实际执行 |
| Android Host 单元测试 | PASS；30 个 suite、102 个 test，0 失败、0 跳过 |
| Linux Native C/BoringSSL、Kotlin、cinterop、链接 | PASS；首次构建 2m12s，15 个任务实际执行 |
| Linux Native 单元测试 | PASS；19 个 suite、63 个 test，0 失败、0 跳过 |
| 同次调用中的 Maven 来源门禁及两组测试重执行 | PASS；30s，39 个任务中 5 个实际执行、34 个已有输出复用 |
| Android ART/模拟器、Darwin、外部 ADB 或真实设备配对 | 本轮未执行 |

固定工具链为 Gradle 9.6.0、项目 Kotlin 2.4.20、AGP 9.4.0、Temurin JDK 25.0.5+8、Android API 37。
Gradle 自身嵌入的 Kotlin 2.3.21 与项目编译器版本分别记录，不能混为一谈。
Linux CMake 3.31.8 在工作区从官方发行包恢复，并核对官方 SHA-256；没有修改 SPAKE2 或 Kadb 生产密码学源码。

## 实际命令

在准备固定 Maven 仓库、设置 JDK25/Android SDK/本机 CMake 路径后，首次执行了：

```sh
./gradlew :kadb:verifyProductionTargetScope :kadb:testAndroidHostTest :kadb:bundleAndroidMainAar --no-build-cache --no-configuration-cache --no-daemon --max-workers=2 --console=plain --stacktrace
./gradlew :kadb:verifyProductionTargetScope :kadb:linuxX64Test --no-build-cache --no-configuration-cache --no-daemon --max-workers=2 --console=plain --stacktrace
```

门禁修改推送后，在上述精确提交上进行同次调用验证；`--rerun` 只强制重新执行两个测试任务：

```sh
./gradlew :kadb:verifySpake2MavenResolution :kadb:verifyProductionTargetScope :kadb:testAndroidHostTest --rerun :kadb:bundleAndroidMainAar :kadb:linuxX64Test --rerun -Pspake2Configurations=androidCompileClasspath,androidRuntimeClasspath,linuxX64CompileKlibraries --no-build-cache --no-configuration-cache --no-daemon --max-workers=2 --console=plain --stacktrace
```

首次构建证明编译和链接确实执行；最后一次调用证明来源门禁和实际测试在同一构建内通过。
最后一次调用复用编译输出的事实已保留在原始日志中，没有将 `UP-TO-DATE` 误报为重新编译。

## 来源报告及文件

- `actual-spake2-maven-resolution.json`：Gradle 任务的原始报告，包含 Android 编译/运行时及 Linux Native KLIB 的六项实物选择。
- `actual-android-maven-resolution.json`、`actual-linux-maven-resolution.json`：上述同一原始报告按配置筛选的视图；每份含 `evidence_derivation` 和原始报告摘要，不冒充独立构建。
- `verified-host-native-exit.json`：最终命令、提交、退出码及构建输入摘要。
- `verified-test-summary.json`：从最终 JUnit XML 生成的逐 suite 计数，要求两类测试实际存在。
- `verified-runtime-result.json`：结果汇总、产物与最终 XML 摘要，明确分离未执行的平台集成和设备配对。
- `toolchain.json`：实际工具链输出及 SDK 元数据。
- `android-host-build.log`、`linux-native-build.log`、`verified-host-native-build.log`：本轮三次构建的原始日志。

Android 和 Linux 均解析到 `spake2ValidatedCandidate` 的真实外部 Maven 模块。
Legacy 与 Primitives 的版本均为 `0.1.0-dev.59105290820b`，报告保留 Gradle 仓库 ID、平台变体及实物摘要。
独立 Java oracle 仍由 Android Host 测试执行。这里的成功不代表 M2 全矩阵或 M3 真机配对已经完成。

## 普通构建入口的补充验证

随后修复了门禁对正常 Native 构建的自动配置选择：它现在读取实际任务图中 Kotlin compilation 的主源码和测试配置。
修复后没有显式指定门禁任务，也没有传入 `spake2Configurations`，执行了：

```sh
./gradlew :kadb:testAndroidHostTest --rerun :kadb:linuxX64Test --rerun --no-build-cache --no-configuration-cache --no-daemon --max-workers=2 --console=plain --stacktrace
```

结果为 **PASS，26s，165 个测试实际执行、0 失败、0 跳过**。编译输出复用，两个测试任务强制重执行。
报告中的 `scheduled_compilations` 非空，并实际包含 Android main/hostTest 与 Linux Native main/test；
六个必要配置各有同版 Legacy 和 Primitives，仓库 ID/名称及实物摘要均验证成功。

该调用额外记录了 Kotlin 模型已经解析的四个 Darwin Maven 配置，总计 20 项实物选择；没有执行 Darwin 编译、链接或测试。
原始报告、命令、范围断言和逐 suite 结果分别保存在 `scheduled-default-maven-resolution.json`、
`scheduled-default-exit.json`、`scheduled-default-scope-assertions.json`、`scheduled-default-test-summary.json`，
原始日志为 `scheduled-default-build.log`。该修复的实测脚本 SHA-256 为
`6d1a1ad528528e0925b7b3ecb556217399368c604e4c8f53980048b177821af1`；
命令记录保留测试时 HEAD 和未提交构建输入差异摘要，后续证据提交可按相同文件摘要核对。
