#!/usr/bin/env python
"""
SNMP测试工具
用于测试与网络设备的SNMP连接和数据采集
"""

import sys
import argparse
from app import create_app
from app.utils.snmp_collector import snmp_get, snmp_walk, check_device_status
from app.utils.snmp_collector import (
    OID_SYS_DESCR, OID_SYS_NAME, OID_SYS_LOCATION, OID_SYS_CONTACT, OID_SYS_UPTIME,
    OID_IF_DESCR, OID_IF_SPEED, OID_IF_IN_OCTETS, OID_IF_OUT_OCTETS,
    OID_CISCO_CPU_5SEC, OID_CISCO_MEM_USED, OID_CISCO_MEM_FREE
)

def test_basic_info(args):
    """测试基本系统信息获取"""
    print(f"正在测试设备 {args.ip} 的基本系统信息...")
    
    # 测试系统描述
    print("系统描述: ", end="")
    sys_descr = snmp_get(args.ip, OID_SYS_DESCR, port=args.port, community=args.community, version=args.version)
    print(sys_descr if sys_descr is not None else "获取失败")
    
    # 测试系统名称
    print("系统名称: ", end="")
    sys_name = snmp_get(args.ip, OID_SYS_NAME, port=args.port, community=args.community, version=args.version)
    print(sys_name if sys_name is not None else "获取失败")
    
    # 测试系统位置
    print("系统位置: ", end="")
    sys_location = snmp_get(args.ip, OID_SYS_LOCATION, port=args.port, community=args.community, version=args.version)
    print(sys_location if sys_location is not None else "获取失败")
    
    # 测试系统联系人
    print("系统联系人: ", end="")
    sys_contact = snmp_get(args.ip, OID_SYS_CONTACT, port=args.port, community=args.community, version=args.version)
    print(sys_contact if sys_contact is not None else "获取失败")
    
    # 测试系统运行时间
    print("系统运行时间: ", end="")
    sys_uptime = snmp_get(args.ip, OID_SYS_UPTIME, port=args.port, community=args.community, version=args.version)
    print(sys_uptime if sys_uptime is not None else "获取失败")

def test_interfaces(args):
    """测试接口信息获取"""
    print(f"正在测试设备 {args.ip} 的接口信息...")
    
    # 获取接口描述
    print("接口列表:")
    if_descr = snmp_walk(args.ip, OID_IF_DESCR, port=args.port, community=args.community, version=args.version)
    
    if not if_descr:
        print("  获取接口列表失败")
        return
    
    # 获取接口速度
    if_speed = snmp_walk(args.ip, OID_IF_SPEED, port=args.port, community=args.community, version=args.version)
    
    # 获取接口输入字节数
    if_in_octets = snmp_walk(args.ip, OID_IF_IN_OCTETS, port=args.port, community=args.community, version=args.version)
    
    # 获取接口输出字节数
    if_out_octets = snmp_walk(args.ip, OID_IF_OUT_OCTETS, port=args.port, community=args.community, version=args.version)
    
    # 显示接口信息
    for oid, descr in if_descr.items():
        # 获取接口索引
        index = oid.split('.')[-1]
        
        # 组装完整OID
        speed_oid = f'{OID_IF_SPEED}.{index}'
        in_octets_oid = f'{OID_IF_IN_OCTETS}.{index}'
        out_octets_oid = f'{OID_IF_OUT_OCTETS}.{index}'
        
        # 获取各项数据
        speed = if_speed.get(speed_oid, 0)
        speed_mbps = int(speed) / 1000000 if speed else 0
        
        in_octets = if_in_octets.get(in_octets_oid, 0)
        out_octets = if_out_octets.get(out_octets_oid, 0)
        
        # 显示接口信息
        print(f"  接口: {descr}")
        print(f"    速度: {speed_mbps:.2f} Mbps")
        print(f"    入站字节数: {in_octets}")
        print(f"    出站字节数: {out_octets}")
        print()

def test_resources(args):
    """测试资源使用率信息获取（仅支持Cisco设备）"""
    print(f"正在测试设备 {args.ip} 的资源使用率信息（仅支持Cisco设备）...")
    
    # 测试CPU使用率
    print("CPU使用率(5秒): ", end="")
    cpu_usage = snmp_get(args.ip, OID_CISCO_CPU_5SEC, port=args.port, community=args.community, version=args.version)
    print(f"{cpu_usage}%" if cpu_usage is not None else "获取失败")
    
    # 测试内存使用情况
    print("内存使用情况: ", end="")
    mem_used = snmp_get(args.ip, OID_CISCO_MEM_USED, port=args.port, community=args.community, version=args.version)
    mem_free = snmp_get(args.ip, OID_CISCO_MEM_FREE, port=args.port, community=args.community, version=args.version)
    
    if mem_used is not None and mem_free is not None:
        total_mem = int(mem_used) + int(mem_free)
        mem_usage = (int(mem_used) / total_mem) * 100 if total_mem > 0 else 0
        print(f"已用: {mem_used} 字节, 空闲: {mem_free} 字节, 使用率: {mem_usage:.2f}%")
    else:
        print("获取失败")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='SNMP测试工具')
    parser.add_argument('ip', help='设备IP地址')
    parser.add_argument('-p', '--port', type=int, default=161, help='SNMP端口，默认161')
    parser.add_argument('-c', '--community', default='public', help='SNMP community，默认public')
    parser.add_argument('-v', '--version', default='2c', choices=['1', '2c'], help='SNMP版本，默认2c')
    parser.add_argument('-t', '--test', choices=['all', 'basic', 'interfaces', 'resources'], default='all', help='测试类型，默认all')
    
    args = parser.parse_args()
    
    # 先测试SNMP连接
    print(f"正在测试与设备 {args.ip} 的SNMP连接...")
    if check_device_status_simple(args.ip, args.port, args.community, args.version):
        print("SNMP连接成功！\n")
        
        # 根据测试类型执行测试
        if args.test == 'all' or args.test == 'basic':
            test_basic_info(args)
            print()
            
        if args.test == 'all' or args.test == 'interfaces':
            test_interfaces(args)
            print()
            
        if args.test == 'all' or args.test == 'resources':
            test_resources(args)
    else:
        print("SNMP连接失败，请检查IP地址、端口、community和SNMP版本是否正确。")

def check_device_status_simple(ip, port, community, version):
    """简单的设备状态检查"""
    sys_descr = snmp_get(ip, OID_SYS_DESCR, port=port, community=community, version=version)
    return sys_descr is not None

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        main() 