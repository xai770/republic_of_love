# MCP Setup Handoff for Cosmic Sister

**Date:** 2026-01-29  
**From:** Arden (GitHub Copilot / Claude)  
**To:** Cosmic Sister (Perplexity AI)  
**Status:** Attempted but not completed

---

## What is MCP?

**Model Context Protocol** - An open standard by Anthropic that lets AI assistants connect to external tools and data sources. Think of it as "plugins for AI" - it would let me:

1. **Browse talent.yoga** - See the actual HTML pages we're building
2. **Better file access** - Read/write without VS Code's file picker limitations  
3. **Database queries** - Direct PostgreSQL access (we have `turing-q` wrapper but MCP would be cleaner)
4. **Web fetching** - Access job board APIs directly

## What We Tried

### Attempt 1: VS Code MCP Extension
- There's supposed to be MCP support in VS Code / GitHub Copilot
- Gershon couldn't find the right menu/settings
- I can't see VS Code UI, so I couldn't guide him visually
- **Blocker:** Need someone who can see Gershon's screen or he can photograph menus

### Attempt 2: Config File Approach
- Created `config/membridge.yaml` (different thing - this is for our LLM prompt management)
- MCP would need a separate config, likely in `~/.config/` or VS Code settings

## What Cosmic Sister Should Help With

### 1. Find the Right MCP Setup for VS Code + Copilot
- Is it built into GitHub Copilot Chat?
- Is it a separate extension?
- What's the current (Jan 2026) recommended approach?

### 2. Specific Servers We Want

```
┌─────────────────────────────────────────────────────────┐
│ MCP Server              │ Purpose                       │
├─────────────────────────┼───────────────────────────────┤
│ filesystem              │ Read/write project files      │
│ postgres                │ Query turing DB directly      │
│ fetch / puppeteer       │ Browse talent.yoga pages      │
│ brave-search (optional) │ Web search for docs           │
└─────────────────────────────────────────────────────────┘
```

### 3. Step-by-Step Instructions
Gershon can:
- Run terminal commands
- Edit config files
- Photograph VS Code menus and send to Sis (phone app)

He cannot:
- Navigate complex UI without guidance
- Debug abstract error messages alone

## Technical Context

- **OS:** Linux (Ubuntu-based)
- **Editor:** VS Code with GitHub Copilot extension
- **AI:** Claude (Opus 4 / Sonnet) via Copilot Chat
- **Database:** PostgreSQL (`turing` database on localhost)
- **Project:** `/home/xai/Documents/ty_learn`
- **Website:** talent.yoga (localhost:3000 when running)

## Files That Might Be Relevant

```
~/.config/          # Likely where MCP config goes
.vscode/settings.json   # VS Code workspace settings
config/membridge.yaml   # NOT MCP - this is our LLM config
```

## Success Criteria

When MCP is working, Arden should be able to:
1. Run a tool that queries PostgreSQL directly (not via run_in_terminal hack)
2. Fetch a URL and see HTML content
3. Read files without the current line-range limitations

---

## For Gershon

When working with Cosmic Sister:
1. Share this memo
2. Ask her to find the current MCP setup guide for VS Code + GitHub Copilot
3. Photograph any menus/dialogs she asks about
4. Run the commands she suggests

We'll pick this up once the MCP bridge is configured. The nightly pipeline is stable now, so this is a good time to improve tooling.

---

*Blood pressure 175 - better than yesterday. Keep floating. 🌙*
