# Kadb SPAKE2 Maven 迁移：M2 跨平台集成验证

日期：2026-11-02（Asia/Singapore）。工作分支：`work/spake2-maven-migration`。

## 当前阶段

M2 从已核实的远端 `08a4e2ae1ba8aec60382600d72dfc97e2f841a08` 继续。
M1 最终代码 `af6aa42ebb2bd880753600ed43fbe6e49d6f197e` 与
[CI 41400073710](https://github.com/Flyfish233/Kadb/actions/runs/41400073710)
的两个成功 job 已再次核对。M1 交付报告、裁决、原始证据和 workflow 保留。

首个 M2 工程提交 `677a39e74ef568ac91bec6db2885929003cc709e` 已推送，
[Darwin CI 41415836057](https://github.com/Flyfish233/Kadb/actions/runs/41415836057)
已启动四个真实 macOS runner job，首批观察保存于
`validation/m2-maven/runs/41415836057/initial-jobs.json`。
**当前等待本轮 Darwin / ART 的完成证据，M2 裁决仍为 NOT VERIFIED。**
workflow 已存在、任务成功排队或依赖解析成功均不等于目标平台执行通过。

## 固定输入与范围

- Maven 候选：`0.1.0-dev.59105290820b`，源码
  `59105290820bcbfd4e0336a2e7713006a461527f`。
- 保留 Legacy / Primitives 的固定二进制、完整对应源码与原有解析来源门禁。
- 优先执行 macOS Arm64 / x64、iOS Simulator Arm64 / x64，再执行 Android ART。
- 每个平台分别记录依赖来源、编译、链接、测试、framework/API 与协议执行。
- 完整外部 ADB 正负矩阵与真实设备专项保留给 M3。

现有工程尚未声明 `iosX64`，固定 Maven 候选已经包含该目标的 KLIB。
本轮补充所需的目标与 C 平台接线，并以实际编译、链接和 Simulator 运行判断支持状态。

## 已取得的首轮结果与最小修复

首轮 `677a39e` 的四个 Darwin 目标均实际编译、链接成功。iOS Simulator Arm64 已通过
Kadb / mDNS 的实际测试、独立 peer 的两个会话、公共 API 与 framework 检查；完整平台裁决
仍等待 device framework、对应源码和最终 artifact。`iosX64` 正在进行 Simulator 阶段。

macOS 两架构已通过 framework 架构/部署检查、外部 Swift consumer 编译链接执行和
完整对应源码收集。测试及配对未开始，原因是新增 workflow 在 macOS Bash 3.2 的 `set -u`
环境下展开空数组 `simulator[@]`，启动命令前即报 `unbound variable`。
本轮据此改为始终非空的命令参数数组，等待修复后的实际执行，不把 0 项测试计作通过。

macOS 首轮 API 步骤误用了 iOS 历史头文件，只缺少 iOS 专属的四项声明。
现从原 CI artifact `12655313986` 提取真实 macOS 历史头文件，保存原始身份。
用原比较器重新比较首轮真实 macOS Arm64 头文件：**943 对 943，0 删除/变更，0 新增**。
这项更正与原始失败报告一并保留；修复后的 CI 将按平台选择正确基线。

APK 专属来源门禁已作为 `8a7a75a4061cb26f86b144454ffba98cf2aee9d4` 推送。
它校验 APK `debugRuntimeClasspath` 的实际仓库、固定请求版本、四个根/Android 组件及两份
Android runtime AAR，不用 Kadb 自身的解析图代替 APK 来源。
对应 Python 回归 **47/47 PASS**，原始日志及输入摘要位于
`validation/m2-maven/local-gates/android-origin/`；这不代表 Gradle 或 ART 已经执行。

M1 workflow 在首轮 M2 接线提交上再次运行：
[41415836056](https://github.com/Flyfish233/Kadb/actions/runs/41415836056)
的 Android Host 和 Linux Native 两个 job 均成功。M1 旧交付证据没有被覆盖。

## 历史对照

原实验基线 `49a88b14e9b731e4c086c920eb74664450c79d9f` 的
[CI 40331404006](https://github.com/Flyfish233/Kadb/actions/runs/40331404006)
已有 iOS Simulator 配对步骤失败记录。已校验原 artifact 并恢复配对原始报告：
`xcrun simctl list devices booted --json` 在 10 秒超时，Native consumer 尚未启动，
没有到达协议断言。历史协议执行应为 NOT VERIFIED，CI step 保留 FAIL 原始状态。

同一基线的 Android Emulator 曾启动完成，但在 Native 驱动执行 `adb tcpip 5556` 后
传输变为 offline，随后 ART 驱动在就绪检查阶段停止，运行检查数为 0。
本轮在独立、未切换 adbd 模式的 Emulator 上执行 ART，保存设备状态、启动日志和有界等待结果。
冻结的历史证据索引位于 `validation/m2-maven/baseline/`。

## 证据入口

- `validation/m2-maven/recovery/recovered-state.json`：本轮恢复身份及受保护输入摘要。
- `validation/m2-maven/baseline/`：迁移前历史结果及归因边界。
- 独立 M2 workflow：按目标保存原始 Gradle 日志、XML 计数、实际解析报告、执行环境及源码身份。

生产密码学与 AOSP nonce 协议不在本轮修改范围内。HARDENED、身份尾部 NUL、
TLS exporter、HKDF、AES-GCM、PeerInfo 与一次性状态机保持原有实现。
