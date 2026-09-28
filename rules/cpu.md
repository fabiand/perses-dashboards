# CPU Recording Rules

## Objective

CPU is a compressible resource - when exhausted, workloads are throttled rather than terminated. These recording rules measure CPU allocation and utilization to enable:

- **Capacity planning** - Understand allocation vs physical capacity
- **Performance optimization** - Detect CPU contention and throttling  
- **Overcommit management** - Track virtual CPU allocation in virtualized environments

## Concept

Recording rules pre-calculate CPU metrics using a consistent dimensional model. The core principle: **track both scope (system vs workloads) and utilization state (used vs free)**.

### Scopes

CPU resources are divided into two scopes:

| Scope | Purpose | Metrics |
|-------|---------|---------|
| `system` | Reserved for OS/hypervisor | count, seconds (utilized true/false) |
| `workloads` | Available for pods/VMs | count, seconds (utilized true/false), ratios |

### Utilization States

| State | Description |
|-------|-------------|
| `utilized="true"` | CPU seconds actively used |
| `utilized="false"` | CPU seconds available (free) |

## Recording Rule Structure

All rules use **colon hierarchy** (Prometheus convention):

```
openshift:node:cpu:count{scope, unit}
openshift:node:cpu:seconds{scope, utilized, unit}
openshift:node:cpu:utilization:ratio{scope, unit}
openshift:node:cpu:overcommit:ratio{scope, unit}
openshift:node:cpu:pressure:ratio{severity, unit}
openshift:cluster:cpu:count{scope, unit}
openshift:cluster:cpu:seconds{scope, utilized, unit}
openshift:cluster:cpu:utilization:ratio{scope, unit}
openshift:cluster:cpu:overcommit:ratio{scope, unit}
openshift:cluster:cpu:imbalance:ratio{scope, unit}
openshift:cluster:cpu:pressure:ratio{severity, unit}
openshift:vm:virtual:cpu:seconds{scope, unit}
openshift:vm:cpu:requested:count{unit}
openshift:vm:cpu:overcommit:ratio{unit}
```

### Label Dimensions

- **scope**: `system`, `workloads`, `virtual`
- **utilized**: `true` (used), `false` (free)
- **severity**: `some` (PSI severity level)
- **unit**: `count`, `seconds`, `ratio`

## Node-level Metrics

| Metric | Labels | Description |
|--------|--------|-------------|
| `openshift:node:cpu:count` | scope="system" | CPU cores reserved for system |
| `openshift:node:cpu:count` | scope="workloads" | CPU cores allocatable to workloads |
| `openshift:node:cpu:seconds` | scope="system", utilized="true" | System CPU usage (rate) |
| `openshift:node:cpu:seconds` | scope="system", utilized="false" | System CPU free |
| `openshift:node:cpu:seconds` | scope="workloads", utilized="true" | Workload CPU usage (rate) |
| `openshift:node:cpu:seconds` | scope="workloads", utilized="false" | Workload CPU free |
| `openshift:node:cpu:utilization:ratio` | scope="workloads" | Workload utilization (used/total) |
| `openshift:node:cpu:overcommit:ratio` | scope="workloads" | vCPU/pCPU ratio per node |
| `openshift:node:cpu:pressure:ratio` | severity="some" | CPU pressure (PSI) |
| `openshift:node:virtual:cpu:seconds` | scope="workloads" | Total vCPU seconds per node |

### Example

```promql
# System CPU cores reserved per node
openshift:node:cpu:count{scope="system"}

# Workload CPU usage per node
openshift:node:cpu:seconds{scope="workloads", utilized="true"}

# CPU pressure per node
openshift:node:cpu:pressure:ratio{severity="some"}
```

## Cluster-level Metrics

| Metric | Labels | Description |
|--------|--------|-------------|
| `openshift:cluster:cpu:count` | scope="system" | Total system CPU cores |
| `openshift:cluster:cpu:count` | scope="workloads" | Total workload CPU cores |
| `openshift:cluster:cpu:seconds` | scope="system", utilized="true" | Cluster system CPU usage |
| `openshift:cluster:cpu:seconds` | scope="system", utilized="false" | Cluster system CPU free |
| `openshift:cluster:cpu:seconds` | scope="workloads", utilized="true" | Cluster workload CPU usage |
| `openshift:cluster:cpu:seconds` | scope="workloads", utilized="false" | Cluster workload CPU free |
| `openshift:cluster:virtual:cpu:seconds` | scope="workloads" | Total cluster vCPU seconds |
| `openshift:cluster:cpu:utilization:ratio` | scope="workloads" | Cluster utilization (used/total) |
| `openshift:cluster:cpu:overcommit:ratio` | scope="virtual" | Cluster vCPU/pCPU ratio |
| `openshift:cluster:cpu:imbalance:ratio` | scope="workloads" | Coefficient of variation across nodes |
| `openshift:cluster:cpu:pressure:ratio` | severity="some" | Max CPU pressure across cluster |

