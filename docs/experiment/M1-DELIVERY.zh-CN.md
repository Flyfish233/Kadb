# Kadb SPAKE2 Maven 迁移：M1 交付

日期：2026-11-02（Asia/Shanghai）。工作分支：`work/spake2-maven-migration`。

## 当前裁决

**M1 PASS。固定 Maven 二进制迁移、真实解析来源、Android Host / Linux Native
编译测试、完整对应源码收集与可复现性均有执行证据，本地与最终代码的远端 CI 全部通过。最终代码提交为
`af6aa42ebb2bd880753600ed43fbe6e49d6f197e`。**

最终代码的远端 CI 为 [41400073710](https://github.com/Flyfish233/Kadb/actions/runs/41400073710)：
**整体 SUCCESS；Android Host 与 Linux Native 两个 job 均 SUCCESS**，全部编译、测试、来源门禁、
完整源码收集和 artifact 上传步骤成功。已核对其 head SHA 正是上述最终代码提交。
较早 AAR 修复提交的
[41399849616](https://github.com/Flyfish233/Kadb/actions/runs/41399849616) 两个 job 已全部成功。

| 阶段 | 裁决与范围 |
| --- | --- |
| M1 | PASS；本地验证及最终代码 Android Host / Linux Native CI 均通过 |
| M2 | NOT EXECUTED；没有启动 Darwin / Android ART / Emulator 全平台矩阵 |
| M3 | NOT EXECUTED；没有本轮外部真实 ADB 或真实设备配对结果 |

交付过程持续以独立提交保存，没有修改或合并 `main`，没有覆盖原实验分支，没有 Maven/Release 正式发布。
后续证据与交付文档提交不改动上述代码快照。

## 已推送的工程检查点

| 提交 | 实际内容 |
| --- | --- |
| `77921027374c7295f65ae82eb1b939a7dae7361e` | 固定版本目录、真实 Maven Legacy 依赖、独占候选仓库、移除旧内嵌生产入口、保留候选实物；当时明确标注构建待验证 |
| `316c64a9761c16293d7f1f69adc7769393e7a705` | 实际 Gradle 来源门禁、完整对应源码锁、负向测试、源码/许可文档与 M1 CI |
| `df9a1f1b2b666103f227b8c52af2018c8620eab2` | 修复源码收集器不接受新 CI 传入的 Android AAR |
| `af6aa42ebb2bd880753600ed43fbe6e49d6f197e` | 普通构建从 KMP 模型自动覆盖实际调度的 main/test 配置 |
| `f6ba8ebd37520626a219aaf1a6ad94d9ace7c384` | 归档本轮来源、正负解析测试、真实构建测试及两次完整对应源码收集证据 |

恢复起点是 `21401b2498bda8ea7b774b74e50c8085ab099c19`；原实验基线是
`49a88b14e9b731e4c086c920eb74664450c79d9f`。恢复时发现的有效未推送代码完整保留后继续完成。

## 实际 Maven 迁移

`gradle/libs.versions.toml` 新增严格固定的 `spake2KmpCandidate` 与 `spake2LegacyKmp`；
`kadb/build.gradle.kts` 使用 `implementation(libs.spake2LegacyKmp)`，原 Java oracle 别名保留。
`settings.gradle.kts` 删除 `:spake2-legacy` 的 include/projectDir，并用 exclusiveContent
将 `io.github.flyfish233` 限定到已验证的候选目录，禁止子项目新增依赖仓库。

候选由原 CI 的已发布结构恢复为 **file Maven 仓库**，实际消费 `.module`、POM、AAR、JAR、KLIB。
此流程没有复制生产源码来代替二进制，也没有 `includeBuild` 或 dependency substitution。
`third-party/spake2` 的历史文件未接回生产构建。

`gradle/spake2-maven.gradle` 会核验实际解析图、固定版本、Legacy 的同版 Primitives、平台变体、
元数据原始文件 URL、缓存字节及来源仓库。仓库名称必须唯一对应候选 canonical URI，descriptor ID
一同记录。该来源接口绑定项目的 Gradle 9.6.0；不支持的版本失败终止。
普通 compile/test/check/AAR 入口也强制执行门禁。

普通调用实际覆盖 Android main/hostTest 和 Linux main/test 四组 compilation、六个必查配置。
最终报告记录 20 次制品选择；其中额外 Darwin 配置仅为依赖解析，没有被计为 Darwin 构建或测试。

## 固定候选身份

| 项目 | 实际核验值 |
| --- | --- |
| SPAKE2 源码 | `59105290820bcbfd4e0336a2e7713006a461527f` |
| 版本 | `0.1.0-dev.59105290820b` |
| 生产入口 | `io.github.flyfish233:spake2-legacy` |
| 传递组件 | `io.github.flyfish233:spake2-primitives` |
| 上游 Maven CI | [40388080222](https://github.com/Flyfish233/spake2/actions/runs/40388080222) |
| Artifact ID | `12682137388` |
| 原始 ZIP SHA-256 | `29fe208f315ea08c9643d4388df8d832b984b04270fd39e55d00328ed4746ac3` |
| 保存的 transport tar.xz SHA-256 | `3ea50362515509300850ac2bdb487bc070379d3e40e346250eb228ed2ad47d33` |

本轮重新下载原始 ZIP 并重算摘要；219 个 Maven 文件与保存的传输包、逐文件 manifest 和恢复的
仓库完全一致。完整 33 个发布单元通过固定上游 checker；Kadb 来源锁覆盖其中 Legacy/Primitives
的 22 个坐标、124 个 Maven 文件。三份完整 source-distribution ZIP 各自的 482 个文件均与固定
Git 源码提交逐字节一致；原生产流程只排除了 `.gitignore`。

候选实物已保存于 `validation/maven-candidate/`，恢复不依赖原 Actions artifact 的到期时间。
本轮没有重建、重签名或修改 SPAKE2 生产密码学源码。

## 实际执行结果

工具链：**Kotlin 2.4.20、Gradle 9.6.0、AGP 9.4.0、Temurin JDK 25.0.5+8、Android SDK 37**。
Linux 使用经官方摘要核验的 CMake 3.31.8。

| 验证 | 本轮执行结果 |
| --- | --- |
| 候选恢复、缺失、篡改、路径/符号链接检查 | 6/6 PASS |
| 完整源码与来源收集器测试 | 42/42 PASS |
| 真实 Gradle 解析正负夹具 | 6/6 PASS |
| Android 生产编译与 AAR 打包 | PASS；首次 25 个任务实际执行 |
| Android Host 单元测试 | 102 个执行，0 失败，0 跳过；保留独立 Java oracle |
| Linux Native C/BoringSSL、cinterop、Kotlin 编译与链接 | PASS；首次 15 个任务实际执行 |
| Linux Native 单元测试 | 63 个执行，0 失败，0 跳过 |
| 普通构建自动门禁与两组测试同次调用 | PASS；165 个测试实际执行，20 次 Maven 制品选择 |
| 完整对应源码创建 | 两次离线创建均 PASS，字节一致 |
| 对应源码独立 verify | PASS，630 文件与两个实际二进制关联 |

六个真实 Gradle 夹具覆盖：JVM/Android/Linux 正确变体、错误请求版本（即便被 force 改回固定版本）、
单一配置缺少 Primitives、项目替换、相同字节来自错误仓库、候选二进制被修改。
Python 测试另覆盖 source lock 陈旧、错误来源/revision、错误变体、源码冒充二进制、源码/许可缺失等。

首次构建确实执行编译和链接；后续用于门禁同次验证的调用复用已有编译输出并强制重跑测试，
原始日志完整保留。普通入口测试发生在 `df9a1f1` 加门禁修复的工作树中；其五项构建输入摘要与
已提交 `af6aa42` 全部一致，见 `runtime/resumed/committed-build-inputs.json`。执行记录没有改写原始身份。

## 完整对应源码与许可材料

`scripts/source_bundle.py`、`validation/source-bundle/dependencies.lock.json` 已改为以真实 Maven
坐标、版本、元数据、来源与摘要收集材料。保留 Legacy/Primitives 完整源码 ZIP、全部相关源码与
许可 companion、Gradle 构建输入，以及 Kadb 原有的 Kotlin、coroutines、Okio、BoringSSL、Android
等来源收集能力。Kadb 自有 Apache-2.0 与上游 AGPL-3.0-only 的既有边界不变。

本地最终完整源码包的身份：

```text
源码提交：af6aa42ebb2bd880753600ed43fbe6e49d6f197e
大小：192726468 bytes
文件：630
发布源码 JAR：64
完整源码档案：9（Kadb + 8 个上游）
SHA-256：3262908d831a107ffd1ff479961a4aa43a8b9407fa8d9fab554f264e37286095
source-lock SHA-256：3d0701f8a9987a048615e27275e10820116055959b86bf447ed7a68df11848a3
```

该包关联本轮真实 AAR（318,468 bytes，SHA-256 `28c4a06b2c7150e02c189c5aab07764db920e5f4af44b21005119c7c511f7a0b`）
与 Native 测试 ELF（27,791,088 bytes，SHA-256 `1742db4415dd494e1a95a092e679dfc4d876ba413f561d9c3f6f6b31d81dedeb`）。
两次比较固定同一源码、解析报告、依赖和二进制输入；不表示不同环境产生的二进制或含不同运行报告的包也必须同哈希。

CI 会上传各 job 的完整源码包、解析报告、测试报告和实际构建产物，保留 90 天。Host 源码包关联 AAR；
现有 Native CI 源码包记录 `binary_associations=0`，与本地已验证的双二进制关联包明确区分。
Native CI 的实际二进制另外随该 job artifact 上传。所有重建所需的候选、脚本、固定来源锁和摘要已进入 Git。

最终 CI 已实际保存的 artifact（可从上述 run 下载，当前到期日为 2027-01-31）：

| Artifact | ID | ZIP 字节数 | GitHub ZIP SHA-256 |
| --- | --- | --- | --- |
| `m1-maven-af6aa42ebb2bd880753600ed43fbe6e49d6f197e` | `13120104510` | 193,805,836 | `2fcd915e45657ebbb93c626a6fb3cdeb8d54469dbea2f77c3d5b30a97b63ba80` |
| `m1-maven-linux-native-af6aa42ebb2bd880753600ed43fbe6e49d6f197e` | `13121092177` | 253,887,793 | `9153205f81d036e106890e67d7c6752e46f54ea15fee78dab235836ce11c2e56` |

## 协议、安全语义和失败归因

`kadb/src` 与旧内嵌密码学源码对实验基线没有改动。另对 11 个关键协议实现逐字节核验，并核验
HARDENED、Role.ALICE、两端 NUL 身份、TLS exporter 的 `adb-label` 精确标签与 NUL、HKDF-SHA256、
AES-128-GCM、PeerInfo 认证、失败销毁和一次性会话约束。R3-K01 的 AOSP 双向 key/nonce 复用协议保持原样；
没有借迁移单方面修改 wire protocol，也没有发起第四轮密码学审计。

本轮新发现并修复的集成问题：

1. AAR/Native 制品在 Gradle 缓存中可能使用 metadata 的 `name`，旧门禁误用 Maven URL 文件名；现按名称映射、属性和摘要绑定。
2. 新的 AAR 对应源码关联被旧 Native-only 格式门禁拒绝；现增加真实 AAR 结构检查及负向测试。
3. 普通 Native 构建的门禁曾受配置解析时机影响；现从实际调度的 KMP main/test 模型取必查配置。

首轮迁移 CI `41399433444` 的 Native job 成功，Host 在完整源码收集步骤因上述 AAR 问题失败；
此前编译、测试、解析门禁都通过。该问题已由 `df9a1f1` 修复并通过后续 CI。

历史基线 CI `40331404006` 的 Android Emulator 未就绪（执行测试前失败）与 iOS Simulator pairing
失败属于迁移前记录；本轮没有重试，也没有将它们归咎于 Maven 迁移。详见 `validation/m1-maven/review/`。

## 直接恢复与继续入口

从工作分支最新 HEAD 恢复即可，不需要旧沙箱或重新审计。准备 JDK25、Android SDK37、CMake 及
原有 Native 构建工具后：

```sh
python3 scripts/prepare_spake2_candidate.py
./gradlew :kadb:testAndroidHostTest :kadb:bundleAndroidMainAar :kadb:linuxX64Test \
  --no-build-cache --no-configuration-cache --console=plain --stacktrace

python3 scripts/source_bundle.py verify-spake2-maven \
  --spake2-resolution-report kadb/build/reports/spake2-maven-resolution.json \
  --output build/spake2-source-verification.json

python3 scripts/source_bundle.py create --repo "$PWD" --ref HEAD \
  --output build/m1-source --cache /tmp/kadb-source-cache \
  --spake2-resolution-report kadb/build/reports/spake2-maven-resolution.json \
  --binary kadb-android-aar=kadb/build/outputs/aar/kadb.aar \
  --binary linuxX64-debug-test=kadb/build/bin/linuxX64/debugTest/test.kexe
```

首次会获取并核验固定来源材料；之后可加 `--offline` 使用已校验缓存。创建命令会输出生成包名和摘要；
可用 `python3 scripts/source_bundle.py verify <包路径> --sha256 <输出摘要>` 独立校验。

后续 M2 从现有 `experiment-validation.yml` 的 Darwin/ART/Emulator 平台任务继续，按平台独立记录
编译、单测和集成。M3 再进行真实 TLS exporter、ADB 正负配对及条件允许时的真机验证。
M1 的已有来源、测试及源码收集结果无需重做。
