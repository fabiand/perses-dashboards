# CPU Recording Rules

## Objective

CPU is a compressible resource - when exhausted, workloads are throttled rather than terminated. Monitoring CPU allocation and utilization is critical for:

- **Capacity planning** - Understand allocation vs physical capacity
- **Performance optimization** - Detect CPU contention and throttling
- **Overcommit management** - Track virtual CPU allocation in virtualized environments

## Concept

Recording rules pre-calculate CPU metrics to simplify dashboard queries and provide consistent accounting. The core principle: **track both scope (system vs workloads) and utilization state (used vs free)**.

Multiple dimensions slice CPU resources to address different operational needs:
- **Scope** - allocation boundary (system, workloads, virtual)
- **Utilization** - usage state (used, free)
- **Level** - aggregation (node, cluster, VM)

Each dimension provides a different lens on the same physical CPU capacity.

# Nodes

Node-level recording rules aggregate CPU metrics for each node, providing per-node visibility into CPU consumption and availability.

### Scopes

CPU resources are divided into scopes based on allocation boundaries:

| Scope | Purpose | Calculation |
|-------|---------|-------------|
| `system` | Reserved for OS/hypervisor | Capacity - Allocatable |
| `workloads` | Available for pods/VMs | Allocatable |
| `virtual` | Virtual CPUs from VMs | Count of vCPUs |

Where:
- **System**: `kube_node_status_capacity{resource="cpu"}` - `kube_node_status_allocatable{resource="cpu"}`
- **Workloads**: `kube_node_status_allocatable{resource="cpu"}`
- **Virtual**: Count from `kubevirt_vmi_vcpu_seconds_total`

#### Example

```promql
# System CPU cores reserved per node
openshift:node:cpu:count{scope="system"}

# Workload CPU cores per node
openshift:node:cpu:count{scope="workloads"}
```

### Utilization States

CPU seconds (rate-based metrics) are categorized by utilization state:

| State | Description |
|-------|-------------|
| `utilized="true"` | CPU seconds actively used (from cgroup usage) |
| `utilized="false"` | CPU seconds available (count - used) |

The free CPU represents headroom between current usage and allocated capacity.

#### Example

```promql
# CPU seconds in use (workloads)
openshift:node:cpu:seconds{scope="workloads", utilized="true"}

# CPU seconds available (workloads)
openshift:node:cpu:seconds{scope="workloads", utilized="false"}
```

### Ratios

Node-level ratios track CPU efficiency and allocation:

| Ratio | Formula | Purpose | Typical Range |
|-------|---------|---------|---------------|
| `utilization` | utilized / (utilized + free) | Fraction of CPU in use | 0.0 - 1.0 |
| `overcommit` | virtual CPU / workload CPU | vCPU/pCPU ratio | > 1.0 (normal for VMs) |
| `pressure` | rate(node_pressure_cpu_waiting_seconds) | Fraction of time waiting for CPU | < 0.1 (healthy) |

#### Utilization Ratio

Tracks how much of the node's workload CPU is currently in use:

```promql
openshift:node:cpu:utilization:ratio{scope="workloads"}
```

Calculated as:
```
openshift:node:cpu:seconds{scope="workloads", utilized="true"}
/
openshift:node:cpu:seconds{scope="workloads"}
```

Values approaching 1.0 indicate the node is consuming most of its CPU and may need more capacity or workload reduction.

#### Overcommit Ratio

Tracks virtual CPU assigned to VMs vs physical CPU allocated:

```promql
openshift:node:cpu:overcommit:ratio{scope="workloads"}
```

Calculated as:
```
sum by (node) (openshift:vm:virtual:cpu:seconds{scope="workloads"})
/
openshift:node:cpu:count{scope="workloads"}
```

**Overcommit values > 1.0 are normal** because VMs are assigned virtual CPUs that share physical cores. However, high overcommit ratios increase throttling risk if VMs become CPU-intensive.

#### Pressure Ratio

Tracks CPU contention using Pressure Stall Information (PSI):

```promql
openshift:node:cpu:pressure:ratio{severity="some"}
```

Calculated as:
```
rate(node_pressure_cpu_waiting_seconds_total[2m])
```

Shows the fraction of time tasks are waiting for CPU to become available. Values > 0.1 indicate contention even if utilization looks acceptable.

### Recording Rules

Node-specific recording rules:

```
openshift:node:cpu:count{scope="system|workloads", unit="count"}
openshift:node:cpu:seconds{scope="system|workloads", utilized="true|false", unit="seconds"}
openshift:node:cpu:utilization:ratio{scope="workloads", unit="ratio"}
openshift:node:cpu:overcommit:ratio{scope="workloads", unit="ratio"}
openshift:node:cpu:pressure:ratio{severity="some", unit="ratio"}
openshift:node:virtual:cpu:seconds{scope="workloads", unit="seconds"}
```

### Label Dimensions

- **scope**: `system`, `workloads`, `virtual`
- **utilized**: `true` (used), `false` (free)
- **severity**: `some` (PSI severity level)
- **unit**: `count`, `seconds`, `ratio`

