# 代码架构说明

## 当前架构

### 文件结构
```
emergency-drill-platform/
├── web_ui.py (3313行) - 主应用文件
├── src/
│   ├── chaos_injector.py - 故障注入器
│   ├── chaos_mesh_injector.py - Chaos Mesh 集成
│   ├── monitor_checker.py - 监控检查
│   ├── grafana_integration.py - Grafana 集成
│   ├── db.py - 数据库操作
│   ├── scheduler.py - 定时调度器（已拆分）
│   └── drill_executor.py - 演练执行器（已拆分）
```

## 已完成的优化

### 1. 调度器模块化 (src/scheduler.py)
- 将 APScheduler 相关逻辑独立
- 负责定时演练任务管理
- 约 150 行代码

### 2. 执行器模块化 (src/drill_executor.py)
- 将演练执行逻辑独立
- 负责后台任务执行和进度跟踪
- 约 170 行代码

## 建议的进一步优化（未实施）

### 为什么暂未实施
1. **风险控制**：大规模重构可能引入 bug
2. **时间成本**：需要完整测试所有功能
3. **当前可用**：现有代码已经能正常工作

### 优化方案

#### 方案一：UI 页面拆分
```
src/ui/
├── pages/
│   ├── home.py - 首页
│   ├── drill.py - 演练执行
│   ├── monitor.py - 监控验证
│   ├── reports.py - 报告查看
│   ├── chain_drill.py - 故障链
│   ├── cluster.py - 集群资源
│   └── settings.py - 系统设置
├── components/
│   ├── sidebar.py - 侧边栏组件
│   └── metrics.py - 指标卡片
└── styles.py - CSS 样式
```

#### 方案二：业务逻辑分层
```
src/
├── core/ - 核心业务逻辑
│   ├── drill_executor.py ✓ (已完成)
│   ├── scheduler.py ✓ (已完成)
│   └── notification.py - 通知服务
├── ui/ - UI 层
│   └── pages/ - 页面组件
└── utils/ - 工具函数
    ├── report_generator.py - 报告生成
    └── helpers.py - 辅助函数
```

## 面试说明要点

### 技术亮点
1. **混沌工程实践**：Chaos Mesh CRD 操作
2. **并发控制**：threading.Lock 保护共享状态
3. **定时任务**：APScheduler + Cron 表达式
4. **数据持久化**：SQLite + 历史记录
5. **容器化部署**：Docker + Kubernetes

### 已知改进点
1. **代码组织**：web_ui.py 过大，应拆分为多个模块
2. **测试覆盖**：缺少单元测试和集成测试
3. **错误处理**：部分异常处理可以更细致
4. **日志系统**：应使用 logging 模块替代 print

### 如果有更多时间
- 完成 UI 页面模块化拆分
- 添加单元测试（pytest）
- 实现 CI/CD 流水线
- 添加 API 文档（OpenAPI）
- 性能优化和缓存机制
