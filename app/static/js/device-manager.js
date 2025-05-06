/**
 * 设备管理界面交互增强
 */
 
// 初始化设备管理页面
document.addEventListener('DOMContentLoaded', function() {
  // 添加淡入动画
  document.querySelectorAll('.device-card, .stat-card').forEach(function(element) {
    element.classList.add('fade-in');
  });
  
  // 初始化设备过滤功能
  initDeviceFilters();
  
  // 初始化流量图表
  initTrafficChart();
  
  // 初始化刷新按钮
  initRefreshButton();
  
  // 初始化终端项目悬停效果
  initTerminalHoverEffects();
  
  // 初始化设备状态徽章
  initStatusTooltips();
});

/**
 * 初始化设备过滤功能
 */
function initDeviceFilters() {
  // 检查是否在设备列表页面
  if (!document.getElementById('deviceGrid')) return;
  
  // 添加过滤器监听器
  document.querySelectorAll('.device-filter').forEach(function(filter) {
    filter.addEventListener('change', function() {
      filterDevices();
    });
  });
  
  // 添加搜索框监听器
  const searchInput = document.getElementById('deviceSearch');
  if (searchInput) {
    searchInput.addEventListener('keyup', function() {
      filterDevices();
    });
  }
  
  // 自动生成位置过滤器选项
  const locationFilter = document.querySelector('[data-filter="location"]');
  if (locationFilter) {
    // 收集所有独特的位置
    const locations = new Set();
    document.querySelectorAll('.device-item').forEach(function(device) {
      const location = device.getAttribute('data-location');
      if (location) locations.add(location);
    });
    
    // 添加位置选项
    locations.forEach(function(location) {
      const option = document.createElement('option');
      option.value = location;
      option.textContent = location;
      locationFilter.appendChild(option);
    });
  }
}

/**
 * 过滤设备列表
 */
function filterDevices() {
  const typeFilter = document.querySelector('[data-filter="type"]');
  const statusFilter = document.querySelector('[data-filter="status"]');
  const locationFilter = document.querySelector('[data-filter="location"]');
  const terminalCountFilter = document.querySelector('[data-filter="terminal-count"]');
  const searchInput = document.getElementById('deviceSearch');
  
  // 获取过滤条件
  const type = typeFilter ? typeFilter.value : '';
  const status = statusFilter ? statusFilter.value : '';
  const location = locationFilter ? locationFilter.value : '';
  const terminalCount = terminalCountFilter ? terminalCountFilter.value : '';
  const searchText = searchInput ? searchInput.value.toLowerCase() : '';
  
  // 过滤设备卡片
  document.querySelectorAll('.device-item').forEach(function(device) {
    const deviceType = device.getAttribute('data-type') || '';
    const deviceStatus = device.getAttribute('data-status') || '';
    const deviceLocation = device.getAttribute('data-location') || '';
    const deviceTerminalCount = parseInt(device.getAttribute('data-terminal-count') || '0');
    const deviceName = device.querySelector('.device-name')?.textContent.toLowerCase() || '';
    
    // 应用过滤条件
    const typeMatch = !type || deviceType === type;
    const statusMatch = !status || deviceStatus === status;
    const locationMatch = !location || deviceLocation === location;
    const searchMatch = !searchText || deviceName.includes(searchText);
    
    // 终端数量匹配逻辑
    let terminalCountMatch = true;
    if (terminalCount) {
      if (terminalCount === '0') {
        terminalCountMatch = deviceTerminalCount === 0;
      } else if (terminalCount === '1-9') {
        terminalCountMatch = deviceTerminalCount > 0 && deviceTerminalCount < 10;
      } else if (terminalCount === '10-19') {
        terminalCountMatch = deviceTerminalCount >= 10 && deviceTerminalCount < 20;
      } else if (terminalCount === '20+') {
        terminalCountMatch = deviceTerminalCount >= 20;
      }
    }
    
    // 显示或隐藏设备
    if (typeMatch && statusMatch && locationMatch && searchMatch && terminalCountMatch) {
      device.style.display = '';
    } else {
      device.style.display = 'none';
    }
  });
  
  // 更新计数器
  updateFilteredCount();
}

/**
 * 更新过滤后的设备计数
 */
