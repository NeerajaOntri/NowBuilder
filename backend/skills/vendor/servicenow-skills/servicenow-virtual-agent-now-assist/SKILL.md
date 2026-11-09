---
name: servicenow-virtual-agent-now-assist
description: ServiceNow Virtual Agent (conversation topics, Virtual Agent Designer, NLU / LLM topic discovery, live agent handoff, channels) and Now Assist generative AI (Now Assist skills such as summarization and resolution notes, Now Assist Skill Kit, Now Assist Guardian, AI Agents, plugins and licensing). Use for chatbot topics, conversational automation, or questions about Now Assist features.
license: Apache-2.0
metadata:
  category: ai
  version: "1.1"
---

# Virtual Agent and Now Assist

## Virtual Agent
- Conversations are **topics** built in **Virtual Agent Designer** (`sys_cs_topic`): a flow of user
  inputs (text, choice, reference, date), bot responses, utilities (script, decision, lookup) and
  actions (create record, call a subflow / action).
- Topic discovery: keywords, NLU models, or LLM topic discovery (with Now Assist in Virtual Agent).
- Hand off to a human with **Live Agent** (Advanced Work Assignment queues).
- Channels: Service Portal / Employee Center web client, Microsoft Teams, Slack, mobile; each needs its
  integration configured.
- Reuse server logic: a topic calls a flow, subflow or script include rather than long inline scripts.
- Test topics in the designer's Test panel as the target persona.

## Now Assist (generative AI)
- Delivered as store applications and plugins per workflow (ITSM, CSM, HRSD, Creator) and needs the
  matching Pro Plus / Now Assist licence - check what is installed before promising a feature.
- Out-of-box skills include incident / case summarization, resolution notes, chat reply
  recommendations, knowledge article generation, and for creators code, flow and playbook generation.
- **Now Assist Skill Kit** creates custom skills (prompt + inputs + provider); **Now Assist Guardian**
  adds offensiveness / prompt-injection filtering and sensitive-data masking; **AI Agents** run
  multi-step agentic workflows with tools.
- Admin: Now Assist Admin console - turn skills on per workflow, choose display locations, review usage.

## What nowBuilder does
nowBuilder doesn't build Virtual Agent topics or Now Assist skills; it explains the configuration
and builds the server pieces they call (script includes, flows, business rules) as plan rows. It never
claims a Now Assist feature is present without checking the instance (e.g. `sys_store_app` /
`v_plugin` for the plugin).
