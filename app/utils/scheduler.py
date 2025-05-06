"""
定时任务调度器
用于调度定期执行的任务，如设备流量数据采集、告警检查等
"""

from datetime import datetime
from app.utils.snmp_collector import poll_all_devices

# 注意：不再从app导入scheduler
# 调度器任务现在直接在app/__init__.py中配置

def poll_devices():
    """
    采集所有设备的流量数据
    此函数由调度器定期调用
    """
    print(f"[{datetime.now()}] 开始执行设备流量数据采集...")
    try:
        poll_all_devices()
        print(f"[{datetime.now()}] 设备流量数据采集完成")
    except Exception as e:
        print(f"[{datetime.now()}] 设备流量数据采集出错: {e}")

def discover_terminals():
    """
    发现和更新终端设备
    此函数由调度器定期调用
    """
    print(f"[{datetime.now()}] 开始执行终端设备发现...")
    try:
        from app.utils.terminal_identifier import schedule_terminal_discovery, init_oui_database
        
        # 初始化OUI数据库
        init_oui_database()
        
        # 执行终端设备发现
        result = schedule_terminal_discovery()
        print(f"[{datetime.now()}] 终端设备发现完成，发现 {result.get('discovered', 0)} 个设备，{result.get('offline', 0)} 个设备离线")
    except Exception as e:
        print(f"[{datetime.now()}] 终端设备发现出错: {e}")

# 不再需要这些函数，因为调度器在app/__init__.py中初始化和管理
# def init_scheduler():
#     """初始化调度器，添加定时任务"""
#     pass

# def start_scheduler():
#     """启动调度器"""
#     pass

# def stop_scheduler():
#     """停止调度器"""
#     pass 