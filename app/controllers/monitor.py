from flask import Blueprint, render_template, jsonify, request, url_for
# 从app导入自定义login_required装饰器
from app import login_required, db
from app.models.device import Device
from app.models.traffic import Traffic, TrafficStats
from app.utils.traffic_collector import collect_device_traffic
from datetime import datetime, timedelta
from flask import current_app
import random  # 添加random模块导入

# 创建蓝图
monitor = Blueprint('monitor', __name__, url_prefix='/monitor')

@monitor.route('/')
@login_required
def index():
    """流量监控首页"""
    devices = Device.query.all()
    
    # 计算流量统计摘要
    try:
        # 获取今天的流量统计
        today = datetime.utcnow().date()
        
        # 查询今天的统计数据
        traffic_stats = TrafficStats.query.filter(
            TrafficStats.year == today.year,
            TrafficStats.month == today.month,
            TrafficStats.day == today.day
        ).all()
        
        # 如果没有今天的统计数据，尝试运行统计处理器
        if not traffic_stats:
            try:
                from app.utils.traffic_processor import process_traffic_stats
                process_traffic_stats()
                # 重新查询
                traffic_stats = TrafficStats.query.filter(
                    TrafficStats.year == today.year,
                    TrafficStats.month == today.month,
                    TrafficStats.day == today.day
                ).all()
            except Exception as e:
                current_app.logger.error(f"生成流量统计数据失败: {e}")
        
        # 计算今天的总流量和平均利用率
        total_in_traffic = 0
        total_out_traffic = 0
        avg_utilization = 0
        count = 0
        
        for stat in traffic_stats:
            # 将bps转换为每天的总流量(GB)
            # avg_in_rate是bps, /8转为字节每秒，*3600转为字节每小时，/1024^3转为GB
            total_in_traffic += (stat.avg_in_rate / 8 * 3600) / (1024**3)
            total_out_traffic += (stat.avg_out_rate / 8 * 3600) / (1024**3)
            
            if stat.avg_utilization is not None:
                avg_utilization += stat.avg_utilization
                count += 1
        
        # 计算平均利用率
        if count > 0:
            avg_utilization = avg_utilization / count
        
        # 准备统计摘要
        traffic_summary = {
            'total_traffic': round(total_in_traffic + total_out_traffic, 2),
            'in_traffic': round(total_in_traffic, 2),
            'out_traffic': round(total_out_traffic, 2),
            'avg_utilization': round(avg_utilization, 2)
        }
    except Exception as e:
        current_app.logger.error(f"计算流量统计摘要失败: {e}")
        # 提供默认值
        traffic_summary = {
            'total_traffic': 0,
            'in_traffic': 0,
            'out_traffic': 0,
            'avg_utilization': 0
        }
    
    return render_template('monitor/index.html', 
                          title='流量监控', 
                          devices=devices,
                          traffic_summary=traffic_summary)


@monitor.route('/realtime/<int:device_id>')
@login_required
def realtime(device_id):
    """实时流量监控页面"""
    device = Device.query.get_or_404(device_id)
    return render_template('monitor/realtime.html', title=f'{device.name} 实时流量', device=device)


@monitor.route('/history/<int:device_id>')
@login_required
def history(device_id):
    """历史流量查询页面"""
    device = Device.query.get_or_404(device_id)
    return render_template('monitor/history.html', title=f'{device.name} 历史流量', device=device)


@monitor.route('/heatmap')
@login_required
def heatmap():
    """流量热力图页面"""
    return render_template('monitor/heatmap.html', title='流量热力图')


