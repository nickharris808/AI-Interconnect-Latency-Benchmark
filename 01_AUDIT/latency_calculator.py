#!/usr/bin/env python3
"""
=============================================================================
OPTICAL LATENCY CALCULATOR
AI Interconnect Latency Benchmark - Physics Verification Tool
=============================================================================

This script calculates optical propagation latency for datacenter interconnects,
comparing standard fiber to low-index architected glass (Superluminal Glass).

WHAT THIS CALCULATES:
---------------------
1. Time-of-Flight (ToF): Pure physics propagation delay
   τ_ToF = L × n / c
   
2. System Overhead (Optional): Real-world link components
   τ_total = τ_ToF + τ_SerDes + τ_FEC + τ_switch

The Time-of-Flight is the ONLY component addressable by improved optical media.
System overhead (SerDes, FEC, switch) is fixed regardless of glass type.

MEDIA TYPES:
------------
- vacuum:       n = 1.0000 (theoretical limit)
- superluminal: n = 1.1524 (Patent 4, Gyroid TPMS, 70% void)
- hollow_core:  n = 1.0030 (Hollow-core PCF, very expensive)
- smf28:        n = 1.4682 (Standard single-mode fiber)
- multimode:    n = 1.4900 (Multimode fiber, older datacenters)

SYSTEM OVERHEAD MODEL:
----------------------
Based on published specifications for InfiniBand NDR and NVLink 5.0:

- SerDes (TX + RX):  100 ns (range: 50-150 ns)
- FEC (if enabled):  100 ns (range: 50-200 ns)
- Switch Fabric:     200 ns (range: 100-400 ns)
- Software Stack:    Variable (not modeled)

Total typical overhead: 400 ns (not including software)

SOURCES:
--------
[1] Speed of light: BIPM SI Definition 2019 (exact: 299,792,458 m/s)
[2] SMF-28 index: Corning Datasheet (1.4682 at 1550nm)
[3] Superluminal index: Patent 4, Maxwell-Garnett EMT
[4] InfiniBand NDR: NVIDIA Quantum-2 Specifications
[5] NVLink 5.0: NVIDIA GTC 2024 Technical Brief

=============================================================================
"""

import argparse
import sys
from typing import Dict, Optional, Tuple


# =============================================================================
# PHYSICAL CONSTANTS
# =============================================================================

# Speed of light in vacuum (exact by SI definition, BIPM 2019)
C_VACUUM_M_S = 299_792_458

# Refractive indices of optical media
MEDIA_INDICES = {
    "vacuum":       1.0000,   # Theoretical limit
    "hollow_core":  1.0030,   # Hollow-core PCF (OFS/NKT)
    "superluminal": 1.1524,   # Genesis Superluminal Glass (Patent 4)
    "smf28":        1.4682,   # Corning SMF-28 Ultra
    "multimode":    1.4900,   # OM4 multimode fiber
}

# Friendly names for display
MEDIA_NAMES = {
    "vacuum":       "Vacuum (theoretical)",
    "hollow_core":  "Hollow-Core PCF",
    "superluminal": "Superluminal Glass (Patent 4)",
    "smf28":        "SMF-28 Standard Fiber",
    "multimode":    "OM4 Multimode Fiber",
}


# =============================================================================
# SYSTEM OVERHEAD MODEL
# =============================================================================

# Typical latencies for link components (nanoseconds)
# Source: NVIDIA InfiniBand NDR, NVLink 5.0 specifications
SYSTEM_OVERHEAD_NS = {
    "serdes_tx":      50,   # Serializer at transmitter
    "serdes_rx":      50,   # Deserializer at receiver
    "fec_encode":     50,   # Forward error correction (encoding)
    "fec_decode":     50,   # Forward error correction (decoding)
    "switch_fabric": 200,   # Switch ASIC traversal (per switch)
}

