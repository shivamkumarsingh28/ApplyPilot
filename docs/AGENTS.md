# Supervisor, agents and tools

## The idea in one minute

When you type a message in the assistant (website or Telegram), three levels work together:

```
Your message
   |
   v
[Guardrails]  blocks attacks, other-user requests, off-topic
   |
   v
[Supervisor]  picks ONE specialist agent
   |
   v
[Agent]       picks a TOOL from its own short list (up to 3 steps)
   |
   v
[Tool]        runs code for YOUR account only, returns facts
   |
   v
[Guardrails]  removes secrets from the answer
   |
   v
Answer
```

## The agents

| Agent | Job | Tools it may use |
|---|---|---|
| `notice_agent` | Content of a notice, safety | `list_notices`, `notice_facts`, `ask_notice`, `scam_report` |
| `eligibility_agent` | Can I apply? What is missing? | `check_eligibility`, `check_readiness`, `profile_gaps`, `notice_facts` |
| `tracker_agent` | Deadlines | `upcoming_deadlines`, `list_notices` |
| `photo_agent` | Photo and signature rules | `photo_requirements`, `notice_facts` |

Code: `services/agents/agents.py`.

## The supervisor

`services/agents/supervisor.py`

- With a real model: it asks for JSON `{"agent": "...", "reason": "..."}`. If the answer is not a real agent name, we ignore it and use the keyword router. A confused or tricked model can never invent an agent.
- Without a model: the keyword router counts matches and picks the best agent.

## The agent loop

`services/agents/runner.py`

With a model, the agent repeats at most 3 times:

1. Show the model its allowed tools and the user message.
2. The model replies with JSON: `{"action":"tool","tool":"...","args":{}}` or `{"action":"final","answer":"..."}`.
3. We check the tool is on this agent's list, then run it.
4. Tool results go back to the model inside `<tool_result>` tags. The prompt says to treat them as data, never orders.

Why plain JSON and not each vendor's "function calling"? It works the same on Meta Muse, Llama on Ollama, and any other model.

Without a model, the agent picks one tool using simple rules and writes the answer from a template.

## The tools

`services/agents/tools.py`. Each tool is a small Python function plus a description.

Safety rules built into `call_tool`:

- The tool must exist **and** be on the calling agent's list.
- The user's role must be allowed.
- Arguments not declared by the tool are dropped.
- A tool receives `ToolContext(db, user)`. There is no way to say "use another user".
- A foreign or missing `notice_id` gives the same message: "Notice not found".

## How to add a new tool

1. Write the function in `tools.py`: `def my_tool(ctx: ToolContext, args: dict) -> dict:`
2. Always filter by `ctx.user.id`. Raise `ToolError("message")` for problems the user can fix.
3. Register it in the `_TOOLS` list with a clear description and parameters.
4. Add its name to the right agent's `tools` in `agents.py`.
5. Add an offline answer in `runner.render` and, if useful, a rule in `rule_select`.
6. Write tests, including one that another user cannot reach it. `test_every_agent_tool_exists` checks the registration.

## How to add a new agent

Add an `Agent(...)` in `agents.py` with a clear description and keywords. The supervisor sees it automatically. Add tests in `tests/test_agents.py`.

## Audit

Each turn writes an `assistant_turn` row (agent, route, tool names) and blocked questions write `guardrail_blocked`. Admins can read them at `GET /api/v1/admin/audit`.
