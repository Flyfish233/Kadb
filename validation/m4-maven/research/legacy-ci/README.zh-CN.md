# 历史 M2 Darwin 失败的限定调查

## 已定位的失败阶段

历史 [M2 run 41439551154](https://github.com/Flyfish233/Kadb/actions/runs/41439551154)，提交 `794b69fecdac0d3fd7d7a54d11f944fa944a65f2`，只有 `iosSimulatorArm64` job `125257677041` 的独立配对步骤失败。实际异常是：

```text
TimeoutExpired: Command '['xcrun', 'simctl', 'list', 'devices', 'booted', '--json']' timed out after 10 seconds
```

这是运行独立 Native 配对程序前的 Simulator 清单预检。`failure-pairing-report.json` 没有 `native_command` 或 `native_exit_code`，下载到的原始 artifact 也没有 `native-consumer.log`。历史 [run_interop.py](https://github.com/Flyfish233/Kadb/blob/794b69fecdac0d3fd7d7a54d11f944fa944a65f2/validation/pairing-peer/run_interop.py) 的操作顺序与此完全对应。Java peer 已启动等待连接，随后由 `finally` 清理终止，退出码 143；该退出码不能解释为 SPAKE2 协议拒绝。

因此，可以高置信度判定**该步骤在启动 Native 配对消费者前，被 CoreSimulator 管理命令的 10 秒期限中断**。这次步骤未取得配对通过证据，也未执行出一例配对协议失败。没有重跑 M2。

## 与成功基线的比较

对照 [成功 M2 run 41418593040](https://github.com/Flyfish233/Kadb/actions/runs/41418593040)，提交 `0d448840863bbf6735eb879ebc7532c321cfca17`。其相同目标执行了 Native 正确码/错误码两项检查，独立 peer 确认两次会话成功完成验收。

[assessment.json](assessment.json) 保存了 Git 对象级比较：Kadb 与 mDNS 源码树、Native pairing consumer、Native 模块构建脚本、整个独立 peer 目录、M2 Darwin 工具、M2 Darwin workflow、版本目录及 settings 均相同。Java reference artifacts 和已编译 peer class 的 SHA256 也相同。macOS、Xcode、Java 和 SDK 版本没有变化。两次 Native 可执行文件 SHA256 不同，故没有宣称二进制逐字节相同。

两份 boot 日志都出现 `Data Migration Failed`，之后都显示该 Simulator 为 Booted；成功基线后来确实完成了配对。不能仅据这条迁移日志认定本次超时根因。保留日志没有证明 CoreSimulator 为何未在 10 秒内回应，运行时调度或服务状态的进一步成因仍未确定。

## 原始计数中的独立问题

失败 run 的汇总曾声称执行 210 项测试。逐条核对其 `test-summary.json` 后发现：

| XML 来源 | 可确认的 executed |
| --- | ---: |
| 当前 `kadb/build/test-results/` 与 `kadb-mdns/build/test-results/` | 70 |
| 已提交在 `validation/m2-maven/runs/` 的历史 XML | 140 |
| 原始汇总输出 | 210 |

当前 70 项的 failed 为 0；这与成功基线的实际 70 项一致。原始汇总器递归扫描仓库，把存档证据也计入了本次执行。原始压缩报告在此完整保留，但本调查不把 210 当成新的实际执行数。此计数问题应在后续 M2 工具维护中限制输入到明确构建输出目录；本轮没有修改或重跑 M2。

## 证据与裁决边界

失败 artifact `13140246180` 的实际 ZIP SHA256 与 GitHub 声明的 `f90dac8093c4c774944dd2d3d6b9dc53beea6e74b12962f8d7cb120529699535` 一致。目录保留失败配对报告、Simulator boot 日志、压缩测试及阶段报告、完整压缩 job 日志、下载身份和源码比较。原始 job 日志经私钥、GitHub token、AWS access-key 扫描，未发现需新增脱敏的匹配；GitHub 原有 `***` 掩码继续保留。精确散列见 [job-log-custody.json](job-log-custody.json)。

这项历史失败仍然是失败记录。其实际失败阶段和相同源码对照，不支持将它认定为 M3/M4 新引入的生产代码回归，也不能替代 M4 的真实 Android 身份认证验收。保留现有 M2 成功基线，同时将 Simulator 预检超时与历史 XML 重复计数列为有限的后续工具维护项。
