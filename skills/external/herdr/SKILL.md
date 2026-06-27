# SKILL: herdr

> Agent Multiplexer that lives in your terminal

## Overview
herdr is a terminal-native Agent multiplexer for running multiple AI coding agents in parallel panes. It tracks which agent is working, waiting, or done, with persistent sessions and SSH attach capability.

## Key Features
- **Parallel Agent Panes**: Run multiple AI coding agents side-by-side in real terminal panes
- **State Awareness**: Tracks agent states (working/waiting/done) in real-time
- **Persistent Sessions**: Resume agent work after disconnect
- **SSH Attach**: Remote access to running agent sessions
- **CLI/Socket Orchestration**: Control agents via CLI commands or socket API
- **Single Rust Binary**: No Electron, no cloud dependency, pure local operation

## Technical Details
- **Language**: Rust
- **License**: AGPL-3.0
- **Stars**: 7,610 (as of 2026-06-27)
- **GitHub**: https://github.com/ogulcancelik/herdr
- **Install**: `cargo install herdr` or download binary from releases

## Quality Assessment
| Criterion | Score | Notes |
|-----------|-------|-------|
| Stars | 7.6K | Growing fast, niche but useful |
| Update Frequency | Active | 2026-05-27 last commit |
| Documentation | Good | README + blog posts |
| Code Quality | High | Rust, single-binary, clean |
| Practical Value | High | Solves real Agent orchestration pain |

## Grade: B+
- Niche but solves a real problem for developers running multiple agents
- Rust implementation ensures performance and reliability
- Terminal-native approach avoids Electron bloat

## Usage with WorkBuddy
```bash
# Install herdr
cargo install herdr

# Start a session with multiple agents
herdr start --agents 3

# Attach via SSH
herdr ssh-attach
```

---
_Discovered: 2026-06-27 | Source: NGJOO Daily Rank #9_
