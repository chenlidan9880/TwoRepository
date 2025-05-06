"""
通知服务模块，用于处理各种通知，包括邮件和短信
"""
import logging
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app
from datetime import datetime

# 阿里云SDK导入
try:
    from alibabacloud_dysmsapi20170525.client import Client as DysmsapiClient
    from alibabacloud_dysmsapi20170525 import models as dysmsapi_models
    from alibabacloud_tea_openapi import models as open_api_models
    from alibabacloud_tea_util import models as util_models
    ALIYUN_SDK_AVAILABLE = True
except ImportError:
    ALIYUN_SDK_AVAILABLE = False
    logging.warning("阿里云SMS SDK未安装，短信功能将不可用。请使用pip install alibabacloud_dysmsapi20170525安装。")

from app.models.user import User
from app.models.alert import Alert

logger = logging.getLogger(__name__)

class NotificationService:
    """
    通知服务类，负责发送各种类型的通知（邮件、短信等）
    """
    
    @staticmethod
    def send_alert_notifications(alert):
        """
        根据告警发送通知
        
        参数:
            alert: Alert 对象
        """
        if not isinstance(alert, Alert):
            logger.error("无效的告警对象")
            return False
            
        # 获取需要接收通知的管理员用户
        admins = User.query.filter_by(is_admin=True).all()
        
        if not admins:
            logger.warning("没有找到管理员用户，无法发送通知")
            return False
            
        success = True
        
        # 为每个满足条件的管理员发送通知
        for admin in admins:
            # 检查是否只接收紧急告警
            if admin.critical_only and alert.severity != 'critical':
                continue
                
            # 邮件通知
            if admin.receive_email and admin.email:
                email_success = NotificationService.send_email_notification(
                    admin.email,
                    f"【校园网监控】{alert.severity.upper()}告警: {alert.title}",
                    NotificationService._format_alert_email(alert)
                )
                success = success and email_success
                
            # 短信通知
            if admin.receive_sms and admin.phone_number:
                sms_success = NotificationService.send_sms_notification(
                    admin.phone_number,
                    {
                        "alert_level": alert.severity.upper(),
                        "alert_title": alert.title,
                        "alert_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                )
                success = success and sms_success
                
        return success
    
    @staticmethod
    def send_email_notification(recipient, subject, body):
        """
        发送邮件通知
        
        参数:
            recipient: 收件人邮箱
            subject: 邮件主题
            body: 邮件内容
        
        返回:
            bool: 是否发送成功
        """
        try:
            msg = MIMEMultipart()
            msg['From'] = current_app.config['MAIL_USERNAME']
            msg['To'] = recipient
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'html'))
            
            server = smtplib.SMTP(
                current_app.config['MAIL_SERVER'], 
                current_app.config['MAIL_PORT']
            )
            
            if current_app.config.get('MAIL_USE_TLS', False):
                server.starttls()
                
            server.login(
                current_app.config['MAIL_USERNAME'],
                current_app.config['MAIL_PASSWORD']
            )
            
            server.send_message(msg)
            server.quit()
            
            logger.info(f"邮件发送成功: {recipient}")
            return True
            
        except Exception as e:
            logger.error(f"邮件发送失败: {str(e)}")
            return False
    
    @staticmethod
    def send_sms_notification(phone_number, template_params):
        """
        发送短信通知（使用阿里云短信服务）
        
        参数:
            phone_number: 手机号码
            template_params: 模板参数，字典格式
        
        返回:
            bool: 是否发送成功
        """
        if not ALIYUN_SDK_AVAILABLE:
            logger.error("阿里云SDK未安装，无法发送短信")
            return False
            
        try:
            # 创建阿里云客户端配置
            config = open_api_models.Config(
                access_key_id=current_app.config['ALIYUN_ACCESS_KEY_ID'],
                access_key_secret=current_app.config['ALIYUN_ACCESS_KEY_SECRET']
            )
            config.endpoint = f'dysmsapi.{current_app.config.get("ALIYUN_REGION_ID", "cn-hangzhou")}.aliyuncs.com'
            
            # 创建客户端
            client = DysmsapiClient(config)
            
            # 创建请求
            send_request = dysmsapi_models.SendSmsRequest(
                phone_numbers=phone_number,
                sign_name=current_app.config['ALIYUN_SMS_SIGN_NAME'],
                template_code=current_app.config['ALIYUN_SMS_TEMPLATE_CODE'],
                template_param=json.dumps(template_params)
            )
            
            # 发送短信
            runtime = util_models.RuntimeOptions()
            response = client.send_sms_with_options(send_request, runtime)
            
            # 检查结果
            if response.body.code == "OK":
                logger.info(f"短信发送成功: {phone_number}, 消息ID: {response.body.biz_id}")
                return True
            else:
                logger.error(f"短信发送失败: 错误码 {response.body.code}, 消息: {response.body.message}")
                return False
                
        except Exception as e:
            logger.error(f"短信发送失败: {str(e)}")
            return False
    
    @staticmethod
    def _format_alert_email(alert):
        """
        格式化告警邮件内容
        
        参数:
            alert: Alert对象
            
        返回:
            str: 格式化后的HTML邮件内容
        """
        severity_color = {
            'critical': '#ff3b30',
            'high': '#ff9500',
            'medium': '#ffcc00',
            'low': '#34c759',
            'info': '#007aff'
        }.get(alert.severity, '#8e8e93')
        
        device_info = f"设备: {alert.device.name} ({alert.device.ip_address})" if alert.device else "全局告警"
        
        return f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
            <div style="background-color: {severity_color}; color: white; padding: 10px 15px; border-radius: 4px; margin-bottom: 20px;">
                <h2 style="margin: 0; font-size: 18px;">{alert.severity.upper()} 级别告警</h2>
            </div>
            
            <h3 style="color: #333; font-size: 18px; margin-top: 0;">{alert.title}</h3>
            
            <p style="color: #666; font-size: 14px; line-height: 1.5;">{alert.message}</p>
            
            <div style="background-color: #f5f5f5; padding: 15px; border-radius: 4px; margin: 20px 0;">
                <p style="margin: 0 0 8px 0; font-size: 14px;"><strong>告警详情：</strong></p>
                <ul style="margin: 0; padding-left: 20px;">
                    <li style="margin-bottom: 5px;">{device_info}</li>
                    <li style="margin-bottom: 5px;">告警时间: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</li>
                    <li style="margin-bottom: 5px;">告警ID: {alert.id}</li>
                    <li style="margin-bottom: 5px;">当前状态: {alert.status}</li>
                    {f'<li style="margin-bottom: 5px;">监测值: {alert.value}</li>' if alert.value is not None else ''}
                    {f'<li style="margin-bottom: 5px;">阈值: {alert.threshold}</li>' if alert.threshold is not None else ''}
                </ul>
            </div>
            
            <div style="font-size: 12px; color: #999; margin-top: 30px; border-top: 1px solid #eee; padding-top: 15px;">
                <p>此邮件由校园网监控系统自动发送，请勿直接回复此邮件。</p>
                <p>若需调整通知设置，请登录系统修改您的个人资料设置。</p>
            </div>
        </div>
        """

# 定义告警阈值配置
class AlertThresholds:
    """告警阈值配置"""
    
    # 流量告警阈值（百分比）
    TRAFFIC_UTILIZATION = {
        'warning': 70,    # 利用率超过70%触发警告
        'critical': 90     # 利用率超过90%触发紧急告警
    }
    
    # CPU利用率阈值（百分比）
    CPU_UTILIZATION = {
        'warning': 75,
        'critical': 90
    }
    
    # 内存利用率阈值（百分比）
    MEMORY_UTILIZATION = {
        'warning': 80,
        'critical': 95
    }
    
    # 设备离线时间阈值（分钟）
    DEVICE_OFFLINE = {
        'warning': 5,      # 离线5分钟触发警告
        'critical': 30     # 离线30分钟触发紧急告警
    }
    
    # 流量异常检测阈值（标准差倍数）
    TRAFFIC_ANOMALY = {
        'warning': 2,      # 流量超过2倍标准差触发警告
        'critical': 4      # 流量超过4倍标准差触发紧急告警
    } 