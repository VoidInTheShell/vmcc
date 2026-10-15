# 当前真机化改动与独立参数表

公开版：省略原机身份与凭据，IP使用文档示例；硬件参数和原始验收结论保留。文件名所指的完整证据保留在原项目工作区，公开选摘见 docs/validation。

Sunshine增量更新：2026-10-14 20:33 EDT。已安装官方稳定版并实际重启验证开机自启；当前boot ID `[INSTANCE_UUID]`。下文原外围整机验收仍对应其标注的前一次boot ID。详见Sunshine配置与验收〔原始工作区：sunshine-20261014/README.md〕。

2026-10-14 14:14 EDT 更新；正式冷启动 boot ID `[INSTANCE_UUID]`。VM100 与 VM101 均运行。本轮已将网卡、声卡、USB、SATA、SPI BIOS、Serial IO、MEI 和 PCH SRAM 模型部署到 VM100，并完成下列测试。原表保留为 CURRENT_REALPC_SUMMARY-before-peripherals-v4-v5.md〔原始工作区：CURRENT_REALPC_SUMMARY-before-peripherals-v4-v5.md〕。

## 已应用的改动

1. 保留项目 QEMU/OVMF、i9-13900K 8P+16E / 24c24t / HT关闭、64GiB、500GiB NVMe、实体 RTX3080、PortalWrt 网关、user 账号及免密 sudo。
2. e1000 实际替换为 I225-V B3 功能模型，原版 igc 驱动收发；新增一个 PCH 根端口，PCIe 树和板载记录同步。
3. ALC4080 USB UAC2 音频使用原版 snd-usb-audio 与 UCM，实际接 PVE ALSA 音频后端。USB 统一为一个 xHCI、16 HS/9 SS 根端口，补上 10G/20G 协议速度、双 lane、两只 USB2 hub 和 ACPI 端口信息。
4. SATA 六个空端口可见；临时接盘实测 6Gb/s 写读。SPI NOR 由原版驱动读取完整32MiB用户 BIOS，SHA256完全一致；实际启动仍使用 OVMF。
5. Serial IO 启用 I²C0、UART0、GSPI0；原版 LPSS/DesignWare/8250_dw/pxa2xx 驱动绑定，I²C 真实 NACK/EEPROM写读、UART/SPI回环通过。iDMA 与 UART 分数分频不虚报。
6. MEI 实现 HECI 传输、HBM2.0 与有限 MKHI 服务，原版 mei_me 绑定；固件版本从用户 BIOS manifest 提取。PCH SRAM 两个窗口实际可写读。这里未实现完整 CSME、安全固件和全部主板电路。
7. SMBIOS 增至15条板载记录、25个有效引用；10张常规 ACPI 表校验通过。实际重编译 generic #5 内核，新增原版驱动模块；NVIDIA、SDDM、OpenGL 实际渲染和网络复核通过。
8. 修复xHCI Stop Endpoint对未执行等时TD的恢复位置；保留修复前后事件跟踪，用原版ALSA反复启停和双工验收。
9. 内存按用户要求暂停。四条 SPD 内容 SHA256 与本轮之前相同；decode-dimms 问题未解决。检测程序和输出没有修改，CPUID 时序缺口保留。

实现位置另见分层源码改动清单〔原始工作区：SOURCE_CHANGE_LAYERS.md〕：覆盖QEMU、SMBIOS/ACPI、OVMF、Guest内核与驱动、PVE启动配置、网络和Sunshine。

## 参数表

“身份/能力枚举”“功能实测”和“完整实体硬件等效”是不同结论。模拟的时钟、链路和品牌不能证明真实 13900K/Z790 执行性能。表中未完成项保留原始现象。

