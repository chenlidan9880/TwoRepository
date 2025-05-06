"""
数据处理流水线模块

负责对采集的原始数据进行处理、分析和挖掘，包括数据清洗、流量统计计算、异常检测和流量特征分析等功能。
采用流水线处理架构，各处理组件可以并行运行，提高系统的处理能力和响应速度。
"""

import logging
import threading
import queue
import time
import json
import numpy as np
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from flask import current_app
from app import db
from app.models.traffic import Traffic, TrafficStats
from app.models.device import Device
from app.models.alert import Alert

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 定义处理器接口
class Processor(ABC):
    """数据处理器基类，定义处理器接口"""
    
    def __init__(self, name):
        self.name = name
        self.next_processor = None
        
    def set_next(self, processor):
        """设置下一个处理器"""
        self.next_processor = processor
        return processor
        
    def process(self, data):
        """处理数据并传递给下一个处理器"""
        result = self._process_impl(data)
        
        if self.next_processor and result:
            return self.next_processor.process(result)
        return result
        
    @abstractmethod
    def _process_impl(self, data):
        """具体处理逻辑，由子类实现"""
        pass


class DataCleanProcessor(Processor):
    """数据清洗处理器"""
    
    def __init__(self):
        super().__init__("DataCleanProcessor")
        
    def _process_impl(self, data):
        """
        实现数据清洗逻辑
        - 去除异常值和无效数据
        - 填充缺失值
        - 标准化数据格式
        """
        logger.debug(f"数据清洗处理: {data.get('source_id', 'unknown')}")
        
        try:
            # 检查必要字段
            required_fields = ['source_id', 'timestamp', 'data']
            for field in required_fields:
                if field not in data:
                    logger.warning(f"数据缺少必要字段: {field}")
                    return None
                    
            # 处理时间戳
            if isinstance(data['timestamp'], str):
                try:
                    data['timestamp'] = datetime.fromisoformat(data['timestamp'])
                except ValueError:
                    # 尝试多种常见格式
                    try:
                        data['timestamp'] = datetime.strptime(data['timestamp'], '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        logger.warning(f"无效的时间戳格式: {data['timestamp']}")
                        data['timestamp'] = datetime.utcnow()
            
            # 检查并清洗数据值
            cleaned_data = {}
            for key, value in data['data'].items():
                # 去除异常值
                if isinstance(value, (int, float)):
                    # 流量值不应为负
                    if key.endswith('_bytes') or key.endswith('_packets'):
                        if value < 0:
                            logger.warning(f"发现负值流量数据: {key}={value}，已修正为0")
                            value = 0
                    
                    # 极端大值可能是错误数据
                    if key.endswith('_bytes') and value > 10**12:  # > 1 TB，可能是错误
                        logger.warning(f"发现异常大流量值: {key}={value}，已标记为可疑")
                        data['suspicious'] = True
                        
                # 将None值替换为0或适当的默认值
                if value is None:
                    if key.endswith('_bytes') or key.endswith('_packets'):
                        value = 0
                
                cleaned_data[key] = value
                
            data['data'] = cleaned_data
            data['cleaned'] = True
            
            return data
            
        except Exception as e:
            logger.error(f"数据清洗处理出错: {str(e)}")
            return None


class TrafficCalculator(Processor):
    """流量统计计算处理器"""
    
    def __init__(self):
        super().__init__("TrafficCalculator")
        
    def _process_impl(self, data):
        """
        实现流量统计计算逻辑
        - 计算流入/流出速率
        - 计算带宽利用率
        - 计算流量增长率
        """
        logger.debug(f"流量统计计算: {data.get('source_id', 'unknown')}")
        
        try:
            if not data.get('cleaned', False):
                logger.warning("收到未清洗的数据")
                return data
                
            # 初始化计算结果
            data['calculated'] = True
            data['metrics'] = {}
            
            # 提取原始数据
            raw_data = data['data']
            
            # 计算流入/流出速率 (bytes/s)
            if 'interval_seconds' in data and data['interval_seconds'] > 0:
                interval = data['interval_seconds']
                
                if 'in_bytes' in raw_data:
                    in_rate = raw_data['in_bytes'] / interval
                    data['metrics']['in_rate'] = in_rate
                    
                if 'out_bytes' in raw_data:
                    out_rate = raw_data['out_bytes'] / interval
                    data['metrics']['out_rate'] = out_rate
            
            # 计算带宽利用率
            if 'bandwidth' in raw_data and raw_data['bandwidth'] > 0:
                bandwidth = raw_data['bandwidth']  # bps
                
                if 'in_rate' in data['metrics']:
                    # 转换bytes/s为bits/s (1 byte = 8 bits)
                    in_bits_rate = data['metrics']['in_rate'] * 8
                    in_util = (in_bits_rate / bandwidth) * 100
                    data['metrics']['in_utilization'] = in_util
                    
                if 'out_rate' in data['metrics']:
                    out_bits_rate = data['metrics']['out_rate'] * 8
                    out_util = (out_bits_rate / bandwidth) * 100
                    data['metrics']['out_utilization'] = out_util
            
            # 计算历史同比数据（如果有历史数据）
            if 'historical_data' in data:
                hist_data = data['historical_data']
                
                if 'in_bytes' in raw_data and 'in_bytes' in hist_data:
                    if hist_data['in_bytes'] > 0:
                        growth_rate = ((raw_data['in_bytes'] - hist_data['in_bytes']) / hist_data['in_bytes']) * 100
                        data['metrics']['in_growth_rate'] = growth_rate
                
                if 'out_bytes' in raw_data and 'out_bytes' in hist_data:
                    if hist_data['out_bytes'] > 0:
                        growth_rate = ((raw_data['out_bytes'] - hist_data['out_bytes']) / hist_data['out_bytes']) * 100
                        data['metrics']['out_growth_rate'] = growth_rate
            
            return data
            
        except Exception as e:
            logger.error(f"流量统计计算出错: {str(e)}")
            return data


class AnomalyDetector(Processor):
    """异常检测处理器"""
    
    def __init__(self):
        super().__init__("AnomalyDetector")
        self.baseline_data = {}  # 存储基线数据
        
    def _process_impl(self, data):
        """
        实现异常检测逻辑
        - 阈值检测
        - 趋势检测
        - 模式检测
        """
        logger.debug(f"异常检测: {data.get('source_id', 'unknown')}")
        
        try:
            if not data.get('calculated', False):
                logger.warning("收到未计算的数据")
                return data
                
            # 初始化异常检测结果
            data['anomalies'] = []
            
            # 提取计算后的指标
            metrics = data.get('metrics', {})
            
            # 1. 阈值检测 - 检查带宽利用率
            if 'in_utilization' in metrics:
                in_util = metrics['in_utilization']
                
                # 带宽利用率超过80%视为异常
                if in_util > 80:
                    severity = 'warning' if in_util < 90 else 'critical'
                    anomaly = {
                        'type': 'threshold',
                        'metric': 'in_utilization',
                        'value': in_util,
                        'threshold': 80,
                        'message': f"入向带宽利用率达到{in_util:.2f}%",
                        'severity': severity
                    }
                    data['anomalies'].append(anomaly)
            
            if 'out_utilization' in metrics:
                out_util = metrics['out_utilization']
                
                # 带宽利用率超过80%视为异常
                if out_util > 80:
                    severity = 'warning' if out_util < 90 else 'critical'
                    anomaly = {
                        'type': 'threshold',
                        'metric': 'out_utilization',
                        'value': out_util,
                        'threshold': 80,
                        'message': f"出向带宽利用率达到{out_util:.2f}%",
                        'severity': severity
                    }
                    data['anomalies'].append(anomaly)
            
            # 2. 趋势检测 - 检查流量增长率
            if 'in_growth_rate' in metrics:
                growth_rate = metrics['in_growth_rate']
                
                # 流量突增50%以上视为异常
                if growth_rate > 50:
                    severity = 'warning' if growth_rate < 100 else 'critical'
                    anomaly = {
                        'type': 'trend',
                        'metric': 'in_growth_rate',
                        'value': growth_rate,
                        'threshold': 50,
                        'message': f"入向流量突增{growth_rate:.2f}%",
                        'severity': severity
                    }
                    data['anomalies'].append(anomaly)
            
            # 3. 动态基线检测
            source_id = data.get('source_id')
            if source_id and 'in_rate' in metrics:
                current_value = metrics['in_rate']
                
                # 更新或创建基线
                if source_id not in self.baseline_data:
                    # 首次见到该数据源，初始化基线
                    self.baseline_data[source_id] = {
                        'values': [current_value],
                        'mean': current_value,
                        'std': 0,
                        'last_updated': datetime.utcnow()
                    }
                else:
                    # 更新基线统计数据
                    baseline = self.baseline_data[source_id]
                    values = baseline['values'][-24:] + [current_value]  # 保留最近24个数据点
                    
                    mean = np.mean(values)
                    std = np.std(values) if len(values) > 1 else 0
                    
                    self.baseline_data[source_id] = {
                        'values': values,
                        'mean': mean,
                        'std': std,
                        'last_updated': datetime.utcnow()
                    }
                    
                    # 检查是否偏离基线
                    # 使用z-score方法，偏离3个标准差视为异常
                    if std > 0:
                        z_score = abs(current_value - mean) / std
                        if z_score > 3:
                            anomaly = {
                                'type': 'baseline',
                                'metric': 'in_rate',
                                'value': current_value,
                                'baseline': mean,
                                'z_score': z_score,
                                'message': f"入向流量偏离基线 (z={z_score:.2f})",
                                'severity': 'warning' if z_score < 5 else 'critical'
                            }
                            data['anomalies'].append(anomaly)
            
            # 生成告警
            if data['anomalies']:
                self._generate_alerts(data)
                
            return data
            
        except Exception as e:
            logger.error(f"异常检测处理出错: {str(e)}")
            return data
            
    def _generate_alerts(self, data):
        """根据检测到的异常生成告警"""
        try:
            source_id = data.get('source_id')
            timestamp = data.get('timestamp', datetime.utcnow())
            
            # 查找设备信息
            device = None
            if 'device_id' in data:
                device = Device.query.get(data['device_id'])
            
            # 为每个异常生成告警
            for anomaly in data['anomalies']:
                severity = anomaly.get('severity', 'warning')
                message = anomaly.get('message', '未知异常')
                
                # 创建告警详情
                details = {
                    'anomaly_type': anomaly.get('type'),
                    'metric': anomaly.get('metric'),
                    'value': anomaly.get('value'),
                    'threshold': anomaly.get('threshold', None),
                    'baseline': anomaly.get('baseline', None),
                    'z_score': anomaly.get('z_score', None)
                }
                
                # 构建告警标题
                title = f"流量异常: {message}"
                if device:
                    title = f"{device.name}: {title}"
                
                # 创建告警
                alert = Alert(
                    title=title,
                    message=message,
                    source_type='traffic',
                    source_id=source_id,
                    severity=severity,
                    details=json.dumps(details),
                    created_at=timestamp,
                    is_handled=False
                )
                
                db.session.add(alert)
            
            db.session.commit()
            logger.info(f"为数据源 {source_id} 生成了 {len(data['anomalies'])} 个告警")
            
        except Exception as e:
            logger.error(f"生成告警时出错: {str(e)}")
            db.session.rollback()


class TrafficFeatureAnalyzer(Processor):
    """流量特征分析处理器"""
    
    def __init__(self):
        super().__init__("TrafficFeatureAnalyzer")
        
    def _process_impl(self, data):
        """
        实现流量特征分析逻辑
        - 识别流量模式
        - 分析周期性特征
        - 识别应用类型
        """
        logger.debug(f"流量特征分析: {data.get('source_id', 'unknown')}")
        
        try:
            # 初始化特征分析结果
            data['features'] = {}
            
            # TODO: 实现更复杂的流量特征分析
            # 由于特征分析需要大量历史数据和复杂算法，这里仅提供简化实现
            
            return data
            
        except Exception as e:
            logger.error(f"流量特征分析出错: {str(e)}")
            return data


class DataPersister(Processor):
    """数据持久化处理器"""
    
    def __init__(self):
        super().__init__("DataPersister")
        
    def _process_impl(self, data):
        """
        实现数据持久化逻辑
        - 将处理后的数据保存到数据库
        - 根据数据类型选择不同的存储策略
        """
        logger.debug(f"数据持久化: {data.get('source_id', 'unknown')}")
        
        try:
            # 区分不同类型的数据
            data_type = data.get('type', 'unknown')
            
            if data_type == 'traffic':
                self._persist_traffic_data(data)
            elif data_type == 'stats':
                self._persist_stats_data(data)
            elif data_type == 'event':
                self._persist_event_data(data)
            else:
                logger.warning(f"未知的数据类型: {data_type}")
                
            data['persisted'] = True
            return data
            
        except Exception as e:
            logger.error(f"数据持久化出错: {str(e)}")
            return data
            
    def _persist_traffic_data(self, data):
        """持久化流量数据"""
        try:
            # 检查必要字段
            if 'device_id' not in data or 'interface_id' not in data or 'data' not in data:
                logger.warning("流量数据缺少必要字段")
                return
                
            # 提取数据
            device_id = data['device_id']
            interface_id = data['interface_id']
            timestamp = data.get('timestamp', datetime.utcnow())
            raw_data = data['data']
            
            # 创建Traffic记录
            traffic = Traffic(
                device_id=device_id,
                interface_id=interface_id,
                timestamp=timestamp,
                in_bytes=raw_data.get('in_bytes', 0),
                out_bytes=raw_data.get('out_bytes', 0),
                in_packets=raw_data.get('in_packets', 0),
                out_packets=raw_data.get('out_packets', 0),
                interval=data.get('interval_seconds', 300)
            )
            
            # 保存到数据库
            db.session.add(traffic)
            db.session.commit()
            
            logger.debug(f"已保存设备 {device_id} 接口 {interface_id} 的流量数据")
            
        except Exception as e:
            logger.error(f"持久化流量数据时出错: {str(e)}")
            db.session.rollback()
            
    def _persist_stats_data(self, data):
        """持久化统计数据"""
        try:
            # 检查必要字段
            if 'device_id' not in data or 'metrics' not in data:
                logger.warning("统计数据缺少必要字段")
                return
                
            # 提取数据
            device_id = data['device_id']
            timestamp = data.get('timestamp', datetime.utcnow())
            metrics = data['metrics']
            
            # 创建TrafficStats记录
            stats = TrafficStats(
                device_id=device_id,
                timestamp=timestamp,
                in_rate=metrics.get('in_rate', 0),
                out_rate=metrics.get('out_rate', 0),
                in_utilization=metrics.get('in_utilization', 0),
                out_utilization=metrics.get('out_utilization', 0),
                details=json.dumps(metrics)
            )
            
            # 保存到数据库
            db.session.add(stats)
            db.session.commit()
            
            logger.debug(f"已保存设备 {device_id} 的流量统计数据")
            
        except Exception as e:
            logger.error(f"持久化统计数据时出错: {str(e)}")
            db.session.rollback()
            
    def _persist_event_data(self, data):
        """持久化事件数据"""
        # 事件数据持久化逻辑，根据实际需求实现
        pass


class ProcessorPipeline:
    """数据处理流水线"""
    
    def __init__(self):
        self.processors = {}
        self.pipelines = {}
        self.queue = queue.Queue()
        self.worker_threads = []
        self.running = False
        
    def add_processor(self, processor):
        """添加处理器"""
        self.processors[processor.name] = processor
        return processor
        
    def create_pipeline(self, name, processor_names):
        """创建处理流水线"""
        if not processor_names:
            logger.warning(f"创建流水线 {name} 失败: 没有指定处理器")
            return None
            
        # 检查所有处理器是否存在
        for processor_name in processor_names:
            if processor_name not in self.processors:
                logger.warning(f"创建流水线 {name} 失败: 处理器 {processor_name} 不存在")
                return None
                
        # 构建处理链
        head = self.processors[processor_names[0]]
        current = head
        
        for processor_name in processor_names[1:]:
            next_processor = self.processors[processor_name]
            current.set_next(next_processor)
            current = next_processor
            
        self.pipelines[name] = head
        logger.info(f"已创建处理流水线: {name}")
        return head
        
    def process(self, pipeline_name, data):
        """将数据提交到指定的处理流水线"""
        if pipeline_name not in self.pipelines:
            logger.warning(f"处理流水线 {pipeline_name} 不存在")
            return None
            
        # 添加到处理队列
        self.queue.put((pipeline_name, data))
        return True
        
    def start(self, num_workers=3):
        """启动处理流水线"""
        self.running = True
        
        # 创建工作线程
        for i in range(num_workers):
            thread = threading.Thread(target=self._worker_loop)
            thread.daemon = True
            thread.start()
            self.worker_threads.append(thread)
            
        logger.info(f"数据处理流水线已启动, 工作线程数: {num_workers}")
        
    def stop(self):
        """停止处理流水线"""
        self.running = False
        
        # 等待所有工作线程结束
        for thread in self.worker_threads:
            thread.join(timeout=3.0)
            
        logger.info("数据处理流水线已停止")
        
    def _worker_loop(self):
        """工作线程循环"""
        while self.running:
            try:
                # 从队列获取数据，设置超时以便能够响应停止信号
                try:
                    pipeline_name, data = self.queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                    
                # 获取处理流水线
                pipeline = self.pipelines.get(pipeline_name)
                if not pipeline:
                    logger.warning(f"未找到处理流水线: {pipeline_name}")
                    self.queue.task_done()
                    continue
                    
                # 处理数据
                try:
                    result = pipeline.process(data)
                    logger.debug(f"数据处理完成: {data.get('source_id', 'unknown')}")
                except Exception as e:
                    logger.error(f"数据处理出错: {str(e)}")
                    
                self.queue.task_done()
                
            except Exception as e:
                logger.error(f"工作线程出错: {str(e)}")
                time.sleep(1)  # 避免因错误导致CPU使用率过高


# 创建全局处理流水线实例
processor_pipeline = ProcessorPipeline()

def init_processor_pipeline():
    """初始化数据处理流水线"""
    try:
        # 创建处理器
        data_clean = DataCleanProcessor()
        traffic_calc = TrafficCalculator()
        anomaly_detector = AnomalyDetector()
        feature_analyzer = TrafficFeatureAnalyzer()
        data_persister = DataPersister()
        
        # 添加处理器
        processor_pipeline.add_processor(data_clean)
        processor_pipeline.add_processor(traffic_calc)
        processor_pipeline.add_processor(anomaly_detector)
        processor_pipeline.add_processor(feature_analyzer)
        processor_pipeline.add_processor(data_persister)
        
        # 创建流水线
        processor_pipeline.create_pipeline(
            'traffic_processing',
            ['DataCleanProcessor', 'TrafficCalculator', 'AnomalyDetector', 'DataPersister']
        )
        
        processor_pipeline.create_pipeline(
            'feature_analysis',
            ['DataCleanProcessor', 'TrafficFeatureAnalyzer', 'DataPersister']
        )
        
        # 启动处理流水线
        processor_pipeline.start()
        
        logger.info("数据处理流水线初始化完成")
        return True
    except Exception as e:
        logger.error(f"初始化数据处理流水线失败: {str(e)}")
        return False
        
def stop_processor_pipeline():
    """停止数据处理流水线"""
    try:
        processor_pipeline.stop()
        logger.info("数据处理流水线已停止")
        return True
    except Exception as e:
        logger.error(f"停止数据处理流水线失败: {str(e)}")
        return False
        
def submit_data(data, pipeline='traffic_processing'):
    """提交数据到处理流水线"""
    return processor_pipeline.process(pipeline, data) 