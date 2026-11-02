# M4 强制身份认证测试环境调查

调查日期：2026-11-02。本文记录目标选择和 AOSP 源码预期；实际运行结果以独立 CI 证据为准。

## 首选目标

选择 Google 官方 SDK 的 `system-images;android-35;google_apis_playstore;x86_64`，建立仅用于本轮任务、结束后销毁的新 AVD。官方清单在调查时提供 revision **9**、extension level **13**、stable channel；下载地址、大小、SDK 清单校验值和源码散列保存在 [primary-sources.json](primary-sources.json)，对应包条目保存在 [official-play-api35-package.xml](official-play-api35-package.xml)。

Google Play 系统镜像使用 release key，官方说明不提供 `adb root`。因此 M4 应采用普通 shell 的系统管理 API，不能直接沿用 M3 的 root 和写入 `/data/misc/adb/adb_keys` 流程。`ro.adb.secure=1`、`ro.build.type=user`、shell UID 2000 仍须在启动后实际核实；独立连接必须收到真实 AUTH token 才能通过环境门槛。[官方 AVD 文档](https://developer.android.com/studio/run/managing-avds)

不修改镜像、adbd、`ro.adb.secure` 或 SELinux。原 Google APIs/userdebug 目标已有 `auth not required` 证据，无需反复尝试同一不符合条件的配置。完整 AOSP 重编译不作为首选，因为官方 user 镜像存在更小且可重复的验证路径。

## 独立身份和控制通道

为新 AVD 生成临时控制身份 C，再单独生成测试身份 A、B。设置独立 `ANDROID_USER_HOME`、`ANDROID_AVD_HOME`、ADB server 端口，并在每条设备操作中指定 `emulator-5554`。`ANDROID_EMULATOR_HOME` 默认使用 `ANDROID_USER_HOME`；也可显式设为同一路径以消除继承环境的差异。[官方环境变量说明](https://developer.android.com/tools/variables)

Android 15 的 [init.ranchu.adb.setup.sh](https://android.googlesource.com/device/generic/goldfish/+/refs/tags/android-15.0.0_r1/init.ranchu.adb.setup.sh) 在授权文件尚不存在时，将 `ro.boot.qemu.adb.pubkey` 中的宿主公钥导入新 AVD。此机制仅用于临时控制身份 C；必须验证 A、B 公钥在试验前不在授权记录中。

通过 C 建立端口映射只负责把字节送到实际 adbd listener。A、B 在该端口上的 AUTH/STLS 会话要分别观察、分别裁决。不能把 C 已经连接当成 A 或 B 的认证证据。

## 普通 shell 可用的系统授权路径

Android 15 的 [Shell manifest](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-15.0.0_r1/packages/Shell/AndroidManifest.xml) 为 shell 声明 `android.permission.MANAGE_DEBUGGING`；[AdbService](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-15.0.0_r1/services/core/java/com/android/server/adb/AdbService.java) 使用该权限保护以下方法。实际镜像仍须以 `dumpsys package com.android.shell` 和 Binder 探测确认权限。

以下编号来自固定的 [Android 15 IAdbManager.aidl](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-15.0.0_r1/core/java/android/debug/IAdbManager.aidl)，只适用于已确认的 API 35 测试目标：

| Binder transaction | 方法 | M4 用途 |
| --- | --- | --- |
| 1 | `allowDebugging(boolean, String)` | 在 A 当前请求的公钥指纹已核对后，通过系统正常授权流程确认 |
| 2 | `denyDebugging()` | 明确拒绝当前 B 授权请求，取得系统 `NO` 裁决 |
| 4 | `allowWirelessDebugging(boolean, String)` | 只允许本次 AVD 当前 Wi-Fi 网络，使用 `alwaysAllow=false` |
| 6 | `getPairedDevices()` | 查看配对身份状态 |
| 7 | `unpairDevice(String)` | 按指纹撤销本轮 A 身份 |
| 9 | `enablePairingByQrCode(String, String)` | 启动真实系统 SPAKE2 配对服务；与 M3 的 QR 秘密路径一致 |
| 10 | `getAdbWirelessPort()` | 读取真实无线调试 listener 端口 |
| 11 | `disablePairing()` | 关闭本轮配对服务 |
| 12 | `isAdbWifiSupported()` | 无写入的 ABI 与能力探测 |

`dumpsys adb` 由 system_server 读取并输出 `user_keys`、`system_keys`、`keystore` 和 `last_key_received`。[AdbDebuggingManager.dump](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-15.0.0_r1/services/core/java/com/android/server/adb/AdbDebuggingManager.java) 因而能够在不 root、不直接读取受保护目录的情况下提供公钥授权证据。门槛不能只检查命令退出码：必须看到公钥字段，并核对临时 C 身份。

## RSA AUTH 的正反验证

在 A 的初次连接中等待 AUTH token、签名尝试和公钥请求。将系统 `last_key_received` 与 A 的 Android 公钥 MD5 指纹比较后，才能调用 transaction 1。`AdbDebuggingManager` 自身也核对当前待处理指纹；不匹配就拒绝该授权响应。

初次人工授权允许当前会话上线，并不足以单独证明签名路径。关闭该会话后，由相同 A 私钥重新建立连接，必须看到 AUTH token → AUTH signature → CNXN，随后完成 Shell。这一新的连接是已授权 RSA 身份签名通过的主要证据。

B 使用独立未授权密钥。在其 AUTH 公钥请求和系统指纹都已观察到后，调用 transaction 2，并保存 `Denying adb confirmation` 与 `adbd_auth: received packet: NO` 等系统日志。B 不应取得 CNXN 或成功 Shell；A 在 B 前后均应可连接。

Android 15 [libadbd_auth](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-15.0.0_r1/libs/adbd_auth/adbd_auth.cpp) 的 `DenyUsbDevice` 清除待授权请求，没有向连接发送强制关闭回调。因此 B 在明确 `NO` 之后等到客户端认证超时是预期的可能行为。拒绝证明必须由真实 AUTH、系统明确拒绝、没有 CNXN 和成功 A 对照共同构成，超时本身不成立。

## 无线 TLS 的验证与撤销边界

Android 15 [adbd auth.cpp](https://android.googlesource.com/platform/packages/modules/adb/+/refs/tags/android-15.0.0_r1/daemon/auth.cpp) 在要求认证时，将 TLS 客户端证书中的公钥与授权公钥逐个比较。M4 应取得对应连接的 STLS/TLS 流量、系统匹配/不匹配裁决和 Shell 结果，分别证明 A 接受、B 拒绝。`auth not required` 一旦出现在目标身份校验路径，不能将该运行算作强制身份认证通过。

按指纹 unpair 的实现先向 adbd 发送 `DD`，用于断开同一公钥的连接，再把移除操作排入持久化队列。`libadbd_auth::IteratePublicKeys` 每次读取 `/adb_keys` 与 `/data/misc/adb/adb_keys`；这里没有需要任意等待数分钟的长期证书文件缓存。

撤销边界应设置为：系统授权记录已确认不含 A，再创建全新 A 连接，并要求它被身份校验拒绝。该观察窗口允许框架消息队列和文件写入的短暂异步延迟，但不能通过重启服务掩盖未生效的撤销。记录撤销时间、轮询次数、授权集合变化，以及 listener/adbd PID 在前后的状态。运行结束保留 C 控制身份到清理结束，然后销毁整个 AVD 与全部临时密钥。

## 来源和结论范围

本目录的 AOSP 文件元数据固定到 `android-15.0.0_r1`，并记录下载后解码源码的 SHA256，用于核对 API 35 的机制预期。它们没有被宣称为 Google Play revision 9 整个镜像的精确对应源码。实际镜像的 build fingerprint、SDK 包 revision、官方 SDK 输入文件 SHA256 和系统日志由运行证据单独确定。这个 `user` 镜像禁止普通 shell 读取或直接执行 adbd，因此单独的运行时 adbd ELF 摘要未取得；原始权限失败也保留在环境证据中。Kadb、固定 Maven 候选及其所链接二进制的对应源码关系继续使用项目既有来源验证流程。

调查本身不判定 M4-A 或 M4-B 通过。只有实际执行的正反连接和撤销证据能够升级对应裁决。
