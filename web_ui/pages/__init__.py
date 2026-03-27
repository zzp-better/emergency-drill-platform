"""
页面模块包
包含所有页面的渲染函数
"""

from .home import render as render_home
from .cluster_resources import render as render_cluster_resources
from .fault_injection import render as render_fault_injection


# 页面名称到渲染函数的映射
PAGE_RENDERERS = {
    'home': render_home,
    'cluster_resources': render_cluster_resources,
    'fault_injection': render_fault_injection,
}


def get_page_renderer(page_name: str):
    """获取页面渲染函数"""
    return PAGE_RENDERERS.get(page_name)


