#!/usr/bin/env python3
"""
AI Interconnect Latency Benchmark
=================================

Calculate optical interconnect latency for AI clusters and demonstrate
the "speed of light bottleneck" in modern AI infrastructure.

This script uses publicly available physics constants and published
GPU specifications. All calculations are reproducible and verifiable.

Author: Genesis Research
License: MIT (this code) / Patent Pending (referenced solutions)
"""

import numpy as np
import argparse
from dataclasses import dataclass
from typing import Dict, List, Tuple

# =============================================================================
# PHYSICAL CONSTANTS (Publicly Known)
# =============================================================================

C_VACUUM_M_S = 299_792_458  # Speed of light in vacuum (m/s) - exact by definition
C_VACUUM_KM_S = 299_792.458  # Speed of light in vacuum (km/s)

# =============================================================================
# OPTICAL MEDIA SPECIFICATIONS
# =============================================================================

@dataclass
class OpticalMedium:
    """Specification for an optical transmission medium."""
    name: str
    refractive_index: float
    description: str
    source: str
    
    @property
    def speed_km_s(self) -> float:
        """Speed of light in this medium (km/s)."""
        return C_VACUUM_KM_S / self.refractive_index
    
    @property
    def speed_m_s(self) -> float:
        """Speed of light in this medium (m/s)."""
        return C_VACUUM_M_S / self.refractive_index
    
    @property
    def percent_of_c(self) -> float:
        """Speed as percentage of vacuum speed."""
        return 100.0 / self.refractive_index


# Standard optical media with public specifications
OPTICAL_MEDIA = {
    "vacuum": OpticalMedium(
        name="Vacuum",
        refractive_index=1.0000,
        description="Theoretical maximum - no medium",
        source="Physics definition"
    ),
    "air": OpticalMedium(
        name="Air (STP)",
        refractive_index=1.000293,
        description="Air at standard temperature and pressure",
        source="CRC Handbook of Chemistry and Physics"
    ),
    "hollow_core": OpticalMedium(
        name="Hollow-Core Fiber",
        refractive_index=1.003,
        description="Air-guided photonic bandgap fiber",
        source="OFS/Lumenisity datasheets"
    ),
    "low_index": OpticalMedium(
        name="Low-Index Glass (?)",
        refractive_index=1.15,
        description="Architected photonic substrate - Patent Pending",
        source="Genesis Research (Patent Pending)"
    ),
    "fused_silica": OpticalMedium(
        name="Fused Silica",
        refractive_index=1.4440,
        description="Pure SiO2 glass at 1550nm",
        source="Corning HPFS datasheet"
    ),
    "smf28": OpticalMedium(
        name="SMF-28 Fiber",
        refractive_index=1.4682,
        description="Standard single-mode fiber (doped silica core)",
        source="Corning SMF-28 Ultra datasheet"
    ),
    "silicon": OpticalMedium(
        name="Silicon Waveguide",
        refractive_index=3.48,
        description="Crystalline silicon at 1550nm",
        source="Soref & Bennett (1987)"
    ),
}


# =============================================================================
# GPU SPECIFICATIONS
# =============================================================================

@dataclass
class GPUSpec:
    """Specification for a GPU compute platform."""
    name: str
    fp8_tflops: float
    fp16_tflops: float
    hbm_bandwidth_gb_s: float
    nvlink_bandwidth_gb_s: float
    tdp_watts: float
    year: int
    source: str
    
    @property
    def ops_per_ns(self) -> float:
        """FP8 operations per nanosecond."""
        return self.fp8_tflops * 1e3  # TFLOPS to GFLOPS = ops/ns


