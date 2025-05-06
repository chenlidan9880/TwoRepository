"""
终端设备识别模块
实现通过MAC地址、UserAgent等信息识别终端设备类型和操作系统
"""

import re
import json
import os
import csv
import requests
from datetime import datetime, timedelta
from flask import current_app
from sqlalchemy import or_
from app import db
from app.models.terminal import Terminal
from app.models.device import Device

# 尝试导入user-agents库，如果不存在则使用替代方案
try:
    from user_agents import parse as ua_parse
    USER_AGENTS_AVAILABLE = True
except ImportError:
    USER_AGENTS_AVAILABLE = False
    current_app.logger.warning("user-agents库未安装，设备识别功能将受限")

# MAC地址OUI前缀数据库存储路径
OUI_DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'oui.csv')

# 设备指纹数据库存储路径
FINGERPRINT_DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'fingerprints.csv')

# MAC地址正则表达式
MAC_REGEX = re.compile(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$')

# 确保数据目录存在
os.makedirs(os.path.join(os.path.dirname(__file__), 'data'), exist_ok=True)

# 公共设备类型映射
DEVICE_TYPE_MAP = {
    'apple': '苹果设备',
    'iphone': '苹果手机',
    'ipad': '苹果平板',
    'macbook': 'MacBook',
    'imac': 'iMac',
    'android': '安卓设备',
    'windows': 'Windows设备',
    'linux': 'Linux设备',
    'router': '路由器',
    'switch': '交换机',
    'printer': '打印机',
    'camera': '摄像头',
    'tv': '智能电视',
    'iot': '物联网设备'
}

# OS类型映射
OS_TYPE_MAP = {
    'windows': 'Windows',
    'macos': 'macOS',
    'ios': 'iOS',
    'android': 'Android',
    'linux': 'Linux',
    'chromeos': 'ChromeOS',
    'ubuntu': 'Ubuntu',
    'debian': 'Debian',
    'fedora': 'Fedora',
    'redhat': 'Red Hat',
    'centos': 'CentOS'
}

# 缓存的OUI数据库
oui_cache = {}

def init_oui_database():
    """初始化OUI数据库"""
    global oui_cache
    
    # 确保数据目录存在
    os.makedirs(os.path.dirname(OUI_DB_PATH), exist_ok=True)
    
    # 检查OUI数据库是否存在，不存在则下载
    if not os.path.exists(OUI_DB_PATH) or os.path.getsize(OUI_DB_PATH) == 0:
        current_app.logger.info("OUI数据库不存在，开始下载...")
        download_oui_database()
    
    # 读取OUI数据库
    if os.path.exists(OUI_DB_PATH):
        try:
            with open(OUI_DB_PATH, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader)  # 跳过表头
                for row in reader:
                    if len(row) >= 2:
                        mac_prefix = row[0].strip().lower()
                        vendor = row[1].strip()
                        oui_cache[mac_prefix] = vendor
            current_app.logger.info(f"已加载 {len(oui_cache)} 条OUI记录到内存")
        except Exception as e:
            current_app.logger.error(f"加载OUI数据库失败: {str(e)}")
    else:
        current_app.logger.warning("OUI数据库文件不存在")

def download_oui_database():
    """下载OUI数据库"""
    try:
        # IEEE OUI数据库官方API - 示例URL，实际使用需要替换
        url = "https://standards-oui.ieee.org/oui/oui.csv"
        
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            with open(OUI_DB_PATH, 'w', encoding='utf-8') as f:
                f.write(response.text)
            current_app.logger.info("OUI数据库下载完成")
            return True
        else:
            current_app.logger.error(f"下载OUI数据库失败，状态码: {response.status_code}")
            # 如果下载失败，创建一个空的数据库文件
            with open(OUI_DB_PATH, 'w', encoding='utf-8') as f:
                f.write("mac_prefix,vendor\n")
            return False
    except Exception as e:
        current_app.logger.error(f"下载OUI数据库异常: {str(e)}")
        # 如果下载失败，创建一个空的数据库文件
        with open(OUI_DB_PATH, 'w', encoding='utf-8') as f:
            f.write("mac_prefix,vendor\n")
        return False

def lookup_mac_vendor(mac_address):
    """查找MAC地址对应的厂商"""
    if not mac_address:
        return None
    
    # 标准化MAC地址格式
    mac_address = re.sub('[.:-]', '', mac_address).lower()
    
    # 如果OUI缓存为空，初始化一次
    if not oui_cache:
        init_oui_database()
    
    # 尝试不同长度的MAC前缀
    for prefix_len in [6, 8, 9]:
        if len(mac_address) >= prefix_len:
            prefix = mac_address[:prefix_len]
            if prefix in oui_cache:
                return oui_cache[prefix]
    
    return None

def parse_user_agent(user_agent_string):
    """解析用户代理字符串"""
    if not user_agent_string:
        return {
            "browser": None,
            "browser_version": None,
            "os": None,
            "os_version": None,
            "device": None,
            "device_brand": None,
            "is_mobile": False,
            "is_tablet": False,
            "is_pc": True
        }
    
    try:
        if USER_AGENTS_AVAILABLE:
            user_agent = ua_parse(user_agent_string)
            
            # 获取操作系统信息
            os_info = f"{user_agent.os.family}"
            if user_agent.os.version_string:
                os_info += f" {user_agent.os.version_string}"
            
            # 获取浏览器信息
            browser_info = f"{user_agent.browser.family}"
            if user_agent.browser.version_string:
                browser_info += f" {user_agent.browser.version_string}"
            
            # 设备类型判断
            device_type = "PC"
            if user_agent.is_mobile:
                device_type = "Mobile"
            elif user_agent.is_tablet:
                device_type = "Tablet"
            
            return {
                "browser": user_agent.browser.family,
                "browser_version": user_agent.browser.version_string,
                "os": user_agent.os.family,
                "os_version": user_agent.os.version_string,
                "device": user_agent.device.family,
                "device_brand": user_agent.device.brand,
                "is_mobile": user_agent.is_mobile,
                "is_tablet": user_agent.is_tablet,
                "is_pc": user_agent.is_pc,
                "os_info": os_info,
                "browser_info": browser_info,
                "device_type": device_type
            }
        else:
            # 简单的用户代理解析逻辑，作为备选方案
            os_info = "Unknown"
            browser_info = "Unknown"
            is_mobile = False
            is_tablet = False
            
            ua = user_agent_string.lower()
            
            # 简单操作系统检测
            if "windows" in ua:
                os_info = "Windows"
            elif "mac os" in ua or "macos" in ua:
                os_info = "macOS"
            elif "iphone" in ua:
                os_info = "iOS"
                is_mobile = True
            elif "ipad" in ua:
                os_info = "iOS"
                is_tablet = True
            elif "android" in ua:
                os_info = "Android"
                is_mobile = "mobile" in ua and "tablet" not in ua
                is_tablet = "tablet" in ua
            elif "linux" in ua:
                os_info = "Linux"
            
            # 简单浏览器检测
            if "chrome" in ua and "edge" not in ua and "safari" not in ua:
                browser_info = "Chrome"
            elif "firefox" in ua:
                browser_info = "Firefox"
            elif "safari" in ua and "chrome" not in ua:
                browser_info = "Safari"
            elif "edge" in ua:
                browser_info = "Edge"
            elif "msie" in ua or "trident" in ua:
                browser_info = "Internet Explorer"
            
            return {
                "browser": browser_info,
                "browser_version": None,
                "os": os_info,
                "os_version": None,
                "device": "Unknown",
                "device_brand": None,
                "is_mobile": is_mobile,
                "is_tablet": is_tablet,
                "is_pc": not (is_mobile or is_tablet),
                "os_info": os_info,
                "browser_info": browser_info,
                "device_type": "Mobile" if is_mobile else "Tablet" if is_tablet else "PC"
            }
    except Exception as e:
        current_app.logger.error(f"解析用户代理字符串失败: {str(e)}")
        return {
            "browser": None,
            "browser_version": None,
            "os": None,
            "os_version": None,
            "device": None,
            "device_brand": None,
            "is_mobile": False,
            "is_tablet": False,
            "is_pc": True,
            "error": str(e)
        }

def identify_terminal(terminal_data):
    """
    识别终端设备信息
    
    Args:
        terminal_data: 包含终端数据的字典，可能包含 mac_address, user_agent, hostname, ip_address 等字段
    
    Returns:
        包含识别结果的字典
    """
    result = {
        "device_type": "Unknown",
        "os_type": "Unknown",
        "vendor": None,
        "browser": None
    }
    
    # 从MAC地址识别厂商
    if "mac_address" in terminal_data and terminal_data["mac_address"]:
        vendor = lookup_mac_vendor(terminal_data["mac_address"])
        if vendor:
            result["vendor"] = vendor
            
            # 通过厂商名称推断设备类型
            vendor_lower = vendor.lower()
            if any(x in vendor_lower for x in ["apple", "iphone", "ipad", "macintosh"]):
                result["device_type"] = "Apple"
            elif any(x in vendor_lower for x in ["samsung", "huawei", "xiaomi", "oppo", "vivo"]):
                result["device_type"] = "Mobile"
            elif "cisco" in vendor_lower:
                result["device_type"] = "Network"
            elif any(x in vendor_lower for x in ["intel", "dell", "lenovo", "hp", "asus"]):
                result["device_type"] = "PC"
    
    # 从用户代理字符串识别设备和操作系统
    if "user_agent" in terminal_data and terminal_data["user_agent"]:
        ua_info = parse_user_agent(terminal_data["user_agent"])
        
        # 更新操作系统信息
        if ua_info["os"] and ua_info["os"] != "Other":
            result["os_type"] = ua_info["os"]
        
        # 更新浏览器信息
        if ua_info["browser"] and ua_info["browser"] != "Other":
            result["browser"] = ua_info["browser"]
        
        # 如果设备类型未知，根据UA推断
        if result["device_type"] == "Unknown":
            if ua_info["is_mobile"]:
                result["device_type"] = "Mobile"
            elif ua_info["is_tablet"]:
                result["device_type"] = "Tablet"
            elif ua_info["is_pc"]:
                result["device_type"] = "PC"
            
            # 根据设备品牌进一步细化设备类型
            if ua_info["device_brand"] and ua_info["device_brand"] != "Other":
                result["vendor"] = ua_info["device_brand"]
                
                if ua_info["device_brand"].lower() == "apple":
                    result["device_type"] = "Apple"
    
    # 根据主机名推断设备类型
    if "hostname" in terminal_data and terminal_data["hostname"]:
        hostname = terminal_data["hostname"].lower()
        
        if any(x in hostname for x in ["iphone", "ipad", "mac"]):
            result["device_type"] = "Apple"
        elif any(x in hostname for x in ["android", "samsung", "huawei", "xiaomi"]):
            result["device_type"] = "Mobile"
        elif any(x in hostname for x in ["pc", "desktop", "laptop"]):
            result["device_type"] = "PC"
        elif any(x in hostname for x in ["router", "switch", "ap"]):
            result["device_type"] = "Network"
    
    return result

def create_or_update_terminal(terminal_data):
    """
    创建或更新终端设备
    
    Args:
        terminal_data: 包含终端数据的字典
    
    Returns:
        创建或更新的终端对象
    """
    mac_address = terminal_data.get("mac_address")
    ip_address = terminal_data.get("ip_address")
    
    # 必须有MAC地址或IP地址
    if not mac_address and not ip_address:
        current_app.logger.warning("无法创建或更新终端：缺少MAC地址和IP地址")
        return None
    
    # 尝试通过MAC地址或IP地址查找现有终端
    query = Terminal.query
    conditions = []
    
    if mac_address:
        conditions.append(Terminal.mac_address == mac_address)
    
    if ip_address:
        conditions.append(Terminal.ip_address == ip_address)
    
    terminal = query.filter(or_(*conditions)).first()
    
    # 如果终端不存在则创建新的
    if not terminal:
        terminal = Terminal()
        terminal.created_at = datetime.now()
        current_app.logger.info(f"创建新终端: {mac_address or ip_address}")
    else:
        current_app.logger.info(f"更新现有终端: {terminal.id} - {terminal.mac_address}")
    
    # 更新终端信息
    terminal = update_terminal_info(terminal, terminal_data)
    
    # 保存到数据库
    try:
        db.session.add(terminal)
        db.session.commit()
        current_app.logger.info(f"终端保存成功: ID {terminal.id}")
        return terminal
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"保存终端失败: {str(e)}")
        return None

