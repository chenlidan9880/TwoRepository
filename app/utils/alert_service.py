"""
告警服务模块，用于生成和管理告警
"""
import logging
from datetime import datetime, timedelta
from app import db
from app.models.alert import Alert
from app.models.device import Device
from app.utils.notification_service import NotificationService, AlertThresholds
from sqlalchemy import func, and_

logger = logging.getLogger(__name__)

class AlertService:
    """告警服务类"""
    
    @staticmethod
    def generate_traffic_alert(device_id, interface, utilization, threshold, alert_type='traffic_high'):
        """
        生成流量告警
        
        Args:
            device_id: 设备ID
            interface: 接口名称
            utilization: 流量利用率（百分比）
            threshold: 触发阈值（百分比）
            alert_type: 告警类型，默认为'traffic_high'
        
        Returns:
            bool: 是否成功生成告警
        """
        try:
            # 确定告警严重程度
            severity = 'critical' if utilization >= AlertThresholds.TRAFFIC_UTILIZATION['critical'] else 'warning'
            
            # 检查是否已存在相同类型的未处理告警
            existing_alert = Alert.query.filter(
                Alert.device_id == device_id,
                Alert.alert_type == alert_type,
                Alert.is_handled == False,
                Alert.severity == severity
            ).first()
            
            if existing_alert:
                # 更新已有告警的值
                existing_alert.value = utilization
                existing_alert.created_at = datetime.utcnow()  # 更新时间
                db.session.commit()
                logger.info(f"更新设备 {device_id} 的流量告警，利用率: {utilization}%")
                return True
            
            # 获取设备信息
            device = Device.query.get(device_id)
            if not device:
                logger.error(f"无法找到设备 ID: {device_id}")
                return False
            
            # 创建告警标题和消息
            title = f"{'高危' if severity == 'critical' else '警告'} - 网络接口流量利用率过高"
            message = f"设备 {device.name} ({device.ip_address}) 的接口 {interface} 流量利用率达到 {utilization:.2f}%，超过了 {threshold:.2f}% 的阈值。请检查网络状况。"
            
            # 创建新告警
            alert = Alert(
                device_id=device_id,
                alert_type=alert_type,
                severity=severity,
                title=title,
                message=message,
                value=utilization,
                threshold=threshold,
                created_at=datetime.utcnow()
            )
            
            db.session.add(alert)
            db.session.commit()
            
            # 发送通知
            NotificationService.send_alert_notifications(alert.id)
            
            logger.info(f"已为设备 {device_id} 生成 {severity} 级流量告警")
            return True
            
        except Exception as e:
            logger.error(f"生成流量告警失败: {str(e)}")
            db.session.rollback()
            return False
    
    @staticmethod
    def generate_device_offline_alert(device_id, offline_duration):
        """
        生成设备离线告警
        
        Args:
            device_id: 设备ID
            offline_duration: 离线时长（分钟）
        
        Returns:
            bool: 是否成功生成告警
        """
        try:
            # 确定告警严重程度
            severity = 'critical' if offline_duration >= AlertThresholds.DEVICE_OFFLINE['critical'] else 'warning'
            
            # 检查是否已存在相同类型的未处理告警
            existing_alert = Alert.query.filter(
                Alert.device_id == device_id,
                Alert.alert_type == 'device_offline',
                Alert.is_handled == False
            ).first()
            
            if existing_alert:
                # 如果严重程度需要提升，则更新
                if existing_alert.severity != 'critical' and severity == 'critical':
                    existing_alert.severity = severity
                    existing_alert.value = offline_duration
                    existing_alert.threshold = AlertThresholds.DEVICE_OFFLINE[severity]
                    db.session.commit()
                    logger.info(f"更新设备 {device_id} 的离线告警为紧急级别，离线时长: {offline_duration}分钟")
                return True
            
            # 获取设备信息
            device = Device.query.get(device_id)
            if not device:
                logger.error(f"无法找到设备 ID: {device_id}")
                return False
            
            # 创建告警标题和消息
            title = f"{'高危' if severity == 'critical' else '警告'} - 设备离线"
            message = f"设备 {device.name} ({device.ip_address}) 已离线 {offline_duration} 分钟。请检查设备状态及网络连接。"
            
            # 创建新告警
            alert = Alert(
                device_id=device_id,
                alert_type='device_offline',
                severity=severity,
                title=title,
                message=message,
                value=offline_duration,
                threshold=AlertThresholds.DEVICE_OFFLINE[severity],
                created_at=datetime.utcnow()
            )
            
            db.session.add(alert)
            db.session.commit()
            
            # 发送通知
            NotificationService.send_alert_notifications(alert.id)
            
            logger.info(f"已为设备 {device_id} 生成 {severity} 级离线告警")
            return True
            
        except Exception as e:
            logger.error(f"生成设备离线告警失败: {str(e)}")
            db.session.rollback()
            return False
    
    @staticmethod
    def generate_traffic_anomaly_alert(device_id, interface, current_value, baseline_value, std_dev):
        """
        生成流量异常告警
        
        Args:
            device_id: 设备ID
            interface: 接口名称
            current_value: 当前流量值
            baseline_value: 基准流量值
            std_dev: 标准差
        
        Returns:
            bool: 是否成功生成告警
        """
        try:
            # 计算偏差倍数
            if baseline_value == 0 or std_dev == 0:
                deviation_factor = 10  # 基准值为0时，设置一个较大的偏差倍数
            else:
                deviation_factor = abs(current_value - baseline_value) / std_dev
            
            # 确定告警严重程度
            severity = 'critical' if deviation_factor >= AlertThresholds.TRAFFIC_ANOMALY['critical'] else 'warning'
            
            # 如果偏差不足以触发告警，则返回
            if deviation_factor < AlertThresholds.TRAFFIC_ANOMALY['warning']:
                return False
            
            # 检查是否已存在相同类型的未处理告警
            existing_alert = Alert.query.filter(
                Alert.device_id == device_id,
                Alert.alert_type == 'traffic_anomaly',
                Alert.is_handled == False
            ).first()
            
            if existing_alert:
                # 如果严重程度需要提升，则更新
                if existing_alert.severity != 'critical' and severity == 'critical':
                    existing_alert.severity = severity
                    existing_alert.value = deviation_factor
                    existing_alert.created_at = datetime.utcnow()
                    db.session.commit()
                    logger.info(f"更新设备 {device_id} 的流量异常告警为紧急级别，偏差倍数: {deviation_factor:.2f}")
                return True
            
            # 获取设备信息
            device = Device.query.get(device_id)
            if not device:
                logger.error(f"无法找到设备 ID: {device_id}")
                return False
            
            # 流量变化类型
            change_type = "增加" if current_value > baseline_value else "减少"
            
            # 创建告警标题和消息
            title = f"{'高危' if severity == 'critical' else '警告'} - 流量异常波动"
            message = f"设备 {device.name} ({device.ip_address}) 的接口 {interface} 流量出现异常，当前值较基准值{change_type}了 {deviation_factor:.2f} 倍标准差。\n当前值: {current_value:.2f}，基准值: {baseline_value:.2f}，标准差: {std_dev:.2f}"
            
            # 创建新告警
            alert = Alert(
                device_id=device_id,
                alert_type='traffic_anomaly',
                severity=severity,
                title=title,
                message=message,
                value=deviation_factor,
                threshold=AlertThresholds.TRAFFIC_ANOMALY[severity],
                created_at=datetime.utcnow()
            )
            
            db.session.add(alert)
            db.session.commit()
            
            # 发送通知
            NotificationService.send_alert_notifications(alert.id)
            
            logger.info(f"已为设备 {device_id} 生成 {severity} 级流量异常告警")
            return True
            
        except Exception as e:
            logger.error(f"生成流量异常告警失败: {str(e)}")
            db.session.rollback()
            return False
    
    @staticmethod
    def check_and_update_alerts():
        """
        检查和更新告警状态
        - 将已恢复的告警标记为已恢复
        - 升级长时间未处理的告警级别
        
        Returns:
            dict: 处理结果统计
        """
        try:
            result = {
                'recovered': 0,
                'escalated': 0
            }
            
            # 检查设备离线告警恢复
            offline_alerts = Alert.query.filter(
                Alert.alert_type == 'device_offline',
                Alert.is_handled == False,
                Alert.is_recovered == False
            ).all()
            
            for alert in offline_alerts:
                device = Device.query.get(alert.device_id)
                if device and device.status == 'online':
                    alert.is_recovered = True
                    alert.recovered_at = datetime.utcnow()
                    result['recovered'] += 1
            
            # 提交更改
            db.session.commit()
            
            # 处理长时间未处理的告警
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            warning_alerts = Alert.query.filter(
                Alert.severity == 'warning',
                Alert.is_handled == False,
                Alert.is_recovered == False,
                Alert.created_at <= one_hour_ago
            ).all()
            
            for alert in warning_alerts:
                alert.severity = 'critical'
                result['escalated'] += 1
            
            # 提交更改
            db.session.commit()
            
            logger.info(f"告警状态更新完成: {result['recovered']} 个告警已恢复，{result['escalated']} 个告警级别已升级")
            return result
            
        except Exception as e:
            logger.error(f"检查和更新告警状态失败: {str(e)}")
            db.session.rollback()
            return {'recovered': 0, 'escalated': 0, 'error': str(e)}
    
    @staticmethod
    def get_alert_statistics(start_date=None, end_date=None):
        """
        获取告警统计数据
        
        Args:
            start_date: 开始日期，默认为过去7天
            end_date: 结束日期，默认为当前时间
        
        Returns:
            dict: 告警统计数据
        """
        try:
            # 设置默认日期范围
            if end_date is None:
                end_date = datetime.utcnow()
            if start_date is None:
                start_date = end_date - timedelta(days=7)
            
            # 按日期和严重程度统计告警数量
            daily_stats = db.session.query(
                func.date(Alert.created_at).label('date'),
                Alert.severity,
                func.count(Alert.id).label('count')
            ).filter(
                Alert.created_at.between(start_date, end_date)
            ).group_by(
                func.date(Alert.created_at),
                Alert.severity
            ).all()
            
            # 处理结果
            daily_data = {}
            for stat in daily_stats:
                date_str = stat.date.strftime('%Y-%m-%d')
                if date_str not in daily_data:
                    daily_data[date_str] = {'critical': 0, 'warning': 0, 'info': 0}
                daily_data[date_str][stat.severity] = stat.count
            
            # 按设备统计告警数量
            device_stats = db.session.query(
                Alert.device_id,
                func.count(Alert.id).label('count')
            ).filter(
                Alert.created_at.between(start_date, end_date)
            ).group_by(
                Alert.device_id
            ).all()
            
            # 处理设备统计结果
            device_data = []
            for stat in device_stats:
                device = Device.query.get(stat.device_id)
                if device:
                    device_data.append({
                        'device_id': stat.device_id,
                        'device_name': device.name,
                        'count': stat.count
                    })
            
            # 按告警类型统计
            type_stats = db.session.query(
                Alert.alert_type,
                func.count(Alert.id).label('count')
            ).filter(
                Alert.created_at.between(start_date, end_date)
            ).group_by(
                Alert.alert_type
            ).all()
            
            # 处理类型统计结果
            type_data = {stat.alert_type: stat.count for stat in type_stats}
            
            # 返回结果
            return {
                'daily_data': daily_data,
                'device_data': device_data,
                'type_data': type_data,
                'period': {
                    'start': start_date.strftime('%Y-%m-%d'),
                    'end': end_date.strftime('%Y-%m-%d')
                }
            }
            
        except Exception as e:
            logger.error(f"获取告警统计数据失败: {str(e)}")
            return {'error': str(e)} 