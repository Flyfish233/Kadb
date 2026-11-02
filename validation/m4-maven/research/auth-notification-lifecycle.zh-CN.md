# M4：RSA 通知、完整公钥字符串与跨阶段隔离边界

本记录解释 CI [41450998239](https://github.com/Flyfish233/Kadb/actions/runs/41450998239) 的实际中断。它没有把未执行的 TLS B 或撤销后重连记作成功，也不提出修改 Android 或 Kadb 生产协议。

## 实际观察

本次代码为 `7890db69afa29e9dd29976f72314e853a4d555c8`。真实 Google Play API 35 user 镜像中，adbd PID 1720、system_server PID 538，`ro.adb.secure=1`。RSA A/B 验收成功；接着 TLS A 完成系统配对、授权记录持久化及实际 STLS 连接。adbd 在 13:18:25.452 匹配 TLS A 公钥，13:18:25.453 记录服务端握手成功；Native 公共 API 完成当前会话握手和 Shell 标记检查。

随后测试发现，先前已经撤销的 **RSA A** 重新出现在授权记录中。它与 **TLS A** 是不同身份。测试驱动因此在 TLS B 执行前停止，既没有接受额外授权项来放宽测试条件，也没有进行未配对 B 或撤销后 A 重连验收。

| 时间 | 当前运行的原始日志 / 授权记录 |
|---|---|
| 13:18:09.646 | framework 收到 RSA A 的 AUTH3 公钥，comment 为 `Kadb@runnervm48cm3`。 |
| 13:18:09.814 | 正常 allowDebugging 保存相同 RSA 公钥，但 comment 为 `runner@runnervm48cm3`。 |
| 13:18:11.783–.784 | 首次会话的断开通知携带 `Kadb@...`，framework 记录该字符串 `alwaysAllow=false`、此前连接时间为 0；随后已授权重连的 CK 携带 `runner@...`。 |
| 13:18:21.902 | 正常 unpair 向 adbd 发送删除 RSA A + `runner@...` 的 DD；紧接着的授权集合只剩控制身份。 |
| 13:18:25.453 | TLS A 成功连接时，framework 收到迟到的 RSA A + `runner@...` 的 CK，并更新它的连接时间。 |
| 13:18:25 之后 | `tls-before-b-keys` 连续 42 次观察到控制身份、TLS A、RSA A 三个公钥；期望集合只有控制身份和 TLS A。 |

RSA A 的公钥 SHA256 是 `c52f9fcd7966d189afccff3eaa49093cd67214d38e0efe1b33ed20d5724440d9`；TLS A 是 `89b2848d31b075adc5305748602cb216c3cdc1a0b70ff75e231c77be118bf300`。报告只保留哈希和已脱敏日志，不保存私钥或完整公钥。

## 参考 AOSP 的两个独立机制

以下解释来自固定 `android-15.0.0_r1` 参考源码。源码内容 SHA256 见 [primary-sources.json](primary-sources.json)。**该 tag 不是 Google Play 镜像精确对应源码的声明**；镜像身份由另行保存的官方 SDK 输入哈希和运行时 fingerprint 识别。观察结果与下述机制一致，对 Google 镜像内部调用路径的判断仍属于有源码依据的解释。

### 1. 传统 RSA CK/DC 通知可以等待后续唤醒

[frameworks/native 的 adbd_auth.cpp](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-15.0.0_r1/libs/adbd_auth/adbd_auth.cpp) 中，`NotifyAuthenticated`（422–428）和 `NotifyDisconnected`（431–439）把传统 RSA CK/DC 写入输出队列，没有调用 `Interrupt`。TLS 连接及断开通知函数（442–466）则明确调用 `Interrupt`。工作线程经 eventfd 唤醒后，在 349–359 更新 framework fd 的可写订阅，再由 378–383 排空输出队列。AUTH3 提示分发（121–140）也会触发唤醒。

这解释了本次两次成批到达：先前首次 RSA 断开与 A 的已授权重连 CK 在 B 的 AUTH3 提示时送达；最后 A 的 CK 在 TLS A 连接时送达。单纯等待一个固定延时不能保证排空一个没有主动唤醒的队列。

[AdbDebuggingManager.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-15.0.0_r1/services/core/java/com/android/server/adb/AdbDebuggingManager.java) 通过异步 Handler 处理 CK（490–496、1050–1064），更新连接计数、连接时间并请求持久化。`setLastConnectionTime`（2225–2236）可以把已经不在授权 map 中的 key 重新插入。因此先观察到删除、后处理旧 CK，足以出现本次回填。

**本次直接回填的字符串与 DD 删除的字符串完全相同，均为 RSA A + `runner@...`。不能把这次失败仅解释成“另一个 comment 别名没有删除”。**

### 2. comment 不影响 RSA 数学身份，却参与 framework 的字符串记账

[daemon/auth.cpp](https://android.googlesource.com/platform/packages/modules/adb/+/refs/tags/android-15.0.0_r1/daemon/auth.cpp) 的签名验证（156–190）从公钥文本的第一个字段解码 RSA 公钥；验证成功后保留整个授权记录字符串作为 `auth_key`。framework 的 `MESSAGE_ADB_ALLOW`（918–938）只核对公钥指纹，然后按传入的完整字符串更新连接表和授权 map；CK/DC 也按完整字符串进行计数。`findKeyFromFingerprint`（1917–1924）返回匹配到的一项完整字符串，`removeKey`（1927–1931）删除该字符串。

所以，使用 `adb keygen` 公钥文件的 `runner@...` 去允许实际 AUTH3 提交的 `Kadb@...`，虽然公钥指纹完全相同、RSA 签名验证确实有效，却会造成首次连接/断开记账不一致。测试应把**实际观察并验证过的当前 AUTH3 完整字符串**传回正常授权 API，像系统确认 UI 那样处理；只在内存中暂存，持久证据继续使用哈希。

统一 comment 是独立的测试工具修正，不能保证消除前述异步 CK 回填。

## 撤销边界与测试选择

framework 的 unpair（1160–1174）发出 DD 并移除授权 map 项；该分支本身不清除 `mConnectedKeys`。周期更新分支（1035–1042）还会从连接表刷新授权 map。不能把一次读取到公钥消失等同于所有旧事件已经处理完毕。

也不宜要求每次已授权 RSA 重连必须收到 DC 才继续：参考 [adb.cpp](https://android.googlesource.com/platform/packages/modules/adb/+/refs/tags/android-15.0.0_r1/adb.cpp) 的签名成功分支（444–452）调用的 notifier（daemon/auth.cpp 297–299）没有注册断开回调；显式注册出现在 AUTH3 提示分支（285–294）。当前运行也只观察到首次授权会话的 RSA DC。这里不对未检查的其他平台分支作推断。

后续采用 RSA/TLS 分阶段的新 AVD：每个 CI matrix job 部署一份独立、可销毁的实例，避免任何先前 RSA CK/连接表状态进入无线验收。若复用实例，则必须设计并证明实际事件处理边界，不能仅等待、忽略额外 key，或把它加入期望授权集合。TLS A/B 正反验证期间仍须保持同一个真实 adbd listener，以排除重启和端口故障。

本次 TLS 阶段清理首次恢复原集合失败，外层清理随后再次通过正常 API 移除回填的 RSA A，并观察到最终仅剩控制身份、无线关闭、转发归零。原始阶段清理错误保留在报告中。该最终快照不证明长期无后续 CK 或周期回填；专用 AVD 的销毁提供测试环境隔离终点。

## 本次裁决范围

- M4-A：**PASS**，当前连接的真实 RSA challenge、签名、A 接受、B 明确拒绝仍成立；跨阶段撤销观察边界的问题独立保留。
- M4-B 配对与 A 身份接受：**PASS**。匹配日志、服务端握手及真实 Shell 互相支持。先对控制公钥记录不匹配、再匹配 A，是查找授权集合的正常过程，单独一条不匹配日志不能代表拒绝。
- M4-B 未配对 B 拒绝、撤销后 A 重连：**NOT VERIFIED**，没有执行。
- M4-B 整体：**NOT VERIFIED**；M4-C：**NOT VERIFIED**；本次整体：**CONDITIONAL PASS**。