def update_terminal_info(terminal, terminal_data):
    """
    更新终端设备信息
    
    Args:
        terminal: 终端对象
        terminal_data: 包含终端数据的字典
    
    Returns:
        更新后的终端对象
    """
    # 更新基本信息
    if "mac_address" in terminal_data and terminal_data["mac_address"]:
        terminal.mac_address = terminal_data["mac_address"]
    
    if "ip_address" in terminal_data and terminal_data["ip_address"]:
        terminal.ip_address = terminal_data["ip_address"]
    
    if "hostname" in terminal_data and terminal_data["hostname"]:
        terminal.hostname = terminal_data["hostname"]
    
    if "connected_device_id" in terminal_data and terminal_data["connected_device_id"]:
        terminal.connected_device_id = terminal_data["connected_device_id"]
    
    if "port_number" in terminal_data and terminal_data["port_number"]:
        terminal.port_number = terminal_data["port_number"]
    
    if "vlan_id" in terminal_data and terminal_data["vlan_id"]:
        terminal.vlan_id = terminal_data["vlan_id"]
    
    if "connection_type" in terminal_data and terminal_data["connection_type"]:
        terminal.connection_type = terminal_data["connection_type"]
    
    if "location" in terminal_data and terminal_data["location"]:
        terminal.location = terminal_data["location"]
    
    # 保存用户代理字符串
    if "user_agent" in terminal_data and terminal_data["user_agent"]:
        terminal.user_agent = terminal_data["user_agent"]
    
    # 使用其他数据识别设备类型和操作系统
    identified_info = identify_terminal(terminal_data)
    
    # 如果未设置设备类型或设备类型为Unknown，则更新
    if not terminal.device_type or terminal.device_type == "Unknown":
        terminal.device_type = identified_info["device_type"]
    
    # 如果未设置操作系统类型或操作系统类型为Unknown，则更新
    if not terminal.os_type or terminal.os_type == "Unknown":
        terminal.os_type = identified_info["os_type"]
    
    # 更新供应商信息
    if identified_info["vendor"] and (not terminal.vendor or terminal.vendor == "Unknown"):
        terminal.vendor = identified_info["vendor"]
    
    # 标记为活跃并更新最后活跃时间
    terminal.is_active = True
    terminal.last_seen = datetime.now()
    terminal.updated_at = datetime.now()
    
    return terminal

