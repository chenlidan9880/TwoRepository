# 校园网流量可视化系统

一个基于Flask的校园网流量可视化系统，用于实时监控网络流量、检测异常流量、识别终端设备类型等。

## 功能特点

- **实时流量监控**: 通过SNMP协议采集网络设备流量数据，实时展示网络流量分布情况
- **异常流量告警**: 基于流量特征分析，识别异常流量行为，并及时发出告警信息
- **用户终端识别**: 识别接入校园网的终端设备类型，为网络管理提供更细粒度的信息
- **数据可视化**: 利用ECharts对网络流量数据进行可视化展示，包括热力图、趋势图等

## 系统架构

系统采用B/S架构，主要包含以下模块：
- 数据采集模块
- 数据处理模块
- 特征分析模块
- 可视化展示模块
- 告警模块

## 环境要求

- Python 3.6+
- 支持SNMP的网络设备
- MySQL 5.7+

## 快速开始

1. 克隆项目
```
git clone https://github.com/yourusername/campus_network_monitor.git
cd campus_network_monitor
```

2. 安装依赖
```
pip install -r requirements.txt
```

3. 配置MySQL数据库
```
# 创建MySQL数据库
mysql -u root -p
CREATE DATABASE campus_network_dev;
CREATE DATABASE campus_network_test;
CREATE DATABASE campus_network_prod;
```

4. 创建.env文件
```
# 复制示例环境文件
cp .env.example .env
# 编辑.env文件，填入你的MySQL用户名和密码
```

5. 初始化数据库
```
flask init-db
```

6. 启动服务
```
python run.py
```

7. 访问系统
```
http://localhost:5000
```

## 配置说明

系统配置文件位于`config`目录下：
- `config.py`: 主配置文件，包含数据库连接信息、SNMP参数等
- `.env`: 环境变量配置文件（需要自行创建，可复制.env.example）

## 开发者

- 您的名字 