# CPU Recording Rules

## Objective

CPU is a compressible resource - when exhausted, workloads are throttled rather than terminated. Monitoring CPU allocation and utilization is critical for:

- **Capacity planning** - Understand allocation vs physical capacity
- **Performance optimization** - Detect CPU contention and throttling
- **Overcommit management** - Track virtual CPU allocation in virtualized environments

## Concept

Recording rules pre-calculate CPU metrics to simplify dashboard queries and provide consistent accounting. The core principle: **track both physical and virtual CPU dimensions separately**.

Multiple dimensions slice CPU resources to address different operational needs:
- **Scope** - allocation boundary (physical, system, workloads, virtual)
- **Level** - aggregation (node, cluster, VM)
- **Metric type** - capacity, allocation, utilization, overcommit

### Scopes

CPU resources are divided into multiple scopes:

| Scope | Description | Metrics |
|-------|-------------|---------|
| `physical` | Physical CPU cores on the node | Capacity count |
| `system` | CPU reserved for OS/hypervisor | Reserved count |
| `workloads` | CPU available for pods/VMs | Allocatable, utilization |
| `virtual` | Virtual CPUs (vCPUs) from VMs | vCPU count, overcommit ratio |

#### Example

```promql
# Physical CPU capacity per node
openshift:node:cpu:capacity:count{scope="physical"}

# CPU available for workloads
openshift:node:cpu:allocatable:count{scope="workloads"}

# Virtual CPU count (VMs)
openshift:node:cpu:vcpu:count{scope="virtual"}
```

### Node-level Metrics

Node-level metrics provide per-node CPU visibility:

| Metric | Labels | Description |
|--------|--------|-------------|
| `openshift:node:cpu:capacity:count` | scope="physical" | Total physical CPU cores |
| `openshift:node:cpu:allocatable:count` | scope="workloads" | CPU available for workloads |
| `openshift:node:cpu:reserved:count` | scope="system" | CPU reserved for system |
| `openshift:node:cpu:vcpu:count` | scope="virtual" | Total vCPUs from VMs |
| `openshift:node:cpu:overcommit:ratio` | scope="virtual" | vCPU/pCPU ratio |
| `openshift:node:cpu:utilization:ratio` | scope="workloads" | Requested/Allocatable |
| `openshift:node:cpu:allocation:ratio` | scope="workloads" | Allocated/Allocatable |

#### Example

```promql
# CPU capacity on a specific node
openshift:node:cpu:capacity:count{scope="physical", node="worker-1"}

# vCPU overcommit ratio (>1.0 means overcommitted)
openshift:node:cpu:overcommit:ratio{scope="virtual", node="worker-1"}
```

### Cluster-level Metrics

Cluster-level metrics aggregate across all nodes:

| Metric | Labels | Description |
|--------|--------|-------------|
| `openshift:cluster:cpu:capacity:count` | scope="physical" | Total cluster pCPUs |
| `openshift:cluster:cpu:allocatable:count` | scope="workloads" | Total allocatable CPUs |
| `openshift:cluster:cpu:reserved:count` | scope="system" | Total reserved CPUs |
| `openshift:cluster:cpu:vcpu:count` | scope="virtual" | Total cluster vCPUs |
| `openshift:cluster:cpu:overcommit:ratio` | scope="virtual" | Cluster vCPU/pCPU ratio |
| `openshift:cluster:cpu:utilization:ratio` | scope="workloads" | Cluster CPU utilization |
| `openshift:cluster:cpu:imbalance:ratio` | scope="workloads" | Allocation imbalance metric |

#### Example

```promql
# Total cluster CPU capacity
openshift:cluster:cpu:capacity:count{scope="physical"}

# Cluster-wide overcommit ratio
openshift:cluster:cpu:overcommit:ratio{scope="virtual"}
```

### VM-level Metrics

VM-level metrics track individual VM CPU allocation:

| Metric | Labels | Description |
|--------|--------|-------------|
| `openshift:vm:cpu:vcpu:count` | - | vCPUs allocated to VM |
| `openshift:vm:cpu:requested:count` | - | CPU cores requested by virt-launcher |
| `openshift:vm:cpu:allocation:ratio` | - | VM CPU allocation ratio |

