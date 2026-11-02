# M1：已验证交付入口

最终裁决：**M1 PASS**。M2 / M3 未执行。

- 中文交付记录：[M1-DELIVERY.zh-CN.md](../../docs/experiment/M1-DELIVERY.zh-CN.md)
- 最终代码提交：`af6aa42ebb2bd880753600ed43fbe6e49d6f197e`
- 最终成功 CI：[41400073710](https://github.com/Flyfish233/Kadb/actions/runs/41400073710)
- 机器可读裁决：`verdict.json`
- 固定候选实物、逐文件摘要与离线恢复：`../maven-candidate/`、`../../scripts/prepare_spake2_candidate.py`
- 本轮实际来源与对应源码：`provenance/resumed-*`
- 普通生产入口强制来源门禁与真实 165 项测试：`runtime/resumed/scheduled-default-*`
- 真实 Gradle 解析正负测试：`runtime/gradle-gate-tests/`
- 远端逐 run/job/step 与上传产物：`runtime/ci/`
- 协议不变与迁移前历史 CI 归因：`review/`

恢复时保留了历史记录。`baseline.json`、`runtime/candidate-lock-verification.json` 及 provenance
中没有 `resumed-` 前缀的文件描述各自当时状态；其中的 NOT VERIFIED 不应被覆盖或误解为本轮最终裁决。
最终裁决以上方 delivery、verdict 与最终代码的真实 CI 为准。

最后的证据和文档提交不修改生产构建代码，不需要重复已完成的源码恢复或密码学审计。
