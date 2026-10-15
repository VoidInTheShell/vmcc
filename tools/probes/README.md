# 独立原始探针

这些程序读取真实 CPUID / Linux 原版驱动接口，不修改检测软件。编译和输出放在管理端或 Guest 临时目录，测试后删除；不要把工程文件留在部署镜像。

```bash
cc -O2 topology.c -o /tmp/topology
cc -O2 cpuid.c -o /tmp/cpuid
cc -O2 server-features.c -o /tmp/server-features
cc -O2 mei.c -o /tmp/mei
cc -O2 serialio.c -o /tmp/serialio
```

`topology` 检查本项目 24 线程、8P16E、HT 关闭和缓存关系。`cpuid` 保留逐核枚举与原始开销；TSC 周期不等于 wall clock 或 CPU 性能。`server-features` 需要 root、原版 msr 模块和 /dev/cpu/*/msr，读取服务器平台特征，不启用不受支持的指令。

`mei` 连接本模型的 MKHI client，发送八次版本查询。`serialio I2C_DEVICE UART_DEVICE` 检查空 I²C 地址 NACK 与 UART 内部回环；必须选本项目 Serial IO 控制器，UART 不得被其他程序占用。其环境变量 `I2C_EEPROM_TEST` 只用于隔离的临时测试 EEPROM，会写入地址 0x50，禁止对实体 SPD 或在用设备启用。正式镜像不启用该变量。

每项程序的 PASS 只覆盖其明示检查。外围模型的完整功能、时序和电气行为边界见主报告。
