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

## 最终代码输入复核：`ff5b332`，PASS

`final-input-review-ff5b332.json` 将复核延伸至
`ff5b33262d001204cf5df2c5684e77690af511cf`。受保护生产 Kotlin／C／密码学／协议文件仍与
原实验基线 `49a88b14…` 一致；M1 代码与交付检查点的既有 workflow、证据、许可文件保持原样。
重新读取固定候选传输包并逐文件计算了全部 **219** 项摘要，另核对 Legacy／Primitives 来源锁内的
**124** 项 inventory，版本、revision、元数据和制品字节均未变化。

相对 M1，允许的来源锁差异精确为 `native_targets` 增加 `iosX64`，以及 Android runtime 的两个
`file_name` 改为 metadata 和真实 Gradle 缓存使用的 `legacy-release.aar`／`primitives-release.aar`。
四个构建脚本仍只有已验证的 `iosX64` 接线变更。

相对后续已执行 Darwin 的 `0d448840863bbf6735eb879ebc7532c321cfca17`，**24 组 Native 源码、
构建／工具链、门禁、候选、peer 和 Darwin workflow 输入的 Git 对象一致**。完整来源锁有两个
Android 文件名字段的变化，因此两次来源锁摘要必须分别记录：

| 身份 | 完整 source-lock SHA-256 |
| --- | --- |
| Darwin 实际执行提交 `0d448840…` | `c9ed5ff9910c9963501526ccfe9a99d7a3df3fb9d75e526c677de1f125b393dd` |
| 最终代码 `ff5b332…` | `1c1cbe03c78b4810dd096a589c0cb8d57ec2a58b5ceb2b54f9171075c1ddfd92` |

这证明 Native 输入延续，不能把原 Darwin run／源码包改标为在 `ff5b332…` 或新来源锁下执行。
原运行、产物及对应源码包继续保留各自实际提交与摘要。

## 最终环境修复后的输入复核：`3c9b396`，PASS

`final-input-review-3c9b396.json` 再次核对
`3c9b396a57e1f369cce341b396be7ab15d23b0e2` 的 Git 对象，覆盖全部 22 组受保护路径、
11 个协议文件和上述 24 组 Native 执行输入；固定候选的 219 个文件及其中 124 个锁定条目
也重新计算摘要。结果继续一致。相对 `ff5b332…`，新增 268 个原始证据／复核路径，另有
7 个 Android 环境修复路径，具体为 M2 workflow、就绪检查、检查测试及四份诊断证据。

完整来源锁没有再变化，仍为 `1c1cbe03c78b4810dd096a589c0cb8d57ec2a58b5ceb2b54f9171075c1ddfd92`。
这份复核不把 Darwin 的原运行身份改为最终提交，也不将正在执行的 Android CI 提前裁决为通过。

## 实际 Arm64 framework 链接符号复核：PASS（明确限定范围）

`iosSimulatorArm64-symbol-abi-review.json` 比较两份原始 ZIP 中的实际静态 framework：
原基线 `49a88b14…`／run `40331404006`／artifact `12655313986`，以及迁移后
`677a39e7…`／run `41415836057`／artifact `13128890597`。两个完整 ZIP、framework 和
实际头文件均重新计算摘要；没有重新构建，也没有把本地复核计入产品测试。

本地没有 Apple／LLVM `nm`。`compare-retained-arm64-symbols.py` 因此只读取本次实际出现的
BSD ar、ARM64 Mach-O object 和 `LC_SYMTAB` 格式，遇到不支持的格式即失败。首先将迁移产物的
**51,957 条**外部定义按 archive member、符号名、`n_value` 与原 CI `xcrun nm -gU` 的完整输出
逐项比较，包含 private external 与 common 定义，multiset 完全一致，再比较原基线。

| 检查 | 原基线 → Maven 迁移后 | 结果 |
| --- | --- | --- |
| 非私有外部定义条目 | 227 → 227 | 名称及每个 member 的定义属性完全保留 |
| 上述条目的不同符号名 | 220 → 220 | 无新增、无移除 |
| framework 头文件所声明类的实际 class／metaclass 符号 | 156 → 156 | 全部保留 |
| Native C bridge 的已声明函数 | 29 → 29 | 全部保留；两个 C 声明头文件逐字节一致 |
| 包含 private external 的全部不同外部符号名 | 51,489 → 51,615 | 无移除；新增 126 个私有符号 |

227 个条目覆盖 220 个名字，是因为三个既有弱 C++ runtime 名字在不同 archive member 中
有重复定义；其定义次数也完全保留。比较的属性包括 `n_type`、`n_desc` 和 segment／section 名称，
所以保留了可见性、弱定义等链接层属性。地址只用于核对同一产物的 `nm` 输出，不要求两次构建地址一致。

头文件有 79 个类声明，对应 158 个可能的 class／metaclass 名字，其中
`_OBJC_CLASS_$_KadbNumber` 与 `_OBJC_METACLASS_$_KadbNumber` 在**原始与迁移后 archive 中均不存在**。
报告保留这个历史事实，没有将它误判为新回归，也没有声称 158 个声明相关符号都已导出。
29 个 `kadb_*` 函数属于 Native C bridge；`Kadb.h` 没有另行声明这些函数为 framework C API。

结合前面的 943→943 真实头文件比较，以及 run `41418593040` 在 macOS Arm64／x64 上已有的
独立 Swift 编译、链接和执行成功，M2 已有声明、链接符号和实际消费路径三层证据。
两套 Swift 日志均记录模型／身份访问、配对错误回调和真实 loopback CNXN 后断连的 IOException 传递成功。
Swift consumer 是当次重新编译的测试应用；本次符号比较是 iOS Simulator Arm64 静态 archive，
**没有验证任意旧版预编译客户端重新链接、所有 Objective-C method encoding／对象布局／调用约定，
也没有验证动态库 export trie 或所有架构的旧二进制 ABI**。这些结果不能扩大为任意二进制兼容性保证。

符号比较可在具备同一原始 ZIP 的环境重现：

```bash
python3 validation/m2-maven/review/compare-retained-arm64-symbols.py \
  --baseline-zip /tmp/kadb-baseline-darwin/artifact.zip \
  --migrated-zip /tmp/kadb-m2-artifacts/13128890597.zip \
  --output validation/m2-maven/review/iosSimulatorArm64-symbol-abi-review.json
```
