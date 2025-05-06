/**
 * 校园网络流量热力图JavaScript文件
 */

// 当文档加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // 初始化热力图
    initHeatmap();
    
    // 初始化流量趋势图
    initTrendChart();
    
    // 初始化设备分布图
    initDeviceDistribution();
    
    // 绑定时间范围按钮事件
    bindTimeRangeEvents();
});

// 全局变量
let heatmapInstance = null;
let trendChart = null;
let distributionChart = null;
let currentTimeRange = 'week'; // 默认时间范围

/**
 * 初始化热力图
 */
function initHeatmap() {
    // 创建热力图实例
    heatmapInstance = h337.create({
        container: document.getElementById('heatmap-canvas'),
        radius: 40,
        maxOpacity: 0.8,
        minOpacity: 0.1,
        blur: 0.85,
        gradient: {
            0.4: 'blue',
            0.6: 'green',
            0.8: 'yellow',
            1.0: 'red'
        }
    });
    
    // 加载热力图数据
    loadHeatmapData(currentTimeRange);
}

/**
 * 加载热力图数据
 */
function loadHeatmapData(timeRange) {
    // 显示加载指示器
    document.getElementById('heatmap-container').classList.add('loading');
    
    // 发起AJAX请求获取数据
    fetch(`/heatmap/data?time_range=${timeRange}`)
        .then(response => response.json())
        .then(data => {
            // 更新热力图
            updateHeatmap(data);
            
            // 更新热点设备表格
            updateHotspotDevices(data.data);
            
            // 移除加载指示器
            document.getElementById('heatmap-container').classList.remove('loading');
        })
        .catch(error => {
            console.error('加载热力图数据出错:', error);
            document.getElementById('heatmap-container').classList.remove('loading');
            alert('加载热力图数据失败，请稍后重试。');
        });
}

/**
 * 更新热力图
 */
function updateHeatmap(data) {
    // 准备热力图数据
    const heatmapData = {
        max: 1.0,
        min: 0,
        data: data.data.map(item => ({
            x: item.x,
            y: item.y,
            value: item.value,
            radius: 40
        }))
    };
    
    // 设置热力图数据
    heatmapInstance.setData(heatmapData);
    
    // 可以选择性更新配置
    if (data.config) {
        // 更新配置
        heatmapInstance.configure(data.config);
    }
}

/**
 * 更新热点设备表格
 */
function updateHotspotDevices(devices) {
    const tbody = document.getElementById('hotspot-devices');
    tbody.innerHTML = '';
    
    // 按热力值排序
    const sortedDevices = [...devices].sort((a, b) => b.value - a.value);
    
    // 取前10个设备
    const topDevices = sortedDevices.slice(0, 10);
    
    // 生成表格行
    topDevices.forEach(device => {
        const row = document.createElement('tr');
        row.className = 'device-item';
        row.setAttribute('data-id', device.device_id);
        
        // 格式化流量数据
        const totalTraffic = formatTraffic(device.traffic);
        const inTraffic = formatTraffic(device.in_traffic);
        const outTraffic = formatTraffic(device.out_traffic);
        
        // 确定流量级别
        const trafficClass = getTrafficClass(device.value);
        
        row.innerHTML = `
            <td>${device.device_name || '未命名设备'}</td>
            <td>${device.location || '-'}</td>
            <td class="traffic-value ${trafficClass}">${totalTraffic}</td>
            <td>${inTraffic}</td>
            <td>${outTraffic}</td>
            <td>${(device.value * 100).toFixed(1)}%</td>
        `;
        
        // 添加点击事件 - 显示设备详情和趋势
        row.addEventListener('click', function() {
            showDeviceTrend(device.device_id);
        });
        
        tbody.appendChild(row);
    });
}

/**
 * 格式化流量数据
 */
function formatTraffic(bytes) {
    if (bytes === undefined || bytes === null) return '-';
    
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let size = bytes;
    let unitIndex = 0;
    
    while (size >= 1024 && unitIndex < units.length - 1) {
        size /= 1024;
        unitIndex++;
    }
    
    return size.toFixed(2) + ' ' + units[unitIndex];
}

/**
 * 获取流量级别的CSS类
 */
function getTrafficClass(value) {
    if (value >= 0.8) return 'traffic-high';
    if (value >= 0.4) return 'traffic-medium';
    return 'traffic-low';
}

/**
 * 初始化流量趋势图
 */
function initTrendChart() {
    // 初始化ECharts实例
    trendChart = echarts.init(document.getElementById('trend-chart'));
    
    // 设置图表选项
    const option = {
        title: {
            text: '整体流量趋势',
            left: 'center',
            textStyle: {
                fontSize: 14
            }
        },
        tooltip: {
            trigger: 'axis',
            formatter: function(params) {
                let result = params[0].name + '<br/>';
                params.forEach(param => {
                    result += `${param.seriesName}: ${formatTraffic(param.value * 125)}/s<br/>`;
                });
                return result;
            }
        },
        legend: {
            data: ['入站流量', '出站流量'],
            bottom: 0
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '15%',
            top: '15%',
            containLabel: true
        },
        xAxis: {
            type: 'category',
            boundaryGap: false,
            data: []
        },
        yAxis: {
            type: 'value',
            axisLabel: {
                formatter: function(value) {
                    return (value * 8).toFixed(0) + ' Mbps';
                }
            }
        },
        series: [
            {
                name: '入站流量',
                type: 'line',
                stack: '总量',
                areaStyle: {},
                emphasis: {
                    focus: 'series'
                },
                data: [],
                smooth: true,
                lineStyle: {
                    width: 2
                },
                itemStyle: {
                    color: '#4CAF50'
                }
            },
            {
                name: '出站流量',
                type: 'line',
                stack: '总量',
                areaStyle: {},
                emphasis: {
                    focus: 'series'
                },
                data: [],
                smooth: true,
                lineStyle: {
                    width: 2
                },
                itemStyle: {
                    color: '#2196F3'
                }
            }
        ]
    };
    
    // 使用刚指定的配置项和数据显示图表
    trendChart.setOption(option);
    
    // 加载全局流量趋势数据
    loadTrendData();
    
    // 窗口大小改变时，重置图表大小
    window.addEventListener('resize', function() {
        trendChart.resize();
    });
}

