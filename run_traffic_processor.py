#!/usr/bin/env python
"""
流量处理器手动运行脚本
可用于：
1. 测试流量处理器功能
2. 手动生成统计数据
3. 填充历史数据
"""

from app import create_app
from app.utils.traffic_processor import process_traffic_stats, process_daily_stats
import argparse

def main():
    """脚本入口函数"""
    parser = argparse.ArgumentParser(description='运行流量处理器')
    parser.add_argument('--hourly', action='store_true', help='运行小时级别流量处理')
    parser.add_argument('--daily', action='store_true', help='运行每日流量处理')
    parser.add_argument('--all', action='store_true', help='运行所有流量处理')
    args = parser.parse_args()
    
    # 如果没有指定参数，默认运行全部
    if not (args.hourly or args.daily):
        args.all = True
    
    app = create_app()
    
    with app.app_context():
        print("开始运行流量处理器...")
        
        if args.hourly or args.all:
            print("运行小时级别流量处理...")
            result = process_traffic_stats()
            print(f"小时级别流量处理结果: {result}")
        
        if args.daily or args.all:
            print("运行每日流量处理...")
            result = process_daily_stats()
            print(f"每日流量处理结果: {result}")
        
        print("流量处理器运行完成")

if __name__ == "__main__":
    main() 