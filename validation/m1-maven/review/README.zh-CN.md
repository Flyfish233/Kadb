# M1 独立只读复核：协议边界与历史 CI

本目录核对范围是 Maven 集成前后的协议文件一致性、实际构建入口和已有失败身份；没有启动新的密码学审计，没有重新执行 iOS Simulator、Android Emulator 或真实设备配对。

## 固定基线与工具链

- Kadb 基线：`49a88b14e9b731e4c086c920eb74664450c79d9f`。
- 实际配置：Gradle 9.6.0、Kotlin 2.4.20、AGP 9.4.0、Java toolchain 25、Android compileSdk 37 / minSdk 23。
- 当前生产目标保留 Android、Linux 和 Darwin；没有 desktop JVM 生产目标。Android host tests 不等同于 Android ART 或真实平台 TLS provider 验证。
- 原 Java oracle 是 `com.github.Flyfish233:spake2-java:1.1.1`，位于 `androidHostTest`。Maven 迁移必须保留该独立 oracle。

## 有界 M1 验证入口

既有 workflow 的真实 Android 构建任务是 `:kadb:bundleAndroidMainAar`，host 测试任务是 `:kadb:testAndroidHostTest`；`verifyProductionTargetScope` 可核对目标没有退化。

在候选 Maven 来源验证通过后，建议执行：

```sh
./gradlew :kadb:verifyProductionTargetScope :kadb:testAndroidHostTest :kadb:bundleAndroidMainAar --no-configuration-cache --console=plain --stacktrace
```

如需要更小的针对性 host 集合，可对 `:kadb:testAndroidHostTest` 使用 `--tests 'com.flyfishxu.kadb.pair.*'`。当前六个 pairing 测试类含 24 个测试方法，覆盖独立 BoringSSL 固定向量、Java oracle TLS peer、错误配对码、PeerInfo 约束、HKDF/AES-GCM 固定向量、认证失败销毁、重复初始化、nonce 耗尽、取消及握手终止。这里记录测试的既有定义，不表示本轮已经执行。

Native 只有在现成工具链可用时才考虑 `:kadb:compileKotlinLinuxX64` 或 `:kadb:linuxX64Test`。不要为了 M1 扩展为 Darwin、Simulator、emulator 和设备矩阵。

## 协议不变门禁

`protocol-baseline.json` 记录 11 个关键生产文件在固定基线的 Git blob、SHA-256 和长度，初始核对全部一致。它包括：

- `LegacyPasswordScalarMode.HARDENED`、`Role.ALICE` 和 `Spake2Exception` 的原异常映射。
- `adb pair client\u0000`、`adb pair server\u0000` 两个尾部 NUL 身份。
- Android 的 `adb-label\u0000` 和 Native `sizeof(label)` 的 64-byte TLS exporter，密码与 exporter 拼接及原清理流程。
- 原 HKDF-SHA256、16-byte AES key、AES-128-GCM、双向独立从零递增的原 nonce 协议。
- PeerInfo 的认证标签验证、8192-byte 长度、设备 GUID 类型与 C 字符串约束。
- 一次性状态机、失败销毁、worker 拥有 crypto 清理、原异常传播。

文件一致性门禁只能证明本次迁移没有改动这些 Kadb 实现。它不能把既有协议风险或未完成的运行时保证升级为 PASS。

## 已存在的基线失败

2026-11-02（Asia/Singapore）通过 GitHub API 重新读取 [run 40331404006](https://github.com/Flyfish233/Kadb/actions/runs/40331404006)，其 `head_sha` 正是固定基线 `49a88b14...`。原始 job/step 状态摘录见 `baseline-ci-runs.json`，失败原始日志行见 `baseline-failure-excerpts.json`。

| 基线 job | 原有结论 | 实际边界 |
| --- | --- | --- |
| corresponding-source | SUCCESS | 原内嵌源码版本的源码收集成功；不能代替本次 Maven 源码收集 |
| android-and-protocol | SUCCESS | 原基线 Android build/host/ABI/source-inventory 步骤成功 |
| linux-native | SUCCESS | 原基线 Native 编译、测试、外部 peer 和 C oracle 步骤成功 |
| Intel macOS | SUCCESS | 原基线 Native/Swift/framework 步骤成功 |
| ARM macOS / iOS Simulator | FAILURE | macOS 和 iOS 编译、Simulator tests 已成功；后续 `Actual simulator pairing and exported API comparison` 步骤失败 |
| emulator-adbd | FAILURE | 两个 driver 均报告 emulator 未在 120 秒内 ready；Native API 与 ART 各自 `checks_executed: 0` |

ARM job 的测试汇总记录 140 个执行测试、0 失败、没有缺失测试组；外部 Simulator pairing 返回 `status: failed`。目前保留的日志不足以确定该 pairing 失败的内部原因，因此不把它笼统定性为环境问题或新产品缺陷。Android Emulator 日志则明确给出 ready 超时；本轮不重试这两类已有失败。

上述失败已在本次 Maven 分支创建之前存在，来源 SHA 不含迁移改动。后续 M1 host 构建若出现新的失败，需要根据具体堆栈与同环境固定基线对照判断，不能因为旧 CI 总体失败就自动归为历史问题。
