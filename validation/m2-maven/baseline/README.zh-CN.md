# M2 历史基线：失败身份与执行边界

核对日期：2026-11-02（Asia/Singapore）。固定基线为
`49a88b14e9b731e4c086c920eb74664450c79d9f`，原 CI 为
[40331404006](https://github.com/Flyfish233/Kadb/actions/runs/40331404006)。
本目录只冻结历史证据，不表示本轮 M2 已执行任何平台。

## Darwin

固定基线的 macOS Intel job 成功。ARM job 的 macOS 编译、测试、外部 Java peer、Swift consumer、
Simulator 启动，以及 iOS 编译／单元测试步骤成功；Kadb 与 mDNS 跨 macOS Arm64／iOS Simulator
Arm64 的汇总为 **140 个执行、0 失败**。本轮从原始 artifact 恢复了精确测试汇总：

| 目标 | Kadb | mDNS |
| --- | --- | --- |
| macOS Arm64 | 65 个执行、0 失败 | 5 个执行、0 失败 |
| iOS Simulator Arm64 | 65 个执行、0 失败、1 个 skipped | 5 个执行、0 失败 |

该 skipped 项是需要显式启用的 `JvmPairingInteropTest`；汇总没有把它计入执行数。独立 peer
流程的结果单独记录如下，不能以这个跳过项替代。

随后 `Actual simulator pairing and exported API comparison` 步骤中的外部配对失败。
此前保留的 step 日志只有 `status: failed`。本轮重新下载并验证原始 Darwin artifact
**12655313986** 后，恢复了内部报告：`xcrun simctl list devices booted --json` 在 **10 秒**后
触发 `TimeoutExpired`，发生在 Native consumer 命令生成／执行之前。Java peer 已就绪，随后被
driver 清理终止（退出码 143）；报告没有 `native_command` 或 Native 执行结果。
这将历史故障定位为 **Simulator 清单预检超时**，协议执行应记为 **NOT VERIFIED**，不能声称
SPAKE2 或 TLS 配对断言失败。为什么该次系统清单查询变慢仍未确定。
由于 API 比较排在失败命令后，不能从该失败步骤推断 API 比较已通过；M2 应拆分配对与 API 门禁。

更早的 `35e002e721d8610dfd08d374fd41cbf666f16c35` 与
`696a85f22f25407f92754361b18ae6fd0c2cdba7` 都有 Simulator 配对成功报告：各完成一个正向会话和
一个错误配对码拒绝，共两项。这证明历史执行曾成功，但不能替代当前固定基线或本轮 Maven 结果。
原工程和原 workflow 没有 `iosX64` 实际覆盖，该项必须独立取得构建与执行证据。

## Android：已定位到 TCP 模式切换后的离线

本轮重新下载原始小型 artifact **12656905230**，核对 GitHub 返回的 ZIP SHA-256：
`54266fc0070d36b4f596768ccbbb96eb9d9029570ad7696db4f2e8b7090825fe`。
完整原包保存在 `emulator-40331404006.zip`（25,634 bytes），命令摘录保存在
`emulator-command-excerpts.json`。原包包含两个 driver 的完整命令流水、报告、模拟器日志及环境版本。

原始日志将之前笼统的“模拟器未就绪”细化为以下顺序：

1. Emulator 在 **29,565 ms** 完成启动。Native driver 的命令 6 返回 `device`，命令 7 返回
   `sys.boot_completed=1`。
2. 命令 19 的 `adb root` 成功；命令 20–22 再次确认设备就绪、启动完成且 UID 为 0。
3. 命令 23 执行 `adb tcpip 5556`，返回码 0。命令 24 开始，`emulator-5554` 持续返回
   `device offline`／`not found`，后续恢复步骤也失败。
4. ART driver 在该 Native driver 之后运行，继承了离线模拟器，并在安装／Instrumentation 之前
   超时。两个 driver 的产品断言执行数都是 **0**。

因此，历史故障已经发生在 Maven 迁移之前，直接观察到的边界是 **adbd TCP 模式切换之后的离线**，
而非初次冷启动过慢。日志尚未证明 adbd 离线的内部原因。M2 有依据的最小隔离措施是先在新启动的
模拟器运行 ART 专项，避免先进行 Native driver 的 TCP 模式切换；如需再运行 Native/adbd，独立
保留其结果，不能用反复增加启动超时替代诊断。

## 证据索引

- `historical-baseline.json`：固定 SHA、run/job 身份、历史状态及来源文件摘要。
- `emulator-command-excerpts.json`：未改写原始命令记录的关键序列摘录。
- `emulator-40331404006.zip`：经摘要验证的完整原始历史 Emulator artifact。
- `darwin-arm-40331404006/`：从原始 Darwin ZIP 精确提取的 Simulator pairing 报告／peer 日志及
  测试汇总；原包 133,596,368 bytes，SHA-256 为
  `d2c0b7733739d97b4291e7d9eaddc4bcb485c1a600ada8cde5c3baffaf60b684`。
  原始 ZIP 已完整验证，仓库仅保存这些小型必要证据。
- `validation/m1-maven/review/baseline-ci-runs.json` 和 `baseline-failure-excerpts.json`：既有
  精确基线的 job／step 状态与原始日志行。原文件保持不变。
