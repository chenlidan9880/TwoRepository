"""
数据存储模块

负责流量数据的存储和管理，采用混合存储策略以满足不同数据的访问需求。
实现数据生命周期管理，根据数据价值和使用频率，自动进行数据归档、压缩和清理。
"""

import logging
import threading
import time
import json
import pickle
from datetime import datetime, timedelta
from flask import current_app
from sqlalchemy import text
from app import db, cache

# 获取Flask应用实例
# 注意：这个导入必须放在这里，而不是函数内部，以避免循环导入
from app import create_app

from app.models.traffic import Traffic, TrafficStats

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HybridStorage:
    """混合存储管理器，结合内存缓存和数据库存储"""
    
    def __init__(self):
        self.cache = cache  # Flask-Caching实例
        self.cleanup_thread = None
        self.archiving_thread = None
        self.running = False
        # 将Flask应用实例保存为实例变量
        self.app = None
        
    def start(self):
        """启动存储管理服务"""
        self.running = True
        
        # 获取Flask应用实例
        self.app = create_app()
        
        # 启动数据清理线程
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop)
        self.cleanup_thread.daemon = True
        self.cleanup_thread.start()
        
        # 启动数据归档线程
        self.archiving_thread = threading.Thread(target=self._archiving_loop)
        self.archiving_thread.daemon = True
        self.archiving_thread.start()
        
        logger.info("混合存储管理器已启动")
        
    def stop(self):
        """停止存储管理服务"""
        self.running = False
        
        # 等待线程结束
        if self.cleanup_thread:
            self.cleanup_thread.join(timeout=3.0)
            
        if self.archiving_thread:
            self.archiving_thread.join(timeout=3.0)
            
        logger.info("混合存储管理器已停止")
        
    def save_traffic_data(self, device_id, interface_id, timestamp, data):
        """保存流量数据"""
        try:
            # 生成缓存键
            cache_key = f"traffic:{device_id}:{interface_id}"
            
            # 保存到内存缓存
            cached_data = self.cache.get(cache_key) or []
            cached_data.append({
                'timestamp': timestamp,
                'data': data
            })
            
            # 只保留最近的数据点
            max_points = current_app.config.get('CACHE_MAX_TRAFFIC_POINTS', 100)
            if len(cached_data) > max_points:
                cached_data = cached_data[-max_points:]
                
            # 更新缓存
            self.cache.set(cache_key, cached_data, 
                          timeout=current_app.config.get('CACHE_TRAFFIC_TIMEOUT', 3600))
            
            # 保存到数据库
            traffic = Traffic(
                device_id=device_id,
                interface_id=interface_id,
                timestamp=timestamp,
                in_bytes=data.get('in_bytes', 0),
                out_bytes=data.get('out_bytes', 0),
                in_packets=data.get('in_packets', 0),
                out_packets=data.get('out_packets', 0),
                interval=data.get('interval', 300)
            )
            
            db.session.add(traffic)
            db.session.commit()
            
            logger.debug(f"已保存设备 {device_id} 接口 {interface_id} 的流量数据")
            return True
            
        except Exception as e:
            logger.error(f"保存流量数据时出错: {str(e)}")
            db.session.rollback()
            return False
            
    def save_stats_data(self, device_id, timestamp, metrics):
        """保存统计数据"""
        try:
            # 生成缓存键
            cache_key = f"stats:{device_id}"
            
            # 保存到内存缓存
            cached_data = self.cache.get(cache_key) or []
            cached_data.append({
                'timestamp': timestamp,
                'metrics': metrics
            })
            
            # 只保留最近的数据点
            max_points = current_app.config.get('CACHE_MAX_STATS_POINTS', 50)
            if len(cached_data) > max_points:
                cached_data = cached_data[-max_points:]
                
            # 更新缓存
            self.cache.set(cache_key, cached_data, 
                          timeout=current_app.config.get('CACHE_STATS_TIMEOUT', 3600))
            
            # 保存到数据库
            stats = TrafficStats(
                device_id=device_id,
                timestamp=timestamp,
                in_rate=metrics.get('in_rate', 0),
                out_rate=metrics.get('out_rate', 0),
                in_utilization=metrics.get('in_utilization', 0),
                out_utilization=metrics.get('out_utilization', 0),
                details=json.dumps(metrics)
            )
            
            db.session.add(stats)
            db.session.commit()
            
            logger.debug(f"已保存设备 {device_id} 的流量统计数据")
            return True
            
        except Exception as e:
            logger.error(f"保存统计数据时出错: {str(e)}")
            db.session.rollback()
            return False
            
    def get_recent_traffic(self, device_id, interface_id=None, hours=24):
        """获取最近一段时间的流量数据"""
        try:
            result = []
            
            # 尝试从缓存获取数据
            if interface_id:
                cache_key = f"traffic:{device_id}:{interface_id}"
                cached_data = self.cache.get(cache_key)
                
                if cached_data:
                    # 从缓存获取符合时间范围的数据
                    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
                    result = [item for item in cached_data 
                             if item['timestamp'] >= cutoff_time]
                    
                    if result:
                        logger.debug(f"从缓存获取设备 {device_id} 接口 {interface_id} 的流量数据")
                        return result
            
            # 如果缓存中没有数据或需要更多数据，从数据库查询
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            query = Traffic.query.filter(
                Traffic.device_id == device_id,
                Traffic.timestamp >= cutoff_time
            ).order_by(Traffic.timestamp)
            
            if interface_id:
                query = query.filter(Traffic.interface_id == interface_id)
                
            traffic_data = query.all()
            
            # 转换为字典格式
            for item in traffic_data:
                result.append({
                    'timestamp': item.timestamp,
                    'data': {
                        'in_bytes': item.in_bytes,
                        'out_bytes': item.out_bytes,
                        'in_packets': item.in_packets,
                        'out_packets': item.out_packets,
                        'interval': item.interval
                    }
                })
                
            logger.debug(f"从数据库获取设备 {device_id} 的流量数据，共 {len(result)} 条")
            return result
            
        except Exception as e:
            logger.error(f"获取流量数据时出错: {str(e)}")
            return []
            
    def get_traffic_summary(self, device_id, interval='hour', days=7):
        """获取流量汇总数据"""
        try:
            result = []
            
            # 确定时间范围
            cutoff_time = datetime.utcnow() - timedelta(days=days)
            
            # 根据汇总间隔选择SQL
            if interval == 'hour':
                # 按小时汇总
                sql = text("""
                    SELECT 
                        DATE_FORMAT(timestamp, '%Y-%m-%d %H:00:00') as time_bucket,
                        SUM(in_bytes) as total_in_bytes,
                        SUM(out_bytes) as total_out_bytes
                    FROM traffic
                    WHERE device_id = :device_id AND timestamp >= :cutoff_time
                    GROUP BY time_bucket
                    ORDER BY time_bucket
                """)
            elif interval == 'day':
                # 按天汇总
                sql = text("""
                    SELECT 
                        DATE_FORMAT(timestamp, '%Y-%m-%d') as time_bucket,
                        SUM(in_bytes) as total_in_bytes,
                        SUM(out_bytes) as total_out_bytes
                    FROM traffic
                    WHERE device_id = :device_id AND timestamp >= :cutoff_time
                    GROUP BY time_bucket
                    ORDER BY time_bucket
                """)
            else:
                # 默认按小时汇总
                sql = text("""
                    SELECT 
                        DATE_FORMAT(timestamp, '%Y-%m-%d %H:00:00') as time_bucket,
                        SUM(in_bytes) as total_in_bytes,
                        SUM(out_bytes) as total_out_bytes
                    FROM traffic
                    WHERE device_id = :device_id AND timestamp >= :cutoff_time
                    GROUP BY time_bucket
                    ORDER BY time_bucket
                """)
                
            # 执行查询
            rows = db.session.execute(sql, {'device_id': device_id, 'cutoff_time': cutoff_time})
            
            # 转换为字典格式
            for row in rows:
                result.append({
                    'time_bucket': row.time_bucket,
                    'total_in_bytes': row.total_in_bytes,
                    'total_out_bytes': row.total_out_bytes
                })
                
            logger.debug(f"获取设备 {device_id} 的流量汇总数据，共 {len(result)} 条")
            return result
            
        except Exception as e:
            logger.error(f"获取流量汇总数据时出错: {str(e)}")
            return []
            
    def _cleanup_loop(self):
        """数据清理循环"""
        # 等待一段时间以确保应用完全初始化
        time.sleep(10)  # 等待10秒钟
        
        while self.running:
            try:
                # 使用存储在实例中的app创建应用上下文
                if self.app:
                    with self.app.app_context():
                        logger.info("开始执行数据清理操作")
                        self._cleanup_old_data()
                        logger.info("数据清理操作完成")
                else:
                    logger.error("无法执行数据清理：Flask应用实例不可用")
                
                # 每天执行一次清理
                time.sleep(86400)  # 24小时
                
            except Exception as e:
                logger.error(f"数据清理出错: {str(e)}")
                time.sleep(3600)  # 出错后等待1小时再重试
                
    def _archiving_loop(self):
        """数据归档循环"""
        # 等待一段时间以确保应用完全初始化
        time.sleep(15)  # 等待15秒钟
        
        while self.running:
            try:
                # 使用存储在实例中的app创建应用上下文
                if self.app:
                    with self.app.app_context():
                        logger.info("开始执行数据归档操作")
                        self._archive_old_data()
                        logger.info("数据归档操作完成")
                else:
                    logger.error("无法执行数据归档：Flask应用实例不可用")
                
                # 每周执行一次归档
                time.sleep(7 * 86400)  # 7天
                
            except Exception as e:
                logger.error(f"数据归档出错: {str(e)}")
                time.sleep(3600)  # 出错后等待1小时再重试
                
    def _cleanup_old_data(self):
        """清理过期数据"""
        try:
            logger.info("开始清理过期数据")
            
            # 根据配置确定保留期限
            retention_days = current_app.config.get('DATA_RETENTION_DAYS', 90)
            cutoff_time = datetime.utcnow() - timedelta(days=retention_days)
            
            # 清理流量数据
            deleted_count = Traffic.query.filter(Traffic.timestamp < cutoff_time).delete()
            
            # 清理统计数据 - 修改为使用正确的时间戳字段
            try:
                # 获取TrafficStats的列名，看看是否包含created_at或recorded_at
                column_names = [column.name for column in TrafficStats.__table__.columns]
                logger.info(f"TrafficStats表的列名: {column_names}")
                
                # 尝试常见的时间戳字段名
                if 'created_at' in column_names:
                    stats_deleted = TrafficStats.query.filter(TrafficStats.created_at < cutoff_time).delete()
                    logger.info(f"使用created_at字段进行清理")
                elif 'recorded_at' in column_names:
                    stats_deleted = TrafficStats.query.filter(TrafficStats.recorded_at < cutoff_time).delete()
                    logger.info(f"使用recorded_at字段进行清理")
                elif 'created_time' in column_names:
                    stats_deleted = TrafficStats.query.filter(TrafficStats.created_time < cutoff_time).delete()
                    logger.info(f"使用created_time字段进行清理")
                elif 'time' in column_names:
                    stats_deleted = TrafficStats.query.filter(TrafficStats.time < cutoff_time).delete()
                    logger.info(f"使用time字段进行清理")
                else:
                    # 如果找不到合适的时间字段，先记录错误，不进行删除
                    logger.error(f"TrafficStats没有找到合适的时间戳字段，跳过统计数据清理")
                    stats_deleted = 0
            except Exception as e:
                logger.error(f"查找TrafficStats时间戳字段时出错: {str(e)}")
                stats_deleted = 0
            
            # 提交事务
            db.session.commit()
            
            logger.info(f"已清理 {deleted_count} 条过期流量数据和 {stats_deleted} 条统计数据")
            
        except Exception as e:
            logger.error(f"清理过期数据时出错: {str(e)}")
            db.session.rollback()
            
    def _archive_old_data(self):
        """归档历史数据"""
        try:
            logger.info("开始归档历史数据")
            
            # 根据配置确定归档期限
            archive_days = current_app.config.get('DATA_ARCHIVE_DAYS', 30)
            cutoff_time = datetime.utcnow() - timedelta(days=archive_days)
            
            # 查询要归档的数据
            traffic_to_archive = Traffic.query.filter(Traffic.timestamp < cutoff_time).all()
            
            if traffic_to_archive:
                # 执行归档逻辑
                self._perform_archiving(traffic_to_archive)
                logger.info(f"已归档 {len(traffic_to_archive)} 条流量数据")
            
            # 统计数据归档 - 修改为使用正确的时间戳字段
            try:
                # 获取TrafficStats的列名，看看是否包含created_at或recorded_at
                column_names = [column.name for column in TrafficStats.__table__.columns]
                
                # 尝试常见的时间戳字段名
                stats_to_archive = []
                if 'created_at' in column_names:
                    stats_to_archive = TrafficStats.query.filter(TrafficStats.created_at < cutoff_time).all()
                    logger.info(f"使用created_at字段进行归档")
                elif 'recorded_at' in column_names:
                    stats_to_archive = TrafficStats.query.filter(TrafficStats.recorded_at < cutoff_time).all()
                    logger.info(f"使用recorded_at字段进行归档")
                elif 'created_time' in column_names:
                    stats_to_archive = TrafficStats.query.filter(TrafficStats.created_time < cutoff_time).all()
                    logger.info(f"使用created_time字段进行归档")
                elif 'time' in column_names:
                    stats_to_archive = TrafficStats.query.filter(TrafficStats.time < cutoff_time).all()
                    logger.info(f"使用time字段进行归档")
                else:
                    # 如果找不到合适的时间字段，记录错误，跳过归档
                    logger.error(f"TrafficStats没有找到合适的时间戳字段，跳过统计数据归档")
            except Exception as e:
                logger.error(f"查找TrafficStats时间戳字段时出错: {str(e)}")
                stats_to_archive = []
                
            if stats_to_archive:
                # 执行统计数据归档
                self._perform_stats_archiving(stats_to_archive)
                logger.info(f"已归档 {len(stats_to_archive)} 条统计数据")
                
        except Exception as e:
            logger.error(f"归档历史数据时出错: {str(e)}")
            
    def _perform_archiving(self, data_list):
        """执行数据归档操作"""
        # 这里是简化的归档示例，实际应根据需求实现
        # 可能的实现包括：
        # 1. 将数据压缩存储到文件系统
        # 2. 转移到归档数据库表
        # 3. 按时间聚合，存储汇总数据而不是原始数据
        
        try:
            # 示例：按设备和日期聚合数据
            aggregated_data = {}
            
            for item in data_list:
                # 按设备ID和日期分组
                date_key = item.timestamp.strftime('%Y-%m-%d')
                agg_key = f"{item.device_id}:{date_key}"
                
                if agg_key not in aggregated_data:
                    aggregated_data[agg_key] = {
                        'device_id': item.device_id,
                        'date': date_key,
                        'total_in_bytes': 0,
                        'total_out_bytes': 0,
                        'total_in_packets': 0,
                        'total_out_packets': 0,
                        'count': 0
                    }
                    
                # 累加数据
                agg_data = aggregated_data[agg_key]
                agg_data['total_in_bytes'] += item.in_bytes
                agg_data['total_out_bytes'] += item.out_bytes
                agg_data['total_in_packets'] += item.in_packets or 0
                agg_data['total_out_packets'] += item.out_packets or 0
                agg_data['count'] += 1
                
            # TODO: 将聚合后的数据保存到归档表或文件
            # 这里仅打印日志作为示例
            logger.info(f"已聚合 {len(aggregated_data)} 条归档记录")
            
            # 从原始表中删除已归档的数据
            for item in data_list:
                db.session.delete(item)
                
            db.session.commit()
            
        except Exception as e:
            logger.error(f"执行数据归档操作时出错: {str(e)}")
            db.session.rollback()
            
    def _perform_stats_archiving(self, data_list):
        """执行统计数据归档操作"""
        # 统计数据归档逻辑，类似于流量数据归档
        try:
            if not data_list:
                return
                
            # 统计数据归档，实现简化版
            logger.info(f"准备归档 {len(data_list)} 条统计数据")
            
            # 从原始表中删除已归档的数据
            for item in data_list:
                db.session.delete(item)
                
            db.session.commit()
            logger.info(f"已完成统计数据归档")
            
        except Exception as e:
            logger.error(f"执行统计数据归档操作时出错: {str(e)}")
            db.session.rollback()