| 类别 | 参数 | 当前值 |
|---|---|---|
| 虚机 | Ubuntu / PortalWrt VMID | 100 / 101；均运行，onboot=1，Portal 启动顺序 1，Ubuntu 顺序 2 |
| 来源 | Ubuntu | ghcr.io/catthehacker/ubuntu:act-24.04；OCI 根文件系统已转换为 GRUB/UEFI 虚机 |
| QEMU | 项目包 | pve-qemu-kvm 10.1.2-7 |
| QEMU | VM100 二进制 | /usr/local/lib/pve-emu-13900k/qemu-system-x86_64 |
| QEMU | SHA256 | 4369c050ced5d113a54610a8b8c74c4dc5ae58a13e37e8efd8c9fe7b1514d967 |
| UEFI | 项目包 / 执行固件 | pve-edk2-firmware-ovmf 4.2025.05-2 / OVMF_CODE_RPL_4M.fd；EDK2 stable202505 X64 RELEASE，4 MiB，Secure Boot 关闭 |
| UEFI | 执行固件 SHA256 | 76d00c08e31571c98ffaaa3a4356e9414adf20b8fb825b287529a9bc26ee15b0 |
| CPU | 品牌 / 插槽 | 13th Gen Intel(R) Core(TM) i9-13900K / LGA1700 |
| CPU | 签名 | GenuineIntel，Family 6，Model 183（0xB7），Stepping 1，CPUID 0x000B0671 |
| CPU | 实际分配 | 1 socket，24 cores，24 threads；8P×1T + 16E×1T，HT 关闭 |
| CPU | QEMU / PVE | -smp 24,sockets=1,dies=1,cores=24,threads=1,maxcpus=24；PVE cores=24，affinity=0-23 |
| CPU | 逐核类型 / APIC | P 类型 0x40、APIC 0–7；E 类型 0x20、APIC 32–47；QEMU core-id 0–23，每核 thread-id=0 |
| CPU | 拓扑叶 | CPUID 0xB、0x1F：SMT shift=0、count=1；包线程数 24；x-force-cpuid-0x1f=on |
| CPU | HT 能力与运行 | CPUID ht 位表示芯片能力，仍可为 1；Linux smt/active=0，thread_siblings 逐核只含自己；DMI Hardware Thread 特征清除 |
| CPU | 宿主亲和性 | 24 vCPU 分别绑定宿主 CPU 0–23；QEMU主线程/RCU/I/O线程及KVM后台线程28–31；内核io_uring worker可能继承发起vCPU的亲和性；服务持久生效 |
| CPU | 频率枚举 | P 3000/5800 MHz；E 2200/4300 MHz；外频 100 MHz；声明不等同物理执行性能 |
| CPU | TSC | tsc-frequency=3000000000，invtsc=on，实际 clocksource=tsc |
| 缓存 | P 核 | 每核 L1D 48 KiB / L1I 32 KiB / L2 2 MiB |
| 缓存 | E 核 | 每核 L1D 32 KiB / L1I 64 KiB；每 4 核共享 L2 4 MiB |
| 缓存 | 总量与实例 | L1D 896 KiB / L1I 1280 KiB；L2 32 MiB、12 实例；L3 36 MiB、1 实例；CPUID L3 sharing-ID 容量 64 |
| CPU | 控制参数 | hypervisor=off,kvm=off,vmware-cpuid-freq=false,pmu=off,host-cache-info=off,host-phys-bits=true,enforce=false,hle=off,rtm=off,dca=off,level=31 |
| CPU | 服务器特征审计 | 24 vCPU 的 DCA/PSN/RDT_MON/RDT_ALLOC/HLE/RTM=0；CPUID 0xF/0x10 subleaf 0–3 全零 |
| CPU | MSR 审计 | PPIN 0x4e/4f、CQM/PQR 0xc8d/c8e/c8f、CAT 0xc90 均不支持，errno=5 |
| CPU | 未补指令 | SHA、AVX-VNNI 仍缺失；未伪报宿主不能执行的指令 |
| 主板 | 厂商 / 型号 / SN | Micro-Star International Co. Ltd. / PRO Z790-A WIFI DDR4（MS-7E07）/ [BOARD_SN]；version=1.0 |
| 系统 | UUID / 机箱 SN | [INSTANCE_UUID] / [CHASSIS_SN] |
| BIOS | 元数据 | American Megatrends International LLC. / E7E07IMS.MB0 / 08/21/2026；用户文件 33,554,432 bytes，32 MiB |
| BIOS | 显示与表版本 | SMBIOS 3.5.0；Type0 长度 26，ROM=0xff，扩展容量=0x0020；CPU-X 96 kB / 32 MB |
| 主板 | SMBIOS 完整性 | Type8 55 个连接器，Type9 9 个插槽，Type41 15 条板载记录；Type2 含 25 个有效句柄；无重复句柄或 OUT OF SPEC |
| 主板 | 扩展插槽 | PCI_E1 Gen5 电气/物理 x16；E2 Gen3 x1；E3 Gen4 电气 x4/物理 x16；E4 Gen3 电气 x1/物理 x16 |
| 主板 | M.2 插槽 | M2_1–4 Socket3、PCIe Gen4 x4；M2_WIFI Key-E；M2_1 被 NVMe 占用；空槽 BDF 使用标准未提供值 |
| 主板 | 已启用板载记录 | I225-V、SATA、SMBus、xHCI、LPC、SPI BIOS、ALC4080、PCH SRAM、I²C0、MEI、UART0、GSPI0；PCI 记录均指向实际设备，USB ALC4080 使用标准无 PCI BDF 值 |
| 主板 | 停用板载记录 | UHD770、Wi-Fi 6E、Bluetooth；未制造可用的图形、无线或蓝牙驱动 |
| 主板 | 连接器清单 | 包括后置 8 USB、前置 7 USB、6 SATA、HDMI/DP、LAN、音频、Wi-Fi 天线、电源/风扇/机箱/RGB/TPM/TBT 等接口记录；清单不代表全部实体电路已模拟 |
| ACPI | 统一头部 | 10 张常规表 ALASKA / MS7E07 / AMI，checksum 全通过；含 USB 端口 SSDT 1921 bytes、Serial IO/ME/SRAM SSDT 200 bytes；FACS 使用标准特殊格式 |
| ACPI | CPU / MADT | 24 个静态 Processor 对象；MADT APIC 0–7、32–47；旧 48 槽 DSDT/APIC initramfs 覆盖已移除 |
| ACPI | 中断 / 热插拔 | 128 条 _PRT 直接 GSI16–23 路由，APIC-only；IRQ0→GSI2，SCI IRQ9→GSI9；CPU/PCI 热插拔关闭 |
| ACPI | 电源 / PCIe | _S5=[7,0,0,0]，PM1 实际支持 SLP_TYP=7；_OSC 0x1C，保留 PME/AER/PCIe capability，关闭 SHPC/PCIe 热插拔权限 |
| ACPI | 其余处理 | MCHC 资源预留；真实 HPET 节点；移除未用 PIC 查询/链接、设备标号辅助方法和错误 _GPE _HID；WWWT；Guest fw_cfg 节点不公开 |
| PCI | Host / LPC | 00:00.0 8086:a700 / subsystem 1462:7e07；00:1f.0 8086:7a04，rev11 |
| PCI | PEG / NVMe 根端口 | 00:01.0 a70d，最大32 GT/s×16；00:06.0 a74d，最大16 GT/s×4；当前链路均8 GT/s，分别x16/x4 |
| PCI | PCH 根端口 | 00:1c.0 7a38、1c.1 7a39、1c.2 7a3a、1c.3 7a3b、1c.4 7a3c、1d.0 7a30、1d.4 7a34、1b.0 7a40，revf1；加 CPU PEG/NVMe，合计 10 个根端口 |
| PCI | USB / SATA / SMBus | 00:14.0 8086:7a60 xHCI；00:17.0 7a62 SATA；00:1f.4 7a23 SMBus；rev11，subsystem 1462:7e07 |
| USB | 实际模型与驱动 | 1 个 PCI xHCI，原版 xhci_hcd；2 个标准 root hub，16 HS + 9 SS 根端口；最高 SuperSpeedPlus 20G 双 10G lane；根端口数不等于物理插口数 |
| 内存 | 保留配置 | 64 GiB，4×16 GiB；先前 DDR4-4000 配置保留；本轮不处理 decode-dimms/SPD 差异 |
| 内存 | 历史身份与时序 | 历史写入 Crucial/Micron BL16G36C16U4W.M8FB1，[DIMM_SN_1]–B4，1Rx8，XMP CL16-19-19-38 / 1.48V；这些字段本轮不重新验收 |
| 内存 | 不变性实测 | 4 条 512-byte EE1004 EEPROM SHA256 与修改前完全一致；完整散列见 spd-unchanged-hashes.txt |
| NVMe | 容量 / 后端 | 500 GiB = 536,870,912,000 bytes；emu-lvm /dev/emu-vg/vm-100-disk-1；Guest 根分区 /dev/nvme0n1p2 |
| NVMe | 型号 / SN / 固件 | KIOXIA-EXCERIA SSD / [NVME_SN] / ECFA15.3；复制 PVE 物理系统盘身份 |
| NVMe | PCI / Subsystem / OUI | Guest 02:00.0；1e0f:0009 / 1e0f:0032，rev01；OUI 8ee38c |
| NVMe | NQN / EUI64 / NGUID | nqn.2019-10.com.kioxia:KIOXIA-EXCERIA SSD:[NVME_SN] / [EUI64] / 0000000000000000[EUI64] |
| NVMe | UUID | namespace 00000000-0000-0000-[NS_UUID]；filesystem [INSTANCE_UUID] |
| 存储 | PVE 管理与实际设备 | PVE sata0 管理后端，启动器转换为实际 NVMe；cache=directsync，discard=on；PVE 实体系统盘未直通 |
| GPU | 实际设备 | 物理 MSI RTX3080 GA102，10240 MiB；GPU 10de:2206 / subsystem1462:3892，音频10de:1aef |
| GPU | 直通 / 持久绑定 | hostpci0=0000:82:00,pcie=1,x-vga=1；宿主82:00.0/.1 → Guest01:00.0/.1；按 BDF 的 VFIO 服务开机生效 |
| GPU | 驱动 / VBIOS / UUID | NVIDIA580.178.04 Open DKMS；94.02.42.00.FB；GPU-[INSTANCE_UUID] |
| GPU | 图形实测 | NVIDIA OpenGL4.6、direct rendering=Yes；Vulkan1.4.312；KMS=Y、fbdev=Y；SDDM :0实际渲染通过 |
| 内核 | 当前实际 release | 6.8.12-generic #5 SMP PREEMPT_DYNAMIC；真实重新编译并冷启动，uname 未覆盖；#4 文件另存回退 |
| 内核 | 配置 | 保留 PARAVIRT=n、HYPERV=n、INTEL_UNCORE_FREQ_CONTROL=n、PERF_EVENTS_INTEL_UNCORE=n；新增原版 IGC、SND_USB_AUDIO、MTD/SPI、LPSS、MEI、8250_DW、SPI_PXA2XX 模块；SERIAL_8250_DWLIB=y；HYPERVISOR_GUEST=y |
| 设备 | 关闭项 | balloon=0,tablet=0,hotplug=0,vmgenid=0,vga=none,numa=0；旧244e桥、29c0身份、Cirrus已移除 |
| 环境 | 实测 | systemd-detect-virt=none；Docker/SDDM active，failed units=0；/lib→usr/lib；kernel+userspace 8.432s（不含固件）；NTP synchronized=yes |
| 网络 | Ubuntu | I225-V B3 虚拟 NIC，[INSTANCE_MAC]；原版 igc；10.20.1.2/24，网关/DNS 10.20.1.1；仅此一块虚拟以太网卡 |
| 网络 | PortalWrt 资源 | 4c / 4 GiB / 原自编译 PortalWrt2084 MiB 镜像 |
| 网络 | PortalWrt WAN / LAN | 物理04:00.0直通 WAN192.0.2.2/24，上游/DNS.233；虚拟 LAN10.20.1.1/24 |
| DHCP | LAN / WAN | 服务接口 br-lan，池 10.20.1.100–199 / 12h，Ubuntu 静态 .2；except-interface=eth0 + no-dhcp-interface=eth0；WAN DHCP/DHCPv6 客户端和服务关闭 |
| 防火墙 | 策略 | input/output/forward ACCEPT + NAT；WAN UDP 67–68/546–547 收发和转发 DROP；本轮 WAN output/forward_out DHCP 规则计数均 0；输入广播被丢弃 |
| 路由 | 上游与宿主 | .233 持久静态 10.20.1.0/24 via 192.0.2.2，本轮 3/3 ping .2；PVE vmbr1=10.20.1.254，默认网关 .233 |
| 账号 | Ubuntu / PortalWrt | Ubuntu user / [凭据省略]，uid1002，sudo/video/render，NOPASSWD sudo实测；PortalWrt root / [凭据省略] |
| 时区 | Ubuntu / PortalWrt | America/New_York；Ubuntu NTP synchronized=yes |
| 检测 | 官方 release v2.8.2 | 原二进制全模式/debug：1/84，45%，confirmation=false，唯一THREAD_MISMATCH |
| 检测 | 官方上游固定提交 | e1a9786576a58177b2a46a0e780226d218bab349 未修改源码，全模式/debug：0/85，0%，confirmation=false；14个src文件比对官方一致 |
| 时序 | 保留缺口 | 24 vCPU × 1000 次 CPUID；P50 2148–2561 cycles，P99 2291–6876 cycles，backwards=0；TSC 2999.883–2999.939 MHz |
| QEMU | 外围模型参数 | i225-v；usb-alc4080；usb2-hub ports=4 ×2；qemu-xhci p2=16,p3=9,z790-ports=on；z790-spi、z790-i2c、z790-uart、z790-gspi、z790-me、z790-sram；完整启动参数见host-runtime.txt |
| 设备 | 迁移状态 | 新外围模型 VMState 标记 unmigratable；完整设备迁移状态未实现，不能据本轮启动验收声明实时迁移或含内存快照可用；RTX3080仍是实体直通 |
| 网卡 | PCI / 链路 | Guest 07:00.0 8086:15f3 rev03，subsystem 1462:7e07；I225-V B3，原版 igc；2.5Gb/s full duplex；根端口 00:1c.3，PCIe 当前 5GT/s×1、最大 8GT/s×1 |
| 网卡 | 功能与边界 | 实际 ping、DNS/HTTPS 流量通过；非只改设备 ID；PTP/PHC 计时、PTM、TSN/EEE 电气行为未完整实现，未验收相应功能 |
| 声卡 | ALC4080 身份 / 位置 | USB 0db0:d1d7，HS05，480Mb/s；原版 snd-usb-audio；稳定卡名 Audio / NVidia；当前冷启动 card1 USB、card0 NVIDIA HDMI；HDMI驱动启动有polling回退，未验证显示器音频输出；卡号可变化 |
| 声卡 | PCM / UCM | UAC2，6 音频流、7 个接口；后置最多 7.1，前置输出最多 32bit/384kHz；16/24/32bit PCM；原版 UCM HiFi、HiFi 5+1、HiFi 7+1 可用 |
| 声卡 | 实际后端 / 验证 | PVE ALC897 plughw:0,0，后端输出48kHz/8ch、输入48kHz/2ch；修复 xHCI 停止/恢复丢TD后，正式虚机26次录音启停、3组192k/384k/48k双工通过，无TRB错误；隔离snd-aloop双向非零；不等于实体384kHz DAC性能 |
| 声卡 | 尚未实现 | 实体 ALC4080 的附加 HID 接口、厂商 DSP、IEC61937 压缩音频及真实插孔电气检测未完整实现 |
| USB | 物理接口配置 | 15 个物理连接器：后置 8 / 前置 7；USB2 6（后2前4），5G 4（后2前2），10G 4（后3前1），20G 1（后1） |
| USB | 内部 Hub / 连接 | 2 个 GL850G 兼容 USB2 hub，05e3:0608 rev0901，各4端口；HS12 后置 hub 2 个外部有效端口，HS13 前置 hub 4 个；ALC4080 HS5；BT HS14 停用 |
| USB | SS / HS 配对 | SS1–9 对应 HS1/3/4/6/7/8/9/10/11；SS1–4 5G，SS5–8 10G，SS9 20G；除实机已知 HS5/12/13/14 外，精确板厂布线配对仍为推定 |
| USB | 读写验收与边界 | 隔离设备原版 Linux 驱动分别识别 480/5000/10000/20000Mb/s，20G rx/tx lanes=2；四盘写读 SHA256 一致；未证明实体 20Gb/s 电气吞吐，PD/DP Alt Mode 未实现 |
| SATA | 控制器 / 空端口 | 8086:7a62 rev11；AHCI 1.3.1，32 command slots，6 ports，6Gb/s，PI=0x3f；正式虚机 ata1–6 均 link down，控制器持续可见 |
| SATA | 功能验收 | 原版 ahci + libata；隔离临时 SATA 盘协商 6.0Gbps，PIO/NCQ DMA 数据通路沿用 QEMU，写读 SHA256 一致；Gen1/Gen2 限速按 SControl 生效 |
| SPI BIOS | PCI / 原版驱动 | 00:1f.5 8086:7a24 rev11，subsystem 1462:7e07；原版 intel-spi + spi-nor，/dev/mtd0 32MiB，只读 |
| SPI BIOS | 完整读取 SHA256 | bf40f12d7d6cfef81622b87183f5d8e2dee3c22e1d3a59ffb398293fa1975954；/dev/mtd0 全盘读取与用户 E7E07IMS.MB0 文件逐字节散列一致 |
| SPI BIOS | 模型边界 | W25Q256 兼容 JEDEC 32MiB；实际主板 flash 厂商未证实；执行固件仍为 OVMF，不执行该 MSI BIOS，也不支持刷写 |
| Serial IO | 启用数量 / 模式 | 本配置启用 I²C0、UART0、GSPI0 各 1 个，共 3 个控制器；其余通道未启用；PIO 模式，NO_IDMA=1，不伪报 iDMA |
| Serial IO | I²C0 | 00:15.0 8086:7a4c rev11 / subsystem1462:7e07；intel-lpss + 原版 i2c_designware；64-entry FIFO；空地址 errno121；隔离 EEPROM 32 字节写读一致 |
| Serial IO | UART0 | 00:1e.0 8086:7a28 rev11 / subsystem1462:7e07；intel-lpss + 原版 8250_dw，复用 QEMU 16550 引擎；115200 配置、64 字节回环一致；分数分频未实现 |
| Serial IO | GSPI0 | 00:1e.2 8086:7a2a rev11 / subsystem1462:7e07；intel-lpss + 原版 spi_pxa2xx_platform；64-word FIFO；1MHz、8bit，32/64/96/128 字节原版 SPI API 回环一致 |
| ME | PCI / 原版驱动 | 00:16.0 8086:7a68 rev11 / subsystem1462:7e07；mei_me + mei，/dev/mei0，dev_state=ENABLED，MSI/INTx、HECI 环形队列和复位实际工作 |
| ME | 协议 / 版本来源 | HBM 2.0 子集（驱动支持2.2），256-byte MTU，单 MKHI client；BIOS $MN2 manifest 提取 16.1.42.2872；原版驱动 fw_ver 与 8 次标准 ioctl/MKHI 查询一致 |
| ME | 明确边界 | 协议模型，不执行 CSME 固件；没有实现完整 ME、PTT、AMT、Boot Guard 证明、密钥/签名、provisioning 或固件更新；未知 MKHI 命令返回不支持 |
| PCH SRAM | PCI / 实际存储窗口 | 00:14.2 8086:7a27 rev11 / subsystem1462:7e07；BAR0 16KiB + BAR2 4KiB，64bit MMIO RAM；各256字节写读一致并恢复原值；未宣称执行 ME 共享固件 |
| 内核 | 新镜像 SHA256 | b80345fc0ee03210253875fd961e8d0b2fcc305b48a876070e1ddc525a644084 |
| 显示与传感器 | 当前未验收项 | 原版 CPU-X 外频显示 -21474836.48MHz、电压0.120V、倍频/温度缺失；不能作为真实频率/电压读数；未改 CPU-X 输出，保留为缺口 |
| USB | 等时停止/恢复修复 | 保留未执行TD地址及cycle state；修复前3/3跳过，修复后39/39恢复正确；另10次初测+26次回归录音启停，无TRB错误；未修改原版ALSA/Linux xHCI驱动 |

