# 校园网络监控系统运行指南

## 项目概述

本项目是一个基于 Flask 框架开发的校园网络监控系统，用于监控校园网络设备、流量、终端和异常情况。系统使用 MySQL 数据库存储数据，通过 Web 界面展示网络监控信息。

## 环境要求

- Python 3.8 或更高版本
- MySQL 5.7 或更高版本
- 虚拟环境（推荐使用）

## 安装与运行步骤

### 1. 准备 MySQL 数据库

1. 确保 MySQL 数据库服务正在运行
2. 创建名为 `campus_network_dev` 的数据库：
   ```sql
   CREATE DATABASE campus_network_dev;
   ```
3. 确保数据库用户名和密码与 `.env` 文件中配置的一致（默认为 root/123456）

### 2. 安装依赖项

在项目根目录下运行以下命令安装所有依赖项：

```bash
pip install -r requirements.txt
```

如果某些包安装失败，可以尝试单独安装重要的依赖：

```bash
pip install Flask==2.2.3 Flask-Login==0.6.2 Flask-SQLAlchemy==3.0.3 PyMySQL==1.0.3 mysqlclient==2.1.1 Flask-Migrate==4.0.4 pyecharts==2.0.3 Flask-Bootstrap==3.3.7.1 python-dotenv==1.0.0 APScheduler==3.10.1
```

### 3. 运行应用

方法一：使用 start_app.py 脚本（推荐）

```bash
python start_app.py
```

此脚本会自动执行以下操作：
- 创建数据库表（如果不存在）
- 初始化示例数据
- 启动 Web 应用

方法二：分步执行

```bash
# 初始化数据库
flask init-db

# 初始化示例数据
python init_sample_data.py

# 启动应用
flask run --host=0.0.0.0 --port=5000
```

### 4. 访问应用

启动应用后，打开浏览器访问：http://localhost:5000

可以使用以下账号登录：
- 管理员账号：
  - 用户名：admin
  - 密码：admin
- 普通用户账号：
  - 用户名：user
  - 密码：password

## 数据库信息

本项目仅使用 MySQL 数据库，主要数据模型包括：
- User：用户模型
- Device：设备模型
- Traffic：流量记录模型
- Alert：告警模型
- Terminal：终端模型

## 数据可视化特别说明

由于原项目依赖的数据可视化库（flask-echarts 和 pyecharts-flask）不可用，我们已经提供了替代方案：

1. 新增了 `data_visualization_guide.py` 文件，其中包含：
   - 使用标准 pyecharts 创建各种图表的函数
   - 在 Flask 视图中使用这些函数的示例代码
   - 使用 Chart.js 作为替代方案的示例代码

2. 要使用这些图表，您可以：
   - 将 `data_visualization_guide.py` 中的函数复制到您的应用中
   - 按照示例代码修改您的视图函数
   - 更新模板以显示图表

3. 所需依赖：
   - pyecharts==2.0.3：Python 图表库
   - Flask-Bootstrap==3.3.7.1：提供 Bootstrap 样式支持
   - Flask-jsglue==0.3.1：用于前端 JavaScript 整合

## 常见问题解决

1. **遇到 "No module named xxx" 错误**：
   确保所有依赖都已正确安装。如果某个包安装失败，可以单独安装：
   ```bash
   pip install xxx
   ```

2. **数据库连接失败**：
   - 检查 MySQL 服务是否启动
   - 检查用户名和密码是否正确
   - 检查数据库是否已创建
   - 对于 Windows 用户，可能需要安装 Visual C++ Redistributable

3. **无法显示数据可视化图表**：
   参考 `data_visualization_guide.py` 文件中的示例，使用标准 pyecharts 或 Chart.js 替代原来的可视化方案。

4. **netifaces 安装失败**：
   如果 netifaces 安装失败，可以尝试：
   ```bash
   pip install --upgrade setuptools wheel
   pip install --no-binary :all: netifaces
   ```
   如果还是失败，可以考虑注释掉 requirements.txt 中的这一行，因为它主要用于网络接口数据采集，不影响核心功能。 