def mark_inactive_terminals():
    """将超过规定时间未活跃的终端设备标记为不活跃"""
    # 设置不活跃时间阈值（24小时）
    inactive_threshold = datetime.now() - timedelta(hours=24)
    
    # 查找并更新不活跃终端
    inactive_terminals = Terminal.query.filter(
        Terminal.is_active == True,
        Terminal.last_seen < inactive_threshold
    ).all()
    
    if inactive_terminals:
        for terminal in inactive_terminals:
            terminal.is_active = False
            terminal.updated_at = datetime.now()
        
        try:
            db.session.commit()
            current_app.logger.info(f"已将 {len(inactive_terminals)} 个终端设备标记为不活跃")
            return len(inactive_terminals)
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"标记不活跃终端失败: {str(e)}")
            return 0
    
    return 0

def discover_terminals_for_device(device):
    """
    为指定网络设备发现连接的终端设备
    
    Args:
        device: 网络设备对象
    
    Returns:
        发现的终端设备数量
    """
    discovered_count = 0
    
    try:
        # 这里假设有一个SNMP或其他方法来获取设备的MAC地址表
        # 实际实现中需要根据设备类型和协议进行适当的数据收集
        mac_table = get_device_mac_table(device)
        
        for entry in mac_table:
            mac_address = entry.get("mac_address")
            port = entry.get("port")
            vlan = entry.get("vlan")
            ip_address = entry.get("ip_address")  # 可能需要通过ARP表获取
            
            if mac_address:
                terminal_data = {
                    "mac_address": mac_address,
                    "ip_address": ip_address,
                    "connected_device_id": device.id,
                    "port_number": port,
                    "vlan_id": vlan,
                    "connection_type": "wired"  # 假设所有都是有线连接
                }
                
                terminal = create_or_update_terminal(terminal_data)
                if terminal:
                    discovered_count += 1
        
        current_app.logger.info(f"设备 {device.name} 发现了 {discovered_count} 个终端")
        return discovered_count
    except Exception as e:
        current_app.logger.error(f"从设备 {device.name} 发现终端失败: {str(e)}")
        return 0

