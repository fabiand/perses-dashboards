# Memory Recording Rules

## Objective

Memory is a non-compressible resource - when exhausted, workloads are terminated rather than slowed down. Accurate monitoring is critical for safe operations. These recording rules measure system and workload memory consumption to enable:

- **Capacity planning** - Understand allocation vs utilization
- **OOM risk detection** - Predict availability issues before they occur
- **Performance analysis** - Distinguish hot (critical) from warm (reclaimable) memory

## Concept

Recording rules pre-calculate memory metrics to simplify dashboard queries and ensure stable accounting. The core principle: **sum over all dimensions always equals capacity**.

Multiple dimensions slice the same memory resource to address different operational needs:
- **Tiers** - hardware technology (DRAM, swap)
- **Scopes** - allocation boundary (system, workloads)
- **Temperature** - access pattern (hot, warm)
- **Utilization** - usage state (used, free)

Each dimension provides a different lens on the same physical memory.

### Tiers

The rules are designed to cover multiple memory tiers in a system:

| Tier | Technology | Latency | Support |
|------|------------|---------|---------|
| `0`  | DRAM (main memory) | ~100ns | Now |
| `1`  | CXL expansion memory | - | Future |
| `2`  | Swap (disk-backed memory) | ~ms | Now |

Where:
- **Tier 0**: `kube_node_status_capacity{resource="memory"}` = `node_memory_MemTotal_bytes` = Amount of DRAM
- **Tier 2**: `node_memory_SwapTotal_bytes` = Amount of Swap

#### Example

```promql
# DRAM memory
openshift:node:memory:bytes{tier="0"}

# Swap memory
openshift:node:memory:bytes{tier="2"}
```

### Scopes

Memory is split into:

| Scope | Purpose | Tier Access |
|-------|---------|-------------|
| `system` | Reserved space for OS/hypervisor | 0 |
| `workloads` | Space for pods/VMs | All |

#### Example

```promql
# System memory
openshift:node:memory:bytes{scope="system"}
openshift:node:memory:bytes{scope="system", tier="0"}

# Workloads memory
openshift:node:memory:bytes{scope="workloads"}
openshift:node:memory:bytes{scope="workloads", tier="2"}
```

#### System Overflow Accounting

System can consume more memory than reserved. When this happens:

- **System free goes negative** - showing how much beyond reservation is being used
- **Overflow is exposed as a separate series** - making over-subscription visible
- **Overflow is also subtracted from workloads free** - reflecting reduced available space
- This preserves the accounting invariant: sum of all series equals capacity
- **Scope sums remain stable**: system scope always sums to reservation, workloads scope always sums to allocatable

##### Example

```promql
# System overflow amount (memory borrowed from workloads)
openshift:node:memory:bytes{scope="workloads", utilized="true", usage="overflow"}

# System free memory (can be negative when over-subscribed)
openshift:node:memory:bytes{scope="system", utilized="false"}
# When negative: system is using (reservation + abs(free)) bytes total
```

### Utilization

Memory is either in use or available for allocation.

| State | Description |
|-------|-------------|
| `utilized="true"` | Memory in use |
| `utilized="false"` | Free memory available for allocation |

#### Example

```promql
# Used memory
openshift:node:memory:bytes{utilized="true"}
openshift:node:memory:bytes{utilized="true", scope="workloads"}
openshift:node:memory:bytes{utilized="true", scope="workloads", tier="0"}

# Free/remaining memory
openshift:node:memory:bytes{utilized="false"}
openshift:node:memory:bytes{utilized="false", scope="system"}
openshift:node:memory:bytes{utilized="false", scope="workloads", tier="2"}
```

#### Temperature

Memory in use is further characterized by **access pattern** - how recently pages were accessed:

- **`hot`** - Working set (active memory). Recently accessed pages. Must be available. Unavailable pages → OOM kill.
- **`warm`** - Inactive file cache. Not recently accessed but still in memory. Should be reclaimed first. Can be freed without OOM.

Impact of memory pressure by temperature:

| Temperature | Performance Impact | Availability Impact (OOM Risk) |
|-------------|-------------------|--------------------------------|
| `warm`      | *High* - reclaiming cache causes disk I/O | *Low* - can be freed without OOM |
| `hot`       | *High* - active pages must stay in memory | *High* - unavailable pages → OOM kill |

This distinction matters for **predicting OOM risk**. Hot memory pressure is critical; warm memory pressure degrades performance but workloads stay available.

##### Example

```promql
# Hot memory (working set)
openshift:node:memory:bytes{temperature="hot"}
openshift:node:memory:bytes{temperature="hot", scope="workloads"}
openshift:node:memory:bytes{temperature="hot", scope="workloads", tier="0"}

# Warm memory (inactive file cache)
openshift:node:memory:bytes{temperature="warm"}
openshift:node:memory:bytes{temperature="warm", scope="workloads"}
openshift:node:memory:bytes{temperature="warm", scope="workloads", tier="2"}
```

### Ratios

| Ratio | What | Use-case | Target |
|-------|------|----------|--------|
| `utilization` | Fraction of workloads memory currently used | Capacity planning and threshold alerts. Values approaching 1.0 signal the cluster needs more memory or workload reduction | 0.7 - 0.8 |
| `pressure` | Fraction of time spent waiting for memory to become available | Detect memory contention before OOM. Workloads competing for cache/buffers even if utilization looks acceptable | < 0.1 |
| `overcommit` | Virtual memory assigned to VMs vs physical memory allocated | Track VM memory safety margin. Values >1 are normal, but high values increase OOM risk if VMs consume full allocation | < 1.5 |
| `imbalance` | Coefficient of Variation of memory utilization across nodes | Detect uneven workload distribution. Measures relative spread of utilization. Higher values indicate poor balance | < 0.3 (balanced), 0.3-0.6 (moderate), >0.6 (high imbalance) |

