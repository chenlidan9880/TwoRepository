"""
终端识别功能测试脚本
"""

from app import app, db
from app.utils.terminal_identifier import identify_terminal, parse_user_agent, lookup_mac_vendor

def test_identify_with_user_agent():
    """测试通过用户代理字符串识别设备"""
    with app.app_context():
        # 测试iPhone用户代理
        ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"
        terminal_data = {"user_agent": ua}
        result = identify_terminal(terminal_data)
        
        print("\n测试iPhone用户代理识别:")
        print(f"设备类型: {result['device_type']}")
        print(f"操作系统: {result['os_type']}")
        print(f"浏览器: {result['browser']}")
        
        # 测试Windows用户代理
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        terminal_data = {"user_agent": ua}
        result = identify_terminal(terminal_data)
        
        print("\n测试Windows用户代理识别:")
        print(f"设备类型: {result['device_type']}")
        print(f"操作系统: {result['os_type']}")
        print(f"浏览器: {result['browser']}")

def test_identify_with_mac():
    """测试通过MAC地址识别设备"""
    with app.app_context():
        # 测试Apple MAC地址
        mac = "00:0D:93:12:34:56"
        terminal_data = {"mac_address": mac}
        result = identify_terminal(terminal_data)
        
        print("\n测试Apple MAC地址识别:")
        print(f"设备类型: {result['device_type']}")
        print(f"厂商: {result['vendor']}")

if __name__ == "__main__":
    print("开始测试终端识别功能...")
    test_identify_with_user_agent()
    test_identify_with_mac()
    print("\n测试完成!") 