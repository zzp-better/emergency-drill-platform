# 架构设计文档 (ARCHITECTURE.md)

## 目录

- [系统概述](#系统概述)
- [设计原则](#设计原则)
- [系统架构](#系统架构)
- [核心模块](#核心模块)
- [数据流](#数据流)
- [技术选型](#技术选型)
- [安全设计](#安全设计)
- [扩展性设计](#扩展性设计)
- [性能优化](#性能优化)

---

## 系统概述

### 项目背景

应急演练自动化平台（Emergency Drill Automation Platform, EDAP）是一个基于云原生技术的故障注入与验证系统。该平台旨在解决传统应急演练中的以下痛点：

1. **手动操作繁琐**: 传统演练需要人工触发故障、监控告警、记录结果
2. **验证不充分**: 难以验证监控告警是否按预期触发
3. **成本高昂**: 商业混沌工程系统授权费用高
4. **定制困难**: 黑盒系统无法根据实际场景定制

### 核心目标

- ✅ **自动化**: 全流程自动化，从故障注入到报告生成
- ✅ **可验证**: 自动验证监控告警、自愈能力
- ✅ **低成本**: 基于开源技术，完全免费
- ✅ **易扩展**: 模块化设计，易于添加新的故障场景
- ✅ **云原生**: 基于 Kubernetes 和 Chaos Mesh

---

## 设计原则

### 1. 模块化设计

系统采用模块化架构，每个模块职责单一、高内聚低耦合：

- **故障注入模块**: 负责各类故障的注入
- **监控验证模块**: 负责验证监控告警
- **报告生成模块**: 负责生成演练报告
- **Web UI 模块**: 负责用户交互

### 2. 可扩展性

- **插件化故障场景**: 通过 YAML 配置文件定义新场景
- **多种故障注入方式**: 支持原生 K8s 和 Chaos Mesh
- **灵活的监控集成**: 支持 Prometheus 及其他监控系统

### 3. 安全性

- **最小权限原则**: 仅申请必要的 Kubernetes 权限
- **输入验证**: 严格验证所有用户输入
- **审计日志**: 记录所有故障注入操作

### 4. 可观测性

- **详细日志**: 记录每个操作的详细信息
- **结构化输出**: 使用 JSON 格式输出结果
- **可视化报告**: 生成 Markdown 格式的演练报告

---

## 系统架构

### 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         用户访问层                                │
│                                                                   │
│  ┌──────────────────┐              ┌──────────────────┐         │
│  │   Web UI         │              │   CLI 工具        │         │
│  │  (Streamlit)     │              │   (Python)        │         │
│  │  - 可视化界面     │              │  - 命令行接口      │         │
│  │  - 交互式操作     │              │  - 脚本自动化      │         │
│  └──────────────────┘              └──────────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      应用服务层                                   │
│                                                                   │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐  │
│  │  故障注入模块     │  │  监控验证模块     │  │  报告生成模块 │  │
│  │ ChaosInjector    │  │ MonitorChecker   │  │ReportGenerator│  │
│  │                  │  │                  │  │               │  │
│  │ - Pod 删除       │  │ - 告警查询       │  │ - Markdown    │  │
│  │ - CPU 压测       │  │ - 指标查询       │  │ - JSON        │  │
│  │ - 网络故障       │  │ - 等待告警触发   │  │ - 统计分析    │  │
│  │ - 磁盘故障       │  │                  │  │               │  │
│  └──────────────────┘  └──────────────────┘  └──────────────┘  │
│           │                      │                               │
│           │                      │                               │
│  ┌────────┴──────────────────────┴───────────────────────────┐  │
│  │              场景配置管理 (YAML)                            │  │
│  │  - pod_crash.yaml                                          │  │
│  │  - cpu_stress.yaml                                         │  │
│  │  - network_delay.yaml                                      │  │
│  │  - disk_io.yaml                                            │  │
│  └────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      基础设施层                                   │
│                                                                   │
│  ┌──────────────────┐              ┌──────────────────┐         │
│  │ Kubernetes API   │              │ Prometheus API   │         │
│  │                  │              │                  │         │
│  │ - Pod 管理       │              │ - 告警查询       │         │
│  │ - 资源监控       │              │ - 指标查询       │         │
│  │ - 事件监听       │              │ - PromQL 执行    │         │
│  └──────────────────┘              └──────────────────┘         │
│           │                                                       │
│           ▼                                                       │
│  ┌──────────────────┐                                            │
│  │   Chaos Mesh     │                                            │
│  │  (可选高级功能)   │                                            │
│  │                  │                                            │
│  │ - StressChaos    │  (CPU/内存压测)                            │
│  │ - NetworkChaos   │  (网络延迟/丢包)                           │
│  │ - IOChaos        │  (磁盘故障)                                │
│  │ - PodChaos       │  (Pod 故障)                                │
│  └──────────────────┘                                            │
└─────────────────────────────────────────────────────────────────┘
```

### 分层架构

#### 1. 用户访问层

**Web UI (Streamlit)**
- 提供可视化的用户界面
- 支持交互式操作
- 实时显示演练进度和结果

**CLI 工具**
- 命令行接口
- 支持脚本自动化
- 适合 CI/CD 集成

#### 2. 应用服务层

**故障注入模块 (ChaosInjector)**
- 统一的故障注入接口
- 支持多种故障类型
- 自动检测故障恢复

**监控验证模块 (MonitorChecker)**
- Prometheus 客户端封装
- 告警查询和验证
- 指标数据分析

**报告生成模块 (ReportGenerator)**
- 自动生成演练报告
- 支持多种输出格式
- 统计分析功能

#### 3. 基础设施层

**Kubernetes**
- 容器编排平台
- 提供 Pod 管理能力
- 资源监控和事件

**Prometheus**
- 监控数据采集
- 告警规则引擎
- 指标查询接口

**Chaos Mesh**
- 高级故障注入
- 丰富的故障场景
- 声明式配置

---

## 核心模块

### 1. 故障注入模块 (ChaosInjector)

#### 职责

- 执行各类故障注入操作
- 监控故障注入结果
- 检测系统自愈能力

#### 类设计

```python
class ChaosInjector:
    """故障注入器 - 统一接口"""

    def __init__(self, use_chaos_mesh: bool = False):
        """初始化故障注入器"""

    # 原生 Kubernetes 故障注入
    def delete_pod(self, namespace, pod_name) -> Dict:
        """删除 Pod，模拟崩溃故障"""

    # Chaos Mesh 故障注入
    def inject_cpu_stress(self, namespace, pod_name, ...) -> Dict:
        """注入 CPU/内存压测故障"""

    def inject_network_delay(self, namespace, pod_name, ...) -> Dict:
        """注入网络延迟故障"""

    def inject_disk_failure(self, namespace, pod_name, ...) -> Dict:
        """注入磁盘故障"""

    # 配置文件驱动
    def inject_from_config(self, config_path: str) -> Dict:
        """根据配置文件注入故障"""
```

#### 支持的故障类型

| 故障类型 | 实现方式 | 使用场景 |
|---------|---------|---------|
| Pod 崩溃 | 原生 K8s API | 验证 Pod 自动重启 |
| CPU 压测 | Chaos Mesh StressChaos | 验证 CPU 告警 |
| 内存压测 | Chaos Mesh StressChaos | 验证内存告警 |
| 网络延迟 | Chaos Mesh NetworkChaos | 验证网络监控 |
| 网络丢包 | Chaos Mesh NetworkChaos | 验证网络容错 |
| 磁盘填充 | Chaos Mesh IOChaos | 验证磁盘告警 |
| 磁盘读写错误 | Chaos Mesh IOChaos | 验证 IO 容错 |

#### 故障注入流程

```
┌─────────────┐
│ 加载配置文件 │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 验证目标存在 │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 执行故障注入 │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 监控故障状态 │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 检测自愈恢复 │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 返回注入结果 │
└─────────────┘
```

### 2. 监控验证模块 (MonitorChecker)

#### 职责

- 查询 Prometheus 告警状态
- 验证预期告警是否触发
- 查询监控指标数据

#### 类设计

```python
class PrometheusClient:
    """Prometheus 客户端"""

    def __init__(self, url: str, username=None, password=None):
        """初始化客户端"""

    def query_alerts(self) -> List[Dict]:
        """查询所有活跃告警"""

    def query_alert_by_name(self, alert_name: str) -> Optional[Dict]:
        """查询指定名称的告警"""

    def query_metrics(self, query: str) -> Dict:
        """执行 PromQL 查询"""

class MonitorChecker:
    """监控验证器"""

    def __init__(self, prometheus_url: str, ...):
        """初始化验证器"""

    def wait_for_alert(self, alert_name: str, timeout: int) -> Dict:
        """等待指定告警触发"""

    def verify_alert_exists(self, alert_name: str) -> bool:
        """验证告警是否存在"""

    def check_pod_metrics(self, namespace: str, pod_name: str) -> Dict:
        """检查 Pod 相关指标"""
```

#### 告警验证流程

```
┌─────────────┐
│ 连接Prometheus│
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 开始轮询告警 │
└──────┬──────┘
       │
       ▼
┌─────────────┐     是    ┌─────────────┐
│ 告警已触发？ ├─────────→│ 记录触发时间 │
└──────┬──────┘           └──────┬──────┘
       │ 否                      │
       ▼                         │
┌─────────────┐                 │
│ 是否超时？   │                 │
└──────┬──────┘                 │
       │ 否                      │
       ▼                         │
┌─────────────┐                 │
│ 等待间隔时间 │                 │
└──────┬──────┘                 │
       │                         │
       └─────────────────────────┘
                │
                ▼
         ┌─────────────┐
         │ 返回验证结果 │
         └─────────────┘
```

### 3. 报告生成模块

#### 职责

- 收集演练数据
- 生成结构化报告
- 提供统计分析

#### 报告内容

```markdown
# 应急演练报告

## 基本信息
- 演练时间: 2026-01-29 10:00:00
- 场景名称: Pod 崩溃演练
- 目标对象: default/nginx-xxx

## 故障注入
- 注入方式: Pod 删除
- 注入时间: 10:00:05
- 注入结果: 成功

## 监控验证
- 预期告警: PodCrashLooping
- 告警触发: 是
- 触发时间: 10:00:15
- 等待时长: 10 秒

## 自愈验证
- Pod 恢复: 是
- 恢复时间: 25 秒
- 新 Pod 状态: Running

## 结论
✅ 演练成功
- 监控告警按预期触发
- Pod 自动恢复正常
```

### 4. Web UI 模块

#### 页面结构

```
┌─────────────────────────────────────┐
│           侧边栏导航                 │
│  ┌───────────────────────────────┐  │
│  │ 🏠 首页                        │  │
│  │ ⚡ 故障注入                    │  │
│  │ 📊 监控验证                    │  │
│  │ 📄 演练报告                    │  │
│  │ ⚙️ 设置                        │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘

首页 (page_home)
├── 统计卡片
│   ├── 演练次数
│   ├── 可用场景
│   └── 成功率
├── 快速开始按钮
└── 演练历史表格

故障注入页面 (page_fault_injection)
├── 故障注入器配置
├── 场景选择
├── 参数配置
│   ├── 命名空间
│   ├── Pod 名称
│   ├── 超时时间
│   └── 检查间隔
└── 执行按钮 + 结果展示

监控验证页面 (page_monitoring)
├── Prometheus 连接配置
├── 告警查询
│   ├── 按名称查询
│   └── 查询所有告警
└── 告警详情展示

演练报告页面 (page_reports)
├── 报告列表
├── 报告预览
├── 下载按钮
└── 演练统计图表

设置页面 (page_settings)
├── Prometheus 配置
├── Kubernetes 配置
├── Chaos Mesh 开关
└── 通知配置
```

#### 状态管理

使用 Streamlit Session State 管理应用状态：

```python
st.session_state = {
    'drill_history': [],        # 演练历史
    'current_drill': None,      # 当前演练
    'chaos_injector': None,     # 故障注入器实例
    'monitor_checker': None,    # 监控验证器实例
}
```

---

## 数据流

### 完整演练流程数据流

```
┌──────────┐
│  用户    │
└────┬─────┘
     │ 1. 选择场景
     ▼
┌──────────────┐
│   Web UI     │
└────┬─────────┘
     │ 2. 加载配置
     ▼
┌──────────────┐
│ 场景配置文件  │
│ (YAML)       │
└────┬─────────┘
     │ 3. 解析配置
     ▼
┌──────────────┐
│ChaosInjector │
└────┬─────────┘
     │ 4. 调用 K8s API
     ▼
┌──────────────┐
│ Kubernetes   │
│ / Chaos Mesh │
└────┬─────────┘
     │ 5. 执行故障注入
     ▼
┌──────────────┐
│  目标 Pod    │
└────┬─────────┘
     │ 6. 产生故障
     ▼
┌──────────────┐
│ Prometheus   │
│ (采集指标)    │
└────┬─────────┘
     │ 7. 触发告警
     ▼
┌──────────────┐
│MonitorChecker│
└────┬─────────┘
     │ 8. 查询告警
     ▼
┌──────────────┐
│ Prometheus   │
│ API          │
└────┬─────────┘
     │ 9. 返回告警数据
     ▼
┌──────────────┐
│ReportGenerator│
└────┬─────────┘
     │ 10. 生成报告
     ▼
┌──────────────┐
│   Web UI     │
└────┬─────────┘
     │ 11. 展示结果
     ▼
┌──────────┐
│  用户    │
└──────────┘
```

### 配置文件数据流

```yaml
# scenarios/cpu_stress.yaml
scenario:
  name: "CPU 压测演练"
  type: "cpu_stress"
  description: "模拟 CPU 资源耗尽"

target:
  namespace: "default"
  pod_name: "nginx-*"

fault:
  duration: "60s"
  cpu:
    workers: 2
  memory:
    enabled: true
    size: "100Mi"

validation:
  alert_name: "HighCPUUsage"
  timeout: 120
```

---

## 技术选型

### 编程语言

**Python 3.8+**
- ✅ 丰富的生态系统
- ✅ Kubernetes 官方客户端支持
- ✅ 易于快速开发
- ✅ 适合运维自动化

### 核心依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| kubernetes | 28.1.0+ | Kubernetes API 客户端 |
| requests | 2.31.0+ | HTTP 请求（Prometheus API） |
| PyYAML | 6.0.1+ | YAML 配置解析 |
| streamlit | 1.29.0+ | Web UI 框架 |
| pandas | 2.0.0+ | 数据处理和展示 |
| pytest | 7.4.3+ | 测试框架 |

### 基础设施

**Kubernetes**
- 容器编排平台
- 提供声明式 API
- 强大的自愈能力

**Chaos Mesh**
- 云原生混沌工程平台
- 丰富的故障注入能力
- 声明式配置

**Prometheus**
- 时序数据库
- 强大的查询语言 (PromQL)
- 灵活的告警规则

---

## 安全设计

### 1. 权限控制

#### RBAC 配置

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: edap-role
rules:
# 只读权限
- apiGroups: [""]
  resources: ["pods", "services", "namespaces"]
  verbs: ["get", "list", "watch"]
# 故障注入权限（最小化）
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["delete"]
# Chaos Mesh 权限
- apiGroups: ["chaos-mesh.org"]
  resources: ["*"]
  verbs: ["create", "delete", "get", "list"]
```

### 2. 输入验证

**Kubernetes 资源名称验证**
```python
def validate_input(input_str, field_name, max_length=253):
    """验证输入符合 K8s 命名规范"""
    # 检查长度
    if len(input_str) > max_length:
        return False, f"{field_name}长度超限"

    # 检查格式（小写字母、数字、连字符）
    if not re.match(r'^[a-z0-9]([-a-z0-9]*[a-z0-9])?$', input_str):
        return False, f"{field_name}格式不合法"

    return True, ""
```

**路径遍历防护**
```python
def load_scenario(filename):
    """安全加载场景文件"""
    # 防止路径遍历
    if '..' in filename or '/' in filename:
        raise ValueError("非法文件名")

    # 验证文件在预期目录内
    abs_path = os.path.abspath(os.path.join('scenarios', filename))
    if not abs_path.startswith(os.path.abspath('scenarios')):
        raise ValueError("文件路径越界")

    return yaml.safe_load(open(abs_path))
```

### 3. 审计日志

所有故障注入操作都会记录详细日志：

```python
logger.info(f"故障注入开始: {scenario_type}")
logger.info(f"目标: {namespace}/{pod_name}")
logger.info(f"操作者: {user}")
logger.info(f"时间: {datetime.now()}")
```

### 4. 安全最佳实践

- ✅ 使用 `yaml.safe_load()` 而非 `yaml.load()`
- ✅ 所有外部输入都经过验证
- ✅ 敏感信息（密码）不记录到日志
- ✅ 使用 HTTPS 连接 Prometheus
- ✅ 支持 Prometheus 基本认证

---

## 扩展性设计

### 1. 添加新的故障场景

#### 步骤 1: 创建配置文件

```yaml
# scenarios/memory_leak.yaml
scenario:
  name: "内存泄漏演练"
  type: "memory_leak"
  description: "模拟应用内存泄漏"

target:
  namespace: "default"
  pod_name: "app-*"

fault:
  duration: "120s"
  leak_rate: "10Mi/s"

validation:
  alert_name: "HighMemoryUsage"
  timeout: 180
```

#### 步骤 2: 实现故障注入方法

```python
def inject_memory_leak(self, namespace, pod_name, leak_rate, duration):
    """注入内存泄漏故障"""
    # 实现逻辑
    pass
```

#### 步骤 3: 注册到配置解析器

```python
def inject_from_config(self, config_path):
    scenario_type = scenario.get('type')

    if scenario_type == 'memory_leak':
        return self.inject_memory_leak(...)
```

### 2. 集成新的监控系统

```python
class GrafanaClient:
    """Grafana 客户端"""

    def query_alerts(self):
        """查询 Grafana 告警"""
        pass

class MonitorChecker:
    def __init__(self, monitor_type='prometheus', ...):
        if monitor_type == 'prometheus':
            self.client = PrometheusClient(...)
        elif monitor_type == 'grafana':
            self.client = GrafanaClient(...)
```

### 3. 添加新的报告格式

```python
class ReportGenerator:
    def generate(self, data, format='markdown'):
        if format == 'markdown':
            return self._generate_markdown(data)
        elif format == 'html':
            return self._generate_html(data)
        elif format == 'pdf':
            return self._generate_pdf(data)
```

---

## 性能优化

### 1. 异步操作

使用异步 I/O 提升性能：

```python
import asyncio

async def inject_multiple_faults(self, targets):
    """并发注入多个故障"""
    tasks = [
        self.inject_fault_async(target)
        for target in targets
    ]
    return await asyncio.gather(*tasks)
```

### 2. 缓存机制

缓存 Kubernetes 资源查询结果：

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def get_pod_info(namespace, pod_name):
    """缓存 Pod 信息"""
    return v1.read_namespaced_pod(pod_name, namespace)
```

### 3. 批量操作

批量查询 Prometheus 指标：

```python
def query_multiple_metrics(self, queries):
    """批量查询指标"""
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(self.query_metrics, q)
            for q in queries
        ]
        return [f.result() for f in futures]
```

### 4. 资源限制

Web UI 容器资源配置：

```yaml
resources:
  requests:
    cpu: 100m
    memory: 256Mi
  limits:
    cpu: 500m
    memory: 512Mi
```

---

## 未来规划

### 短期目标 (1-3 个月)

- [ ] 容器化部署（Dockerfile）
- [ ] Helm Chart 打包
- [ ] Grafana 仪表板集成
- [ ] AlertManager 通知集成

### 中期目标 (3-6 个月)

- [ ] 多集群支持
- [ ] 定时演练（CronJob）
- [ ] 演练模板市场
- [ ] PDF 报告导出

### 长期目标 (6-12 个月)

- [ ] AI 驱动的故障场景推荐
- [ ] 自动化根因分析
- [ ] 演练效果评分系统
- [ ] 企业级权限管理

---

## 参考资料

- [Kubernetes 官方文档](https://kubernetes.io/docs/)
- [Chaos Mesh 文档](https://chaos-mesh.org/docs/)
- [Prometheus 文档](https://prometheus.io/docs/)
- [Streamlit 文档](https://docs.streamlit.io/)

---

**最后更新**: 2026-01-29
**版本**: v1.0.0
**作者**: 应急运维工程师
