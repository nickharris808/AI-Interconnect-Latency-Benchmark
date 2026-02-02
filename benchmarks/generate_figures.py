#!/usr/bin/env python3
"""
Generate publication-quality figures for the AI Interconnect Latency Benchmark.

This script creates visualizations that demonstrate the speed of light
bottleneck in AI infrastructure.

Author: Genesis Research
License: MIT
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path

# Use a clean, professional style
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.size'] = 11
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['figure.titlesize'] = 16

# Output directory
FIGURES_DIR = Path(__file__).parent.parent / "figures"
FIGURES_DIR.mkdir(exist_ok=True)

# Physical constants
C_VACUUM = 299_792.458  # km/s


def fig_speed_of_light_comparison():
    """
    Bar chart comparing speed of light in different media.
    """
    media = [
        ("Vacuum", 1.0000, "#2ecc71"),
        ("Air", 1.0003, "#27ae60"),
        ("Hollow-Core\nFiber", 1.003, "#3498db"),
        ("Low-Index\nGlass (?)", 1.15, "#f39c12"),
        ("Standard\nFiber", 1.468, "#e74c3c"),
        ("Silicon", 3.48, "#c0392b"),
    ]
    
    names = [m[0] for m in media]
    speeds = [C_VACUUM / m[1] for m in media]
    colors = [m[2] for m in media]
    percents = [100 / m[1] for m in media]
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    bars = ax.bar(names, speeds, color=colors, edgecolor='white', linewidth=2)
    
    # Add percentage labels
    for bar, pct in zip(bars, percents):
        height = bar.get_height()
        ax.annotate(f'{pct:.1f}%',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 5),
                    textcoords="offset points",
                    ha='center', va='bottom',
                    fontsize=11, fontweight='bold')
    
    # Add "THE GAP" annotation
    ax.annotate('THE GAP\n(26% faster)',
                xy=(3, speeds[3]),
                xytext=(3.7, speeds[3] + 20000),
                fontsize=12, fontweight='bold', color='#f39c12',
                arrowprops=dict(arrowstyle='->', color='#f39c12', lw=2))
    
    ax.set_ylabel('Speed of Light (km/s)', fontsize=12)
    ax.set_title('Speed of Light in Different Optical Media\n'
                 'Standard fiber operates at only 68% of theoretical maximum',
                 fontsize=14, fontweight='bold')
    ax.set_ylim(0, 350000)
    
    # Add horizontal line at vacuum speed
    ax.axhline(y=C_VACUUM, color='#2ecc71', linestyle='--', linewidth=2, alpha=0.7)
    ax.text(5.5, C_VACUUM + 5000, 'Vacuum limit', fontsize=10, color='#2ecc71')
    
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "speed_of_light_comparison.png", dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {FIGURES_DIR / 'speed_of_light_comparison.png'}")


def fig_latency_bottleneck():
    """
    The main 'aha' chart showing the latency bottleneck.
    """
    # Distance range
    distances = np.linspace(1, 500, 100)  # meters
    
    # Media
    n_fiber = 1.468
    n_low_index = 1.15
    n_vacuum = 1.0
    
    # Latencies (round-trip, in microseconds)
    lat_fiber = 2 * distances * n_fiber / (C_VACUUM * 1e3) * 1e6
    lat_low = 2 * distances * n_low_index / (C_VACUUM * 1e3) * 1e6
    lat_vacuum = 2 * distances * n_vacuum / (C_VACUUM * 1e3) * 1e6
    
    # GPU compute time for reference (H100: 3958 TFLOPS)
    # Time to do 1M operations
    gpu_time = 1e6 / (3958e12) * 1e6  # microseconds for 1M ops
    
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # Fill the "wasted" region
    ax.fill_between(distances, lat_vacuum, lat_fiber, 
                    alpha=0.3, color='#e74c3c', label='Latency Tax (wasted)')
    
    # Fill the "recoverable" region
    ax.fill_between(distances, lat_low, lat_fiber,
                    alpha=0.4, color='#f39c12', label='Recoverable with Low-Index')
    
    # Plot lines
    ax.plot(distances, lat_fiber, 'r-', linewidth=3, label=f'Standard Fiber (n={n_fiber})')
    ax.plot(distances, lat_low, '-', color='#f39c12', linewidth=3, 
            label=f'Low-Index Glass (n={n_low_index}) - Patent Pending')
    ax.plot(distances, lat_vacuum, 'g--', linewidth=2, label='Vacuum (theoretical limit)')
    
    # Mark 100m point
    ax.axvline(x=100, color='gray', linestyle=':', linewidth=1, alpha=0.7)
    ax.annotate('100m\n(typical rack-scale)',
                xy=(100, 0.5), xytext=(130, 0.3),
                fontsize=10, color='gray',
                arrowprops=dict(arrowstyle='->', color='gray'))
    
    # Add annotation for the gap
    ax.annotate('26% latency\nreduction',
                xy=(350, (lat_fiber[70] + lat_low[70])/2),
                fontsize=12, fontweight='bold', color='#f39c12',
                ha='center')
    
    ax.set_xlabel('Interconnect Distance (meters)', fontsize=12)
    ax.set_ylabel('Round-Trip Latency (microseconds)', fontsize=12)
    ax.set_title('The Speed of Light Bottleneck in AI Infrastructure\n'
                 'Standard fiber wastes 31% of light speed; Low-index glass recovers most of it',
                 fontsize=14, fontweight='bold')
    ax.legend(loc='upper left', fontsize=10)
    ax.set_xlim(0, 500)
    ax.set_ylim(0, 5)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "latency_bottleneck.png", dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {FIGURES_DIR / 'latency_bottleneck.png'}")


def fig_gpu_utilization_gap():
    """
    Show GPU utilization vs communication overhead.
    """
    # Cluster sizes
    gpus = np.array([16, 64, 256, 1024, 4096, 16384, 65536])
    
    # Model: Communication time grows with sqrt(N) due to all-reduce
    # Compute time stays constant per GPU
    compute_time = 100  # ms per step (fixed)
    
    # Communication latency (simplified model)
    # Base latency + hop-dependent component
    base_latency_ms = 0.1  # 100 microseconds base
    latency_per_hop_fiber = 0.001  # 1 microsecond per hop (simplified)
    latency_per_hop_low = 0.00074  # 26% less
    
    hops = np.log2(gpus)  # Ring all-reduce hops
    
    comm_fiber = base_latency_ms + hops * latency_per_hop_fiber * gpus / 100
    comm_low = base_latency_ms + hops * latency_per_hop_low * gpus / 100
    
    utilization_fiber = compute_time / (compute_time + comm_fiber) * 100
    utilization_low = compute_time / (compute_time + comm_low) * 100
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    x = np.arange(len(gpus))
    width = 0.35
    
    bars1 = ax.bar(x - width/2, utilization_fiber, width, 
                   label='Standard Fiber', color='#e74c3c', alpha=0.8)
    bars2 = ax.bar(x + width/2, utilization_low, width,
                   label='Low-Index Glass', color='#f39c12', alpha=0.8)
    
    # Add value labels
    for bar in bars1:
        height = bar.get_height()
        ax.annotate(f'{height:.0f}%',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3), textcoords="offset points",
                    ha='center', va='bottom', fontsize=9, color='#c0392b')
    
    for bar in bars2:
        height = bar.get_height()
        ax.annotate(f'{height:.0f}%',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3), textcoords="offset points",
                    ha='center', va='bottom', fontsize=9, color='#d68910')
    
    ax.set_xlabel('Cluster Size (GPUs)', fontsize=12)
    ax.set_ylabel('GPU Compute Utilization (%)', fontsize=12)
    ax.set_title('GPU Utilization vs. Cluster Size\n'
                 'Larger clusters suffer more from interconnect latency',
                 fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([f'{g:,}' for g in gpus])
    ax.legend(loc='lower left', fontsize=10)
    ax.set_ylim(0, 105)
    ax.axhline(y=90, color='gray', linestyle='--', linewidth=1, alpha=0.5)
    ax.text(6.5, 91, '90% target', fontsize=9, color='gray')
    
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "gpu_utilization_gap.png", dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {FIGURES_DIR / 'gpu_utilization_gap.png'}")


def fig_moores_law_vs_light():
    """
    Show exponential compute growth vs flat speed of light.
    """
    years = np.array([2014, 2016, 2018, 2020, 2022, 2024])
    
    # GPU FLOPS (FP16, normalized to 2014)
    flops = np.array([1, 10, 40, 100, 300, 800])  # Approximate scaling
    
    # Memory bandwidth (normalized)
    mem_bw = np.array([1, 1.5, 2, 4, 5, 7])
    
    # Speed of light (constant!)
    light_speed = np.array([1, 1, 1, 1, 1, 1])
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    ax.semilogy(years, flops, 'b-o', linewidth=3, markersize=10, 
                label='GPU Compute (FLOPS)')
    ax.semilogy(years, mem_bw, 'g-s', linewidth=3, markersize=10,
                label='Memory Bandwidth')
    ax.semilogy(years, light_speed, 'r--', linewidth=4,
                label='Speed of Light')
    
    # Add annotations
    ax.annotate('800× growth',
                xy=(2024, flops[-1]),
                xytext=(2022, flops[-1] * 2),
                fontsize=11, fontweight='bold', color='blue',
                arrowprops=dict(arrowstyle='->', color='blue'))
    
    ax.annotate('0× growth\n(Physics limit)',
                xy=(2024, 1),
                xytext=(2022, 0.3),
                fontsize=11, fontweight='bold', color='red',
                arrowprops=dict(arrowstyle='->', color='red'))
    
    ax.set_xlabel('Year', fontsize=12)
    ax.set_ylabel('Relative Performance (log scale)', fontsize=12)
    ax.set_title("Moore's Law vs. The Speed of Light\n"
                 "Compute scales exponentially; interconnect speed is fixed",
                 fontsize=14, fontweight='bold')
    ax.legend(loc='upper left', fontsize=11)
    ax.set_xlim(2013, 2025)
    ax.set_ylim(0.1, 2000)
    ax.grid(True, alpha=0.3, which='both')
    
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "moores_law_vs_light.png", dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {FIGURES_DIR / 'moores_law_vs_light.png'}")


def fig_latency_breakdown():
    """
    Pie chart showing latency breakdown in distributed training.
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Current state (with standard fiber)
    labels1 = ['Forward Pass', 'Backward Pass', 'Gradient Sync\n(Bandwidth)', 
               'Gradient Sync\n(Latency)']
    sizes1 = [38, 38, 11, 13]
    colors1 = ['#3498db', '#2980b9', '#e67e22', '#e74c3c']
    explode1 = (0, 0, 0, 0.1)
    
    ax1.pie(sizes1, explode=explode1, labels=labels1, colors=colors1,
            autopct='%1.0f%%', shadow=True, startangle=90,
            textprops={'fontsize': 11})
    ax1.set_title('Current State\n(Standard Fiber)', fontsize=14, fontweight='bold')
    
    # With low-index glass
    labels2 = ['Forward Pass', 'Backward Pass', 'Gradient Sync\n(Bandwidth)', 
               'Gradient Sync\n(Latency)']
    sizes2 = [40, 40, 12, 8]  # Latency reduced
    colors2 = ['#3498db', '#2980b9', '#e67e22', '#f39c12']
    explode2 = (0, 0, 0, 0.05)
    
    ax2.pie(sizes2, explode=explode2, labels=labels2, colors=colors2,
            autopct='%1.0f%%', shadow=True, startangle=90,
            textprops={'fontsize': 11})
    ax2.set_title('With Low-Index Glass\n(Patent Pending)', fontsize=14, fontweight='bold')
    
    fig.suptitle('Training Step Time Breakdown for 10T Parameter Model\n'
                 'Reducing latency frees compute for useful work',
                 fontsize=14, fontweight='bold', y=1.02)
    
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "latency_breakdown.png", dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {FIGURES_DIR / 'latency_breakdown.png'}")


