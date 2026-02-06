#!/usr/bin/env python3
"""
=============================================================================
FIGURE GENERATION SCRIPT
AI Interconnect Latency Benchmark
=============================================================================

This script generates all visualizations for the benchmark repository.

FIGURES GENERATED:
------------------
1. n_eff_vs_void_fraction.png   - Effective index vs void fraction (EMT comparison)
2. latency_bottleneck.png       - Latency comparison across media types
3. speed_of_light_comparison.png - Speed of light in different media
4. system_latency_breakdown.png  - ToF vs system overhead at various distances
5. annual_savings_sensitivity.png - Economic impact vs sync rate

DEPENDENCIES:
-------------
  pip install matplotlib numpy

=============================================================================
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import math

# Set style
plt.style.use('default')
plt.rcParams['figure.figsize'] = [10, 6]
plt.rcParams['figure.dpi'] = 150
plt.rcParams['font.size'] = 11
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['axes.labelsize'] = 12

# Output directory
OUTPUT_DIR = Path(__file__).parent

# Physical constants
C_VACUUM = 299_792_458  # m/s
N_SILICA = 1.45
N_SMF28 = 1.4682


def maxwell_garnett(f_void: float, n_solid: float = N_SILICA) -> float:
    """Calculate effective refractive index using Maxwell-Garnett."""
    eps_solid = n_solid ** 2
    eps_void = 1.0
    f_solid = 1 - f_void
    
    eps_eff = eps_void + f_solid * (eps_solid - eps_void)
    return math.sqrt(eps_eff)


def bruggeman(f_void: float, n_solid: float = N_SILICA, tol: float = 1e-10) -> float:
    """Calculate effective refractive index using Bruggeman."""
    eps_solid = n_solid ** 2
    eps_void = 1.0
    f_solid = 1 - f_void
    
    eps_eff = f_void * eps_void + f_solid * eps_solid  # Initial guess
    
    for _ in range(100):
        term1 = f_void * (eps_void - eps_eff) / (eps_void + 2*eps_eff)
        term2 = f_solid * (eps_solid - eps_eff) / (eps_solid + 2*eps_eff)
        residual = term1 + term2
        
        if abs(residual) < tol:
            break
        
        # Newton-Raphson update
        dterm1 = -f_void * (eps_void + 2*eps_void) / (eps_void + 2*eps_eff)**2
        dterm2 = -f_solid * (eps_solid + 2*eps_solid) / (eps_solid + 2*eps_eff)**2
        derivative = dterm1 + dterm2
        
        if abs(derivative) > 1e-15:
            eps_eff = eps_eff - residual / derivative
        
        eps_eff = max(1.0, min(eps_eff, eps_solid))
    
    return math.sqrt(eps_eff)


def figure_1_neff_vs_void():
    """
    Figure 1: Effective refractive index vs void fraction
    Compares Maxwell-Garnett and Bruggeman EMT
    """
    print("Generating: n_eff_vs_void_fraction.png")
    
    void_fractions = np.linspace(0.0, 0.85, 100)
    n_eff_mg = [maxwell_garnett(f) for f in void_fractions]
    n_eff_br = [bruggeman(f) for f in void_fractions]
    n_eff_linear = [1.0 * f + N_SILICA * (1-f) for f in void_fractions]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    ax.plot(void_fractions * 100, n_eff_mg, 'b-', linewidth=2, label='Maxwell-Garnett')
    ax.plot(void_fractions * 100, n_eff_br, 'r--', linewidth=2, label='Bruggeman')
    ax.plot(void_fractions * 100, n_eff_linear, 'g:', linewidth=1.5, label='Linear (unphysical)')
    
    # Mark key points
    ax.axhline(y=1.20, color='orange', linestyle='--', alpha=0.7, label='Superluminal threshold (n=1.20)')
    ax.axhline(y=1.1524, color='purple', linestyle=':', alpha=0.7, label='Patent 4 target (n=1.15)')
    
    # Mark Patent 4 operating point
    ax.scatter([70], [1.1524], s=100, c='purple', zorder=5, marker='*')
    ax.annotate('Patent 4\n(70% void)', xy=(70, 1.1524), xytext=(55, 1.22),
                fontsize=10, arrowprops=dict(arrowstyle='->', color='purple'))
    
    ax.set_xlabel('Void Fraction (%)')
    ax.set_ylabel('Effective Refractive Index (n_eff)')
    ax.set_title('Effective Refractive Index vs Void Fraction\nAir-Silica Architected Glass')
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0, 85)
    ax.set_ylim(1.0, 1.5)
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'n_eff_vs_void_fraction.png', dpi=150, bbox_inches='tight')
    plt.close()


def figure_2_latency_comparison():
    """
    Figure 2: Latency comparison across media types
    """
    print("Generating: latency_bottleneck.png")
    
    media = {
        'Vacuum': 1.0000,
        'Hollow-Core PCF': 1.0030,
        'Superluminal Glass': 1.1524,
        'SMF-28 Fiber': 1.4682,
        'Multimode Fiber': 1.4900,
    }
    
    distances = [50, 100, 200, 500]
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    # Left panel: Latency vs distance
    ax1 = axes[0]
    colors = ['green', 'cyan', 'purple', 'red', 'orange']
    
    for (name, n), color in zip(media.items(), colors):
        latencies = [2 * d * n / C_VACUUM * 1e9 for d in distances]
        ax1.plot(distances, latencies, 'o-', color=color, linewidth=2, 
                 markersize=8, label=f'{name} (n={n})')
    
    ax1.set_xlabel('Distance (m)')
    ax1.set_ylabel('Round-Trip Latency (ns)')
    ax1.set_title('Optical Latency vs Distance')
    ax1.legend(loc='upper left', fontsize=9)
    ax1.grid(True, alpha=0.3)
    ax1.set_xlim(0, 550)
    
    # Right panel: Bar chart at 200m
    ax2 = axes[1]
    distance = 200  # meters
    
    names = list(media.keys())
    latencies = [2 * distance * n / C_VACUUM * 1e9 for n in media.values()]
    
    bars = ax2.barh(names, latencies, color=colors)
    
    # Add value labels
    for bar, lat in zip(bars, latencies):
        ax2.text(bar.get_width() + 20, bar.get_y() + bar.get_height()/2, 
                 f'{lat:.1f} ns', va='center', fontsize=10)
    
    # Highlight savings
    smf_lat = 2 * distance * 1.4682 / C_VACUUM * 1e9
    super_lat = 2 * distance * 1.1524 / C_VACUUM * 1e9
    savings = smf_lat - super_lat
    
    ax2.axvline(x=super_lat, color='purple', linestyle='--', alpha=0.5)
    ax2.axvline(x=smf_lat, color='red', linestyle='--', alpha=0.5)
    
    ax2.set_xlabel('Round-Trip Latency (ns)')
    ax2.set_title(f'Latency Comparison at {distance}m\nSuperluminal saves {savings:.0f} ns per hop')
    ax2.set_xlim(0, max(latencies) * 1.3)
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'latency_bottleneck.png', dpi=150, bbox_inches='tight')
    plt.close()


def figure_3_speed_comparison():
    """
    Figure 3: Speed of light in different media
    """
    print("Generating: speed_of_light_comparison.png")
    
    media = {
        'Vacuum': 1.0000,
        'Hollow-Core PCF': 1.0030,
        'Superluminal Glass\n(Patent 4)': 1.1524,
        'SMF-28 Fiber': 1.4682,
    }
    
    speeds = {name: C_VACUUM / n / 1000 for name, n in media.items()}  # km/s
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    names = list(speeds.keys())
    values = list(speeds.values())
    colors = ['green', 'cyan', 'purple', 'red']
    
    bars = ax.bar(names, values, color=colors, edgecolor='black', linewidth=1.5)
    
    # Add value labels
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 3000, 
                f'{val:,.0f}\nkm/s', ha='center', fontsize=10)
    
    # Add percentage of c
    for bar, (name, n) in zip(bars, media.items()):
        pct = 100 / n
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height()/2, 
                f'{pct:.1f}%\nof c', ha='center', va='center', fontsize=12, 
                fontweight='bold', color='white')
    
    ax.set_ylabel('Speed of Light (km/s)')
    ax.set_title('Speed of Light in Optical Media\nSlower glass = slower data')
    ax.set_ylim(0, 320000)
    
    # Add horizontal line at vacuum speed
    ax.axhline(y=C_VACUUM/1000, color='green', linestyle='--', alpha=0.3, label='Vacuum limit')
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'speed_of_light_comparison.png', dpi=150, bbox_inches='tight')
    plt.close()


def figure_4_system_breakdown():
    """
    Figure 4: ToF vs system overhead at various distances
    """
    print("Generating: system_latency_breakdown.png")
    
    distances = [10, 25, 50, 100, 200, 500, 1000]
    
    # System overhead (fixed)
    serdes = 200  # ns
    fec = 200     # ns
    switch = 200  # ns
    total_overhead = serdes + fec + switch  # 600 ns
    
    # Calculate ToF at each distance (SMF-28, round-trip)
    tof = [2 * d * N_SMF28 / C_VACUUM * 1e9 for d in distances]
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Stacked bar chart
    x = np.arange(len(distances))
    width = 0.6
    
    # Bottom: system overhead (fixed)
    ax.bar(x, [total_overhead] * len(distances), width, label='System Overhead\n(SerDes+FEC+Switch)', 
           color='gray', alpha=0.7)
    
    # Top: ToF (variable)
    ax.bar(x, tof, width, bottom=[total_overhead] * len(distances), 
           label='Time-of-Flight\n(SMF-28)', color='red', alpha=0.8)
    
    # Calculate and annotate ToF percentage
    for i, (d, t) in enumerate(zip(distances, tof)):
        total = total_overhead + t
        tof_pct = t / total * 100
        ax.text(i, total + 50, f'{tof_pct:.0f}%', ha='center', fontsize=10, fontweight='bold')
    
    ax.set_xticks(x)
    ax.set_xticklabels([f'{d}m' for d in distances])
    ax.set_xlabel('Link Distance')
    ax.set_ylabel('Total Latency (ns)')
    ax.set_title('System Latency Breakdown: ToF vs Overhead\nNumbers show ToF percentage of total')
    ax.legend(loc='upper left')
    ax.grid(True, alpha=0.3, axis='y')
    
    # Add annotation
    ax.annotate('ToF dominates\nat longer distances', xy=(5.5, 4500), fontsize=11,
                arrowprops=dict(arrowstyle='->', color='red'),
                xytext=(4, 6000))
    ax.annotate('Overhead dominates\nat short distances', xy=(0.5, 700), fontsize=11,
                arrowprops=dict(arrowstyle='->', color='gray'),
                xytext=(1.5, 2000))
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'system_latency_breakdown.png', dpi=150, bbox_inches='tight')
    plt.close()


def figure_5_savings_sensitivity():
    """
    Figure 5: Annual savings sensitivity to sync rate
    """
    print("Generating: annual_savings_sensitivity.png")
    
    # Fixed parameters (GB200 NVL72)
    gpus = 4608
    distance = 200
    hops = 8
    fiber_fraction = 0.70
    gpu_cost = 2.00
    
    sync_rates = np.logspace(1, 4, 50)  # 10 to 10,000 syncs/sec
    
    # Calculate savings
    tof_smf = 2 * distance * N_SMF28 / C_VACUUM * 1e9
    tof_super = 2 * distance * 1.1524 / C_VACUUM * 1e9
    savings_per_hop = tof_smf - tof_super
    
    annual_savings = []
    for rate in sync_rates:
        effective_syncs = rate * fiber_fraction
        daily_savings_ns = effective_syncs * 86400 * hops * savings_per_hop
        daily_gpu_hours = (daily_savings_ns / 1e9) * gpus / 3600
        annual = daily_gpu_hours * 365 * gpu_cost
        annual_savings.append(annual)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    ax.loglog(sync_rates, annual_savings, 'b-', linewidth=2)
    
    # Mark key sync rates
    key_rates = [100, 500, 1000, 2000, 5000]
    for rate in key_rates:
        idx = np.argmin(np.abs(sync_rates - rate))
        ax.scatter([rate], [annual_savings[idx]], s=80, c='red', zorder=5)
        ax.annotate(f'{rate} sync/s\n${annual_savings[idx]:,.0f}/yr', 
                    xy=(rate, annual_savings[idx]),
                    xytext=(rate*1.5, annual_savings[idx]*0.6),
                    fontsize=9, arrowprops=dict(arrowstyle='->', color='gray'))
    
    ax.set_xlabel('Synchronization Rate (syncs/second)')
    ax.set_ylabel('Annual Savings (USD)')
    ax.set_title(f'Sensitivity Analysis: Annual Savings vs Sync Rate\nGB200 NVL72: {gpus} GPUs, {distance}m fiber, {fiber_fraction*100:.0f}% fiber fraction')
    ax.grid(True, alpha=0.3, which='both')
    
    # Add reference bands
    ax.axhspan(10000, 100000, alpha=0.1, color='yellow', label='Measurable ($10K-$100K)')
    ax.axhspan(100000, 1000000, alpha=0.1, color='orange', label='Significant ($100K-$1M)')
    ax.axhspan(1000000, 10000000, alpha=0.1, color='red', label='Critical (>$1M)')
    
    ax.legend(loc='lower right')
    ax.set_xlim(10, 15000)
    ax.set_ylim(1000, 5000000)
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'annual_savings_sensitivity.png', dpi=150, bbox_inches='tight')
    plt.close()


def main():
    print("=" * 60)
    print("AI Interconnect Latency Benchmark - Figure Generation")
    print("=" * 60)
    print()
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Generate all figures
    figure_1_neff_vs_void()
    figure_2_latency_comparison()
    figure_3_speed_comparison()
    figure_4_system_breakdown()
    figure_5_savings_sensitivity()
    
    print()
    print("=" * 60)
    print(f"All figures saved to: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
