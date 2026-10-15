# 验收与测试范围

## 原机结果

外围整机验收窗口为 2026-10-14 14:14 EDT 的冷启动。Sunshine 为随后 20:33 EDT 记录的另一次重启；没有把两次 boot ID 合成同一次完整验收。公开原始输出选摘在 validation，原始工作区仍保留完整日志。

| 项目 | 结果 | 边界 |
|---|---|---|
| 13900K 拓扑 | 8P+16E，24c24t，SMT off；逐核审计通过 | 不等于实体 13900K 性能 |
| 主板 | 55 Type8 / 9 Type9 / 15 Type41 / 25 有效引用；10 张常规 ACPI 校验通过 | 记录接口不代表全部电路实现 |
| 原版 VMAware v2.8.2 | 1/84、45%、confirmation=false；THREAD_MISMATCH | 该 release 按默认32线程比较；没有把输出改成0 |
| 原版上游固定提交 | 0/85、0%、confirmation=false | 与发布版测试总数/规则不同，不当成同口径改善百分比 |
| 时序 | 24×1000 CPUID：P50 2148–2561、P99 2291–6876 cycles；backwards0 | CPUID 开销仍有缺口；零命中不代表时序过关 |
| I225-V / 网络 | 原版 igc；ping/DNS/HTTPS 实包 | PTP/TSN 等未完整实现 |
| USB / SATA | 四档 USB 枚举与盘写读；6 空 SATA 端口可见、接盘6Gb/s写读 | 不代表20G实体吞吐/PD/DP |
| 音频 | xHCI 修复前3/3跳过，修复后39/39恢复正确；26次录音+3组双工无TRB错误 | 完整DSP/HID与长期压力未验收 |
| SPI / Serial IO / MEI / SRAM | 完整32MiB读hash；原版驱动写读/回环/版本查询通过 | 不执行实体BIOS/完整CSME，不虚报iDMA |
| Guest kernel | 原机generic#5真实启动；额外内核源码差异0 | 构建配置和模块不同于 Ubuntu 发行内核 |
| RTX3080 / KDE | NVIDIA OpenGL/Vulkan 实际渲染，SDDM active | 无 UHD770 身份伪装；实体显卡直通 |
| Sunshine | 未登录KDE重启自动active/running、NRestarts0；H.264/HEVC NVENC探测通过 | Moonlight真实端到端串流/音频/手柄未验收 |
| SPD | 四条 EEPROM 散列保留 | decode-dimms 对齐按用户要求暂停 |

## 新复用包实测

1. 原始 QEMU 10.1.2 tarball 通过固定 SHA 校验；两份补丁以 fuzz=0 应用并完整编译，1792 个构建步骤完成。新二进制 SHA 见 PROVENANCE。
2. 100 组独立身份查重，无 system/board/chassis/NVMe/MAC/DIMM 等碰撞；每机四条 DIMM 连续。SMBIOS Type17 和对应 SPD SN 一致，SPD 其余字节与模板相同；输出目录重用被拒绝。
3. 两个隔离 QEMU 启动进程使用同一新二进制、不同生成 bundle，通过 UEFI、原机 Guest 内核与只读 BusyBox initramfs实际启动。无正式盘、GPU 或网络接入。各自 system UUID/system SN/board SN/chassis SN、四条 EEPROM SN 和24个CPU读取全部符合清单；原始日志见 vmcc-smoke-a.log、vmcc-smoke-b.log。
4. 外部 SPD 为错误长度时 QEMU 拒绝启动并报告必须2048字节；避免默默复用另一个实例的 SPD。
5. 未登记 VMID 原样链到原 launcher 的执行路径通过测试。
6. 原机 QEMU SHA 仍为4369c050…，VM100/101仍运行；没有将测试构建安装回原机。

## 批量工厂实测（2026-10-15）

- 原机重编译并启动 #6，builder@build；去除串口启动参数。NVIDIA、SDDM、Sunshine、ROM 资源恢复服务实际重启 active。
- 从停止的原 VM 只读提取 7.9 GiB 文件集，创建两台各 500 GiB 的新 VM；同一张 RTX3080 顺序使用，禁止并发。两台使用不同 SN/UUID/MAC/IP、GPT/PARTUUID/ext4/FAT ID、machine-id 和 SSH host keys，只有指定桌面账号。
- 第一实例首次检查发现三处 OCI 来源文件残留，修正规则后通过；清理后及重启后均为 35/35。保留首次 FAIL 记录在私有工作区，不隐去调试事实。
- 第二实例使用修正后的工厂全流程生成，无需 Guest 内手工修补，首次与重启后均为 35/35。原始比较结果去除身份后保存为 `validation/factory-201.json`；第一实例重启结果为 `factory-200-reboot.json`。
- 对比读取实际逐核 CPUID、25 个 PCI 设备/驱动、102 条 SMBIOS（规范化唯一身份后）、10 张常规 ACPI、内核 hash、DIMM 连号、NVMe、GPU、内存、网络与账号/文件状态；不是只比较生成配置。
- 两台实际 OpenGL 4.6 direct rendering 使用 NVIDIA GeForce RTX3080；第二实例经 PortalWrt 的 HTTPS 请求返回 200。Sunshine 未登录自启并监听四个 IPv4 any TCP 端口；没有真实 Moonlight 客户端，串流仍 NOT RUN。
- 8 项工具测试（含 100 组身份生成）、Python compileall、shell 语法与入口调用检查通过。新 thin volume 优化导入后占用约 1.72%，而非把 500 GiB 空白写满。

完整重新构建 QEMU/OVMF 属于此前 v0.1.0 验收；本轮复用相同运行包。#6 内核为既有锁定源树的增量构建，完整内核从零构建没有重复执行。新主机、新 GPU、另一种 PVE 版本、真实 Moonlight、长期外围压力与 cpufreq 后端仍未验证。

35/35 表示与当前硬件基线及干净实例规则对齐，不表示虚拟化不可检测。CPUID 时序、宿主缺少的指令及外围模型功能边界继续保留。新实例另行运行相同未修改的 VMAware 固定提交，二进制 SHA256 `734a78a947f393b6e72638f437053898ec914df93bc452d36e504fdd6aa54a7a`；本次 0/85、0%、confirmation=false，原始输出见 `validation/factory-201-vmaware-all.txt`。临时程序退出自动删除，输出只在管理端。