| 类别 | 参数 | 当前值 |
|---|---|---|
| Sunshine | 版本 / 来源 | 官方稳定版2026.914.233613-1+ubuntu24.04；提交63d35f702ee9e362e43263742981836ec0710384；Ubuntu24.04 amd64 deb，官方digest校验一致 |
| Sunshine | 管理 / 客户端 | https://10.20.1.2:47990；user / [凭据省略]；Moonlight手动添加10.20.1.2并通过PIN首次配对；名称Ubuntu-EMU-RTX3080 |
| Sunshine | 开机自启 | user服务app-dev.lizardbyte.app.Sunshine.service，别名sunshine；default.target+graphical-session.target；Linger=yes；实际重启未登录KDE时active/running、NRestarts=0 |
| Sunshine | 画面 / 编码 | NVIDIA Xorg无显示器1920×1080/60Hz、X11捕获；RTX3080 h264_nvenc/hevc_nvenc通过自身编码探测；AV1不广播；SDDM保持密码登录 |
| Sunshine | 输入 / 内核 | user新增input组；官方udev规则访问uinput/uhid；匹配#5内核源码编译原版uhid.ko并在重启自动加载；内核镜像SHA不变 |
| Sunshine | 音频 / 验收范围 | PipeWire/Pulse/WirePlumber active，未登录时auto_null/monitor；上游.233管理接口认证HTTP200；未连接真实Moonlight客户端，端到端串流/音频/手柄尚未验收 |
| Sunshine | 安全与权限参数 | LAN管理，UPnP disabled；user进程；root拥有helper复制当前Xorg授权至用户运行目录；X11使用CAP_SYS_NICE+p，未保留KMS所需CAP_SYS_ADMIN文件能力 |
| Sunshine | 安装包 / 二进制SHA256 | deb c38e9c705f650f8705f61702717e99bec34044c5028fcb8f23a08fe041292c21；sunshine 61e1ecbc8db2df786b9760c652aa4b9885dff36c57d4af09616344314cb7c34c |

