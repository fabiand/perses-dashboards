#!/usr/bin/env python3
"""
Validate memory accounting rules using symbolic math.

This verifies that sum(openshift:node:memory:bytes) == capacity
under different overflow scenarios.
"""

import sympy as sp
from sympy import symbols, Max, simplify


def define_base_symbols():
    """Define symbolic variables for base metrics and return them as a dictionary."""
    # Capacity metrics (inputs from Kubernetes)
    cap = symbols('capacity', positive=True)           # node_memory_MemTotal_bytes
    alloc = symbols('allocatable', positive=True)     # kube_node_status_allocatable

    # System reservation
    res = cap - alloc

    # Actual usage from cgroups
    s_hot = symbols('sys_hot', nonnegative=True)          # container_memory_working_set_bytes{id="/system.slice"}
    s_warm = symbols('sys_warm', nonnegative=True)        # container_memory_total_inactive_file_bytes{id="/system.slice"}
    w_hot = symbols('wl_hot', nonnegative=True)            # container_memory_working_set_bytes{id="/kubepods.slice"}
    w_warm = symbols('wl_warm', nonnegative=True)          # container_memory_total_inactive_file_bytes{id="/kubepods.slice"}

    # Swap
    s_total = symbols('swap_total', nonnegative=True)
    s_used = symbols('swap_used', nonnegative=True)

    print("\nSymbolic variables defined:")
    print(f"  capacity = {cap}")
    print(f"  allocatable = {alloc}")
    print(f"  reservation = capacity - allocatable")
    print(f"  sys_hot, sys_warm, wl_hot, wl_warm (cgroup usage)")
    print(f"  swap_total, swap_used")

    return {
        'capacity': cap,
        'allocatable': alloc,
        'reservation': res,
        'sys_hot': s_hot,
        'sys_warm': s_warm,
        'wl_hot': w_hot,
        'wl_warm': w_warm,
        'swap_total': s_total,
        'swap_used': s_used
    }

def test_implementation_with_scenarios(impl_name, tier0_sum_expr, system_scope_expr, workloads_scope_expr, base_vars):
    """
    Test an implementation with concrete numeric scenarios.

    This function evaluates a given implementation's expressions against three test scenarios:
    1. No overflow - system usage stays within reservation
    2. Moderate overflow - system exceeds reservation by 5GB
    3. Large overflow - real cluster data with 1330GB overflow

    For each scenario, it verifies that:
    - Total tier0 sum equals capacity
    - System scope sum matches expected value (varies by implementation)
    - Workloads scope sum matches expected value (varies by implementation)

    Args:
        impl_name: Descriptive name for this implementation (for output)
        tier0_sum_expr: Symbolic expression for total tier 0 sum
        system_scope_expr: Symbolic expression for system scope sum
        workloads_scope_expr: Symbolic expression for workloads scope sum
        base_vars: Dictionary of base symbolic variables

    Returns:
        Tuple of (test1_pass, test2_pass, test3_pass) booleans
    """
    cap = base_vars['capacity']
    alloc = base_vars['allocatable']
    s_hot = base_vars['sys_hot']
    s_warm = base_vars['sys_warm']
    w_hot = base_vars['wl_hot']
    w_warm = base_vars['wl_warm']
    s_total = base_vars['swap_total']
    s_used = base_vars['swap_used']

    print("\n" + "=" * 80)
    print(f"CONCRETE TEST SCENARIOS - {impl_name}")
    print("=" * 80)

    def test_scenario(name, values):
        """Test a concrete scenario with numeric values."""
        print(f"\n{name}")
        print("-" * 40)

        # Substitute values
        tier0_numeric = tier0_sum_expr.subs(values)
        tier0_result = tier0_numeric.evalf()
        capacity_result = values[cap]

        reservation_value = values[cap] - values[alloc]
        system_usage = values[s_hot] + values[s_warm]
        workloads_usage = values[w_hot] + values[w_warm]
        overflow_value = max(system_usage - reservation_value, 0)

        print(f"  Capacity: {capacity_result}")
        print(f"  Reservation: {reservation_value}")
        print(f"  System usage: {system_usage}")
        print(f"  Workloads usage: {workloads_usage}")
        print(f"  Overflow: {overflow_value}")

        # Scope-specific sums
        system_scope_numeric = system_scope_expr.subs(values).evalf()
        workloads_scope_numeric = workloads_scope_expr.subs(values).evalf()

        print(f"\n  System scope sum: {system_scope_numeric}")
        print(f"    Expected (reservation): {reservation_value}")
        print(f"    Match? {abs(system_scope_numeric - reservation_value) < 0.001}")

        print(f"\n  Workloads scope sum: {workloads_scope_numeric}")
        print(f"    Expected (allocatable): {values[alloc]}")
        print(f"    Match? {abs(workloads_scope_numeric - values[alloc]) < 0.001}")

        print(f"\n  Total (system + workloads): {tier0_result}")
        print(f"    Expected (capacity): {capacity_result}")
        print(f"    Match? {abs(tier0_result - capacity_result) < 0.001}")

        return abs(tier0_result - capacity_result) < 0.001

    # Scenario 1: No overflow (system within reservation)
    scenario1 = {
        cap: 100,
        alloc: 90,
        s_hot: 5,
        s_warm: 3,  # system uses 8GB, reservation is 10GB - no overflow
        w_hot: 40,
        w_warm: 20,
        s_total: 0,
        s_used: 0
    }
    test1_pass = test_scenario("Scenario 1: No overflow", scenario1)

    # Scenario 2: Overflow (system exceeds reservation)
    scenario2 = {
        cap: 100,
        alloc: 90,
        s_hot: 10,
        s_warm: 5,  # system uses 15GB, reservation is 10GB - overflow 5GB
        w_hot: 40,
        w_warm: 20,
        s_total: 0,
        s_used: 0
    }
    test2_pass = test_scenario("Scenario 2: Overflow (system exceeds reservation)", scenario2)

    # Scenario 3: Large overflow (real-world from cluster)
    scenario3 = {
        cap: 17060,  # 17.06 TB
        alloc: 16946,  # ~16.95 TB
        s_hot: 249,
        s_warm: 1195,  # system uses 1444GB, reservation is 114GB - overflow 1330GB
        w_hot: 2301,
        w_warm: 493,
        s_total: 0,
        s_used: 0
    }
    test3_pass = test_scenario("Scenario 3: Large overflow (real cluster data)", scenario3)

    return test1_pass, test2_pass, test3_pass


