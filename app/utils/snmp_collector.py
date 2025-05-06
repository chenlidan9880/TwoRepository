"""
SNMP数据采集模块
用于从网络设备收集数据，如流量、CPU使用率、内存使用率等
"""

import time
from datetime import datetime
from pysnmp.hlapi import (
    SnmpEngine, CommunityData, UdpTransportTarget, 
    ContextData, ObjectType, ObjectIdentity, getCmd, nextCmd
)
from app import db
from app.models.traffic import Traffic
from app.models.device import Device
from app.models.alert import Alert

# 常用SNMP OID
OID_IF_DESCR = '1.3.6.1.2.1.2.2.1.2'  # 接口描述
OID_IF_TYPE = '1.3.6.1.2.1.2.2.1.3'    # 接口类型
OID_IF_MTU = '1.3.6.1.2.1.2.2.1.4'     # 接口MTU
OID_IF_SPEED = '1.3.6.1.2.1.2.2.1.5'   # 接口速度
OID_IF_MAC = '1.3.6.1.2.1.2.2.1.6'     # 接口物理地址
OID_IF_ADMIN_STATUS = '1.3.6.1.2.1.2.2.1.7'  # 接口管理状态
OID_IF_OPER_STATUS = '1.3.6.1.2.1.2.2.1.8'   # 接口操作状态
OID_IF_IN_OCTETS = '1.3.6.1.2.1.2.2.1.10'    # 接口输入字节数
OID_IF_IN_UCAST = '1.3.6.1.2.1.2.2.1.11'     # 接口输入单播包数
OID_IF_IN_ERRORS = '1.3.6.1.2.1.2.2.1.14'    # 接口输入错误数
OID_IF_OUT_OCTETS = '1.3.6.1.2.1.2.2.1.16'   # 接口输出字节数
OID_IF_OUT_UCAST = '1.3.6.1.2.1.2.2.1.17'    # 接口输出单播包数
OID_IF_OUT_ERRORS = '1.3.6.1.2.1.2.2.1.20'   # 接口输出错误数

# CPU和内存OID (Cisco设备)
OID_CISCO_CPU_5SEC = '1.3.6.1.4.1.9.9.109.1.1.1.1.3.1'  # 5秒CPU使用率
OID_CISCO_MEM_USED = '1.3.6.1.4.1.9.9.48.1.1.1.5.1'     # 已用内存
OID_CISCO_MEM_FREE = '1.3.6.1.4.1.9.9.48.1.1.1.6.1'     # 剩余内存

# 系统信息OID
OID_SYS_DESCR = '1.3.6.1.2.1.1.1.0'  # 系统描述
OID_SYS_UPTIME = '1.3.6.1.2.1.1.3.0'  # 系统运行时间
OID_SYS_CONTACT = '1.3.6.1.2.1.1.4.0'  # 系统联系人
OID_SYS_NAME = '1.3.6.1.2.1.1.5.0'  # 系统名称
OID_SYS_LOCATION = '1.3.6.1.2.1.1.6.0'  # 系统位置


def snmp_get(device, oid, port=161, community='public', version='2c'):
    """
    获取单个SNMP OID的值
    
    参数:
        device: 设备IP地址
        oid: SNMP OID
        port: SNMP端口，默认161
        community: SNMP community，默认public
        version: SNMP版本，默认2c
    
    返回:
        OID对应的值，或者None（如果出错）
    """
    try:
        error_indication, error_status, error_index, var_binds = next(
            getCmd(
                SnmpEngine(),
                CommunityData(community, mpModel={'1': 0, '2c': 1}[version]),
                UdpTransportTarget((device, port), timeout=2.0, retries=3),
                ContextData(),
                ObjectType(ObjectIdentity(oid))
            )
        )
        
        if error_indication:
            print(f"SNMP错误: {error_indication}")
            return None
        elif error_status:
            print(f"SNMP错误状态: {error_status.prettyPrint()} at {error_index and var_binds[int(error_index) - 1][0] or '?'}")
            return None
        else:
            for var_bind in var_binds:
                return var_bind[1]
    except Exception as e:
        print(f"获取SNMP数据时出错: {e}")
        return None


