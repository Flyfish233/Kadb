# 固定 SPAKE2 Maven 候选

本目录保存 M1 使用的**实际 Maven 二进制候选**，使恢复工作不依赖会过期的
GitHub Actions 下载地址。它是工作分支中的验证输入，没有进行 Maven 或 Release
正式发布，也没有重新编译、修改或重新签名 SPAKE2。

| 身份 | 固定值 |
| --- | --- |
| 源码仓库 | `https://github.com/Flyfish233/spake2` |
| 源码提交 | `59105290820bcbfd4e0336a2e7713006a461527f` |
| Maven 版本 | `0.1.0-dev.59105290820b` |
| 原 CI | [40388080222](https://github.com/Flyfish233/spake2/actions/runs/40388080222) |
| 原 GitHub artifact | `12682137388`，`spake2-maven-candidate` |
| 原 ZIP SHA-256 | `29fe208f315ea08c9643d4388df8d832b984b04270fd39e55d00328ed4746ac3` |
| 本目录 tar.xz SHA-256 | `3ea50362515509300850ac2bdb487bc070379d3e40e346250eb228ed2ad47d33` |
| 本目录 tar.xz 大小 | 1,766,332 bytes |

新的传输压缩包使用 USTAR + XZ，将 Maven 目录中的 219 个文件按路径排序，
设定 `mtime=uid=gid=0`、`mode=0644`、空 `uname/gname`，不接受符号链接。
解压根目录为 `maven/`。压缩格式及外层摘要改变，**219 个 Maven 文件的字节没有改变**；
它们共 11,012,660 bytes，每个文件的大小和 SHA-256 均列于
[`manifest.json`](manifest.json)，并已从压缩包逐项读回核对。

候选包含上游完整的 33 个发布坐标，包括 RFC、Legacy、Primitives 及其平台变体；
Kadb 的生产依赖只使用 Legacy，Primitives 由同版本 metadata 传递解析。
保留完整候选不表示 Kadb 新增 RFC 生产依赖。

## 离线恢复入口

```sh
python3 scripts/prepare_spake2_candidate.py
```

成功时 stdout 只输出已核验 Maven 仓库的绝对路径，默认位置为
`build/spake2-candidate/maven`。通过 `--output /path/to/parent` 可改为
`/path/to/parent/maven`。脚本无需网络及上游 checkout，先核对固定来源身份、
压缩包摘要、全部 219 条路径及每个文件的摘要，再以原子目录移动完成恢复。
已有目标只有完全一致才会复用；差异、缺文件、额外文件和符号链接均拒绝覆盖。

有界恢复测试：

```sh
python3 -m unittest discover -s validation/m1-maven/tests -p 'test_prepare_candidate.py' -v
```

## 来源及完整源码

本次从经过身份认证的 GitHub connector 重新下载了原 artifact；下载文件 SHA-256
与单独取得的 GitHub artifact API digest 一致。完整发布结构检查通过。
三个 umbrella 的 `-source-distribution.zip` 各有 482 个普通文件，与固定源码
提交的 Git blob 内容逐字节一致；上游构建配置只排除了该提交中的 `.gitignore`。
三份完整源码 ZIP 的 SHA-256 均为
`4a2f3ff76d52b58aae758d83b0600499b5c02d9be8300d9f9fff3c1920519a0c`。

本次复查记录及可执行的 Git 对照脚本位于
[`../m1-maven/provenance/`](../m1-maven/provenance/)。原 GitHub artifact 的到期日为
`2026-11-09T19:39:21Z`；本目录保存的是恢复所需实物，不需要再次访问该临时下载地址。

上游运行时代码保持 **AGPL-3.0-only**，没有 linking exception；完整源码、
sources/documentation companions 及第三方许可说明原样保留在候选中。
Kadb 自有代码的 Apache-2.0 许可没有因此被改写。整体交付要求见
`docs/experiment/LICENSES.md` 与对应源码交付文档。

这些检查证明候选身份、发布结构和对应源码一致性，不声称本次完成新的密码学
审计、全平台二进制可复现构建、正式签名证明、M2 或 M3 验证。
