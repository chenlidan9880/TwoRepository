"""
NetFlow/sFlow数据采集模块

负责接收和解析来自网络设备的NetFlow/sFlow流量数据，为系统提供细粒度的流量信息。
支持NetFlow v5/v9和sFlow v5协议。
"""

import socket
import struct
import threading
import time
import logging
import json
from datetime import datetime
from flask import current_app
from app import db
from app.models.traffic import Traffic
from app.models.device import Device

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# NetFlow v5包头格式
NETFLOW_V5_HEADER_FORMAT = '!HHIIIIBBH'
# NetFlow v5记录格式
NETFLOW_V5_RECORD_FORMAT = '!IIIIHHHHHIIIIHHBBBBHHBBI'

# sFlow配置
SFLOW_PORT = 6343
NETFLOW_PORT = 2055

class FlowCollector:
    """流量收集器基类，定义通用接口"""
    
    def __init__(self, db_session=None):
        self.db_session = db_session
        self.running = False
        self.collectors = []
        self.cache = {}  # 用于暂存处理结果
    
    def start(self):
        """启动收集器"""
        self.running = True
        logger.info("流量收集器已启动")
    
    def stop(self):
        """停止收集器"""
        self.running = False
        logger.info("流量收集器已停止")
        
    def save_flow_data(self, device_ip, interface_id, in_bytes, out_bytes, timestamp=None):
        """保存流量数据到数据库"""
        if not timestamp:
            timestamp = datetime.utcnow()
            
        try:
            # 查找设备
            device = Device.query.filter_by(ip_address=device_ip).first()
            if not device:
                logger.warning(f"未找到IP为{device_ip}的设备")
                return False
                
            # 创建流量记录
            traffic = Traffic(
                device_id=device.id,
                interface_id=interface_id,
                timestamp=timestamp,
                in_bytes=in_bytes,
                out_bytes=out_bytes,
                interval=300  # 默认5分钟间隔
            )
            
            # 保存到数据库
            if self.db_session:
                self.db_session.add(traffic)
                self.db_session.commit()
            else:
                db.session.add(traffic)
                db.session.commit()
                
            logger.debug(f"已保存设备{device_ip}接口{interface_id}的流量数据")
            return True
            
        except Exception as e:
            logger.error(f"保存流量数据时出错: {str(e)}")
            if self.db_session:
                self.db_session.rollback()
            else:
                db.session.rollback()
            return False


class NetFlowCollector(FlowCollector):
    """NetFlow数据收集器，支持v5/v9协议"""
    
    def __init__(self, listen_ip='0.0.0.0', listen_port=NETFLOW_PORT, db_session=None):
        super().__init__(db_session)
        self.listen_ip = listen_ip
        self.listen_port = listen_port
        self.socket = None
        self.collector_thread = None
        
    def start(self):
        """启动NetFlow收集器"""
        super().start()
        try:
            # 创建UDP套接字
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.bind((self.listen_ip, self.listen_port))
            
            # 启动收集线程
            self.collector_thread = threading.Thread(target=self._collect_loop)
            self.collector_thread.daemon = True
            self.collector_thread.start()
            
            logger.info(f"NetFlow收集器已启动，监听 {self.listen_ip}:{self.listen_port}")
            return True
            
        except Exception as e:
            logger.error(f"启动NetFlow收集器失败: {str(e)}")
            return False
            
    def stop(self):
        """停止NetFlow收集器"""
        super().stop()
        if self.socket:
            self.socket.close()
        logger.info("NetFlow收集器已停止")
        
    def _collect_loop(self):
        """NetFlow数据收集循环"""
        while self.running:
            try:
                # 接收数据
                data, addr = self.socket.recvfrom(4096)
                src_ip = addr[0]
                
                # 处理数据包
                self._process_packet(data, src_ip)
                
            except socket.timeout:
                continue
            except Exception as e:
                logger.error(f"NetFlow数据收集错误: {str(e)}")
                time.sleep(1)  # 避免因错误导致CPU使用率过高
                
    def _process_packet(self, data, src_ip):
        """处理NetFlow数据包"""
        try:
            # 解析NetFlow头部
            version = struct.unpack('!H', data[0:2])[0]
            
            if version == 5:
                self._process_netflow_v5(data, src_ip)
            elif version == 9:
                self._process_netflow_v9(data, src_ip)
            else:
                logger.warning(f"不支持的NetFlow版本: {version}")
                
        except Exception as e:
            logger.error(f"处理NetFlow数据包时出错: {str(e)}")
            
    def _process_netflow_v5(self, data, src_ip):
        """处理NetFlow v5数据包"""
        try:
            # 解析包头
            header = struct.unpack(NETFLOW_V5_HEADER_FORMAT, data[0:24])
            version, count, sys_uptime, unix_secs, unix_nsecs, flow_sequence, engine_type, engine_id, sampling_interval = header
            
            # 处理流记录
            for i in range(count):
                # 计算记录的起始位置
                start_pos = 24 + i * 48
                
                # 确保数据长度足够
                if start_pos + 48 > len(data):
                    logger.warning("NetFlow v5数据包长度不足")
                    break
                    
                # 解析流记录
                record = struct.unpack(NETFLOW_V5_RECORD_FORMAT, data[start_pos:start_pos+48])
                
                # 提取关键字段
                src_addr, dst_addr, next_hop, input_if, output_if = record[0:5]
                d_pkts, d_octets = record[6:8]
                
                # 记录流量数据
                self._record_interface_traffic(src_ip, input_if, d_octets, 0)
                self._record_interface_traffic(src_ip, output_if, 0, d_octets)
                
            logger.debug(f"处理了来自{src_ip}的NetFlow v5数据包，包含{count}条记录")
            
        except Exception as e:
            logger.error(f"处理NetFlow v5数据包时出错: {str(e)}")
            
    def _process_netflow_v9(self, data, src_ip):
        """处理NetFlow v9数据包 (简化实现)"""
        # NetFlow v9使用模板定义数据格式，完整实现较为复杂
        # 这里仅提供简化的框架实现
        logger.info(f"收到来自{src_ip}的NetFlow v9数据包，当前为简化实现")
        
    def _record_interface_traffic(self, device_ip, interface_id, in_bytes, out_bytes):
        """记录接口流量数据"""
        # 生成缓存键
        cache_key = f"{device_ip}:{interface_id}"
        
        # 获取当前时间
        now = datetime.utcnow()
        
        # 检查缓存中是否已有该接口的数据
        if cache_key in self.cache:
            last_update, last_in, last_out = self.cache[cache_key]
            
            # 如果距离上次更新超过5分钟，保存数据并更新缓存
            if (now - last_update).total_seconds() >= 300:
                self.save_flow_data(device_ip, interface_id, last_in + in_bytes, last_out + out_bytes, last_update)
                self.cache[cache_key] = (now, in_bytes, out_bytes)
            else:
                # 更新缓存中的流量数据
                self.cache[cache_key] = (last_update, last_in + in_bytes, last_out + out_bytes)
        else:
            # 添加到缓存
            self.cache[cache_key] = (now, in_bytes, out_bytes)


