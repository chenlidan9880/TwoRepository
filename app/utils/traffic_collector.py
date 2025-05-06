import time
from datetime import datetime
import random
from app import db
from app.models.traffic import Traffic

# 定义SNMP OID
OID_IF_DESCR = '1.3.6.1.2.1.2.2.1.2'  # 接口描述
OID_IF_IN_OCTETS = '1.3.6.1.2.1.2.2.1.10'  # 入口流量（字节）
OID_IF_OUT_OCTETS = '1.3.6.1.2.1.2.2.1.16'  # 出口流量（字节）
OID_IF_IN_PACKETS = '1.3.6.1.2.1.2.2.1.11'  # 入口数据包数
OID_IF_OUT_PACKETS = '1.3.6.1.2.1.2.2.1.17'  # 出口数据包数
OID_IF_IN_ERRORS = '1.3.6.1.2.1.2.2.1.14'  # 入口错误数
OID_IF_OUT_ERRORS = '1.3.6.1.2.1.2.2.1.20'  # 出口错误数
OID_IF_SPEED = '1.3.6.1.2.1.2.2.1.5'  # 接口带宽

def collect_device_traffic(device):
    """
    通过SNMP采集设备流量数据
    
    注意：由于我们不能实际连接到SNMP设备，这里使用随机数模拟数据
    实际项目中，请使用PySNMP库采集真实数据
    """
    # 模拟数据
    interfaces = ["GigabitEthernet0/0", "GigabitEthernet0/1", "GigabitEthernet1/0", "Loopback0"]
    traffic_data = []
    
    # 为每个接口生成模拟数据
    for interface in interfaces:
        # 带宽（bps）：100Mbps, 1Gbps等
        bandwidth = random.choice([100000000, 1000000000])
        
        # 入口和出口流量（字节）：随机生成
        in_octets = int(random.uniform(0.1, 0.8) * bandwidth / 8 * 5)  # 5秒内的字节数
        out_octets = int(random.uniform(0.1, 0.8) * bandwidth / 8 * 5)
        
        # 数据包数：根据流量估算
        in_packets = int(in_octets / random.uniform(100, 1500))  # 平均包大小在100-1500字节之间
        out_packets = int(out_octets / random.uniform(100, 1500))
        
        # 错误数：很少，随机生成
        in_errors = random.randint(0, 5)
        out_errors = random.randint(0, 5)
        
        # 计算入站和出站速率（bps）
        in_rate = in_octets * 8 / 5
        out_rate = out_octets * 8 / 5
        
        # 计算最大流量速率（bps）- 使用入站和出站中的较大值
        # 全双工网络中，入站和出站可以同时达到最大带宽，不应该相加
        max_rate = max(in_rate, out_rate)
        
        # 带宽利用率（百分比）- 使用最大流量值（入站或出站）除以带宽
        utilization = min(100, (max_rate / bandwidth) * 100)
        
        # 创建流量数据记录
        traffic = Traffic(
            device_id=device.id,
            interface=interface,
            in_octets=in_octets,
            out_octets=out_octets,
            in_packets=in_packets,
            out_packets=out_packets,
            in_errors=in_errors,
            out_errors=out_errors,
            bandwidth=bandwidth,
            utilization=utilization,
            timestamp=datetime.utcnow()
        )
        
        # 保存到数据库
        db.session.add(traffic)
        
        # 添加到返回结果
        traffic_data.append({
            'interface': interface,
            'in_rate': in_rate,  # bps
            'out_rate': out_rate,  # bps
            'in_packets': in_packets,
            'out_packets': out_packets,
            'in_errors': in_errors,
            'out_errors': out_errors,
            'bandwidth': bandwidth,
            'utilization': utilization
        })
    
    # 提交到数据库
    db.session.commit()
    
    return traffic_data


def collect_all_devices_traffic():
    """
    采集所有设备的流量数据
    """
    from app.models.device import Device
    
    start_time = time.time()
    devices = Device.query.filter_by(status='online').all()
    
    device_count = 0
    for device in devices:
        try:
            collect_device_traffic(device)
            print(f"已采集 {device.name} 的流量数据")
            device_count += 1
        except Exception as e:
            print(f"采集 {device.name} 的流量数据失败: {e}")
    
    # 如果有新采集的流量数据，尝试生成统计数据
    if device_count > 0:
        try:
            from app.utils.traffic_processor import process_traffic_stats
            print("正在生成流量统计数据...")
            process_traffic_stats()
            print("流量统计数据生成完成")
        except Exception as e:
            print(f"生成流量统计数据失败: {e}")
    
    end_time = time.time()
    print(f"流量采集完成，共采集了 {device_count} 个设备的数据，耗时 {end_time - start_time:.2f} 秒")
    
    return True


def check_traffic_anomalies():
    """
    检查流量异常情况
    """
    from app.models.device import Device
    from app.models.alert import Alert
    from flask import current_app
    
    devices = Device.query.filter_by(status='online').all()
    threshold = current_app.config['TRAFFIC_ALERT_THRESHOLD']
    
    for device in devices:
        # 获取最新的流量数据
        traffic = Traffic.query.filter_by(device_id=device.id).order_by(Traffic.timestamp.desc()).first()
        
        if traffic and traffic.utilization > threshold:
            # 创建告警
            alert = Alert(
                device_id=device.id,
                alert_type='traffic_high',
                severity='warning',
                title=f"{device.name} 流量超出阈值",
                message=f"{device.name} 的 {traffic.interface} 接口流量使用率达到 {traffic.utilization:.2f}%，超过阈值 {threshold}%",
                value=traffic.utilization,
                threshold=threshold
            )
            db.session.add(alert)
            
            print(f"已为 {device.name} 创建流量超出阈值告警")
    
    db.session.commit()
    return True 