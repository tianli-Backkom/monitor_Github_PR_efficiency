#!/usr/bin/env python3
"""
修复PR数据文件中的执行时长数据
"""

import json
import os
import sys
from datetime import datetime

# 配置
DATA_DIR = "pr_data"

def fix_duration_data():
    """修复PR数据文件中的执行时长数据"""
    # 获取最新的数据文件
    json_files = [f for f in os.listdir(DATA_DIR) if f.endswith(".json") and f.startswith("pr_data_")]
    if not json_files:
        print("错误: 没有找到PR数据文件", file=sys.stderr)
        sys.exit(1)
    
    # 按文件名排序，获取最新的文件
    json_files.sort(reverse=True)
    latest_file = json_files[0]
    file_path = os.path.join(DATA_DIR, latest_file)
    
    print(f"修复文件: {file_path}")
    
    # 加载数据
    with open(file_path, "r", encoding="utf-8") as f:
        pr_data = json.load(f)
    
    print(f"原始数据: {len(pr_data)} 个PR")
    
    # 修复执行时长数据
    fixed_pr_data = []
    fixed_count = 0
    
    for pr in pr_data:
        # 复制PR数据
        fixed_pr = pr.copy()
        
        # 修复PR Test (NPU)执行时长（超过2小时的设为None）
        pr_test_duration = pr.get("pr_test_npu_duration")
        if pr_test_duration is not None:
            print(f"PR #{pr['pr_number']}: PR Test duration = {pr_test_duration} 秒")
            if pr_test_duration > 7200:  # 7200秒 = 2小时
                fixed_pr["pr_test_npu_duration"] = None
                fixed_count += 1
        
        # 修复Lint执行时长（超过30分钟的设为None）
        lint_duration = pr.get("lint_duration")
        if lint_duration is not None:
            print(f"PR #{pr['pr_number']}: Lint duration = {lint_duration} 秒")
            if lint_duration > 1800:  # 1800秒 = 30分钟
                fixed_pr["lint_duration"] = None
                fixed_count += 1
        
        fixed_pr_data.append(fixed_pr)
    
    print(f"修复了 {fixed_count} 个执行时长数据")
    
    # 保存修复后的数据
    today = datetime.now().strftime("%Y%m%d")
    fixed_file_path = os.path.join(DATA_DIR, f"pr_data_{today}_fixed.json")
    
    with open(fixed_file_path, "w", encoding="utf-8") as f:
        json.dump(fixed_pr_data, f, indent=2, ensure_ascii=False)
    
    print(f"修复后的数据已保存到: {fixed_file_path}")
    print(f"修复了 {len(pr_data) - len(fixed_pr_data)} 个PR的执行时长数据")
    
    return fixed_file_path

if __name__ == "__main__":
    fix_duration_data()