# Overhead scenarios
OVERHEAD_SCENARIOS = {
    "none": {
        "description": "ToF only (no overhead)",
        "serdes": False,
        "fec": False,
        "switches": 0
    },
    "minimal": {
        "description": "Direct link (SerDes only)",
        "serdes": True,
        "fec": False,
        "switches": 0
    },
    "typical": {
        "description": "Typical datacenter (1 switch)",
        "serdes": True,
        "fec": True,
        "switches": 1
    },
    "spine_leaf": {
        "description": "Spine-leaf topology (2 switches)",
        "serdes": True,
        "fec": True,
        "switches": 2
    },
    "fat_tree": {
        "description": "Fat-tree topology (3 switches)",
        "serdes": True,
        "fec": True,
        "switches": 3
    }
}


# =============================================================================
# LATENCY CALCULATIONS
# =============================================================================

def calculate_tof_ns(distance_m: float, refractive_index: float) -> float:
    """
    Calculate one-way time-of-flight in nanoseconds.
    
    Formula: τ = L × n / c
    
    Parameters:
    -----------
    distance_m : float
        Link distance in meters
    refractive_index : float
        Refractive index of the medium
        
    Returns:
    --------
    float : One-way propagation time in nanoseconds
    """
    time_seconds = distance_m * refractive_index / C_VACUUM_M_S
    time_ns = time_seconds * 1e9
    return time_ns


def calculate_system_overhead_ns(scenario: str) -> Tuple[float, Dict]:
    """
    Calculate system overhead for a given network scenario.
    
    Parameters:
    -----------
    scenario : str
        One of: 'none', 'minimal', 'typical', 'spine_leaf', 'fat_tree'
        
    Returns:
    --------
    tuple : (total_overhead_ns, breakdown_dict)
    """
    if scenario not in OVERHEAD_SCENARIOS:
        raise ValueError(f"Unknown scenario: {scenario}")
    
    config = OVERHEAD_SCENARIOS[scenario]
    breakdown = {}
    
    # SerDes (both ends)
    if config["serdes"]:
        breakdown["serdes"] = SYSTEM_OVERHEAD_NS["serdes_tx"] + SYSTEM_OVERHEAD_NS["serdes_rx"]
    else:
        breakdown["serdes"] = 0
    
    # FEC (if enabled)
    if config["fec"]:
        breakdown["fec"] = SYSTEM_OVERHEAD_NS["fec_encode"] + SYSTEM_OVERHEAD_NS["fec_decode"]
    else:
        breakdown["fec"] = 0
    
    # Switch fabric
    breakdown["switches"] = config["switches"] * SYSTEM_OVERHEAD_NS["switch_fabric"]
    
    total = sum(breakdown.values())
    return total, breakdown


def calculate_link_latency(distance_m: float, 
                           media_type: str = "smf28",
                           scenario: str = "none",
                           round_trip: bool = True) -> Dict:
    """
    Calculate complete link latency with optional system overhead.
    
    Parameters:
    -----------
    distance_m : float
        Link distance in meters
    media_type : str
        Optical media type
    scenario : str
        System overhead scenario
    round_trip : bool
        If True, calculate round-trip latency
        
    Returns:
    --------
    dict : Comprehensive latency analysis
    """
    if media_type not in MEDIA_INDICES:
        raise ValueError(f"Unknown media type: {media_type}")
    
    n = MEDIA_INDICES[media_type]
    
    # Time of flight
    tof_one_way_ns = calculate_tof_ns(distance_m, n)
    tof_ns = tof_one_way_ns * (2 if round_trip else 1)
    
    # System overhead
    overhead_ns, overhead_breakdown = calculate_system_overhead_ns(scenario)
    overhead_ns = overhead_ns * (2 if round_trip else 1)  # Overhead at both ends for round-trip
    
    # Total latency
    total_ns = tof_ns + overhead_ns
    
    # Speed calculation
    speed_m_s = C_VACUUM_M_S / n
    speed_km_s = speed_m_s / 1000
    fraction_of_c = 1.0 / n
    
    return {
        "distance_m": distance_m,
        "media_type": media_type,
        "media_name": MEDIA_NAMES[media_type],
        "refractive_index": n,
        "round_trip": round_trip,
        "scenario": scenario,
        "scenario_description": OVERHEAD_SCENARIOS[scenario]["description"],
        "tof_ns": tof_ns,
        "overhead_ns": overhead_ns,
        "overhead_breakdown": overhead_breakdown,
        "total_ns": total_ns,
        "speed_km_s": speed_km_s,
        "fraction_of_c": fraction_of_c,
        "tof_fraction": tof_ns / total_ns if total_ns > 0 else 1.0
    }


