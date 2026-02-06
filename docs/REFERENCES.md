# References

## Bibliography for AI Interconnect Latency Benchmark

All references are verified against their original sources. Where specifications are estimated or projected, this is explicitly noted.

---

## AI Training Infrastructure

[1] T. Brown, B. Mann, N. Ryder, et al., "Language Models are Few-Shot Learners," in *Advances in Neural Information Processing Systems*, vol. 33, 2020, pp. 1877–1901. arXiv:2005.14165.
**Note:** This paper describes GPT-3 training infrastructure, NOT GPT-4. The "~10,000 GPU" cluster scale refers to GPT-3.

[2] OpenAI, "GPT-4 Technical Report," arXiv:2303.08774, March 2023.
**Note:** OpenAI did not disclose exact GPU counts for GPT-4. The "25,000+" estimate is from industry reporting, not this paper.

[3] S. Narayanan, M. Shoeybi, J. Casper, et al., "Efficient Large-Scale Language Model Training on GPU Clusters Using Megatron-LM," in *Proc. SC*, 2021.

---

## NVIDIA Hardware Specifications

[4] NVIDIA Corporation, "NVIDIA H100 Tensor Core GPU Datasheet," 2023.
URL: https://www.nvidia.com/en-us/data-center/h100/
**Status:** VERIFIED — All H100 specs in this repo match this datasheet.

[5] NVIDIA Corporation, "NVIDIA Blackwell Architecture Technical Brief," GTC 2024.
**Status:** ESTIMATED — B200 specs (9,000 FP8 TFLOPS, 192GB HBM3e) are derived from Jensen Huang's GTC 2024 keynote, not a final product datasheet. These may change.

[6] NVIDIA Corporation, "NVIDIA GB200 NVL72 Specifications," 2024.
URL: https://www.nvidia.com/en-us/data-center/gb200-nvl72/
**Status:** VERIFIED — Rack-level specifications confirmed.

[7] NVIDIA Corporation, "NVIDIA Quantum-2 InfiniBand Platform Specifications," 2023.
URL: https://www.nvidia.com/en-us/networking/quantum2/

[8] NVIDIA Corporation, "NVIDIA NVLink and NVSwitch," 2024.
URL: https://www.nvidia.com/en-us/data-center/nvlink/

**Rubin (R100) Note:** All "Rubin" specifications in this repository are PROJECTIONS based on NVIDIA's published roadmap trajectory. They are NOT from any official datasheet or technical brief. Use for planning purposes only.

---

## Optical Fiber Properties

[9] Corning Incorporated, "Corning SMF-28 Ultra Optical Fiber Product Information," Product Bulletin PI1424, 2023.
URL: https://www.corning.com/optical-communications/worldwide/en/home/products/fiber/optical-fiber-products/smf-28-ultra.html
**Key value used:** n = 1.4682 at 1550 nm (core refractive index).

[10] I. H. Malitson, "Interspecimen Comparison of the Refractive Index of Fused Silica," *Journal of the Optical Society of America*, vol. 55, no. 10, pp. 1205–1209, Oct. 1965.
**Key value used:** n(SiO2) = 1.4580 at 587.6 nm; ~1.4440 at 1550 nm (Sellmeier fit).
**Note:** Our scripts use n = 1.45 as a round number for bulk fused silica. The Sellmeier-accurate value at 1550 nm is ~1.444. This introduces a ~0.4% error in n_eff calculations that is smaller than the EMT model uncertainty.

[11] G. P. Agrawal, *Fiber-Optic Communication Systems*, 4th ed. Hoboken, NJ: John Wiley & Sons, 2010.

[12] F. Poletti, et al., "Towards High-Capacity Fibre-Optic Communications at the Speed of Light in Vacuum," *Nature Photonics*, vol. 7, no. 4, pp. 279–284, Apr. 2013.
**Key value used:** Hollow-core fiber n ≈ 1.003.

---

## Effective Medium Theory

[13] J. C. Maxwell Garnett, "Colours in Metal Glasses and in Metallic Films," *Philosophical Transactions of the Royal Society A*, vol. 203, pp. 385–420, 1904.

[14] D. A. G. Bruggeman, "Berechnung verschiedener physikalischer Konstanten von heterogenen Substanzen," *Annalen der Physik*, vol. 416, no. 7, pp. 636–664, 1935.

[15] V. A. Markel, "Introduction to the Maxwell Garnett approximation: tutorial," *J. Opt. Soc. Am. A*, vol. 33, no. 7, pp. 1244–1256, Jul. 2016.
**Note:** This tutorial explicitly discusses validity limits of MG for non-spherical inclusions.

---

## Triply-Periodic Minimal Surfaces

[16] A. H. Schoen, "Infinite Periodic Minimal Surfaces without Self-Intersections," NASA Technical Note D-5541, Washington, D.C., 1970.

---

## Metrology and Standards

[17] Bureau International des Poids et Mesures, "The International System of Units (SI)," SI Brochure, 9th ed., 2019.
URL: https://www.bipm.org/en/publications/si-brochure
**Key value used:** c = 299,792,458 m/s (exact by definition).

---

## Cloud Computing Costs

[18] Amazon Web Services, "Amazon EC2 P5 Instances," 2024.
URL: https://aws.amazon.com/ec2/instance-types/p5/
**Key value used:** ~$2.00/GPU-hour (on-demand equivalent for H100-class).

---

## Genesis Research (Patent Pending)

[19] Genesis Research, "Architected Photonic Substrates for Low-Index Optical Interconnects," U.S. Provisional Patent Application, filed Jan. 2026. (Patent 4)

[20] Genesis Research, "Inverse-Designed Optical Couplers for Superluminal Glass Integration," U.S. Provisional Patent Application, filed Jan. 2026. (Patent 13)

---

## Citation Verification Notes

- All URLs were tested as of January 2026.
- Where a citation is used to support a specific numerical claim, the "Key value used" annotation identifies exactly what was taken from that source.
- NVIDIA Rubin specifications are NOT cited to any official source because no official source exists. They are roadmap projections.
- The Malitson 1965 silica index value (n=1.45) used in our EMT calculations is a rounded approximation. The Sellmeier-accurate value at 1550nm is ~1.444. This ~0.4% difference is smaller than the uncertainty between Maxwell-Garnett and Bruggeman models (~1.4%).

---

*Last updated: February 2026*
