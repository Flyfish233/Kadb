# Kadb SPAKE2 Maven 迁移：M2 跨平台集成验证

日期：2026-11-02（UTC）。工作分支：`work/spake2-maven-migration`。

## 阶段裁决

**Darwin 四个平台 PASS；M2 总体暂为 NOT VERIFIED，等待 Android 网络就绪修复后的完整运行。**
这份阶段报告对应最新工程提交 `3c9b396a57e1f369cce341b396be7ab15d23b0e2`。
各项结果绑定实际执行的源码 SHA，不把后续证据提交当成重新执行。

[Darwin CI 41418593040](https://github.com/Flyfish233/Kadb/actions/runs/41418593040)
在 `0d448840863bbf6735eb879ebc7532c321cfca17` 上完成四个平台的实际验证。
Android 有界网络就绪修复已推送，
[CI 41422457772](https://github.com/Flyfish233/Kadb/actions/runs/41422457772) 正在执行。

| 平台 | 编译 | 链接 / 打包 | 产品测试 | 独立 peer 协议 | 来源 / 完整源码 | 裁决 |
|---|---|---|---|---|---|---|
| macOS Arm64 | PASS | PASS | 65 Kadb + 5 mDNS | 正向 1 + 错误码拒绝 1 | PASS | **PASS** |
| macOS x64 | PASS | PASS | 65 Kadb + 5 mDNS | 正向 1 + 错误码拒绝 1 | PASS | **PASS** |
| iOS Simulator Arm64 | PASS | PASS | 65 Kadb + 5 mDNS | 正向 1 + 错误码拒绝 1 | PASS | **PASS** |
| iOS Simulator x64 | PASS | PASS | 65 Kadb + 5 mDNS | 正向 1 + 错误码拒绝 1 | PASS | **PASS** |
| Android ART / API 35 x86_64 | 既有运行 PASS | APK 构建、安装已有成功记录 | 最终修复重跑中 | 最终修复重跑中 | `ff5b332` 已 PASS | **NOT VERIFIED**（等待最终重跑） |

Darwin 共 **280 次产品测试执行、0 失败**，另有 **8 个独立 peer 会话**。
重复 CI 不累加；Simulator 原有可选 `JvmPairingInteropTest` 的跳过不计为执行或通过，
本轮必需的独立 Native consumer / peer 专项则在四个目标上均真实执行。

## 固定输入与 M1 保留

本轮从核实的远端 `08a4e2ae1ba8aec60382600d72dfc97e2f841a08` 继续；
M1 最终代码为 `af6aa42ebb2bd880753600ed43fbe6e49d6f197e`，原成功运行
[41400073710](https://github.com/Flyfish233/Kadb/actions/runs/41400073710) 保留。
M1 的交付报告、裁决、原始证据、来源门禁及旧 `experiment-validation.yml` 均未覆盖。

Maven 候选仍为 **`0.1.0-dev.59105290820b`**，源码仍为
**`59105290820bcbfd4e0336a2e7713006a461527f`**。
复核重新计算了候选传输包内 219 个文件的摘要，并核对全部 124 项 Legacy / Primitives
来源锁 inventory；候选二进制、坐标、版本、发布 URL、长度和摘要均保持原值。

[M1 重跑 41420744679](https://github.com/Flyfish233/Kadb/actions/runs/41420744679)
在 `ff5b332` 上的 Android Host、Linux Native 均通过。
原 M1 的 165 项产品测试不混入本轮 ART 或 Darwin 新执行计数。

## Darwin 实际结果

工作流使用实际 `macos-26` / `macos-26-intel` runner，固定 Xcode 26.4.1；
Kotlin 2.4.20、Gradle 9.6.0、Java 25 的版本及 runner / Simulator 状态均保存于各目标证据中。
每个目标分别执行 Maven Legacy / Primitives KLIB 真实解析与来源门禁、Native 编译、
链接、JUnit XML 计数、独立配对与完整对应源码收集。

四个平台的公共头文件均与恢复出的精确 `49a88b1` 实验基线比较：
**943 项声明对 943 项，0 删除 / 变更，0 新增**。
两个 macOS 外部 Swift consumer 均完成编译、链接及运行。
各 framework 还经过实际归档架构、部署元数据和符号清单检查；macOS 的部署下限为 12.0，
iOS 为 15.0。该元数据检查不代表在最低 OS 版本上执行。

iOS Arm64 真机架构 framework 另行完成编译、链接、943 项 API 比较和二进制源码关联；
本轮未声称在 iPhone 上执行。该构建结果纳入 Simulator Arm64 job 的完整证据。

各完整对应源码包均校验 630 个文件、64 个已发布 source JAR、9 个源码 archive。
源码包摘要与实际链接出的二进制关联保留如下，完整 archive 位于相应 CI artifact。

| 目标 | 二进制关联数 | 对应源码包 SHA-256 |
|---|---:|---|
| macOS Arm64 | 3 | `112fa0d24dae3e59902ec46b4240407962335ed696be3a113c4c45821a08939a` |
| macOS x64 | 3 | `fdda9a5bc0a571105fb9e7045a726c25a369db21b70567c4cd72520428da8c98` |
| iOS Simulator Arm64，含 device framework | 4 | `2a92c8a6a11554722bf8033698e767732f799e4fdd0362d7eff98c7f2ba072aa` |
| iOS Simulator x64 | 3 | `4c0ed0f3ea51f9307ff33bec4ffd5ecddbb2c2f1009872e85f7a5311c79c259f` |

Darwin 实际执行的 source-lock SHA-256 为 `c9ed5ff9910c9963501526ccfe9a99d7a3df3fb9d75e526c677de1f125b393dd`。
Android 文件名修复后的完整锁摘要为 `1c1cbe03c78b4810dd096a589c0cb8d57ec2a58b5ceb2b54f9171075c1ddfd92`。
两者差异精确为两个 Android runtime `file_name` 字段；Native 候选及 Native 输入未变。
原 run、原源码包及原摘要均保留，不将不同提交的源码包冒充同一物件。

## Android 实际执行与有限环境修复

[首轮 41419309545](https://github.com/Flyfish233/Kadb/actions/runs/41419309545)
已完成 APK 构建、安装与 ART 上的 **9 / 9** 项检查，以及独立 peer 正向和错误码两个会话。
运行记录为 Android API 35、Dalvik 2.1.0、平台 `AndroidOpenSSL`、TLS 1.3，
`bundled_conscrypt=false`；Android 平台 TLS exporter 与 PeerInfo 专项实际执行。
该轮整体保留 **FAIL**：APK runtime 来源锁预期的两个文件名与 Gradle 实际缓存名不符。

修复仅把两个 `file_name` 更正为发布 Gradle metadata 中的 `legacy-release.aar` /
`primitives-release.aar`。坐标、版本、字节、长度及 SHA-256 未变，所有来源门禁保留。
来源锁测试 **48 / 48 PASS**，包含错误别名拒绝用例。

[第二轮 41420744621](https://github.com/Flyfish233/Kadb/actions/runs/41420744621)
已在真实 APK `debugRuntimeClasspath` 上验证 **23 个外部模块 + 1 个项目 artifact**、
四个 SPAKE2 根 / Android 组件、两份 Android runtime AAR，以及实际仓库、版本、哈希与完整源码关联。
该轮通过 6 项 identity 检查后，TCP connect 到 `10.0.2.2` 报 `ENETUNREACH`，
尚未进入 TLS / SPAKE2，peer 会话数为 0；整体同样保留 **FAIL**。

对比两轮 APK，全部文件项内容除 `META-INF/CERT.RSA` 外一致，六份 DEX、独立 peer 类及依赖、
工具和 emulator fingerprint 均相同。原始 logcat 证明第二轮系统 boot / package manager
就绪时，Wi-Fi / DHCP / 默认路由仍在初始化。

`3c9b396` 只修复 M2 就绪脚本：在原 **120 秒、单次尝试** 内，要求 Android active default network、
通往 `10.0.2.2` 的默认 IPv4 路由及同接口 on-link 路由均存在且未 linkdown。
原始 `dumpsys connectivity`、路由输出和等待时间被保存；不探测有限会话 peer 的端口，
不重试已开始的协议，不改 APK 生产代码。三个针对性测试覆盖缺失默认网络、错误网关、
不完整路由、接口不匹配、linkdown 及成功路径。新的完整运行结果尚待收集。

## 实际问题与历史归因

| 问题 | 证据与归因 | 最小处理 |
|---|---|---|
| 原工程未声明 `iosX64` | 固定候选已有该 KLIB；未接线无法执行目标 | 补充四处构建 / C 平台接线及来源锁目标列表 |
| 首轮 macOS 测试 / 配对未启动 | Bash 3.2 在 `set -u` 下展开空数组报错，0 项执行 | 改为始终非空的命令数组；修复后两架构真实通过 |
| 首轮 API 基线选错 | macOS 误用 iOS 头文件；旧 iOS 基线 921 项，精确恢复基线已有 943 项 | 按平台冻结精确历史头文件；保持严格比较器，未放宽声明检查 |
| Android 来源锁文件名不符 | 真实 APK runtime graph 与已发布 Gradle metadata 一致，原锁文件名错误 | 仅更正两个文件名；哈希与来源检查保留 |
| Android boot 早于网络 | 六份 DEX 不变；TCP connect 报 `ENETUNREACH`，未到协议 | 有证据的有界网络就绪等待；等待完整重跑结果 |

迁移前 [49a88b1 / CI 40331404006](https://github.com/Flyfish233/Kadb/actions/runs/40331404006)
的 iOS Simulator 配对失败发生在 `simctl list devices booted --json` 的 10 秒超时，
Native consumer 尚未启动。历史协议执行为 **NOT VERIFIED**，原 CI step 的 FAIL 保留。

同一基线的 Android emulator 实际已在约 30 秒内启动；随后 Native 驱动执行
`adb tcpip 5556` 后 transport offline，ART 就绪检查停止，0 项执行。
本轮在独立 fresh emulator 上运行 ART，没有执行该 M3 adbd 模式切换。
这些环境故障没有被计为 Maven 迁移的密码学回归。

## 证据与边界

机器裁决：`validation/m2-maven/verdict.json`。
原始阶段日志、JUnit XML、实际依赖图、环境、源码 SHA、二进制关联、API / 符号与失败归因
按 run / target 保存于 `validation/m2-maven/runs/`。
`artifact-custody.json` 记录 GitHub archive 的 SHA-256 和每个保留文件的摘要；大文本日志采用无损 gzip。
少数早期完整 job 解码文本保存时多出一个末尾 LF，原文件保留，并补充精确解码副本与
`runs/decoded-job-log-fidelity.json` 说明。artifact 内原始文件没有这种转换。

独立复核位于 `validation/m2-maven/review/`，历史恢复与新故障诊断分别位于
`baseline/`、`android-fix/` 和 `android-network-fix/`。
完整外部 ADB 正负矩阵、真实 Android / iOS 设备与最低 OS 运行仍为 **NOT VERIFIED**，属于后续专项。

生产 Kotlin / Native C / SPAKE2 密码学没有修改；HARDENED、身份尾部 NUL、TLS exporter、
HKDF、AES-GCM、PeerInfo、一次性状态机和 AOSP nonce 协议保持原行为。
没有改动 main、合并 PR、正式发布或修改许可证。
