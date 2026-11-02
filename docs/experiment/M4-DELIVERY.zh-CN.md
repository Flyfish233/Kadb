# M4：强制身份认证与真实身份拒绝验证 — 最终交付

## 一、裁决与执行身份

**M4 整体 PASS。M4-A 的真实 RSA AUTH 正反验证与 M4-B 的真实无线 TLS 身份接受、未配对拒绝和撤销后新连接拒绝均已通过。M4-C 实体设备保持 NOT VERIFIED。**

| 验收项 | 裁决 | 当前执行证据 |
| --- | --- | --- |
| M4-A：已授权 RSA、未授权拒绝、真实协议身份 | **PASS** | 4 个新连接、32 项 Native 检查；20 字节 token 与 256 字节签名逐连接验证；B 有系统 NO、没有 CNXN，A 前后均成功。 |
| M4-B：无线配对、强制 TLS 身份及撤销 | **PASS** | 真实系统配对 1 次；5 个 TLS 新连接、合计 43 项 Native 检查；B 和撤销后的 A 都被真实证书校验拒绝。 |
| M4-C：实体设备 | **NOT VERIFIED** | 未选择或操作 OnePlus、其他个人手机或实体设备。 |
| M4 整体 | **PASS** | 合并同一提交的两个独立 AVD job；两项必要验收和清理均通过。 |