Note: CPU metrics do not use tiers (unlike memory). All CPU is the same technology.

# Cluster

Cluster-level recording rules aggregate across all nodes, providing cluster-wide visibility into CPU consumption and availability.

### Scopes

Cluster aggregations sum node-level metrics:

| Scope | Formula | Purpose |
|-------|---------|---------|
| `system` | sum(node system) | Total system CPU |
| `workloads` | sum(node workloads) | Total workload CPU |
| `virtual` | sum(node virtual) | Total vCPUs |

#### Example

```promql
# Total cluster workload CPU
openshift:cluster:cpu:count{scope="workloads"}

# Total cluster vCPUs
openshift:cluster:virtual:cpu:seconds{scope="workloads"}
```

### Ratios

Cluster-level ratios provide cluster-wide health metrics:

| Ratio | Formula | Purpose |
|-------|---------|---------|
| `utilization` | sum(node utilized) / sum(node total) | Cluster-wide utilization |
| `overcommit` | sum(virtual) / sum(workloads) | Cluster vCPU/pCPU ratio |
| `imbalance` | p80 quantile of percentage point distance from mean pressure | Pressure balance across nodes - 80% of nodes within this many pp of mean pressure |
| `pressure` | max(node pressure) | Worst-case node contention |

#### Utilization Ratio

Tracks cluster-wide CPU utilization:

```promql
openshift:cluster:cpu:utilization:ratio{scope="workloads"}
```

Calculated as:
```
sum(openshift:node:cpu:seconds{scope="workloads", utilized="true"})
/
sum(openshift:node:cpu:seconds{scope="workloads"})
```

**Important**: Cannot average per-node ratios. Must compute `sum(numerator) / sum(denominator)` for capacity-weighted cluster-wide ratios.

#### Overcommit Ratio

Tracks cluster-wide vCPU/pCPU ratio:

```promql
openshift:cluster:cpu:overcommit:ratio{scope="virtual"}
```

Calculated as:
```
sum(openshift:cluster:virtual:cpu:seconds)
/
sum(openshift:cluster:cpu:seconds)
```

Values > 1.0 indicate overcommit. Values > 2.0 may cause contention under load.

#### Imbalance Ratio

Measures how evenly CPU pressure is distributed across nodes using p80 quantile of percentage point distance from mean:

```promql
openshift:cluster:cpu:imbalance:distance:p80{scope="workloads"}
```

Calculated as:
```
quantile(0.80,
  abs(
    openshift:node:cpu:pressure:ratio{severity="some"}
    -
    scalar(avg(openshift:node:cpu:pressure:ratio{severity="some"}))
  )
)
```

Shows the spread: 80% of nodes are within this many percentage points of the mean pressure.

**Interpretation**:
- < 0.11 (±11pp): Healthy balanced distribution
- 0.11 - 0.22: Unhealthy balance
- 0.22 - 0.33: Severely unbalanced
- > 0.33: Critically unbalanced - rebalancing recommended

**Why pressure instead of utilization**: Pressure imbalance is more actionable than utilization imbalance. High utilization without pressure is healthy (CPUs are being used efficiently), but pressure always indicates contention. Measuring pressure imbalance shows where the actual bottlenecks are.

**Design rationale**: This metric uses simple, direct language that anyone can understand without a statistics background. Previously we used Coefficient of Variation (stddev/mean), which is mathematically sound but difficult to interpret for most users - what does a CV of 0.45 actually mean in practice? The p80 distance metric gives you an immediately actionable number: 0.22 means "80% of your nodes are within ±22 percentage points of the mean." No mental math, no statistical knowledge required - you can instantly visualize whether your cluster is balanced or not.

#### Pressure Ratio

Shows worst-case CPU contention across the cluster:

```promql
openshift:cluster:cpu:pressure:ratio{severity="some"}
```

Calculated as:
```
max(openshift:node:cpu:pressure:ratio{severity="some"})
```

Shows the maximum pressure across all nodes. Even if cluster utilization is moderate, high pressure on one node indicates a problem.

### Recording Rules

Cluster-specific recording rules:

```
openshift:cluster:cpu:count{scope="system|workloads", unit="count"}
openshift:cluster:cpu:seconds{scope="system|workloads", utilized="true|false", unit="seconds"}
openshift:cluster:virtual:cpu:seconds{scope="workloads", unit="seconds"}
openshift:cluster:cpu:utilization:ratio{scope="workloads", unit="ratio"}
openshift:cluster:cpu:overcommit:ratio{scope="virtual", unit="ratio"}
openshift:cluster:cpu:imbalance:distance:p80{scope="workloads", unit="ratio"}
openshift:cluster:cpu:pressure:ratio{severity="some", unit="ratio"}
```

# VMs

VM-level recording rules track CPU metrics for individual virtual machines running on KubeVirt, providing per-VM visibility into CPU allocation and overcommit behavior.

