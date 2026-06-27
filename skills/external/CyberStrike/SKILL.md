# SKILL: CyberStrike

> AI-Powered Offensive Security Agent with 7,300+ Actionable Security Skills

## Overview
CyberStrike is the first open-source AI agent built specifically for offensive security. It provides autonomous penetration testing from your terminal, connecting to Claude, GPT, Gemini or any LLM subscription to execute real security operations based on MITRE ATT&CK frameworks.

## Key Features
- **7,300+ Security Skills**: Based on MITRE ATT&CK (2,000+ Atomic tests), CIS Benchmarks (1,500+ controls), custom pentesting playbooks
- **Multi-LLM Support**: Switch between Claude, GPT, Gemini mid-session for different task strengths
- **Autonomous Pentesting**: Full penetration testing loop — recon → exploit → post-exploit → report
- **Terminal-Native**: CLI-first interface, no GUI required
- **MITRE ATT&CK Mapping**: All operations mapped to ATT&CK techniques for traceability
- **Real Execution**: Not simulation — executes actual security tests against targets

## Technical Details
- **Language**: TypeScript
- **License**: MIT
- **Stars**: 874 (as of 2026-06-27)
- **GitHub**: https://github.com/CyberStrikeus/CyberStrike
- **Website**: https://cyberstrike.io
- **Install**: `npm install -g cyberstrike` or clone

## Quality Assessment
| Criterion | Score | Notes |
|-----------|-------|-------|
| Stars | 874 | Low stars but niche domain, active community |
| Update Frequency | Active | Feb 2026 launch, regular updates |
| Documentation | Good | README + website + guides |
| Code Quality | Good | TypeScript, structured skill system |
| Practical Value | Very High (for security) | First true offensive security AI agent |

## Grade: B
- Niche but high-impact for security professionals
- Low star count reflects niche audience, not quality
- MIT license = easy adoption
- ⚠️ Ethical use only — offensive security tool requires responsible deployment

## Usage with WorkBuddy
```bash
# Install
npm install -g cyberstrike

# Run pentest with Claude
cyberstrike --llm claude --target scope.yaml

# Switch LLM mid-session
cyberstrike --llm gpt-4
```

---
_Discovered: 2026-06-27 | Source: NGJOO Daily Rank #14 | ⚠️ Offensive security tool — ethical use only_
