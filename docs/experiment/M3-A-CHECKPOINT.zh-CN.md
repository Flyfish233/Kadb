# M3-A 执行检查点

真实 CI：[41439551227](https://github.com/Flyfish233/Kadb/actions/runs/41439551227)。实际执行代码 `794b69fecdac0d3fd7d7a54d11f944fa944a65f2`。

**M3-A：CONDITIONAL PASS。** 固定 Maven 候选编译出的外部 Linux Native consumer 对 Android API 35 的真实 adbd 完成十五项检查；三次真实连接、两次重连；全部退出码及清理断言通过。

对端 fingerprint：`google/sdk_gphone64_x86_64/emu64xa:15/AE3A.240806.043/12960925:userdebug/dev-keys`。adbd 1.0.41；实际可执行文件 `/apex/com.android.adbd/bin/adbd`，SHA-256 `008accf96d7cf61d63af6c30d9ec60cdb0ae88bed7b09f49967e257ec5bf5893`。

本次直接沿用既有 5555 listener，不调用 `adb tcpip`，解决了历史 40331404006 在切换 5556 后失去控制 transport 的问题。M2 的默认网络时序问题单独使用既有 readiness 门禁。

实际观察 `ro.adb.secure=0`；三次连接均为普通 CNXN，没有 AUTH 或 STLS。测试没有关闭认证，也不把未执行的认证拒绝探针算作通过。AUTH 和 STLS 仍为 NOT VERIFIED。此检查点不是 SPAKE2 配对成功证明。

临时公钥列表恢复、owner/group/mode 与原 UID/监听属性恢复、测试 APK 和文件删除、临时私钥删除均有断言与原始命令记录。独立 ADB server 5038 和专用 AVD 随 CI 清理。Native consumer 实际耗时 3037ms；Sync payload 1,048,589 bytes。

固定 SPAKE2 `0.1.0-dev.59105290820b` 与源码 `59105290820bcbfd4e0336a2e7713006a461527f` 未变化。完整对应源码 artifact `13137449967` 与二进制 artifact `13139600657` 在同次 CI 中关联，原始 ZIP digest、日志和关键报告保存在 `validation/m3-maven/runs/41439551227/`。

下一阶段执行真实 Android 系统 SPAKE2 配对服务；受控 peer 异常注入单独记录。物理设备 M3-C 保持 NOT VERIFIED。R3-K01 双向 GCM nonce 继承风险不在本检查点改动。
