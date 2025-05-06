#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
高级模拟数据生成系统 - 整合多种模拟方案

此脚本整合了以下数据模拟方案：
1. 基础拓扑构建：使用图论模型生成网络拓扑结构、设备和终端
2. 流量模拟：使用ARIMA和GARCH等高级统计模型生成网络流量数据
3. 异常行为注入：添加网络安全事件和异常流量模式
"""

import os
import sys
import argparse
from datetime import datetime

# 导入各个模拟模块
from network_topology_generator import generate_network_topology
from advanced_traffic_generator import generate_advanced_traffic
from security_events_generator import generate_security_events

def setup_data_dirs():
    """设置数据目录"""
    os.makedirs('data', exist_ok=True)
    os.makedirs('logs', exist_ok=True)

def log_message(message, level="INFO"):
    """记录日志消息"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] [{level}] {message}"
    print(log_line)
    
    # 写入日志文件
    with open(os.path.join('logs', 'simulation.log'), 'a', encoding='utf-8') as f:
        f.write(log_line + "\n")

def generate_all_data(args):
    """生成所有模拟数据"""
    start_time = datetime.now()
    log_message(f"开始生成模拟数据，参数：{args}")
    
    # 步骤1：生成网络拓扑、设备和终端
    if args.topology:
        log_message("开始生成网络拓扑结构...")
        try:
            generate_network_topology(clear_existing=not args.no_clear)
            log_message("网络拓扑生成完成")
        except Exception as e:
            log_message(f"生成网络拓扑时出错: {str(e)}", "ERROR")
            if args.debug:
                import traceback
                traceback.print_exc()
    
    # 步骤2：生成高级流量数据
    if args.traffic:
        log_message(f"开始生成高级流量数据 ({args.days} 天)...")
        try:
            generate_advanced_traffic(days=args.days, samples_per_hour=args.samples, clear_existing=not args.no_clear)
            log_message("高级流量数据生成完成")
        except Exception as e:
            log_message(f"生成高级流量数据时出错: {str(e)}", "ERROR")
            if args.debug:
                import traceback
                traceback.print_exc()
    
    # 步骤3：生成安全事件和异常流量
    if args.security:
        log_message(f"开始生成安全事件和异常流量数据 ({args.days} 天)...")
        try:
            generate_security_events(days=args.days, clear_existing=not args.no_clear)
            log_message("安全事件数据生成完成")
        except Exception as e:
            log_message(f"生成安全事件数据时出错: {str(e)}", "ERROR")
            if args.debug:
                import traceback
                traceback.print_exc()
    
    # 总结
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    log_message(f"模拟数据生成完成，总耗时：{duration:.2f}秒")

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='高级网络数据模拟系统 - 生成真实网络流量和行为')
    
    # 功能选择参数
    parser.add_argument('--all', action='store_true', help='生成所有类型的模拟数据')
    parser.add_argument('--topology', action='store_true', help='生成网络拓扑结构')
    parser.add_argument('--traffic', action='store_true', help='生成高级流量数据')
    parser.add_argument('--security', action='store_true', help='生成安全事件和异常流量')
    
    # 数据量和质量参数
    parser.add_argument('--days', type=int, default=7, help='生成多少天的数据 (默认: 7)')
    parser.add_argument('--samples', type=int, default=12, help='每小时生成多少个样本点 (默认: 12，即5分钟一个)')
    
    # 其他选项
    parser.add_argument('--no-clear', action='store_true', help='不清除现有数据（默认会清除）')
    parser.add_argument('--debug', action='store_true', help='启用调试模式，显示详细错误信息')
    
    args = parser.parse_args()
    
    # 如果指定了--all，则启用所有功能
    if args.all:
        args.topology = True
        args.traffic = True
        args.security = True
    
    # 如果没有指定任何功能，默认生成所有数据
    if not (args.topology or args.traffic or args.security):
        args.topology = True
        args.traffic = True
        args.security = True
    
    return args

def main():
    """主函数"""
    try:
        # 设置数据目录
        setup_data_dirs()
        
        # 解析命令行参数
        args = parse_arguments()
        
        # 生成所有模拟数据
        generate_all_data(args)
        
    except Exception as e:
        log_message(f"程序运行出错: {str(e)}", "ERROR")
        if '--debug' in sys.argv:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 