def snmp_walk(device, oid, port=161, community='public', version='2c'):
    """
    获取SNMP OID子树的值（SNMP WALK）
    
    参数:
        device: 设备IP地址
        oid: SNMP OID
        port: SNMP端口，默认161
        community: SNMP community，默认public
        version: SNMP版本，默认2c
    
    返回:
        OID-值对的字典，或者空字典（如果出错）
    """
    result = {}
    try:
        for (error_indication, error_status, error_index, var_binds) in nextCmd(
                SnmpEngine(),
                CommunityData(community, mpModel={'1': 0, '2c': 1}[version]),
                UdpTransportTarget((device, port), timeout=2.0, retries=3),
                ContextData(),
                ObjectType(ObjectIdentity(oid)),
                lexicographicMode=False
        ):
            if error_indication:
                print(f"SNMP错误: {error_indication}")
                break
            elif error_status:
                print(f"SNMP错误状态: {error_status.prettyPrint()} at {error_index and var_binds[int(error_index) - 1][0] or '?'}")
                break
            else:
                for var_bind in var_binds:
                    # 获取OID和对应的值
                    oid = str(var_bind[0])
                    value = var_bind[1]
                    result[oid] = value
        return result
    except Exception as e:
        print(f"执行SNMP WALK时出错: {e}")
        return {}


def check_device_status(device):
    """
    检查设备状态（是否在线）
    
    参数:
        device: Device对象
    
    返回:
        True: 设备在线
        False: 设备离线
    """
    sysDescr = snmp_get(
        device.ip_address, 
        OID_SYS_DESCR, 
        port=device.snmp_port or 161,
        community=device.snmp_community or 'public',
        version=device.snmp_version or '2c'
    )
    
    return sysDescr is not None


def get_interface_traffic(device):
    """
    获取设备所有接口的流量数据
    
    参数:
        device: Device对象
    
    返回:
        接口流量数据的列表，每个元素包含接口名称、输入字节数、输出字节数等
    """
    try:
        # 获取接口描述
        if_descr = snmp_walk(
            device.ip_address, 
            OID_IF_DESCR, 
            port=device.snmp_port or 161,
            community=device.snmp_community or 'public',
            version=device.snmp_version or '2c'
        )
        
        # 获取接口速度
        if_speed = snmp_walk(
            device.ip_address, 
            OID_IF_SPEED, 
            port=device.snmp_port or 161,
            community=device.snmp_community or 'public',
            version=device.snmp_version or '2c'
        )
        
        # 获取接口输入字节数
        if_in_octets = snmp_walk(
            device.ip_address, 
            OID_IF_IN_OCTETS, 
            port=device.snmp_port or 161,
            community=device.snmp_community or 'public',
            version=device.snmp_version or '2c'
        )
        
        # 获取接口输出字节数
        if_out_octets = snmp_walk(
            device.ip_address, 
            OID_IF_OUT_OCTETS, 
            port=device.snmp_port or 161,
            community=device.snmp_community or 'public',
            version=device.snmp_version or '2c'
        )
        
        # 获取接口输入错误数
        if_in_errors = snmp_walk(
            device.ip_address, 
            OID_IF_IN_ERRORS, 
            port=device.snmp_port or 161,
            community=device.snmp_community or 'public',
            version=device.snmp_version or '2c'
        )
        
        # 获取接口输出错误数
        if_out_errors = snmp_walk(
            device.ip_address, 
            OID_IF_OUT_ERRORS, 
            port=device.snmp_port or 161,
            community=device.snmp_community or 'public',
            version=device.snmp_version or '2c'
        )
        
        # 获取接口输入包数
        if_in_ucast = snmp_walk(
            device.ip_address, 
            OID_IF_IN_UCAST, 
            port=device.snmp_port or 161,
            community=device.snmp_community or 'public',
            version=device.snmp_version or '2c'
        )
        
        # 获取接口输出包数
        if_out_ucast = snmp_walk(
            device.ip_address, 
            OID_IF_OUT_UCAST, 
            port=device.snmp_port or 161,
            community=device.snmp_community or 'public',
            version=device.snmp_version or '2c'
        )
        
        # 获取接口操作状态
        if_oper_status = snmp_walk(
            device.ip_address, 
            OID_IF_OPER_STATUS, 
            port=device.snmp_port or 161,
            community=device.snmp_community or 'public',
            version=device.snmp_version or '2c'
        )
        
        # 整合数据
        interfaces = []
        for oid, descr in if_descr.items():
            # 获取接口索引
            index = oid.split('.')[-1]
            if_index_oid = f'{OID_IF_DESCR}.{index}'
            
            # 组装完整OID
            speed_oid = f'{OID_IF_SPEED}.{index}'
            in_octets_oid = f'{OID_IF_IN_OCTETS}.{index}'
            out_octets_oid = f'{OID_IF_OUT_OCTETS}.{index}'
            in_errors_oid = f'{OID_IF_IN_ERRORS}.{index}'
            out_errors_oid = f'{OID_IF_OUT_ERRORS}.{index}'
            in_ucast_oid = f'{OID_IF_IN_UCAST}.{index}'
            out_ucast_oid = f'{OID_IF_OUT_UCAST}.{index}'
            oper_status_oid = f'{OID_IF_OPER_STATUS}.{index}'
            
            # 获取各项数据
            speed = int(if_speed.get(speed_oid, 0))
            in_octets = int(if_in_octets.get(in_octets_oid, 0))
            out_octets = int(if_out_octets.get(out_octets_oid, 0))
            in_errors = int(if_in_errors.get(in_errors_oid, 0))
            out_errors = int(if_out_errors.get(out_errors_oid, 0))
            in_packets = int(if_in_ucast.get(in_ucast_oid, 0))
            out_packets = int(if_out_ucast.get(out_ucast_oid, 0))
            oper_status = int(if_oper_status.get(oper_status_oid, 0))
            
            # 计算带宽利用率
            utilization = 0
            if speed > 0:
                utilization = ((in_octets + out_octets) * 8 / speed) * 100
            
            # 添加到结果列表
            interface_data = {
                'interface': str(descr),
                'in_octets': in_octets,
                'out_octets': out_octets,
                'in_packets': in_packets,
                'out_packets': out_packets,
                'in_errors': in_errors,
                'out_errors': out_errors,
                'bandwidth': speed,
                'utilization': utilization,
                'status': 'up' if oper_status == 1 else 'down'
            }
            interfaces.append(interface_data)
        
        return interfaces
    except Exception as e:
        print(f"获取设备{device.ip_address}接口流量数据时出错: {e}")
        return []


