/**
 * 拓扑可视化调试脚本
 */

// 检查Three.js库是否加载
function checkThreeJs() {
    console.log('检查Three.js加载状态');
    if (typeof THREE === 'undefined') {
        console.error('错误: Three.js 库未加载!');
        document.getElementById('error-message').innerHTML = 
            '<div class="alert alert-danger">Three.js 库加载失败! 请检查网络连接或刷新页面。</div>';
        return false;
    }
    console.log('Three.js 已成功加载!', THREE.REVISION);
    return true;
}

// 加载拓扑数据并记录响应
function loadTopologyData() {
    console.log('开始加载拓扑数据...');
    $.ajax({
        url: '/topology/api/topology-data',
        method: 'GET',
        success: function(data) {
            console.log('成功获取拓扑数据:', data);
            document.getElementById('data-info').innerHTML = 
                '<div class="alert alert-success">成功获取拓扑数据: ' + 
                data.nodes.length + ' 个节点, ' + 
                data.links.length + ' 个连接</div>';
        },
        error: function(error) {
            console.error('获取拓扑数据失败:', error);
            document.getElementById('data-info').innerHTML = 
                '<div class="alert alert-danger">获取拓扑数据失败! 详情请查看控制台。</div>';
        }
    });
}

// 页面加载完成后执行
$(document).ready(function() {
    console.log('拓扑调试工具已初始化');
    
    // 创建调试信息区域
    const debugContainer = document.createElement('div');
    debugContainer.innerHTML = `
        <div id="debug-panel" style="position:absolute; top:10px; left:10px; z-index:1000; background:rgba(255,255,255,0.8); padding:10px; border-radius:5px;">
            <h4>拓扑调试信息</h4>
            <div id="error-message"></div>
            <div id="data-info"></div>
            <button id="check-threejs" class="btn btn-sm btn-primary">检查Three.js</button>
            <button id="load-data" class="btn btn-sm btn-info">加载拓扑数据</button>
        </div>
    `;
    document.body.appendChild(debugContainer);
    
    // 绑定按钮事件
    document.getElementById('check-threejs').addEventListener('click', checkThreeJs);
    document.getElementById('load-data').addEventListener('click', loadTopologyData);
}); 