function updateFilteredCount() {
  const counter = document.getElementById('filteredCount');
  if (!counter) return;
  
  const totalDevices = document.querySelectorAll('.device-item').length;
  const visibleDevices = document.querySelectorAll('.device-item').length - 
                         document.querySelectorAll('.device-item[style*="display: none"]').length;
  
  counter.textContent = `显示 ${visibleDevices} / ${totalDevices} 个设备`;
}

/**
 * 初始化流量图表
 */
function initTrafficChart() {
  const chartContainer = document.getElementById('traffic-chart');
  if (!chartContainer) return;
  
  // 检查Echarts库是否加载
  if (typeof echarts === 'undefined') {
    console.log('Echarts库未加载，尝试重新加载');
    
    // 尝试重新加载Echarts库
    const script = document.createElement('script');
    script.src = '/static/vendor/echarts/echarts.min.js';
    script.onload = function() {
      console.log('Echarts库加载成功，初始化图表');
      // 延迟一点时间初始化，确保库完全加载
      setTimeout(initTrafficChart, 500);
    };
    script.onerror = function() {
      console.error('加载Echarts库失败');
      chartContainer.innerHTML = '<div class="alert alert-danger">图表库加载失败，请刷新页面重试</div>';
    };
    document.head.appendChild(script);
    return;
  }
  
  // 如果图表已经初始化，先销毁
  if (window.trafficChart) {
    window.trafficChart.dispose();
  }
  
  try {
    // 初始化图表
    window.trafficChart = echarts.init(chartContainer);
    
    // 添加时间范围选择按钮事件
    document.querySelectorAll('.traffic-controls .btn').forEach(function(btn) {
      btn.addEventListener('click', function() {
        document.querySelectorAll('.traffic-controls .btn').forEach(function(b) {
          b.classList.remove('active');
        });
        btn.classList.add('active');
        
        // 这里可以根据需要发送AJAX请求获取不同时间范围的数据
        // 目前只是示例，实际应用中应该调用API获取数据
        const period = btn.getAttribute('data-period');
        console.log('选择时间范围:', period);
        
        // 修改图表标题
        let title = '24小时流量趋势';
        if (period === '7d') title = '7天流量趋势';
        if (period === '30d') title = '30天流量趋势';
        
        // 以演示为目的，重新设置图表选项
        const option = window.trafficChart.getOption();
        option.title = [{ text: title }];
        window.trafficChart.setOption(option);
      });
    });
    
    // 窗口大小改变时重绘图表
    window.addEventListener('resize', function() {
      if (window.trafficChart) {
        window.trafficChart.resize();
      }
    });
  } catch (error) {
    console.error('初始化流量图表失败:', error);
    chartContainer.innerHTML = '<div class="alert alert-danger">初始化图表失败: ' + error.message + '</div>';
  }
}

/**
 * 初始化刷新按钮
 */
function initRefreshButton() {
  const refreshButton = document.getElementById('refreshDevice');
  if (!refreshButton) return;
  
  refreshButton.addEventListener('click', function() {
    const icon = refreshButton.querySelector('i');
    if (icon) icon.classList.add('fa-spin');
    
    // 模拟数据刷新
    setTimeout(function() {
      if (icon) icon.classList.remove('fa-spin');
      
      // 显示成功消息
      const alertContainer = document.createElement('div');
      alertContainer.className = 'alert alert-success alert-dismissible fade show mt-3';
      alertContainer.innerHTML = `
        <i class="fas fa-check-circle me-2"></i> 设备数据刷新成功
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
      `;
      
      // 添加到页面
      const header = document.querySelector('.device-detail-header');
      if (header) {
        header.after(alertContainer);
        
        // 自动关闭
        setTimeout(function() {
          alertContainer.remove();
        }, 3000);
      }
    }, 1500);
  });
}

/**
 * 初始化终端悬停效果
 */
function initTerminalHoverEffects() {
  document.querySelectorAll('.terminal-item').forEach(function(item) {
    item.addEventListener('mouseenter', function() {
      item.style.boxShadow = '0 0.15rem 1.75rem 0 rgba(58, 59, 69, 0.15)';
    });
    
    item.addEventListener('mouseleave', function() {
      item.style.boxShadow = 'none';
    });
  });
}

/**
 * 初始化状态提示
 */
function initStatusTooltips() {
  // 需要Bootstrap的Tooltip功能
  if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
    document.querySelectorAll('[title]').forEach(function(element) {
      new bootstrap.Tooltip(element);
    });
  }
} 