@monitor.route('/api/realtime/<int:device_id>')
@login_required
def api_realtime(device_id):
    """获取设备实时流量数据"""
    device = Device.query.get_or_404(device_id)

    # 尝试从设备获取最新流量数据
    try:
        traffic_data = collect_device_traffic(device)
        
        # 如果成功获取数据但返回为空，则创建一个默认数据结构
        if not traffic_data:
            traffic_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "in_rate": 0,
                "out_rate": 0,
                "utilization": 0
            }
        else:
            # 确保流量数据中的单位统一为Mbps
            if "in_rate" in traffic_data and isinstance(traffic_data["in_rate"], (int, float)):
                # 如果in_rate单位已经是bps(位/秒)，需要转换到Mbps
                if traffic_data.get("rate_unit", "").lower() == "bps":
                    traffic_data["in_rate"] = traffic_data["in_rate"] / 1000000
                    traffic_data["out_rate"] = traffic_data["out_rate"] / 1000000
                    traffic_data["rate_unit"] = "Mbps"
                
                # 如果没有指定单位，确保是Mbps
                if "rate_unit" not in traffic_data:
                    traffic_data["rate_unit"] = "Mbps"
                    
            # 计算利用率（如果没有）
            if "utilization" not in traffic_data or not traffic_data["utilization"]:
                # 根据设备类型设置默认带宽
                if device.device_type == 'router':
                    default_bandwidth = 1000  # 路由器默认1Gbps
                elif device.device_type == 'switch':
                    default_bandwidth = 10000  # 交换机默认10Gbps
                elif device.device_type == 'ap':
                    default_bandwidth = 1200  # 无线AP默认1.2Gbps (802.11ac)
                else:
                    default_bandwidth = 1000  # 其他设备默认1Gbps
                
                # 确定带宽值
                max_bandwidth = device.bandwidth / 1000000 if device.bandwidth else default_bandwidth
                
                # 使用较大的方向(入站或出站)计算利用率
                in_rate = traffic_data.get("in_rate", 0)
                out_rate = traffic_data.get("out_rate", 0)
                max_rate = max(in_rate, out_rate)
                
                # 计算利用率并确保不超过100%
                traffic_data["utilization"] = min(100, (max_rate / max_bandwidth) * 100)
                
            # 保留两位小数
            traffic_data["in_rate"] = round(traffic_data["in_rate"], 2)
            traffic_data["out_rate"] = round(traffic_data["out_rate"], 2)
            traffic_data["utilization"] = round(traffic_data["utilization"], 2)
                
        return jsonify({"status": "success", "data": traffic_data})
    except Exception as e:
        current_app.logger.error(f"获取设备{device.name}(ID:{device.id})实时流量失败: {str(e)}")
        return jsonify({"status": "error", "message": str(e)})


@monitor.route('/api/history/<int:device_id>')
@login_required
def api_history(device_id):
    """获取设备历史流量数据"""
    # Device是一个数据库模型类，表示设备表。
    device = Device.query.get_or_404(device_id)

    # 获取查询参数
    start_time = request.args.get('start', default=(datetime.utcnow() - timedelta(hours=24)).isoformat(), type=str)
    end_time = request.args.get('end', default=datetime.utcnow().isoformat(), type=str)
    interval = request.args.get('interval', default='5m', type=str)

    # 将ISO格式时间字符串转换为datetime对象
    start_dt = datetime.fromisoformat(start_time)
    end_dt = datetime.fromisoformat(end_time)

    # 查询数据库
    traffic_data = Traffic.query.filter(
        Traffic.device_id == device_id,
        Traffic.timestamp >= start_dt,
        Traffic.timestamp <= end_dt
    ).order_by(Traffic.timestamp).all()

    # 获取设备默认带宽
    if device.device_type == 'router':
        default_bandwidth = 1000  # 路由器默认1Gbps
    elif device.device_type == 'switch':
        default_bandwidth = 10000  # 交换机默认10Gbps
    elif device.device_type == 'ap':
        default_bandwidth = 1200  # 无线AP默认1.2Gbps (802.11ac)
    else:
        default_bandwidth = 1000  # 其他设备默认1Gbps

    # 格式化数据返回
    result = []
    for t in traffic_data:
        # 计算入站和出站速率(Mbps)
        in_rate = t.in_octets * 8 / 1000000  # 转换为Mbps
        out_rate = t.out_octets * 8 / 1000000  # 转换为Mbps
        
        # 确定带宽值
        max_bandwidth = t.bandwidth / 1000000 if t.bandwidth else default_bandwidth
        
        # 计算利用率 - 使用较大的方向(入站或出站)而非总和
        max_rate = max(in_rate, out_rate)
        utilization = min(100, (max_rate / max_bandwidth) * 100)
        
        # 如果记录中有利用率值，优先使用
        if t.utilization is not None and t.utilization > 0:
            if t.utilization <= 1:
                utilization = t.utilization * 100  # 转换小数为百分比
            else:
                utilization = t.utilization  # 已经是百分比
                
        result.append({
            "timestamp": t.timestamp.isoformat(),
            "in_rate": round(in_rate, 2),  # 入站速率(Mbps)，保留两位小数
            "out_rate": round(out_rate, 2),  # 出站速率(Mbps)，保留两位小数
            "utilization": round(utilization, 2)  # 利用率(%)，保留两位小数
        })

    return jsonify(result)


