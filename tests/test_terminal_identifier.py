"""
终端识别器测试脚本
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# 将项目根目录添加到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.utils.terminal_identifier import (
    init_oui_database, lookup_mac_vendor, parse_user_agent, 
    identify_terminal, update_terminal_info
)

class TestTerminalIdentifier(unittest.TestCase):
    """终端识别器测试类"""
    
    def setUp(self):
        """测试前准备"""
        # 确保测试目录存在
        os.makedirs('app/utils/data', exist_ok=True)
        
        # 创建测试OUI数据
        with open('app/utils/data/oui_test.csv', 'w') as f:
            f.write("mac_prefix,vendor\n")
            f.write("000D93,Apple, Inc.\n")
            f.write("001121,Cisco Systems, Inc.\n")
            f.write("74D02B,ASUSTek COMPUTER INC.\n")
    
    @patch('app.utils.terminal_identifier.OUI_DB_PATH', 'app/utils/data/oui_test.csv')
    def test_oui_database(self):
        """测试OUI数据库初始化和查询"""
        # 初始化OUI数据库
        init_oui_database()
        
        # 测试查找厂商
        vendor = lookup_mac_vendor("00:0D:93:12:34:56")
        self.assertEqual(vendor, "Apple, Inc.")
        
        # 测试不同格式的MAC地址
        vendor = lookup_mac_vendor("00-0D-93-12-34-56")
        self.assertEqual(vendor, "Apple, Inc.")
        
        # 测试小写MAC地址
        vendor = lookup_mac_vendor("00:0d:93:12:34:56")
        self.assertEqual(vendor, "Apple, Inc.")
        
        # 测试不存在的MAC前缀
        vendor = lookup_mac_vendor("00:FF:FF:12:34:56")
        self.assertIsNone(vendor)
    
    def test_parse_user_agent(self):
        """测试用户代理解析"""
        # 测试Windows Chrome
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        result = parse_user_agent(ua)
        self.assertEqual(result["os"], "Windows")
        self.assertEqual(result["browser"], "Chrome")
        self.assertTrue(result["is_pc"])
        
        # 测试iPhone Safari
        ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"
        result = parse_user_agent(ua)
        self.assertEqual(result["os"], "iOS")
        self.assertEqual(result["browser"], "Mobile Safari")
        self.assertTrue(result["is_mobile"])
        self.assertEqual(result["device_brand"], "Apple")
        
        # 测试Android Chrome
        ua = "Mozilla/5.0 (Linux; Android 10; SM-G970F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36"
        result = parse_user_agent(ua)
        self.assertEqual(result["os"], "Android")
        self.assertEqual(result["browser"], "Chrome Mobile")
        self.assertTrue(result["is_mobile"])
        
        # 测试空用户代理
        result = parse_user_agent("")
        self.assertIsNone(result["os"])
        self.assertIsNone(result["browser"])
    
    @patch('app.utils.terminal_identifier.lookup_mac_vendor')
    def test_identify_terminal(self, mock_lookup):
        """测试终端识别"""
        # 设置模拟返回值
        mock_lookup.return_value = "Apple, Inc."
        
        # 测试仅MAC地址识别
        terminal_data = {
            "mac_address": "00:0D:93:12:34:56"
        }
        result = identify_terminal(terminal_data)
        self.assertEqual(result["vendor"], "Apple, Inc.")
        self.assertEqual(result["device_type"], "Apple")
        
        # 测试主机名识别
        terminal_data = {
            "hostname": "iphone-user"
        }
        result = identify_terminal(terminal_data)
        self.assertEqual(result["device_type"], "Apple")
        
        # 测试用户代理识别
        terminal_data = {
            "user_agent": "Mozilla/5.0 (Linux; Android 10; SM-G970F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36"
        }
        result = identify_terminal(terminal_data)
        self.assertEqual(result["device_type"], "Mobile")
        self.assertEqual(result["os_type"], "Android")
        
        # 测试综合识别
        terminal_data = {
            "mac_address": "00:0D:93:12:34:56",
            "hostname": "macbook-pro",
            "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15"
        }
        result = identify_terminal(terminal_data)
        self.assertEqual(result["vendor"], "Apple, Inc.")
        self.assertEqual(result["device_type"], "Apple")
        self.assertEqual(result["os_type"], "Mac OS X")
        self.assertEqual(result["browser"], "Safari")

if __name__ == "__main__":
    unittest.main() 