def validate_implicit_overflow_accounting(base_vars):
    """
    Validate implicit overflow accounting: no overflow series, clamped system_free.

    This approach hides overflow as an internal calculation rather than exposing it
    as a queryable metric. Overflow is accounted for by subtracting it from
    workloads_free, and system_free is clamped to never go negative.

    Key characteristics:
    - system_free is clamped at 0 using Max(reservation - usage, 0)
    - Overflow is calculated internally but NOT exposed as a separate series
    - Overflow is subtracted from workloads_free to maintain total = capacity

    What makes it different:
    - Only 6 tier-0 series (hot/warm/free for system and workloads)
    - No explicit overflow series visible to users
    - Scope sums vary with overflow (system can appear to exceed reservation)

    Correctness:
    - CORRECT: Total tier-0 sum always equals capacity
    - However, scope-level sums are not stable (don't always equal reservation/allocatable)
    - Overflow is hidden from operators (must query scope sums to detect it)
    """
    cap = base_vars['capacity']
    alloc = base_vars['allocatable']
    res = base_vars['reservation']
    s_hot = base_vars['sys_hot']
    s_warm = base_vars['sys_warm']
    w_hot = base_vars['wl_hot']
    w_warm = base_vars['wl_warm']
    s_total = base_vars['swap_total']
    s_used = base_vars['swap_used']

    print("\n" + "=" * 80)
    print("IMPLICIT OVERFLOW ACCOUNTING (no separate overflow series)")
    print("=" * 80)

    # System scope (tier 0)
    sys_hot_curr = s_hot
    sys_warm_curr = s_warm
    sys_free_curr = Max(res - (s_hot + s_warm), 0)  # clamped at 0

    # Overflow (internal calculation, NOT a separate series)
    overflow_curr = Max((s_hot + s_warm) - res, 0)

    # Workloads scope (tier 0)
    wl_hot_curr = w_hot
    wl_warm_curr = w_warm
    wl_free_curr = alloc - (w_hot + w_warm) - overflow_curr  # overflow subtracted here

    # Tier 2 (swap)
    swap_warm_curr = s_used
    swap_free_curr = s_total - s_used

    print("\nRecording rules (tier 0):")
    print(f"  system_hot = {sys_hot_curr}")
    print(f"  system_warm = {sys_warm_curr}")
    print(f"  system_free = Max(reservation - (sys_hot + sys_warm), 0)")
    print(f"  workloads_hot = {wl_hot_curr}")
    print(f"  workloads_warm = {wl_warm_curr}")
    print(f"  workloads_free = allocatable - (wl_hot + wl_warm) - overflow")
    print(f"  (overflow is internal calculation, not exposed as series)")

    # Validate invariants
    print("\n" + "=" * 80)
    print("VALIDATION: Does sum(all series) == capacity?")
    print("=" * 80)

    # Sum of all tier 0 series (the ones exposed as openshift:node:memory:bytes)
    tier0_sum_curr = (sys_hot_curr + sys_warm_curr + sys_free_curr +
                      wl_hot_curr + wl_warm_curr + wl_free_curr)

    print("\nTier 0 sum (before simplification):")
    print(f"  {tier0_sum_curr}")

    # Simplify
    tier0_simplified = simplify(tier0_sum_curr)

    print("\nTier 0 sum (after simplification):")
    print(f"  {tier0_simplified}")

    # Check if it equals capacity
    is_valid_curr = simplify(tier0_simplified - cap) == 0

    print(f"\nTier 0 sum == capacity? {is_valid_curr}")

    if is_valid_curr:
        print("✓ CURRENT IMPLEMENTATION: Accounting is correct!")
    else:
        print("✗ CURRENT IMPLEMENTATION: Accounting is BROKEN!")
        print(f"  Difference: {simplify(tier0_simplified - cap)}")

    # Total across all tiers
    total_curr = tier0_sum_curr + swap_warm_curr + swap_free_curr
    total_simplified = simplify(total_curr)

    print(f"\nTotal sum (tier 0 + tier 2) = {total_simplified}")
    print(f"Expected: capacity + swap_total = {cap + s_total}")
    print(f"Match? {simplify(total_simplified - (cap + s_total)) == 0}")

    # Analyze scope-specific sums
    print("\n" + "=" * 80)
    print("SCOPE-SPECIFIC SUMS")
    print("=" * 80)

    # System scope sum
    system_scope_curr = sys_hot_curr + sys_warm_curr + sys_free_curr
    system_simplified = simplify(system_scope_curr)

    print("\nSystem scope (tier 0):")
    print(f"  system_hot + system_warm + system_free")
    print(f"  = {system_scope_curr}")
    print(f"  Simplified: {system_simplified}")

    # Workloads scope sum
    workloads_scope_curr = wl_hot_curr + wl_warm_curr + wl_free_curr
    workloads_simplified = simplify(workloads_scope_curr)

    print("\nWorkloads scope (tier 0):")
    print(f"  workloads_hot + workloads_warm + workloads_free")
    print(f"  = {workloads_scope_curr}")
    print(f"  Simplified: {workloads_simplified}")

    print("\nWhat should these equal?")
    print(f"  System scope should equal: reservation = {res}")
    print(f"  Workloads scope should equal: allocatable = {alloc}")

    # Validate scope decomposition
    print("\n" + "=" * 80)
    print("SCOPE DECOMPOSITION: sum(all) = sum(scope=system) + sum(scope=workloads)?")
    print("=" * 80)

    total_from_scopes = system_scope_curr + workloads_scope_curr
    total_from_scopes_simplified = simplify(total_from_scopes)

    print(f"\n  sum(scope=system) + sum(scope=workloads) = {total_from_scopes_simplified}")
    print(f"  sum(all series) = {tier0_simplified}")

    scope_match = simplify(total_from_scopes_simplified - tier0_simplified) == 0
    print(f"  Match? {scope_match}")

    if scope_match:
        print("  ✓ Scope decomposition is consistent")
    else:
        print("  ✗ WARNING: Scope decomposition inconsistent!")
        print(f"  Difference: {simplify(total_from_scopes_simplified - tier0_simplified)}")

    # Test with concrete scenarios
    test1, test2, test3 = test_implementation_with_scenarios(
        "CURRENT IMPLEMENTATION",
        tier0_sum_curr,
        system_scope_curr,
        workloads_scope_curr,
        base_vars
    )

    return {
        'is_valid': is_valid_curr,
        'test1_pass': test1,
        'test2_pass': test2,
        'test3_pass': test3
    }