def compare_media(distance_m: float, 
                  scenario: str = "none",
                  round_trip: bool = True) -> Dict:
    """
    Compare latency across all media types.
    
    Returns dict with comparisons and savings.
    """
    results = {}
    
    for media_type in MEDIA_INDICES:
        results[media_type] = calculate_link_latency(
            distance_m, media_type, scenario, round_trip
        )
    
    # Calculate savings vs SMF-28
    smf_tof = results["smf28"]["tof_ns"]
    for media_type in results:
        savings = smf_tof - results[media_type]["tof_ns"]
        results[media_type]["savings_vs_smf28_ns"] = savings
        results[media_type]["savings_vs_smf28_pct"] = (savings / smf_tof * 100) if smf_tof > 0 else 0
    
    return results


# =============================================================================
# OUTPUT FORMATTING
# =============================================================================

def print_single_result(result: Dict):
    """Print detailed result for a single media type."""
    print()
    print("=" * 78)
    print("          OPTICAL LATENCY CALCULATION - AI Interconnect Benchmark")
    print("=" * 78)
    
    print(f"\n📐 LINK PARAMETERS:")
    print(f"   Distance:          {result['distance_m']:.1f} m")
    print(f"   Media:             {result['media_name']}")
    print(f"   Refractive Index:  {result['refractive_index']:.4f}")
    print(f"   Mode:              {'Round-Trip' if result['round_trip'] else 'One-Way'}")
    print(f"   Overhead Scenario: {result['scenario_description']}")
    
    print(f"\n⚡ LATENCY BREAKDOWN:")
    print(f"   Time-of-Flight:    {result['tof_ns']:.2f} ns ({result['tof_fraction']*100:.1f}% of total)")
    
    if result['overhead_ns'] > 0:
        print(f"\n   System Overhead:   {result['overhead_ns']:.2f} ns")
        breakdown = result['overhead_breakdown']
        if breakdown.get('serdes', 0) > 0:
            print(f"     - SerDes:        {breakdown['serdes'] * (2 if result['round_trip'] else 1):.0f} ns")
        if breakdown.get('fec', 0) > 0:
            print(f"     - FEC:           {breakdown['fec'] * (2 if result['round_trip'] else 1):.0f} ns")
        if breakdown.get('switches', 0) > 0:
            print(f"     - Switches:      {breakdown['switches'] * (2 if result['round_trip'] else 1):.0f} ns")
    
    print(f"\n   ─────────────────────────────────")
    print(f"   TOTAL LATENCY:     {result['total_ns']:.2f} ns")
    
    print(f"\n🚀 SPEED OF LIGHT IN MEDIUM:")
    print(f"   Speed:             {result['speed_km_s']:,.0f} km/s")
    print(f"   Fraction of c:     {result['fraction_of_c']:.4f} ({result['fraction_of_c']*100:.2f}%)")
    
    if result.get('savings_vs_smf28_ns', 0) > 0:
        print(f"\n💰 SAVINGS VS SMF-28:")
        print(f"   ToF Savings:       {result['savings_vs_smf28_ns']:.2f} ns")
        print(f"   Improvement:       {result['savings_vs_smf28_pct']:.1f}%")
    
    print(f"\n{'='*78}")


