# 多实例身份盘点

同配置机器保留同一硬件型号、PCI ID、固件版本、ACPI 结构和资源规模；每台实例使用固定且独立的身份。`identity.json` 是持久来源，属于本地部署数据，已被 Git 忽略。不要通过每次开机随机化来生成身份。

| 标识或状态 | 复制规则 | 当前工具如何处理 | 后续验收 |
|---|---|---|---|
| PVE VMID / 名称 | 每实例不同 | init 生成指定 VMID 与 hostname；audit 查重 | 宿主 VMID 不得已存在 |
| SMBIOS Type1 system UUID | 每实例不同 | UUIDv4；PVE smbios1→QEMU -uuid | Guest product_uuid |
| Type1 system SN | 每实例不同 | 随机 SYS 前缀；写入 Type1 参数 | Guest product_serial |
| Type2 board SN | 每实例不同 | 随机 07E07 前缀；重建 SMBIOS 字符串区 | Guest board_serial |
| Type3 chassis SN | 每实例不同 | 随机 DT 前缀；写入 Type3 参数 | Guest chassis_serial |
| Type17 DIMM SN ×4 | 机内连续、跨机不重复 | 随机 32bit 起点，连续四条；audit 查重 | DMI 与 EEPROM 两边比对 |
| SPD bytes 325–328 ×4 | 与对应 Type17 相同 | 生成独立 2048-byte 文件；仅更改这 16 字节 | 两个实际启动实例已验证 |
| SPD JEDEC / XMP / 时序等 | 同型号可相同 | 保留当前模板其余字节；SN 区不在既有 base/module CRC 覆盖区内 | decode-dimms 差异仍暂停，不宣称修好 |
| NVMe serial | 每盘不同 | 随机 12 位十六进制串，PVE 与实际 nvme 属性一致 | nvme id-ctrl |
| NVMe SUBNQN | 随 SN 改 | 固定厂家/型号前缀 + 实例 SN | nvme id-ctrl |
| NVMe EUI64 | 每盘不同 | 保留厂家前缀，其余随机 | nvme id-ns |
| NVMe NGUID / namespace UUID | 每 namespace 不同且互相一致 | NGUID=8-byte zero+EUI64；UUID 同一 128bit 值 | id-ns / descriptor list |
| 网卡 permanent MAC / NVM MAC | 每实例不同 | 参数 MAC 同时进入原版驱动的 NVM/收发模型；默认本地管理，支持指定 OUI | ip link / ethtool |
| IP / DHCP reservation / hostname | 同二层内不同 | 必须指定地址；audit 比较提供的清单 | ARP 冲突、真实路由与流量另测 |
| Portal LAN MAC / WAN 地址 / VMID | 新建路由器时独立 | 配置模板要求人工分配 | 同一个物理 WAN NIC 不能同时直通给两台 VM |
| EFI variables / Boot entries | 每实例独立 | create-vm.sh 创建新 efidisk，禁止共用源机 efidisk | 实际启动并核对启动项 |
| GPT disk GUID / 分区 PARTUUID | 克隆后应重新分配 | identity 生成值；新建 GPT 时自动写入 | 自动更新 fstab/GRUB/initramfs，再冷启动核对 |
| ext4 FS UUID / FAT volume ID | 克隆后盘级身份应独立 | ext4 UUID 与 FAT ID 均在 identity 中固定，新建文件系统时写入 | 块设备与全部启动引用一致 |
| Linux machine-id / D-Bus ID | 每实例不同 | 离线置空 machine-id，首启生成；D-Bus 路径链接至同一文件 | 重启后读取，勿在线复用原 machine-id |
| SSH host keys | 每实例不同 | 离线排除旧 host keys 并 ssh-keygen -A | 指纹应不同；账号 authorized_keys 由操作者审阅 |
| DHCP DUID / leases / NetworkManager UUID | 清理继承状态 | 提取时排除租约/NM 状态和旧 connection 文件；新静态 netplan | 新启动后检查运行配置 |
| Sunshine 证书 / UUID / 配对 / Web 凭据 | 每实例重新创建 | 不复制旧 sunshine 目录；每实例新建配置，不设置通用 Web 密码 | 新 Web 凭据、PIN 和真实客户端连接 |
| 账号密码 / sudo 规则 | 自行设置凭据，权限可复用 | 按参数创建账号/UID及免密 sudo；密码从管理端 0600 文件读取 | 首次 SSH 后核验 sudo -n |
| RTX3080 GPU UUID / SN / VBIOS | 来自实际直通设备 | 不篡改；新机器分配另一块可用 GPU | nvidia-smi；同一设备不能并发独占直通 |
| 物理 WAN NIC 序列/MAC | 来自实际设备 | 不篡改 | 实际 BDF、驱动与 IOMMU group |
| CPU Processor ID / CPUID 签名 | 同型号相同 | BFEBFBFF000B0671 等为型号/功能组合，不视为全球唯一 SN | 不人为改坏 CPUID 一致性 |
| PCI vendor/device/subsystem/revision | 同型号相同 | 保留 13900K/Z790/MSI/I225/KIOXIA 型号值 | PCI 树与绑定驱动 |
| SMBIOS handles / ACPI OEM/table ID | 同配置可相同 | 保留拓扑与引用；不是机器唯一编号 | 无重复句柄和悬空引用 |
| BIOS / ME firmware version / image hash | 同固件版本相同 | 用户自行提供 BIOS 文件；不生成虚假固件版本 | 只读 SPI hash 与版本查询；不是完整 CSME |
| USB2 Hub / ALC4080 SN | 当前描述符未声明 SN | 保留无序列号的设备描述；不杜撰 SN | 当前 usb2-hub 与 usb-alc4080 枚举核对 |
| root hub bus 名、PCI BDF、音频 card 编号 | 来自拓扑/枚举 | 不是全球唯一身份；card 编号允许变化 | 使用稳定设备路径/卡名 |
| 应用 token / VPN / 浏览器会话等 | 克隆前审阅或移除 | 不属于硬件生成器可穷举的状态 | Golden image 中不得包含个人会话 |

`audit` 只检查传入的身份文件，不查询整网、现有 PVE 或其他项目。每实例文件应进入私有 CMDB/受控备份，而不是公开 Git。随机值由 secrets/UUID 生成；若审计发现冲突，应为尚未部署的新实例重新生成，不能改正在运行的机器身份。
