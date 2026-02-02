#!/usr/bin/env python3
"""
=============================================================================
LATENCY CALCULATOR
AI Interconnect Latency Benchmark
=============================================================================

This script calculates the propagation latency for optical interconnects
at different refractive indices.

THE PROBLEM:
    Standard silica fiber (n=1.45) slows light to 69% of vacuum speed.
    This creates a synchronization lock in large GPU clusters.

THE PHYSICS:
    Speed of light in medium: v = c / n
    One-way latency: t = L × n / c
    
THE OPPORTUNITY:
    Low-index architected glass (n=1.15) moves data at 260,000 km/s.
    That's a 26% speed boost over standard fiber.

=============================================================================
Source: Patent 4 (Photonics) - Superluminal Glass
Data Room: PROVISIONAL_4_PHOTONICS_DATA_ROOM/
Physics: 04_REPRODUCIBILITY_SCRIPTS/generate_low_index_lattice.py
=============================================================================

Author: Genesis Research
License: MIT (this code) / Patent Pending (referenced solutions)
"""

import argparse
import sys

# =============================================================================
# PHYSICAL CONSTANTS
# =============================================================================

# Speed of light in vacuum (exact by SI definition)
C_VACUUM_M_S = 299_792_458          # m/s
C_VACUUM_KM_S = 299_792.458         # km/s

# =============================================================================
# OPTICAL MEDIA
# =============================================================================

MEDIA = {
    "vacuum": {
        "name": "Vacuum",
        "n": 1.0000,
        "source": "Physics definition"
    },
    "superluminal": {
        "name": "Superluminal Glass™",
        "n": 1.1524,  # From Maxwell-Garnett: 30.6% solid, 69.4% void
        "source": "Genesis Patent 4 (Provisional)"
    },
    "hollow_core": {
        "name": "Hollow-Core Fiber",
        "n": 1.003,
        "source": "Lumenisity CoreSmart"
    },
    "silica": {
        "name": "Standard Silica (SiO₂)",
        "n": 1.4500,
        "source": "Corning HPFS datasheet"
    },
    "smf28": {
        "name": "SMF-28 Fiber",
        "n": 1.4682,
        "source": "Corning SMF-28 Ultra"
    },
}


# =============================================================================
# LATENCY CALCULATIONS
# =============================================================================

def calculate_latency_ns(distance_m: float, n: float) -> float:
    """
    Calculate one-way propagation latency in nanoseconds.
    
    Physics:
        t = d × n / c
        
    Args:
        distance_m: Cable/interconnect length in meters
        n: Refractive index of medium
        
    Returns:
        Latency in nanoseconds
    """
    latency_s = (distance_m * n) / C_VACUUM_M_S
    return latency_s * 1e9


def calculate_speed_km_s(n: float) -> float:
    """Calculate speed of light in medium (km/s)."""
    return C_VACUUM_KM_S / n


def calculate_speed_fraction(n: float) -> float:
    """Calculate speed as fraction of c."""
    return 1.0 / n


# =============================================================================
# MAIN BENCHMARK
# =============================================================================