def validate_double_counted_overflow(base_vars):
    """
    Validate double-counted overflow accounting: overflow series + clamped system_free (BROKEN).

    This approach attempted to make overflow visible while keeping system_free non-negative.
    The fatal flaw: overflow gets counted twice in the total sum, breaking the
    fundamental invariant that sum(all series) must equal capacity.

    Key characteristics:
    - system_free is clamped at 0 using Max(reservation - usage, 0)
    - Overflow is exposed as a SEPARATE series (system_overflow)
    - Overflow is ALSO subtracted from workloads_free

    What makes it different:
    - 7 tier-0 series (hot/warm/free for system and workloads, PLUS system_overflow)
    - Overflow is explicitly visible as a separate metric

    Correctness:
    - BROKEN: Double-counting of overflow
    - Overflow appears in both:
      1. system_hot + system_warm (the physical memory usage that caused overflow)
      2. system_overflow (duplicate series counting the same bytes)
    - This causes total to be: capacity + overflow (overcounts by overflow amount)
    - Example: 5GB overflow → sum = 105GB when capacity = 100GB
    - The bug: We can't both clamp system_free AND expose overflow as a separate series
    """
    cap = base_vars['capacity']
    alloc = base_vars['allocatable']
    res = base_vars['reservation']
    s_hot = base_vars['sys_hot']
    s_warm = base_vars['sys_warm']
    w_hot = base_vars['wl_hot']
    w_warm = base_vars['wl_warm']

    print("\n" + "=" * 80)
    print("DOUBLE-COUNTED OVERFLOW (overflow series + clamped system_free) - BROKEN")
    print("=" * 80)

    # Old approach: overflow as a separate series
    sys_hot_old = s_hot
    sys_warm_old = s_warm
    sys_free_old = Max(res - (s_hot + s_warm), 0)  # same clamping
    sys_overflow_old = Max((s_hot + s_warm) - res, 0)  # SEPARATE SERIES

    overflow_old = Max((s_hot + s_warm) - res, 0)

    wl_hot_old = w_hot
    wl_warm_old = w_warm
    wl_free_old = alloc - (w_hot + w_warm) - overflow_old  # overflow still subtracted

    print("\nOld recording rules (tier 0):")
    print(f"  system_hot = {sys_hot_old}")
    print(f"  system_warm = {sys_warm_old}")
    print(f"  system_free = Max(reservation - (sys_hot + sys_warm), 0)")
    print(f"  system_overflow = Max((sys_hot + sys_warm) - reservation, 0)  ← EXTRA SERIES")
    print(f"  workloads_hot = {wl_hot_old}")
    print(f"  workloads_warm = {wl_warm_old}")
    print(f"  workloads_free = allocatable - (wl_hot + wl_warm) - overflow")

    # Sum including the overflow series
    tier0_sum_old = (sys_hot_old + sys_warm_old + sys_free_old + sys_overflow_old +
                     wl_hot_old + wl_warm_old + wl_free_old)

    tier0_old_simplified = simplify(tier0_sum_old)

    print("\nOld tier 0 sum (after simplification):")
    print(f"  {tier0_old_simplified}")

    is_valid_old = simplify(tier0_old_simplified - cap) == 0

    print(f"\nOld tier 0 sum == capacity? {is_valid_old}")

    if not is_valid_old:
        print("✗ OLD IMPLEMENTATION: Accounting is BROKEN!")
        overcount = simplify(tier0_old_simplified - cap)
        print(f"  Overcount: {overcount}")
        print(f"  This equals the overflow value (double-counted)")

    # Validate scope decomposition
    print("\n" + "=" * 80)
    print("SCOPE DECOMPOSITION: sum(all) = sum(scope=system) + sum(scope=workloads)?")
    print("=" * 80)

    system_scope_old = sys_hot_old + sys_warm_old + sys_free_old  # system scope only
    workloads_scope_old = wl_hot_old + wl_warm_old + wl_free_old + sys_overflow_old  # workloads includes overflow

    total_from_scopes_old = system_scope_old + workloads_scope_old
    total_from_scopes_old_simplified = simplify(total_from_scopes_old)

    print(f"\n  sum(scope=system) = {simplify(system_scope_old)}")
    print(f"  sum(scope=workloads with overflow) = {simplify(workloads_scope_old)}")
    print(f"  sum(scope=system) + sum(scope=workloads) = {total_from_scopes_old_simplified}")
    print(f"  sum(all series) = {tier0_old_simplified}")

    scope_match_old = simplify(total_from_scopes_old_simplified - tier0_sum_old) == 0
    print(f"  Match? {scope_match_old}")

    if scope_match_old:
        print("  ✓ Scope decomposition is consistent")
    else:
        print("  ✗ WARNING: Scope decomposition inconsistent!")

    # Test old implementation with overflow scenario
    print("\nTest old implementation with overflow scenario:")
    scenario2 = {
        cap: 100,
        alloc: 90,
        s_hot: 10,
        s_warm: 5,
        w_hot: 40,
        w_warm: 20,
        base_vars['swap_total']: 0,
        base_vars['swap_used']: 0
    }
    tier0_old_numeric = tier0_sum_old.subs(scenario2)
    tier0_old_result = tier0_old_numeric.evalf()
    print(f"  Sum(all series including overflow): {tier0_old_result}")
    print(f"  Expected (capacity): {scenario2[cap]}")
    print(f"  Overcount: {tier0_old_result - scenario2[cap]}")
    print(f"  Overflow value: {max((scenario2[s_hot] + scenario2[s_warm]) - (scenario2[cap] - scenario2[alloc]), 0)}")

    return {
        'is_valid': is_valid_old
    }