def get_device_mac_table(device):
    """
    获取网络设备的MAC地址表
    
    Args:
        device: 网络设备对象
    
    Returns:
        MAC地址表条目列表
    """
    try:
        # 针对不同设备类型使用不同的获取方法
        if device.device_type.lower() in ['pc', 'server', 'host', 'computer']:
            return get_pc_mac_table(device)
        else:
            # 网络设备使用SNMP获取MAC表
            return get_network_device_mac_table(device)
    except Exception as e:
        current_app.logger.error(f"获取设备{device.name}的MAC地址表失败: {str(e)}")
        return []

def get_pc_mac_table(device):
    """获取PC设备的MAC地址表"""
    mac_table = []
    
    try:
        # 对于PC设备，使用SNMP获取ARP表
        import subprocess
        import re
        
        # 先尝试通过SNMP获取ARP表
        if check_device_status(device):
            # 使用SNMP尝试获取ARP表
            arp_table_oid = '1.3.6.1.2.1.4.22.1.2'  # IP-MIB::ipNetToMediaPhysAddress
            arp_entries = snmp_walk(
                device.ip_address,
                arp_table_oid,
                port=device.snmp_port or 161,
                community=device.snmp_community or 'public',
                version=device.snmp_version or '2c'
            )
            
            if arp_entries:
                for oid, mac_value in arp_entries.items():
                    # 尝试从OID中提取IP地址
                    ip_parts = oid.split('.')[-4:]
                    if len(ip_parts) == 4:
                        ip_address = '.'.join(ip_parts)
                        # 将MAC值转换为标准格式
                        mac_hex = ':'.join([f'{x:02x}' for x in bytes(mac_value)])
                        
                        mac_table.append({
                            "mac_address": mac_hex,
                            "ip_address": ip_address,
                            "port": "eth0",  # 假设端口
                            "vlan": 1        # 假设VLAN
                        })
        
        # 如果设备是本地PC，可以直接使用系统命令获取
        if device.ip_address in ['127.0.0.1', 'localhost'] or is_local_device(device.ip_address):
            import platform
            if platform.system() == 'Windows':
                # Windows系统，使用arp -a命令
                result = subprocess.run(['arp', '-a'], capture_output=True, text=True)
                for line in result.stdout.splitlines():
                    match = re.search(r'(\d+\.\d+\.\d+\.\d+)\s+([0-9a-f-]+)', line, re.IGNORECASE)
                    if match:
                        ip = match.group(1)
                        mac = match.group(2).replace('-', ':')
                        mac_table.append({
                            "mac_address": mac,
                            "ip_address": ip,
                            "port": "LAN",
                            "vlan": 1
                        })
            elif platform.system() == 'Linux':
                # Linux系统，使用ip neigh命令
                result = subprocess.run(['ip', 'neigh'], capture_output=True, text=True)
                for line in result.stdout.splitlines():
                    parts = line.split()
                    if len(parts) >= 5 and parts[2] == 'lladdr':
                        ip = parts[0]
                        mac = parts[3]
                        mac_table.append({
                            "mac_address": mac,
                            "ip_address": ip,
                            "port": parts[1],
                            "vlan": 1
                        })
    except Exception as e:
        current_app.logger.error(f"获取PC设备MAC表失败: {str(e)}")
    
    # 删除模拟数据生成代码，只返回真实发现的终端
    return mac_table