### Example

```promql
# Total cluster workload CPU
openshift:cluster:cpu:count{scope="workloads"}

# Cluster CPU utilization
openshift:cluster:cpu:utilization:ratio{scope="workloads"}

# Cluster overcommit ratio
openshift:cluster:cpu:overcommit:ratio{scope="virtual"}
```

## VM-level Metrics

| Metric | Labels | Description |
|--------|--------|-------------|
| `openshift:vm:virtual:cpu:seconds` | scope="workloads" | vCPU count per VM |
| `openshift:vm:cpu:requested:count` | - | CPU cores requested by virt-launcher |
| `openshift:vm:cpu:overcommit:ratio` | - | VM vCPU/requested ratio |

### Example

```promql
# vCPUs for a specific VM
openshift:vm:virtual:cpu:seconds{name="my-vm", namespace="default"}

# CPU request for VM
openshift:vm:cpu:requested:count{name="my-vm", namespace="default"}
```

## Source Metrics

| Source Metric | Description |
|--------------|-------------|
| `kube_node_status_capacity{resource="cpu"}` | Physical CPU capacity per node |
| `kube_node_status_allocatable{resource="cpu"}` | CPU allocatable to workloads |
| `container_cpu_usage_seconds_total{id="/system.slice"}` | System CPU usage |
| `container_cpu_usage_seconds_total{id="/kubepods.slice"}` | Workload CPU usage |
| `node_pressure_cpu_waiting_seconds_total` | CPU pressure (PSI) |
| `kubevirt_vmi_vcpu_seconds_total` | VM vCPU count |
| `kube_pod_container_resource_requests{resource="cpu"}` | Container CPU requests |

## Ratio Interpretations

### Utilization Ratio

Fraction of CPU currently in use:

| Ratio Range | Interpretation |
|-------------|----------------|
| 0.0 - 0.7 | Healthy capacity |
| 0.7 - 0.85 | Monitor usage |
| > 0.85 | High utilization |

```promql
# Nodes with high utilization (>85%)
openshift:node:cpu:utilization:ratio{scope="workloads"} > 0.85
```

### Overcommit Ratio

vCPU allocation vs physical capacity:

| Ratio Range | Interpretation |
|-------------|----------------|
| 0.0 - 1.0 | No overcommit |
| 1.0 - 2.0 | Moderate overcommit (typical) |
| 2.0 - 4.0 | High overcommit |
| > 4.0 | Very high overcommit (performance risk) |

```promql
# Nodes with high overcommit (>2.0)
openshift:node:cpu:overcommit:ratio{scope="workloads"} > 2.0
```

### Imbalance Ratio

Coefficient of variation measuring workload distribution:

| Ratio Range | Interpretation |
|-------------|----------------|
| < 0.3 | Balanced distribution |
| 0.3 - 0.6 | Moderate imbalance |
| > 0.6 | High imbalance - rebalancing recommended |

```promql
# Check cluster CPU imbalance
openshift:cluster:cpu:imbalance:ratio{scope="workloads"}
```

### Pressure Ratio (PSI)

Fraction of time tasks are waiting for CPU:

| Ratio Range | Interpretation |
|-------------|----------------|
| < 0.1 | Low pressure |
| 0.1 - 0.3 | Moderate pressure |
| > 0.3 | High pressure (contention) |

```promql
# Nodes with high CPU pressure
openshift:node:cpu:pressure:ratio{severity="some"} > 0.3
```

## Common Queries

### Capacity Planning

```promql
# Total cluster CPU capacity
openshift:cluster:cpu:count{scope="workloads"}

# Used vs free
openshift:cluster:cpu:seconds{scope="workloads", utilized="true"}
openshift:cluster:cpu:seconds{scope="workloads", utilized="false"}
```

### Performance Analysis

```promql
# Per-node CPU utilization
openshift:node:cpu:utilization:ratio{scope="workloads"}

# Cluster-wide utilization
openshift:cluster:cpu:utilization:ratio{scope="workloads"}
```

### Overcommit Monitoring

```promql
# Total vCPUs vs physical CPUs
openshift:cluster:virtual:cpu:seconds{scope="workloads"}
/
openshift:cluster:cpu:count{scope="workloads"}
```

### Imbalance Detection

```promql
# Detect unbalanced CPU allocation
openshift:cluster:cpu:imbalance:ratio{scope="workloads"} > 0.6
```

## Important Notes

- **Rate windows**: All rate calculations use 2-minute windows `[2m]` for stability
- **Scope dimensions**: System and workloads are mutually exclusive; sum equals total capacity
- **Utilization state**: used + free = total for each scope
- **Virtual CPU tracking**: Counts vCPUs from kubevirt_vmi_vcpu_seconds_total
- **Cluster ratios**: Computed as `sum(numerator) / sum(denominator)` for capacity-weighted averages