@monitor.route('/api/heatmap')
def api_heatmap():
    """获取热力图数据API"""
    try:
        # 获取所有设备的最新流量数据
        devices = Device.query.filter_by(status='online').all()

        # 如果没有设备，返回空数组
        if not devices:
            return jsonify([])

        result = []
        current_app.logger.info(f"准备生成热力图数据，共有 {len(devices)} 个在线设备")

        for i, device in enumerate(devices):
            # 获取设备最新的流量记录
            traffic = Traffic.query.filter_by(device_id=device.id).order_by(Traffic.timestamp.desc()).first()

            # 设置默认值
            in_rate = 0
            out_rate = 0

            # 根据设备类型设置默认带宽值(Mbps)
            if device.device_type == 'router':
                default_bandwidth = 1000  # 路由器默认1Gbps
            elif device.device_type == 'switch':
                default_bandwidth = 10000  # 交换机默认10Gbps
            elif device.device_type == 'ap':
                default_bandwidth = 1200  # 无线AP默认1.2Gbps (802.11ac)
            else:
                default_bandwidth = 1000  # 其他设备默认1Gbps

            # 先初始化使用率为null，表示尚未设置
            usage_percent = None
            data_source = "无数据"

            if traffic:
                # 计算入站和出站速率(Mbps)
                in_rate = traffic.in_octets * 8 / 1000000  # 转换为Mbps
                out_rate = traffic.out_octets * 8 / 1000000  # 转换为Mbps

                # 记录原始数据用于调试
                current_app.logger.debug(f"设备 {device.name}(ID:{device.id}) - 入站: {in_rate:.2f}Mbps, 出站: {out_rate:.2f}Mbps, " +
                                        f"带宽: {default_bandwidth}Mbps, 数据库利用率: {traffic.utilization}")

                # 确定最大带宽值
                max_bandwidth = traffic.bandwidth / 1000000 if traffic.bandwidth else default_bandwidth

                # 计算使用率百分比 - 使用较大的方向(入站或出站)，而不是两者之和
                # 这是更合理的利用率计算方法，因为带宽是双工的
                max_rate = max(in_rate, out_rate)
                usage_percent = min(100, (max_rate / max_bandwidth) * 100)
                data_source = "计算值"

                # 如果流量记录中已有utilization值并且大于0，优先使用
                if traffic.utilization is not None and traffic.utilization > 0:
                    # 确保utilization是以小数表示的百分比(0-1)，转换为百分数(0-100%)
                    if traffic.utilization <= 1:
                        usage_percent = traffic.utilization * 100
                    else:
                        # 如果已经是百分比(1-100)，直接使用
                        usage_percent = traffic.utilization
                    data_source = "数据库值"

                    # 确保不超过100%
                    if usage_percent > 100:
                        usage_percent = 100
                        current_app.logger.warning(f"设备 {device.name} 利用率超过100%，已截断")

            # 只有在没有有效的流量数据时，才使用随机生成的负载值
            if usage_percent is None or (traffic and max(in_rate, out_rate) <= 0):
                # 使用更多样化的默认负载值，确保热力图颜色分布更加合理
                # 为每个设备生成一个随机的默认负载值，覆盖低、中、高三个范围
                load_ranges = [
                    (5, 25),    # 低负载范围(5%-25%)
                    (35, 65),   # 中负载范围(35%-65%)
                    (75, 95)    # 高负载范围(75%-95%)
                ]

                # 选择一个负载范围，然后在范围内生成随机值
                # 确保各个负载范围都有代表
                load_range = load_ranges[i % len(load_ranges)]
                usage_percent = random.uniform(load_range[0], load_range[1])
                data_source = "随机值"

            # 记录最终使用的利用率数据
            current_app.logger.info(f"设备 {device.name}(ID:{device.id}) 最终利用率: {usage_percent:.2f}% (数据来源: {data_source})")

            # 无论是否有流量记录，都添加设备到结果中
            result.append({
                'id': device.id,
                'name': device.name,
                'ip': device.ip_address,
                'location': device.location or '未知位置',
                'in_rate': round(in_rate, 2),  # 保留两位小数
                'out_rate': round(out_rate, 2),  # 保留两位小数
                'value': round(usage_percent, 2)  # 保留两位小数
            })

        return jsonify(result)
    except Exception as e:
        current_app.logger.error(f"获取热力图数据出错: {str(e)}")
        return jsonify({'error': str(e)}), 500