def get_network_device_mac_table(device):
    """获取网络设备的MAC地址表(使用SNMP)"""
    mac_table = []
    
    try:
        # 思科设备MAC地址表OID
        cisco_mac_table_oid = '1.3.6.1.2.1.17.4.3.1.1'  # dot1dTpFdbAddress
        
        # 通过SNMP读取MAC地址表
        mac_entries = snmp_walk(
            device.ip_address,
            cisco_mac_table_oid,
            port=device.snmp_port or 161,
            community=device.snmp_community or 'public',
            version=device.snmp_version or '2c'
        )
        
        if mac_entries:
            # 获取端口映射
            port_oid = '1.3.6.1.2.1.17.4.3.1.2'  # dot1dTpFdbPort
            port_entries = snmp_walk(
                device.ip_address,
                port_oid,
                port=device.snmp_port or 161,
                community=device.snmp_community or 'public',
                version=device.snmp_version or '2c'
            )
            
            # 获取端口名称映射
            port_name_oid = '1.3.6.1.2.1.31.1.1.1.1'  # ifName
            port_names = snmp_walk(
                device.ip_address,
                port_name_oid,
                port=device.snmp_port or 161,
                community=device.snmp_community or 'public',
                version=device.snmp_version or '2c'
            )
            
            # 处理MAC地址表
            for oid, mac_value in mac_entries.items():
                # 从OID提取索引
                index = oid.split('.')[-1]
                
                # 获取端口
                port_oid_key = f"{port_oid}.{index}"
                port_index = port_entries.get(port_oid_key, None)
                
                # 获取端口名称
                port_name = "unknown"
                if port_index:
                    port_name_key = f"{port_name_oid}.{port_index}"
                    port_name = port_names.get(port_name_key, f"Port{port_index}")
                
                # 将MAC值转换为标准格式
                mac_hex = ':'.join([f'{x:02x}' for x in bytes(mac_value)])
                
                mac_table.append({
                    "mac_address": mac_hex,
                    "port": port_name,
                    "vlan": 1  # 默认VLAN
                })
        
        # 如果无法获取MAC表，尝试获取ARP表
        if not mac_table:
            arp_table_oid = '1.3.6.1.2.1.4.22.1.2'  # ipNetToMediaPhysAddress
            arp_entries = snmp_walk(
                device.ip_address,
                arp_table_oid,
                port=device.snmp_port or 161,
                community=device.snmp_community or 'public',
                version=device.snmp_version or '2c'
            )
            
            if arp_entries:
                for oid, mac_value in arp_entries.items():
                    # 从OID提取IP
                    ip_parts = oid.split('.')[-4:]
                    if len(ip_parts) == 4:
                        ip_address = '.'.join(ip_parts)
                        
                        # 将MAC值转换为标准格式
                        mac_hex = ':'.join([f'{x:02x}' for x in bytes(mac_value)])
                        
                        mac_table.append({
                            "mac_address": mac_hex,
                            "ip_address": ip_address,
                            "port": "unknown",
                            "vlan": 1
                        })
    except Exception as e:
        current_app.logger.error(f"通过SNMP获取MAC表失败: {str(e)}")
    
    return mac_table

def is_local_device(ip):
    """检查IP是否是本地设备"""
    import socket
    try:
        hostname = socket.gethostname()
        local_ips = socket.gethostbyname_ex(hostname)[2]
        return ip in local_ips or ip in ['127.0.0.1', 'localhost']
    except:
        return False

def schedule_terminal_discovery():
    """
    调度全网终端设备发现任务
    
    Returns:
        执行结果统计
    """
    current_app.logger.info("开始全网终端设备发现")
    
    # 初始化OUI数据库
    init_oui_database()
    
    # 标记不活跃终端
    offline_count = mark_inactive_terminals()
    
    # 获取所有活跃的网络设备
    devices = Device.query.filter_by(status="active").all()
    
    total_discovered = 0
    for device in devices:
        discovered = discover_terminals_for_device(device)
        total_discovered += discovered
    
    current_app.logger.info(f"终端设备发现完成，共发现 {total_discovered} 个终端")
    
    return {
        "discovered": total_discovered,
        "offline": offline_count
    } 