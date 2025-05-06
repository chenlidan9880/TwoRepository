-- 校园网络监控系统数据库表结构
-- 适用于SQLite和MySQL

-- 用户表
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(64) NOT NULL UNIQUE,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(128) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'user',
    last_login DATETIME,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

-- 设备表
CREATE TABLE devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(64) NOT NULL,
    ip_address VARCHAR(15) NOT NULL UNIQUE,
    mac_address VARCHAR(17),
    device_type VARCHAR(20) NOT NULL,
    location VARCHAR(100),
    description TEXT,
    snmp_community VARCHAR(64) DEFAULT 'public',
    snmp_version VARCHAR(10) DEFAULT '2c',
    snmp_port INTEGER DEFAULT 161,
    cpu_usage FLOAT DEFAULT 0,
    memory_usage FLOAT DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'unknown',
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

-- 流量数据表
CREATE TABLE traffic (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER NOT NULL,
    interface VARCHAR(64) NOT NULL,
    interface_index VARCHAR(10),
    inbound BIGINT NOT NULL DEFAULT 0,
    outbound BIGINT NOT NULL DEFAULT 0,
    in_packets BIGINT DEFAULT 0,
    out_packets BIGINT DEFAULT 0,
    in_errors INTEGER DEFAULT 0,
    out_errors INTEGER DEFAULT 0,
    bandwidth_utilization FLOAT DEFAULT 0,
    timestamp DATETIME NOT NULL,
    FOREIGN KEY (device_id) REFERENCES devices (id) ON DELETE CASCADE
);

-- 创建流量数据表索引
CREATE INDEX idx_traffic_device_id ON traffic (device_id);
CREATE INDEX idx_traffic_timestamp ON traffic (timestamp);
CREATE INDEX idx_traffic_device_timestamp ON traffic (device_id, timestamp);

-- 告警表
CREATE TABLE alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER NOT NULL,
    alert_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    title VARCHAR(100) NOT NULL,
    message TEXT NOT NULL,
    value FLOAT,
    threshold FLOAT,
    unit VARCHAR(10),
    is_read BOOLEAN NOT NULL DEFAULT 0,
    is_handled BOOLEAN NOT NULL DEFAULT 0,
    handled_by INTEGER,
    handled_at DATETIME,
    recovery_at DATETIME,
    duration INTEGER,
    created_at DATETIME NOT NULL,
    FOREIGN KEY (device_id) REFERENCES devices (id) ON DELETE CASCADE,
    FOREIGN KEY (handled_by) REFERENCES users (id) ON DELETE SET NULL
);

-- 创建告警表索引
CREATE INDEX idx_alerts_device_id ON alerts (device_id);
CREATE INDEX idx_alerts_handled ON alerts (is_handled);
CREATE INDEX idx_alerts_severity ON alerts (severity);
CREATE INDEX idx_alerts_created_at ON alerts (created_at);

-- 终端表
CREATE TABLE terminals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hostname VARCHAR(64),
    ip_address VARCHAR(15) NOT NULL UNIQUE,
    mac_address VARCHAR(17) NOT NULL UNIQUE,
    device_type VARCHAR(20) NOT NULL DEFAULT 'unknown',
    os_type VARCHAR(20),
    status VARCHAR(20) NOT NULL DEFAULT 'unknown',
    location VARCHAR(100),
    device_id INTEGER,
    connect_port VARCHAR(32),
    connect_type VARCHAR(32),
    description TEXT,
    last_seen DATETIME,
    first_seen DATETIME NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    FOREIGN KEY (device_id) REFERENCES devices (id) ON DELETE SET NULL
);

-- 创建终端表索引
CREATE INDEX idx_terminals_status ON terminals (status);
CREATE INDEX idx_terminals_device_type ON terminals (device_type);
CREATE INDEX idx_terminals_last_seen ON terminals (last_seen);
CREATE INDEX idx_terminals_device_id ON terminals (device_id);

-- 终端历史记录表
CREATE TABLE terminal_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    terminal_id INTEGER NOT NULL,
    ip_address VARCHAR(15) NOT NULL,
    status VARCHAR(20) NOT NULL,
    connection_time DATETIME,
    disconnection_time DATETIME,
    duration INTEGER,
    created_at DATETIME NOT NULL,
    FOREIGN KEY (terminal_id) REFERENCES terminals (id) ON DELETE CASCADE
);

-- 创建终端历史记录表索引
CREATE INDEX idx_terminal_history_terminal_id ON terminal_history (terminal_id);
CREATE INDEX idx_terminal_history_connection_time ON terminal_history (connection_time);

-- 系统设置表
CREATE TABLE settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    setting_key VARCHAR(50) NOT NULL UNIQUE,
    setting_value TEXT NOT NULL,
    setting_type VARCHAR(20) NOT NULL DEFAULT 'string',
    description TEXT,
    updated_at DATETIME NOT NULL
);

-- 添加默认系统设置
INSERT INTO settings (setting_key, setting_value, setting_type, description, updated_at) VALUES
    ('traffic_high_threshold', '80', 'float', '流量高负载阈值(%)', DATETIME('now')),
    ('cpu_high_threshold', '85', 'float', 'CPU高负载阈值(%)', DATETIME('now')),
    ('memory_high_threshold', '80', 'float', '内存高负载阈值(%)', DATETIME('now')),
    ('data_retention_days', '90', 'integer', '数据保留天数', DATETIME('now')),
    ('auto_refresh_interval', '30', 'integer', '页面自动刷新间隔(秒)', DATETIME('now'));

-- 操作日志表
CREATE TABLE operation_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    operation_type VARCHAR(20) NOT NULL,
    target_type VARCHAR(20) NOT NULL,
    target_id INTEGER,
    details TEXT,
    ip_address VARCHAR(15),
    created_at DATETIME NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
);

-- 创建操作日志表索引
CREATE INDEX idx_operation_logs_user_id ON operation_logs (user_id);
CREATE INDEX idx_operation_logs_operation_type ON operation_logs (operation_type);
CREATE INDEX idx_operation_logs_created_at ON operation_logs (created_at); 