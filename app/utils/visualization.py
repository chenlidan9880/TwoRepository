"""
数据可视化模块

负责生成各类数据可视化组件，包括热力图、趋势图、设备类型分布图等。
提供数据预处理和格式转换功能，将原始数据转换为前端可视化所需的格式。
"""

import logging
import json
import math
from datetime import datetime, timedelta
from flask import current_app
from app import db
from app.models.device import Device
from app.models.traffic import Traffic, TrafficStats
from app.models.terminal import Terminal

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HeatmapGenerator:
    """流量热力图生成器"""
    
    def __init__(self):
        self.device_locations = {}
        # 不在初始化时加载设备位置信息，而是在需要时加载
        self._locations_loaded = False
        
    def _load_device_locations(self):
        """加载设备位置信息"""
        if self._locations_loaded:
            return
            
        try:
            devices = Device.query.all()
            
            for device in devices:
                if device.location:
                    # 尝试解析位置坐标
                    coords = self._parse_location(device.location)
                    if coords:
                        self.device_locations[device.id] = coords
                        
            logger.info(f"已加载 {len(self.device_locations)} 个设备的位置信息")
            self._locations_loaded = True
            
        except Exception as e:
            logger.error(f"加载设备位置信息时出错: {str(e)}")
            
    def _parse_location(self, location_str):
        """解析位置字符串为坐标"""
        try:
            # 支持多种位置格式
            
            # 1. 直接坐标格式 "x,y"
            if ',' in location_str:
                parts = location_str.split(',')
                if len(parts) >= 2:
                    try:
                        x = float(parts[0].strip())
                        y = float(parts[1].strip())
                        return {'x': x, 'y': y}
                    except ValueError:
                        pass
            
            # 2. JSON格式 {"x": 100, "y": 200}
            if location_str.startswith('{') and location_str.endswith('}'):
                try:
                    coords = json.loads(location_str)
                    if 'x' in coords and 'y' in coords:
                        return coords
                except json.JSONDecodeError:
                    pass
            
            # 3. 预定义位置映射
            location_map = {
                '网络中心': {'x': 500, 'y': 300},
                '教学楼': {'x': 300, 'y': 200},
                '图书馆': {'x': 400, 'y': 400},
                '宿舍楼': {'x': 600, 'y': 500},
                '行政楼': {'x': 700, 'y': 300},
                '实验室': {'x': 200, 'y': 300}
            }
            
            if location_str in location_map:
                return location_map[location_str]
                
            return None
            
        except Exception as e:
            logger.error(f"解析位置字符串时出错: {str(e)}")
            return None
            
    def generate_heatmap_data(self, time_range='hour'):
        """生成热力图数据"""
        try:
            # 确保设备位置信息已加载
            self._load_device_locations()
            
            # 确定时间范围
            end_time = datetime.utcnow()
            
            if time_range == 'hour':
                start_time = end_time - timedelta(hours=1)
            elif time_range == 'day':
                start_time = end_time - timedelta(days=1)
            elif time_range == 'week':
                start_time = end_time - timedelta(weeks=1)
            else:
                start_time = end_time - timedelta(hours=1)
                
            # 获取设备流量数据
            device_traffic = self._get_device_traffic(start_time, end_time)
            
            # 生成热力图数据点
            heatmap_data = []
            
            for device_id, traffic_info in device_traffic.items():
                if device_id in self.device_locations:
                    location = self.device_locations[device_id]
                    
                    # 计算热力值（基于流量大小）
                    intensity = self._calculate_intensity(traffic_info['total_bytes'])
                    
                    data_point = {
                        'x': location['x'],
                        'y': location['y'],
                        'value': intensity,
                        'device_id': device_id,
                        'device_name': traffic_info['device_name'],
                        'traffic': traffic_info['total_bytes'],
                        'in_traffic': traffic_info['in_bytes'],
                        'out_traffic': traffic_info['out_bytes']
                    }
                    
                    heatmap_data.append(data_point)
                    
            logger.info(f"已生成 {len(heatmap_data)} 个热力图数据点")
            
            # 生成热力图配置
            heatmap_config = {
                'radius': 40,
                'maxOpacity': 0.8,
                'minOpacity': 0.1,
                'blur': 0.85,
                'gradient': {
                    '0.4': 'blue',
                    '0.6': 'green',
                    '0.8': 'yellow',
                    '1.0': 'red'
                }
            }
            
            return {
                'data': heatmap_data,
                'config': heatmap_config,
                'time_range': time_range,
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"生成热力图数据时出错: {str(e)}")
            return {'data': [], 'config': {}, 'error': str(e)}
            
    def _get_device_traffic(self, start_time, end_time):
        """获取设备流量数据"""
        try:
            result = {}
            
            # 查询时间范围内的流量数据
            traffic_data = db.session.query(
                Traffic.device_id,
                db.func.sum(Traffic.in_bytes).label('total_in_bytes'),
                db.func.sum(Traffic.out_bytes).label('total_out_bytes')
            ).filter(
                Traffic.timestamp >= start_time,
                Traffic.timestamp <= end_time
            ).group_by(Traffic.device_id).all()
            
            # 设备名称映射
            device_names = {}
            for device in Device.query.all():
                device_names[device.id] = device.name
                
            # 处理查询结果
            for item in traffic_data:
                device_id = item.device_id
                in_bytes = item.total_in_bytes or 0
                out_bytes = item.total_out_bytes or 0
                total_bytes = in_bytes + out_bytes
                
                result[device_id] = {
                    'device_name': device_names.get(device_id, f"设备 {device_id}"),
                    'in_bytes': in_bytes,
                    'out_bytes': out_bytes,
                    'total_bytes': total_bytes
                }
                
            return result
                
        except Exception as e:
            logger.error(f"获取设备流量数据时出错: {str(e)}")
            return {}
            
    def _calculate_intensity(self, bytes_count):
        """根据流量大小计算热力值"""
        # 使用对数缩放，避免极端值导致其他点不可见
        if bytes_count <= 0:
            return 0
            
        # 基本缩放策略
        # 假设低于1MB的流量强度较低，大于1GB的流量强度较高
        log_value = math.log10(bytes_count + 1)  # +1避免log(0)
        
        # 缩放到0-1范围
        max_expected_log = 9  # 10^9 = 1GB
        scaled_value = min(log_value / max_expected_log, 1.0)
        
        return scaled_value


