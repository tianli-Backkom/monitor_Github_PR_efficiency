#!/usr/bin/env python3
"""
检查PR执行时长数据，找出异常值
"""

import json

# 加载PR数据
with open('pr_data/pr_data_20260104.json', 'r', encoding='utf-8') as f:
    pr_data = json.load(f)

print("异常的PR Test (NPU)执行时长数据：")
print("-" * 60)

# 找出异常值
for pr in pr_data:
    duration = pr.get('pr_test_npu_duration')
    if duration and duration > 10000:  # 超过10000秒（约2.7小时）视为异常
        minutes = duration / 60
        print(f"PR #{pr['pr_number']}:")
        print(f"  标题: {pr['title']}")
        print(f"  创建时间: {pr['created_at']}")
        print(f"  执行时长: {duration:.2f} 秒 = {minutes:.2f} 分钟")
        print(f"  Head SHA: {pr['head_sha']}")
        print(f"  PR链接: {pr['html_url']}")
        print()

print("异常的Lint执行时长数据：")
print("-" * 60)

for pr in pr_data:
    duration = pr.get('lint_duration')
    if duration and duration > 1000:  # 超过1000秒（约16分钟）视为异常
        minutes = duration / 60
        print(f"PR #{pr['pr_number']}:")
        print(f"  标题: {pr['title']}")
        print(f"  创建时间: {pr['created_at']}")
        print(f"  执行时长: {duration:.2f} 秒 = {minutes:.2f} 分钟")
        print(f"  Head SHA: {pr['head_sha']}")
        print(f"  PR链接: {pr['html_url']}")
        print()