class SFlowCollector(FlowCollector):
    """sFlow数据收集器，支持v5协议"""
    
    def __init__(self, listen_ip='0.0.0.0', listen_port=SFLOW_PORT, db_session=None):
        super().__init__(db_session)
        self.listen_ip = listen_ip
        self.listen_port = listen_port
        self.socket = None
        self.collector_thread = None
        
    def start(self):
        """启动sFlow收集器"""
        super().start()
        try:
            # 创建UDP套接字
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.bind((self.listen_ip, self.listen_port))
            
            # 启动收集线程
            self.collector_thread = threading.Thread(target=self._collect_loop)
            self.collector_thread.daemon = True
            self.collector_thread.start()
            
            logger.info(f"sFlow收集器已启动，监听 {self.listen_ip}:{self.listen_port}")
            return True
            
        except Exception as e:
            logger.error(f"启动sFlow收集器失败: {str(e)}")
            return False
            
    def stop(self):
        """停止sFlow收集器"""
        super().stop()
        if self.socket:
            self.socket.close()
        logger.info("sFlow收集器已停止")
        
    def _collect_loop(self):
        """sFlow数据收集循环"""
        while self.running:
            try:
                # 接收数据
                data, addr = self.socket.recvfrom(4096)
                src_ip = addr[0]
                
                # 处理数据包
                self._process_packet(data, src_ip)
                
            except socket.timeout:
                continue
            except Exception as e:
                logger.error(f"sFlow数据收集错误: {str(e)}")
                time.sleep(1)  # 避免因错误导致CPU使用率过高
                
    def _process_packet(self, data, src_ip):
        """处理sFlow数据包 (简化实现)"""
        # sFlow协议解析较为复杂，这里仅提供简化的框架实现
        logger.info(f"收到来自{src_ip}的sFlow数据包，当前为简化实现")


# 创建全局收集器实例
netflow_collector = NetFlowCollector()
sflow_collector = SFlowCollector()

def init_flow_collectors():
    """初始化流量收集器"""
    try:
        # 启动NetFlow收集器
        netflow_collector.start()
        
        # 启动sFlow收集器
        sflow_collector.start()
        
        logger.info("流量收集器初始化完成")
        return True
    except Exception as e:
        logger.error(f"初始化流量收集器失败: {str(e)}")
        return False
        
def stop_flow_collectors():
    """停止流量收集器"""
    try:
        netflow_collector.stop()
        sflow_collector.stop()
        logger.info("流量收集器已停止")
        return True
    except Exception as e:
        logger.error(f"停止流量收集器失败: {str(e)}")
        return False 