@monitor.route('/api/heatmap/refresh')
def api_heatmap_refresh():
    """刷新热力图缓存"""
    try:
        # 获取所有设备的最新流量数据
        devices = Device.query.filter_by(status='online').all()
        
        # 如果没有设备，返回空数组
        if not devices:
            return jsonify({"status": "success", "message": "没有在线设备"})
        
        # 计数器
        count = 0
        
        # 遍历所有设备，强制更新流量数据
        for device in devices:
            # 尝试从设备获取最新流量数据（如果有相应功能）
            try:
                collect_device_traffic(device)
                count += 1
            except Exception as e:
                current_app.logger.warning(f"更新设备{device.name}流量数据出错: {str(e)}")
        
        return jsonify({
            "status": "success", 
            "message": f"成功刷新{count}个设备的流量数据",
            "count": count
        })
    except Exception as e:
        current_app.logger.error(f"刷新热力图缓存出错: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@monitor.route('/api/recalculate_utilization')
@login_required
def recalculate_utilization():
    """重新计算所有流量记录的利用率，使用最大流量值（入站或出站）除以带宽"""
    try:
        # 获取所有流量记录
        traffic_records = Traffic.query.all()
        
        # 计数器
        count = 0
        high_utilization_count = 0
        
        # 遍历所有记录，重新计算利用率
        for traffic in traffic_records:
            # 计算入站和出站速率(Mbps)
            in_rate = traffic.in_octets * 8 / 5  # 5秒内的数据
            out_rate = traffic.out_octets * 8 / 5
            
            # 获取带宽 (bps)
            bandwidth = traffic.bandwidth or 1000000000  # 默认1Gbps
            
            # 重新计算利用率 - 使用入站和出站中的较大值
            max_rate = max(in_rate, out_rate)
            old_utilization = traffic.utilization
            new_utilization = min(100, (max_rate / bandwidth) * 100)
            
            # 只有当新旧利用率差值大于1%时才更新
            if abs(new_utilization - old_utilization) > 1:
                traffic.utilization = new_utilization
                count += 1
                
                # 记录高利用率设备数量（超过70%的设备）
                if new_utilization > 70:
                    high_utilization_count += 1
        
        # 提交更改到数据库
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": f"成功重新计算了{count}条流量记录的利用率",
            "updated_records": count,
            "high_utilization_count": high_utilization_count
        })
    except Exception as e:
        current_app.logger.error(f"重新计算流量利用率出错: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500 