- 工作分支：`work/spake2-maven-migration`。
- 恢复与核实的用户基线：`895674e5725b2cf328bf427e1500cb8f2e6e231e`；M3 实际代码 `ef5ae480e598ec08309fa6bfed12af44996bbfea`。
- **实际构建与执行代码：`03e903ea058e3eb27a36dd047b8af2868d33f7fc`。** 后续交付提交保存证据、报告及一个已本地通过的验收聚合测试子场景；没有再改生产代码或实际运行驱动。
- **成功 CI：[41453219296](https://github.com/Flyfish233/Kadb/actions/runs/41453219296)**，RSA job [125303313927](https://github.com/Flyfish233/Kadb/actions/runs/41453219296/job/125303313927)、TLS job [125303313686](https://github.com/Flyfish233/Kadb/actions/runs/41453219296/job/125303313686) 均 success。
- 当前验收客户端是独立 **Kotlin/Native linuxX64 公共 API consumer**；对端是真实 Android adbd/system_server。未重跑 M1/M2/M3 完整矩阵。

本次最终 CI 实际执行 **75 项 Native 检查 = RSA 32 + 无线 43**，共 9 个 ADB 认证连接和 1 个系统配对连接。45 项工具测试在两个 job 各执行一次，合计 90 次执行，单独计数。两组驱动分别执行 79、108 条命令，这些也不被当成额外测试用例。合并裁决见 [combined-verification.json](../../validation/m4-maven/runs/41453219296/combined-verification.json)。单阶段原报告的顶层 `verdict=NOT VERIFIED` 是有意的范围约束：只有该 job 的 `run_verdict` 和所选 M4 子项为 PASS，完整 M4 必须在此合并。

## 二、真实且强制认证的目标

| 项目 | 实际值 |
| --- | --- |
| 官方 SDK 包 | `system-images;android-35;google_apis_playstore;x86_64` |
| 镜像 | Android 15 / API 35，revision **9**，extension **13**，`user/release-keys` |
| Build fingerprint | `google/sdk_gphone64_x86_64/emu64xa:15/AE3A.240806.036/12592187:user/release-keys` |
| 安全属性 | `ro.adb.secure=1`、`ro.debuggable=0`、`ro.secure=1`；shell UID **2000** |
| Emulator / platform-tools | Emulator **37.2.13**, build **16740729**；adb **37.0.1-15733141** |
| 执行宿主 | GitHub Ubuntu 24.04、x86_64、KVM；Kotlin **2.4.20**，Native linuxX64 |
| RSA 实例 | adbd PID **1730**，TCP listener **5555** |
| TLS 实例 | adbd PID **1772**，system_server PID **539**；TLS listener **32975**，系统配对 listener **46795** |

镜像来源、官方 r09 下载条目和参考源码散列见 [环境研究](../../validation/m4-maven/research/AUTH-TARGET.zh-CN.md)、[primary-sources.json](../../validation/m4-maven/research/primary-sources.json)。实际 system/vendor/ramdisk/kernel 输入已逐一 SHA256 识别，见 [官方镜像身份](../../validation/m4-maven/runs/41453219296/tls/evidence/official-image-identity.json)。CI 明确断言 API、tag、ABI 和 revision 9，升级镜像不会静默替代当前目标。

每个 job 新建临时控制身份 C、独立 `ANDROID_USER_HOME`/`ANDROID_EMULATOR_HOME`/`ANDROID_AVD_HOME`、ADB server **5038**，所有设备命令显式指定 `emulator-5554`。通过官方 emulator 首次启动机制为仅该新 AVD 配置 C；测试身份 A/B 与 C 不同，测试前验证不存在于授权集合。两组 C 的哈希不同，证明不是共享一份授权状态。端口转发只传递字节；A/B 的当前 AUTH/STLS 必须独立通过观察器和系统裁决。

环境门槛除属性外，还要求新连接收到真实 20 字节 AUTH token、没有成功 CNXN，并确认普通 shell 拥有系统正常授权管理接口权限。本轮未 root、未修改系统镜像/分区/SELinux/认证属性，未直接写授权文件。设备端身份校验没有被放宽。

官方 `user` 镜像限制普通 shell 读取或直接执行 adbd，单独运行时 adbd ELF 哈希未取得；权限失败原样保留。官方 SDK 输入哈希和运行时 fingerprint 识别这个外部测试对端。固定 `android-15.0.0_r1` 源码用于解释机制，**没有被当作 Google Play 二进制的精确对应源码**。Kadb 自身及所链接依赖的精确源码关联见第七节。

## 三、M4-A：真实 RSA AUTH

原始报告：[RSA report.json](../../validation/m4-maven/runs/41453219296/rsa/evidence/auth/report.json)；独立复核：[RSA evidence-review.json](../../validation/m4-maven/runs/41453219296/rsa/evidence-review.json)。

| 当前连接 | AUTH token / 签名 / AUTH3 | adbd CNXN | Shell / 裁决 | 尝试耗时 |
| --- | --- | ---: | --- | ---: |
| 新 A 正常授权 | 2 / 1 / 1 | 1 | 正常允许后成功 | 174 ms |
| 已授权 A，负向前 | 1 / 1 / **0** | 1 | 签名接受，Shell 成功 | 54 ms |
| 未授权 B，明确拒绝 | 2 / 1 / 1 | **0** | 系统 NO，无成功会话 | 8,020 ms |
| 已授权 A，负向后 | 1 / 1 / **0** | 1 | 签名接受，Shell 成功 | 46 ms |

四个连接的 token 摘要各不相同。观察器在当前连接内用对应临时公钥独立验证 RSA-2048 / PKCS#1 v1.5 / SHA1-prehashed 签名，要求 token 20 字节、签名 256 字节。原始 token/签名只在内存中检查，证据保留长度、摘要、连接序号及验证结果；没有宣称销毁原始字节后又做了一次离线签名重建。

首次授权只在观察到当前 A 的 AUTH3、公钥匹配和系统 `last_key_received` 指纹匹配后，调用正常 `IAdbManager.allowDebugging`。传入的完整公钥字符串来自该次 AUTH3，只移除协议末尾 NUL，并用摘要核对 Binder 参数。首次允许不能独立证明签名接受，因此主要正向证据是前后两个无需 AUTH3、无需再次允许的新连接。

B 的公钥和签名确实到达同一 adbd。系统在 **13:32:48.069** 同时记录 framework `Denying adb confirmation` 与 adbd `received packet: NO`。B 没有得到 adbd CNXN 或 Shell，A 随后仍成功；所有会话 listener 和 PID 保持稳定。参考 AOSP 的 NO 路径不一定主动断开待认证 socket，所以 B 在明确拒绝后经过 8.020 秒客户端期限终止。**超时不是拒绝依据**，真实 AUTH、指定身份、系统 NO、无 CNXN 和 A 的前后对照共同构成证据。

## 四、M4-B：无线 TLS 身份强制校验与撤销

原始报告：[TLS report.json](../../validation/m4-maven/runs/41453219296/tls/evidence/auth/report.json)；独立复核：[TLS evidence-review.json](../../validation/m4-maven/runs/41453219296/tls/evidence-review.json)。

首先通过系统正常 QR pairing API 启动真实 system_server 的 SPAKE2 配对服务。临时身份 A 使用正确秘密调用公共 `Kadb.pair`，实际完成配对与身份清理三项检查；系统授权记录由仅 C 变为严格的 C+A。没有重跑 M3 错误码大矩阵。

| 当前 TLS 连接 | 系统身份裁决 | 当前 ADB 会话 / Shell | 尝试耗时 |
| --- | --- | --- | ---: |
| 已配对 A，负向前 | 精确匹配 A 公钥；服务端握手成功 | 成功 / 成功 | 248 ms |
| 未配对 B | **CERTIFICATE_VERIFY_FAILED** | 拒绝 / 未取得 | 59 ms |
| 已配对 A，负向后 | 精确匹配 A 公钥；服务端握手成功 | 成功 / 成功 | 113 ms |
| 撤销后 A | **CERTIFICATE_VERIFY_FAILED** | 拒绝 / 未取得 | 54 ms |
| 撤销后的合法控制身份 C | 精确匹配 C 公钥；服务端握手成功 | 成功 / 成功 | 99 ms |

五个 Native 进程各建立一个新连接，均有双向 STLS 和 TLS 1.3 ServerHello；整个序列保持 adbd **1772**、listener **32975**，没有重启或换端口。观察器不解密 TLS，因此 ServerHello 只作为协商证据；接受结论还要求实际系统公钥匹配、服务端握手成功和公共 API 的当前 ADB 会话/Shell。TLS 中的 CNXN 已加密，不把明文帧计数缺失误写成不存在或成功。

两个负例在各自唯一的当前连接日志中分别出现：

```text
13:34:59.938  adbd: [server]: Handshake failed in SSL_accept/SSL_connect [CERTIFICATE_VERIFY_FAILED]
13:35:02.384  adbd: [server]: Handshake failed in SSL_accept/SSL_connect [CERTIFICATE_VERIFY_FAILED]
```

它们前面有授权公钥查找不匹配、后面有 transport 关闭；同段没有身份接受或服务端握手成功。Native 得到 **`AdbPairAuthException: Pairing required or trust missing`**，没有进入成功状态。59/54 ms 的直接拒绝不是端口不可用或认证超时，合法 A/C 的前后对照进一步排除了服务故障。

### 撤销的实际生效边界

正常 `IAdbManager.unpairDevice` 按 A 指纹撤销；adbd 在 **13:35:01.882** 收到 DD。授权读取第一次仍见 A、第二次只见 C，撤销与确认共 **329 ms、2 次轮询**。驱动另做一次持久化读回后才建立新 A 连接，随后取得上述证书拒绝，C 在同一服务上继续成功。A 没有被负向尝试重新加入授权集合。

这里证明的是**正常撤销并观察到持久化移除后的新连接失去权限**；329 ms 是这次实际观测，不能当作所有设备的固定撤销 SLA。没有用重启掩盖缓存，也没有另外声称已验证正在运行的长连接即时被踢下线。

## 五、生命周期、隔离与必要修正

每个认证进程的八项检查包含：导入指定临时身份、最初未连接、成功或拒绝的实际结果、Shell 或失败状态、耗时边界、关闭、同一对象关闭后立即拒绝复用、身份存储清理。所有关闭后的复用都在本次记录为 0 ms；未授权会话一旦意外成功，即使后续 Shell 或其他检查失败，也会被判 FAIL。

两组最终授权集合分别恢复为各自的 C；临时 A/B 私钥目录删除、owned forwards 归零。TLS 配对秘密删除，配对服务关闭，`adb_wifi_enabled` 恢复 **0**，Binder 端口 **-1**，原 TLS listener 不再存在。两个 job 原始日志均确认 emulator 应答关闭，随后停止专用 ADB server 并删除专属 AVD/控制身份目录。最终隔离边界是销毁测试实例。

本轮工程变更集中在：

| 范围 | 实际变更与原因 |
| --- | --- |
| Native 独立 consumer | 新增 `auth/Main.kt` 和 4 行构建入口，通过公共 API 执行正反连接、准确计数和关闭后不可复用检查。原 M3 consumer 保持原样。 |
| 协议与系统观察 | 复用 `run_emulator.py`、`adb_observer.py` 和 M3 TLS 元数据解析；增加当前 token/签名归属、内存中的一次性 AUTH3 请求、会话专属日志标记、PID/端口和授权集合交叉检查。 |
| rootless 系统接口 | 用 `getAdbWirelessPort()` Binder 查询真实端口；正常 allow/deny/unpair，不直接写授权文件。 |
| 验收错误处理 | TLS 负向必须有精确证书验证失败，不能由普通 SSL 错误替代；异常路径保留真实 consumer 记录，防止未授权成功被隐藏为 NOT VERIFIED。 |
| CI 隔离 | RSA/TLS 分别使用全新 AVD；独立临时控制身份、显式 serial/server/forward、有限超时和 always 清理；每个单阶段报告只裁决自身。 |
| 既有 CI | M1 workflow 仅增加 M4 路径忽略；M2/M3 workflow 与成功证据未覆盖。 |

两个实际遇到的问题均保留了失败证据：

1. 官方 user 镜像拒绝 shell 读取 `service.adb.tls.port`，虽然 listener 已经启动。改用正常 Binder getter 后实际解决，没有调整系统权限。
2. 先前同一 AVD 串行测试中，已撤销 RSA A 因迟到 CK 在后续 TLS 事件时重新进入 framework 授权表。另有 AUTH3 `Kadb@...` 与 keygen `runner@...` 注释不一致的连接记账问题。前者采用阶段独立 AVD 隔离，后者改为传回实际 AUTH3 字符串。**没有把多余公钥加入预期白名单，也没有声称仅改注释就修复平台通知机制。** 源码预期、实际时序和边界见 [通知生命周期调查](../../validation/m4-maven/research/auth-notification-lifecycle.zh-CN.md)。RSA 最终快照不被描述成平台所有通知队列已排空。

## 六、增量交付与失败记录

| CI / 实际代码 | 结果 | 保存的结论 |
| --- | --- | --- |
| [41447772316](https://github.com/Flyfish233/Kadb/actions/runs/41447772316) / `0122057` | success | 官方 secure user 镜像、真实 AUTH、rootless 管理先决条件 PASS。 |
| [41449058069](https://github.com/Flyfish233/Kadb/actions/runs/41449058069) / `443211e` | failure | RSA 32 项 PASS；TLS 未进入配对，端口属性访问受限。 |
| [41450998239](https://github.com/Flyfish233/Kadb/actions/runs/41450998239) / `7890db6` | failure | RSA、真实配对和 TLS A 接受通过，共 43 项；严格集合检查发现旧 RSA 身份回填，B/撤销未执行。局部清理失败由外层清理恢复，原错误保留。 |
| [41453219296](https://github.com/Flyfish233/Kadb/actions/runs/41453219296) / `03e903e` | **success，2/2 jobs** | 独立新 AVD 的 RSA 32 项与无线 43 项全部通过，清理均 PASS。 |

环境检查点 `94fd039`、RSA 检查点 `c6a9db4`、无线正向及失败检查点 `358a0ef` 已先后推送；有效成果没有等到最终通过才首次交付。初始恢复保留了其他旧 checkout 的未提交工作，未操作 main 或原实验分支。

## 七、证据、实际二进制和精确源码

完整索引从 [verdict.json](../../validation/m4-maven/verdict.json) 与 [最终 run 目录](../../validation/m4-maven/runs/41453219296/) 开始。每组有 `raw-evidence.tar.gz`、逐文件长度/SHA256 清单、artifact 保管链、完整压缩 job 日志、运行环境、系统授权与每个连接的报告。RSA/TLS 分别保存 **66 / 71** 个已脱敏原始证据文件。没有提交私钥、临时配对秘密或长期设备凭据。

| Artifact | 链接 |
| --- | --- |
| RSA 原始证据与实际二进制 | [13145881635](https://github.com/Flyfish233/Kadb/actions/runs/41453219296/artifacts/13145881635) |
| TLS 原始证据与实际二进制 | [13145184771](https://github.com/Flyfish233/Kadb/actions/runs/41453219296/artifacts/13145184771) |
| RSA job 精确对应源码 | [13145233944](https://github.com/Flyfish233/Kadb/actions/runs/41453219296/artifacts/13145233944) |
| TLS job 精确对应源码 | [13145139489](https://github.com/Flyfish233/Kadb/actions/runs/41453219296/artifacts/13145139489) |

两份证据 ZIP 已下载并重算 digest；四份实际可执行文件副本（两个不同 consumer，在两个 job 各一份）的长度和 SHA256 均与来源关联记录一致。两个 job 构建相同的二进制；完整对应源码包也具有相同的内容摘要。同次 CI 执行 Maven 实际解析验证、来源完整性验证、源码收集和 binary association，结果为 verified：630 个清单文件、64 个 published source jars、9 个 source archives、2 个 binary associations。未将这些一致性检查称作新的专业审计或一般性的可复现构建证明。

| 实际对象 | SHA256 |
| --- | --- |
| Native auth consumer，24,765,440 bytes | `c2969cb0f8d730413603e264660b4b5668f64b73f61fe9af0b8952314a595806` |
| Native real pairing consumer，25,107,792 bytes | `cb9dd1c6e895685308ad6ae9962579dfeecd8b3967a4847aa8ed572b44a13d31` |
| 精确对应源码 tar.gz，217,198,849 bytes | `82af86fe9bebafc80762c08905ed89a32f819540c1e50f184ab287bf5e1a0b4d` |
| 依赖来源锁 | `1c1cbe03c78b4810dd096a589c0cb8d57ec2a58b5ceb2b54f9171075c1ddfd92` |

固定候选仍为 **`0.1.0-dev.59105290820b`**，源码 **`59105290820bcbfd4e0336a2e7713006a461527f`**。Git 对象级三方比较见 [baseline-preservation.json](../../validation/m4-maven/baseline-preservation.json)：生产 Kadb/mDNS、依赖配置和来源锁、既有 M1/M2/M3 证据相对用户基线保留。`LegacyPasswordScalarMode.HARDENED`、Alice/Bob 及尾 NUL、TLS exporter 原始标签、HKDF-SHA256、AES-128-GCM、PeerInfo、一次性会话、失败销毁、异常映射与 AOSP 双向 nonce 行为均未改变。

CI artifact 当前保留至 **2027-01-31**。这些实验 artifact 不能作为将来正式分发时唯一的长期源码提供方式；正式分发仍需将实际二进制、对应源码与 notices 一起持久保存。

## 八、历史 M2 失败的限定调查

历史 `41439551154` 的 iOS Simulator Arm64 失败定位到 Native consumer 启动前的 `simctl list devices booted --json` **10 秒超时**。原失败报告没有 Native 启动命令/退出码或 consumer 日志；Java peer 的 143 是 finally 清理结果。相关生产/配对源码、workflow 和已编译 peer class 与已通过 M2 基线相同，不能据此认定 M3/M4 生产回归。

原汇总 210 项包含 140 项仓库中存档 XML；本次真正构建输出中的 **70 项、0 失败**另行核实。未据原汇总虚增执行数，未重跑 M2，也没有把两边都出现的 `Data Migration Failed` 当作已证明的根因。完整限定调查见 [legacy-ci/README.zh-CN.md](../../validation/m4-maven/research/legacy-ci/README.zh-CN.md)。后续可单独处理 Simulator 预检期限和汇总输入范围。

## 九、剩余边界与发行建议

- **M4-C 仍为 NOT VERIFIED。** 实体设备集成留待明确指定和授权的独立任务；本次结果覆盖上述官方镜像和 Native 客户端执行范围。
- **R3-K01 仍开放。** 继承的双向 GCM nonce 协议风险未改、未消除；没有为通过 M4 而单方面变更 AOSP wire protocol。
- **Gate C 未自动提升为 PASS。** M4 关闭的是本目标上的强制客户端身份认证证据缺口，不等于独立专业安全审计，也不自动解决稳定/安全发行的其他门禁。
- TLS 撤销验证针对授权持久化移除后的全新连接；活动长连接即时断开和其他设备/版本的撤销延迟没有另行验收。
- RSA 通知生命周期异常作为外部平台观察保留，本轮通过可销毁实例隔离，未修改 Android 实现或宣称问题已修复。

可以推进固定开发候选的后续集成工作；稳定或安全发行前仍应对 R3-K01 形成明确处置决定，并完成所需实体设备与发行门禁。**本轮未发布 Maven/Release、未修改或合并 main、未更改许可证和仓库可见性。**