GPU_SPECS = {
    "k80": GPUSpec(
        name="NVIDIA K80",
        fp8_tflops=0,  # No FP8 support
        fp16_tflops=0,  # No FP16 support
        hbm_bandwidth_gb_s=480,
        nvlink_bandwidth_gb_s=0,
        tdp_watts=300,
        year=2014,
        source="NVIDIA K80 Datasheet"
    ),
    "v100": GPUSpec(
        name="NVIDIA V100",
        fp8_tflops=0,  # No FP8 support
        fp16_tflops=125,
        hbm_bandwidth_gb_s=900,
        nvlink_bandwidth_gb_s=300,
        tdp_watts=300,
        year=2017,
        source="NVIDIA V100 Datasheet"
    ),
    "a100": GPUSpec(
        name="NVIDIA A100",
        fp8_tflops=624,  # Approximated from FP16
        fp16_tflops=312,
        hbm_bandwidth_gb_s=2039,
        nvlink_bandwidth_gb_s=600,
        tdp_watts=400,
        year=2020,
        source="NVIDIA A100 Datasheet"
    ),
    "h100": GPUSpec(
        name="NVIDIA H100 SXM5",
        fp8_tflops=3958,
        fp16_tflops=1979,
        hbm_bandwidth_gb_s=3350,
        nvlink_bandwidth_gb_s=900,
        tdp_watts=700,
        year=2023,
        source="NVIDIA H100 Whitepaper"
    ),
    "b200": GPUSpec(
        name="NVIDIA B200",
        fp8_tflops=9000,  # Estimated
        fp16_tflops=4500,  # Estimated
        hbm_bandwidth_gb_s=8000,  # Estimated
        nvlink_bandwidth_gb_s=1800,
        tdp_watts=1000,  # Estimated
        year=2024,
        source="NVIDIA GTC 2024 Keynote (estimates)"
    ),
}


# =============================================================================
# LATENCY CALCULATIONS
# =============================================================================

def calculate_latency_ns(distance_m: float, medium: OpticalMedium) -> float:
    """
    Calculate one-way propagation latency in nanoseconds.
    
    Physics: t = d / v = d * n / c
    
    Args:
        distance_m: Path length in meters
        medium: Optical medium specification
        
    Returns:
        Latency in nanoseconds
    """
    latency_s = distance_m * medium.refractive_index / C_VACUUM_M_S
    return latency_s * 1e9  # Convert to nanoseconds


def calculate_latency_tax_ns(distance_m: float, medium: OpticalMedium) -> float:
    """
    Calculate the latency 'tax' vs vacuum (one-way).
    
    This is the additional delay caused by using this medium
    instead of vacuum.
    
    Args:
        distance_m: Path length in meters
        medium: Optical medium specification
        
    Returns:
        Additional latency in nanoseconds
    """
    delta_n = medium.refractive_index - 1.0
    tax_s = distance_m * delta_n / C_VACUUM_M_S
    return tax_s * 1e9


def calculate_wasted_ops(latency_ns: float, gpu: GPUSpec) -> float:
    """
    Calculate operations that could have executed during latency.
    
    Args:
        latency_ns: Latency in nanoseconds
        gpu: GPU specification
        
    Returns:
        Number of floating-point operations
    """
    return latency_ns * gpu.ops_per_ns


# =============================================================================
# BENCHMARK FUNCTIONS
# =============================================================================

