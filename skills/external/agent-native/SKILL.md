# SKILL: agent-native

> Framework for Building Agent-Native Applications — UI + Agent as Equal Citizens

## Overview
agent-native is BuilderIO's open-source framework that treats GUI and Agent as equal citizens. A single `defineAction` unifies 6 call surfaces (UI, HTTP, MCP, A2A, CLI, Agent Tool Call), enabling apps where rich UI and autonomous agents coexist naturally.

## Key Features
- **defineAction Unification**: One definition covers UI button, HTTP endpoint, MCP tool, A2A call, CLI command, and Agent tool
- **6 Call Surfaces**: UI / HTTP / MCP / A2A / CLI / Agent Tool Call — all from one action
- **Context-Aware Agent**: Agent knows what you're looking at (select text → Cmd+I → instruct)
- **Agents Call Agents**: Tag another agent from any app, they coordinate over A2A protocol
- **Self-Improving**: Agent learns from interactions and improves over time
- **Template Marketplace**: Pre-built agent-native app templates
- **Monorepo Support**: Shared auth, shared state across agent+UI

## Technical Details
- **Language**: TypeScript
- **License**: MIT
- **Stars**: 2,629 (as of 2026-06-27)
- **GitHub**: https://github.com/BuilderIO/agent-native
- **Author**: BuilderIO (same team as Mitosis, Figma-to-Code)
- **Install**: `npx create-agent-native@latest`

## Quality Assessment
| Criterion | Score | Notes |
|-----------|-------|-------|
| Stars | 2.6K | Growing fast since June 2026 launch |
| Update Frequency | Very Active | June 2026 launch, daily commits |
| Documentation | Excellent | README + architecture docs + blog posts |
| Code Quality | High | BuilderIO pedigree, clean TypeScript |
| Practical Value | Very High | Solves Agent+UI architecture problem |

## Grade: A
- BuilderIO team has strong track record (Mitosis, Figma-to-Code)
- Novel architecture: truly unifies Agent and UI, not bolt-on
- 6-surface unification is genuinely innovative
- MIT license, well-documented, one-command setup

## Usage with WorkBuddy
```bash
# Create a new agent-native app
npx create-agent-native@latest my-app

# Add an action that works across all 6 surfaces
defineAction('analyze', {
  ui: { button: 'Analyze' },
  agent: { description: 'Analyze the selected data' },
  mcp: { tool: 'analyze_data' },
  a2a: { protocol: 'agent-message' },
  cli: { command: 'analyze' },
  http: { endpoint: '/api/analyze' }
})
```

---
_Discovered: 2026-06-27 | Source: NGJOO Daily Rank #16_
