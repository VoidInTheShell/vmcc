# 工程资料与镜像内容

Git 保存可复用的最终实现，不依赖按时间顺序执行历史调参脚本。

| 资料 | 保存位置 / 处理 |
|---|---|
| QEMU 最终 98 文件差异、新增外围模型 | `patches/0001-qemu-10.1.2-z790-baseline.patch` |
| 每实例 SPD 加载增量 | `patches/0002-qemu-per-instance-spd.patch` |
| OVMF、内核、源码版本与构建参数 | `tools/build-{qemu,ovmf,kernel}.sh`、`profiles/`、`docs/PROVENANCE.md` |
| SMBIOS / ACPI / PCI 拓扑 | `templates/platform/`、`templates/qemu-args.json` |
| 内核构建身份与桌面启动 | 内核构建脚本使用 Kbuild 支持的 `builder@build`、版本 6、源包日期；离线准备写入 `99-desktop.cfg` |
| GPU ROM 资源修复 | `templates/guest/pci-rom-resource.py` 与 systemd 单元；只写内核已分配地址，保持 ROM decode 关闭 |
| CPU 原始探针 | `tools/probes/`；只读取 CPUID、MSR 与时间，不修改检测软件 |
| 干净实例工厂 | `capture-source.py`、`prepare-guest.py`、`build-boot-disk.py`、`batch.py` |
| 实际验收采集与比较 | `collect-guest.py`、`verify-instance.py`；经 SSH stdin 执行，结果写到管理端 |
| Sunshine / 网络运行配置 | `templates/sunshine/`、`install-sunshine.py`、离线准备工具；保留官方虚拟 HID |
| 临时安装包、旧内核、对象文件、重复 rootfs / 整盘 | 不进入 Git；成功导入后清理本批次的 rootfs 与 sparse image 工作副本 |
| 历史版本调参脚本、重复验证程序、临时跟踪日志 | 最终补丁和统一验收器替代；不在生成的 Guest 中保留 |
| BIOS、PortalWrt / Ubuntu 镜像 | 用户自行提供，不随公开库分发 |
| 原机 SN / UUID / MAC、密码、SSH 私钥、Sunshine 配对与证书 | 不进入公开 Git；新实例自动生成各自标识和状态 |
| 原始验收记录 | 管理端私有工作目录；公开报告仅摘录去除实例身份的结果 |

新实例不复制 `/root`、`/home`、`/var/log`、CI runner 环境、旧 `emu-native` 内核、检测工具副本、工程备份或项目身份清单。只保留驱动、固件、软件包数据库、桌面、网络和 Sunshine 所需的功能文件。运行脚本采用实际用途命名。

v0.1.0 的在线 `guest-finalize.py` 已由离线准备替代：不再往 Guest 写入项目标记或克隆备份。管理端的计划、分配回执和验收结果用于审计与重试，不嵌入新虚机。

这些处理不能把虚拟硬件变成实体硬件。CPUID 执行开销、宿主缺少的指令与 cpufreq 能力、未完成的外围功能仍按报告如实记录；不通过修改检测应用或伪造输出消除差异。
