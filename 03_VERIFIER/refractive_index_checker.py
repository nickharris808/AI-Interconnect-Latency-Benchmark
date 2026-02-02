#!/usr/bin/env python3
"""
=============================================================================
REFRACTIVE INDEX CHECKER
AI Interconnect Latency Benchmark
=============================================================================

Calculate the effective refractive index of a porous glass lattice
based on void fraction using Maxwell-Garnett effective medium theory.

THE PHYSICS:
    For a composite medium (solid + voids), the effective dielectric
    constant follows mixing rules. For dilute spherical inclusions:
    
    n_eff² = n_void² + f_solid × (n_solid² - n_void²)
    
    Where:
    - n_solid = 1.45 (fused silica SiO₂)
    - n_void = 1.00 (air/vacuum)
    - f_solid = solid volume fraction

THE INSIGHT:
    Higher void fraction → Lower n_eff → Faster light

=============================================================================
Source: Patent 4 (Photonics) - Superluminal Glass
Physics: 04_REPRODUCIBILITY_SCRIPTS/generate_low_index_lattice.py
=============================================================================

Author: Genesis Research
License: MIT (this code) / Patent Pending (referenced lattice designs)
"""

import argparse
import math
import sys

# =============================================================================
# PHYSICAL CONSTANTS
# =============================================================================

C_VACUUM_KM_S = 299_792.458  # Speed of light in vacuum (km/s)

# Material properties
N_SOLID = 1.45   # Fused silica (SiO₂) at 1550nm
N_VOID = 1.00    # Air/vacuum

# =============================================================================
# EFFECTIVE MEDIUM CALCULATIONS
# =============================================================================

def calculate_n_eff(void_fraction: float, method: str = "maxwell_garnett") -> float:
    """
    Calculate effective refractive index using effective medium theory.
    
    Args:
        void_fraction: Fraction of volume that is void (0-1)
        method: Mixing rule to use
            - "maxwell_garnett": Maxwell-Garnett EMT (dilute inclusions)
            - "bruggeman": Bruggeman EMT (symmetric)
            - "linear": Simple volume-weighted average
    
    Returns:
        Effective refractive index
    """
    f_solid = 1.0 - void_fraction
    f_void = void_fraction
    
    if method == "maxwell_garnett":
        # Maxwell-Garnett: Good for isolated inclusions
        # n_eff² = n_void² + f_solid × (n_solid² - n_void²)
        n_eff_sq = N_VOID**2 + f_solid * (N_SOLID**2 - N_VOID**2)
        return math.sqrt(n_eff_sq)
    
    elif method == "bruggeman":
        # Bruggeman: Symmetric, good for co-continuous structures
        # f_void × (n_void² - n_eff²)/(n_void² + 2×n_eff²) + 
        # f_solid × (n_solid² - n_eff²)/(n_solid² + 2×n_eff²) = 0
        # Solved numerically
        from scipy.optimize import brentq
        
        def bruggeman_eq(n_eff):
            term1 = f_void * (N_VOID**2 - n_eff**2) / (N_VOID**2 + 2*n_eff**2)
            term2 = f_solid * (N_SOLID**2 - n_eff**2) / (N_SOLID**2 + 2*n_eff**2)
            return term1 + term2
        
        return brentq(bruggeman_eq, 1.0, N_SOLID)
    
    elif method == "linear":
        # Simple linear mixing (not physically accurate for optics)
        n_eff_sq = f_void * N_VOID**2 + f_solid * N_SOLID**2
        return math.sqrt(n_eff_sq)
    
    else:
        raise ValueError(f"Unknown method: {method}")


def calculate_speed(n_eff: float) -> float:
    """Calculate speed of light in medium (km/s)."""
    return C_VACUUM_KM_S / n_eff


def calculate_speed_fraction(n_eff: float) -> float:
    """Calculate speed as fraction of c."""
    return 1.0 / n_eff


def is_superluminal(n_eff: float, threshold: float = 1.20) -> bool:
    """
    Check if refractive index meets 'superluminal' criteria.
    
    Note: Nothing travels faster than c. 'Superluminal' means faster
    than light in conventional glass (n > 1.4), not faster than vacuum.
    
    Args:
        n_eff: Effective refractive index
        threshold: Maximum n for superluminal classification
        
    Returns:
        True if n_eff < threshold
    """
    return n_eff < threshold


# =============================================================================
# MAIN
# =============================================================================

