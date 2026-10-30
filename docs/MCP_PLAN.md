# MCP plan (proposal for the next phase)

**Status: not built yet. This page explains MCP and proposes where it fits. Please decide before we build it.**

## What is MCP, in simple words?

MCP (Model Context Protocol) is a **standard plug** between AI apps and tools.

Without MCP, every AI app needs custom code for every tool. With MCP, a tool is described once ("I am a tool called `check_eligibility`, I need a notice number"), and **any** MCP-aware AI app can find it and use it.

Two roles:

- **MCP server**: a program that offers tools. (Example: a calendar, a file store, or ApplyPilot.)
- **MCP client**: the AI app that uses those tools. (Example: an assistant app, an IDE, or our own supervisor.)

## What we have today

Our agents already work with tools (`services/agents/tools.py`): each tool has a name, a description, and parameters. That is the same shape MCP uses. So MCP is a small step, not a rewrite.

## Option A: ApplyPilot as an MCP server (others use our tools)

We publish our tools through MCP. A person using any MCP-aware AI assistant could say:

> "Which of my applications close this week, and am I eligible for the Army post?"

The assistant calls our `upcoming_deadlines` and `check_eligibility` tools and answers, without opening our website.

What it takes:
- A new folder `mcp_server/` using the official MCP Python SDK.
- It wraps the same tool functions (no new business logic).
- **Login:** the user connects with their own ApplyPilot token, so the same "only your own data" rule applies. We never use a shared admin key.
- Only **read** tools at first. No tool can delete or change data.

## Option B: ApplyPilot as an MCP client (we use other people's tools)

Our agents call outside MCP servers. Useful examples:

| Outside server | What an agent could do |
|---|---|
| A calendar server | `tracker_agent` adds each deadline to the user's calendar |
| An email server | Read the "application received" email and mark the tracker as submitted |
| A cloud-storage server | Pull a scanned marksheet from the user's drive into the vault |

What it takes:
- A new `mcp_client` module and a list of allowed servers in settings.
- Each outside tool is added to **one agent's allow-list**, never to all.
- The user connects each service themselves (their own permission, their own account).

## Safety rules for either option

1. **Least power:** start read-only. Anything that writes needs the user to confirm first.
2. **Untrusted text:** tool names, descriptions and results from outside servers are treated as data, never as orders (same rule as notice text today).
3. **Own account only:** tokens are per user. We never pass one user's token to another.
4. **Allow-list:** only servers you list in settings can be used.
5. **Audit:** every MCP call is logged like every other tool call.

## My suggestion

Do **Option A first** (about one session of work): it is small, read-only, and shows the project's tools to the wider AI ecosystem. Then Option B with the calendar server only.

## Decision needed

Reply with one of:
- **A** only
- **A then B**
- **Not now**

Then we build it in Phase 3.