#### Example

```promql
# Per-node workload utilization
openshift:node:memory:utilization:ratio

# Per-node memory pressure
openshift:node:memory:pressure:ratio

# Per-VM overcommit
openshift:vm:memory:overcommit:ratio

# Cluster workload imbalance
openshift:cluster:memory:imbalance:ratio
```

## Recording Rule Structure

All rules use **colon hierarchy** (Prometheus convention for recording rules):

```
openshift:node:memory:bytes{scope, tier, utilized, temperature, usage}
openshift:node:memory:utilization:ratio
openshift:cluster:memory:utilization:ratio
openshift:cluster:memory:imbalance:ratio
openshift:vm:memory:overcommit:ratio
```

### Label Dimensions

- **tier**: `0` (DRAM), `2` (swap)
- **scope**: `system`, `workloads`
- **utilized**: `true` (used), `false` (free)
- **temperature**: `hot` (working_set), `warm` (inactive_file) - page access frequency
- **usage**: `overflow` (system memory borrowed from workloads space)

## Query Patterns

### 1. Sum by tier

**Use-case**: Total memory available in DRAM vs swap.

```promql
# Total DRAM capacity per node
sum by (node) (openshift:node:memory:bytes{tier="0"})

# Total swap capacity per node
sum by (node) (openshift:node:memory:bytes{tier="2"})
```

**Why**: Understand total memory capacity across tiers. DRAM should equal `kube_node_status_capacity{resource="memory"}`, swap shows configured swap space.

### 2. Sum by utilized

**Use-case**: How much memory is used vs free.

```promql
# Total memory in use (DRAM)
sum(openshift:node:memory:bytes{tier="0", utilized="true"})

# Total free memory (DRAM)
sum(openshift:node:memory:bytes{tier="0", utilized="false"})
```

**Why**: Monitor cluster-wide utilization. Used + Free = Total capacity.

**Use-case**: Workload memory pressure.

```promql
# Workload utilization ratio per node
openshift:node:memory:utilization:ratio

# Cluster-wide workload utilization (capacity-weighted)
openshift:cluster:memory:utilization:ratio
```

**Why**: Track how much of workloads space is consumed. The cluster ratio is capacity-weighted (can't average per-node ratios).

### 3. Sum by scope

**Use-case**: System vs workload memory consumption.

```promql
# System memory used
sum(openshift:node:memory:bytes{scope="system", utilized="true"})

# Workload memory used
sum(openshift:node:memory:bytes{scope="workloads", utilized="true"})
```

**Why**: Identify if system or workloads are consuming memory.

**Use-case**: Detect system overflow and over-subscription.

```promql
# Nodes where system exceeds reservation (overflow > 0)
openshift:node:memory:bytes{scope="workloads", utilized="true", usage="overflow"} > 0

# Nodes with negative system free (same information, different view)
openshift:node:memory:bytes{scope="system", utilized="false"} < 0
```

**Why**: Alert when system components borrow from workloads space. This triggers `SystemMemoryExceedsReservation` alert. The overflow series and negative system_free show the same condition from different perspectives.

### 4. Combine dimensions

**Use-case**: Hot vs warm workload memory.

```promql
# Hot memory (working set) - likely to cause OOM if unavailable
sum(openshift:node:memory:bytes{scope="workloads", tier="0", temperature="hot", utilized="true"})

# Warm memory (inactive file cache) - can be reclaimed
sum(openshift:node:memory:bytes{scope="workloads", tier="0", temperature="warm", utilized="true"})
```

**Why**: Distinguish between critical working set and reclaimable cache. Hot memory pressure is more severe.

**Use-case**: VM overcommit monitoring.

```promql
# Per-VM overcommit ratio
openshift:vm:memory:overcommit:ratio

# Cluster-wide VM overcommit (capacity-weighted)
openshift:cluster:memory:overcommit:ratio
```

**Why**: Track virtual memory assignment vs physical allocation. Values >1 indicate overcommit.

**Use-case**: Memory utilization imbalance detection.

```promql
# Cluster-wide memory imbalance (Coefficient of Variation)
openshift:cluster:memory:imbalance:ratio
```

**Why**: Detect uneven workload distribution across nodes. Computed as `stddev(utilization) / avg(utilization)`. Values <0.3 indicate balanced distribution, 0.3-0.6 moderate imbalance, >0.6 high imbalance requiring workload rebalancing.

## Important Notes

- **Recording rules and data lag**: Recording rules can reference other recording rules, but this creates time lag between when base metrics update and when dependent rules evaluate. To avoid inconsistencies, complex rules expand other recording rules inline (using base metrics directly). Comments mark these expansions with "same as openshift:..." to document which recording rule is being inlined.
- **Role filtering**: Dashboard queries use `and on (node) kube_node_role{role=~"$role"}` for role filtering. Recording rules don't pre-filter by role (dynamic dashboard variable).
- **Cluster ratios**: Can't average per-node ratios. Must compute `sum(numerator) / sum(denominator)` for capacity-weighted cluster-wide ratios.
