#!/usr/bin/env python3
"""
PR效率报告生成脚本

功能：读取本地PR数据，解析PR效率关键指标，并生成HTML页面展示
"""

import os
import sys
import json
import argparse
from string import Template
from datetime import datetime, timedelta

# 配置常量
DATA_DIR = "pr_data"  # 数据目录
HTML_OUTPUT_FILE = "pr_efficiency_report.html"  # HTML输出文件


def load_latest_pr_data():
    """加载最新的PR数据"""
    # 获取数据目录下的所有JSON文件
    json_files = [f for f in os.listdir(DATA_DIR) if f.endswith(".json") and f.startswith("pr_data_")]
    if not json_files:
        print(f"错误: 数据目录 {DATA_DIR} 中没有找到PR数据文件", file=sys.stderr)
        sys.exit(1)
    
    # 优先使用带"_fixed"后缀的修复后文件
    fixed_files = [f for f in json_files if "_fixed" in f]
    if fixed_files:
        # 按文件名排序，获取最新的修复文件
        fixed_files.sort(reverse=True)
        latest_file = fixed_files[0]
    else:
        # 没有修复文件，使用普通文件
        json_files.sort(reverse=True)
        latest_file = json_files[0]
    
    file_path = os.path.join(DATA_DIR, latest_file)
    
    # 加载数据
    with open(file_path, "r", encoding="utf-8") as f:
        pr_data = json.load(f)
    
    print(f"已加载最新PR数据文件: {latest_file}，共 {len(pr_data)} 个PR")
    return pr_data


def calculate_pr_metrics(pr_data):
    """计算PR效率关键指标"""
    if not pr_data:
        return {}
    
    total_prs = len(pr_data)
    merged_prs = [pr for pr in pr_data if pr["merged"]]
    merged_count = len(merged_prs)
    closed_prs = [pr for pr in pr_data if pr["status"] == "closed"]
    closed_count = len(closed_prs)
    
    # 计算合并率
    merge_rate = round((merged_count / total_prs) * 100, 1) if total_prs > 0 else 0
    
    # 计算平均PR生命周期（从创建到合并/关闭的时间）
    lifecycle_days = []
    for pr in pr_data:
        if pr["status"] != "open":
            created_at = datetime.strptime(pr["created_at"], "%Y-%m-%dT%H:%M:%SZ")
            closed_or_merged_at = pr["merged_at"] or pr["closed_at"]
            if closed_or_merged_at:
                closed_or_merged_at = datetime.strptime(closed_or_merged_at, "%Y-%m-%dT%H:%M:%SZ")
                lifecycle = (closed_or_merged_at - created_at).total_seconds() / (24 * 3600)  # 转换为天
                lifecycle_days.append(lifecycle)
    
    avg_lifecycle = round(sum(lifecycle_days) / len(lifecycle_days), 1) if lifecycle_days else 0
    
    # 计算平均代码变更量
    total_additions = sum(pr["additions"] for pr in pr_data)
    total_deletions = sum(pr["deletions"] for pr in pr_data)
    total_changed_files = sum(pr["changed_files"] for pr in pr_data)
    
    avg_additions = round(total_additions / total_prs, 1) if total_prs > 0 else 0
    avg_deletions = round(total_deletions / total_prs, 1) if total_prs > 0 else 0
    avg_changed_files = round(total_changed_files / total_prs, 1) if total_prs > 0 else 0
    
    # 计算平均评论数
    total_comments = sum(pr["comments_count"] + pr["review_comments_count"] for pr in pr_data)
    avg_comments = round(total_comments / total_prs, 1) if total_prs > 0 else 0
    
    # 计算PR创建者分布
    creator_stats = {}
    for pr in pr_data:
        creator = pr["creator"]
        if creator in creator_stats:
            creator_stats[creator] += 1
        else:
            creator_stats[creator] = 1
    
    # 按日期的PR创建趋势
    date_stats = {}
    for pr in pr_data:
        created_date = pr["created_at"][:10]  # 提取日期部分（YYYY-MM-DD）
        if created_date in date_stats:
            date_stats[created_date] += 1
        else:
            date_stats[created_date] = 1
    
    # 转换为有序列表
    sorted_dates = sorted(date_stats.items())

    # 计算执行时长数据（按执行时间点记录，不按天平均）
    duration_data = []
    for pr in pr_data:
        # 提取完整的执行时间（包括时分秒）
        execution_time = pr["created_at"]
        
        # 创建执行时长数据条目
        duration_entry = {
            "time": execution_time,
            "lint": pr.get("lint_duration"),
            "pr_test_npu": pr.get("pr_test_npu_duration")
        }
        
        duration_data.append(duration_entry)
    
    # 按执行时间排序
    sorted_duration_data = sorted(duration_data, key=lambda x: x["time"])
    
    # 转换为用于图表的格式
    sorted_duration_dates = []
    for entry in sorted_duration_data:
        # 只保留有执行时长数据的条目
        if entry["lint"] is not None or entry["pr_test_npu"] is not None:
            # 提取日期时间作为标签
            date_time_label = entry["time"].replace("T", " ")[:-1]  # 格式：YYYY-MM-DD HH:MM:SS
            sorted_duration_dates.append((date_time_label, entry))
    
    return {
        "total_prs": total_prs,
        "merged_count": merged_count,
        "closed_count": closed_count,
        "merge_rate": merge_rate,
        "avg_lifecycle": avg_lifecycle,
        "avg_additions": avg_additions,
        "avg_deletions": avg_deletions,
        "avg_changed_files": avg_changed_files,
        "avg_comments": avg_comments,
        "creator_stats": dict(sorted(creator_stats.items(), key=lambda x: x[1], reverse=True)),
        "date_stats": sorted_dates,
        "duration_stats": sorted_duration_dates
    }