class TrendChartGenerator:
    """趋势图生成器"""
    
    def generate_traffic_trend(self, device_id=None, time_range='day', interval='5min'):
        """生成流量趋势图数据"""
        try:
            # 确定时间范围
            end_time = datetime.utcnow()
            
            if time_range == 'hour':
                start_time = end_time - timedelta(hours=1)
                if interval == '5min':
                    group_interval = 300  # 5分钟
                else:
                    group_interval = 60  # 1分钟
            elif time_range == 'day':
                start_time = end_time - timedelta(days=1)
                if interval == 'hour':
                    group_interval = 3600  # 1小时
                else:
                    group_interval = 300  # 5分钟
            elif time_range == 'week':
                start_time = end_time - timedelta(weeks=1)
                group_interval = 3600  # 1小时
            elif time_range == 'month':
                start_time = end_time - timedelta(days=30)
                group_interval = 86400  # 1天
            else:
                start_time = end_time - timedelta(hours=24)
                group_interval = 300  # 默认5分钟
                
            # 查询流量数据
            if device_id:
                # 单设备趋势
                traffic_data = self._get_device_trend(device_id, start_time, end_time, group_interval)
                
                return {
                    'time_range': time_range,
                    'interval': interval,
                    'start_time': start_time.isoformat(),
                    'end_time': end_time.isoformat(),
                    'device_id': device_id,
                    'series': traffic_data
                }
            else:
                # 全局趋势
                traffic_data = self._get_global_trend(start_time, end_time, group_interval)
                
                return {
                    'time_range': time_range,
                    'interval': interval,
                    'start_time': start_time.isoformat(),
                    'end_time': end_time.isoformat(),
                    'series': traffic_data
                }
                
        except Exception as e:
            logger.error(f"生成流量趋势图数据时出错: {str(e)}")
            return {'series': [], 'error': str(e)}
            
    def _get_device_trend(self, device_id, start_time, end_time, interval_seconds):
        """获取单个设备的流量趋势"""
        try:
            # 查询时间范围内的原始流量数据
            traffic_records = Traffic.query.filter(
                Traffic.device_id == device_id,
                Traffic.timestamp >= start_time,
                Traffic.timestamp <= end_time
            ).order_by(Traffic.timestamp).all()
            
            # 按时间间隔分组聚合
            grouped_data = self._group_by_interval(traffic_records, interval_seconds)
            
            # 构造返回数据
            in_series = []
            out_series = []
            
            for timestamp, data in sorted(grouped_data.items()):
                in_series.append({
                    'x': timestamp,
                    'y': data['in_bytes'] / (interval_seconds if interval_seconds > 0 else 300) * 8  # 转换为bits/s
                })
                
                out_series.append({
                    'x': timestamp,
                    'y': data['out_bytes'] / (interval_seconds if interval_seconds > 0 else 300) * 8  # 转换为bits/s
                })
                
            return [
                {'name': '入站流量', 'data': in_series, 'type': 'in'},
                {'name': '出站流量', 'data': out_series, 'type': 'out'}
            ]
            
        except Exception as e:
            logger.error(f"获取设备趋势数据时出错: {str(e)}")
            return []
            
    def _get_global_trend(self, start_time, end_time, interval_seconds):
        """获取全局流量趋势"""
        try:
            # 查询时间范围内所有设备的原始流量数据
            traffic_records = Traffic.query.filter(
                Traffic.timestamp >= start_time,
                Traffic.timestamp <= end_time
            ).order_by(Traffic.timestamp).all()
            
            # 按时间间隔分组聚合
            grouped_data = self._group_by_interval(traffic_records, interval_seconds)
            
            # 构造返回数据
            in_series = []
            out_series = []
            
            for timestamp, data in sorted(grouped_data.items()):
                in_series.append({
                    'x': timestamp,
                    'y': data['in_bytes'] / (interval_seconds if interval_seconds > 0 else 300) * 8  # 转换为bits/s
                })
                
                out_series.append({
                    'x': timestamp,
                    'y': data['out_bytes'] / (interval_seconds if interval_seconds > 0 else 300) * 8  # 转换为bits/s
                })
                
            return [
                {'name': '入站流量', 'data': in_series, 'type': 'in'},
                {'name': '出站流量', 'data': out_series, 'type': 'out'}
            ]
            
        except Exception as e:
            logger.error(f"获取全局趋势数据时出错: {str(e)}")
            return []
            
    def _group_by_interval(self, traffic_records, interval_seconds):
        """将流量记录按时间间隔分组聚合"""
        grouped_data = {}
        
        for record in traffic_records:
            # 计算时间戳所在的时间间隔
            timestamp = record.timestamp
            interval_start = timestamp.replace(
                microsecond=0,
                second=timestamp.second - (timestamp.second % 60),
                minute=timestamp.minute - (timestamp.minute % (interval_seconds // 60))
            )
            
            if interval_seconds >= 3600:
                interval_start = interval_start.replace(minute=0)
                
            if interval_seconds >= 86400:
                interval_start = interval_start.replace(hour=0)
                
            interval_key = interval_start.isoformat()
            
            # 累加该间隔内的流量
            if interval_key not in grouped_data:
                grouped_data[interval_key] = {
                    'in_bytes': 0,
                    'out_bytes': 0
                }
                
            grouped_data[interval_key]['in_bytes'] += record.in_bytes
            grouped_data[interval_key]['out_bytes'] += record.out_bytes
            
        return grouped_data


class DeviceDistributionGenerator:
    """设备分布图生成器"""
    
    def generate_terminal_distribution(self):
        """生成终端设备类型分布数据"""
        try:
            # 查询终端设备类型分布
            terminal_types = db.session.query(
                Terminal.device_type,
                db.func.count(Terminal.id).label('count')
            ).group_by(Terminal.device_type).all()
            
            # 构造返回数据
            result = []
            
            for item in terminal_types:
                device_type = item.device_type or '未知'
                count = item.count
                
                result.append({
                    'name': device_type,
                    'value': count
                })
                
            return result
            
        except Exception as e:
            logger.error(f"生成终端设备类型分布数据时出错: {str(e)}")
            return []
            

# 创建全局可视化生成器实例
heatmap_generator = HeatmapGenerator()
trend_chart_generator = TrendChartGenerator()
device_distribution_generator = DeviceDistributionGenerator()

def get_heatmap_data(time_range='hour'):
    """获取热力图数据的便捷函数"""
    return heatmap_generator.generate_heatmap_data(time_range)
    
def get_traffic_trend(device_id=None, time_range='day', interval='5min'):
    """获取流量趋势图数据的便捷函数"""
    return trend_chart_generator.generate_traffic_trend(device_id, time_range, interval)
    
def get_terminal_distribution():
    """获取终端设备类型分布数据的便捷函数"""
    return device_distribution_generator.generate_terminal_distribution() 