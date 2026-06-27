# SKILL: workweave-router

> Intelligent Model Router for Agentic Systems — 50ms routing, 40-70% cost reduction

## Overview
Weave Router is a smart model routing proxy that uses reinforcement learning to route each prompt to the optimal LLM model in under 50ms. It reduces API costs by 40-70% by avoiding unnecessary use of expensive models like Opus 4.7 for simple tasks.

## Key Features
- **RL-Based Routing**: Reinforcement learning algorithm continuously optimizes model selection
- **50ms Latency**: Sub-50ms routing decision for each prompt
- **40-70% Cost Savings**: Measured reduction in token costs across real workloads
- **Claude Code / Codex / OpenCode Integration**: One-command setup for popular coding agents
- **On/Off Toggle**: `npx @workweave/router on --claude` / `off` without losing config
- **Transparent Proxy**: Works as a local proxy, no code changes needed

## Technical Details
- **Language**: Go
- **License**: ELv2 (Elastic License v2)
- **Stars**: 382 (as of 2026-06-27, newly launched)
- **GitHub**: https://github.com/workweave/router
- **Install**: `npx @workweave/router on --claude`

## Quality Assessment
| Criterion | Score | Notes |
|-----------|-------|-------|
| Stars | 382 | Newly launched, HackerNews 135pts |
| Update Frequency | Very Active | Launched June 2026 |
| Documentation | Good | README + HN launch post |
| Code Quality | High | Go, clean architecture |
| Practical Value | Very High | Direct cost savings for LLM users |

## Grade: B+
- Extremely practical value (cost optimization is top concern for LLM users)
- Low stars but strong HN reception and clear trajectory
- Go implementation = fast, lightweight proxy
- ELv2 license limits some commercial redistribution

## Usage with WorkBuddy
```bash
# Enable for Claude Code
npx @workweave/router on --claude

# Enable for Codex
npx @workweave/router on --codex

# Check status
npx @workweave/router status

# Disable (reverts to direct provider routing)
npx @workweave/router off --claude
```

---
_Discovered: 2026-06-27 | Source: NGJOO Daily Rank #10 + HackerNews_