def run_media_comparison(distance_m: float, gpu: GPUSpec, verbose: bool = True) -> List[Dict]:
    """
    Compare latency across all optical media.
    
    Args:
        distance_m: Path length in meters
        gpu: GPU specification for wasted ops calculation
        verbose: Print results to stdout
        
    Returns:
        List of result dictionaries
    """
    results = []
    
    if verbose:
        print("=" * 78)
        print("AI INTERCONNECT LATENCY BENCHMARK")
        print("The Speed of Light Problem")
        print("=" * 78)
        print()
        print(f"Configuration:")
        print(f"  Distance: {distance_m} m")
        print(f"  GPU: {gpu.name} ({gpu.fp8_tflops:,.0f} TFLOPS FP8)")
        print()
        print("-" * 78)
        header = f"{'Medium':<25} {'n':>8} {'Speed (km/s)':>14} {'Latency':>12} {'Wasted Ops':>16}"
        print(header)
        print("-" * 78)
    
    for key, medium in OPTICAL_MEDIA.items():
        latency = calculate_latency_ns(distance_m, medium)
        wasted = calculate_wasted_ops(latency, gpu)
        tax = calculate_latency_tax_ns(distance_m, medium)
        
        result = {
            "key": key,
            "name": medium.name,
            "n": medium.refractive_index,
            "speed_km_s": medium.speed_km_s,
            "latency_ns": latency,
            "latency_tax_ns": tax,
            "wasted_ops": wasted,
            "percent_of_c": medium.percent_of_c,
        }
        results.append(result)
        
        if verbose:
            marker = " <-- THE GAP" if "?" in medium.name else ""
            wasted_str = f"{wasted/1e9:.2f}B" if wasted > 1e9 else f"{wasted/1e6:.1f}M"
            print(f"{medium.name:<25} {medium.refractive_index:>8.4f} "
                  f"{medium.speed_km_s:>14,.0f} {latency:>10.2f} ns "
                  f"{wasted_str:>14}{marker}")
    
    if verbose:
        print("-" * 78)
        print()
        
        # Calculate improvement potential
        fiber = next(r for r in results if r["key"] == "smf28")
        low_idx = next(r for r in results if r["key"] == "low_index")
        
        improvement_ns = fiber["latency_ns"] - low_idx["latency_ns"]
        improvement_pct = (improvement_ns / fiber["latency_ns"]) * 100
        
        print("THE OPPORTUNITY:")
        print(f"  Standard fiber latency: {fiber['latency_ns']:.2f} ns (one-way)")
        print(f"  Low-index glass latency: {low_idx['latency_ns']:.2f} ns (one-way)")
        print(f"  Latency reduction: {improvement_ns:.2f} ns ({improvement_pct:.1f}%)")
        print()
        
        # Annualized calculation
        syncs_per_sec = 1000  # Typical for distributed training
        gpus = 10000
        ops_saved = improvement_ns * gpu.ops_per_ns * syncs_per_sec * gpus
        
        print("AT SCALE (10,000 GPUs, 1,000 syncs/sec):")
        print(f"  Ops recovered per second: {ops_saved:.2e}")
        print(f"  Equivalent GPU-hours saved per day: {ops_saved * 86400 / (gpu.fp8_tflops * 1e12 * 3600):.1f}")
        print()
        print("=" * 78)
        print("Solution: Patent Pending (Provisional Filed January 2026)")
        print("Contact: nick@genesis.ai")
        print("=" * 78)
    
    return results


def run_distance_sweep(
    distances_m: List[float],
    medium: OpticalMedium,
    gpu: GPUSpec
) -> List[Dict]:
    """
    Calculate latency across multiple distances.
    
    Args:
        distances_m: List of distances to evaluate
        medium: Optical medium
        gpu: GPU specification
        
    Returns:
        List of result dictionaries
    """
    results = []
    for d in distances_m:
        latency = calculate_latency_ns(d, medium)
        wasted = calculate_wasted_ops(latency, gpu)
        results.append({
            "distance_m": d,
            "latency_ns": latency,
            "wasted_ops": wasted,
            "latency_tax_ns": calculate_latency_tax_ns(d, medium),
        })
    return results


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="AI Interconnect Latency Benchmark"
    )
    parser.add_argument(
        "--distance", "-d",
        type=float,
        default=100.0,
        help="Interconnect distance in meters (default: 100)"
    )
    parser.add_argument(
        "--gpu", "-g",
        type=str,
        default="h100",
        choices=list(GPU_SPECS.keys()),
        help="GPU model for compute comparison (default: h100)"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Output file for results (CSV format)"
    )
    
    args = parser.parse_args()
    
    gpu = GPU_SPECS[args.gpu]
    results = run_media_comparison(args.distance, gpu, verbose=True)
    
    if args.output:
        import csv
        with open(args.output, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
        print(f"\nResults saved to: {args.output}")


if __name__ == "__main__":
    main()
