# M1 来源证据索引

`resumed-*` 文件记录本次继续执行中实际完成的验证。没有此前缀的候选来源、publication
和源码比较文件是从旧工作树恢复的历史证据；它们保留供追溯，不代替本轮重新执行。

本轮主要入口：

- `resumed-candidate-origin.json`：重新下载原 ZIP，核对固定 artifact/run/source 身份，并与保存的 219 个 Maven 文件逐字节比较。
- `resumed-publication-check.json`：固定上游检查器重新验证 33 个发布单元。
- `resumed-source-archive-vs-git.json`：三份完整源码包分别对照不可变 Git 提交，482 个文件逐字节一致。
- `resumed-scheduled-resolution-source-check.json`：独立核验普通 Gradle 构建的实际组件、来源、变体和缓存字节。
- `resumed-full-source-verification.json`：最终代码提交的两次完整离线源码收集、同哈希比较和独立验证。
- `resumed-source-bundle-manifest.json`：完整文件清单、固定依赖材料及实际 AAR / Native 测试 ELF 关联。
- `resumed-aar-source-gate-regression.json`：本次发现的 AAR 收集入口失败及修复后的实际验证。

原始 ZIP、候选传输包与源码收集 tar.gz 是不同层次的文件，各自的摘要不得混用。
源码收集包的可复现比较固定了提交、解析报告、依赖材料和二进制输入；没有宣称跨编译器或
跨平台构建出的二进制逐字节可复现，也没有将 Maven 解析视为设备配对。

源码收集大包由 `.github/workflows/m1-maven.yml` 上传为 GitHub Actions artifact。
Git 中保留完整候选实物、收集实现、固定输入、摘要及清单，因此恢复不依赖本机临时路径。
