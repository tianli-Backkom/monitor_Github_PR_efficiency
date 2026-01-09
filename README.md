# GitHub PR效率监控系统

## 系统简介

该系统用于监控和展示 `sgl-project/sglang` 仓库中带有 `npu` 标签的PR效率数据，帮助团队了解PR门禁执行情况、识别需要改进的开发流程。

## 核心功能

### 监控脚本 (`monitor_prs.py`)
- 获取指定仓库近两周内创建的带有 `npu` 标签的PR列表
- 收集PR的门禁检查（checks）和workflow执行时长数据
- 统计门禁重试次数，识别需要重点关注的开发者
- 支持API分页处理和速率限制
- 自动保存数据到本地JSON文件

### 展示脚本 (`generate_pr_report.py`)
- 读取本地最新的PR数据文件
- 计算7个核心PR效率指标
- 生成美观的HTML可视化报告

## 监控指标

### 核心指标

| 指标名称 | 说明 | 计算方法 |
|---------|------|---------|
| **PR总数** | 近两周内带有 `npu` 标签的PR总数 | 直接统计 |
| **待合入PR数量** | 状态为open且带有 `npu` 标签的PR数量 | 统计open状态PR |
| **run-ci标签PR数量** | 同时包含 `run-ci` 和 `npu` 标签的PR数量 | 统计双标签PR |
| **PR门禁成功率** | 门禁通过的PR占比 | (通过PR数 / 总PR数) × 100% |
| **门禁静态检查任务时长** | Lint任务的平均执行时长 | 所有PR的lint_duration平均值 |
| **PR Test自动化执行时长** | PR Test任务的平均执行时长 | 所有PR的pr_test_duration平均值 |
| **PR Test(NPU)自动化执行时长** | PR Test (NPU)任务的平均执行时长 | 所有PR的pr_test_npu_duration平均值 |

### 门禁重试次数分析

| 指标名称 | 说明 |
|---------|------|
| **平均门禁重试次数** | 所有PR的平均门禁重试次数 |
| **门禁重试次数分布** | 按重试次数分类统计（0次、1-2次、3-5次、>5次） |
| **门禁重试次数最多的开发者** | 识别需要重点关注的开发者，帮助改进本地调试环境 |

## 依赖安装

### 所需Python依赖

- requests：用于发送HTTP请求

### 安装方法

```bash
pip install requests
```

## GitHub Token配置

### 生成Personal Access Token (PAT)

1. 登录GitHub账号
2. 进入 `Settings` → `Developer settings` → `Personal access tokens` → `Tokens (classic)`
3. 点击 `Generate new token (classic)`
4. 选择权限：至少需要 `repo` 或 `public_repo` 权限
5. 设置过期时间
6. 生成并复制token

### 配置环境变量

#### Windows PowerShell

```powershell
$env:GH_TOKEN = "your_github_token_here"
```

#### Windows CMD

```cmd
set GH_TOKEN=your_github_token_here
```

#### Linux/macOS

```bash
export GH_TOKEN="your_github_token_here"
```

## 脚本运行

### 1. 监控脚本 (`monitor_prs.py`)

获取最新的PR数据并保存到本地：

```bash
python monitor_prs.py
```

**说明**：
- 脚本会获取近两周内带有 `npu` 标签的PR数据
- 数据会保存到 `pr_data/pr_data_YYYYMMDD.json` 文件中
- 包含PR基本信息、门禁状态、执行时长、重试次数等数据

### 2. 展示脚本 (`generate_pr_report.py`)

生成PR效率HTML报告：

```bash
python generate_pr_report.py
```

**可选参数**：
- `-o, --output`：指定HTML输出文件名（默认：`pr_efficiency_report.html`）

**示例**：
```bash
python generate_pr_report.py --output my_report.html
```

## 数据存储

- PR数据保存在 `pr_data` 目录下
- 文件命名格式：`pr_data_YYYYMMDD.json`
- 系统自动使用最新的数据文件生成报告
- 建议定期清理旧的数据文件，只保留最新的数据

## 输出报告说明

### HTML报告包含以下内容

#### 1. 核心指标卡片
- 7个核心指标的数值展示
- 平均门禁重试次数

#### 2. 门禁重试次数分布
- 按重试次数分类的PR数量统计
- 帮助识别门禁执行效率问题

