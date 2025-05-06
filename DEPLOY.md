# 校园网络监控系统部署指南

## 环境要求

- Python 3.8+
- MySQL/SQLite
- 网络设备支持SNMP

## 安装步骤

1. 克隆代码库
```bash
git clone <repository-url>
cd campus_network_monitor
```

2. 创建虚拟环境并安装依赖
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

3. 配置环境变量
```bash
# Linux/Mac
export FLASK_APP=run.py
export FLASK_DEBUG=1  # 开发环境使用

# Windows
set FLASK_APP=run.py
set FLASK_DEBUG=1
```

4. 初始化数据库
```bash
flask init_db
```

## 终端识别模块部署

1. 确保数据库中有终端设备表的vendor和user_agent字段
```bash
python migrations/add_terminal_fields.py
```

2. 检查数据目录是否存在
```bash
mkdir -p app/utils/data
```

3. 更新OUI数据库（可选，系统会自动下载）
```bash
# 可以手动更新OUI数据库
# 从IEEE获取: https://standards-oui.ieee.org/oui/oui.csv
# 保存到app/utils/data/oui.csv
```

## 运行系统

1. 启动应用
```bash
python run.py
```

2. 访问Web界面
```
http://localhost:5000
```

3. 默认管理员账号
- 用户名: admin
- 密码: admin123

## 定时任务

系统启动后会自动运行以下定时任务：
- 每5分钟采集一次设备流量数据
- 每15分钟发现一次终端设备并更新状态

## 手动操作

- 终端设备发现: 在终端设备管理页面点击"发现终端设备"按钮
- 终端设备识别: 在终端设备管理页面点击"识别设备"按钮，输入MAC地址或用户代理字符串

## 故障排除

1. 如果OUI数据库下载失败
```bash
# 手动下载并保存到数据目录
curl -o app/utils/data/oui.csv https://standards-oui.ieee.org/oui/oui.csv
```

2. 如果终端设备识别功能不工作
```bash
# 检查user-agents库是否安装
pip install user-agents

# 检查数据库字段是否添加
python migrations/add_terminal_fields.py
```

3. 如果调度器任务失败
```bash
# 检查日志
tail -f logs/app.log

# 手动触发任务
python -c "from app import app; from app.utils.terminal_identifier import schedule_terminal_discovery; with app.app_context(): schedule_terminal_discovery()"
``` 