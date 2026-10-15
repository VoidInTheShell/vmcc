# 构建与部署

## 前置与范围

基线是 Intel VMX/KVM、PVE QEMU 10.1.2 系列、Ubuntu 24.04 amd64。原机宿主 Linux 为 6.17.2-1-pve，Guest 为真实构建的 6.8.12-generic #5。项目没有修改宿主 KVM 内核。现有专用 /usr/bin/kvm 启动器由 VMCC 的 fallback 链保留；部署新实例不替换原机 QEMU。

每台同时运行的实例需要可用的 RTX3080 及其音频功能、24 个可分配宿主 CPU 和互不重叠的 I/O CPU、64 GiB RAM、500 GiB 后端。GPU 先完成 IOMMU/VFIO 绑定与独占检查。项目不清除物理盘，不替用户重新划分 NVMe 存储池，也不自动抢占已分配设备。

先准备好 PVE 存储、隔离 LAN bridge、用户自行提供的 PortalWrt 镜像、授权使用的 MSI BIOS，以及不含个人会话的 Ubuntu 模板。一个 LAN 可以共用原路由器并为新 Ubuntu 分配新地址；若复制整对 Ubuntu/PortalWrt，则需要另一块 WAN NIC、不同 WAN 地址和无重叠 LAN/上游路由。

## 构建运行包

在独立 Ubuntu 24.04 构建环境执行，不要把编译依赖装进正在使用的 PVE：

```bash
sudo apt-get update
sudo apt-get install -y build-essential ninja-build pkg-config python3-venv \
  libglib2.0-dev libpixman-1-dev libgcrypt20-dev zlib1g-dev libaio-dev \
  liburing-dev libasound2-dev libgnutls28-dev libjpeg-dev libpng-dev \
  libslirp-dev git curl patch nasm uuid-dev acpica-tools
tools/build-qemu.sh
tools/build-ovmf.sh
```

QEMU tarball 由 SHA256 锁定，所有 98 项基线源码差异在 0001 补丁中；0002 是新复用版的外部 SPD 增量。构建脚本拒绝复用已有源目录，防止重复打补丁。OVMF 使用 edk2-stable202505，Host Bridge ID 改为 a700；实际执行的依旧是 OVMF。Release 运行包已含对应 QEMU、OVMF、libjpeg 及许可证。

Guest 内核可复用清理后的原模板，或在 Ubuntu noble 开启对应 deb-src 后运行：

```bash
sudo apt-get install -y build-essential bc bison flex libssl-dev libelf-dev \
  cpio kmod rsync dwarves zstd
tools/build-kernel.sh
```

生成的 boot/lib/usr 是 Guest 的 staging 内容；复制到新 Guest 后运行 depmod、update-initramfs、update-grub，再用同一源码生成的 headers/Module.symvers 重建 NVIDIA DKMS。UHID 在复用构建中直接启用为模块。内核不是 bit-for-bit 可复现承诺：编译时间、工具链和构建环境会影响散列。本轮未重新跑一次完整内核构建；原机内核和模块的真实运行验收见报告。

## 生成并注册新实例

若不克隆现有磁盘，可以从锁定的 `ghcr.io/catthehacker/ubuntu:act-24.04` OCI manifest（见 PROVENANCE）用 skopeo/umoci 解包准备 rootfs，安装 systemd-sysv、GRUB EFI、initramfs-tools、openssh-server、netplan.io、sudo、KDE/SDDM/Xorg 等，再把构建的内核 staging 合入。已有 rootfs 需先审阅账号、会话和 root 私有数据。`sudo tools/build-boot-disk.sh PREPARED_ROOTFS NEW_DISK.raw` 创建新的 500 GiB 稀疏普通文件并安装 EFI/GRUB；新建 GPT/分区/文件系统时各自生成独立身份，因此不需要对克隆 UUID 做原地改写。该参数化脚本保留自原始实际制盘流程，本轮只做语法检查，未额外创建 500 GiB 磁盘。输出只能是不存在的普通文件，不能指定块设备。

按 README 的 init/render 命令生成身份和 bundle。磁盘参数指向已导入、没有被其他 VM 引用的独立卷。推荐导入离线清理后的模板副本；不要把源机磁盘或 efidisk 同时挂给另一台机器。默认音频后端为 none；需要宿主音频时显式给 render 添加 `--audio-backend plughw:0,0` 并确认该 PCM 可用。

把源码目录、bundle、解压后的 runtime 和用户 BIOS 放到目标 PVE 后，先只读检查：