Unlike node-level metrics that aggregate across all workloads, VM metrics expose each virtual machine's CPU usage with **per-VM cardinality** using `{name, namespace, node}` labels.

### Virtual CPUs

VMs are assigned virtual CPUs that share physical cores:

```promql
# vCPU count per VM
openshift:vm:virtual:cpu:seconds{scope="workloads"}
```

Calculated from:
```
count by (name, namespace, node) (kubevirt_vmi_vcpu_seconds_total)
```

### Requested CPUs

VMs request physical CPU cores through the virt-launcher pod:

```promql
# CPU cores requested by VM
openshift:vm:cpu:requests:count
```

Calculated from:
```
sum by (name, namespace, node) (
  kube_pod_container_resource_requests{resource="cpu", pod=~"virt-launcher-.*"}
)
```

### Overcommit Ratio

Tracks virtual CPU vs physical allocation per VM:

```promql
openshift:vm:cpu:overcommit:ratio
```

Calculated as:
```
openshift:vm:virtual:cpu:seconds
/
openshift:vm:cpu:requests:count
```

**Overcommit values > 1.0 are normal** for VMs. A VM with 4 vCPUs and 2 physical cores has overcommit ratio of 2.0.

### Recording Rules

VM-specific recording rules:

```
openshift:vm:virtual:cpu:seconds{scope="workloads", unit="seconds"}
openshift:vm:cpu:requests:count{unit="count"}
openshift:vm:cpu:overcommit:ratio{unit="ratio"}
```

### Label Dimensions

VM metrics use these label dimensions:

- **name**: VM name (from `kubevirt_vmi_info`)
- **namespace**: Kubernetes namespace containing the VM
- **node**: Host node running the VM
- **scope**: `workloads` (all VM CPU is implicitly workload)
- **unit**: `count`, `seconds`, `ratio`

### Query Patterns

#### Per-VM CPU Allocation

Track CPU allocation for specific VMs:

```promql
# vCPUs for a VM
openshift:vm:virtual:cpu:seconds{name="my-vm", namespace="default"}

# Physical CPU requested
openshift:vm:cpu:requests:count{name="my-vm", namespace="default"}
```

#### VM Overcommit Tracking

Monitor virtual vs physical allocation:

```promql
# Per-VM overcommit
openshift:vm:cpu:overcommit:ratio

# VMs with high overcommit (>3.0)
openshift:vm:cpu:overcommit:ratio > 3.0
```

High overcommit ratios are normal but increase throttling risk if the VM becomes CPU-intensive.

#### Aggregate VM CPU per Node

Total CPU consumed by all VMs on a node:

```promql
# Total vCPUs per node
sum by (node) (openshift:vm:virtual:cpu:seconds{scope="workloads"})
```

Understand VM footprint on each host node for capacity planning.

### Key Differences from Node Metrics

| Aspect | Nodes | VMs |
|--------|-------|-----|
| **Cardinality** | Per-node aggregates | Per-VM granularity |
| **Labels** | `{node, scope, ...}` | `{name, namespace, node, scope, ...}` |
| **Scope** | `system` vs `workloads` | No scope (implicitly workloads) |
| **Capacity** | Node allocatable CPU | VM requested cores (pod requests) |
| **Overcommit** | Tracked at node level | Tracked per-VM (virtual vs physical) |
| **Data Source** | cgroup metrics for system/kubepods slices | kubevirt_vmi metrics and pod requests |

**Key Insight**: VM metrics expose per-workload CPU behavior while node metrics show system-wide resource availability. VM overcommit approaching high values signals an individual VM may experience throttling. Node utilization approaching 1.0 signals the entire node is running out of CPU.

## Source Metrics

The recording rules are built from these base metrics:

| Source Metric | Description |
|--------------|-------------|
| `kube_node_status_capacity{resource="cpu"}` | Physical CPU capacity per node |
| `kube_node_status_allocatable{resource="cpu"}` | CPU allocatable to workloads |
| `container_cpu_usage_seconds_total{id="/system.slice"}` | System CPU usage (rate) |
| `container_cpu_usage_seconds_total{id="/kubepods.slice"}` | Workload CPU usage (rate) |
| `node_pressure_cpu_waiting_seconds_total` | CPU pressure (PSI) |
| `kubevirt_vmi_vcpu_seconds_total` | VM vCPU count |
| `kube_pod_container_resource_requests{resource="cpu"}` | Container CPU requests |
| `kubevirt_vmi_info` | VM metadata (name, namespace, pod mapping) |

## Important Notes

- **Rate windows**: All rate calculations use 2-minute windows `[2m]` for stability
- **Scope dimensions**: System and workloads are mutually exclusive; sum equals total capacity
- **Utilization state**: used + free = total for each scope
- **Virtual CPU tracking**: Counts vCPUs from kubevirt_vmi_vcpu_seconds_total
- **Cluster ratios**: Computed as `sum(numerator) / sum(denominator)` for capacity-weighted averages
- **No tiers**: Unlike memory, CPU does not have tier dimensions (all CPU is same technology)