def get_device_cpu_memory(device):
    """
    获取设备CPU和内存使用率
    目前仅支持Cisco设备
    
    参数:
        device: Device对象
    
    返回:
        包含CPU和内存使用率的字典，或None（如果出错）
    """
    try:
        # 获取CPU使用率
        cpu_usage = snmp_get(
            device.ip_address, 
            OID_CISCO_CPU_5SEC, 
            port=device.snmp_port or 161,
            community=device.snmp_community or 'public',
            version=device.snmp_version or '2c'
        )
        
        # 获取内存使用情况
        mem_used = snmp_get(
            device.ip_address, 
            OID_CISCO_MEM_USED, 
            port=device.snmp_port or 161,
            community=device.snmp_community or 'public',
            version=device.snmp_version or '2c'
        )
        
        mem_free = snmp_get(
            device.ip_address, 
            OID_CISCO_MEM_FREE, 
            port=device.snmp_port or 161,
            community=device.snmp_community or 'public',
            version=device.snmp_version or '2c'
        )
        
        # 计算内存使用率
        mem_usage = 0
        if mem_used is not None and mem_free is not None:
            total_mem = int(mem_used) + int(mem_free)
            if total_mem > 0:
                mem_usage = (int(mem_used) / total_mem) * 100
        
        return {
            'cpu': int(cpu_usage) if cpu_usage else 0,
            'memory': mem_usage
        }
    except Exception as e:
        print(f"获取设备{device.ip_address}的CPU和内存使用率时出错: {e}")
        return {'cpu': 0, 'memory': 0}


def collect_traffic_data(device):
    """
    收集设备流量数据并保存到数据库
    
    参数:
        device: Device对象
    
    返回:
        成功收集数据返回True，否则返回False
    """
    try:
        # 先检查设备状态
        is_online = check_device_status(device)
        
        # 更新设备状态
        device.status = 'online' if is_online else 'offline'
        device.updated_at = datetime.now()
        db.session.commit()
        
        if not is_online:
            # 如果设备离线，则创建离线告警
            create_offline_alert(device)
            return False
        
        # 获取所有接口的流量数据
        interfaces = get_interface_traffic(device)
        
        # 存储流量数据
        timestamp = datetime.now()
        for interface_data in interfaces:
            # 只记录状态为up的接口数据
            if interface_data['status'] == 'up':
                traffic = Traffic(
                    device_id=device.id,
                    interface=interface_data['interface'],
                    in_octets=interface_data['in_octets'],
                    out_octets=interface_data['out_octets'],
                    in_packets=interface_data['in_packets'],
                    out_packets=interface_data['out_packets'],
                    in_errors=interface_data['in_errors'],
                    out_errors=interface_data['out_errors'],
                    bandwidth=interface_data['bandwidth'],
                    utilization=interface_data['utilization'],
                    timestamp=timestamp
                )
                db.session.add(traffic)
        
        # 获取CPU和内存使用率
        resource_usage = get_device_cpu_memory(device)
        
        # 检查是否需要创建告警
        check_and_create_alerts(device, interfaces, resource_usage)
        
        # 提交数据库事务
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        print(f"收集设备{device.ip_address}流量数据时出错: {e}")
        return False


