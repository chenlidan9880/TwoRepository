import time
from datetime import datetime, timedelta
from sqlalchemy import func
from app import db
from app.models.traffic import Traffic, TrafficStats
from app.models.device import Device
import logging
from flask import current_app

# 获取日志记录器
logger = logging.getLogger(__name__)

def process_traffic_stats():
    """
    将Traffic实时数据聚合为TrafficStats统计数据
    处理逻辑：
    1. 按设备ID、小时分组聚合最近的Traffic数据
    2. 计算每个小时的平均和最高流量值
    3. 生成TrafficStats记录
    """
    try:
        # 获取当前时间或测试时间
        if current_app.config.get('TESTING_DATE'):
            now = current_app.config.get('TESTING_DATE')
            if isinstance(now, str):
                now = datetime.fromisoformat(now)
            logger.info(f"使用测试日期: {now}")
        else:
            now = datetime.utcnow()
        
        # 获取一小时前的时间
        one_hour_ago = now - timedelta(hours=1)
        
        # 查找所有在线设备
        devices = Device.query.filter_by(status='online').all()
        
        stats_count = 0
        
        for device in devices:
            # 按小时计算统计数据
            hour_stats = db.session.query(
                func.avg(Traffic.in_octets * 8 / 5).label('avg_in_rate'),  # 转换为bps
                func.avg(Traffic.out_octets * 8 / 5).label('avg_out_rate'),  # 转换为bps
                func.max(Traffic.in_octets * 8 / 5).label('max_in_rate'),  # 转换为bps
                func.max(Traffic.out_octets * 8 / 5).label('max_out_rate'),  # 转换为bps
                func.avg(Traffic.utilization).label('avg_utilization')
            ).filter(
                Traffic.device_id == device.id,
                Traffic.timestamp >= one_hour_ago,
                Traffic.timestamp < now
            ).first()
            
            # 跳过没有数据的设备
            if not hour_stats or hour_stats.avg_in_rate is None:
                logger.info(f"设备 {device.name} (ID: {device.id}) 在过去一小时内没有流量数据")
                continue
            
            # 查找峰值时间（利用率最高的时间点）
            peak_traffic = Traffic.query.filter(
                Traffic.device_id == device.id,
                Traffic.timestamp >= one_hour_ago,
                Traffic.timestamp < now
            ).order_by(Traffic.utilization.desc()).first()
            
            peak_time = peak_traffic.timestamp if peak_traffic else now
            
            # 创建TrafficStats记录
            traffic_stats = TrafficStats(
                device_id=device.id,
                hour=now.hour,
                day=now.day,
                month=now.month,
                year=now.year,
                avg_in_rate=hour_stats.avg_in_rate,
                avg_out_rate=hour_stats.avg_out_rate,
                max_in_rate=hour_stats.max_in_rate,
                max_out_rate=hour_stats.max_out_rate,
                avg_utilization=hour_stats.avg_utilization,
                peak_time=peak_time,
                created_at=now
            )
            
            db.session.add(traffic_stats)
            stats_count += 1
        
        # 提交事务
        db.session.commit()
        logger.info(f"成功处理 {stats_count} 个设备的流量统计数据")
        return True
    
    except Exception as e:
        logger.error(f"处理流量统计数据时出错: {str(e)}")
        # 回滚事务
        db.session.rollback()
        return False

def process_daily_stats():
    """
    处理每日流量统计数据
    将前一天的详细流量数据聚合为统计数据，并可选择性地清理旧的详细数据
    """
    try:
        # 获取当前时间
        now = datetime.utcnow()
        
        # 获取昨天的日期范围
        yesterday_start = datetime(now.year, now.month, now.day) - timedelta(days=1)
        yesterday_end = datetime(now.year, now.month, now.day) - timedelta(seconds=1)
        
        # 获取所有设备
        devices = Device.query.all()
        
        daily_stats_count = 0
        
        for device in devices:
            # 检查是否已存在昨天的统计数据
            existing_stats = TrafficStats.query.filter(
                TrafficStats.device_id == device.id,
                TrafficStats.year == yesterday_start.year,
                TrafficStats.month == yesterday_start.month,
                TrafficStats.day == yesterday_start.day,
                TrafficStats.hour == 0  # 小时为0表示这是每日统计数据
            ).first()
            
            if existing_stats:
                logger.info(f"设备 {device.name} 已存在昨天 ({yesterday_start.date()}) 的统计数据")
                continue
            
            # 聚合昨天的流量数据
            daily_stats = db.session.query(
                func.avg(TrafficStats.avg_in_rate).label('avg_in_rate'),
                func.avg(TrafficStats.avg_out_rate).label('avg_out_rate'),
                func.max(TrafficStats.max_in_rate).label('max_in_rate'),
                func.max(TrafficStats.max_out_rate).label('max_out_rate'),
                func.avg(TrafficStats.avg_utilization).label('avg_utilization')
            ).filter(
                TrafficStats.device_id == device.id,
                TrafficStats.created_at >= yesterday_start,
                TrafficStats.created_at <= yesterday_end,
                TrafficStats.hour != 0  # 排除已有的每日统计数据
            ).first()
            
            # 跳过没有数据的设备
            if not daily_stats or daily_stats.avg_in_rate is None:
                logger.info(f"设备 {device.name} 在昨天没有流量统计数据")
                continue
            
            # 查找昨天峰值时间
            peak_stats = TrafficStats.query.filter(
                TrafficStats.device_id == device.id,
                TrafficStats.created_at >= yesterday_start,
                TrafficStats.created_at <= yesterday_end
            ).order_by(TrafficStats.avg_utilization.desc()).first()
            
            peak_time = peak_stats.peak_time if peak_stats else yesterday_start
            
            # 创建每日统计记录 (hour=0 表示这是每日汇总)
            daily_traffic_stats = TrafficStats(
                device_id=device.id,
                hour=0,  # 表示这是每日汇总数据
                day=yesterday_start.day,
                month=yesterday_start.month,
                year=yesterday_start.year,
                avg_in_rate=daily_stats.avg_in_rate,
                avg_out_rate=daily_stats.avg_out_rate,
                max_in_rate=daily_stats.max_in_rate,
                max_out_rate=daily_stats.max_out_rate,
                avg_utilization=daily_stats.avg_utilization,
                peak_time=peak_time,
                created_at=now
            )
            
            db.session.add(daily_traffic_stats)
            daily_stats_count += 1
        
        # 提交事务
        db.session.commit()
        logger.info(f"成功处理 {daily_stats_count} 个设备的每日流量统计数据")
        return True
    
    except Exception as e:
        logger.error(f"处理每日流量统计数据时出错: {str(e)}")
        # 回滚事务
        db.session.rollback()
        return False


def run_traffic_processor():
    """运行流量处理器"""
    logger.info("开始运行流量处理器...")
    process_traffic_stats()
    process_daily_stats()
    logger.info("流量处理器运行完成")


if __name__ == "__main__":
    # 如果直接运行此文件，则执行处理
    run_traffic_processor() 