def print_comparison_table(results: Dict, distance_m: float, scenario: str, round_trip: bool):
    """Print comparison table for all media types."""
    print()
    print("=" * 78)
    print("          OPTICAL MEDIA COMPARISON - AI Interconnect Benchmark")
    print("=" * 78)
    
    mode = "Round-Trip" if round_trip else "One-Way"
    print(f"\n📐 LINK: {distance_m:.1f} m | Mode: {mode} | Overhead: {OVERHEAD_SCENARIOS[scenario]['description']}")
    
    print(f"\n┌{'─'*28}┬{'─'*10}┬{'─'*12}┬{'─'*12}┬{'─'*12}┐")
    print(f"│ {'Media':<26} │ {'n':>8} │ {'ToF (ns)':>10} │ {'Total (ns)':>10} │ {'Savings':>10} │")
    print(f"├{'─'*28}┼{'─'*10}┼{'─'*12}┼{'─'*12}┼{'─'*12}┤")
    
    # Sort by refractive index
    sorted_media = sorted(results.keys(), key=lambda x: results[x]['refractive_index'])
    
    for media in sorted_media:
        r = results[media]
        name = MEDIA_NAMES[media][:26]
        savings = f"{r['savings_vs_smf28_ns']:.1f} ns" if r['savings_vs_smf28_ns'] > 0 else "—"
        print(f"│ {name:<26} │ {r['refractive_index']:>8.4f} │ {r['tof_ns']:>10.2f} │ {r['total_ns']:>10.2f} │ {savings:>10} │")
    
    print(f"└{'─'*28}┴{'─'*10}┴{'─'*12}┴{'─'*12}┴{'─'*12}┘")
    
    # Highlight superluminal savings
    super_result = results.get("superluminal")
    if super_result:
        print(f"\n✨ SUPERLUMINAL GLASS ADVANTAGE:")
        print(f"   ToF Savings vs SMF-28: {super_result['savings_vs_smf28_ns']:.2f} ns ({super_result['savings_vs_smf28_pct']:.1f}%)")
        print(f"   → Light travels {super_result['speed_km_s'] - results['smf28']['speed_km_s']:,.0f} km/s faster")
    
    print(f"\n{'='*78}")
    
    # Importance of ToF at this distance
    typical_total = results["smf28"]["total_ns"]
    tof_fraction = results["smf28"]["tof_ns"] / typical_total if typical_total > 0 else 1.0
    
    print(f"\n📊 ANALYSIS:")
    print(f"   At {distance_m:.1f}m with {OVERHEAD_SCENARIOS[scenario]['description'].lower()}:")
    print(f"   → Time-of-Flight is {tof_fraction*100:.1f}% of total latency")
    
    if tof_fraction > 0.5:
        print(f"   → ToF DOMINANT: Superluminal Glass provides significant benefit")
    else:
        print(f"   → OVERHEAD DOMINANT: Superluminal benefit is diluted by system latency")
        print(f"      Consider: longer links, fewer switches, or architecture changes")
    
    print()