## 验收与原始结果

- 主板/CPU/ACPI/PCI验收 JSON〔原始工作区：audio-iso-v6-20261014/raw/mainboard-summary.json〕：`PERIPHERALS_V6_PASS`；完整PCI〔原始工作区：audio-iso-v6-20261014/raw/pci-identities.txt〕、DMI〔原始工作区：audio-iso-v6-20261014/raw/dmidecode.txt〕、原版CPU-X输出〔原始工作区：audio-iso-v6-20261014/raw/cpu-x-dump.txt〕。
- 正式虚机MEI原始查询〔原始工作区：audio-iso-v6-20261014/raw/mei-native-probe.txt〕、UART/I²C〔原始工作区：audio-iso-v6-20261014/raw/serialio-native-probe.txt〕、SRAM写读〔原始工作区：audio-iso-v6-20261014/raw/sram-native-probe.json〕；隔离I²C EEPROM/SPI传输及启动全日志〔原始工作区：serialio-me-v5-20261014/host/serialio-me-test.log〕。
- 最终USB四档/SATA/ALSA组合全日志〔原始工作区：audio-iso-v6-20261014/host/combined-peripheral.log〕、非零双向音频采样统计〔原始工作区：audio-iso-v6-20261014/host/combined-peripheral-summary.txt〕、正式USB/音频描述符与UCM〔原始工作区：audio-iso-v6-20261014/raw/usb-audio.txt〕。五块临时盘读取SHA均为 `a9752e25c231d2e59c3df878b44a46b0a400e5fe3f910dddecd0b6ed2fd826f7`；正式500GiB盘未用于破坏性测试。
- 完整32MiB SPI读取及早期音频日志〔原始工作区：serialio-me-v5-20261014/host/spi-full-read-and-early-audio.log〕：SPI SHA与用户BIOS完全一致。早期及正式录音中曾复现音频TRB错误，现已定位为xHCI Stop Endpoint跳过未执行的等时TD并修复；修复前原始内核日志〔原始工作区：audio-iso-v6-20261014/raw/dmesg-before-fix.txt〕、实际补丁〔原始工作区：audio-iso-v6-20261014/source/xhci-iso-stop.patch〕、前后事件对照〔原始工作区：audio-iso-v6-20261014/raw/trace-regression-summary.json〕保留。
- 修复后正式ALSA回归〔原始工作区：audio-iso-v6-20261014/raw/audio-regression.json〕：20次独立录音加6次双工录音，每次48000帧，三组3秒播放含7.1/192kHz、前置2ch/384kHz和2ch/48kHz；完整最终内核日志〔原始工作区：audio-iso-v6-20261014/raw/dmesg-final.txt〕中无TRB错误。宿主物理PCM状态采样〔原始工作区：serialio-me-v5-20261014/host/physical-audio-running.txt〕核对实际后端。模拟前端采样率由QEMU转换到宿主48kHz，不宣称ALC897物理DAC运行384kHz。
- 真实内核/用户/服务/时区〔原始工作区：audio-iso-v6-20261014/raw/boot-and-account.txt〕、RTX3080实际帧渲染〔原始工作区：audio-iso-v6-20261014/raw/graphics-console.txt〕、Vulkan〔原始工作区：audio-iso-v6-20261014/raw/vulkan-summary.txt〕、逐核服务器指令/MSR审计〔原始工作区：audio-iso-v6-20261014/raw/server-features.txt〕、SPD不变散列〔原始工作区：audio-iso-v6-20261014/raw/spd-unchanged-hashes.txt〕。
- PortalWrt当前配置〔原始工作区：audio-iso-v6-20261014/raw/portal-network.txt〕、运行中DHCP接口限制〔原始工作区：audio-iso-v6-20261014/raw/portal-dhcp-runtime.txt〕、上游静态路由与实包ping〔原始工作区：audio-iso-v6-20261014/raw/upstream-route.txt〕。dnsmasq的DHCP UDP socket仍按其实现显示`0.0.0.0:67`，应用只服务br-lan，明确排除eth0；WAN入站DHCP在防火墙丢弃，出站/转发禁发。没有把通配socket误写为只bind一个地址。

