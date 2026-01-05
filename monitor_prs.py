#!/usr/bin/env python3
"""
PR监控脚本

功能：每天查询最近两周PR数据，并将数据保存到本地
"""

import os
import sys
import json
import time
from datetime import datetime, timedelta
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 配置常量
BASE_URL = "https://api.github.com"
API_VERSION = "2022-11-28"
OWNER = "sgl-project"
REPO = "sglang"
TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
RETRY_COUNT = 3
RETRY_DELAY = 5  # 秒
RATE_LIMIT_DELAY = 60  # 秒
DATA_DIR = "pr_data"  # 数据保存目录


def get_github_token():
    """从环境变量获取GitHub Personal Access Token"""
    token = os.environ.get("GH_TOKEN")
    if not token:
        print("错误: 未找到环境变量 GH_TOKEN", file=sys.stderr)
        sys.exit(1)
    return token


def create_session():
    """创建带重试机制的HTTP会话"""
    session = requests.Session()
    retry = Retry(
        total=RETRY_COUNT,
        read=RETRY_COUNT,
        connect=RETRY_COUNT,
        backoff_factor=RETRY_DELAY,
        status_forcelist=[500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def calculate_time_range():
    """计算近两周的时间范围"""
    now = datetime.utcnow()
    two_weeks_ago = now - timedelta(days=14)
    return {
        "since": two_weeks_ago.strftime(TIME_FORMAT),
        "until": now.strftime(TIME_FORMAT)
    }


def get_pr_list(session, headers, time_range):
    """获取符合时间范围的PR列表"""
    pr_list = []
    page = 1
    per_page = 100  # 每页最大100条
    
    while True:
        url = f"{BASE_URL}/repos/{OWNER}/{REPO}/pulls"
        params = {
            "state": "all",
            "sort": "created",
            "direction": "desc",
            "per_page": per_page,
            "page": page,
            "labels": "npu"  # 只获取带有npu label的PR
        }
        
        response = session.get(url, headers=headers, params=params)
        
        # 处理速率限制
        if response.status_code == 403 and "rate limit" in response.text.lower():
            reset_time = int(response.headers.get("X-RateLimit-Reset", 0))
            wait_time = max(reset_time - int(time.time()), RATE_LIMIT_DELAY)
            print(f"速率限制已达，将等待 {wait_time} 秒后重试...")
            time.sleep(wait_time)
            continue
        
        response.raise_for_status()  # 抛出其他HTTP错误
        
        prs = response.json()
        if not prs:
            break
        
        # 筛选近两周内创建的PR
        for pr in prs:
            created_at = datetime.strptime(pr["created_at"], TIME_FORMAT)
            since = datetime.strptime(time_range["since"], TIME_FORMAT)
            until = datetime.strptime(time_range["until"], TIME_FORMAT)
            
            if since <= created_at <= until:
                pr_list.append(pr)  # 直接保存完整的PR对象，而不仅仅是PR编号
            elif created_at < since:
                # 因为按创建时间降序排序，所以后续PR都会更早，直接退出循环
                break
        
        if created_at < since:
            break
        
        page += 1
        time.sleep(0.5)  # 避免请求过快
    
    return pr_list


def get_pr_detail(session, headers, pr):
    """获取单个PR的详细信息（仅当需要时调用）"""
    # 注意：GitHub PR列表接口默认不返回代码变更信息（additions/deletions/changed_files）
    # 这些字段只在详情接口中返回，所以几乎所有PR都需要调用详情接口
    url = f"{BASE_URL}/repos/{OWNER}/{REPO}/pulls/{pr['number']}"
    response = session.get(url, headers=headers)
    
    # 处理速率限制
    if response.status_code == 403 and "rate limit" in response.text.lower():
        reset_time = int(response.headers.get("X-RateLimit-Reset", 0))
        wait_time = max(reset_time - int(time.time()), RATE_LIMIT_DELAY)
        print(f"速率限制已达，将等待 {wait_time} 秒后重试...")
        time.sleep(wait_time)
        return get_pr_detail(session, headers, pr)  # 递归重试
    
    response.raise_for_status()
    return response.json()


def get_pr_details_batch(session, headers, pr_list, batch_size=10):
    """批量获取PR详情，提高效率"""
    pr_details = []
    detail_api_calls = 0
    total_prs = len(pr_list)
    
    for i, pr in enumerate(pr_list, 1):
        try:
            # 进度显示，每处理10个PR更新一次
            if i % 10 == 0 or i == total_prs:
                print(f"处理进度: {i}/{total_prs} ({i/total_prs:.1%})...")
            
            # 检查PR是否带有npu标签
            pr_has_npu_label = False
            if 'labels' in pr:
                for label in pr['labels']:
                    if label.get('name') == 'npu':
                        pr_has_npu_label = True
                        break
            
            if not pr_has_npu_label:
                print(f"跳过PR #{pr['number']}：不带有npu标签")
                continue
            
            # 获取PR详情
            pr_detail = get_pr_detail(session, headers, pr)
            
            # 再次检查PR详情中是否带有npu标签（确保准确性）
            pr_detail_has_npu_label = False
            if 'labels' in pr_detail:
                for label in pr_detail['labels']:
                    if label.get('name') == 'npu':
                        pr_detail_has_npu_label = True
                        break
            
            if not pr_detail_has_npu_label:
                print(f"跳过PR #{pr['number']}：详情中不带有npu标签")
                continue
            
            formatted_data = format_pr_data(pr_detail)
            
            # 获取workflow执行时长数据
            try:
                head_sha = formatted_data["head_sha"]
                workflow_runs = get_workflow_runs(session, headers, head_sha)
                duration_data = parse_workflow_duration(workflow_runs)
                
                # 将执行时长数据添加到PR数据中
                formatted_data.update(duration_data)
            except Exception as e:
                print(f"获取PR #{pr['number']}的workflow执行时长时发生错误: {e}")
                # 添加默认值
                formatted_data["lint_duration"] = None
                formatted_data["pr_test_npu_duration"] = None
            
            pr_details.append(formatted_data)
            detail_api_calls += 1
            
            # 减少延迟时间
            time.sleep(0.1)
            
        except KeyboardInterrupt:
            print(f"\n用户中断操作，已处理 {i} 个PR")
            return pr_details, detail_api_calls, True
        except Exception as e:
            print(f"\n处理PR #{pr['number']} 时发生错误: {e}")
            continue
    
    return pr_details, detail_api_calls, False


def format_pr_data(pr_detail):
    """格式化PR数据"""
    return {
        "pr_number": pr_detail["number"],
        "title": pr_detail["title"],
        "status": pr_detail["state"],
        "created_at": pr_detail["created_at"],
        "creator": pr_detail["user"]["login"],
        "merged": pr_detail["merged"],
        "merged_at": pr_detail["merged_at"],
        "closed_at": pr_detail["closed_at"],
        "additions": pr_detail.get("additions", 0),  # 使用get方法，避免字段不存在时出错
        "deletions": pr_detail.get("deletions", 0),
        "changed_files": pr_detail.get("changed_files", 0),
        "comments_count": pr_detail["comments"],
        "review_comments_count": pr_detail["review_comments"],
        "html_url": pr_detail["html_url"],
        "head_sha": pr_detail["head"]["sha"]  # 保存PR最新提交的SHA值，用于后续查询workflow
    }


def get_workflow_runs(session, headers, head_sha):
    """获取指定head.sha的workflow执行详情"""
    url = f"{BASE_URL}/repos/{OWNER}/{REPO}/actions/runs"
    params = {
        "head_sha": head_sha,
        "per_page": 100  # 每页最大100条
    }
    
    response = session.get(url, headers=headers, params=params)
    
    # 处理速率限制
    if response.status_code == 403 and "rate limit" in response.text.lower():
        reset_time = int(response.headers.get("X-RateLimit-Reset", 0))
        wait_time = max(reset_time - int(time.time()), RATE_LIMIT_DELAY)
        print(f"速率限制已达，将等待 {wait_time} 秒后重试...")
        time.sleep(wait_time)
        return get_workflow_runs(session, headers, head_sha)  # 递归重试
    
    response.raise_for_status()
    return response.json()['workflow_runs']


def parse_workflow_duration(workflow_runs):
    """解析workflow执行时长，返回指定workflow的执行时长（秒）"""
    duration_data = {
        "lint_duration": None,
        "pr_test_npu_duration": None
    }
    
    for run in workflow_runs:
        workflow_name = run.get("name", "")
        status = run.get("status", "")
        conclusion = run.get("conclusion", "")
        
        # 只处理已完成的workflow
        if status != "completed":
            continue
        
        try:
            # 使用GitHub API提供的run_duration_ms字段（以毫秒为单位）
            if "run_duration_ms" in run and run["run_duration_ms"] is not None:
                # 转换为秒
                duration = run["run_duration_ms"] / 1000
            else:
                # 兼容旧API，使用created_at和updated_at计算（备用方案）
                created_at = datetime.strptime(run["created_at"], TIME_FORMAT)
                updated_at = datetime.strptime(run["updated_at"], TIME_FORMAT)
                duration = (updated_at - created_at).total_seconds()
                
                # 如果计算出的时长超过10小时，可能是错误数据，跳过
                if duration > 36000:  # 36000秒 = 10小时
                    continue
            
            if workflow_name == "Lint":
                duration_data["lint_duration"] = duration
            elif workflow_name == "PR Test (NPU)":
                duration_data["pr_test_npu_duration"] = duration
        except (KeyError, ValueError) as e:
            print(f"解析workflow执行时长时发生错误: {e}")
            continue
    
    return duration_data


def save_pr_data(pr_data):
    """保存PR数据到本地文件"""
    # 创建数据目录
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    
    # 生成文件名（格式：pr_data_20251231.json）
    today = datetime.now().strftime("%Y%m%d")
    file_path = os.path.join(DATA_DIR, f"pr_data_{today}_fixed.json")
    
    # 保存数据
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(pr_data, f, indent=2, ensure_ascii=False)
    
    print(f"PR数据已保存到 {file_path}")
    return file_path


def run_daily():
    """每天运行一次的主函数"""
    # 获取GitHub Token
    token = get_github_token()
    
    # 创建会话和请求头
    session = create_session()
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": API_VERSION
    }
    
    # 计算时间范围
    time_range = calculate_time_range()
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 将获取 {time_range['since']} 至 {time_range['until']} 期间创建的PR")
    
    try:
        # 获取PR列表
        print("正在获取PR列表...")
        pr_list = get_pr_list(session, headers, time_range)
        print(f"共找到 {len(pr_list)} 个符合条件的PR")
        
        # 批量获取PR详情
        print("正在批量获取PR详情...")
        pr_details, detail_api_calls, interrupted = get_pr_details_batch(session, headers, pr_list)
        
        if pr_details:
            # 保存数据
            save_pr_data(pr_details)
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 数据获取完成")
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 共调用详情接口 {detail_api_calls} 次")
        
        if interrupted:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 用户中断操作，已处理 {len(pr_details)} 个PR")
        
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 发生错误: {e}", file=sys.stderr)
        return False
    
    return True


def main():
    """主函数"""
    # 命令行参数解析（简化，不再需要--once参数）
    import argparse
    parser = argparse.ArgumentParser(description="PR监控脚本")
    args = parser.parse_args()
    
    # 只运行一次监控任务
    run_daily()


if __name__ == "__main__":
    main()
