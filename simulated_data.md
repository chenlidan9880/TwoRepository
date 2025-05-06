# 校园网络监控系统模拟数据生成指南

本文档详细介绍校园网络监控系统中用于生成模拟数据的各种脚本和工具，帮助开发者和部署人员理解如何创建测试环境和模拟真实网络状况。

## 目录

1. [概述](#概述)
2. [终端数据生成脚本](#终端数据生成脚本)
3. [流量数据模拟脚本](#流量数据模拟脚本)
4. [运行指南](#运行指南)
5. [脚本定位与区别](#脚本定位与区别)
6. [注意事项](#注意事项)
7. [故障排除](#故障排除)
8. [最佳实践](#最佳实践)

## 概述

校园网络监控系统需要大量真实的终端数据和流量数据才能进行有效的测试和演示。系统提供了多个脚本来模拟不同类型的数据：

- **终端设备数据**：包括PC、笔记本、服务器、移动设备等各种终端类型
- **网络设备数据**：路由器、交换机、无线AP等网络设备
- **流量数据**：模拟各种网络设备和终端之间的流量情况
- **告警数据**：基于阈值生成的告警信息

## 终端数据生成脚本

### 1. init_sample_data.py

**功能**：初始化基础示例数据，包括用户、设备、终端和告警数据

**终端数据生成特点**：
- 生成50个随机终端设备
- 随机分配不同的终端类型（PC、笔记本、服务器、平板、手机）
- 随机生成MAC地址和分配IP地址
- 为每个终端随机选择操作系统类型
- 随机设置入站和出站流量（500,000-5,000,000字节范围）
- 为终端随机分配物理位置和连接的网络设备

**代码示例**：
```python
# 随机生成50个终端
for i in range(1, 51):
    ip_last = i + 100  # 从192.168.1.101开始
    mac_addr = ':'.join([f'{random.randint(0, 255):02x}' for _ in range(6)])
    terminal_type = random.choice(terminal_types)
    os_name = random.choice(os_list)
    
    # 按照终端类型选择位置
    location = random.choice(['教学楼', '实验室', '办公室', '宿舍', '图书馆'])
    
    # 随机连接到一个设备上
    device = random.choice(devices)
    
    terminal = Terminal(
        mac_address=mac_addr,
        ip_address=f"192.168.1.{ip_last}",
        hostname=f"HOST-{i:03d}",
        device_type=terminal_type,
        os_type=os_name,
        is_active=True,
        first_seen=now - timedelta(days=random.randint(1, 30)),
        last_seen=now - timedelta(minutes=random.randint(0, 120)),
        in_traffic=random.randint(500000, 5000000),
        out_traffic=random.randint(500000, 5000000)
    )
    db.session.add(terminal)
```

### 2. init_db.py

**功能**：初始化数据库结构并添加基础数据

**终端数据生成特点**：
- 创建预定义的示例终端（学生PC、教师笔记本、实验室电脑等）
- 设置固定的IP地址和MAC地址
- 根据终端状态（online/offline）设置is_active属性
- 创建终端的时间戳记录（first_seen、last_seen等）

**代码示例**：
```python
# 添加示例终端
terminals = [
    {
        'hostname': 'student-pc-001',
        'ip_address': '192.168.10.1',
        'mac_address': '00:1A:2B:3C:4D:5E',
        'device_type': '个人电脑',
        'os_type': 'Windows',
        'status': 'online',
        'location': '学生宿舍'
    },
    # 更多终端...
]

for terminal in terminals:
    t = Terminal(
        hostname=terminal['hostname'],
        ip_address=terminal['ip_address'],
        mac_address=terminal['mac_address'],
        device_type=terminal['device_type'],
        os_type=terminal['os_type'],
        is_active=terminal['status'] == 'online',
        location=terminal['location'],
        first_seen=datetime.now() - timedelta(days=7),
        last_seen=datetime.now() if terminal['status'] == 'online' else datetime.now() - timedelta(days=1),
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    db.session.add(t)
```

### 3. add_test_data.py

**功能**：添加更多测试数据，用于扩充现有数据库

**终端数据生成特点**：
- 添加特定命名的测试终端设备
- 将终端与已存在的网络设备关联
- 设置详细的终端信息（包括厂商、连接设备等）
- 自动设置终端的活跃状态

**代码示例**：
```python
terminals = [
    {
        'hostname': 'student-pc1',
        'mac_address': '00:1A:2B:3C:4D:5E',
        'ip_address': '192.168.10.101',
        'device_type': 'PC',
        'os_type': 'Windows',
        'vendor': 'Dell',
        'connected_device_id': device_ids[0] if len(device_ids) > 0 else None,
        'status': 'online',
        'location': '计算机学院机房'
    },
    # 更多终端...
]

for terminal_data in terminals:
    terminal = Terminal.query.filter_by(mac_address=terminal_data['mac_address']).first()
    if not terminal:
        terminal = Terminal(**terminal_data)
        terminal.created_at = datetime.now()
        terminal.updated_at = datetime.now()
        terminal.last_seen = datetime.now()
        terminal.is_active = True
        db.session.add(terminal)
```

### 4. network_topology_generator.py

**功能**：生成完整的校园网络拓扑结构，包括核心设备、汇聚层设备、接入层设备和终端设备

**终端数据生成特点**：
- 基于校园不同区域（教学楼、宿舍、图书馆等）创建终端
- 自动连接终端到相应的网络设备
- 根据终端类型分配不同的流量特征和带宽使用
- 创建VLAN和端口信息
- 生成真实的用户代理字符串

**代码示例**：
```python
def create_terminal(hostname, ip_address, mac_address, device_type, os_type, vendor, connected_device, location):
    """创建并添加新的终端设备"""
    terminal = Terminal(
        hostname=hostname,
        ip_address=ip_address,
        mac_address=mac_address,
        device_type=device_type,
        os_type=os_type,
        vendor=vendor,
        connected_device_id=connected_device.id,
        is_active=random.random() > 0.2,  # 80%概率在线
        location=location,
        connection_type="wireless" if connected_device.device_type == "wireless" else "wired",
        port_number=f"Gi0/{random.randint(1, 24)}" if connected_device.device_type == "switch" else None,
        vlan_id=str(random.randint(10, 50)) if connected_device.device_type == "switch" else None,
        user_agent=generate_user_agent(device_type, os_type, vendor)
    )
    
    # 根据终端类型分配不同的流量数据
    if device_type == "PC":
        in_traffic = random.randint(50000000, 5000000000)  # 50MB-5GB
        out_traffic = random.randint(10000000, 1000000000)  # 10MB-1GB
    elif device_type == "Mobile":
        in_traffic = random.randint(10000000, 1000000000)  # 10MB-1GB
        out_traffic = random.randint(5000000, 500000000)  # 5MB-500MB
    else:  # IoT设备
        in_traffic = random.randint(1000000, 100000000)  # 1MB-100MB
        out_traffic = random.randint(500000, 50000000)  # 500KB-50MB
    
    terminal.in_traffic = in_traffic
    terminal.out_traffic = out_traffic
    terminal.bandwidth_usage = random.uniform(0.01, 0.5)  # 1%-50%
    terminal.first_seen = datetime.now() - timedelta(days=random.randint(1, 30))
    terminal.last_seen = datetime.now() - timedelta(minutes=random.randint(0, 120))
    
    db.session.add(terminal)
    return terminal
```

## 流量数据模拟脚本

### 1. advanced_traffic_generator.py

**功能**：使用高级统计模型生成真实的网络流量数据

**流量数据生成特点**：
- 基于ARIMA和GARCH统计模型生成流量波动
- 模拟工作日/周末和一天中不同时段的流量差异
- 为设备生成多个接口的流量数据
- 计算带宽利用率、错误包率等指标
- 能够生成长时间范围（如7天）的历史数据
- 更新终端设备的流量数据

**代码示例**：
```python
def generate_advanced_traffic(days=7, samples_per_hour=12, clear_existing=True):
    """生成基于复杂统计模型的高级流量数据
    
    使用ARIMA和GARCH模型生成符合真实网络特性的流量波动
    """
    app = create_app()
    with app.app_context():
        # 获取所有设备
        devices = Device.query.all()
        terminals = Terminal.query.all()
        
        # 为设备生成流量数据
        for device in devices:
            # 基于设备类型确定基础流量特征
            base_traffic = setup_base_traffic_pattern(device.device_type)
            
            # 生成ARIMA预测的基础趋势
            n_samples = samples_per_hour * 24 * days
            trend_data = generate_arima_trend(n_samples)
            
            # 生成GARCH波动率模拟的噪声
            volatility_data = generate_garch_volatility(n_samples)
            
            # 为设备生成流量数据
            generate_device_traffic(device, start_time, end_time, 
                                   samples_per_hour, base_traffic, 
                                   trend_data, volatility_data)
            
        # 为终端设备生成流量数据
        for terminal in terminals:
            # 根据终端类型定义流量模式
            terminal_traffic = generate_terminal_traffic_pattern(terminal.device_type)
            
            # 更新终端流量统计
            update_terminal_traffic(terminal, terminal_traffic)
```

### 2. init_sample_data.py 中的流量生成功能

**流量数据生成特点**：
- 为每个设备生成过去24小时的逐小时流量数据
- 每个设备配置多个网络接口
- 考虑一天中不同时段的流量波动（高峰期增加流量）
- 生成入站和出站的字节数、包数
- 模拟少量的包错误和丢包
- 计算接口带宽利用率

**代码示例**：
```python
# 随机生成接口每小时的流量数据
for hour in range(24, 0, -1):
    time_point = now - timedelta(hours=hour)
    
    # 模拟流量数据，随机生成入站和出站流量
    in_octets_per_second = int(random.uniform(10000000, 100000000))  # 10-100 MB/s
    out_octets_per_second = int(random.uniform(5000000, 80000000))   # 5-80 MB/s
    
    # 为高峰时段(9-12, 14-17)增加流量
    hour_of_day = time_point.hour
    if (9 <= hour_of_day <= 12) or (14 <= hour_of_day <= 17):
        in_octets_per_second = int(in_octets_per_second * 1.5)
        out_octets_per_second = int(out_octets_per_second * 1.5)
    
    # 存储一小时的累计数据
    traffic = Traffic(
        device_id=device.id,
        interface=interface,
        in_octets=in_octets_per_second * 3600,  # 一小时的累计字节数
        out_octets=out_octets_per_second * 3600,
        in_packets=in_packets_per_second * 3600,
        out_packets=out_packets_per_second * 3600,
        in_errors=in_errors,
        out_errors=out_errors,
        bandwidth=bandwidth,
        utilization=utilization,
        timestamp=time_point
    )
    db.session.add(traffic)
```

### 3. init_db.py 中的流量生成功能

**流量数据生成特点**：
- 为设备创建不同接口的流量数据
- 模拟24小时内每小时的流量波动
- 根据时间变化生成不同的流量数据

**代码示例**：
```python
# 添加示例流量数据
now = datetime.now()
for device in device_objs:
    for i in range(24):  # 过去24小时的数据
        time_point = now - timedelta(hours=i)
        # 模拟两个接口的流量数据
        for interface in ['GigabitEthernet0/0', 'GigabitEthernet0/1']:
            # 模拟流量数据，不同时间点有所波动
            inbound = 1000000 + (i % 12) * 500000
            outbound = 800000 + (i % 12) * 400000
            utilization = ((inbound + outbound) / 1000000000) * 100  # 假设1Gbps带宽
            
            t = Traffic(
                device_id=device.id,
                interface=interface,
                interface_index=f"{interface.replace('GigabitEthernet', '')}" if 'GigabitEthernet' in interface else '0',
                inbound=inbound,
                outbound=outbound,
                bandwidth_utilization=utilization,
                timestamp=time_point
            )
            db.session.add(t)
```

## 运行指南

### 初始化基本数据

```bash
# 创建数据库表并添加基础数据
python init_db.py

# 添加更多示例数据
python init_sample_data.py

# 添加测试数据
python add_test_data.py
```

### 生成网络拓扑和终端

```bash
# 生成完整的网络拓扑结构，包括网络设备和终端
python network_topology_generator.py
```

### 生成高级流量数据

```bash
# 生成7天的流量数据，每小时12个样本点
python advanced_traffic_generator.py 7 12 

# 生成3天的流量数据，每小时6个样本点，不清除现有数据
python advanced_traffic_generator.py 3 6 False
```

## 脚本定位与区别

虽然上述脚本在功能上有一定重叠，但它们各自有不同的定位和使用场景：

### 各脚本定位与特点

1. **init_db.py**：
   - **主要目的**：基础数据库初始化
   - **特点**：创建必要的数据库表结构，添加少量基础数据
   - **适用场景**：系统首次安装，只需基础数据就能运行

2. **init_sample_data.py**：
   - **主要目的**：创建丰富的示例数据
   - **特点**：生成大量随机终端(50个)，更全面的演示数据
   - **适用场景**：演示环境或测试环境准备

3. **add_test_data.py**：
   - **主要目的**：添加特定测试数据
   - **特点**：添加预定义的测试数据，更加可控
   - **适用场景**：特定功能测试，不需要大量随机数据

4. **network_topology_generator.py**：
   - **主要目的**：生成真实网络拓扑
   - **特点**：关注网络结构，生成分层的网络架构
   - **适用场景**：需要测试复杂网络拓扑功能时

5. **advanced_traffic_generator.py**：
   - **主要目的**：生成高质量流量数据
   - **特点**：使用ARIMA和GARCH统计模型，生成真实流量波动
   - **适用场景**：需要分析真实流量特征时

### 建议使用方式

虽然这些脚本有功能重叠，但不建议直接删除任何脚本，而是根据需求选择使用：

1. **简单测试环境**：仅使用 `init_db.py`
2. **演示环境**：使用 `init_sample_data.py`
3. **复杂拓扑测试**：使用 `network_topology_generator.py`
4. **流量分析测试**：使用 `advanced_traffic_generator.py`
5. **特定功能测试**：使用 `add_test_data.py`

如果确实想减少重复，可以考虑：
1. 将 `init_db.py` 仅保留为数据库结构初始化工具，移除示例数据生成功能
2. 将 `add_test_data.py` 集成到其他脚本中作为可选模块
3. 创建一个统一的数据生成配置界面，可选择需要的数据类型和数量

总体而言，这些脚本是为不同阶段和目的设计的，虽有重叠但不完全多余，可以根据具体需求选择使用。

## 注意事项

1. **数据清除警告**：多数脚本在运行前会清除现有相同类型的数据。如果需要保留现有数据，请检查脚本参数或修改脚本。

2. **执行顺序**：建议按照以下顺序执行脚本：
   - 先运行 `init_db.py` 创建数据库结构
   - 再运行 `network_topology_generator.py` 生成网络拓扑
   - 最后运行 `advanced_traffic_generator.py` 生成详细流量数据

3. **资源消耗**：生成大量数据（特别是使用`advanced_traffic_generator.py`）可能会消耗较多系统资源和时间，建议在服务器资源空闲时运行。

4. **数据库连接**：确保配置文件中的数据库连接信息正确，并且数据库服务正在运行。

5. **重复运行**：某些脚本重复运行可能导致数据冗余或不一致，请谨慎操作。

## 故障排除

### 常见问题及解决方案

1. **Terminal字段错误**: 如遇到 "'total_traffic' is an invalid keyword argument for Terminal" 错误，请检查 Terminal 模型定义，正确的字段应为 `in_traffic` 和 `out_traffic`。

   解决方案：修改相关脚本，确保使用正确的字段名称：
   ```python
   # 错误
   terminal = Terminal(total_traffic=1000000)
   
   # 正确
   terminal = Terminal(in_traffic=500000, out_traffic=500000)
   ```

2. **数据库连接问题**：如遇到数据库连接错误，请检查配置文件和数据库服务状态。

3. **内存不足**：生成大量数据时可能遇到内存不足问题，可以通过调整批量提交大小或减少生成数据量解决：
   ```python
   # 调整批量提交大小
   if len(traffic_data_list) >= 500:  # 改为更小的值
       db.session.add_all(traffic_data_list)
       db.session.commit()
       traffic_data_list = []
   ```

4. **应用上下文错误**：如遇到 "Working outside of application context" 错误，确保在适当的 Flask 应用上下文中执行数据库操作：
   ```python
   app = create_app()
   with app.app_context():
       # 数据库操作代码
   ```

## 最佳实践

1. **开发环境测试**：在部署到生产环境前，先在开发环境测试数据生成脚本。

2. **数据量控制**：根据系统性能和需求调整生成的数据量，避免生成过多无用数据。

3. **数据备份**：在运行可能清除数据的脚本前，先备份重要数据。

4. **脚本定制**：根据实际需求修改脚本参数，例如调整设备数量、流量特征等。

5. **定期更新**：设置定时任务定期生成新的模拟数据，保持系统数据的新鲜度。

6. **监控生成过程**：对于大型数据生成任务，添加日志和进度指示器以监控进度。

---

本文档详细介绍了校园网络监控系统中模拟数据生成的各种方法和工具。通过运行这些脚本，可以快速创建一个包含丰富数据的测试环境，用于开发、测试和演示系统功能。如有任何问题，请联系项目管理员或技术支持团队。 