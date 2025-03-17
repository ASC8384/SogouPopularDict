#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import logging
import subprocess

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('run_all')

def run_script(script_path, args=None):
    """运行指定的Python脚本"""
    cmd = [sys.executable, script_path]
    if args:
        cmd.extend(args)
    
    logger.info(f"运行脚本: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info(f"脚本输出: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"脚本运行失败: {e}")
        logger.error(f"错误输出: {e.stderr}")
        return False

def main():
    """主函数"""
    # 获取脚本目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 下载并转换词库
    download_script = os.path.join(script_dir, 'download_and_convert.py')
    if not run_script(download_script):
        logger.error("下载词库失败，退出")
        return False
    
    # 转换为Rime格式
    convert_script = os.path.join(script_dir, 'convert_to_rime.py')
    if not run_script(convert_script):
        logger.error("转换为Rime格式失败，退出")
        return False
    
    logger.info("所有任务完成")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 