/**
 * 加载流量趋势数据
 */
function loadTrendData(deviceId = null) {
    // 构造请求URL
    let url = `/heatmap/trend?time_range=${currentTimeRange}`;
    if (deviceId) {
        url += `&device_id=${deviceId}`;
    }
    
    // 发起AJAX请求获取数据
    fetch(url)
        .then(response => response.json())
        .then(data => {
            updateTrendChart(data, deviceId);
        })
        .catch(error => {
            console.error('加载流量趋势数据出错:', error);
        });
}

/**
 * 更新流量趋势图
 */
function updateTrendChart(data, deviceId = null) {
    // 准备X轴数据和Y轴数据
    const xAxisData = [];
    const inSeriesData = [];
    const outSeriesData = [];
    
    // 确保数据存在且有series
    if (data && data.series && data.series.length >= 2) {
        // 提取入站流量数据
        const inSeries = data.series.find(s => s.type === 'in') || { data: [] };
        // 提取出站流量数据
        const outSeries = data.series.find(s => s.type === 'out') || { data: [] };
        
        // 处理入站流量数据
        inSeries.data.forEach(item => {
            if (!xAxisData.includes(item.x)) {
                xAxisData.push(item.x);
            }
            inSeriesData.push(item.y / 8); // 转换bit/s为byte/s
        });
        
        // 处理出站流量数据
        outSeries.data.forEach(item => {
            if (!xAxisData.includes(item.x)) {
                outSeriesData.push(item.y / 8); // 转换bit/s为byte/s
            }
        });
    }
    
    // 更新图表标题
    let title = '整体流量趋势';
    if (deviceId) {
        const device = document.querySelector(`tr[data-id="${deviceId}"]`);
        if (device) {
            const deviceName = device.querySelector('td:first-child').textContent;
            title = `${deviceName} 流量趋势`;
        } else {
            title = `设备 ${deviceId} 流量趋势`;
        }
    }
    
    // 更新图表选项
    trendChart.setOption({
        title: {
            text: title
        },
        xAxis: {
            data: xAxisData
        },
        series: [
            {
                name: '入站流量',
                data: inSeriesData
            },
            {
                name: '出站流量',
                data: outSeriesData
            }
        ]
    });
}

/**
 * 显示设备流量趋势
 */
function showDeviceTrend(deviceId) {
    loadTrendData(deviceId);
}

/**
 * 初始化设备分布图
 */
function initDeviceDistribution() {
    // 初始化ECharts实例
    distributionChart = echarts.init(document.getElementById('device-distribution'));
    
    // 设置图表选项
    const option = {
        title: {
            text: '终端设备类型分布',
            left: 'center',
            textStyle: {
                fontSize: 14
            }
        },
        tooltip: {
            trigger: 'item',
            formatter: '{a} <br/>{b}: {c} ({d}%)'
        },
        legend: {
            orient: 'horizontal',
            bottom: 0,
            data: []
        },
        series: [
            {
                name: '设备类型',
                type: 'pie',
                radius: ['40%', '70%'],
                avoidLabelOverlap: false,
                itemStyle: {
                    borderRadius: 10,
                    borderColor: '#fff',
                    borderWidth: 2
                },
                label: {
                    show: false,
                    position: 'center'
                },
                emphasis: {
                    label: {
                        show: true,
                        fontSize: 14,
                        fontWeight: 'bold'
                    }
                },
                labelLine: {
                    show: false
                },
                data: []
            }
        ]
    };
    
    // 使用刚指定的配置项和数据显示图表
    distributionChart.setOption(option);
    
    // 加载设备分布数据
    loadDistributionData();
    
    // 窗口大小改变时，重置图表大小
    window.addEventListener('resize', function() {
        distributionChart.resize();
    });
}

/**
 * 加载设备分布数据
 */
function loadDistributionData() {
    // 发起AJAX请求获取数据
    fetch('/heatmap/distribution')
        .then(response => response.json())
        .then(data => {
            updateDistributionChart(data);
        })
        .catch(error => {
            console.error('加载设备分布数据出错:', error);
        });
}

/**
 * 更新设备分布图
 */
function updateDistributionChart(data) {
    // 准备图例数据
    const legendData = data.map(item => item.name);
    
    // 更新图表选项
    distributionChart.setOption({
        legend: {
            data: legendData
        },
        series: [
            {
                data: data
            }
        ]
    });
}

/**
 * 绑定时间范围按钮事件
 */
function bindTimeRangeEvents() {
    const buttons = document.querySelectorAll('.time-range');
    
    buttons.forEach(button => {
        button.addEventListener('click', function() {
            // 移除其他按钮的active类
            buttons.forEach(btn => btn.classList.remove('active'));
            
            // 添加当前按钮的active类
            this.classList.add('active');
            
            // 更新当前时间范围
            currentTimeRange = this.getAttribute('data-range');
            
            // 重新加载数据
            loadHeatmapData(currentTimeRange);
            loadTrendData();
        });
    });
} 