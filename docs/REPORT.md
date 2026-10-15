# PVE EMU 当前交付与验收

公开版：省略原机身份与凭据，IP使用文档示例；硬件参数和原始验收结论保留。文件名所指的完整证据保留在原项目工作区，公开选摘见 docs/validation。

Sunshine更新：2026-10-14 20:33 EDT。官方稳定版2026.914.233613已安装，正式重启后无需登录KDE自动启动，服务enabled/active/running且NRestarts=0。当前boot ID `[INSTANCE_UUID]`；以下外围完整验收记录仍为前一次启动。管理地址 **https://10.20.1.2:47990**，user / [凭据省略]；Moonlight添加10.20.1.2后需PIN配对。RTX3080的H.264/HEVC NVENC探测通过；未连接真实Moonlight客户端。详见Sunshine配置与原始验收〔原始工作区：sunshine-20261014/README.md〕。

2026-10-14 14:14 EDT更新。正式冷启动boot ID `[INSTANCE_UUID]`，VM100/101均运行。Ubuntu为i9-13900K 8P+16E、24c24t、HT关闭，64GiB/500GiB虚拟NVMe，实体RTX3080直通；网络和user免密sudo继续有效。新增设备已部署并实际测试，完整CSME、电气特性和时序等缺口保留。

## 完整改动与独立参数表

现有参数表已更新〔原始工作区：CURRENT_REALPC_SUMMARY.md〕，包含新QEMU/内核散列、I225-V、ALC4080、USB数量与速度、SATA、SPI BIOS、Serial IO、MEI、PCH SRAM、SMBIOS/ACPI参数、功能证据和未完成项。旧版保留为FINAL_REPORT-before-peripherals-v4-v5.md〔原始工作区：FINAL_REPORT-before-peripherals-v4-v5.md〕及旧参数表〔原始工作区：CURRENT_REALPC_SUMMARY-before-peripherals-v4-v5.md〕。

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
| Ubuntu Guest 内核 | Ubuntu linux=6.8.0-147.147；.config、生成头文件、Module.symvers；真实 release 6.8.12-generic #5 | 配置关闭 PARAVIRT/XEN/HYPERV 等未使用功能和不适用 uncore 访问，保留容器能力；启用 NVMe、igc、USB Audio、SPI/MTD、LPSS、MEI 等原版驱动；Sunshine 补编原版 UHID 模块。 | 已对实际内核树和同版本 Ubuntu 源码逐文件核对：C/H/S/Rust/DTS/Kconfig/Makefile 额外差异为 0；当前变化在配置和构建产物，不是给检测应用伪返回。 |
| GPU / KDE / 用户态驱动 | PVE hostpci0、VFIO 按 BDF 绑定；原版 NVIDIA 580.178.04 Open DKMS、Xorg/SDDM/UCM | RTX3080 GPU 与 HDMI 音频实体直通；匹配实际 #5 内核头文件重建 DKMS，保持 KDE 可用。 | 真实 OpenGL/Vulkan 渲染通过；不再将 GPU 声称为 UHD770，NVIDIA 驱动源码未做身份伪装修改。 |
| PVE 启动与亲和性 | /usr/bin/kvm Python 启动器；100.conf；ubuntu-q35.cfg；pve-emu-pin-vcpus / systemd | 仅 VM100 选专用 QEMU/OVMF，管理 SATA 后端转换 NVMe、e1000 转 I225-V；24 vCPU 与主/I/O 线程分配；其他 VM 沿用原启动器。 | 这里名为 kvm 的文件是用户态启动器；宿主实际 Linux 6.17.2-1-pve 内核未修改。 |
| 网络 / PortalWrt / 账号 | PVE 桥与路由；Guest 网络/账号配置；PortalWrt UCI、dnsmasq、firewall | WAN .232 → .233，LAN10.20.1.0/24、Ubuntu .2、WAN 禁 DHCP、上游静态路由；America/New_York；user 免密 sudo。 | 网络已做实际包验证；此层为系统配置，并不属于 QEMU 源码补丁。 |
| Sunshine / 开机自启 | 官方 Sunshine deb；Xorg headless 配置；user systemd drop-in；sunshine-launch / sunshine-xauthority；udev/input/UHID | 未登录 KDE 时自动启动，1080p60 X11 捕获与 NVENC 探测；实际重启 enabled/active/running，NRestarts=0。 | 未修改 Sunshine 源码；真实 Moonlight 端到端串流、音频/手柄尚未验收。 |
| vmcc 复用增量 | patches/0002-qemu-per-instance-spd.patch；tools/vmcc.py、kvm-wrapper.py 等 | 按实例外部加载 2048-byte SPD，生成独立系统/主板/机箱/磁盘/MAC 身份，保持四条 DIMM 连号；公开版移除原机身份与凭据。 | 这是新复用包的增量，不回写当前 VM100；复制实例的整机验收必须单独执行。 |

