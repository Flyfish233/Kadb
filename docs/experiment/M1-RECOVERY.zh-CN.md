# SPAKE2 Maven 迁移 M1：恢复检查点

日期：2026-11-02（Asia/Singapore）。本检查点仅记录恢复与来源身份，尚不表示迁移或测试通过。

## 已确认的起点

- Kadb 基线：`experiment/kmp-native-core`，`49a88b14e9b731e4c086c920eb74664450c79d9f`。
- 新工作分支：`work/spake2-maven-migration`，从上述精确提交创建。
- SPAKE2 迁移资料：`0795a4b3d7c8fbdabde8641360717e3e0903f308`。
- Maven 候选源码：`59105290820bcbfd4e0336a2e7713006a461527f`。
- 固定版本：`0.1.0-dev.59105290820b`；生产入口为 `io.github.flyfish233:spake2-legacy`，Primitives 由同版 Maven metadata 传递解析。
- 原 CI：[40388080222](https://github.com/Flyfish233/spake2/actions/runs/40388080222)，artifact ID `12682137388`。
- 原 artifact ZIP SHA-256：`29fe208f315ea08c9643d4388df8d832b984b04270fd39e55d00328ed4746ac3`。

## 恢复结果

开始时远端仅有 Kadb `main` 与 `experiment/kmp-native-core`，没有同名迁移分支，也没有可恢复的迁移 PR。
可访问的旧目录为先前 SPAKE2 审计克隆和 Kadb 只读基线；工作树干净，未发现真实 Maven 迁移改动。
本次在新目录独立克隆，未覆盖旧工作树。开始时没有继承运行中的构建进程。

沙盒外网络申请已通过。终端 `gh` 没有认证；GitHub 连接器可读取原候选并保存 Git 检查点。
提交采用 GitHub Git Data API、明确父提交与非强制 ref 更新，本地再取回并核对内容树。

原候选已重新下载，摘要与 GitHub artifact 记录一致，完整 33 发布单元结构门禁通过。
它的来源仍为原 CI 产物，不是本机重建；详细来源、源码比较和实际消费者证据在后续检查点补齐。

## 本轮范围与不变量

只执行 M1：真实 Maven 依赖替换、固定来源/变体验证、完整对应源码收集，以及当前 host 可直接执行的有界编译和回归。
不启动 M2 跨平台矩阵、M3 真实设备配对或第四轮密码学审计。

保留 HARDENED、Role.ALICE、两个带尾部 NUL 的 ADB 身份、TLS exporter 与标签、HKDF-SHA256、AES-128-GCM、
PeerInfo 认证、一次性状态机、失败销毁与异常映射。SPAKE2 生产源码和 AOSP 双向 GCM nonce 协议不改。
原 Java BoringSSL oracle 测试依赖继续保留。AGPL-3.0-only 与 Apache-2.0 的既有许可说明继续适用。

## 后续检查点

1. 本文件：基线与来源身份。
2. 固定版本、独占候选仓库、移除内嵌生产入口、实际解析组件门禁。
3. 对应源码/许可证/来源锁与负向验证。
4. 有界测试原始证据、中文 M1 交付报告及明确裁决。

基线 CI [40331404006](https://github.com/Flyfish233/Kadb/actions/runs/40331404006) 已在迁移前失败。
历史 macOS ARM 模拟器集成与 Android Emulator 失败仅记录和归因，不在 M1 无限重试。

## 继续执行检查点 1：实际 Maven 依赖替换

2026-11-02（Asia/Singapore）恢复执行时，远端仍为 `21401b2498bda8ea7b774b74e50c8085ab099c19`。
找到旧工作树中的未提交迁移成果后，完整复制到新的工作目录；旧目录和有效改动均保留。
本检查点先交付生产 Gradle 入口及候选实物，后续独立提交消费者来源门禁、对应源码锁和 CI。

- `gradle/libs.versions.toml` 新增严格固定的 KMP 候选版本及 Legacy 坐标，原 Java oracle 别名保留。
- `kadb/build.gradle.kts` 的生产依赖改为 `implementation(libs.spake2LegacyKmp)`。
- `settings.gradle.kts` 移除 `:spake2-legacy` 的 include/projectDir，使用 file Maven 仓库和 exclusiveContent 隔离 `io.github.flyfish233`。
- `validation/maven-candidate/` 保存原 CI 产物的完整 Maven 文件集合；只是重新封装传输压缩包，没有重建二进制。
- `python3 scripts/prepare_spake2_candidate.py` 逐文件校验并离线恢复候选；本轮 6 个恢复/篡改/缺失/路径测试实际通过。
- 本轮重新取得 GitHub artifact 元数据，并重算保留的原 ZIP SHA-256，均与上述固定身份一致。

**本检查点为静态迁移已交付、构建待验证；M1 尚未 PASS。**
它不将候选文件完整性、上游成功构建或旧基线 CI 等同于 Kadb 本轮编译/单测通过。
后续首先增加实际 Gradle 组件、传递依赖、变体、来源摘要和项目替换门禁，再记录当前工具链的执行结果。
