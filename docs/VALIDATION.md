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

代码语法、3项工具测试和新实例启动验证均已运行。脚本参数化后，以下**尚未运行**：在另一台 PVE 使用 install-host --apply 新建完整 VM、完整新克隆 KDE/RTX3080/NVMe/PortalWrt 联合验收、泛化 Sunshine 安装器的重启/Moonlight验收、参数化 fresh-disk 与完整内核重新构建、GPT/FS 规划UUID的离线应用。部署说明保留这些门槛，不将其写成一键完成。

独立实例测试仅验证身份机制和该配置可引导；新实例不能沿用原机 VMAware、时序、网络或 GPU 验收结果。
