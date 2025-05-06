"""
数据可视化解决方案指南

由于原项目使用的 flask-echarts 和 pyecharts-flask 包不可用，
这个文件提供了使用 pyecharts 和其他库实现数据可视化的示例代码。
"""

from flask import render_template, Markup
from pyecharts import options as opts
from pyecharts.charts import Line, Bar, Pie, Gauge
from pyecharts.globals import ThemeType

# PyEcharts 直接集成示例

def create_line_chart(x_data, y_data, title="流量趋势", subtitle=""):
    """
    创建折线图
    
    参数:
        x_data: X轴数据（例如时间点）
        y_data: Y轴数据（例如流量值）
        title: 图表标题
        subtitle: 图表副标题
    
    返回:
        渲染后的HTML字符串
    """
    line = (
        Line(init_opts=opts.InitOpts(theme=ThemeType.LIGHT))
        .add_xaxis(x_data)
        .add_yaxis("流量数据", y_data, is_smooth=True)
        .set_global_opts(
            title_opts=opts.TitleOpts(title=title, subtitle=subtitle),
            tooltip_opts=opts.TooltipOpts(trigger="axis"),
            toolbox_opts=opts.ToolboxOpts(is_show=True),
            yaxis_opts=opts.AxisOpts(
                type_="value",
                axistick_opts=opts.AxisTickOpts(is_show=True),
                splitline_opts=opts.SplitLineOpts(is_show=True),
            ),
            xaxis_opts=opts.AxisOpts(type_="category", boundary_gap=False),
        )
    )
    return Markup(line.render_embed())

def create_bar_chart(x_data, y_data, title="设备流量对比"):
    """创建柱状图"""
    bar = (
        Bar(init_opts=opts.InitOpts(theme=ThemeType.LIGHT))
        .add_xaxis(x_data)
        .add_yaxis("流量数据", y_data)
        .set_global_opts(
            title_opts=opts.TitleOpts(title=title),
            toolbox_opts=opts.ToolboxOpts(is_show=True),
        )
    )
    return Markup(bar.render_embed())

def create_pie_chart(data_pairs, title="流量分布"):
    """创建饼图"""
    pie = (
        Pie(init_opts=opts.InitOpts(theme=ThemeType.LIGHT))
        .add("", data_pairs)
        .set_global_opts(
            title_opts=opts.TitleOpts(title=title),
            legend_opts=opts.LegendOpts(orient="vertical", pos_top="15%", pos_left="2%"),
        )
        .set_series_opts(label_opts=opts.LabelOpts(formatter="{b}: {c} ({d}%)"))
    )
    return Markup(pie.render_embed())

def create_gauge_chart(value, title="CPU使用率"):
    """创建仪表盘"""
    gauge = (
        Gauge(init_opts=opts.InitOpts(theme=ThemeType.LIGHT))
        .add("", [("", value)], max_=100)
        .set_global_opts(
            title_opts=opts.TitleOpts(title=title),
        )
    )
    return Markup(gauge.render_embed())

# 在Flask视图中的使用示例

"""
# 在Flask视图函数中使用的示例代码:

from flask import render_template
from app.models.traffic import Traffic
from app.models.device import Device
from datetime import datetime, timedelta
import random

@app.route('/dashboard')
def dashboard():
    # 获取过去24小时的时间点
    now = datetime.now()
    time_points = [(now - timedelta(hours=i)).strftime('%H:%M') for i in range(24, 0, -1)]
    
    # 假设从数据库获取流量数据
    traffic_data = [random.randint(100, 1000) for _ in range(24)]
    
    # 获取设备名称列表
    devices = Device.query.all()
    device_names = [device.name for device in devices]
    device_traffic = [random.randint(100, 1000) for _ in range(len(devices))]
    
    # 生成饼图数据
    pie_data = [(name, traffic) for name, traffic in zip(device_names, device_traffic)]
    
    # 生成CPU使用率数据
    cpu_usage = random.randint(20, 90)
    
    # 创建图表
    line_chart = create_line_chart(time_points, traffic_data, "过去24小时流量趋势")
    bar_chart = create_bar_chart(device_names, device_traffic, "设备流量对比")
    pie_chart = create_pie_chart(pie_data, "流量分布")
    gauge_chart = create_gauge_chart(cpu_usage, "CPU使用率")
    
    return render_template(
        'dashboard.html',
        line_chart=line_chart,
        bar_chart=bar_chart,
        pie_chart=pie_chart,
        gauge_chart=gauge_chart
    )
"""

# 在HTML模板中的使用示例

"""
<!-- dashboard.html 模板示例 -->
{% extends 'base.html' %}

{% block content %}
<div class="container">
    <h1>网络监控仪表盘</h1>
    
    <div class="row">
        <div class="col-md-6">
            <div class="card">
                <div class="card-header">过去24小时流量趋势</div>
                <div class="card-body">
                    {{ line_chart|safe }}
                </div>
            </div>
        </div>
        
        <div class="col-md-6">
            <div class="card">
                <div class="card-header">设备流量对比</div>
                <div class="card-body">
                    {{ bar_chart|safe }}
                </div>
            </div>
        </div>
    </div>
    
    <div class="row mt-4">
        <div class="col-md-6">
            <div class="card">
                <div class="card-header">流量分布</div>
                <div class="card-body">
                    {{ pie_chart|safe }}
                </div>
            </div>
        </div>
        
        <div class="col-md-6">
            <div class="card">
                <div class="card-header">CPU使用率</div>
                <div class="card-body">
                    {{ gauge_chart|safe }}
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
"""

# 使用Chart.js的替代方案

"""
# 在Flask视图中使用Chart.js的示例

from flask import render_template, jsonify

@app.route('/chart_data')
def chart_data():
    # 获取数据
    time_points = [(now - timedelta(hours=i)).strftime('%H:%M') for i in range(24, 0, -1)]
    traffic_data = [random.randint(100, 1000) for _ in range(24)]
    
    return jsonify({
        'labels': time_points,
        'datasets': [{
            'label': '流量数据',
            'data': traffic_data,
            'borderColor': 'rgba(75, 192, 192, 1)',
            'backgroundColor': 'rgba(75, 192, 192, 0.2)',
        }]
    })

@app.route('/charts')
def charts():
    return render_template('charts.html')
"""

"""
<!-- charts.html 使用Chart.js的模板示例 -->
{% extends 'base.html' %}

{% block head %}
{{ super() }}
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
{% endblock %}

{% block content %}
<div class="container">
    <h1>网络监控仪表盘 (Chart.js)</h1>
    
    <div class="row">
        <div class="col-md-12">
            <div class="card">
                <div class="card-header">过去24小时流量趋势</div>
                <div class="card-body">
                    <canvas id="trafficChart"></canvas>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
document.addEventListener('DOMContentLoaded', function() {
    fetch('/chart_data')
        .then(response => response.json())
        .then(data => {
            const ctx = document.getElementById('trafficChart').getContext('2d');
            new Chart(ctx, {
                type: 'line',
                data: data,
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        });
});
</script>
{% endblock %}
""" 