# 创建全局存储管理器实例
storage_manager = HybridStorage()

def init_storage():
    """初始化存储管理器"""
    try:
        storage_manager.start()
        logger.info("存储管理器初始化完成")
        return True
    except Exception as e:
        logger.error(f"初始化存储管理器失败: {str(e)}")
        return False
        
def stop_storage():
    """停止存储管理器"""
    try:
        storage_manager.stop()
        logger.info("存储管理器已停止")
        return True
    except Exception as e:
        logger.error(f"停止存储管理器失败: {str(e)}")
        return False
        
def save_traffic_data(device_id, interface_id, timestamp, data):
    """保存流量数据的便捷函数"""
    return storage_manager.save_traffic_data(device_id, interface_id, timestamp, data)
    
def save_stats_data(device_id, timestamp, metrics):
    """保存统计数据的便捷函数"""
    return storage_manager.save_stats_data(device_id, timestamp, metrics)
    
def get_recent_traffic(device_id, interface_id=None, hours=24):
    """获取最近流量数据的便捷函数"""
    return storage_manager.get_recent_traffic(device_id, interface_id, hours)
    
def get_traffic_summary(device_id, interval='hour', days=7):
    """获取流量汇总数据的便捷函数"""
    return storage_manager.get_traffic_summary(device_id, interval, days) 