以下为当前冷启动原始检测汇总，完整输出分别链接；发布版没有写成零命中。

```text
HYBRID_TOPOLOGY_AUDIT=PASS
TESTED_VCPUS=24
SERVER_FEATURE_AUDIT=PASS
PERIPHERALS_V6_PASS

VMAware v2.8.2 official release:
VM brand: Unknown
VM likeliness: 45%
VM confirmation: false
VM detections: 1/84
Hit: THREAD_MISMATCH

VMAware official upstream e1a9786, unmodified source:
VM brand: Unknown
VM likeliness: 0%
VM confirmation: false
VM detections: 0/85
```

发布版all〔原始工作区：audio-iso-v6-20261014/raw/vmaware-all.txt〕、发布版debug〔原始工作区：audio-iso-v6-20261014/raw/vmaware-debug.txt〕、上游all〔原始工作区：audio-iso-v6-20261014/raw/vmaware-upstream-all.txt〕、上游debug〔原始工作区：audio-iso-v6-20261014/raw/vmaware-upstream-debug.txt〕、工具二进制校验〔原始工作区：audio-iso-v6-20261014/raw/unmodified-tools.txt〕。上游源码固定提交 `e1a9786576a58177b2a46a0e780226d218bab349`，前轮14个源码文件官方比对〔原始工作区：mainboard-v3-20261014/raw/vmaware-source-verification.json〕保留；本轮未改源码和二进制。