#### 3. 门禁重试次数最多的开发者
- 按重试次数排序的开发者列表
- 识别需要重点关注的开发者，帮助改进本地调试环境

#### 4. PR详情列表
- PR编号、标题、状态、创建者
- 创建时间、合并状态、代码变更量
- 评论数、门禁状态
- 门禁静态检查时长
- PR Test执行时长
- PR Test(NPU)执行时长
- 门禁重试次数

#### 5. 趋势图表
- PR提交与失败趋势
- Lint执行时长趋势
- PR Test (NPU)执行时长趋势

## 关键逻辑说明

### 时间筛选
- 脚本自动计算近两周的时间范围（以脚本运行时间为基准，向前推14天）
- 使用ISO 8601格式与GitHub API交互
- 按创建时间降序排序，提高筛选效率

### 门禁重试次数计算
- 统计同一个check名称被重新执行的次数
- 每个check名称的执行次数减去1（第一次不算重试）
- 例如：某个check执行了3次，则重试次数为2

### 门禁状态判断
- **passed**：所有checks都通过
- **failed**：至少有一个check失败
- **pending**：checks还在运行中
- **unknown**：无法获取门禁状态

### 执行时长数据
- **lint_duration**：Lint任务的执行时长（秒）
- **pr_test_duration**：PR Test任务的执行时长（秒）
- **pr_test_npu_duration**：PR Test (NPU)任务的执行时长（秒）

## 部署建议

### 方式一：GitHub Workflow（推荐）

使用GitHub Actions实现自动化运行：

1. **配置GitHub Secrets**：
   - 在GitHub仓库中导航到 `Settings` → `Secrets and variables` → `Actions`
   - 添加名为 `GH_TOKEN` 的secret，值为你的GitHub Personal Access Token
   - 确保PAT具有 `repo` 或 `public_repo` 权限

2. **Workflow执行流程**：
   - 自动检出代码
   - 设置Python环境
   - 安装依赖
   - 运行监控脚本获取PR数据
   - 生成PR效率报告
   - 上传报告作为artifact

Workflow配置文件：[`.github/workflows/monitor-prs.yml`](file:///d:/code/monitor_Github_PR_efficiency/.github/workflows/monitor-prs.yml)

### 方式二：本地定时任务

使用系统定时任务（如cron或Windows任务计划）：

1. **创建定时任务**：
   - 每天运行一次监控脚本，获取最新PR数据
   - 每天运行一次展示脚本，生成最新报告

2. **示例cron配置**：
   ```bash
   # 每天9点运行监控脚本
   0 9 * * * cd /path/to/monitor_Github_PR_efficiency && python monitor_prs.py
   
   # 每天9:30运行展示脚本
   30 9 * * * cd /path/to/monitor_Github_PR_efficiency && python generate_pr_report.py
   ```

### 方式三：手动运行

```bash
# 运行一次监控任务
python monitor_prs.py

# 生成PR效率报告
python generate_pr_report.py
```

## 项目结构

```
monitor_Github_PR_efficiency/
├── .github/
│   └── workflows/
│       └── monitor-prs.yml      # GitHub Actions配置
├── pr_data/                     # PR数据存储目录
│   └── pr_data_YYYYMMDD.json    # PR数据文件
├── monitor_prs.py               # 监控脚本
├── generate_pr_report.py        # 报告生成脚本
├── pr_efficiency_report.html    # 生成的HTML报告
├── SETUP_TOKEN.md               # GitHub Token设置指南
└── README.md                    # 项目说明文档
```

## 注意事项

1. 请确保GitHub Token具有足够的权限
2. 脚本默认获取 `sgl-project/sglang` 仓库的PR数据
3. 如果需要修改目标仓库，请编辑 `monitor_prs.py` 中的 `OWNER` 和 `REPO` 常量
4. 对于大型仓库，获取所有PR详情可能需要较长时间
5. 请遵守GitHub API使用条款
6. 建议定期清理旧的PR数据文件，避免占用过多磁盘空间

## 实际价值

通过本系统可以：
1. **监控PR门禁执行效率**：了解门禁成功率和平均执行时长
2. **识别问题开发者**：通过门禁重试次数分析，找出需要改进本地调试环境的开发者
3. **优化开发流程**：根据数据分析结果，提出针对性的改进措施
4. **提高代码质量**：通过门禁重试次数统计，促进开发者提高代码质量

## 许可证

MIT