```bash
sudo python3 tools/install-host.py --bundle /path/to/bundle --runtime /path/to/runtime
```

它检查 VMID、磁盘引用、GPU/VFIO、CPU、bridge、BIOS SHA、模型与 SPD 扩展；不会检查远端 IP 是否占用。检查通过后才执行注册：

```bash
sudo python3 tools/install-host.py --bundle /path/to/bundle --runtime /path/to/runtime --apply
sudo sh /opt/vmcc/instances/200/create-vm.sh
```

安装器保留 `/usr/bin/kvm.vmcc-original`，只分流登记 VMID，未登记 VMID 沿用原启动器；共享 runtime 已存在且不同则拒绝覆盖。create-vm.sh 创建一块新的 EFI variables 盘，不启动 VM。相同 PVE 版本下实际 `qm showcmd 200 --pretty` 仍应复核；安装器/完整新 VM 创建流程尚未在另一台 PVE 做端到端验证。

## 克隆清理与首次启动

`identity.json` 已生成 GPT/PARTUUID/ext4 UUID 的规划值，当前工具不会自动改磁盘。磁盘 GUID、分区 UUID、ext4/FAT ID 如需全部独立，应在离线副本上修改，并同步 fstab、GRUB、initramfs 中的引用；必须冷启动验收。没有经验证的通用文件系统改号器，因此这一步保留明确人工门槛，不能报告为已自动完成。

新 VM 首次以隔离网络和 serial console 启动。将本项目及其 identity.json 放入 Guest：

```bash
sudo python3 tools/guest-finalize.py --identity /path/to/identity.json
sudo python3 tools/guest-finalize.py --identity /path/to/identity.json --reset-clone --apply
sudo passwd user
```

工具用实际 DMI UUID 检查目标，重建 machine-id、SSH host keys、继承租约/NM/Sunshine 状态，配置静态 netplan、时区、user 和免密 sudo。旧配置放在 root 私有备份；应由操作者审阅后删除不需保留的旧克隆凭据。网络在重启后应用；从 serial console 操作，避免通过旧地址中断工作。

Sunshine 使用官方 2026.914.233613 Ubuntu24.04 deb（散列见来源）。KDE/SDDM/Xorg、原版 NVIDIA、PipeWire 和 UHID 先可用，再执行 `tools/install-sunshine.py --deb /path/to/deb --name workstation-001 --apply`。它启用 linger、自启、X11/NVENC 和独立 Xauthority helper；需要在新实例设置 Web 凭据并重新 PIN 配对，不复制旧证书。新泛化安装器尚未做另一台 KDE 的重启验收；原机的自启已真实重启验证。

## PortalWrt 与上游

PortalWrt：4 核/4 GiB、与自编译镜像相同容量、OVMF/q35、物理 WAN NIC 独占直通、一个连接隔离 LAN 的虚拟 NIC。`tools/render-portal.py` 生成配置脚本，执行前审阅网卡名称、WAN 地址和上游。WAN 静态，不启 DHCP/DHCPv6 客户端；dnsmasq 限 LAN 并显式排除 WAN；fw4 保持 ACCEPT/NAT 并对 WAN DHCP 输入、输出和转发 DROP。脚本替换新路由器 network/dhcp/firewall，先保存旧配置，不重启网络；通过 serial console 再执行 reload。

上游手动添加且持久化 `LAN_SUBNET via PORTAL_WAN_IP`，验证实际到新 Ubuntu 的 request/reply；单纯 route 表或端口监听不算网络验收。原机已验证的配置是来源记录，不是新实例可直接复用的 IP。

## 回退与验收

只注册未启动时：禁用对应 `vmcc-affinity@VMID` 服务，移走该 registry 文件和实例目录；所有 VMCC 实例均停机且不再登记后，才可恢复 `/usr/bin/kvm.vmcc-original`。不要删除其他实例的共享 runtime 或直接覆盖 PVE 的包文件。新建 VM/卷按实际归属单独回收，源机卷不涉及。正式启动后应先备份配置并同步回退 QEMU/ACPI/SMBIOS/Guest 内核，避免半套模型。

验收至少覆盖：24c24t/8P16E/SMT off、实例身份与四条连号、DMI/ACPI/PCI 引用、NVMe UUID/NQN、原版驱动、GPU/KDE 实际渲染、Portal 实包路由与 WAN DHCP 抓包、Sunshine 未登录重启自启及真实 Moonlight、原版 VMAware 和独立 CPUID 时序。不得修改检测软件或把原机结果标成克隆机通过。
