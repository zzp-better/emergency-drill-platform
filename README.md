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
- ✅ **故障注入**：支持 Pod 故障、网络故障、资源压测等多种场景
- ✅ **监控验证**：自动验证 Prometheus 告警是否按预期触发
- ✅ **预案验证**：自动生成应急演练报告，验证预案有效性
- ✅ **简单易用**：Web UI 操作，无需复杂配置
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
- Chaos Mesh 已安装（可选，后续版本会用到）

### 安装依赖

```bash
pip install -r requirements.txt
```

### 第一个故障注入示例

```bash
# 运行 Pod 删除故障注入
python src/chaos_injector.py --config scenarios/pod_crash.yaml
```

### 监控验证示例

```bash
# 验证 Prometheus 告警
python src/monitor_checker.py --scenario pod_crash
```

## 项目结构

```
emergency-drill-platform/
├── README.md                   # 项目说明
├── requirements.txt            # Python 依赖
├── src/                        # 源代码
│   ├── chaos_injector.py      # 故障注入模块
│   ├── monitor_checker.py     # 监控验证模块
│   └── report_generator.py    # 报告生成模块
├── scenarios/                  # 故障场景配置
│   ├── pod_crash.yaml         # Pod 崩溃场景
│   ├── cpu_stress.yaml        # CPU 压测场景
│   └── network_delay.yaml     # 网络延迟场景
├── docs/                       # 文档
├── tests/                      # 测试代码
└── examples/                   # 示例代码
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
- [ ] 实现 Pod 故障注入
- [ ] 实现监控告警验证
- [ ] 实现报告自动生成
- [ ] 集成 Chaos Mesh
- [ ] 开发 Web UI
- [ ] 容器化部署
- [ ] Helm Chart 打包

## 贡献指南

欢迎提交 Issue 和 Pull Request！

## 许可证

Apache License 2.0

## 联系方式

- GitHub Issues: [提交问题](https://github.com/your-username/emergency-drill-platform/issues)
- 作者：应急运维工程师
- 背景：4年运维经验 | RHCA | CKA | CKS | 中国移动
