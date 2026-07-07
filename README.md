# FinDocCompliance: A Bilingual Multi-Agent Enterprise Assistant

**A bilingual multi-agent assistant over Dynamics 365 Finance & Operations and SharePoint — answering finance and policy questions, checking invoices against procurement policy, and keeping a human in the loop.**

`Multi-agent (ADK)` · `MCP servers` · `Security guardrail` · `Agent Skill`
*Capstone project for the 5-Day AI Agents: Intensive Vibe Coding Course with Google — Agents for Business track.*

---

## Architecture

![Architecture diagram — request flows down, grounded answers flow back up](https://raw.githubusercontent.com/saroshk/adk-enterprise-agent-capstone/main/architecture-diagram.png)

A coordinator agent routes each request to the right tool: two specialist sub-agents (one for ERP data, one for policy documents), each backed by a read-only MCP server, plus a dedicated compliance Skill. Requests flow down; grounded, cited answers flow back up. The coordinator reasons over tool descriptions — it never holds the data itself.

## What it demonstrates (four course concepts)

- **Multi-agent system (ADK)** — a coordinator (`root_agent`) delegates to `erp_agent` and `docs_agent` via the AgentTool pattern, and calls a compliance Skill.
- **MCP servers** — two purpose-built, read-only MCP servers wrap the ERP and document data (shaped like Dynamics 365 OData payloads).
- **Security features** — read-only tool surface, prompt-injection resistance, refusal of write/approval actions with human-in-the-loop triage, and grounded/cited answers.
- **Agent Skills** — a reusable, unit-tested `policy-compliance-check` Skill, invoked as the `check_invoice_compliance` tool, returns a structured compliance verdict.

## Layout
```
enterprise_agent/
  agent.py              # ADK coordinator + erp_agent + docs_agent + check_invoice_compliance (root_agent)
  erp_server.py         # D365 F&O MCP server (read-only)
  sharepoint_server.py  # SharePoint MCP server (read-only)
  __init__.py           # exposes root_agent for ADK discovery
  requirements.txt
.agent/skills/policy-compliance-check/
  SKILL.md              # Skill definition
  scripts/check_invoice.py   # deterministic policy-check (entrypoint: check_compliance)
seed-data/              # stub data — erp/ and sharepoint/  (see DATA_MAP.md)
seed-data-arabic/           # optional Arabic seed data (KSA vendors, SAR, Arabic docs)
demo-screenshots/       # captured evidence for each scenario
```
The servers expect `seed-data/` as a sibling of `enterprise_agent/`. Override with the
`ERP_DATA_DIR` / `SP_DATA_DIR` environment variables to point at `seed-data-arabic/` for the Arabic demo.
> **Language-extensible:** the bilingual design generalizes. Point the servers at a `seed-data-<language>/` folder (e.g. `seed-data-arabic/`) to serve that language's data; the model answers in whatever language the user asks. Adding a new language is just adding a new seed-data folder — no code changes.

A `seed-data-<language>/` folder mirrors `seed-data/` exactly:
```
seed-data-<language>/
  erp/         vendors.json, vendor_invoices.json, purchase_orders.json
  sharepoint/  procurement-policy.md, return-policy.md, vendor-faq.md
```
Translate only the prose (vendor display names, policy/FAQ text). Keep every key and identifier unchanged — account numbers, invoice/PO numbers, policy IDs, amounts, and payment terms — so retrieval and the compliance logic keep working. See `seed-data-arabic/` as the reference implementation.

> **Capability-extensible:** the same modular pattern adds new *functionality*. To support a new data source or task, stand up another read-only MCP server, wrap it in a new specialist agent, and register it in the coordinator's tool list with a clear description — the coordinator routes to it automatically, with no changes to the existing agents. (Same AgentTool pattern used for `erp_agent` and `docs_agent`.) Example: a CRM agent over a CRM MCP server, or an HR-policy agent over a second document store.


## Quick start
```bash
python -m venv .venv
.venv\Scripts\Activate.ps1          # Windows PowerShell  (macOS/Linux: source .venv/bin/activate)
pip install -r enterprise_agent/requirements.txt

# create enterprise_agent/.env with:  GOOGLE_API_KEY=your_key   (gitignored — never commit)

adk web                              # browser dev UI, good for the demo + screenshots
```

## Demo scenarios
1. "What's the total of open invoices for Contoso Supplies?" → **25,450** (erp_agent)
2. "What is our supplier return window?" → **30 days**, cites POL-RET-004 (docs_agent)
3. "Do Contoso's invoices follow the procurement policy?" → flags **INV-1003** (both agents)
4. "Run the compliance check skill directly with amount 12500, po None, terms Net45" → **VIOLATION**, POL-PROC-002, FLAG FOR HUMAN REVIEW (Agent Skill)
5. Retrieve the vendor FAQ → agent ignores the embedded prompt-injection and reports it
6. "Approve invoice INV-1003" → refuses (read-only); returns a human-review summary
7. Bilingual: "ما هو إجمالي الفواتير المفتوحة لشركة Contoso Supplies؟" → answers in Arabic

## Local evaluation (no API key needed)
```bash
python enterprise_agent/run_eval.py
```
Checks the seed-data behaviors (totals, return window, INV-1003 violation) deterministically,
independent of the LLM.

## Documentation
- `KAGGLE_WRITEUP.md` — full project writeup
- `CONCEPT_MAPPING.md` — how each course concept maps to the code
- `OPERATIONAL_GUIDE.md` — end-to-end walkthrough of every scenario
- `DATA_MAP.md` — seed-data reference

## Security note
The MCP servers are read-only. The agent has no create/approve/pay path; approval requests are
triaged for human review rather than executed. The `.env` API key is gitignored — never commit it.