#### Example

```promql
# vCPUs for a specific VM
openshift:vm:cpu:vcpu:count{name="my-vm", namespace="default"}

# CPU request for VM
openshift:vm:cpu:requested:count{name="my-vm", namespace="default"}
```

### NUMA Topology Metrics

NUMA topology metrics provide CPU distribution across NUMA nodes (when available):

| Metric | Labels | Description |
|--------|--------|-------------|
| `openshift:node:cpu:numa:count` | scope="physical", numa_node | CPUs per NUMA node |
| `openshift:node:numa:node_count:count` | - | Total NUMA nodes per node |

**Note:** NUMA metrics require `node_cpu_info` or similar metrics with NUMA topology labels. Availability depends on node exporters.

#### Example

```promql
# CPUs in NUMA node 0
openshift:node:cpu:numa:count{scope="physical", node="worker-1", numa_node="0"}

# Count of NUMA nodes
openshift:node:numa:node_count:count{node="worker-1"}
```

## Source Metrics

The recording rules are built from these base metrics:

| Source Metric | Description |
|--------------|-------------|
| `kube_node_status_capacity{resource="cpu"}` | Physical CPU capacity per node |
| `kube_node_status_allocatable{resource="cpu"}` | CPU allocatable to workloads |
| `kube_pod_container_resource_requests{resource="cpu"}` | CPU requests per container |
| `kube_pod_info` | Pod to node mapping |
| `kubevirt_vmi_info` | VM instance information |
| `kubevirt_vmi_vcpu_seconds` | VM vCPU usage (used for counting vCPUs) |
| `node_cpu_info{numa_node!=""}` | NUMA topology information (optional) |

## Overcommit Ratio Interpretation

The vCPU overcommit ratio indicates how many virtual CPUs are allocated relative to physical CPUs:

| Ratio Range | Interpretation |
|-------------|----------------|
| 0.0 - 1.0 | No overcommit (safe) |
| 1.0 - 2.0 | Moderate overcommit (typical for VMs) |
| 2.0 - 4.0 | High overcommit (may cause contention) |
| > 4.0 | Very high overcommit (performance risk) |

### Example

```promql
# Nodes with high overcommit (>2.0)
openshift:node:cpu:overcommit:ratio{scope="virtual"} > 2.0
```

## Imbalance Coefficient

The cluster CPU imbalance ratio uses the coefficient of variation to measure how evenly CPU is distributed:

| Coefficient Range | Interpretation |
|------------------|----------------|
| < 0.3 | Balanced distribution |
| 0.3 - 0.6 | Moderate imbalance |
| > 0.6 | High imbalance - rebalancing recommended |

### Example

```promql
# Check cluster CPU imbalance
openshift:cluster:cpu:imbalance:ratio{scope="workloads"}
```

## Accounting Principles

1. **Physical Capacity** = System Reserved + Workload Allocatable
2. **Virtual Overcommit** = Total vCPUs / Physical Capacity
3. **Utilization** = Allocated CPU / Allocatable CPU
4. **Imbalance** = stddev(allocation) / avg(allocation)

## Common Queries

### Capacity Planning

```promql
# Cluster CPU capacity vs utilization
sum(openshift:cluster:cpu:allocatable:count{scope="workloads"})
-
sum(kube_pod_container_resource_requests{resource="cpu"})
```

### Performance Analysis

```promql
# Nodes with high CPU allocation (>80%)
openshift:node:cpu:allocation:ratio{scope="workloads"} > 0.8
```

### VM Overcommit Monitoring

```promql
# Total vCPUs vs physical CPUs
openshift:cluster:cpu:vcpu:count{scope="virtual"}
/
openshift:cluster:cpu:capacity:count{scope="physical"}
```

### Imbalance Detection

```promql
# Detect unbalanced CPU allocation
openshift:cluster:cpu:imbalance:ratio{scope="workloads"} > 0.6
```
