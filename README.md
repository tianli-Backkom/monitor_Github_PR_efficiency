# GitHub PR效率监控系统

## 系统功能

该系统由两个脚本组成，用于监控和展示GitHub仓库PR效率：

1. **监控脚本** (`monitor_prs.py`)：每天查询最近两周带有`npu`标签的PR数据，并将数据保存到本地
2. **展示脚本** (`generate_pr_report.py`)：读取本地PR数据，解析PR效率关键指标，并生成HTML页面展示

## 核心功能

### 监控脚本
- 获取指定仓库近两周内创建的PR列表
- 支持处理API分页（最多100条/页）
- 支持API请求失败重试机制（最多3次）
- 自动处理GitHub API速率限制
- 每天自动运行，保存数据到本地
- 符合PEP8代码规范

### 展示脚本
- 读取本地最新的PR数据文件
- 计算PR效率关键指标（合并率、平均生命周期等）
- 生成美观的HTML报告，包含：
  - 核心指标卡片展示
  - PR详情列表
  - PR创建者分布
  - PR创建趋势图
  - 详细指标说明

## 依赖安装

### 所需Python依赖

- requests：用于发送HTTP请求

### 安装方法

```bash
pip install requests
```

## GitHub PAT配置

### 生成PAT

1. 登录GitHub账号
2. 进入`Settings` -> `Developer settings` -> `Personal access tokens` -> `Tokens (classic)`
3. 点击`Generate new token`
4. 选择权限：至少需要`repo`或`public_repo`权限
5. 设置过期时间
6. 生成并复制PAT

### 配置环境变量

#### Windows

```cmd
set GITHUB_PAT=your_github_token_here
```

或者在PowerShell中：

```powershell
$env:GITHUB_PAT = "your_github_token_here"
```

#### Linux/macOS

```bash
export GITHUB_PAT=your_github_token_here
```

## 脚本运行

### 1. 监控脚本 (`monitor_prs.py`)

#### 命令格式

```bash
python monitor_prs.py [OPTIONS]
```

#### 可选参数

- `--once`：只运行一次，不进行循环（默认：每天自动运行一次）

#### 示例

#### 只运行一次，获取并保存PR数据

```bash
python monitor_prs.py --once
```

#### 每天自动运行（后台运行）

```bash
# Linux/macOS
nohup python monitor_prs.py > monitor.log 2>&1 &

# Windows（使用PowerShell后台运行）
Start-Job -ScriptBlock { python monitor_prs.py }
```

### 2. 展示脚本 (`generate_pr_report.py`)

#### 命令格式

```bash
python generate_pr_report.py [OPTIONS]
```

#### 可选参数

- `-o, --output`：HTML输出文件名（默认：`pr_efficiency_report.html`）

#### 示例

#### 生成默认文件名的HTML报告

```bash
python generate_pr_report.py
```

#### 指定HTML输出文件名

```bash
python generate_pr_report.py --output my_pr_report.html
```

## 数据存储

- PR数据保存在`pr_data`目录下，文件名格式：`pr_data_20251231.json`
- 每个文件包含当天获取的近两周内的PR数据
- 系统自动使用最新的数据文件生成报告

## 输出报告说明

### HTML报告包含以下内容

1. **核心指标卡片**：
   - 总PR数
   - 已合并PR数
   - 合并率
   - 平均生命周期
   - 平均新增代码行
   - 平均评论数

2. **PR详情列表**：
   - PR编号和标题
   - 状态和创建者
   - 创建时间和合并状态
   - 代码变更量
   - 评论数
   - GitHub链接

3. **PR创建者分布**：
   - 显示每个创建者的PR数量
   - 以标签云形式展示

4. **PR创建趋势图**：
   - 按日期的PR创建数量柱状图
   - 可视化展示PR创建趋势

5. **详细指标说明**：
   - 所有计算指标的详细说明
   - 指标数值和解释

## 关键逻辑说明

### 时间筛选

- 脚本自动计算近两周的时间范围（以脚本运行时间为基准，向前推14天）
- 使用ISO 8601格式（如：2025-12-17T00:00:00Z）与GitHub API交互
- 按创建时间降序排序，提高筛选效率

### 分页处理

- 每页获取最多100条PR数据
- 循环获取直到没有更多数据或超出时间范围
- 避免不必要的API请求

### 速率限制处理

- 检测响应中的速率限制信息
- 当达到速率限制时，根据`X-RateLimit-Reset`头计算等待时间
- 自动等待后重试请求

### 指标计算

| 指标名称 | 计算方法 | 说明 |
|---------|---------|------|
| 总PR数 | 直接统计 | 近两周内创建的PR总数 |
| 合并率 | (已合并PR数 / 总PR数) * 100% | 已合并PR占总PR数的比例 |
| 平均生命周期 | 总生命周期 / 已关闭PR数 | 从创建到合并/关闭的平均时间（天） |
| 平均代码变更 | 总新增/删除行数 / 总PR数 | 每个PR平均的代码变更量 |
| 平均评论数 | 总评论数 / 总PR数 | 每个PR平均的评论和评审评论总数 |

## 注意事项

1. 请确保GitHub PAT具有足够的权限
2. 脚本默认获取`sgl-project/sglang`仓库的PR数据
3. 如果需要修改目标仓库，请编辑脚本中的`OWNER`和`REPO`常量
4. 对于大型仓库，获取所有PR详情可能需要较长时间
5. 请遵守GitHub API使用条款
6. 监控脚本需要在后台持续运行，或通过定时任务（如cron）定期执行

## 系统架构

```
┌─────────────────┐     ┌───────────────┐     ┌────────────────────┐
│  GitHub API     │     │  监控脚本      │     │  展示脚本          │
│                 │────▶│  monitor_prs.py│────▶│  generate_pr_report.py │
└─────────────────┘     └───────────────┘     └────────────────────┘
                              │                          │
                              ▼                          ▼
                        ┌───────────┐            ┌─────────────────┐
                        │ PR数据文件 │            │ HTML报告文件     │
                        │ pr_data/  │            │ pr_efficiency_report.html │
                        └───────────┘            └─────────────────┘
```

## 部署建议

### 方式一：GitHub Workflow（推荐）

使用GitHub Actions实现自动化运行：

1. **创建GitHub workflow文件**：
   - 在仓库中创建 `.github/workflows/monitor-prs.yml` 文件（已提供模板）
   - 配置每天UTC时间1点（北京时间9点）自动运行
   - 支持手动触发

2. **配置GitHub Secrets**：
   - 在GitHub仓库中导航到 `Settings` → `Secrets and variables` → `Actions`
   - 添加名为 `GITHUB_PAT` 的secret，值为你的GitHub Personal Access Token
   - 确保PAT具有 `repo` 或 `public_repo` 权限

3. **Workflow执行流程**：
   - 自动检出代码
   - 设置Python环境
   - 安装依赖
   - 运行监控脚本获取PR数据
   - 生成PR效率报告
   - 上传报告作为artifact，保留30天

### 方式二：本地定时任务

使用系统定时任务（如cron或Windows任务计划）：

1. **创建定时任务**：
   - 每天运行一次监控脚本，获取最新PR数据
   - 每天运行一次展示脚本，生成最新报告

2. **示例cron配置**：
   ```bash
   # 每天9点运行监控脚本
   0 9 * * * python /path/to/monitor_prs.py
   
   # 每天9:30运行展示脚本
   30 9 * * * python /path/to/generate_pr_report.py
   ```

### 方式三：手动运行

```bash
# 运行一次监控任务
python monitor_prs.py

# 生成PR效率报告
python generate_pr_report.py
```

## 许可证

MIT