def print_distance_sweep(media_type: str, scenario: str, round_trip: bool):
    """Print latency vs distance table for a given media type."""
    distances = [10, 25, 50, 100, 200, 500, 1000]
    
    print()
    print("=" * 78)
    print(f"          DISTANCE SWEEP - {MEDIA_NAMES[media_type]}")
    print("=" * 78)
    
    mode = "Round-Trip" if round_trip else "One-Way"
    print(f"\n📐 Media: n = {MEDIA_INDICES[media_type]} | Mode: {mode}")
    print(f"   Overhead: {OVERHEAD_SCENARIOS[scenario]['description']}")
    
    print(f"\n┌{'─'*12}┬{'─'*12}┬{'─'*12}┬{'─'*12}┬{'─'*12}┐")
    print(f"│ {'Distance':>10} │ {'ToF (ns)':>10} │ {'Overhead':>10} │ {'Total':>10} │ {'ToF %':>10} │")
    print(f"├{'─'*12}┼{'─'*12}┼{'─'*12}┼{'─'*12}┼{'─'*12}┤")
    
    for d in distances:
        r = calculate_link_latency(d, media_type, scenario, round_trip)
        print(f"│ {d:>8} m │ {r['tof_ns']:>10.1f} │ {r['overhead_ns']:>10.1f} │ {r['total_ns']:>10.1f} │ {r['tof_fraction']*100:>9.1f}% │")
    
    print(f"└{'─'*12}┴{'─'*12}┴{'─'*12}┴{'─'*12}┴{'─'*12}┘")
    
    print(f"\n📈 OBSERVATION:")
    r_100 = calculate_link_latency(100, media_type, scenario, round_trip)
    r_500 = calculate_link_latency(500, media_type, scenario, round_trip)
    print(f"   At 100m: ToF is {r_100['tof_fraction']*100:.0f}% of total latency")
    print(f"   At 500m: ToF is {r_500['tof_fraction']*100:.0f}% of total latency")
    print(f"   → ToF dominates at longer distances; Superluminal Glass most valuable for > 100m links")
    print()


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Calculate optical propagation latency with system overhead",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s 100                      # 100m, SMF-28, ToF only
  %(prog)s 100 -m superluminal      # 100m, Superluminal Glass
  %(prog)s 200 --compare            # Compare all media at 200m
  %(prog)s 100 --overhead typical   # Include SerDes + FEC + 1 switch
  %(prog)s 100 --overhead fat_tree  # Fat-tree topology (3 switches)
  %(prog)s 200 --sweep              # Distance sweep table
  %(prog)s 100 --one-way            # One-way latency (not round-trip)

Media Types:
  vacuum        n = 1.0000 (theoretical limit)
  hollow_core   n = 1.0030 (hollow-core PCF)
  superluminal  n = 1.1524 (Patent 4 - Superluminal Glass)
  smf28         n = 1.4682 (standard single-mode fiber)
  multimode     n = 1.4900 (OM4 multimode)

Overhead Scenarios:
  none         ToF only (default)
  minimal      SerDes only (direct optical link)
  typical      SerDes + FEC + 1 switch
  spine_leaf   SerDes + FEC + 2 switches
  fat_tree     SerDes + FEC + 3 switches
        """
    )
    
    parser.add_argument(
        "distance",
        type=float,
        help="Link distance in meters"
    )
    parser.add_argument(
        "-m", "--media",
        type=str,
        default="smf28",
        choices=list(MEDIA_INDICES.keys()),
        help="Optical media type (default: smf28)"
    )
    parser.add_argument(
        "-o", "--overhead",
        type=str,
        default="none",
        choices=list(OVERHEAD_SCENARIOS.keys()),
        help="System overhead scenario (default: none)"
    )
    parser.add_argument(
        "--compare", "-c",
        action="store_true",
        help="Compare all media types"
    )
    parser.add_argument(
        "--sweep", "-s",
        action="store_true",
        help="Show distance sweep table"
    )
    parser.add_argument(
        "--one-way",
        action="store_true",
        help="Calculate one-way latency (default: round-trip)"
    )
    
    args = parser.parse_args()
    
    round_trip = not args.one_way
    
    if args.compare:
        results = compare_media(args.distance, args.overhead, round_trip)
        print_comparison_table(results, args.distance, args.overhead, round_trip)
    elif args.sweep:
        print_distance_sweep(args.media, args.overhead, round_trip)
    else:
        result = calculate_link_latency(args.distance, args.media, args.overhead, round_trip)
        results = compare_media(args.distance, args.overhead, round_trip)
        result["savings_vs_smf28_ns"] = results[args.media]["savings_vs_smf28_ns"]
        result["savings_vs_smf28_pct"] = results[args.media]["savings_vs_smf28_pct"]
        print_single_result(result)


if __name__ == "__main__":
    main()
