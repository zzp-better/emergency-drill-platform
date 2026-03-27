# Emergency Drill Automation Platform (EDAP)

**应急演练自动化平台** - 基于云原生技术的故障注入与验证系统

## 项目背景

在中国移动工作期间，我使用过京东的商业混沌工程系统进行应急演练。虽然功能强大，但存在以下问题：

1. **成本高昂**：商业系统授权费用高，中小企业难以承受
2. **定制困难**：黑盒系统，无法根据实际应急管理场景定制
3. **场景通用**：缺少针对应急预案验证的专用功能

因此，我基于开源技术栈开发了这个轻量化的应急演练自动化平台。

## 核心特性

- ✅ **开源免费**：基于 Apache 2.0 协议，完全免费使用
- ✅ **故障注入**：支持 Pod 故障、CPU 压测、网络故障、磁盘 IO 故障等多种场景
- ✅ **Chaos Mesh 集成**：通过 Chaos Mesh 实现丰富的故障注入场景
- ✅ **监控验证**：自动验证 Prometheus 告警是否按预期触发
- ✅ **预案验证**：自动生成应急演练报告，验证预案有效性
- ✅ **故障链编排**：支持多步骤故障链，实现复杂演练场景
- ✅ **定时调度**：支持 Cron 表达式定时执行演练任务
- ✅ **Web UI**：直观的可视化界面，操作简单
- ✅ **云原生**：基于 Kubernetes 和 Chaos Mesh

## 技术架构

```
┌──────────────────────────────────────────┐
│    Emergency Drill Platform              │
└──────────────────────────────────────────┘
               │
     ┌─────────┼─────────┐
     ▼         ▼         ▼
┌────────┐ ┌────────┐ ┌────────┐
│故障注入│ │监控验证│ │报告生成│
└────────┘ └────────┘ └────────┘
     │         │         │
     ▼         ▼         ▼
Chaos Mesh  Prometheus  Markdown
  │
  ├── CPU 压测
  ├── 网络延迟/丢包
  ├── 磁盘 IO 故障
  └── Pod 故障
```

## 技术栈

- **编程语言**：Python 3.8+
- **容器编排**：Kubernetes
- **故障注入**：Chaos Mesh
- **监控系统**：Prometheus
- **Web 框架**：Streamlit (待开发)
- **容器化**：Docker + Helm

## 快速开始

### 前置条件

- Kubernetes 集群（本地可使用 Kind 或 Minikube）
- Python 3.8+
- kubectl 已配置
- Chaos Mesh 已安装（用于高级故障场景，可选）

### 安装依赖

```bash
pip install -r requirements.txt
```

### 方式一：Web UI（推荐）

启动可视化界面：

```bash
streamlit run app.py
```

然后在浏览器中访问 http://localhost:8501

### 方式二：命令行

```bash
# 运行 Pod 删除故障注入（原生 K8s）
python src/chaos_injector.py

# 运行 Chaos Mesh 故障注入
python examples/chaos_mesh_drill.py

# 验证 Prometheus 告警
python src/monitor_checker.py
```

## 项目结构

```
emergency-drill-platform/
├── README.md                   # 项目说明
├── app.py                     # Web UI 入口（Streamlit）
├── requirements.txt            # Python 依赖
├── src/                        # 核心源代码
│   ├── chaos_injector.py      # 故障注入模块（支持原生 K8s 和 Chaos Mesh）
│   ├── chaos_mesh_injector.py # Chaos Mesh 故障注入模块
│   ├── monitor_checker.py     # 监控验证模块
│   ├── scheduler.py           # 定时调度模块
│   └── db.py                  # 数据库模块
├── web_ui/                     # Web UI 模块化代码
│   ├── pages/                 # 页面模块
│   │   ├── home.py           # 首页
│   │   ├── cluster_resources.py  # 集群资源
│   │   ├── fault_injection.py    # 故障注入
│   │   ├── chain_drill.py        # 故障链
│   │   ├── reports.py            # 演练报告
│   │   ├── settings.py           # 系统设置
│   │   └── monitor.py            # 监控面板
│   ├── config.py              # 配置常量
│   ├── state.py               # 状态管理
│   ├── utils.py               # 工具函数
│   ├── drill_executor.py      # 演练执行器
│   └── chain_executor.py      # 故障链执行器
├── scenarios/                  # 故障场景配置
│   ├── pod_crash.yaml         # Pod 崩溃场景
│   ├── cpu_stress.yaml        # CPU 压测场景
│   ├── network_delay.yaml     # 网络延迟场景
│   └── disk_io.yaml           # 磁盘 IO 故障场景
├── docs/                       # 文档
├── tests/                      # 测试代码
└── examples/                   # 示例代码
    ├── complete_drill.py       # 完整演练流程示例
    └── chaos_mesh_drill.py    # Chaos Mesh 演练示例
```

## 使用场景

### 场景 1：应急预案验证

验证"核心业务 Pod 崩溃"应急预案是否有效：

1. 自动删除指定 Pod
2. 检查监控告警是否触发
3. 验证 Pod 是否在预期时间内恢复
4. 生成演练报告

### 场景 2：定期自动演练

通过 Kubernetes CronJob，每天自动执行应急演练，确保系统随时处于可用状态。

### 场景 3：新系统上线前验证

在新系统上线前，批量执行故障注入，验证监控告警、自愈能力是否正常。

## 开发计划

- [x] 项目初始化
- [x] 实现 Pod 故障注入
- [x] 实现监控告警验证
- [x] 实现报告自动生成（基础版）
- [x] 集成 Chaos Mesh（CPU 压测、网络故障、磁盘 IO 故障）
- [x] 开发 Web UI
- [ ] 容器化部署
- [ ] Helm Chart 打包

## 快速演示

### 原生 Kubernetes 演练

运行完整的应急演练（故障注入 + 监控验证 + 报告生成）：

```bash
python examples/complete_drill.py
```

这个示例会：
1. 删除指定 Pod（故障注入）
2. 验证 Prometheus 告警是否触发
3. 自动生成 Markdown 格式的演练报告

### Chaos Mesh 演练

运行 Chaos Mesh 故障注入演练：

```bash
python examples/chaos_mesh_drill.py
```

支持的故障场景：
1. **CPU 压测**：模拟 CPU 资源耗尽
2. **网络延迟**：模拟网络不稳定
3. **磁盘故障**：模拟磁盘空间不足或读写错误
4. **完整演练流程**：故障注入 + 监控验证 + 报告生成

## Chaos Mesh 安装指南

如果需要使用 Chaos Mesh 的高级故障场景，请先安装 Chaos Mesh：

```bash
# 使用 Helm 安装 Chaos Mesh
helm repo add chaos-mesh https://charts.chaos-mesh.org
helm repo update
kubectl create namespace chaos-mesh
helm install chaos-mesh chaos-mesh/chaos-mesh -n chaos-mesh --version 2.6.1

# 验证安装
kubectl get pod -n chaos-mesh
```

详细安装指南：https://chaos-mesh.org/docs/installation

## 贡献指南

欢迎提交 Issue 和 Pull Request！

## 许可证

Apache License 2.0

## 联系方式

- GitHub Issues: [提交问题](https://github.com/your-username/emergency-drill-platform/issues)
- 作者：应急运维工程师
- 背景：4年运维经验 | RHCA | CKA | CKS | 中国移动
