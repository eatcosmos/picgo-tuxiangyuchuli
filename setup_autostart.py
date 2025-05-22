#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import platform
import shutil
import winreg
import argparse

def get_script_path():
    """获取当前脚本的绝对路径"""
    return os.path.dirname(os.path.abspath(__file__))

def setup_windows_autostart(enable=True):
    """设置Windows开机自启动"""
    # 获取启动脚本的完整路径
    script_dir = get_script_path()
    bat_path = os.path.join(script_dir, 'start_playwright_service.bat')
    
    if not os.path.exists(bat_path):
        print(f"错误: 启动脚本不存在: {bat_path}")
        return False
    
    # 获取当前用户的启动文件夹路径
    startup_folder = os.path.join(os.environ['APPDATA'], 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup')
    shortcut_path = os.path.join(startup_folder, 'Playwright Chrome Service.lnk')
    
    if enable:
        # 创建快捷方式
        try:
            import win32com.client
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(shortcut_path)
            shortcut.TargetPath = bat_path
            shortcut.WorkingDirectory = script_dir
            shortcut.WindowStyle = 7  # 7 = 最小化
            shortcut.Description = "启动Playwright Chrome服务"
            shortcut.Save()
            print(f"已成功添加到开机自启动: {shortcut_path}")
            return True
        except Exception as e:
            print(f"创建快捷方式失败: {e}")
            
            # 备选方案: 直接复制批处理文件到启动文件夹
            try:
                target_path = os.path.join(startup_folder, 'start_playwright_service.bat')
                shutil.copy2(bat_path, target_path)
                print(f"已使用备选方案添加到开机自启动: {target_path}")
                return True
            except Exception as e2:
                print(f"备选方案也失败了: {e2}")
                return False
    else:
        # 移除快捷方式
        try:
            if os.path.exists(shortcut_path):
                os.remove(shortcut_path)
                print(f"已从开机自启动中移除: {shortcut_path}")
            
            # 同时检查备选方案创建的文件
            alt_path = os.path.join(startup_folder, 'start_playwright_service.bat')
            if os.path.exists(alt_path):
                os.remove(alt_path)
                print(f"已从开机自启动中移除备选文件: {alt_path}")
            
            return True
        except Exception as e:
            print(f"移除自启动项失败: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description="Playwright Chrome服务自启动设置工具")
    parser.add_argument('action', choices=['enable', 'disable'],
                       help='要执行的操作: enable(启用自启动), disable(禁用自启动)')
    
    args = parser.parse_args()
    
    system = platform.system()
    
    if system != 'Windows':
        print(f"不支持的操作系统: {system}，目前仅支持Windows")
        return
    
    if args.action == 'enable':
        print("设置Playwright Chrome服务开机自启动...")
        setup_windows_autostart(True)
    elif args.action == 'disable':
        print("禁用Playwright Chrome服务开机自启动...")
        setup_windows_autostart(False)

if __name__ == "__main__":
    main() 