def generate_html_report(pr_data, metrics):
    """生成HTML报告"""
    # 生成PR表格行
    pr_table_rows = ""
    for pr in pr_data:
        # 格式化合并状态
        merged_status = "已合并" if pr["merged"] else "未合并"
        if pr["status"] == "open":
            merged_status = "Open"
        
        # 格式化代码变更
        code_changes = f"+{pr['additions']} / -{pr['deletions']} ({pr['changed_files']} files)"
        
        # 格式化评论数
        comments = f"{pr['comments_count']} + {pr['review_comments_count']}"
        
        pr_table_rows += f"""
        <tr>
            <td><a href="{pr['html_url']}" target="_blank">#{pr['pr_number']}</a></td>
            <td>{pr['title']}</td>
            <td>{pr['status']}</td>
            <td>{pr['creator']}</td>
            <td>{pr['created_at']}</td>
            <td>{merged_status}</td>
            <td>{code_changes}</td>
            <td>{comments}</td>
        </tr>
        """
    
    # 生成创建者分布
    creator_items = ""
    for creator, count in metrics["creator_stats"].items():
        creator_items += f"""
        <div class="creator-item">
            <span class="creator-name">{creator}</span>
            <span class="creator-count">{count}</span>
        </div>
        """

    # 准备提交与失败趋势图数据
    # 1. 计算按日期分组的提交PR数和失败PR数
    date_data = {}
    for pr in pr_data:
        created_date = pr["created_at"][:10]  # 提取日期部分（YYYY-MM-DD）
        
        if created_date not in date_data:
            date_data[created_date] = {
                "total": 0,
                "failed": 0
            }
        
        # 统计提交PR数
        date_data[created_date]["total"] += 1
        
        # 统计失败PR数（已关闭但未合并）
        if pr["status"] == "closed" and not pr["merged"]:
            date_data[created_date]["failed"] += 1
    
    # 2. 转换为有序列表
    sorted_dates = sorted(date_data.items())
    
    # 3. 提取日期、提交数和失败数
    chart_dates = [date for date, _ in sorted_dates]
    chart_total = [data["total"] for _, data in sorted_dates]
    chart_failed = [data["failed"] for _, data in sorted_dates]
    
    # 4. 转换为JSON格式
    chart_dates_json = json.dumps(chart_dates)
    chart_total_json = json.dumps(chart_total)
    chart_failed_json = json.dumps(chart_failed)
    
    # 准备执行时长趋势图数据
    # 1. 提取执行时间、lint时长和PR Test (NPU)时长
    lint_chart_dates = []
    lint_chart_duration = []
    pr_test_chart_dates = []
    pr_test_chart_duration = []
    
    for date_label, duration_data in metrics["duration_stats"]:
        # Lint执行时长数据
        if duration_data["lint"] is not None:
            lint_chart_dates.append(date_label)
            lint_chart_duration.append(duration_data["lint"])
        
        # PR Test (NPU)执行时长数据
        if duration_data["pr_test_npu"] is not None:
            pr_test_chart_dates.append(date_label)
            pr_test_chart_duration.append(duration_data["pr_test_npu"])
    
    # 2. 转换为JSON格式
    lint_chart_dates_json = json.dumps(lint_chart_dates)
    lint_chart_duration_json = json.dumps(lint_chart_duration)
    pr_test_chart_dates_json = json.dumps(pr_test_chart_dates)
    pr_test_chart_duration_json = json.dumps(pr_test_chart_duration)
    
    # 生成HTML内容
    generated_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 使用string.Template来避免转义大括号
    html_template = Template('''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GitHub PR效率报告</title>
    <!-- 添加Chart.js库 -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f5f5f5; color: #333; line-height: 1.6; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        header { background-color: #24292e; color: white; padding: 20px; border-radius: 8px; margin-bottom: 30px; text-align: center; }
        h1 { font-size: 2.5em; margin-bottom: 10px; }
        .subtitle { font-size: 1.2em; opacity: 0.8; }
        .metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .metric-card { background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1); text-align: center; }
        .metric-value { font-size: 2.5em; font-weight: bold; color: #28a745; margin-bottom: 10px; }
        .metric-label { font-size: 1.1em; color: #666; }
        .section { background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1); margin-bottom: 30px; }
        h2 { font-size: 1.8em; margin-bottom: 20px; color: #24292e; border-bottom: 2px solid #e1e4e8; padding-bottom: 10px; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #e1e4e8; }
        th { background-color: #f6f8fa; font-weight: 600; }
        tr:hover { background-color: #f6f8fa; }
        a { color: #0366d6; text-decoration: none; }
        a:hover { text-decoration: underline; }
        .creator-list { display: flex; flex-wrap: wrap; gap: 15px; margin-bottom: 20px; }
        .creator-item { background-color: #f6f8fa; padding: 10px 15px; border-radius: 20px; display: flex; align-items: center; gap: 10px; }
        .creator-name { font-weight: 600; }
        .creator-count { background-color: #28a745; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.9em; }
        .line-chart-container { height: 400px; margin-bottom: 20px; }
        .line-chart { height: 100%; width: 100%; }
        .footer { text-align: center; color: #666; font-size: 0.9em; margin-top: 30px; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>GitHub PR效率报告</h1>
            <p class="subtitle">仓库: sgl-project/sglang | 生成时间: $generated_time</p>
        </header>
        
        <!-- 核心指标 -->
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-value">$total_prs</div>
                <div class="metric-label">总PR数</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">$merged_count</div>
                <div class="metric-label">已合并PR数</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">$merge_rate%</div>
                <div class="metric-label">合并率</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">$avg_lifecycle天</div>
                <div class="metric-label">平均生命周期</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">$avg_additions</div>
                <div class="metric-label">平均新增代码行</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">$avg_comments</div>
                <div class="metric-label">平均评论数</div>
            </div>
        </div>
        
        <!-- PR提交与失败趋势图 -->
        <div class="section">
            <h2>PR提交与失败趋势</h2>
            <div class="line-chart-container">
                <canvas id="prTrendChart" class="line-chart"></canvas>
            </div>
        </div>
        
        <!-- Lint执行时长趋势图 -->
        <div class="section">
            <h2>Lint执行时长趋势</h2>
            <div class="line-chart-container">
                <canvas id="lintDurationChart" class="line-chart"></canvas>
            </div>
        </div>
        
        <!-- PR Test (NPU)执行时长趋势图 -->
        <div class="section">
            <h2>PR Test (NPU)执行时长趋势</h2>
            <div class="line-chart-container">
                <canvas id="prTestDurationChart" class="line-chart"></canvas>
            </div>
        </div>
        
        <!-- PR列表 -->
        <div class="section">
            <h2>PR详情列表</h2>
            <table>
                <thead>
                    <tr>
                        <th>PR编号</th>
                        <th>标题</th>
                        <th>状态</th>
                        <th>创建者</th>
                        <th>创建时间</th>
                        <th>合并状态</th>
                        <th>代码变更</th>
                        <th>评论数</th>
                    </tr>
                </thead>
                <tbody>
                    $pr_table_rows
                </tbody>
            </table>
        </div>
        
        <!-- PR创建者分布 -->
        <div class="section">
            <h2>PR创建者分布</h2>
            <div class="creator-list">
                $creator_items
            </div>
        </div>
        
        <script>
            // 初始化折线图
            const ctx = document.getElementById('prTrendChart').getContext('2d');
            const prTrendChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: $chart_dates_json,
                    datasets: [
                        {
                            label: '提交PR数',
                            data: $chart_total_json,
                            borderColor: '#28a745',
                            backgroundColor: 'rgba(40, 167, 69, 0.1)',
                            borderWidth: 2,
                            fill: true,
                            tension: 0.1
                        },
                        {
                            label: '失败PR数',
                            data: $chart_failed_json,
                            borderColor: '#dc3545',
                            backgroundColor: 'rgba(220, 53, 69, 0.1)',
                            borderWidth: 2,
                            fill: true,
                            tension: 0.1
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'top',
                        },
                        title: {
                            display: true,
                            text: 'PR提交与失败趋势图'
                        },
                        tooltip: {
                            mode: 'index',
                            intersect: false,
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: '数量'
                            }
                        },
                        x: {
                            title: {
                                display: true,
                                text: '日期'
                            }
                        }
                    }
                }
            });
        </script>
        
        <script>
            // 自定义时间格式化函数 (秒 -> 分:秒)
            function formatDuration(seconds) {
                var mins = Math.floor(seconds / 60);
                var secs = Math.round(seconds % 60);
                return mins + 'm' + secs + 's';
            }
            
            // 初始化Lint执行时长折线图
            const lintCtx = document.getElementById('lintDurationChart').getContext('2d');
            const lintDurationChart = new Chart(lintCtx, {
                type: 'line',
                data: {
                    labels: $lint_chart_dates_json,
                    datasets: [
                        {
                            label: 'Lint执行时长',
                            data: $lint_chart_duration_json,
                            borderColor: '#007bff',
                            backgroundColor: 'rgba(0, 123, 255, 0.1)',
                            borderWidth: 2,
                            fill: true,
                            tension: 0.1
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'top',
                        },
                        title: {
                            display: true,
                            text: 'Lint执行时长趋势图'
                        },
                        tooltip: {
                            mode: 'index',
                            intersect: false,
                            callbacks: {
                                label: function(context) {
                                    return context.dataset.label + ': ' + formatDuration(context.parsed.y);
                                }
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: '执行时长'
                            },
                            ticks: {
                                callback: function(value) {
                                    return formatDuration(value);
                                }
                            }
                        },
                        x: {
                            title: {
                                display: true,
                                text: '执行时间'
                            }
                        }
                    }
                }
            });
        </script>
        
        <script>
            // 初始化PR Test (NPU)执行时长折线图
            const prTestCtx = document.getElementById('prTestDurationChart').getContext('2d');
            const prTestDurationChart = new Chart(prTestCtx, {
                type: 'line',
                data: {
                    labels: $pr_test_chart_dates_json,
                    datasets: [
                        {
                            label: 'PR Test (NPU)执行时长',
                            data: $pr_test_chart_duration_json,
                            borderColor: '#ffc107',
                            backgroundColor: 'rgba(255, 193, 7, 0.1)',
                            borderWidth: 2,
                            fill: true,
                            tension: 0.1
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'top',
                        },
                        title: {
                            display: true,
                            text: 'PR Test (NPU)执行时长趋势图'
                        },
                        tooltip: {
                            mode: 'index',
                            intersect: false,
                            callbacks: {
                                label: function(context) {
                                    return context.dataset.label + ': ' + formatDuration(context.parsed.y);
                                }
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: '执行时长'
                            },
                            ticks: {
                                callback: function(value) {
                                    return formatDuration(value);
                                }
                            }
                        },
                        x: {
                            title: {
                                display: true,
                                text: '执行时间'
                            }
                        }
                    }
                }
            });
        </script>
        
        <footer class="footer">
            <p>报告生成时间: $generated_time</p>
            <p>数据来源: GitHub API</p>
        </footer>
    </div>
</body>
</html>
''')
    
    # 使用Template.substitute方法格式化HTML内容
    html_content = html_template.substitute(
        generated_time=generated_time,
        pr_table_rows=pr_table_rows,
        creator_items=creator_items,
        total_prs=metrics["total_prs"],
        merged_count=metrics["merged_count"],
        closed_count=metrics["closed_count"],
        merge_rate=metrics["merge_rate"],
        avg_lifecycle=metrics["avg_lifecycle"],
        avg_additions=metrics["avg_additions"],
        avg_deletions=metrics["avg_deletions"],
        avg_changed_files=metrics["avg_changed_files"],
        avg_comments=metrics["avg_comments"],
        chart_dates_json=chart_dates_json,
        chart_total_json=chart_total_json,
        chart_failed_json=chart_failed_json,
        lint_chart_dates_json=lint_chart_dates_json,
        lint_chart_duration_json=lint_chart_duration_json,
        pr_test_chart_dates_json=pr_test_chart_dates_json,
        pr_test_chart_duration_json=pr_test_chart_duration_json
    )
    
    return html_content


def save_html_report(html_content, output_file):
    """保存HTML报告到文件"""
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"PR效率报告已生成: {output_file}")
    return output_file


def main():
    """主函数"""
    # 命令行参数解析
    parser = argparse.ArgumentParser(description="生成PR效率报告")
    parser.add_argument(
        "--output", "-o",
        default=HTML_OUTPUT_FILE,
        help=f"HTML输出文件名 (默认: {HTML_OUTPUT_FILE})"
    )
    args = parser.parse_args()
    
    try:
        # 加载最新PR数据
        pr_data = load_latest_pr_data()
        
        # 计算PR指标
        metrics = calculate_pr_metrics(pr_data)
        
        # 生成HTML报告
        html_content = generate_html_report(pr_data, metrics)
        
        # 保存HTML报告
        save_html_report(html_content, args.output)
        
    except Exception as e:
        print(f"发生错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