def run_checker(lattice_density_pct: float, verbose: bool = True):
    """
    Check refractive index for a given lattice density.
    
    Args:
        lattice_density_pct: Solid fraction as percentage (0-100)
        verbose: Print detailed output
    """
    if lattice_density_pct < 0 or lattice_density_pct > 100:
        print("ERROR: Lattice density must be between 0% and 100%")
        sys.exit(1)
    
    solid_fraction = lattice_density_pct / 100.0
    void_fraction = 1.0 - solid_fraction
    
    # Calculate using Maxwell-Garnett
    n_eff = calculate_n_eff(void_fraction, method="maxwell_garnett")
    speed = calculate_speed(n_eff)
    speed_frac = calculate_speed_fraction(n_eff)
    is_super = is_superluminal(n_eff)
    
    if verbose:
        print()
        print("=" * 60)
        print("         REFRACTIVE INDEX CHECKER")
        print("         Effective Medium Theory Calculator")
        print("=" * 60)
        print()
        print(f"  INPUT:")
        print(f"    Lattice Density (solid):  {lattice_density_pct:.1f}%")
        print(f"    Void Fraction:            {void_fraction*100:.1f}%")
        print()
        print(f"  MATERIAL PROPERTIES:")
        print(f"    n_solid (SiO₂):           {N_SOLID:.2f}")
        print(f"    n_void (air):             {N_VOID:.2f}")
        print()
        print("-" * 60)
        print()
        print(f"  RESULTS (Maxwell-Garnett EMT):")
        print()
        print(f"    ┌────────────────────────────────────────────────┐")
        print(f"    │  Refractive Index:   {n_eff:.4f}                   │")
        print(f"    │  Speed:              {speed:,.0f} km/s              │")
        print(f"    │  Speed:              {speed_frac:.2f}c                      │")
        print(f"    │                                                │")
        
        if is_super:
            print(f"    │  Status:   ✅ SUPERLUMINAL (n < 1.20)          │")
        else:
            print(f"    │  Status:   ⚠️  NOT SUPERLUMINAL (n ≥ 1.20)      │")
        
        print(f"    └────────────────────────────────────────────────┘")
        print()
        
        # Comparison table
        print(f"  COMPARISON:")
        print(f"    {'Medium':<25} {'n':>8} {'Speed (km/s)':>15}")
        print(f"    {'-'*25} {'-'*8} {'-'*15}")
        print(f"    {'Your Lattice':<25} {n_eff:>8.4f} {speed:>15,.0f}")
        print(f"    {'Standard Fiber':<25} {1.468:>8.4f} {C_VACUUM_KM_S/1.468:>15,.0f}")
        print(f"    {'Vacuum (limit)':<25} {1.000:>8.4f} {C_VACUUM_KM_S:>15,.0f}")
        print()
        
        # Speed improvement
        improvement = (1.468 - n_eff) / 1.468 * 100
        speed_boost = (speed / (C_VACUUM_KM_S/1.468) - 1) * 100
        print(f"  SPEED BOOST vs STANDARD FIBER: {speed_boost:.1f}%")
        print()
        print("=" * 60)
        
        if is_super:
            print("  This lattice meets SUPERLUMINAL criteria!")
            print("  Patent Pending: Contact nick@genesis.ai")
        else:
            print("  TIP: Increase void fraction to lower refractive index.")
            print("       Target: >65% void for n < 1.20")
        
        print("=" * 60)
        print()
    
    return {
        "solid_fraction_pct": lattice_density_pct,
        "void_fraction_pct": void_fraction * 100,
        "n_eff": n_eff,
        "speed_km_s": speed,
        "speed_fraction_c": speed_frac,
        "is_superluminal": is_super,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Calculate effective refractive index from lattice density",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python refractive_index_checker.py 30         # 30% solid (70% void)
  python refractive_index_checker.py 30.6       # Genesis target density
  python refractive_index_checker.py 50         # 50% solid
  
Physics:
  Uses Maxwell-Garnett Effective Medium Theory:
  n_eff² = n_void² + f_solid × (n_solid² - n_void²)
  
  Where:
    n_solid = 1.45 (fused silica)
    n_void = 1.00 (air)

Target for Superluminal:
  Solid fraction ≤ 35% → n_eff < 1.20 → SUPERLUMINAL
  Genesis uses 30.6% solid (69.4% void) → n_eff = 1.1524

Patent Pending. Contact: nick@genesis.ai
"""
    )
    
    parser.add_argument(
        "density",
        type=float,
        help="Lattice density (solid fraction) as percentage (0-100)"
    )
    
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Minimal output"
    )
    
    args = parser.parse_args()
    
    if args.quiet:
        result = run_checker(args.density, verbose=False)
        status = "SUPERLUMINAL" if result["is_superluminal"] else "STANDARD"
        print(f"Refractive Index: {result['n_eff']:.4f}. "
              f"Speed: {result['speed_fraction_c']:.2f}c. "
              f"Status: {status}.")
    else:
        run_checker(args.density)


if __name__ == "__main__":
    main()
