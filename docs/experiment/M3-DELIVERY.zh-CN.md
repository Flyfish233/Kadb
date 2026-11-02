# M3：真实 AOSP adbd、无线配对与认证链验证交付

## 结论

**M3 的主要目标——公共 `Kadb.pair` 与真实 Android AOSP 配对服务互操作，以及约定的分层负向验收——PASS。M3 整体为 CONDITIONAL PASS：当前镜像未启用连接身份认证，完整的强制认证链仍未验证。**

最终真实执行代码：[`ef5ae480e598ec08309fa6bfed12af44996bbfea`](https://github.com/Flyfish233/Kadb/commit/ef5ae480e598ec08309fa6bfed12af44996bbfea)。

最终 CI：[`41440741512`](https://github.com/Flyfish233/Kadb/actions/runs/41440741512)，`native-adbd` job **success**。所有编译、来源关联、受控 peer、真实 adbd、真实系统配对和清理步骤均实际执行成功。

| 验收项 | 裁决 | 实际证据与剩余范围 |
| --- | --- | --- |
| **M3-A：ADB 连接与认证** | **CONDITIONAL PASS** | Native 公共 API 15/15，三次连接、两次重连、完整清理；另在无线端口实际完成双向 STLS 与 Shell。RSA AUTH 正向及未授权拒绝尚未验证。 |
| **M3-B：真实 AOSP SPAKE2 配对** | **PASS** | 真实系统服务上的错误码拒绝、正确码配对与 Android 公钥持久化成功；后续 STLS 连接成功。独立受控 peer 的 13 会话、11 项负向验收全部通过，层级单独记录。 |
| **M3-C：实体设备集成** | **NOT VERIFIED** | 未选择、修改或测试任何个人手机；无专用实体 Android 或 iOS 执行环境。 |

实际系统日志包含 `adbd_tls_verify_cert: auth not required`，与 `ro.adb.secure=0` 一致。因此，STLS 连接成功不能证明未配对身份会被拒绝。本交付不宣称完整连接身份强制验证 PASS。

机器裁决：[`validation/m3-maven/verdict.json`](../../validation/m3-maven/verdict.json)。

## 一、恢复、边界与增量交付

恢复基线为 `ecc0f358b46a9805d0c102318f211b5e4fe67f14`，工作分支始终为 `work/spake2-maven-migration`。先检查多个旧工作树，再从干净的 M2 checkout 建立独立副本；旧 M1 checkout 的未提交修改未被覆盖。

| 提交 | 内容 |
| --- | --- |
| `24a9672ccc2b62698590d9e47c8c82896a873754` | 独立 M3 workflow、恢复记录与历史原始失败日志。 |
| `794b69fecdac0d3fd7d7a54d11f944fa944a65f2` | 修复 Emulator listener 切换问题，增强逐连接证据与恢复断言。 |
| `e49405fa42668cde4ff264cb88090d8643f8812b` | **先行推送真实 adbd 15 项成功结果**，保留 AUTH 缺口。 |
| `12dcab973a828c44d1bd2d40673b768ff45f9c12` | 真实系统配对驱动、独立 Native consumer、13 会话受控负向测试。 |
| `ef5ae480e598ec08309fa6bfed12af44996bbfea` | 在已保存 M3-A 检查点之后触发 M3 配对执行。 |

M1/M2 的既有结论、测试断言和固定候选未被改写。M1 的触发范围仅排除独立 M3 harness 路径。首次 Native harness 推送按既有规则同时触发了 M2 Darwin workflow；其结果未被计入本次 M3 验收，也未成为继续工作的门槛。后续实现提交与 M3 专用执行请求分开，最终只触发 M3 workflow。

没有修改 `main`、原实验基线、SPAKE2 生产密码学实现、许可证或仓库可见性；没有正式发布，也没有开启第四轮密码学审计。

## 二、真实对端、环境与来源身份

| 项目 | 实际记录 |
| --- | --- |
| CI host | Ubuntu 24.04 runner，Linux `7.0.0-1017-azure`，x86_64，KVM |
| JDK / Gradle | Temurin `25.0.5+8` / Gradle `9.6.0` |
| Kotlin / AGP | 项目 Kotlin `2.4.20` / AGP `9.4.0`；Gradle 内置 Kotlin 版本另行记录 |
| Emulator | `37.2.13`，build `16740729` |
| Android 镜像 | `system-images;android-35;google_apis;x86_64`，revision **9**，extension level **13** |
| Android | API **35**，Android **15** |
| fingerprint | `google/sdk_gphone64_x86_64/emu64xa:15/AE3A.240806.043/12960925:userdebug/dev-keys` |
| adbd | `1.0.41`，`/apex/com.android.adbd/bin/adbd` |
| adbd SHA-256 | `008accf96d7cf61d63af6c30d9ec60cdb0ae88bed7b09f49967e257ec5bf5893` |
| host adb | `1.0.41`，platform-tools `37.0.1-15733141` |
| Native TLS | 静态 BoringSSL，固定源码 `5b83e5d1abf0ae0033ae52ab579d906b67633b2c` |
| SPAKE2 Maven | **`0.1.0-dev.59105290820b`** |
| SPAKE2 对应源码 | **`59105290820bcbfd4e0336a2e7713006a461527f`** |

真实配对由 `android.debug.IAdbManager.enablePairingByQrCode` 启动，调用 Android 系统 JNI 的 AOSP native pairing server。采用每次新生成的临时六位码，不需要读取或保存用户配对码。Android 的系统服务实际持有该端口：

| 端点 | 实际进程 | 本次端口 | 证据 |
| --- | --- | ---: | --- |
| SPAKE2 pairing | `system_server`，PID **558** | **36803** | 系统 pairing-start 日志、`_adb-tls-pairing._tcp` 广播、`ss -ltnp` 进程归属 |
| 配对后 ADB TLS 连接 | `adbd`，PID **3428** | **45249** | `service.adb.tls.port`、`ss -ltnp`、双向 STLS 与真实 Shell |
| 普通 ADB listener | 同一模拟器的 adbd | **5555** | 原有监听、ADB forward 和逐连接 header 元数据 |

三个端口用途不同。配对通过字节透明的 loopback relay 和官方 ADB forward 到达真实 Android 服务；没有项目 Java server 参与该段验收。

## 三、M3-A：十五项 Native 公共 API 与历史故障修复

历史 CI `40331404006` 的原始日志显示：Android 已启动，Package Manager 就绪，`adb root` 成功；随后 `adb tcpip 5556` 返回 0，控制 transport 立即变为 offline，Native consumer 实际执行数为 **0**。

对应 AOSP `daemon/main.cpp` 在设置 `service.adb.tcp.port` 后使用指定端口，替换无 USB 场景下的默认 TCP/VSOCK 5555 listener。旧驱动因此破坏了自己的 Emulator 控制入口。新驱动沿用已经存在的 5555 listener，不再调用 `adb tcpip` 或改写 listener properties；公钥重载使用有界 root/unroot 重启。

这与 M2 的故障不同：M2 当时 ADB transport 正常，ART 已执行六项身份检查，应用连接 `10.0.2.2` 才发生 `ENETUNREACH`。本次保留 M2 已验证的默认网络与路由 readiness 门禁。

本次两次 M3 CI 各自完整执行十五项；最终代码的结果为：

| 类别 | 实际检查 |
| --- | --- |
| 身份 / 协商 | `identity_import`、`feature_negotiation` |
| Shell | `shell_v2` |
| Sync | `sync_transfer`、`sync_stat`、`sync_shell_metadata`、`sync_directory`、`sync_symlink`、`sync_empty_file` |
| APK | `install`、`uninstall` |
| 生命周期 | `reconnect_1`、`reconnect_2`、`cleanup`、`close_terminal` |

最终执行 **15/15**，consumer 退出码 **0**，耗时 **2790 ms**；三次实际连接，两个重连，无 header parse error。Sync 传输 **1,048,589 bytes**，内容摘要一致。初次独立检查点同样为 15/15，耗时 3037 ms。

普通 listener 的 AUTH 和 STLS 帧实际均为零；未授权 RSA probe 未执行。框架没有关闭认证，也没有把缺失探针记作通过。最终无线连接上的 STLS 成功证据来自下一节，不能追溯声称普通 5555 listener 使用了 TLS。

## 四、M3-B：真实配对与后续连接

完整调用路径保留公共 `Kadb.pair` 与既有产品实现：真实 TLS → 当前连接 exporter → Legacy SPAKE25519 HARDENED → HKDF → AES-GCM → PeerInfo 校验。

| 实际执行 | Native 检查数 | 退出码 | 对端证据 |
| --- | ---: | ---: | --- |
| 错误配对码 | **3** | **0**，预期拒绝验收成功 | TLS 1.3 ServerHello 后，真实 system_server 记录 GCM 解密失败；临时公钥未进入授权列表。 |
| 正确配对码 | **3** | **0** | 公共 `Kadb.pair` 正常返回；Android 实际新增临时公钥。 |
| 配对后的连接、Shell、关闭 | **4** | **0** | 一次双向 STLS，真实 Shell marker 成功，连接关闭且临时身份清除。 |

合计是 **3 个真实 Native 进程、10 项检查**，其中只有前两项为配对会话。两次配对均实际协商 TLS **1.3**，ServerHello version `0x0304`，cipher `0x1301`。

错误码场景在真实系统进程中记录 `Failed to decrypt`、`Unable to decrypt data`；Kadb 得到 `Could not exchange peer info.`。其通过条件同时要求 TLS 协商、系统 GCM 拒绝和授权列表未改变，不能用 TCP 连接失败替代。

随后正确码成功，Android 新增且只新增本次公钥。独立按 ADB 格式计算公钥 MD5 指纹与系统记录一致。清理后公钥集合恢复到原集合。

三次进程均导入同一个未改写的临时 RSA 私钥文件。报告中的 `KadbIdentitySnapshot.fingerprintSha256` 对重新生成的证书 DER 求摘要，因此配对与后续连接的证书摘要可以不同；它不是 ADB 授权公钥的稳定指纹。此区别已在证据复核中核对。

**后续连接成功与身份拒绝强制执行仍是两个结论。** 当前 adbd 明确记录 `auth not required`；没有执行未配对 TLS 身份拒绝探针。该项保持 **NOT VERIFIED**。真实端点上的 exporter 错配注入也未执行，下一节提供单独层级的会话隔离验收。

## 五、独立受控 peer：13 场实际会话，11 项负向验收

该层使用独立 Java peer 和实际 Native 公共 API consumer；`real_adbd=false`。七个参考 JAR 的固定 SHA-256 门禁保留，Java peer 不链接 Kadb 生产类。

双方退出码均为 **0**。实际日志包含 **13 次 accept、13 次 TLS 1.3 完成、13 个完整 case**；Native 同一进程执行所有场景，最后正向恢复成功。

| 场景 | 数量 | 判据 / 关闭方向 |
| --- | ---: | --- |
| 初始正向、失败后的正向恢复 | 2 | 完整 PeerInfo，观察客户端关闭；最后一次在同一 Native 进程内。 |
| 错误码、跨 TLS 会话旧 exporter、错误角色、缺失身份 NUL | 4 | 已完成 TLS/SPAKE 后，peer 实际 GCM 认证失败；peer 发起关闭。 |
| 无效 SPAKE 长度、不支持的 header 版本 | 2 | Native 拒绝实际异常消息，观察客户端关闭。 |
| GCM tag 篡改、已认证但非法 PeerInfo 类型 | 2 | peer 先验证正常客户端 PeerInfo，再注入响应错误；观察客户端关闭。 |
| 网络中断 | 1 | peer 在收到客户端 SPAKE 消息后断开。 |
| coroutine 超时、显式取消 | 2 | 约 1500 ms 的有界结束，观察客户端关闭；取消完成 `cancelAndJoin()`。 |

跨会话测试保存首个真实 TLS 会话的 exporter，并明确断言它不同于新会话的 exporter，再用于新会话制造实际 GCM 失败。没有记录 exporter 字节。

六个负向场景直接观测到客户端发起关闭，另外五个仅有 peer 发起关闭证据，报告保留这个区别。公开身份存储清除、新会话恢复得到验证；没有声称从外部观察到了内部内存全部清零。

驱动的部分失败结果、缺失 final JSON 和实际执行事件也独立保留。M2 原有默认调用仍为两个会话；新增十三会话只由 `--m3-negative-suite` 启用。

## 六、清理与秘密处理

M3-A 的原始命令确认：APK 已卸载、测试目录删除、forward 删除、授权列表原字节及 owner/group/mode 恢复，adbd UID 与 listener/auth properties 恢复。

M3-B 使用系统的定向 `unpairDevice` 移除本次临时身份，并验证原授权集合完全恢复；取消 pairing 服务、移除两个 owned forwards，等待无线调试异步关闭后恢复原 setting、TLS/GUID properties 和 UID **2000**。实际 `cleanup_errors=[]`。

两段测试的私钥与配对码仅存临时目录，测试结束删除。配对命令与系统日志在写入证据之前脱敏；原始 artifact 没有另附未经脱敏的 pairing logcat。没有将临时码、私钥或长期凭据提交到 Git。

ADB server 使用独立端口 **5038**，模拟器明确指定 `emulator-5554` 并先检查 `ro.kernel.qemu=1`；CI 最后销毁专用 AVD、bootstrap key 目录和所属进程。未自动选择实体设备。

## 七、证据、完整对应源码与失败记录

| 材料 | 位置 |
| --- | --- |
| 首次真实 adbd CI | [41439551227](https://github.com/Flyfish233/Kadb/actions/runs/41439551227) |
| 最终真实配对 CI | [41440741512](https://github.com/Flyfish233/Kadb/actions/runs/41440741512) |
| 最终二进制及原始执行 artifact | [13140836193](https://github.com/Flyfish233/Kadb/actions/runs/41440741512/artifacts/13140836193) |
| 精确对应源码 artifact | [13141210687](https://github.com/Flyfish233/Kadb/actions/runs/41440741512/artifacts/13141210687) |
| 最终报告、日志摘要、原始记录压缩包 | [`validation/m3-maven/runs/41440741512/`](../../validation/m3-maven/runs/41440741512/) |
| 历史 transport 失败与本地环境准备失败 | [`validation/m3-maven/recovery/`](../../validation/m3-maven/recovery/) |

最终源码包 SHA-256：

`e604bc1851d6632fed08ab5b64b4d7b3d27e2467d2ff3f732a58b3982318fc9c`

最终对应源码 ZIP artifact digest：

`4dfcf84f047bdb714e6e0d46441756fd97fe2698df12f5229c58d02818da3196`

最终二进制/执行 ZIP artifact digest：

`b299777c9574fb1ff774b70a33863223043b4eb86a1e31bcb7a3868930cd3b32`

实际执行的 real-pairing Native binary SHA-256：

`b7c66748f36d50aa45d2747229a517e1d296d8969d7f02feaad9c25cf9cd36f8`

已下载并重算最终 artifact 内四个二进制的长度与 SHA，均吻合 exact-code source association。完整源码收集、校验和生成在同次 CI 中执行；复核了 manifest/result 与 binary association，没有把该步骤描述成一次新的 M1/M2 密码学审计。

最终原始证据包包含 **47 个文件**，逐文件长度与 SHA 清单、原 ZIP digest、原始 job log、关键 JSON 都已保留。文件副本忠于实际执行，CI 状态报告没有事后改成另一种结论。

本地补充 Native 构建曾因 JVM trust-store PKIX 和离线缺失 iOSX64 依赖元数据停止。这些是环境准备失败，协议执行数为零；原始失败日志完整保留。没有通过跳过来源校验或关闭 TLS 校验取绿。真正十三会话验收来自最终 CI。

## 八、剩余问题与正式发行建议

1. **AUTH / 连接身份门禁：** 在启用认证的专用测试目标上补充真实 RSA AUTH 正向、未授权 RSA 拒绝，以及未配对 TLS 身份拒绝。当前 stock Emulator 的日志已经明确界定此缺口，不继续无界寻找替代镜像。
2. **实体设备：** 在明确指定的可恢复 Android 测试设备上完成配对、连接及授权恢复；iOS 真机访问 Android 为后续独立扩展，不使用 Simulator 成功替代。
3. **R3-K01：** 双向 GCM nonce 继承风险仍未消除。本次保留 AOSP wire compatibility，未单方面修改 nonce、HARDENED、NUL 身份、exporter label、HKDF、GCM 或 PeerInfo 语义。
4. **发行：** 本轮足以保留并推进固定开发候选。建议暂缓宣称“完整强制认证链已验证”或作稳定安全发行；先完成上述认证/实体集成门禁，并对 R3-K01 明确形成发行决定。任何后续分发均应随实际二进制持久保留对应源码与 notices；CI artifact 的保留期到 2027-01-31，不能成为正式发行唯一的长期源码提供方式。

## 复现入口与原始规范

专用 workflow：[`m3-adbd.yml`](../../.github/workflows/m3-adbd.yml)。真实 ADB driver、系统 pairing driver、受控 peer 命令及有界清理均在受测提交中明确记录；不接受通过选择首个设备自动运行。

原始系统实现：

- [Android 15 IAdbManager AIDL](https://android.googlesource.com/platform/frameworks/base/+/refs/heads/android15-release/core/java/android/debug/IAdbManager.aidl)
- [Android 15 系统 pairing JNI](https://android.googlesource.com/platform/frameworks/base/+/refs/heads/android15-release/services/core/jni/com_android_server_adb_AdbDebuggingManager.cpp)
- [Android 15 AdbDebuggingManager](https://android.googlesource.com/platform/frameworks/base/+/refs/heads/android15-release/services/core/java/com/android/server/adb/AdbDebuggingManager.java)
- [AOSP pairing connection](https://android.googlesource.com/platform/packages/modules/adb/+/refs/heads/android15-release/pairing_connection/pairing_connection.cpp)
- [AOSP adbd listener 初始化](https://android.googlesource.com/platform/packages/modules/adb/+/refs/heads/android15-release/daemon/main.cpp)