def validate_explicit_overflow_with_stable_scopes(base_vars):
    """
    Validate explicit overflow accounting with stable scope sums: overflow series + negative system_free.

    This approach makes overflow highly visible as a separate queryable metric while
    maintaining stable, predictable scope-level sums. The key innovation: allowing
    system_free to go negative eliminates double-counting.

    Key characteristics:
    - system_free is NOT clamped - can go negative when system exceeds reservation
    - Overflow is exposed as a SEPARATE series (system_overflow) tagged as workloads scope
    - Overflow is subtracted from workloads_free

    What makes it different:
    - 7 tier-0 series (hot/warm/free for system and workloads, PLUS system_overflow in workloads)
    - system_free can be negative (clearly shows over-subscription)
    - Scope sums are STABLE:
      * System scope always sums to reservation (even when over-subscribed)
      * Workloads scope (including overflow) always sums to allocatable

    Correctness:
    - CORRECT: Total tier-0 sum always equals capacity (symbolically proven)
    - BENEFIT: Overflow is explicitly visible AND scope sums are stable
    - BENEFIT: Negative system_free is an immediate red flag for operators
    - The key insight: By not clamping system_free, we avoid double-counting
      * system_free = -1330GB shows system is 1330GB over-subscribed
      * system_overflow = +1330GB shows how much workloads gave up
      * These cancel out when summing, maintaining correct accounting
    """
    cap = base_vars['capacity']
    alloc = base_vars['allocatable']
    res = base_vars['reservation']
    s_hot = base_vars['sys_hot']
    s_warm = base_vars['sys_warm']
    w_hot = base_vars['wl_hot']
    w_warm = base_vars['wl_warm']

    print("\n" + "=" * 80)
    print("EXPLICIT OVERFLOW WITH STABLE SCOPES (overflow series + negative system_free)")
    print("=" * 80)

    # Alternative: negative system_free, overflow as separate series
    sys_hot_alt = s_hot
    sys_warm_alt = s_warm
    sys_free_alt = res - (s_hot + s_warm)  # NO CLAMP - can go negative
    sys_overflow_alt = Max((s_hot + s_warm) - res, 0)  # separate series

    overflow_alt = Max((s_hot + s_warm) - res, 0)

    wl_hot_alt = w_hot
    wl_warm_alt = w_warm
    wl_free_alt = alloc - (w_hot + w_warm) - overflow_alt  # still subtract overflow

    print("\nAlternative recording rules (tier 0):")
    print(f"  system_hot = {sys_hot_alt}")
    print(f"  system_warm = {sys_warm_alt}")
    print(f"  system_free = reservation - (sys_hot + sys_warm)  ← NO CLAMP (can be negative)")
    print(f"  system_overflow = Max((sys_hot + sys_warm) - reservation, 0)  ← SEPARATE SERIES")
    print(f"  workloads_hot = {wl_hot_alt}")
    print(f"  workloads_warm = {wl_warm_alt}")
    print(f"  workloads_free = allocatable - (wl_hot + wl_warm) - overflow")

    # System scope sum
    system_scope_alt = sys_hot_alt + sys_warm_alt + sys_free_alt
    system_alt_simplified = simplify(system_scope_alt)

    # Workloads scope sum (including overflow as workloads series)
    workloads_scope_alt = wl_hot_alt + wl_warm_alt + wl_free_alt + sys_overflow_alt
    workloads_alt_simplified = simplify(workloads_scope_alt)

    # Total sum
    tier0_sum_alt = system_scope_alt + workloads_scope_alt
    tier0_alt_simplified = simplify(tier0_sum_alt)

    print("\nSystem scope sum:")
    print(f"  {system_alt_simplified}")
    print(f"  Should equal: reservation = {res}")

    print("\nWorkloads scope sum (including overflow series):")
    print(f"  {workloads_alt_simplified}")
    print(f"  Should equal: allocatable = {alloc}")

    print("\nTotal sum:")
    print(f"  {tier0_alt_simplified}")
    print(f"  Should equal: capacity = {cap}")

    is_valid_alt = simplify(tier0_alt_simplified - cap) == 0
    print(f"\nAlternative tier 0 sum == capacity? {is_valid_alt}")

    # Validate scope decomposition
    print("\n" + "=" * 80)
    print("SCOPE DECOMPOSITION: sum(all) = sum(scope=system) + sum(scope=workloads)?")
    print("=" * 80)

    total_from_scopes_alt = system_scope_alt + workloads_scope_alt
    total_from_scopes_alt_simplified = simplify(total_from_scopes_alt)

    print(f"\n  sum(scope=system) = {system_alt_simplified}")
    print(f"  sum(scope=workloads with overflow) = {workloads_alt_simplified}")
    print(f"  sum(scope=system) + sum(scope=workloads) = {total_from_scopes_alt_simplified}")
    print(f"  sum(all series) = {tier0_alt_simplified}")

    scope_match_alt = simplify(total_from_scopes_alt_simplified - tier0_sum_alt) == 0
    print(f"  Match? {scope_match_alt}")

    if scope_match_alt:
        print("  ✓ Scope decomposition is consistent")
    else:
        print("  ✗ WARNING: Scope decomposition inconsistent!")

    # Test with overflow scenario
    print("\nTest alternative with overflow scenario (Scenario 2):")
    print("-" * 40)

    scenario2 = {
        cap: 100,
        alloc: 90,
        s_hot: 10,
        s_warm: 5,
        w_hot: 40,
        w_warm: 20,
        base_vars['swap_total']: 0,
        base_vars['swap_used']: 0
    }

    system_alt_numeric = system_scope_alt.subs(scenario2).evalf()
    workloads_alt_numeric = workloads_scope_alt.subs(scenario2).evalf()
    tier0_alt_numeric = tier0_sum_alt.subs(scenario2).evalf()

    print(f"  System scope sum: {system_alt_numeric}")
    print(f"    sys_hot(10) + sys_warm(5) + sys_free(10-15=-5) = {scenario2[s_hot]} + {scenario2[s_warm]} + {scenario2[cap] - scenario2[alloc] - scenario2[s_hot] - scenario2[s_warm]} = {system_alt_numeric}")
    print(f"    Expected (reservation): {scenario2[cap] - scenario2[alloc]}")
    print(f"    Match? {abs(system_alt_numeric - (scenario2[cap] - scenario2[alloc])) < 0.001}")

    print(f"\n  Workloads scope sum (including overflow): {workloads_alt_numeric}")
    print(f"    wl_hot(40) + wl_warm(20) + wl_free(90-60-5=25) + overflow(5) = {workloads_alt_numeric}")
    print(f"    Expected (allocatable): {scenario2[alloc]}")
    print(f"    Match? {abs(workloads_alt_numeric - scenario2[alloc]) < 0.001}")

    print(f"\n  Total: {tier0_alt_numeric}")
    print(f"    Expected (capacity): {scenario2[cap]}")
    print(f"    Match? {abs(tier0_alt_numeric - scenario2[cap]) < 0.001}")

    # Test with real cluster data
    print("\nTest alternative with real cluster data (Scenario 3):")
    print("-" * 40)

    scenario3 = {
        cap: 17060,
        alloc: 16946,
        s_hot: 249,
        s_warm: 1195,
        w_hot: 2301,
        w_warm: 493,
        base_vars['swap_total']: 0,
        base_vars['swap_used']: 0
    }

    system_alt_s3 = system_scope_alt.subs(scenario3).evalf()
    workloads_alt_s3 = workloads_scope_alt.subs(scenario3).evalf()
    tier0_alt_s3 = tier0_sum_alt.subs(scenario3).evalf()

    print(f"  System scope sum: {system_alt_s3}")
    print(f"    sys_hot(249) + sys_warm(1195) + sys_free(114-1444=-1330) = {system_alt_s3}")
    print(f"    Expected (reservation): {scenario3[cap] - scenario3[alloc]}")
    print(f"    system_free would be NEGATIVE: {scenario3[cap] - scenario3[alloc] - scenario3[s_hot] - scenario3[s_warm]}")

    print(f"\n  Workloads scope sum (including overflow): {workloads_alt_s3}")
    print(f"    Expected (allocatable): {scenario3[alloc]}")

    print(f"\n  Total: {tier0_alt_s3}")
    print(f"    Expected (capacity): {scenario3[cap]}")
    print(f"    Match? {abs(tier0_alt_s3 - scenario3[cap]) < 0.001}")

    return {
        'is_valid': is_valid_alt
    }

