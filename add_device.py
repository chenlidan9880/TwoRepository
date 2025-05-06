#!/usr/bin/env python
"""
添加设备工具
用于通过命令行向系统添加网络设备
"""

import sys
import argparse
from app import create_app, db
from app.models.device import Device
from datetime import datetime
from app.utils.snmp_collector import check_device_status_simple, OID_SYS_DESCR

def add_device(args):
    """
    添加设备到系统
    
    参数:
        args: 命令行参数
    
    返回:
        成功返回True，失败返回False
    """
    try:
        # 检查设备是否已存在
        existing_device = Device.query.filter_by(ip_address=args.ip).first()
        if existing_device:
            print(f"错误: IP地址为 {args.ip} 的设备已存在")
            return False
        
        # 检查SNMP连接
        if args.check_snmp:
            print(f"正在测试与设备 {args.ip} 的SNMP连接...")
            if not check_device_status_simple(args.ip, args.port, args.community, args.version):
                print("SNMP连接失败，无法添加设备。")
                if not args.force:
                    return False
                print("由于指定了--force参数，将继续添加设备，但设备可能无法正常监控。")
                status = 'offline'
            else:
                print("SNMP连接成功！")
                status = 'online'
        else:
            status = 'online'
        
        # 创建设备对象
        device = Device(
            name=args.name,
            ip_address=args.ip,
            device_type=args.type,
            location=args.location,
            description=args.description,
            snmp_community=args.community,
            snmp_version=args.version,
            snmp_port=args.port,
            status=status,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # 保存到数据库
        db.session.add(device)
        db.session.commit()
        
        print(f"设备 {args.name} (IP: {args.ip}) 添加成功！")
        return True
    except Exception as e:
        db.session.rollback()
        print(f"添加设备时出错: {e}")
        return False

def check_device_status_simple(ip, port, community, version):
    """简单的设备状态检查"""
    from app.utils.snmp_collector import snmp_get
    sys_descr = snmp_get(ip, OID_SYS_DESCR, port=port, community=community, version=version)
    return sys_descr is not None

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='添加设备工具')
    parser.add_argument('ip', help='设备IP地址')
    parser.add_argument('--name', help='设备名称，默认使用IP地址')
    parser.add_argument('--type', default='交换机', choices=['路由器', '交换机', '防火墙', '服务器', '无线AP', '其他'], help='设备类型，默认为交换机')
    parser.add_argument('--location', default='', help='设备位置')
    parser.add_argument('--description', default='', help='设备描述')
    parser.add_argument('--port', type=int, default=161, help='SNMP端口，默认161')
    parser.add_argument('--community', default='public', help='SNMP community，默认public')
    parser.add_argument('--version', default='2c', choices=['1', '2c'], help='SNMP版本，默认2c')
    parser.add_argument('--no-check', dest='check_snmp', action='store_false', help='不检查SNMP连接')
    parser.add_argument('--force', action='store_true', help='强制添加设备，即使SNMP连接失败')
    
    # 设置默认值
    parser.set_defaults(check_snmp=True)
    
    args = parser.parse_args()
    
    # 如果未指定名称，则使用IP地址作为名称
    if not args.name:
        args.name = args.ip
    
    app = create_app()
    with app.app_context():
        add_device(args)

if __name__ == '__main__':
    main() 