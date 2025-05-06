# 校园网络监控系统用户手册

## 目录

1. [系统简介](#系统简介)
2. [安装与配置](#安装与配置)
   - [系统要求](#系统要求)
   - [安装步骤](#安装步骤)
   - [配置数据库](#配置数据库)
3. [SNMP协议配置](#SNMP协议配置)
   - [路由器/交换机配置](#路由器交换机配置)
   - [系统SNMP配置](#系统SNMP配置)
4. [设备管理](#设备管理)
   - [添加设备](#添加设备)
   - [编辑设备](#编辑设备)
   - [删除设备](#删除设备)
5. [数据采集](#数据采集)
   - [自动采集](#自动采集)
   - [手动采集](#手动采集)
6. [流量监控](#流量监控)
   - [实时监控](#实时监控)
   - [历史数据](#历史数据)
   - [流量热力图](#流量热力图)
7. [终端管理](#终端管理)
   - [终端识别](#终端识别)
   - [终端状态监控](#终端状态监控)
8. [告警管理](#告警管理)
   - [告警配置](#告警配置)
   - [告警通知](#告警通知)
9. [命令行工具](#命令行工具)
   - [测试SNMP连接](#测试SNMP连接)
   - [添加设备工具](#添加设备工具)
   - [数据采集工具](#数据采集工具)
10. [常见问题解答](#常见问题解答)

## 系统简介

校园网络监控系统是一个基于Web的网络设备监控平台，用于监控校园网络中的路由器、交换机、服务器等设备的状态和流量。系统使用SNMP协议采集设备数据，并使用ECharts等可视化工具展示网络流量和设备状态。

主要功能包括：
- 设备状态监控
- 网络流量实时监控
- 流量历史数据分析
- 流量热力图
- 终端设备管理
- 告警管理

## 安装与配置

### 系统要求

- Python 3.8+
- MySQL 5.7+ 或 SQLite
- 现代浏览器（Chrome, Firefox, Safari, Edge等）

### 安装步骤

1. 克隆项目代码：
   ```bash
   git clone https://github.com/yourusername/campus_network_monitor.git
   cd campus_network_monitor
   ```

2. 创建并激活虚拟环境：
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Linux/Mac
   source venv/bin/activate
   ```

3. 安装依赖包：
   ```bash
   pip install -r requirements.txt
   ```

4. 初始化数据库：
   ```bash
   python reset_db.py
   ```

5. 启动应用：
   ```bash
   python start_app.py
   ```

6. 访问网页：
   打开浏览器，访问 http://localhost:5000

### 配置数据库

系统默认使用SQLite数据库，如需使用MySQL等其他数据库，请修改`config.py`文件：

```python
# SQLite配置
SQLALCHEMY_DATABASE_URI = 'sqlite:///app.db'

# MySQL配置示例
# SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://username:password@localhost/dbname'
```

## SNMP协议配置

### 路由器/交换机配置

在使用系统采集设备数据前，需要在网络设备上启用SNMP功能。以下是常见设备的SNMP配置方法：

#### Cisco设备

```
enable
configure terminal
snmp-server community public RO
snmp-server location Campus Building A
snmp-server contact admin@example.com
end
write memory
```

#### H3C设备

```
system-view
snmp-agent
snmp-agent community read public
snmp-agent sys-info location "Campus Building A"
snmp-agent sys-info contact admin@example.com
quit
save
```

#### 华为设备

```
system-view
snmp-agent
snmp-agent community read public
snmp-agent sys-info location Campus Building A
snmp-agent sys-info contact admin@example.com
quit
save
```

### 系统SNMP配置

系统需要安装PySNMP和相关依赖：

```bash
pip install pysnmp
```

确保防火墙允许SNMP流量通过（UDP端口161）。

## 设备管理

### 添加设备

#### 通过Web界面添加

1. 登录系统
2. 点击"设备管理"
3. 点击"添加设备"按钮
4. 填写设备信息：
   - 设备名称
   - IP地址
   - 设备类型
   - 位置
   - SNMP配置（Community、版本、端口）
5. 点击"保存"按钮

#### 通过命令行工具添加

使用`add_device.py`工具添加设备：

```bash
python add_device.py 192.168.1.1 --name "Core Router" --type "路由器" --location "数据中心" --community "public" --version "2c"
```

参数说明：
- `192.168.1.1`: 设备IP地址（必须）
- `--name`: 设备名称（可选，默认使用IP地址）
- `--type`: 设备类型（可选，默认为交换机）
- `--location`: 设备位置（可选）
- `--description`: 设备描述（可选）
- `--port`: SNMP端口（可选，默认161）
- `--community`: SNMP community（可选，默认public）
- `--version`: SNMP版本（可选，默认2c）
- `--no-check`: 不检查SNMP连接（可选）
- `--force`: 强制添加设备，即使SNMP连接失败（可选）

### 编辑设备

1. 在设备列表中找到要编辑的设备
2. 点击"编辑"按钮
3. 修改设备信息
4. 点击"保存"按钮

### 删除设备

1. 在设备列表中找到要删除的设备
2. 点击"删除"按钮
3. 确认删除操作

## 数据采集

### 自动采集

系统默认每5分钟自动采集一次设备数据。采集频率可在`app/utils/scheduler.py`文件中修改：

```python
def init_scheduler():
    """初始化调度器并添加定时任务"""
    from app.utils.snmp_collector import poll_all_devices
    
    # 每5分钟执行一次数据采集
    scheduler.add_job(
        poll_devices,
        'interval',
        minutes=5,
        id='collect_data',
        replace_existing=True
    )
```

### 手动采集

#### 通过Web界面采集

1. 进入设备详情页
2. 点击"采集数据"按钮

#### 通过命令行工具采集

使用`collect_data.py`工具手动采集数据：

```bash
# 采集所有设备数据
python collect_data.py

# 采集指定设备数据（按ID）
python collect_data.py --device 1

# 采集指定设备数据（按IP）
python collect_data.py --device 192.168.1.1

# 安静模式，只显示错误信息
python collect_data.py -q
```

## 流量监控

### 实时监控

实时监控页面显示设备当前的流量数据，包括：
- 总流量
- 入站流量
- 出站流量
- 带宽利用率

数据每30秒自动刷新一次。

### 历史数据

历史数据页面可以查看设备的历史流量数据，支持以下功能：
- 选择时间范围（1小时、6小时、1天、7天、30天）
- 查看特定时间段的平均流量
- 下载历史数据报表

### 流量热力图

流量热力图直观地显示网络中各设备的流量状况，包括：
- 设备位置分布
- 流量负载级别（低、中、高）
- 点击设备可查看详细信息

## 终端管理

### 终端识别

系统通过以下方式识别网络中的终端设备：
- SNMP查询设备MAC地址表
- 分析ARP表和路由表
- 识别终端操作系统类型和设备类型

### 终端状态监控

终端管理页面显示以下信息：
- 终端总数
- 在线/离线终端数
- 各类型终端数量
- 终端详细列表（包括ID、主机名、IP地址、MAC地址、设备类型、操作系统类型、状态等）

## 告警管理

### 告警配置

系统支持以下类型的告警：
- 设备离线告警
- 带宽利用率超阈值告警
- CPU/内存使用率超阈值告警
- 接口状态变化告警

告警阈值可在系统设置中配置。

### 告警通知

告警发生时，系统提供以下通知方式：
- Web界面显示
- 邮件通知
- 短信通知（需配置短信服务）

## 命令行工具

### 测试SNMP连接

使用`test_snmp.py`工具测试SNMP连接：

```bash
# 测试基本连接和系统信息
python test_snmp.py 192.168.1.1 --community public --version 2c --test basic

# 测试接口信息
python test_snmp.py 192.168.1.1 --community public --version 2c --test interfaces

# 测试资源信息（CPU、内存）
python test_snmp.py 192.168.1.1 --community public --version 2c --test resources
```

### 添加设备工具

参见[通过命令行工具添加](#通过命令行工具添加)章节。

### 数据采集工具

参见[通过命令行工具采集](#通过命令行工具采集)章节。

## 常见问题解答

### Q: 无法连接到设备SNMP，应该如何排查？

A: 请检查以下几点：
1. 确认设备IP地址是否正确
2. 确认SNMP配置是否正确（Community、版本、端口）
3. 检查设备防火墙是否允许SNMP流量
4. 使用`test_snmp.py`工具测试SNMP连接
5. 确认网络连接是否正常

### Q: 系统采集数据频率如何调整？

A: 编辑`app/utils/scheduler.py`文件，修改`minutes=5`参数为需要的时间间隔。

### Q: 如何备份系统数据？

A: 系统使用SQLite数据库时，只需备份`app.db`文件。使用MySQL等其他数据库时，请使用相应的数据库备份工具。

### Q: 系统支持哪些SNMP版本？

A: 系统支持SNMPv1和SNMPv2c。

### Q: 如何自定义告警阈值？

A: 登录系统后，进入"系统设置"页面，在"告警设置"部分可以配置各种告警的阈值。 