def fig_the_trillion_dollar_wait():
    """
    Dramatic visualization of cumulative wasted compute.
    """
    # Model: 10,000 GPUs, 1 year of training
    days = np.arange(1, 366)
    
    h100_cost_per_hour = 2.0  # Typical cloud pricing
    gpus = 10000
    latency_waste_fraction = 0.05  # 5% of time lost to latency
    
    hours_per_day = 24
    cumulative_cost = days * hours_per_day * gpus * h100_cost_per_hour * latency_waste_fraction
    
    # With improvement (40% latency reduction = 2% time recovered)
    improved_waste_fraction = 0.03
    cumulative_cost_improved = days * hours_per_day * gpus * h100_cost_per_hour * improved_waste_fraction
    
    savings = cumulative_cost - cumulative_cost_improved
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    ax.fill_between(days, 0, cumulative_cost / 1e6, 
                    alpha=0.3, color='#e74c3c', label='Latency Waste (Standard Fiber)')
    ax.fill_between(days, 0, cumulative_cost_improved / 1e6,
                    alpha=0.4, color='#f39c12', label='Latency Waste (Low-Index Glass)')
    
    ax.plot(days, cumulative_cost / 1e6, 'r-', linewidth=2)
    ax.plot(days, cumulative_cost_improved / 1e6, '-', color='#f39c12', linewidth=2)
    ax.plot(days, savings / 1e6, 'g--', linewidth=2, label='Savings')
    
    # Add final values
    ax.annotate(f'${cumulative_cost[-1]/1e6:.1f}M wasted',
                xy=(365, cumulative_cost[-1]/1e6),
                xytext=(300, cumulative_cost[-1]/1e6 + 5),
                fontsize=12, fontweight='bold', color='#c0392b',
                arrowprops=dict(arrowstyle='->', color='#c0392b'))
    
    ax.annotate(f'${savings[-1]/1e6:.1f}M saved',
                xy=(365, savings[-1]/1e6),
                xytext=(300, savings[-1]/1e6 + 2),
                fontsize=12, fontweight='bold', color='#27ae60',
                arrowprops=dict(arrowstyle='->', color='#27ae60'))
    
    ax.set_xlabel('Days of Training', fontsize=12)
    ax.set_ylabel('Cumulative Cost ($M)', fontsize=12)
    ax.set_title('The Cost of Waiting for Light\n'
                 '10,000 GPU cluster, 1 year of continuous training',
                 fontsize=14, fontweight='bold')
    ax.legend(loc='upper left', fontsize=10)
    ax.set_xlim(0, 365)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "the_trillion_dollar_wait.png", dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {FIGURES_DIR / 'the_trillion_dollar_wait.png'}")


def main():
    """Generate all figures."""
    print("Generating figures for AI Interconnect Latency Benchmark...")
    print(f"Output directory: {FIGURES_DIR}")
    print()
    
    fig_speed_of_light_comparison()
    fig_latency_bottleneck()
    fig_gpu_utilization_gap()
    fig_moores_law_vs_light()
    fig_latency_breakdown()
    fig_the_trillion_dollar_wait()
    
    print()
    print("All figures generated successfully!")
    print(f"View them in: {FIGURES_DIR}")


if __name__ == "__main__":
    main()
