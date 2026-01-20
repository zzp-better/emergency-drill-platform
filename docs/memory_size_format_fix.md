# Chaos Mesh 内存大小格式修复说明

## 问题描述

在使用 Chaos Mesh 的 StressChaos 注入 CPU/内存压测故障时，出现以下错误：

```
Kubernetes API 错误: 403 - Forbidden - admission webhook "vstresschaos.kb.io" denied the request:
Spec.Stressors.MemoryStressor.Size: Invalid value: "100Mi": incorrect bytes format: invalid suffix: 'mi'
```

## 根本原因

Chaos Mesh 的 StressChaos 资源要求内存大小使用**纯字节数**（不带单位），而不是 Kubernetes 标准的单位格式（`Mi`, `Gi`, `mi`, `gi`）。

之前的代码将用户输入的内存大小转换为带单位的格式（如 `100Mi` 或 `100mi`），但这不符合 Chaos Mesh 的要求。

## 修复方案

### 1. 修改内存大小转换逻辑

**文件**: `src/chaos_injector.py` 和 `src/chaos_mesh_injector.py`

修改前：
```python
# 将小写单位转换为大写
memory_size = memory_size.lower()
if memory_size.endswith('mi'):
    memory_size = memory_size[:-2] + 'Mi'
elif memory_size.endswith('gi'):
    memory_size = memory_size[:-2] + 'Gi'
```

修改后：
```python
# Chaos Mesh StressChaos 期望的字节格式（不带单位）
memory_size = memory_size.lower()

# 转换为字节数
if memory_size.endswith('mi') or memory_size.endswith('mb'):
    # Mebibyte/Megabyte -> 字节 (1 Mi = 1024 * 1024 = 1048576 bytes)
    num = int(memory_size[:-2])
    memory_size = str(num * 1024 * 1024)
elif memory_size.endswith('gi') or memory_size.endswith('gb'):
    # Gibibyte/Gigabyte -> 字节 (1 Gi = 1024 * 1024 * 1024 = 1073741824 bytes)
    num = int(memory_size[:-2])
    memory_size = str(num * 1024 * 1024 * 1024)
elif memory_size.endswith('ki') or memory_size.endswith('kb'):
    # Kibibyte/Kilobyte -> 字节 (1 Ki = 1024 bytes)
    num = int(memory_size[:-2])
    memory_size = str(num * 1024)
# 如果是纯数字，假设已经是字节数
```

### 2. 更新 YAML 配置文件

**文件**: `scenarios/cpu_stress.yaml` 和 `scenarios/disk_io.yaml`

将内存大小从带单位的格式改为纯字节数：
- `100Mi` → `104857600` (100 * 1024 * 1024)
- `1Gi` → `1073741824` (1 * 1024 * 1024 * 1024)

### 3. 更新示例代码

**文件**: `examples/chaos_mesh_drill.py` 和 `examples/quick_test.py`

示例代码使用人类可读的单位格式（如 `100Mi`, `1Gi`），代码会自动转换为字节数。

### 4. 更新文档字符串

更新所有相关函数的文档字符串，说明会自动转换为字节数。

## 正确的内存大小格式

### 用户输入格式（自动转换）

代码支持以下输入格式，会自动转换为字节数：

| 输入格式 | 转换结果 | 说明 |
|---------|---------|------|
| `100Mi` | `104857600` | Mebibyte (二进制) |
| `100mi` | `104857600` | Mebibyte (二进制) |
| `100MB` | `104857600` | Megabyte (十进制) |
| `100mb` | `104857600` | Megabyte (十进制) |
| `1Gi` | `1073741824` | Gibibyte (二进制) |
| `1gi` | `1073741824` | Gibibyte (二进制) |
| `1GB` | `1073741824` | Gigabyte (十进制) |
| `1gb` | `1073741824` | Gigabyte (十进制) |
| `1024ki` | `1048576` | Kibibyte (二进制) |
| `1024kb` | `1048576` | Kilobyte (十进制) |
| `104857600` | `104857600` | 纯字节数（直接使用） |

### Chaos Mesh API 格式

Chaos Mesh StressChaos 的 `size` 字段期望的是纯字节数（字符串类型），不带任何单位。

## 使用示例

```python
# CPU 压测 - 使用人类可读的单位格式
injector.inject_cpu_stress(
    namespace="default",
    pod_name="nginx-test-xxx",
    cpu_count=2,
    memory_size="100Mi",  # 会自动转换为 104857600
    duration="60s"
)

# 磁盘填充 - 使用人类可读的单位格式
injector.inject_disk_failure(
    namespace="default",
    pod_name="nginx-test-xxx",
    path="/var/log",
    fault_type="disk_fill",
    size="1Gi",  # 会自动转换为 1073741824
    duration="60s"
)

# 直接使用字节数
injector.inject_cpu_stress(
    namespace="default",
    pod_name="nginx-test-xxx",
    cpu_count=2,
    memory_size="104857600",  # 直接使用字节数
    duration="60s"
)
```

## 兼容性说明

代码现在会自动处理以下输入格式：
- `100Mi` → `104857600`
- `100mi` → `104857600`
- `100MB` → `104857600`
- `100mb` → `104857600`
- `1Gi` → `1073741824`
- `1gi` → `1073741824`
- `1GB` → `1073741824`
- `1gb` → `1073741824`
- `104857600` → `104857600`（保持不变，假设已经是字节数）

## 常用转换参考

| 单位 | 字节数 |
|------|--------|
| 1 Ki/Ki | 1024 |
| 1 Mi/Mi | 1,048,576 |
| 1 Gi/Gi | 1,073,741,824 |
| 1 Ti/Ti | 1,099,511,627,776 |

## 相关文档

- [Chaos Mesh StressChaos 文档](https://chaos-mesh.org/docs/chaos-mesh/stresschaos/)
- [Kubernetes 资源单位](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/#resource-units-in-kubernetes)
