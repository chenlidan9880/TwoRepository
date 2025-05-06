#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
专门用于生成告警数据的脚本，不会影响现有设备、终端和流量数据
"""

import random
from datetime import datetime, timedelta
from app import create_app, db
from app.models.device import Device
from app.models.alert import Alert


def generate_alerts(clear_existing=True, count_per_device=3):
    """为现有设备生成告警数据"""
    app = create_app()
    with app.app_context():
        # 获取所有现有设备
        devices = Device.query.all()
        if not devices:
            print("没有找到网络设备，请先运行设备生成脚本")
            return

        # 如果设置了清除标志，则先清除现有告警
        if clear_existing:
            try:
                print("清除现有告警数据...")
                Alert.query.delete()
                db.session.commit()
                print("现有告警已清除")
            except Exception as e:
                print(f"清除告警出错: {str(e)}")
                db.session.rollback()

        # 定义告警类型和严重程度
        alert_types = {
            'traffic_high': '流量告警',
            'cpu_high': 'CPU告警',
            'memory_high': '内存告警',
            'device_down': '设备离线',
            'security_threat': '安全威胁'
        }

        severity_levels = ['info', 'warning', 'critical']
        now = datetime.now()

        # 为每个设备生成告警
        print(f"开始为{len(devices)}个设备生成告警...")
        alert_count = 0

        for device in devices:
            # 每个设备生成指定数量的告警
            for _ in range(random.randint(1, count_per_device)):
                # 随机选择告警类型和严重程度
                alert_type = random.choice(list(alert_types.keys()))
                severity = random.choice(severity_levels)

                # 随机生成告警时间（过去72小时内）
                alert_time = now - timedelta(hours=random.randint(1, 72))

                # 根据告警类型准备详细信息
                value = 0
                threshold = 0

                if alert_type == 'traffic_high':
                    value = random.uniform(850, 950)
                    threshold = 800
                    title = f"设备 {device.name} 流量超过阈值"
                    message = f"设备 {device.name} 流量突增，达到 {value:.2f} Mbps，超过阈值 {threshold} Mbps"
                elif alert_type == 'cpu_high':
                    value = random.uniform(90, 99)
                    threshold = 85
                    title = f"设备 {device.name} CPU使用率过高"
                    message = f"设备 {device.name} CPU使用率达到 {value:.2f}%，超过阈值 {threshold}%"
                elif alert_type == 'memory_high':
                    value = random.uniform(85, 98)
                    threshold = 80
                    title = f"设备 {device.name} 内存使用率过高"
                    message = f"设备 {device.name} 内存使用率达到 {value:.2f}%，超过阈值 {threshold}%"
                elif alert_type == 'device_down':
                    title = f"设备 {device.name} 无法连接"
                    message = f"设备 {device.name} 连续3次ping不通，可能已经离线"
                elif alert_type == 'security_threat':
                    title = f"设备 {device.name} 安全威胁"
                    message = f"设备 {device.name} 检测到可疑访问尝试，可能存在安全风险"

                # 创建告警实例
                alert = Alert(
                    device_id=device.id,
                    alert_type=alert_type,
                    severity=severity,
                    title=title,
                    message=message,
                    value=value,
                    threshold=threshold,
                    is_read=random.choice([True, False]),
                    is_handled=random.choice([True, False]),
                    created_at=alert_time
                )

                db.session.add(alert)
                alert_count += 1

                # 每100条提交一次，避免内存问题
                if alert_count % 100 == 0:
                    db.session.commit()
                    print(f"已生成{alert_count}条告警...")

        # 提交所有剩余告警
        db.session.commit()
        print(f"告警生成完成，共生成{alert_count}条告警数据")


if __name__ == '__main__':
    import sys

    # 默认清除现有告警，每个设备生成3个告警
    clear_existing = True
    count_per_device = 3

    # 如果提供了命令行参数
    if len(sys.argv) > 1:
        clear_existing = sys.argv[1].lower() in ('true', 't', '1', 'yes', 'y')
    if len(sys.argv) > 2:
        count_per_device = int(sys.argv[2])

    generate_alerts(clear_existing, count_per_device)