根据[发布版源码](https://github.com/NotRequiem/VMAware/blob/v2.8.2/src/vmaware.hpp#L6848)与[上游修正](https://github.com/NotRequiem/VMAware/blob/e1a9786576a58177b2a46a0e780226d218bab349/src/vmaware.hpp#L7437)，发布版按默认32线程比较，未正确处理该机型关闭HT。结合逐核CPUID和Linux SMT关闭，THREAD_MISMATCH判断为该规则误报。发布版CLI仍显示2.8.1是[release说明](https://github.com/NotRequiem/VMAware/releases/tag/v2.8.2)记录的问题。CPUID时序独立日志见完整结果〔原始工作区：audio-iso-v6-20261014/raw/cpuid-timing.txt〕和范围汇总〔原始工作区：audio-iso-v6-20261014/raw/cpuid-summary.json〕，零命中不能代替时序通过。

## 尚未完成或未验收

- CPUID时序、SHA/AVX-VNNI和原版CPU-X外频/电压/温度/倍频读数仍存在缺口；没有修改检测应用，也没有伪报宿主不能执行的指令。
- 完整CSME固件、安全服务、TPM/PTT、AMT、Boot Guard证明、Super-I/O、真实温度/风扇和全部主板电路未等效实现；ME版本查询通过仅证明本模型服务工作。
- Serial IO为三个已启用控制器的PIO功能子集；iDMA、UART分数分频、完整外部引脚与电气特性未实现。USB精确板厂配对部分推定，PD/DP Alt Mode、实体20Gb/s性能未验收。
- 网卡PTP/PHC/PTM/TSN与ALC4080厂商HID/DSP/IEC61937存在上述限制；xHCI停止/恢复错误已修复并完成功能回归，仍未宣称长期压力或实体电气性能验收。
- SPD/decode-dimms对齐按用户要求暂停；四条EEPROM内容保持不变。

## 来源与复核产物

主板接口数量参考[MSI官方规格](https://www.msi.com/Motherboard/PRO-Z790-A-WIFI-DDR4/Specification)；GL850G与音频接口参考[MSI官方手册](https://download.msi.com/archive/mnu_exe/mb/PROZ790-AWIFIDDR4.pdf)。PCI ID和寄存器/协议对照本轮归档的原版Linux驱动源码及[Intel 700系列PCH资料](https://cdrdv2-public.intel.com/743835/743835-004.pdf)。原版驱动通过和模型边界以上述原始日志为准。

- 实际QEMU源码〔原始工作区：audio-iso-v6-20261014/source/〕、正式SMBIOS/ACPI配置〔原始工作区：serialio-me-v5-20261014/source/host-config/〕、构建与实施脚本〔原始工作区：serialio-me-v5-20261014/implementation/〕、宿主实际进程及配置〔原始工作区：audio-iso-v6-20261014/host/host-runtime.txt〕、清理后宿主状态〔原始工作区：audio-iso-v6-20261014/host/host-final-state.txt〕。脚本含阶段性增量，不能不检查前置条件盲目重复运行。
- PVE备份：`/root/pve-emu-provision-20261013/backup/nic-audio-io-v4/`与`backup/serialio-me-v5/`及`backup/audio-iso-v6/`；虚机#4内核及生成头文件备份：`/root/emu-backup/serialio-me-v5/`。回退设备模型时需同步恢复QEMU/VM配置/SMBIOS/ACPI，避免启用记录指向不存在的设备。
- Guest当前日志：`/var/log/emu-validation/peripherals-v6/`。没有新增持久root SSH公钥；本任务临时HTTP服务和snd-aloop已清理，ALC4080正式后端继续使用PVE物理ALC897。

最终完整性清单：FINAL_PERIPHERALS_SHA256SUMS〔原始工作区：FINAL_PERIPHERALS_SHA256SUMS〕。旧有阶段性SHA256清单保持不变。

Sunshine新增配置、原始日志与散列见安装记录〔原始工作区：sunshine-20261014/README.md〕和SUNSHINE_SHA256SUMS〔原始工作区：sunshine-20261014/SUNSHINE_SHA256SUMS〕。