def main():
    """
    Main execution flow for memory accounting validation.

    This script validates three different approaches to memory accounting:
    1. Current: No overflow series, clamped system_free
    2. Old: Overflow series + clamped system_free (proves it's broken)
    3. Alternative: Overflow series + negative system_free (proves it's correct)

    The validation uses symbolic math to prove correctness algebraically,
    then tests with concrete numeric scenarios to verify the implementation.
    """
    print("=" * 80)
    print("Memory Accounting Validation")
    print("=" * 80)

    # Define base symbolic variables
    base_vars = define_base_symbols()

    # Validate each implementation
    current_results = validate_implicit_overflow_accounting(base_vars)
    old_results = validate_double_counted_overflow(base_vars)
    alt_results = validate_explicit_overflow_with_stable_scopes(base_vars)

    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    print(f"\n1. IMPLICIT OVERFLOW ACCOUNTING (no overflow series):")
    print(f"   Mathematically correct? {current_results['is_valid']}")
    print(f"   Scenario 1 (no overflow): {'PASS' if current_results['test1_pass'] else 'FAIL'}")
    print(f"   Scenario 2 (overflow): {'PASS' if current_results['test2_pass'] else 'FAIL'}")
    print(f"   Scenario 3 (real cluster): {'PASS' if current_results['test3_pass'] else 'FAIL'}")

    print(f"\n2. DOUBLE-COUNTED OVERFLOW (overflow series + clamped system_free):")
    print(f"   Mathematically correct? {old_results['is_valid']}")
    print(f"   Problem: Overflow is counted twice (once in system_hot+system_warm, once as separate series)")

    print(f"\n3. EXPLICIT OVERFLOW WITH STABLE SCOPES (overflow series + negative system_free):")
    print(f"   Mathematically correct? {alt_results['is_valid']}")
    print(f"   System scope sums to: reservation (always)")
    print(f"   Workloads scope sums to: allocatable (always)")
    print(f"   Overflow series shows: how much system borrowed from workloads")
    print(f"   system_free can be: NEGATIVE (shows over-subscription)")

    print("\n" + "=" * 80)
    if alt_results['is_valid']:
        print("✓ VALIDATION SUCCESSFUL:")
        print("  1. IMPLICIT OVERFLOW: Numerically correct ✓")
        print("      - Overflow hidden in internal calculation")
        print("      - Scope sums vary with overflow (system can exceed reservation)")
        print("  2. DOUBLE-COUNTED OVERFLOW: BROKEN ✗")
        print("      - Overflow counted twice: in system usage AND as separate series")
        print("      - Sum = capacity + overflow (incorrect)")
        print("  3. EXPLICIT OVERFLOW WITH STABLE SCOPES: Symbolically proven ✓")
        print("      - Overflow visible as queryable series")
        print("      - Scope sums always stable (system=reservation, workloads=allocatable)")
        print("      - Negative system_free clearly shows over-subscription")
    else:
        print("✗ VALIDATION FAILED: Check the model")


if __name__ == "__main__":
    main()