公开复用项目：[VoidInTheShell/vmcc](https://github.com/VoidInTheShell/vmcc)。当前实例完整身份仅保留在本地/本报告；公开仓库使用每实例生成机制。

## 本轮结果

| 项目 | 已应用及实测 | 原始记录 |
|---|---|---|
| CPU/主板 | 8P16E/24c24t；55连接器、9插槽、15板载记录、25有效引用；10张常规ACPI校验通过 | 验收JSON〔原始工作区：audio-iso-v6-20261014/raw/mainboard-summary.json〕、CPU-X〔原始工作区：audio-iso-v6-20261014/raw/cpu-x-dump.txt〕、PCI〔原始工作区：audio-iso-v6-20261014/raw/pci-identities.txt〕 |
| 网卡 | I225-V B3 8086:15f3，原版igc，2.5G链路；实际网关ping与HTTPS | 网络原始记录〔原始工作区：audio-iso-v6-20261014/raw/nic-network.txt〕 |
| USB/SATA | 1 xHCI、16HS/9SS根端口、15物理接口配置；480/5000/10000/20000Mb/s枚举和四盘写读；SATA六空端口可见、接盘6Gb/s写读通过 | 最终组合全日志〔原始工作区：audio-iso-v6-20261014/host/combined-peripheral.log〕、正式USB树〔原始工作区：audio-iso-v6-20261014/raw/usb-tree.txt〕 |
| 音频 | ALC4080原版snd-usb-audio/UCM；修复xHCI等时停止/恢复后，26次录音启停与3组高采样率双工无TRB错误；ALC897正式后端，隔离loopback双向非零，NVIDIA HDMI保留 | 采样统计〔原始工作区：audio-iso-v6-20261014/host/combined-peripheral-summary.txt〕、修复后正式回归〔原始工作区：audio-iso-v6-20261014/raw/audio-regression.json〕、设备与UCM〔原始工作区：audio-iso-v6-20261014/raw/usb-audio.txt〕 |
| SPI BIOS | 原版intel-spi/spi-nor读取32MiB，SHA与用户BIOS完全相同；只读，实际执行OVMF | 完整读取日志〔原始工作区：serialio-me-v5-20261014/host/spi-full-read-and-early-audio.log〕 |
| Serial IO | 原版LPSS/DesignWare/8250_dw/pxa2xx；I²C EEPROM32字节、UART64字节、SPI32/64/96/128字节回环一致 | 正式UART/I²C〔原始工作区：audio-iso-v6-20261014/raw/serialio-native-probe.txt〕、隔离完整传输〔原始工作区：serialio-me-v5-20261014/host/serialio-me-test.log〕 |
| MEI/SRAM | 原版mei_me状态ENABLED，HBM2.0/MKHI查询16.1.42.2872；SRAM16KiB/4KiB窗口实际写读 | MEI查询〔原始工作区：audio-iso-v6-20261014/raw/mei-native-probe.txt〕、SRAM〔原始工作区：audio-iso-v6-20261014/raw/sram-native-probe.json〕 |
| 内核/图形/账号 | 真实generic#5；Docker/SDDM active、failed0、user免密sudo；RTX3080 NVIDIA580.178.04、实际OpenGL渲染通过 | 运行状态〔原始工作区：audio-iso-v6-20261014/raw/boot-and-account.txt〕、图形〔原始工作区：audio-iso-v6-20261014/raw/graphics-console.txt〕 |
| VMAware发布版 | 全模式/debug均1/84、45%、confirmation=false，唯一THREAD_MISMATCH | all〔原始工作区：audio-iso-v6-20261014/raw/vmaware-all.txt〕、debug〔原始工作区：audio-iso-v6-20261014/raw/vmaware-debug.txt〕 |
| VMAware原版上游 | 固定提交e1a9786，全模式/debug均0/85、0%、confirmation=false | all〔原始工作区：audio-iso-v6-20261014/raw/vmaware-upstream-all.txt〕、debug〔原始工作区：audio-iso-v6-20261014/raw/vmaware-upstream-debug.txt〕 |
| 指令/时序 | 24CPU服务器特征/MSR审计通过；CPUID开销保留 | 服务器特征〔原始工作区：audio-iso-v6-20261014/raw/server-features.txt〕、时序〔原始工作区：audio-iso-v6-20261014/raw/cpuid-summary.json〕 |
| Portal与上游 | WAN.232/上游.233，LAN10.20.1.1/24，Ubuntu.2；WAN禁DHCP，上游持久路由实包3/3通过 | Portal〔原始工作区：audio-iso-v6-20261014/raw/portal-network.txt〕、DHCP运行〔原始工作区：audio-iso-v6-20261014/raw/portal-dhcp-runtime.txt〕、上游〔原始工作区：audio-iso-v6-20261014/raw/upstream-route.txt〕 |
| 内存 | 按要求暂停；四条SPD SHA与改动前一致 | 散列〔原始工作区：audio-iso-v6-20261014/raw/spd-unchanged-hashes.txt〕 |

## 不能视为已完成的部分

MEI是协议和有限服务模型，没有执行完整CSME，PTT/AMT/Boot Guard安全功能未实现。Serial IO的iDMA/分数分频、ALC4080厂商HID/DSP、网卡完整PTP/TSN、USB电气吞吐/PD/DP、真实主板传感器等仍有限制。录音TRB错误已定位为xHCI停止/恢复跳过未执行TD并修复；修复后39次端点恢复位置全部正确，26次录音启停和3组双工无TRB错误，修复前后日志完整保留；未宣称长期稳定性测试完成。CPU-X外频/电压/倍频/温度显示仍有异常或缺失；SHA/AVX-VNNI、CPUID时序及暂停的SPD问题没有被写成通过。检测程序和输出未修改，参数表逐项区分了能力枚举、实测与边界。

## 产物与回退

专用QEMU SHA256 `4369c050ced5d113a54610a8b8c74c4dc5ae58a13e37e8efd8c9fe7b1514d967`；真实#5内核SHA256 `b80345fc0ee03210253875fd961e8d0b2fcc305b48a876070e1ddc525a644084`。OVMF此前已为a700 Host Bridge重编译，本轮外围修复未再次改动，SHA256 `76d00c08e31571c98ffaaa3a4356e9414adf20b8fb825b287529a9bc26ee15b0`。

最终源码〔原始工作区：audio-iso-v6-20261014/source/〕、本轮修复与采集脚本〔原始工作区：audio-iso-v6-20261014/implementation/〕、外围实施脚本〔原始工作区：serialio-me-v5-20261014/implementation/〕、当前日志〔原始工作区：audio-iso-v6-20261014/raw/〕、当前宿主证据〔原始工作区：audio-iso-v6-20261014/host/〕、前轮证据〔原始工作区：serialio-me-v5-20261014/host/〕。PVE备份在`/root/pve-emu-provision-20261013/backup/{nic-audio-io-v4,serialio-me-v5,audio-iso-v6}/`，Guest旧#4内核和生成头文件在`/root/emu-backup/serialio-me-v5/`。没有新增持久root SSH公钥；测试HTTP与snd-aloop已清理。

最终完整性清单：FINAL_PERIPHERALS_SHA256SUMS〔原始工作区：FINAL_PERIPHERALS_SHA256SUMS〕。旧有阶段性SHA256清单保持不变。
