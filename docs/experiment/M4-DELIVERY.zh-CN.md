# M4：强制身份认证与真实身份拒绝验证

## 执行中检查点

恢复并核实远端基线 `895674e5725b2cf328bf427e1500cb8f2e6e231e`，分支
`work/spake2-maven-migration`。M1/M2/M3 已有成功证据不变。本次只执行 M4。

已恢复干净的 M3 工作树；另一旧 M1 checkout 中的未提交改动完整保留。
初始检查没有发现运行中的 Gradle、emulator 或本分支 CI。当前本地无 `/dev/kvm`，
真实 Android 执行使用独立 GitHub Ubuntu runner 的专用一次性 AVD。

第一项可执行调查使用官方 `system-images;android-35;google_apis_playstore;x86_64`
镜像。通过 emulator 标准机制配置独立临时控制身份 C，随后要求实际
`ro.adb.secure=1`、真实 AUTH token 和 rootless 系统管理权限。未修改镜像、
系统分区、认证属性或授权文件。A/B 测试身份与 C 分离。

独立 M4 workflow 及环境探针已保存；探针不是 M4-A/B 完成证据。
环境 CI [41447772316](https://github.com/Flyfish233/Kadb/actions/runs/41447772316) 已实际成功。
镜像 fingerprint 为 `google/sdk_gphone64_x86_64/emu64xa:15/AE3A.240806.036/12592187:user/release-keys`，
revision 9；实际 `ro.adb.secure=1`、`ro.debuggable=0`、shell UID 2000。
新连接返回真实 20 字节 AUTH token，没有 CNXN；授权 dump 确认独立控制身份。
完整原始证据与下载 digest 已保存在 `validation/m4-maven/runs/41447772316/`。
用户镜像限制 shell 读取/直接执行 adbd，相关失败原样保留，不伪造二进制摘要。

| 项目 | 当前裁决 |
| --- | --- |
| M4-A RSA AUTH | PASS：实际 4 个会话、32 项检查 |
| M4-B 无线 TLS 身份强制认证与撤销 | NOT VERIFIED：配对及已授权 A 正向已实际通过，B/撤销仍待执行 |
| M4-C 实体设备 | NOT VERIFIED（无设备授权，不执行） |
| M4 整体 | CONDITIONAL PASS（TLS 继续执行中） |

固定候选仍为 `0.1.0-dev.59105290820b`，对应源码
`59105290820bcbfd4e0336a2e7713006a461527f`。生产密码学未修改；R3-K01 保持开放。

## RSA 实际通过检查点

实际代码 `443211e91262fb021335b168b42fe7f18591b6eb`，CI [41449058069](https://github.com/Flyfish233/Kadb/actions/runs/41449058069)。M4-A PASS。
独立临时 A 首次通过匹配的系统确认授权；新连接真实 AUTH token 和 Kadb 的 256 字节签名经独立公钥验证，随后 CNXN 与 Shell 成功。
未授权 B 的签名本身有效，但没有授权记录；系统明确记录 `Denying adb confirmation` 与 `adbd_auth: received packet: NO`，没有 CNXN。
B 经 8179 ms 有界等待结束，随后 A 再次完成 AUTH、CNXN 与 Shell。四个进程各执行八项身份及生命周期检查。
原授权集合、forward、临时私钥和 shell 状态的清理通过。

该 CI 的总体状态为 failure：无线部分尚未进入配对，原因是普通 shell 读取 `service.adb.tls.port` 被平台拒绝，
真实 adbd 已记录 listener 在端口 36175 启动。此处只调整测试工具使用正常 Binder 查询，不改动目标系统权限或认证机制。
原始报告、66 个证据文件、运行日志及两份实际二进制摘要核对保存在 `validation/m4-maven/runs/41449058069/`。

## 无线正向实际通过与阶段隔离修正

代码 `7890db69afa29e9dd29976f72314e853a4d555c8` 的 CI [41450998239](https://github.com/Flyfish233/Kadb/actions/runs/41450998239) 已解决普通 shell 无法读取端口属性的问题：通过 `IAdbManager.getAdbWirelessPort()` 取得实际 TLS listener **42005**，adbd PID **1720**。真实系统 SPAKE2 配对成功，公钥持久化与独立 A 的 STLS、TLS 1.3、adbd `Matched auth_key`、`Handshake succeeded` 和 Shell 均成立。该次实际执行 43 项 Native 检查（RSA 32、配对 3、TLS 正向 8），另有 31 项工具测试通过。

工具在 B 测试前发现授权集合意外增加了先前撤销的 RSA A，严格停止，没有把额外公钥纳入预期白名单。13:18:21.902 系统已接收移除 RSA A 的 `DD`；13:18:25.453 TLS 事件发生时，延后的 RSA `CK` 到达 framework，并再次更新该身份的授权记录。因此本次 B 拒绝与 TLS 撤销都没有执行，M4-B 保持 NOT VERIFIED。TLS 阶段的局部授权恢复检查失败；外层清理随后移除了本轮全部临时身份，最终授权集合、端口、密钥和无线设置恢复通过，AVD 已销毁。

源码调查另外确认正常授权接口应使用当前 AUTH3 的完整公钥字符串；仅保持 RSA key blob 相同而替换注释，会改变 framework 按完整字符串维护的连接状态。修正将使用观察器内存中核实的实际请求串，并将 RSA、TLS 分成独立创建和销毁的 AVD。TLS 自身的已配对、未配对、撤销后重连仍要求同一 adbd PID 和 listener。此次不是关闭认证或改动授权判断。71 个已脱敏证据文件、完整 job 日志、两份实际可执行文件的摘要核对和下载身份保存在 `validation/m4-maven/runs/41450998239/`。
