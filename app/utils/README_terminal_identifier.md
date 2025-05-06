# 终端设备识别模块

本模块提供了用于识别和管理校园网终端设备信息的功能，通过分析MAC地址、用户代理字符串和主机名等信息，识别设备类型、操作系统、厂商等特征。

## 主要功能

1. **MAC地址OUI识别**：通过MAC地址的OUI前缀识别设备厂商
2. **用户代理解析**：解析HTTP请求中的User-Agent字符串，识别操作系统、浏览器和设备类型
3. **终端设备发现**：从网络设备采集MAC地址表，发现新的终端设备
4. **设备指纹管理**：维护终端设备特征的指纹数据库
5. **设备状态管理**：自动标记不活跃的终端设备

## 文件结构

- `terminal_identifier.py` - 主要功能实现文件
- `data/` - 数据目录
  - `oui.csv` - MAC地址OUI数据库
  - `fingerprints.csv` - 设备指纹数据库

## 使用方法

### 1. 初始化OUI数据库

```python
from app.utils.terminal_identifier import init_oui_database

# 初始化OUI数据库
init_oui_database()
```

### 2. 识别终端设备

```python
from app.utils.terminal_identifier import identify_terminal

# 通过MAC地址识别
terminal_data = {
    "mac_address": "00:1A:2B:3C:4D:5E"
}
result = identify_terminal(terminal_data)
print(f"设备类型: {result['device_type']}")
print(f"厂商: {result['vendor']}")

# 通过用户代理字符串识别
terminal_data = {
    "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/604.1"
}
result = identify_terminal(terminal_data)
print(f"设备类型: {result['device_type']}")
print(f"操作系统: {result['os_type']}")
print(f"浏览器: {result['browser']}")
```

### 3. 创建或更新终端设备

```python
from app.utils.terminal_identifier import create_or_update_terminal

terminal_data = {
    "mac_address": "00:1A:2B:3C:4D:5E",
    "ip_address": "192.168.1.100",
    "hostname": "user-laptop",
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

terminal = create_or_update_terminal(terminal_data)
```

### 4. 触发终端设备发现

```python
from app.utils.terminal_identifier import schedule_terminal_discovery

# 发现终端设备
result = schedule_terminal_discovery()
print(f"发现 {result['discovered']} 个设备")
print(f"{result['offline']} 个设备离线")
```

## 数据库结构

### OUI数据库 (oui.csv)

```
mac_prefix,vendor
000D93,Apple, Inc.
001121,Cisco Systems, Inc.
74D02B,ASUSTek COMPUTER INC.
...
```

### 指纹数据库 (fingerprints.csv)

```
mac_address,vendor,device_type,os_type,hostname,signature
00:11:22:33:44:55,Apple,Mobile,iOS,iPhone,Mozilla/5.0 (iPhone; CPU iPhone OS 14_4 like Mac OS X)
...
```

## 定时任务

终端设备识别模块通过调度器每15分钟自动运行一次终端设备发现任务，自动更新终端设备状态、识别新设备和标记离线设备。

## 扩展点

1. 增强设备类型识别规则
2. 添加DHCP和ARP数据收集方法
3. 实现更复杂的设备指纹识别算法
4. 集成网络行为分析功能 