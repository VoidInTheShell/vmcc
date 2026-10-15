# 当前改动实现层清单

公开版：省略原机身份与凭据，IP使用文档示例；硬件参数和原始验收结论保留。文件名所指的完整证据保留在原项目工作区，公开选摘见 docs/validation。

## 实现层与源码改动清单

“QEMU 设备模型”“固件”“Guest 内核”和“系统配置”是不同实现层。下面列实际修改位置及边界；检测软件、检测输出和 PVE 宿主 Linux KVM 内核未修改。源码比对记录以 2026-10-14 导出的最终构建树为准。

| 实现层 | 文件或配置 | 改动内容 | 证据与限制 |
|---|---|---|---|
| QEMU 基线与范围 | QEMU 10.1.2 源码；完整差异清单 98 个文件，其中 5 个新增模型 | 包含原 EMU 项目的字符串/默认设备标识变更和本次硬件模型改动；部分 ARM/PPC/S390 等基线文件不进入 x86_64 目标，不能算作本机启用设备。 | 对比宿主原始 qemu-10.1.2.tar.xz 与最终构建树；98 项完整散列清单随 vmcc 保存。 |
| CPU / CPUID | target/i386/cpu.c | 8P+16E、24c24t、关闭 HT；逐核类型、APIC、缓存、拓扑叶 0xB/0x1F、频率枚举与服务器功能位过滤。CPU 参数和 vCPU 亲和性同时生效。 | 逐核拓扑和服务器特征审计通过；SHA/AVX-VNNI、真实性能和 CPUID 时序缺口保留。 |
| QEMU 的 KVM 用户态接口 | target/i386/kvm/kvm.c | 原项目修改 KVM CPUID signature 分支；本机还使用 kvm=off、hypervisor=off 等 CPU 参数。 | 这是 QEMU 用户态源码，不是 PVE 宿主机的 Linux KVM 模块；未改宿主 KVM 内核。 |
| SMBIOS 生成器 | hw/smbios/smbios.c | ROM 扩展容量、SMBIOS 3.5 入口和平台默认标识等；BIOS ROM 容量为 32 MiB。 | CPU-X ROM 栏已有数值；生成器源码与外部 Type 数据分别维护。 |
| SMBIOS 实例数据 | /usr/local/share/pve-emu/smbios-13900k/ 下实际启用的 98 个 Type 文件 | Type0/4/7/16/17/19/20、Type2、55 个 Type8、9 个 Type9、15 个 Type41；主板、机箱、DIMM 身份、插槽、设备位置和引用关系。Type1/3 使用命令行。 | 25 个有效 contained-object 引用、无重复句柄；记录的接口并不代表所有主板电路已经实现。 |
| ACPI 核心 | hw/i386/acpi-build.c；hw/acpi/{core,cpu,pci,aml-build}.c；include/hw/acpi/aml-build.h | 静态 24 个 Processor、MADT APIC 0–7/32–47、128 条 _PRT、SCI/IRQ、电源 _S5、_OSC 权限、OEM 头与资源节点；移除旧 48 槽覆盖和热插拔幽灵对象。 | 10 张常规 ACPI 表校验通过；旧 initramfs DSDT/APIC 覆盖已移除。 |
| ACPI 外部表 / fw_cfg | ssdt.aml、ssdt-ec.aml、hpet.aml、z790-usb-v4.aml、z790-serialio-v5.aml；hw/nvram/fw_cfg*.c、hw/i386/fw_cfg.c | USB _UPC/_PLD 与 Serial IO/ME/SRAM 节点；统一 ALASKA / MS7E07 / AMI 头；Guest fw_cfg 公开节点关闭。 | 外部表通过 -acpitable 加载；并非直接刷入实体 MSI 固件。 |
| PCI / q35 / PCIe 根端口 | hw/pci-host/q35.c；hw/pci/pci.c；hw/i386/{pc_q35,pc}.c；hw/pci-bridge/{ioh3420,pcie_root_port}.c；include/hw/{southbridge/ich9.h,pci/pci_ids.h} | Raptor Lake / Z790 Host/LPC/SMBus 身份、MSI subsystem、10 个根端口、总线位置和链路能力；默认旧桥/显示设备关闭。 | 底层仍为经过修改的 q35；最大/当前 PCIe 速度枚举不能代替电气性能。 |
| NVMe | hw/nvme/{ctrl,subsys}.c；NVMe/NVMe namespace 启动参数 | KIOXIA 型号/固件/PCI/OUI/NQN；SN、EUI64、NGUID、namespace UUID 来自实例配置；当前机复制宿主物理系统盘身份，实际仍用 500 GiB 虚拟盘。 | 没有直通 PVE 系统盘；namespace UUID 等由模型现有属性传入，并未修改 hw/nvme/ns.c。 |
| SMBus / SPD | hw/i2c/{smbus_eeprom,pm_smbus}.c | 512-byte EE1004 页访问和四条 SPD 数据；当前序列为连续四条。 | 按用户要求暂停：decode-dimms 未对齐；本轮只证明四条 EEPROM 散列不变，不把时序写成通过。 |
| I225-V 网卡 | hw/net/{igb,igb_core}.c；hw/net/igb_core.h | 基于 igb 引擎扩展 I225-V 功能，包括身份、NVM、MMIO、队列、收发和中断；原版 igc 驱动绑定。 | 2.5G 链路枚举、ping/DNS/HTTPS 通过；PTP/PHC/PTM/TSN/EEE 未完整实现。 |
| xHCI / USB 2/3 | hw/usb/{hcd-xhci,hcd-xhci-pci,core,bus,desc,dev-hub,dev-storage,dev-uas}.c；对应 .h；include/hw/usb.h | 一个 xHCI、16HS/9SS、速度/双 lane 协议、Hub、端口配对；修复 Stop Endpoint 跳过未执行等时 TD 的 dequeue/cycle 恢复。 | 修复后 39/39 次恢复位置正确；四档 USB 写读一致；无物理 20Gb/s、PD/DP 等效声明。 |
| ALC4080 音频 | 新增 hw/usb/dev-alc4080.c；hw/usb/meson.build | USB UAC2 六流七接口、PCM 数据通路和音量等；接宿主 ALC897 ALSA 48kHz 后端；Guest 使用原版 snd-usb-audio/UCM。 | 26 次录音启停和 3 组双工无 TRB 错误；HID/DSP/IEC61937 和真实 384kHz DAC 未完整实现。 |
| SATA AHCI | hw/ide/{ahci,ich}.c；include/hw/ide/ahci.h | Z790 7a62、AHCI1.3.1、6 端口、6Gb/s 和 SControl Gen1/2 限速；数据通路沿用 QEMU。 | 正式 ata1–6 空端口可见；隔离接盘写读 SHA 一致。 |
| SPI BIOS | 新增 hw/misc/z790-spi.c | 只读 32 MiB SPI NOR 访问与 JEDEC 行为，原版 intel-spi/spi-nor 可读取用户文件。 | 整片读取 SHA 相同；没有执行 MSI BIOS 或实现刷写；BIOS 文件不进入公开仓库。 |
| Serial IO | 新增 hw/misc/z790-serialio.c | I²C0、UART0、GSPI0；LPSS/DesignWare/16550/pxa2xx 所需 PIO 寄存器、FIFO、传输与回环。 | 原版驱动传输一致；NO_IDMA=1，iDMA 与 UART 分数分频未实现。 |
| MEI / HECI | 新增 hw/misc/z790-me.c | HECI 队列与 MSI/INTx、HBM2.0 子集、有限 MKHI 查询；版本从用户 BIOS manifest 读取为 16.1.42.2872。 | 原版 mei_me ENABLED 和标准查询通过；不执行完整 CSME，PTT/AMT/Boot Guard 等未实现。 |
| PCH SRAM / 模型注册 | 新增 hw/misc/z790-sram.c；hw/misc/{Kconfig,meson.build} | 16 KiB + 4 KiB RAM BAR、模型构建和注册；新外围标记 unmigratable。 | 写读并恢复原值通过；不能据此声明实时迁移或含内存快照支持。 |
| OVMF / EDK2 | OvmfPkg/Include/IndustryStandard/Q35MchIch9.h | EDK2 stable202505 将 Host Bridge 识别从 0x29c0 改为 0xa700；X64 RELEASE、4 MiB、Secure Boot 关闭，重编译执行固件。 | 此前已重编译；最近外围轮次未再次修改。MSI E7E07IMS.MB0 仅供标识与 SPI 只读内容。 |
| Ubuntu Guest 内核 | Ubuntu linux=6.8.0-147.147；.config、生成头文件、Module.symvers；真实 release 6.8.12-generic #6；builder@build | 配置关闭 PARAVIRT/XEN/HYPERV 等未使用功能和不适用 uncore 访问，保留容器能力；启用 NVMe、igc、USB Audio、SPI/MTD、LPSS、MEI 等原版驱动；Sunshine 补编原版 UHID 模块。 | 已对实际内核树和同版本 Ubuntu 源码逐文件核对：C/H/S/Rust/DTS/Kconfig/Makefile 额外差异为 0；当前变化在配置和构建产物，不是给检测应用伪返回。 |
| GPU / KDE / 用户态驱动 | PVE hostpci0、VFIO 按 BDF 绑定；原版 NVIDIA 580.178.04 Open DKMS、Xorg/SDDM/UCM | RTX3080 GPU 与 HDMI 音频实体直通；ABI 与 #5 相同的 #6 内核及原有 DKMS，保持 KDE 可用。 | 真实 OpenGL/Vulkan 渲染通过；不再将 GPU 声称为 UHD770，NVIDIA 驱动源码未做身份伪装修改。 |
| PVE 启动与亲和性 | /usr/bin/kvm Python 启动器；100.conf；ubuntu-q35.cfg；pve-emu-pin-vcpus / systemd | 仅 VM100 选专用 QEMU/OVMF，管理 SATA 后端转换 NVMe、e1000 转 I225-V；24 vCPU 与主/I/O 线程分配；其他 VM 沿用原启动器。 | 这里名为 kvm 的文件是用户态启动器；宿主实际 Linux 6.17.2-1-pve 内核未修改。 |
| 网络 / PortalWrt / 账号 | PVE 桥与路由；Guest 网络/账号配置；PortalWrt UCI、dnsmasq、firewall | WAN .232 → .233，LAN10.20.1.0/24、Ubuntu .2、WAN 禁 DHCP、上游静态路由；America/New_York；user 免密 sudo。 | 网络已做实际包验证；此层为系统配置，并不属于 QEMU 源码补丁。 |
| Sunshine / 开机自启 | 官方 Sunshine deb；Xorg headless 配置；user systemd drop-in；sunshine-launch / sunshine-xauthority；udev/input/UHID | 未登录 KDE 时自动启动，1080p60 X11 捕获与 NVENC 探测；实际重启 enabled/active/running，NRestarts=0。 | 未修改 Sunshine 源码；真实 Moonlight 端到端串流、音频/手柄尚未验收。 |
| vmcc 复用增量 | patches/0002-qemu-per-instance-spd.patch；tools/vmcc.py、kvm-wrapper.py 等 | 按实例外部加载 2048-byte SPD，生成独立系统/主板/机箱/磁盘/MAC 身份，保持四条 DIMM 连号；公开版移除原机身份与凭据。 | 这是新复用包的增量，不回写当前 VM100；复制实例的整机验收必须单独执行。 |

公开复用项目：[VoidInTheShell/vmcc](https://github.com/VoidInTheShell/vmcc)。当前实例完整身份仅保留在本地/本报告；公开仓库使用每实例生成机制。

2026-10-15 增量：`tools/batch.py` 串联离线准备、独立制盘、PVE 分配与注册；`collect-guest.py` / `verify-instance.py` 直接读取并比较实际数据。`pci-rom-resource` 只恢复已分配的禁用 ROM BAR；`build-kernel.sh` 使用官方 Kbuild 构建元数据参数。用户要求保留 Sunshine HID 与 hypervisor bit=0；不改检测应用。资料保留与清理映射见 [工程资料清单](ENGINEERING_MATERIALS.md)。
