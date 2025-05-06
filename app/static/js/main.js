/**
 * 校园网流量可视化系统主JS文件
 */

// 初始化ToolTips
const initTooltips = () => {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
};

// 初始化Popovers
const initPopovers = () => {
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    const popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
};

// 确认删除操作
const confirmDelete = (event, message = '确定要删除吗？') => {
    if (!confirm(message)) {
        event.preventDefault();
        return false;
    }
    return true;
};

// 格式化流量大小
const formatTraffic = (bytes, decimals = 2) => {
    if (bytes === 0) return '0 Bytes';

    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];

    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
};

// 格式化流量速率
const formatRate = (bps, decimals = 2) => {
    if (bps === 0) return '0 bps';

    const k = 1000;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['bps', 'Kbps', 'Mbps', 'Gbps', 'Tbps'];

    const i = Math.floor(Math.log(bps) / Math.log(k));

    return parseFloat((bps / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
};

// 生成随机颜色
const getRandomColor = () => {
    const letters = '0123456789ABCDEF';
    let color = '#';
    for (let i = 0; i < 6; i++) {
        color += letters[Math.floor(Math.random() * 16)];
    }
    return color;
};

// 初始化自动刷新
const initAutoRefresh = (url, interval = 5000) => {
    setInterval(() => {
        fetch(url)
            .then(response => response.json())
            .then(data => {
                if (typeof window.updateData === 'function') {
                    window.updateData(data);
                }
            })
            .catch(error => console.error('Error:', error));
    }, interval);
};

// 文档加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    initTooltips();
    initPopovers();

    // 处理删除按钮
    document.querySelectorAll('.btn-delete').forEach(button => {
        button.addEventListener('click', (event) => {
            confirmDelete(event);
        });
    });
}); 