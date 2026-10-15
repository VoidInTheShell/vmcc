# vmcc

将 PVE 上的一套 13900K / Z790 虚机配置整理为可审阅、可构建、可生成独立实例身份的项目。当前配置为 **8P + 16E、24 核 24 线程、HT 关闭、64 GiB DDR4、500 GiB NVMe、实体 RTX3080 直通**。

项目包含 QEMU 10.1.2 完整补丁、OVMF 和 Guest 内核构建脚本、SMBIOS/ACPI 模板、每实例身份生成器、PVE 启动器、账号/网络/Sunshine 配置工具以及验收记录。检测应用及其输出未修改。

**已验证：**原始 QEMU 源码应用补丁并完整编译；100 组实例标识查重；两个无磁盘隔离实例实际启动并读取各自 DMI 和四条连续 SPD SN；错误 SPD 输入拒绝启动。新实例的完整 KDE/GPU/PortalWrt 克隆部署尚未执行，不能把原机验收自动继承给新实例。

## 快速开始

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

这些命令只生成本地文件，不连接 PVE、不创建或启动虚机。示例的磁盘、GPU、CPU 和网段必须按目标主机选择。省略 `--mac-prefix` 时使用随机本地管理单播 MAC；指定 OUI 时仍需查重和确认网内无冲突。身份只生成一次并持久保存，重启不随机变化。

## 文档与产物

| 内容 | 位置 |
|---|---|
| 本次改动落在什么层、哪些源码文件 | [分层清单](docs/CHANGE_LAYERS.md) |
| 当前配置的 108 项参数与验收边界 | [独立参数表](docs/CURRENT_PARAMETERS.md) |
| 主机前置、构建、注册、克隆和回退 | [部署说明](docs/DEPLOYMENT.md) |
| SN / UUID / MAC 及克隆状态盘点 | [实例身份清单](docs/IDENTITIES.md) |
| 原机验收、复用包测试及未验证项 | [验证记录](docs/VALIDATION.md) |
| 上游版本、散列、许可证 | [来源](docs/PROVENANCE.md)、[NOTICE](NOTICE.md) |
| 可下载源码包和 QEMU/OVMF 运行包 | [Releases](https://github.com/VoidInTheShell/vmcc/releases) |

源码仓库不包含用户 BIOS、PortalWrt 镜像、Ubuntu 整盘、密码、SSH 密钥、Sunshine 证书或配对状态。运行包提供 QEMU/OVMF；Guest 内核提供锁定配置和构建脚本，不包含预配置账号的整盘镜像。

## 能力边界

底层仍为修改后的 q35 和设备模型；品牌/速度枚举不代表实体芯片电气行为或 13900K 执行性能。CPUID 开销、宿主缺少的 SHA/AVX-VNNI、CPU-X 部分传感器读数、暂停的 SPD/decode-dimms 对齐、完整 CSME/PTT/AMT/Boot Guard、部分网卡/音频/Serial IO 功能仍有缺口。新外围模型不支持完整迁移状态。Moonlight 端到端串流未验收。

使用 GPL-2.0-or-later；上游文件保留各自许可证和作者声明，见 [NOTICE](NOTICE.md)。