def create_offline_alert(device):
    """
    创建设备离线告警
    
    参数:
        device: Device对象
    """
    # 检查是否已存在未处理的离线告警
    existing_alert = Alert.query.filter_by(
        device_id=device.id,
        alert_type='device_down',
        is_handled=False
    ).first()
    
    if not existing_alert:
        alert = Alert(
            device_id=device.id,
            alert_type='device_down',
            severity='critical',
            title=f"设备 {device.name} 无法连接",
            message=f"设备 {device.name} 无法通过SNMP连接，可能已经离线",
            is_read=False,
            is_handled=False,
            created_at=datetime.now()
        )
        db.session.add(alert)
        db.session.commit()


def check_and_create_alerts(device, interfaces, resource_usage):
    """
    检查是否需要创建告警
    
    参数:
        device: Device对象
        interfaces: 接口流量数据列表
        resource_usage: CPU和内存使用率
    """
    # 检查接口利用率告警
    for interface_data in interfaces:
        if interface_data['utilization'] > 80:
            # 创建流量告警
            create_traffic_alert(device, interface_data)
    
    # 检查CPU使用率告警
    if resource_usage['cpu'] > 85:
        create_cpu_alert(device, resource_usage['cpu'])
    
    # 检查内存使用率告警
    if resource_usage['memory'] > 80:
        create_memory_alert(device, resource_usage['memory'])


def create_traffic_alert(device, interface_data):
    """
    创建流量告警
    
    参数:
        device: Device对象
        interface_data: 接口流量数据
    """
    interface = interface_data['interface']
    utilization = interface_data['utilization']
    
    # 检查是否已存在未处理的告警
    existing_alert = Alert.query.filter_by(
        device_id=device.id,
        alert_type='traffic_high',
        is_handled=False
    ).first()
    
    if not existing_alert:
        # 根据利用率确定告警级别
        severity = 'warning'
        if utilization > 90:
            severity = 'critical'
        
        alert = Alert(
            device_id=device.id,
            alert_type='traffic_high',
            severity=severity,
            title=f"设备 {device.name} 接口 {interface} 流量过高",
            message=f"设备 {device.name} 接口 {interface} 带宽利用率达到 {utilization:.2f}%，超过阈值 80%",
            value=utilization,
            threshold=80,
            is_read=False,
            is_handled=False,
            created_at=datetime.now()
        )
        db.session.add(alert)


def create_cpu_alert(device, cpu_usage):
    """
    创建CPU使用率告警
    
    参数:
        device: Device对象
        cpu_usage: CPU使用率
    """
    # 检查是否已存在未处理的告警
    existing_alert = Alert.query.filter_by(
        device_id=device.id,
        alert_type='cpu_high',
        is_handled=False
    ).first()
    
    if not existing_alert:
        # 根据使用率确定告警级别
        severity = 'warning'
        if cpu_usage > 95:
            severity = 'critical'
        
        alert = Alert(
            device_id=device.id,
            alert_type='cpu_high',
            severity=severity,
            title=f"设备 {device.name} CPU使用率过高",
            message=f"设备 {device.name} CPU使用率达到 {cpu_usage:.2f}%，超过阈值 85%",
            value=cpu_usage,
            threshold=85,
            is_read=False,
            is_handled=False,
            created_at=datetime.now()
        )
        db.session.add(alert)


def create_memory_alert(device, memory_usage):
    """
    创建内存使用率告警
    
    参数:
        device: Device对象
        memory_usage: 内存使用率
    """
    # 检查是否已存在未处理的告警
    existing_alert = Alert.query.filter_by(
        device_id=device.id,
        alert_type='memory_high',
        is_handled=False
    ).first()
    
    if not existing_alert:
        # 根据使用率确定告警级别
        severity = 'warning'
        if memory_usage > 90:
            severity = 'critical'
        
        alert = Alert(
            device_id=device.id,
            alert_type='memory_high',
            severity=severity,
            title=f"设备 {device.name} 内存使用率过高",
            message=f"设备 {device.name} 内存使用率达到 {memory_usage:.2f}%，超过阈值 80%",
            value=memory_usage,
            threshold=80,
            is_read=False,
            is_handled=False,
            created_at=datetime.now()
        )
        db.session.add(alert)


def poll_all_devices():
    """
    轮询所有设备的流量数据
    """
    devices = Device.query.all()
    for device in devices:
        collect_traffic_data(device)
        # 暂停一会儿，避免过多请求导致远程设备负载过高
        time.sleep(1) 