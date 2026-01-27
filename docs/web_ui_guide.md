# Web UI 使用指南

## 概述

应急演练自动化平台现已提供基于 Streamlit 的 Web UI，提供可视化的操作界面，无需使用命令行即可完成应急演练。

## 快速启动

### 1. 安装依赖

```bash
cd emergency-drill-platform
pip install -r requirements.txt
```

### 2. 启动 Web UI

```bash
streamlit run web_ui.py
```

### 3. 访问界面

启动后会自动打开浏览器，或手动访问：
- 本地访问：http://localhost:8501
- 网络访问：http://<你的IP>:8501

## 功能模块

### 🏠 首页

展示平台概览信息：
- 演练次数统计
- 可用场景数量
- 演练成功率
- 演练历史记录

**快速操作**：
- 📋 开始故障注入演练
- 📊 查看监控告警

---

### ⚡ 故障注入

提供可视化的故障注入操作：

**功能**：
1. 选择故障场景（从 scenarios/ 目录加载）
2. 配置参数：
   - 命名空间
   - Pod 名称
   - 超时时间
   - 检查间隔
3. 一键执行演练
4. 实时显示演练进度
5. 展示演练结果

**支持的故障场景**：
- Pod 崩溃（PodCrash）
- CPU 压测（CPUStress）
- 网络延迟（NetworkDelay）
- 磁盘 IO 故障（DiskIO）

---

### 📊 监控验证

查询和验证 Prometheus 告警：

**功能**：
1. 配置 Prometheus 连接：
   - Prometheus URL
   - 用户名/密码（可选）
2. 告警查询：
   - 按告警名称查询
   - 设置等待超时时间
3. 实时告警刷新
4. 告警详情展示

**告警信息**：
- 告警名称
- 严重级别（warning/critical）
- 状态（firing/pending）
- 描述信息
- 标签（namespace、pod 等）

---

### 📄 演练报告

查看和下载演练报告：

**功能**：
1. 报告列表展示
2. 报告内容预览（Markdown 格式）
3. 报告下载功能
4. 演练统计：
   - 总演练次数
   - 平均耗时
   - 成功率
5. 场景分布图表

**报告存储位置**：
- `reports/` 目录
- 格式：Markdown (.md)

---

### ⚙️ 设置

配置平台参数：

**Prometheus 配置**：
- Prometheus URL
- 用户名/密码

**Kubernetes 配置**：
- Kubeconfig 路径
- 默认命名空间

**通知配置**（可选）：
- 启用通知
- Webhook URL
- 通知事件选择

---

## 使用示例

### 示例 1：执行 Pod 崩溃演练

1. 打开 Web UI
2. 点击侧边栏「⚡ 故障注入」
3. 选择「Pod 崩溃 - 模拟应用崩溃」场景
4. 配置参数：
   - 命名空间：default
   - Pod 名称：nginx-deployment-xxx
   - 超时时间：60 秒
5. 点击「🚀 开始演练」
6. 查看演练结果

### 示例 2：查询告警

1. 点击侧边栏「📊 监控验证」
2. 输入告警名称：PodCrashLooping
3. 点击「🔍 查询告警」
4. 查看告警详情

### 示例 3：查看演练报告

1. 点击侧边栏「📄 演练报告」
2. 展开报告查看详情
3. 点击「📥 下载报告」保存到本地

---

## 技术架构

```
Web UI (Streamlit)
    │
    ├── 故障注入模块 → Chaos Mesh / K8s API
    ├── 监控验证模块 → Prometheus API
    └── 报告生成模块 → Markdown
```

---

## 常见问题

### Q: Web UI 无法启动？

A: 检查以下几点：
1. 确认已安装 streamlit：`pip install streamlit`
2. 检查端口 8501 是否被占用
3. 查看终端错误信息

### Q: 场景列表为空？

A: 检查 scenarios/ 目录是否存在且包含 .yaml 配置文件。

### Q: Prometheus 连接失败？

A: 检查以下几点：
1. Prometheus URL 是否正确
2. 网络是否可达
3. 是否需要认证（用户名/密码）

### Q: 如何停止 Web UI？

A: 在终端按 `Ctrl + C` 停止 Streamlit 服务。

---

## 后续开发计划

- [ ] 集成真实的故障注入和监控验证逻辑
- [ ] 支持批量演练执行
- [ ] 添加演练模板功能
- [ ] 支持导出 PDF 报告
- [ ] 添加用户认证和权限管理
- [ ] 支持多语言（中英文）

---

## 相关文档

- [快速入门指南](quick_start.md)
- [Chaos Mesh 集成指南](chaos_mesh_guide.md)
- [README](../README.md)
