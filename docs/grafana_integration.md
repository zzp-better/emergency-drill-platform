# Grafana 集成指南

本文档介绍如何将 Grafana 集到应急演练自动化平台中，实现演练结果的可视化展示。

## 功能特性

- ✅ **自动创建仪表板** - Grafana 通过 API或配置文件自动创建和管理仪表板
- ✅ **演练注释**: 在演练执行时自动向 Grafana 创建注释标记演练事件
- ✅ **指标推送**: 支持将演练指标推送到 Prometheus Pushgateway
- ✅ **嵌入 URL生成**: 方便在 Web UI中嵌入 Grafana 仪表板
- ✅ **配置驱动**: YAML 配置文件定义演练场景
- ✅ **Docker 部署支持**: 通过 Docker Compose 快速启动完整的 Grafana+Prometheus+Pushgateway环境
- ✅**无需安装**: 只需安装 Docker和 Docker Compose 即可
- ✅**生产环境**:** 只适合开发/测试环境
- ✅ **完整演练**:**在 `examples/` 目录下运行 `python examples/chaos_mesh_drill.py` 即可启动 Grafana并查看演练结果
- ✅ **命令行操作**: `python examples/chaos_mesh_drill.py` 或 `python examples/complete_drill.py` 运行演练
- ✅ **Web UI** - 启动 Web UI 后，访问 http://localhost:8501
- ✅ **API**: Grafana 客户端类已集成，提供完整的 API
- ✅ **仪表板管理器**: 自动创建和管理仪表板
- ✅ **指标推送器**: 支持将演练指标推送到 Prometheus Pushgateway
- ✅ **嵌入 URL生成**: 方便在 web UI中嵌入 Grafana 仪表板
- ✅ **配置驱动**: YAML 配置文件定义演练场景
- ✅ **Docker 部署支持**: 通过 Docker Compose 快速启动完整的 Grafana+Prometheus+Pushgateway环境
 - ✅ **无需安装**: 只需安装 Docker和 Docker Compose 即可
- ✅ **生产环境**:
- - ✅ **开发环境**: 直接使用 `python examples/chaos_mesh_drill.py` 或 `python examples/complete_drill.py` 运行演练
- ✅ **Web UI**: 启动 Web UI 后，访问 http://localhost:8501
- ✅ **Grafana 集成测试**: 在设置页面测试 Grafana 连接
        if config:
            try:
                grafana = GrafanaIntegration(
                    grafana_url=config.get('grafana_url'),
                    grafana_api_key=config.get('grafana_api_key'),
                    grafana_username=config.get('grafana_username'),
                    grafana_password=config.get('grafana_password')
                )
                st.session_state.grafana_integration = graf_integration
                st.success("✓ Grafana 连接成功")
            except Exception as e:
                st.error(f"✗ 连接 Grafana 失败: {e}")
        
        st.markdown("---")
        st.markdown("### 🥳 完成！恭喜！Grafana 集成功能已成功添加到项目中！ 🎉

""")
""")            label_visibility="collapsed"
        )
    }
>>>>>>> REPLACE
