#!/usr/bin/env python3
"""
检查PR数据文件中是否包含workflow执行时长数据
"""

import os
import json

def check_pr_data():
    """检查PR数据文件"""
    # 数据目录
    data_dir = "pr_data"
    
    # 获取数据目录下的所有JSON文件
    json_files = [f for f in os.listdir(data_dir) if f.endswith(".json") and f.startswith("pr_data_")]
    if not json_files:
        print("错误: 数据目录中没有找到PR数据文件")
        return
    
    # 按文件名排序，获取最新的文件
    json_files.sort(reverse=True)
    latest_file = json_files[0]
    file_path = os.path.join(data_dir, latest_file)
    
    print(f"检查文件: {file_path}")
    
    # 加载数据
    with open(file_path, "r", encoding="utf-8") as f:
        pr_data = json.load(f)
    
    # 检查是否有PR数据
    if not pr_data:
        print("错误: 数据文件为空")
        return
    
    # 检查第一个PR数据
    first_pr = pr_data[0]
    print(f"\n第一个PR的数据结构:")
    print(f"PR编号: {first_pr.get('pr_number')}")
    print(f"标题: {first_pr.get('title')}")
    
    # 检查是否包含workflow执行时长数据
    if 'head_sha' in first_pr:
        print(f"包含head_sha: {first_pr['head_sha']}")
    else:
        print("不包含head_sha")
    
    if 'lint_duration' in first_pr:
        print(f"包含lint_duration: {first_pr['lint_duration']}")
    else:
        print("不包含lint_duration")
    
    if 'pr_test_npu_duration' in first_pr:
        print(f"包含pr_test_npu_duration: {first_pr['pr_test_npu_duration']}")
    else:
        print("不包含pr_test_npu_duration")
    
    # 统计包含执行时长数据的PR数量
    total_prs = len(pr_data)
    prs_with_lint = sum(1 for pr in pr_data if 'lint_duration' in pr and pr['lint_duration'] is not None)
    prs_with_pr_test = sum(1 for pr in pr_data if 'pr_test_npu_duration' in pr and pr['pr_test_npu_duration'] is not None)
    
    print(f"\n统计信息:")
    print(f"总PR数: {total_prs}")
    print(f"包含lint_duration的PR数: {prs_with_lint}")
    print(f"包含pr_test_npu_duration的PR数: {prs_with_pr_test}")

if __name__ == "__main__":
    check_pr_data()