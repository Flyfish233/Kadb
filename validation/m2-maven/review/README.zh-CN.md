# M2 独立复核：原有输入与 iOS 原始执行证据

复核日期：2026-11-02（Asia/Singapore）。本目录区分两组身份：

- 源码范围复核：M1 HEAD `08a4e2ae1ba8aec60382600d72dfc97e2f841a08` 至
  `892331117cddb6b7a0bd370c29ab2ffb117dd38d`。
- 原始平台执行：[41415836057](https://github.com/Flyfish233/Kadb/actions/runs/41415836057)，
  执行源码 `677a39e74ef568ac91bec6db2885929003cc709e`。

这次复核重新读取 Git 对象、原始 artifact、JUnit XML、两端配对日志、实际 framework 头文件和
对应源码绑定；没有重新执行 Darwin 测试，也没有把复核检查数加入产品测试数。

## 原有输入保持情况：PASS

`preserved-inputs-8923311.json` 保存逐项 Git object ID、摘要和断言结果：

- 15 组受保护路径的 Git 对象完全一致，包括 Kadb／mDNS 源码、Native C、内嵌历史 SPAKE2、
  BoringSSL 材料、Maven 候选原包、原有 Maven 来源门禁、版本目录、仓库配置、M1 证据、M1 workflow
  和两个旧 experiment workflow，以及独立 peer 源码／依赖摘要。
- 5 份许可证／许可边界文件逐字节一致。
- 11 个关键协议文件的摘要仍与迁移前基线 `49a88b14e9b731e4c086c920eb74664450c79d9f` 一致。
  同时检查了 HARDENED、Role.ALICE、双方尾部 NUL 身份、64-byte TLS exporter 与精确标签、HKDF、
  AES-GCM、PeerInfo 认证及一次性状态机的既有标记。
- 四个构建脚本的差异精确限定为增加 `iosX64` 目标及其已有 Simulator C 构建参数。
  来源锁仅在 `native_targets` 增加 `iosX64`；候选身份及整个 `spake2_maven` 块保持不变。

因此本轮没有修改 SPAKE2 生产密码学源码或 AOSP nonce 协议，没有改写 M1 已通过的 workflow／证据。
上述结论只覆盖指定的 Git 提交区间，不代替新的安全审计。

## 原始 iOS 执行证据复核：两项目标均 PASS

| 目标 | 原始 JUnit 独立计数 | 独立 peer | 精确基线 API 比较 | 对应源码实物绑定 |
| --- | --- | --- | --- | --- |
| iOS Simulator Arm64 | Kadb 65＋mDNS 5 执行；0 失败；1 skipped | 两端正常退出；正向 1＋错误码拒绝 1 | 943→943；无增删；头文件逐字节一致 | framework、测试程序、配对程序 3 项 |
| iOS Simulator x64 | Kadb 65＋mDNS 5 执行；0 失败；1 skipped | 两端正常退出；正向 1＋错误码拒绝 1 | 943→943；无增删；头文件逐字节一致 | framework、测试程序、配对程序 3 项 |

每项目标的 skipped 项均为需要显式启用的 `JvmPairingInteropTest`，没有计入 70 个执行测试。
单独配对程序的两项断言由其自己的日志证明，不与 JUnit 重复计数。

独立复核做了以下实物检查：

1. 重新计算两个完整下载 ZIP 的 SHA-256，并与 GitHub artifact digest／保存的 custody 记录核对；
   对每个保留文件重新检查压缩后及解压后的摘要和长度。
2. 直接解析两套实际 JUnit XML，逐 suite 核对 XML 属性与 testcase 数量、失败、错误和跳过标记，
   并检查 testcase 身份没有重复。
3. 使用未修改的 `validation/compare-objc-api.py`，将两个实际 framework 头文件与从精确
   `49a88b14…` 原始 artifact 提取的 iOS 头文件比较。此次没有使用较早的 921 声明快照。
4. 从 Native consumer 和独立 Java peer 的原始日志分别解析唯一的 JSON 结果，核对其与配对
   报告一致，确实完成两次 Simulator 会话。
5. 从原始 ZIP 直接读取并计算 framework、测试可执行文件、配对可执行文件的摘要和长度，逐项
   与 source manifest、平台产物记录以及配对程序自己的身份核对。每项目标均精确绑定 3 项。
6. 重新计算原始 ZIP 内完整对应源码包的摘要，与 CI `source-bundle-result.json` 核对；其来源锁
   摘要与实际执行提交一致。没有在本次复核中重新运行完整源码收集器。

详细输入身份、实际比较命令、结果与逐项计数见两个
`*-independent-evidence-review.json`。`*-exact-baseline-api.json` 与 `.log` 保存实际 API 比较输出。
这里的 API 结论针对真实导出的声明及相应产物；不将它扩大为所有下游应用的二进制兼容性保证。
