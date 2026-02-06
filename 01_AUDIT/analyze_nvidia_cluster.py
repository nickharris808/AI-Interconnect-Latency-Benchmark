#!/usr/bin/env python3
"""
=============================================================================
NVIDIA CLUSTER LATENCY ANALYSIS
AI Interconnect Latency Benchmark - Economic Impact Calculator
=============================================================================

This script analyzes the latency impact on NVIDIA GPU clusters using real
specifications from H100, B200, GB200 NVL72, and projected Rubin.

THE PROBLEM:
------------
At scale (1,000+ GPUs), optical interconnect latency becomes a measurable
constraint on training efficiency. Every round-trip through standard fiber
(n=1.468) adds latency compared to what is physically possible.

WHAT THIS SCRIPT MODELS:
------------------------
1. Time-of-Flight (ToF) latency for optical interconnects
2. Comparison: Standard fiber vs. Superluminal Glass (n=1.15)
3. Economic impact: GPU-hours and dollars lost to waiting

CRITICAL MODELING PARAMETERS:
-----------------------------
1. Syncs per second: Highly workload-dependent
   - Data parallelism only: ~100/sec
   - Pipeline parallelism: ~500-2000/sec
   - Aggressive micro-batching: ~5000/sec
   
2. Fiber fraction: NOT all syncs traverse optical fiber
   - Intra-node (NVLink copper): No fiber
   - Intra-rack (NVSwitch): No fiber
   - Inter-rack (optical): Yes
   - Inter-pod (long-haul): Yes
   
3. Hops per sync: Network topology dependent
   - Flat network: 2-4 hops
   - Spine-leaf: 4-6 hops
   - Fat-tree: 6-12 hops

HONEST LIMITATIONS:
-------------------
- SerDes, FEC, and switch latencies are NOT modeled (use --include-system-overhead)
- Sync rate is highly variable; use sensitivity analysis
- Not all training frameworks have the same sync patterns
- This is a CEILING on savings; actual savings may be lower

SOURCES:
--------
[1] NVIDIA H100 Datasheet (2023)
[2] NVIDIA Blackwell Architecture Technical Brief (GTC 2024)
[3] NVIDIA GB200 NVL72 Specifications (2024)
[4] SMF-28 refractive index: Corning Datasheet (n=1.4682)
[5] Superluminal Glass: Patent 4, Genesis Research (n=1.1524)

=============================================================================
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional
import sys


# =============================================================================
# PHYSICAL CONSTANTS
# =============================================================================

# Speed of light in vacuum (exact by SI definition)
C_VACUUM_M_S = 299_792_458

# Refractive indices
N_STANDARD_FIBER = 1.4682  # SMF-28 at 1550nm (Corning datasheet)
N_SUPERLUMINAL = 1.1524    # Genesis Superluminal Glass (Patent 4)

# Economic parameters
DEFAULT_GPU_HOUR_COST_USD = 2.00  # AWS p5.48xlarge equivalent

# Time constants
SECONDS_PER_DAY = 86_400
SECONDS_PER_YEAR = 365.25 * SECONDS_PER_DAY


# =============================================================================
# SYSTEM OVERHEAD (OPTIONAL)
# =============================================================================

# Typical system latencies (nanoseconds) per link
SYSTEM_OVERHEAD = {
    "serdes_round_trip": 200,    # TX (50ns) + RX (50ns) × 2 ends
    "fec_round_trip": 200,       # Encode + Decode × 2 ends
    "switch_per_hop": 200,       # Per switch traversal
}


# =============================================================================
# LATENCY CALCULATIONS
# =============================================================================

def calculate_tof_ns(distance_m: float, n: float) -> float:
    """
    Calculate round-trip time-of-flight in nanoseconds.
    
    Formula: τ = 2 × L × n / c
    """
    return 2 * distance_m * n / C_VACUUM_M_S * 1e9


def calculate_savings_per_hop_ns(distance_m: float) -> float:
    """
    Calculate ToF savings per hop (round-trip) for Superluminal vs SMF-28.
    """
    tof_smf = calculate_tof_ns(distance_m, N_STANDARD_FIBER)
    tof_super = calculate_tof_ns(distance_m, N_SUPERLUMINAL)
    return tof_smf - tof_super


# =============================================================================
# CLUSTER ANALYSIS
# =============================================================================

def analyze_cluster(config: Dict, 
                    verbose: bool = True,
                    include_system_overhead: bool = False,
                    override_fiber_fraction: Optional[float] = None,
                    override_syncs_per_sec: Optional[float] = None,
                    gpu_hour_cost: float = DEFAULT_GPU_HOUR_COST_USD) -> Dict:
    """
    Perform complete latency analysis for an NVIDIA cluster configuration.
    
    Parameters:
    -----------
    config : dict
        Cluster configuration loaded from JSON
    verbose : bool
        Print detailed output
    include_system_overhead : bool
        Include SerDes, FEC, switch latencies (reduces ToF fraction)
    override_fiber_fraction : float, optional
        Override config's fiber fraction (0.0 to 1.0)
    override_syncs_per_sec : float, optional
        Override config's syncs per second
    gpu_hour_cost : float
        Cost per GPU-hour in USD
        
    Returns:
    --------
    dict : Comprehensive analysis results
    """
    
    # Extract configuration
    chip_name = config.get("chip_name", "Unknown")
    
    interconnect = config.get("interconnect", {})
    cluster = config.get("cluster_config", {})
    specs = config.get("specs", {})
    
    # Key parameters
    total_gpus = cluster.get("total_gpus", 256)
    cluster_distance_m = interconnect.get("typical_cluster_distance_m", 
                                          interconnect.get("external_fabric_distance_m", 100))
    
    # Sync parameters (with overrides)
    syncs_per_second = override_syncs_per_sec or cluster.get("syncs_per_second", 1000)
    fiber_fraction = override_fiber_fraction if override_fiber_fraction is not None else cluster.get("fiber_fraction", 0.70)
    hops_per_sync = cluster.get("gradient_sync_hops", 4)
    
    # GPU specs (for context)
    fp8_tflops = specs.get("fp8_tflops", 3958)
    
    # ==========================================================================
    # LATENCY CALCULATIONS
    # ==========================================================================
    
    # Time-of-Flight (pure physics)
    tof_smf_ns = calculate_tof_ns(cluster_distance_m, N_STANDARD_FIBER)
    tof_super_ns = calculate_tof_ns(cluster_distance_m, N_SUPERLUMINAL)
    savings_per_hop_ns = tof_smf_ns - tof_super_ns
    
    # System overhead (if requested)
    if include_system_overhead:
        overhead_per_hop_ns = (SYSTEM_OVERHEAD["serdes_round_trip"] + 
                               SYSTEM_OVERHEAD["fec_round_trip"] +
                               SYSTEM_OVERHEAD["switch_per_hop"])
    else:
        overhead_per_hop_ns = 0
    
    total_latency_per_hop_smf = tof_smf_ns + overhead_per_hop_ns
    tof_fraction = tof_smf_ns / total_latency_per_hop_smf if total_latency_per_hop_smf > 0 else 1.0
    
    # ==========================================================================
    # ECONOMIC IMPACT
    # ==========================================================================
    
    # Per-sync latency (only for fiber-traversing syncs)
    effective_syncs_per_second = syncs_per_second * fiber_fraction
    latency_per_sync_ns = hops_per_sync * total_latency_per_hop_smf
    savings_per_sync_ns = hops_per_sync * savings_per_hop_ns
    
    # Daily latency tax (all GPUs wait during sync)
    # This is the maximum possible impact assuming sync is blocking
    daily_latency_tax_ns = (effective_syncs_per_second * 
                            SECONDS_PER_DAY * 
                            latency_per_sync_ns)
    daily_latency_tax_seconds = daily_latency_tax_ns / 1e9
    
    # GPU-hours: All GPUs are idle during sync latency
    # GPU-hours/day = (total_latency_seconds/day) × (total_gpus) / (3600 sec/hour)
    daily_latency_tax_gpu_hours = daily_latency_tax_seconds * total_gpus / 3600
    
    # Savings
    daily_savings_ns = (effective_syncs_per_second * 
                        SECONDS_PER_DAY * 
                        savings_per_sync_ns)
    daily_savings_gpu_hours = (daily_savings_ns / 1e9) * total_gpus / 3600
    
    # Annual projections
    annual_latency_tax_gpu_hours = daily_latency_tax_gpu_hours * 365
    annual_savings_gpu_hours = daily_savings_gpu_hours * 365
    annual_savings_usd = annual_savings_gpu_hours * gpu_hour_cost
    
    # Wasted FLOPS per round-trip
    ops_per_ns = fp8_tflops * 1e3  # TFLOPS to GFLOPS = ops/ns
    wasted_ops_per_hop = tof_smf_ns * ops_per_ns
    
    # ==========================================================================
    # RESULTS
    # ==========================================================================
    
    results = {
        "chip_name": chip_name,
        "total_gpus": total_gpus,
        "cluster_distance_m": cluster_distance_m,
        "syncs_per_second": syncs_per_second,
        "fiber_fraction": fiber_fraction,
        "effective_fiber_syncs_per_second": effective_syncs_per_second,
        "hops_per_sync": hops_per_sync,
        "include_system_overhead": include_system_overhead,
        "overhead_per_hop_ns": overhead_per_hop_ns,
        "tof_smf_ns": tof_smf_ns,
        "tof_super_ns": tof_super_ns,
        "savings_per_hop_ns": savings_per_hop_ns,
        "total_latency_per_hop_smf": total_latency_per_hop_smf,
        "tof_fraction": tof_fraction,
        "savings_per_sync_ns": savings_per_sync_ns,
        "daily_latency_tax_gpu_hours": daily_latency_tax_gpu_hours,
        "daily_savings_gpu_hours": daily_savings_gpu_hours,
        "annual_latency_tax_gpu_hours": annual_latency_tax_gpu_hours,
        "annual_savings_gpu_hours": annual_savings_gpu_hours,
        "annual_savings_usd": annual_savings_usd,
        "wasted_ops_per_hop": wasted_ops_per_hop,
        "gpu_hour_cost": gpu_hour_cost,
    }
    
    if verbose:
        print_analysis(results, config)
    
    return results


def print_analysis(results: Dict, config: Dict):
    """Pretty-print the analysis results."""
    print()
    print("=" * 78)
    print(f"  NVIDIA CLUSTER LATENCY ANALYSIS: {results['chip_name']}")
    print("=" * 78)
    
    print(f"\n📊 CLUSTER CONFIGURATION:")
    print(f"   Total GPUs:              {results['total_gpus']:,}")
    print(f"   Cluster Distance:        {results['cluster_distance_m']} m")
    print(f"   Total Syncs/sec:         {results['syncs_per_second']:,}")
    print(f"   Fiber Fraction:          {results['fiber_fraction']*100:.0f}%")
    print(f"   → Fiber Syncs/sec:       {results['effective_fiber_syncs_per_second']:,.0f}")
    print(f"   Hops per Sync:           {results['hops_per_sync']}")
    
    if results['include_system_overhead']:
        print(f"\n⚙️  SYSTEM OVERHEAD (INCLUDED):")
        print(f"   SerDes + FEC + Switch:   {results['overhead_per_hop_ns']:.0f} ns per hop")
    else:
        print(f"\n⚙️  SYSTEM OVERHEAD: Not included (pure ToF analysis)")
        print(f"   Use --include-system-overhead to add SerDes/FEC/switch")
    
    print(f"\n⚡ TIME-OF-FLIGHT ANALYSIS (Round-Trip, {results['cluster_distance_m']}m):")
    print(f"   SMF-28 (n=1.468):        {results['tof_smf_ns']:.2f} ns")
    print(f"   Superluminal (n=1.15):   {results['tof_super_ns']:.2f} ns")
    print(f"   Savings per Hop:         {results['savings_per_hop_ns']:.2f} ns")
    print(f"   Savings per Sync:        {results['savings_per_sync_ns']:.2f} ns ({results['hops_per_sync']} hops)")
    
    if results['include_system_overhead']:
        print(f"\n📉 ToF FRACTION OF TOTAL:")
        print(f"   ToF is {results['tof_fraction']*100:.1f}% of per-hop latency")
        print(f"   → Superluminal improves only the ToF portion")
    
    print(f"\n💰 DAILY IMPACT:")
    print(f"   Latency Tax (SMF-28):    {results['daily_latency_tax_gpu_hours']:.1f} GPU-hours/day")
    print(f"   Recoverable Savings:     {results['daily_savings_gpu_hours']:.1f} GPU-hours/day")
    
    print(f"\n📈 ANNUAL PROJECTION (@ ${results['gpu_hour_cost']:.2f}/GPU-hr):")
    print(f"   Annual Latency Tax:      {results['annual_latency_tax_gpu_hours']:,.0f} GPU-hours")
    print(f"   Annual Recoverable:      {results['annual_savings_gpu_hours']:,.0f} GPU-hours")
    print(f"   Annual Savings:          ${results['annual_savings_usd']:,.0f}")
    
    # Compute idle during latency
    print(f"\n🧮 COMPUTE IDLE DURING LATENCY:")
    print(f"   FP8 FLOPS wasted per hop: {results['wasted_ops_per_hop']:.2e}")
    
    # Severity assessment
    if results['annual_savings_usd'] > 1_000_000:
        severity = "🚨 CRITICAL"
    elif results['annual_savings_usd'] > 100_000:
        severity = "⚠️ SIGNIFICANT"
    elif results['annual_savings_usd'] > 10_000:
        severity = "📊 MEASURABLE"
    else:
        severity = "ℹ️ MINOR"
    
    print(f"\n{'─' * 78}")
    print(f"\n{severity} LATENCY IMPACT ASSESSMENT")
    print(f"\n   At {results['total_gpus']:,} GPUs, {results['cluster_distance_m']}m fiber, ")
    print(f"   {results['effective_fiber_syncs_per_second']:,.0f} fiber syncs/sec:")
    print(f"\n   → Potential annual savings: ${results['annual_savings_usd']:,.0f}")
    
    print(f"\n{'=' * 78}")
    print(f"🔒 SOLUTION: SUPERLUMINAL GLASS (Patent Pending)")
    print(f"   n_eff = 1.15 | Speed = 260,146 km/s | 27% faster than SMF-28")
    print(f"   Contact: nick@genesis.ai")
    print(f"{'=' * 78}")
    print()


def print_sensitivity_table(config: Dict, 
                            gpu_hour_cost: float = DEFAULT_GPU_HOUR_COST_USD):
    """Print sensitivity analysis table for sync rate variations."""
    
    chip_name = config.get("chip_name", "Unknown")
    cluster = config.get("cluster_config", {})
    interconnect = config.get("interconnect", {})
    
    total_gpus = cluster.get("total_gpus", 256)
    distance = interconnect.get("typical_cluster_distance_m", 100)
    hops = cluster.get("gradient_sync_hops", 4)
    fiber_fraction = cluster.get("fiber_fraction", 0.70)
    
    sync_rates = [100, 500, 1000, 2000, 5000, 10000]
    
    print()
    print("=" * 78)
    print(f"  SENSITIVITY ANALYSIS: {chip_name}")
    print("=" * 78)
    print(f"\n📐 Fixed Parameters:")
    print(f"   GPUs: {total_gpus:,} | Distance: {distance}m | Hops: {hops} | Fiber: {fiber_fraction*100:.0f}%")
    
    print(f"\n┌{'─'*16}┬{'─'*24}┬{'─'*18}┬{'─'*16}┐")
    print(f"│ {'Syncs/sec':>14} │ {'Training Style':>22} │ {'Annual Savings':>16} │ {'Confidence':>14} │")
    print(f"├{'─'*16}┼{'─'*24}┼{'─'*18}┼{'─'*16}┤")
    
    style_map = {
        100: "Data parallel",
        500: "Moderate pipeline",
        1000: "Dense pipeline",
        2000: "Tensor + pipeline",
        5000: "Micro-batching",
        10000: "Extreme (theoretical)"
    }
    
    conf_map = {
        100: "HIGH",
        500: "HIGH",
        1000: "MEDIUM",
        2000: "MEDIUM",
        5000: "LOW",
        10000: "SPECULATIVE"
    }
    
    for rate in sync_rates:
        result = analyze_cluster(
            config, 
            verbose=False, 
            override_syncs_per_sec=rate,
            gpu_hour_cost=gpu_hour_cost
        )
        style = style_map.get(rate, "Unknown")
        conf = conf_map.get(rate, "?")
        print(f"│ {rate:>14,} │ {style:>22} │ ${result['annual_savings_usd']:>15,.0f} │ {conf:>14} │")
    
    print(f"└{'─'*16}┴{'─'*24}┴{'─'*18}┴{'─'*16}┘")
    
    print(f"\n📝 NOTES:")
    print(f"   - Sync rate varies dramatically by workload and framework")
    print(f"   - 'Fiber fraction' accounts for syncs that don't traverse optical")
    print(f"   - Conservative analysis: use 500-1000 syncs/sec")
    print(f"   - Aggressive analysis: use 2000-5000 syncs/sec")
    print()


# =============================================================================
# CONFIG LOADING
# =============================================================================

def load_config(config_name: str, config_dir: Optional[Path] = None) -> Dict:
    """Load NVIDIA cluster configuration from JSON."""
    if config_dir is None:
        config_dir = Path(__file__).parent.parent / "configs"
    
    config_path = config_dir / f"{config_name}.json"
    
    if not config_path.exists():
        # Try adding nvidia_ prefix
        config_path = config_dir / f"nvidia_{config_name}.json"
    
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")
    
    with open(config_path, 'r') as f:
        return json.load(f)


def list_configs(config_dir: Optional[Path] = None) -> List[str]:
    """List available configuration files."""
    if config_dir is None:
        config_dir = Path(__file__).parent.parent / "configs"
    
    configs = []
    for p in config_dir.glob("*.json"):
        configs.append(p.stem)
    return sorted(configs)


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Analyze NVIDIA cluster latency impact",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s nvidia_gb200_nvl72           # Analyze GB200 cluster
  %(prog)s nvidia_b200                   # Analyze B200 cluster
  %(prog)s nvidia_gb200_nvl72 --sensitivity   # Sync rate sensitivity
  %(prog)s nvidia_h100 --fiber-fraction 0.5   # Override fiber fraction
  %(prog)s --all                              # Analyze all configs
  %(prog)s nvidia_gb200_nvl72 --include-system-overhead  # Include SerDes/FEC

Available Configurations:
  nvidia_h100        H100 SXM5 cluster (256 GPUs)
  nvidia_b200        B200 Blackwell cluster (2,048 GPUs)
  nvidia_gb200_nvl72 GB200 NVL72 rack cluster (4,608 GPUs)
  nvidia_rubin_2026  Rubin projected cluster (100,000 GPUs)
        """
    )
    
    parser.add_argument(
        "config",
        nargs="?",
        default="nvidia_gb200_nvl72",
        help="Config name (default: nvidia_gb200_nvl72)"
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Analyze all available configs"
    )
    parser.add_argument(
        "--sensitivity", "-s",
        action="store_true",
        help="Show sensitivity analysis table"
    )
    parser.add_argument(
        "--fiber-fraction", "-f",
        type=float,
        help="Override fiber fraction (0.0 to 1.0)"
    )
    parser.add_argument(
        "--syncs-per-sec",
        type=float,
        help="Override syncs per second"
    )
    parser.add_argument(
        "--include-system-overhead",
        action="store_true",
        help="Include SerDes, FEC, switch latencies"
    )
    parser.add_argument(
        "--gpu-cost",
        type=float,
        default=DEFAULT_GPU_HOUR_COST_USD,
        help=f"GPU-hour cost in USD (default: ${DEFAULT_GPU_HOUR_COST_USD})"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available configurations"
    )
    
    args = parser.parse_args()
    
    # List configs
    if args.list:
        configs = list_configs()
        print("Available configurations:")
        for c in configs:
            print(f"  {c}")
        return
    
    # Validate fiber fraction
    if args.fiber_fraction is not None:
        if not 0.0 <= args.fiber_fraction <= 1.0:
            print("ERROR: fiber-fraction must be between 0.0 and 1.0", file=sys.stderr)
            sys.exit(1)
    
    # Get config list
    config_dir = Path(__file__).parent.parent / "configs"
    
    if args.all:
        config_names = [p.stem for p in config_dir.glob("nvidia_*.json")]
    else:
        config_names = [args.config]
    
    all_results = []
    
    for config_name in config_names:
        try:
            config = load_config(config_name, config_dir)
            
            if args.sensitivity:
                print_sensitivity_table(config, args.gpu_cost)
            else:
                result = analyze_cluster(
                    config,
                    verbose=not args.json,
                    include_system_overhead=args.include_system_overhead,
                    override_fiber_fraction=args.fiber_fraction,
                    override_syncs_per_sec=args.syncs_per_sec,
                    gpu_hour_cost=args.gpu_cost
                )
                all_results.append(result)
                
        except FileNotFoundError as e:
            print(f"ERROR: {e}", file=sys.stderr)
        except KeyError as e:
            print(f"ERROR: Invalid config {config_name}: missing key {e}", file=sys.stderr)
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON in {config_name}: {e}", file=sys.stderr)
    
    if args.json and all_results:
        print(json.dumps(all_results, indent=2))


if __name__ == "__main__":
    main()
