# 校园网络监控系统安装解决方案

## 依赖项安装问题解决

### 1. netifaces 安装失败

错误信息:
```
error: Microsoft Visual C++ 14.0 or greater is required. Get it with "Microsoft C++ Build Tools"
```

**解决方案**:

1. **方法一: 忽略此依赖（推荐）**
   
   我们已经在 requirements.txt 中注释掉了 netifaces 依赖，因为它主要用于网络接口数据采集，不影响系统的核心功能。直接跳过这个包的安装即可。

2. **方法二: 安装 Microsoft C++ Build Tools**

   如果您需要完整功能，可以安装 Microsoft C++ Build Tools：
   - 访问: https://visualstudio.microsoft.com/visual-cpp-build-tools/
   - 下载并安装 "Microsoft C++ Build Tools"
   - 在安装过程中选择 "C++ 构建工具" 组件
   - 安装完成后，重新运行 `pip install netifaces==0.11.0`

### 2. 数据可视化库问题

由于原项目使用的 flask-echarts 和 pyecharts-flask 包不可用，我们提供了以下替代方案：

1. 现在使用直接的 pyecharts 库创建图表
2. 添加了 Flask-Bootstrap 和 Flask-jsglue 支持前端展示
3. 提供了 `data_visualization_guide.py` 文件，包含创建各种图表的示例代码

如果您遇到数据可视化方面的问题，请参考 `data_visualization_guide.py` 文件中的示例代码。

## 运行步骤

1. **安装依赖**:
   ```bash
   pip install -r requirements.txt
   ```

2. **准备数据库**:
   ```sql
   CREATE DATABASE campus_network_dev;
   ```
   确保数据库用户名和密码与 `.env` 文件中的配置一致。

3. **运行应用**:
   ```bash
   python start_app.py
   ```

4. **访问应用**:
   - 打开浏览器访问: http://localhost:5000
   - 管理员账号: admin / admin
   - 普通用户账号: user / password

## 项目代码结构

- `app/`: 应用主目录
  - `models/`: 数据模型定义
  - `controllers/`: 控制器和路由
  - `templates/`: HTML 模板
  - `static/`: 静态资源文件
- `config/`: 配置文件
- `data_visualization_guide.py`: 数据可视化指南和示例
- `init_sample_data.py`: 示例数据初始化脚本
- `start_app.py`: 应用启动脚本

## 常见运行问题解决

1. **端口冲突**:
   如果 5000 端口被占用，可以修改 `start_app.py` 中的端口号:
   ```python
   app.run(host='0.0.0.0', port=5001, debug=True)
   ```

2. **数据库连接错误**:
   - 确保 MySQL 服务正在运行
   - 检查用户名和密码是否正确
   - 确保已创建 `campus_network_dev` 数据库

3. **页面显示异常**:
   如果页面显示不正常，可能是数据可视化组件有问题，尝试使用 Chart.js 方案（参考 `data_visualization_guide.py`）。 