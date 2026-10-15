# vmcc

将 PVE 上的一套 13900K / Z790 虚机配置整理为可审阅、可构建、可生成独立实例身份的项目。当前配置为 **8P + 16E、24 核 24 线程、HT 关闭、64 GiB DDR4、500 GiB NVMe、实体 RTX3080 直通**。

项目包含 QEMU 10.1.2 完整补丁、OVMF 和 Guest 内核构建脚本、SMBIOS/ACPI 模板、每实例身份生成器、PVE 启动器、离线账号/网络/Sunshine 配置、批量工厂和实际数据验收器。检测应用及其输出未修改。

**已验证：**QEMU 从原始源码完整构建；100 组身份查重；实际生成两台独立 500 GiB 的 KDE/RTX3080/NVMe 实例，硬件与干净状态对比及重启均 35/35；最终工厂实例无需手工修补。相同未修改 VMAware 固定版本实测 0/85。限制和测试口径见 [验证记录](docs/VALIDATION.md)。

## 批量生成

在 PVE 上只读提取停止的源 VM 文件集，编辑 `examples/batch.json` 后：

```bash
./vmcc batch plan --spec /private/batch.json --out instances/batch-001
sudo ./vmcc batch apply --plan instances/batch-001 \
  --password-file /private/account-password --apply --start
```

工厂创建独立的 500 GiB 磁盘与文件系统，重建账号、网络、SSH 和 Sunshine 状态；不复制工程资料、用户会话或 CI runner 环境。密码文件须为 0600，不进入仓库。GPU、存储与网络前置、只读预检和实机对比验收见 [部署说明](docs/DEPLOYMENT.md)。

## 单实例配置生成

```bash
git clone https://github.com/VoidInTheShell/vmcc.git
cd vmcc
./vmcc init --name workstation-001 --vmid 200 \
  --address 10.20.1.2/24 --gateway 10.20.1.1 \
  --mac-prefix D8:FC:93 --out instances/workstation-001

./vmcc render --identity instances/workstation-001/identity.json \
  --out instances/workstation-001/bundle \
  --disk emu-lvm:vm-200-disk-1 --efi-storage emu-lvm \
  --bridge vmbr2 --gpu 0000:82:00 \
  --bios /opt/firmware/E7E07IMS.MB0 \
  --vcpu-cpus 0-23 --io-cpus 28-31

./vmcc audit instances/*/identity.json
python3 -m unittest discover -s tests -v
```

本节 init/render/audit 命令只生成本地文件，不连接 PVE、不创建或启动虚机。示例的磁盘、GPU、CPU 和网段必须按目标主机选择。省略 `--mac-prefix` 时使用随机本地管理单播 MAC；指定 OUI 时仍需查重和确认网内无冲突。身份只生成一次并持久保存，重启不随机变化。

## 文档与产物

| 内容 | 位置 |
|---|---|
| 本次改动落在什么层、哪些源码文件 | [分层清单](docs/CHANGE_LAYERS.md) |
| 当前配置参数与验收边界 | [独立参数表](docs/CURRENT_PARAMETERS.md) |
| 主机前置、构建、离线准备、批量创建和验收 | [部署说明](docs/DEPLOYMENT.md) |
| SN / UUID / MAC 及克隆状态盘点 | [实例身份清单](docs/IDENTITIES.md) |
| 原机验收、复用包测试及未验证项 | [验证记录](docs/VALIDATION.md) |
| 工程资料保留与清理规则 | [资料清单](docs/ENGINEERING_MATERIALS.md) |
| 上游版本、散列、许可证 | [来源](docs/PROVENANCE.md)、[NOTICE](NOTICE.md) |
| 可下载源码包和 QEMU/OVMF 运行包 | [Releases](https://github.com/VoidInTheShell/vmcc/releases) |

源码仓库不包含用户 BIOS、PortalWrt 镜像、Ubuntu 整盘、密码、SSH 密钥、Sunshine 证书或配对状态。运行包提供 QEMU/OVMF；Guest 内核提供锁定配置和构建脚本，不包含预配置账号的整盘镜像。

## 能力边界

底层仍为修改后的 q35 和设备模型；品牌/速度枚举不代表实体芯片电气行为或 13900K 执行性能。CPUID 开销、Guest 缺少 cpufreq 后端、宿主缺少的 SHA/AVX-VNNI、CPU-X 部分传感器读数、暂停的 SPD/decode-dimms 对齐、完整 CSME/PTT/AMT/Boot Guard、部分网卡/音频/Serial IO 功能仍有缺口。新外围模型不支持完整迁移状态。Moonlight 端到端串流未验收。

使用 GPL-2.0-or-later；上游文件保留各自许可证和作者声明，见 [NOTICE](NOTICE.md)。