def run_benchmark(cable_length_m: float, verbose: bool = True):
    """
    Run the latency benchmark for a given cable length.
    
    Args:
        cable_length_m: Length of optical interconnect in meters
        verbose: Print detailed output
    """
    
    # Calculate for standard fiber and superluminal glass
    n_standard = MEDIA["silica"]["n"]
    n_superluminal = MEDIA["superluminal"]["n"]
    n_vacuum = MEDIA["vacuum"]["n"]
    
    lat_standard = calculate_latency_ns(cable_length_m, n_standard)
    lat_superluminal = calculate_latency_ns(cable_length_m, n_superluminal)
    lat_vacuum = calculate_latency_ns(cable_length_m, n_vacuum)
    
    speed_standard = calculate_speed_km_s(n_standard)
    speed_superluminal = calculate_speed_km_s(n_superluminal)
    
    gap = lat_standard - lat_superluminal
    gap_vs_vacuum = lat_standard - lat_vacuum
    improvement_pct = (gap / lat_standard) * 100
    
    if verbose:
        print()
        print("=" * 70)
        print("           AI INTERCONNECT LATENCY CALCULATOR")
        print("           The Speed of Light Problem")
        print("=" * 70)
        print()
        print(f"  INPUT: Cable Length = {cable_length_m} meters")
        print()
        print("-" * 70)
        print(f"  {'MEDIUM':<25} {'n':>8} {'SPEED (km/s)':>15} {'LATENCY':>12}")
        print("-" * 70)
        
        for key in ["vacuum", "superluminal", "hollow_core", "silica", "smf28"]:
            medium = MEDIA[key]
            n = medium["n"]
            speed = calculate_speed_km_s(n)
            lat = calculate_latency_ns(cable_length_m, n)
            
            marker = ""
            if key == "superluminal":
                marker = " ← PATENT PENDING"
            elif key == "silica":
                marker = " ← CURRENT"
                
            print(f"  {medium['name']:<25} {n:>8.4f} {speed:>15,.0f} {lat:>10.2f} ns{marker}")
        
        print("-" * 70)
        print()
        print("  ANALYSIS:")
        print(f"    Standard Silica latency:     {lat_standard:.2f} ns")
        print(f"    Superluminal Glass latency:  {lat_superluminal:.2f} ns")
        print(f"    Theoretical minimum (vacuum): {lat_vacuum:.2f} ns")
        print()
        print(f"  ┌─────────────────────────────────────────────────────────────┐")
        print(f"  │  LATENCY GAP: {gap:.2f} ns  ({improvement_pct:.1f}% improvement)           │")
        print(f"  │                                                             │")
        print(f"  │  You are losing {gap:.0f}ns per hop.                              │")
        print(f"  └─────────────────────────────────────────────────────────────┘")
        print()
        
        # Scale analysis
        print("  AT SCALE (100,000-GPU cluster, 1,000 syncs/sec):")
        syncs_per_sec = 1000
        gpus = 100_000
        hops_per_sync = 10  # Average hops in fat-tree
        daily_gap_ns = gap * syncs_per_sec * gpus * hops_per_sync * 86400
        daily_gap_hours = daily_gap_ns / 1e9 / 3600
        
        print(f"    Hops per sync: ~{hops_per_sync}")
        print(f"    Daily latency tax: {daily_gap_hours:.1f} GPU-hours")
        print(f"    Annual cost (@$2/GPU-hr): ${daily_gap_hours * 365 * 2:,.0f}")
        print()
        
        # Training impact
        print("  FEAR: In a trillion-parameter training run, this adds up to")
        print("        WEEKS of wasted compute time.")
        print()
        print("=" * 70)
        print("  SOLUTION: Superluminal Glass™ (Patent Pending)")
        print("            n_eff = 1.15 | Speed = 260,000 km/s")
        print("            Contact: nick@genesis.ai")
        print("=" * 70)
        print()
    
    return {
        "cable_length_m": cable_length_m,
        "latency_standard_ns": lat_standard,
        "latency_superluminal_ns": lat_superluminal,
        "latency_vacuum_ns": lat_vacuum,
        "gap_ns": gap,
        "improvement_pct": improvement_pct,
    }


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Calculate optical interconnect latency",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python latency_calculator.py                 # Default: 100m
  python latency_calculator.py --length 50     # 50 meters
  python latency_calculator.py -l 1000         # 1 kilometer
  
The Problem:
  Standard silica fiber (n=1.45) slows light to 69% of vacuum speed.
  In a 100,000-GPU cluster, this creates a synchronization lock.
  
The Solution:
  Superluminal Glass (n=1.15) moves data at 260,000 km/s.
  That's 26% faster than standard fiber.
  
  Patent Pending. Contact: nick@genesis.ai
"""
    )
    
    parser.add_argument(
        "-l", "--length",
        type=float,
        default=100.0,
        help="Cable length in meters (default: 100)"
    )
    
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Minimal output (just the gap)"
    )
    
    args = parser.parse_args()
    
    if args.quiet:
        result = run_benchmark(args.length, verbose=False)
        print(f"Latency: {result['latency_standard_ns']:.0f}ns (Standard) vs "
              f"{result['latency_superluminal_ns']:.0f}ns (Superluminal). "
              f"Gap: {result['gap_ns']:.0f}ns.")
    else:
        run_benchmark(args.length)


if __name__ == "__main__":
    main()
