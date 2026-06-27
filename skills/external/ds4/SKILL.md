# SKILL: ds4

> Redis Author's Hand-Crafted DeepSeek V4 Local Inference Engine

## Overview
ds4 (DwarfStar 4) is a small, native inference engine written in pure C by Redis creator Salvatore Sanfilippo (antirez). It's optimized for DeepSeek V4 Flash local inference, supporting Metal (Apple), CUDA (NVIDIA), and ROCm (AMD). Not a generic GGUF runner — it's completely self-contained with hand-written kernels.

## Key Features
- **Pure C Implementation**: No dependencies, hand-written compute kernels
- **DeepSeek V4 Flash Optimized**: Purpose-built for this specific model architecture
- **Metal + CUDA + ROCm**: Full GPU backend coverage across platforms
- **128GB MacBook Pro Support**: Run 284B MoE model locally with 2-bit quantization
- **KV Cache Persistence**: Cache persists between sessions, faster warm starts
- **Complete Inference Stack**: From tokenizer to model loading to inference, all in C

## Technical Details
- **Language**: C (pure, no framework dependencies)
- **License**: BSD-2-Clause
- **Stars**: 15,987 (as of 2026-06-27)
- **GitHub**: https://github.com/antirez/ds4
- **Author**: antirez (Salvatore Sanfilippo, Redis creator)
- **Install**: Build from source (make)

## Quality Assessment
| Criterion | Score | Notes |
|-----------|-------|-------|
| Stars | 16K | Impressive for a niche inference engine |
| Update Frequency | Active | Regular commits since May 2026 |
| Documentation | Excellent | Detailed README + engineering blog posts |
| Code Quality | Exceptional | antirez-level C craftsmanship |
| Practical Value | High | Enables local DeepSeek V4 on consumer hardware |

## Grade: A
- antirez pedigree guarantees exceptional code quality
- Solves real hardware constraint problem (local inference on Macs)
- BSD license, clean C code, no bloat
- Narrow but deep: does one thing extremely well

## Usage with WorkBuddy
```bash
# Clone and build
git clone https://github.com/antirez/ds4
cd ds4 && make

# Run inference (Metal backend on Mac)
./ds4 --model /path/to/model --prompt "Hello"
```

---
_Discovered: 2026-06-27 | Source: NGJOO Daily Rank #12_
