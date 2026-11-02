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
实际运行结果将在后续检查点增量加入。

| 项目 | 当前裁决 |
| --- | --- |
| M4-A RSA AUTH | NOT VERIFIED |
| M4-B 无线 TLS 身份强制认证与撤销 | NOT VERIFIED |
| M4-C 实体设备 | NOT VERIFIED（无设备授权，不执行） |
| M4 整体 | NOT VERIFIED（执行中） |

固定候选仍为 `0.1.0-dev.59105290820b`，对应源码
`59105290820bcbfd4e0336a2e7713006a461527f`。生产密码学未修改；R3-K01 保持开放。
