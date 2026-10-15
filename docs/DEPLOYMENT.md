# 构建、批量生成与验收

Intel VMX/KVM、PVE QEMU 10.1.2 系列、Ubuntu 24.04 amd64。宿主内核未修改。Guest 为自构建 6.8.12-generic #6，使用 Ubuntu linux=6.8.0-147.147 源包和仓库锁定配置，不是 Canonical 原版二进制。

每台并发实例需要独占 GPU 及 HDMI 音频、64 GiB RAM、500 GiB 的 PVE lvmthin 存储、24 个 vCPU 亲和 CPU 和另选 I/O CPU。存储池、VFIO、LAN bridge、PortalWrt 和上游路由先准备好；工厂不清除物理盘或改 WAN。单张 GPU 可以显式顺序使用，原 VM 必须停止、新 VM 必须 onboot=0；禁止并发占用。

## 构建或取得运行包

独立 Ubuntu 24.04 构建环境执行，依赖和版本见各脚本与 PROVENANCE：

```bash
tools/build-qemu.sh
tools/build-ovmf.sh
tools/build-kernel.sh
```

也可使用 Release 的 runtime，包含 QEMU、OVMF、libjpeg 和许可证。Guest 内核 staging 需要相同 headers/Module.symvers 和 NVIDIA DKMS。Kbuild 固定 builder/build、版本 6、源包 changelog 时间，仍不承诺不同工具链的二进制完全一致。QEMU 的原始 tarball 与补丁均固定 SHA；MSI BIOS 和操作系统镜像由用户自行提供。

## 只读生成源文件集

源 VM 已安装所需 Ubuntu/KDE/SDDM/Xorg、内核与原版驱动、Sunshine。工厂复用这套软件包和运行文件，重新创建实例状态，不复制整盘。源 VM 停止后挂载 ro,noload，禁止日志回放：

```bash
sudo python3 tools/capture-source.py --vmid 100 \
  --out /var/lib/vmcc/seed --shutdown
```

`--shutdown` 是显式停机操作；不指定时要求源 VM 已停止。源盘只读，输出目录必须不存在。提取排除源用户目录、root 工程资料、日志、CI runner 环境、旧内核、SSH host keys、租约、Sunshine 配对等。源文件集也应保存在管理端私有目录，不上传公开库。

## 一次规划，批量创建

复制 `examples/batch.json`，填写目标主机路径、存储、bridge 和每台机器的 VMID、名称、账号/UID、静态地址、时区、GPU、CPU 亲和性及音频后端。示例有两张不同 GPU；当前主机只有一张时只保留一项。

```bash
./vmcc batch plan --spec /private/batch.json --out instances/batch-001
```

plan 只生成本地文件，包含独立身份、QEMU/SMBIOS/SPD 配置、磁盘身份和计划校验。查重失败不发布半成品计划。密码不在 JSON 或 Git 中：另外创建权限 0600 的密码文件，每行内容为该批次账号密码；分批可用不同密码文件。

```bash
sudo ./vmcc batch apply --plan instances/batch-001 \
  --password-file /private/account-password

sudo ./vmcc batch apply --plan instances/batch-001 \
  --password-file /private/account-password --apply --start
```

第一次为只读预检。第二次依次：复制临时 rootfs、离线重建账号和状态、新建 500 GiB 普通稀疏镜像、写入计划中的 GPT/PARTUUID/ext4/FAT ID、更新 fstab/GRUB/initramfs、分配新的 PVE thin volume、导入、注册专用启动器并创建 VM。`--start` 才启动。每台新建独立 EFI variables 盘。

如果 GPU 也在已停止源 VM 的配置中，显式加 `--allow-stopped-gpu-sharing`，并保持新实例 `onboot: 0`。预检拒绝运行中的设备归属、已有 VMID/登记、重复 GPU、无效 CPU/bridge/固件、容量不足和有响应的 IP。IP 探测不能证明所有休眠设备均无冲突，地址仍须由网络管理员预留。

`install-host.py` 保留 `/usr/bin/kvm.vmcc-original`，仅登记实例使用新 runtime，其他 VM 沿用现有启动器。已有 runtime 不同则拒绝覆盖。失败保留宿主回执和相关资源，不自动销毁或回退。只在分配磁盘前失败时可用 `--retry-before-allocation` 重做本计划的临时文件；分配资源后须按回执检查，禁止盲目重复执行。

成功导入后删除本批临时 rootfs 和 sparse image；保留管理端 identity、配置 bundle 与分配回执。新 Guest 不放置项目目录、身份清单、调参脚本、验证日志或克隆备份。

## 实机数据验收

先从源 VM 读取基线，再对每个新实例读取真实数据。采集程序通过 SSH stdin 执行，不安装进 Guest：

```bash
python3 tools/verify-instance.py --target user@SOURCE_IP \
  --out /private/baseline

python3 tools/verify-instance.py --target user@NEW_IP \
  --baseline /private/baseline/actual.json \
  --identity instances/batch-001/200/identity.json \
  --out /private/acceptance-200
```

SSH 参数可重复 `--ssh-option`，如 `--ssh-option BatchMode=yes` 或 `--ssh-option ProxyJump=root@PVE_IP`。账号须能 `sudo -n`。输出不可覆盖；结果写到管理端，不放公开 Git。非 PASS 退出码为 1。创建成功、能 SSH、Sunshine 监听均不能单独代替整体验收。

比较包括逐核 8P16E/24 线程、CPUID 功能、完整 PCI/原版驱动、SMBIOS 类型/句柄/内容（规范化唯一身份）、四条连号、ACPI、内核、内存、NVMe、GPU、唯一账号/SSH/machine-id、磁盘身份、网络、桌面/Sunshine/ROM 服务和残留。功能深入测试另用 `tools/probes/` 及报告中的外围测试方法。Sunshine 官方虚拟 HID 和 hypervisor bit=0 保持现有配置；SPD decode-dimms 对齐仍暂停。

Sunshine Web 需要每实例新设凭据并重新配对，不继承原机证书。监听 IPv4 0.0.0.0，TCP 47984/47989/47990/48010、UDP 47998–48000 规则持久化；不主动启用或改变防火墙默认策略。Moonlight 实际串流仍须真实客户端验收。

PortalWrt 可以共享现有路由器，每台 Ubuntu 用不同地址。新建路由器时见 `tools/render-portal.py`，另选 WAN NIC、WAN 地址和 LAN，并配置上游静态路由；WAN DHCP 禁止规则不能省略。

新 thin volume 导入仅在刚分配、没有 origin、data_percent=0 时使用 qemu-img `--target-is-zero`；不用于现有盘或快照。语义见 [QEMU 官方文档](https://www.qemu.org/docs/master/tools/qemu-img.html#cmdoption-qemu-img-convert-target-is-zero)。
