# 来源与构建锁定

本次归档日期：2026-10-14。来源版本描述本次使用的内容，不追踪上游默认分支的未来变化。

| 组件 | 固定来源 / 参数 | 散列或版本 |
|---|---|---|
| QEMU 原始源码 | https://download.qemu.org/qemu-10.1.2.tar.xz | SHA256 9d75f331c1a5cb9b6eb8fd9f64f563ec2eab346c822cb97f8b35cd82d3f11479 |
| 基线 EMU 项目 | https://github.com/AICodo/pve-emu-realpc | 当时项目包 pve-qemu-kvm 10.1.2-7；不能用当前 main 代替历史已部署内容 |
| 本次 QEMU 改动 | patches/0001-qemu-10.1.2-z790-baseline.patch | 对原始 tarball 共 98 个文件差异，含此前 EMU 修改；5 个新增外围模型 |
| VMCC 增量 | patches/0002-qemu-per-instance-spd.patch | 外部 2048-byte SPD 文件；运行时 VMCC_SPD_FILE |
| 原机专用 QEMU | 既有部署的二进制 | 4369c050ced5d113a54610a8b8c74c4dc5ae58a13e37e8efd8c9fe7b1514d967 |
| VMCC 构建 QEMU | Ubuntu24.04 amd64，8 jobs；构建选项见工具 | a6aa3075805053d6f74c706e29d73551c2d1b63a7a09fcbad98f29028b3a6283 |
| OVMF | EDK2 edk2-stable202505，commit 6951dfe7d59d144a3a980bd7eda699db2d8554ac | HostBridge a700；X64 RELEASE GCC5、4MiB、Secure Boot false |
| OVMF 执行文件 | OVMF_CODE_RPL_4M.fd | 76d00c08e31571c98ffaaa3a4356e9414adf20b8fb825b287529a9bc26ee15b0 |
| Ubuntu kernel source | linux=6.8.0-147.147 | orig SHA256 26512115972bdf017a4ac826cc7d3e9b0ba397d4f85cd330e4e4ff54c78061c8；Ubuntu diff SHA256 370fa76631a470323e92a0b25dca6012287c4ada448c7f2e4954f45a628e936c |
| Guest 原机 kernel | 真实 6.8.12-generic #6，builder@build | 6b64e38cb94c14233d20436d8385217ad05d4b4b40815bd3310c75855602d7cf；额外 UHID 为原版源码模块 |
| Ubuntu OCI | ghcr.io/catthehacker/ubuntu:act-24.04 | index sha256:62d572b92f9f32d3427b6d220ad1f9dca9c7b6ffad37d295425037dbff78abaf；amd64 manifest sha256:dff4ec57d90046a7283aafc314298380be82bfeccb9ad0f1b36c4ebe74aabe78 |
| MSI BIOS 用户文件 | E7E07IMS.MB0，32MiB；用户自行取得 | bf40f12d7d6cfef81622b87183f5d8e2dee3c22e1d3a59ffb398293fa1975954；不随公开仓库/包分发 |
| NVIDIA | 官方 580.178.04 Open DKMS | Guest 原版驱动；物理 RTX3080 |
| Sunshine | https://github.com/LizardByte/Sunshine/releases/tag/v2026.914.233613 | commit 63d35f702ee9e362e43263742981836ec0710384；Ubuntu24.04 deb SHA256 c38e9c705f650f8705f61702717e99bec34044c5028fcb8f23a08fe041292c21 |
| VMAware 发布版 | https://github.com/NotRequiem/VMAware/releases/tag/v2.8.2 | 原版；全模式/debug 1/84、45%、confirmation=false；THREAD_MISMATCH |
| VMAware 上游 | https://github.com/NotRequiem/VMAware/tree/e1a9786576a58177b2a46a0e780226d218bab349 | 原版固定提交；0/85、0%、confirmation=false |

98 项清单的 before/after 是原始 tarball 与原机最终源码的 SHA；export_sha256 对应公开补丁结果。唯一公开基线数据调整是将固化 SPD SN 归一为 00000001–00000004，随后运行时由实例 SPD 覆盖。当前 VM100 未改成这套新身份，也未替换其执行文件。

原始工作区包含各阶段增量脚本和完整日志。本仓库通过最终差异补丁与锁定模板替代依赖旧路径、旧 VMID、旧密码的阶段性重放；不用顺序运行所有历史脚本。文档公开版去除原机唯一标识、密码、私网地址等实例信息，原始完整报告单独保留。

构建身份由官方 Kbuild 环境变量设置，源码日期取锁定源包 changelog。#5 原始日志保留历史事实；#6 已在原机重启运行。没有覆盖 uname 或修改检测应用。
