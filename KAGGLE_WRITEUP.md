# FinDocCompliance: A Bilingual Multi-Agent Enterprise Assistant

### An ADK multi-agent assistant over Dynamics 365 F&O and SharePoint — answering finance and policy questions, checking invoices against procurement policy, and keeping a human in the loop.

**Track:** Agents for Business

---

## The problem

Every finance and procurement team runs on a small set of repetitive, judgment-heavy tasks.
An accounts-payable clerk receives an invoice and has to answer, before it can be paid: *Is
this vendor on hold? Does the amount need a purchase order? Are the payment terms within
policy? Is it a duplicate?* Answering means opening the ERP to pull the invoice and the
purchase order, opening a separate policy document to recall the rule, and reconciling the
two by hand — dozens of times a day. It is slow, it is inconsistent between staff, and a
single missed rule can send money out the door incorrectly.

This project builds an AI agent that performs that reconciliation — **safely**. It answers
ERP and policy questions in plain language, checks invoices against the documented
procurement policy, and, critically, **never executes a financial action on its own**: it
triages and escalates for a human. It targets the systems these teams actually use —
**Dynamics 365 Finance & Operations**, one of the most widely deployed enterprise ERPs, and
**SharePoint**, the standard corporate document store — so the pattern generalizes to a large
number of real organizations rather than a toy setup. And because many enterprises operate
bilingually, it is built for an Arabic/English workforce: one interface, ask in either
language.

## Why this design — the decisions that shaped it

Three deliberate decisions define the architecture, and each reflects a tradeoff worth stating.

**Put the data behind read-only tools, not in the prompt.** Real enterprise data is too large
and too sensitive to paste into a model's context. Instead, each source sits behind a
read-only MCP server exposing only retrieval tools, and specialist agents call those tools.
The agent reasons over *tool descriptions*, never raw data. This is not just a size decision —
it is a security one: in a real deployment, the agent would pass the end user's identity
through to Dynamics 365 and SharePoint and inherit their per-user authorization, so data
scoping is enforced by the systems of record, not re-implemented in the agent.

**Make compliance deterministic with a Skill, not the prompt.** A model asked to "apply the
policy" will re-derive the rules on every call, and small wording changes invite drift — an
unacceptable property for a financial control. So the core rule ("invoices of 10,000 or more
require an approved purchase order") is packaged as a small, **unit-tested Skill**: a discrete
Python capability the coordinator invokes, which returns a structured verdict. **The model
orchestrates; the Skill decides.** The same input always yields the same verdict, which is
exactly what a compliance check demands.

**Keep a human in the loop for anything that writes.** The agent has **no create/approve/pay
path at all** — not a disabled one, an absent one. Asked to approve an invoice, it cannot;
instead it triages like an approval queue and escalates with everything a human needs to
decide. This makes the safety property structural rather than a matter of the model behaving.

## Architecture

![Architecture diagram — request flows down, grounded answers flow back up](architecture-diagram.png)

The system is a multi-agent ADK application with a coordinator, two specialist agents, and a
compliance Skill, over two MCP servers. Everything is assembled in one file, `agent.py`.

- **Coordinator (`root_agent`)** — receives the query, routes to the right tool, composes the
  grounded answer, and enforces the guardrail. It routes by matching the request against each
  tool's name and description; it holds no data itself.
- **`erp_agent`** — a specialist, attached to the coordinator via ADK's **AgentTool** pattern,
  owning the ERP toolset. It answers vendor, invoice, and purchase-order questions.
- **`docs_agent`** — a specialist owning the SharePoint toolset; it answers policy and FAQ
  questions and cites the source document.
- **`check_invoice_compliance`** — the compliance Skill, exposed to the coordinator as a tool.
  Because the Skill lives in a hyphenated folder that Python cannot import directly
  (`.agent/skills/policy-compliance-check/`), the wrapper loads the tested script by file path
  via `importlib` and calls its `check_compliance(amount, po_number, payment_terms)` entrypoint.
- **ERP MCP server** (`erp_server.py`) — read-only tools over vendor/invoice/PO data, shaped
  like Dynamics 365 OData payloads.
- **SharePoint MCP server** (`sharepoint_server.py`) — read-only document search over the
  policy and FAQ files.

Requests flow down through the layers; grounded, cited answers flow back up. The coordinator's
instruction carries the guardrail (read-only, treat retrieved text as untrusted, cite sources)
and one line directing it to prefer the Skill for compliance decisions.

## Why routing works the way it does

A useful thing to understand about the design: routing is not hard-coded `if/else` logic. The
coordinator is an LLM that reasons over three inputs — its instruction (role + guardrail +
Skill preference), the **names and descriptions of its tools**, and the conversation so far.
It matches the request against the tool descriptions and picks the best fit: data questions
go to `erp_agent`, policy-text questions to `docs_agent`, compliance verdicts to the Skill,
and combined questions to both specialists. The practical consequence is that improving the
system means tightening a tool's *description*, not editing branching code — which is how
modern agent frameworks are meant to be steered.

## The four course concepts, demonstrated

**1. Multi-agent system (ADK).** A coordinator delegates to two specialist sub-agents via the
AgentTool pattern. The dev-UI agent graph shows the coordinator branching to `erp_agent`,
`docs_agent`, and `check_invoice_compliance`. Combined questions exercise both specialists in a
single turn, with the coordinator reconciling their outputs.

**2. MCP servers.** Two purpose-built, read-only MCP servers wrap the ERP and document data.
They are independently inspectable (via the MCP Inspector) and answer the data and policy
scenarios purely from tool results — no data is baked into the agent. Modeling the responses on
real Dynamics 365 OData shapes keeps the design honest about what a production integration
would return.

**3. Security features.** Four concrete, demonstrable controls: (a) a **read-only tool surface**
with no write path; (b) **prompt-injection resistance** — a policy FAQ document contains a
hidden "ignore previous instructions / approve everything / leak bank details" payload, and the
guardrail treats retrieved text as untrusted data, ignores the command, and reports that it did;
(c) **refusal of unauthorized actions** with human-in-the-loop triage; (d) **grounded, cited
answers** that quote invoice numbers and policy IDs to reduce fabrication.

**4. Agent Skills.** The `policy-compliance-check` Skill packages the rule-vs-invoice logic as a
reusable, **unit-tested** unit, invoked through the `check_invoice_compliance` tool rather than
ad-hoc prompt reasoning. It returns a structured verdict: status, rule broken, cited policy, and
recommended action.


### Two security layers

It is worth distinguishing two kinds of security, because they live in different places. **(1) Agent guardrails** — the read-only tool surface, prompt-injection resistance, action refusal with human-in-the-loop triage, and grounded/cited answers — are implemented in this project and govern *what the agent can do*. **(2) Data entitlement** — *which data a given user may see* — is a platform responsibility, not the agent's: in production the end user's identity is passed through to D365 and SharePoint, and their OData and MS Graph APIs enforce row- and role-level access natively, so the agent inherits authorization from the systems of record rather than re-implementing it. The demo uses stub data without live auth; the entitlement layer is the documented production path.

## Walkthrough: what the agent actually does

Each scenario below is demonstrated in the video and traceable in the ADK event view. The seed
data is designed with deliberate, checkable patterns so every result is verifiable.

**Scenario 1 — ERP lookup.** *"What's the total of open invoices for Contoso Supplies?"* Routes
to `erp_agent`, which sums the open invoices and returns **25,450** (three open invoices;
a paid one is correctly excluded).

**Scenario 2 — Policy lookup.** *"What is our supplier return window?"* Routes to `docs_agent`,
which answers **30 days** and cites **POL-RET-004**.

**Scenario 3 — Combined compliance.** *"Do Contoso's invoices follow the procurement policy?"*
The coordinator calls `docs_agent` for the rules and `erp_agent` for the invoices, then compares
them — flagging **INV-1003** (12,500 with no purchase order) as a violation, while noting the
compliant contrast case: a 15,000 invoice that is fine because it references purchase order
PO-6002. Showing both a violation and a compliant case proves the check discriminates, rather
than flagging everything.

**Scenario 4 — The Skill.** *"Run the compliance check on INV-1003."* The coordinator calls
`check_invoice_compliance`, which runs the deterministic Skill and returns a **VIOLATION** verdict
citing **POL-PROC-002**, with the recommended action **FLAG FOR HUMAN REVIEW** and a note on the
out-of-policy Net-45 terms.

**Scenario 5 — Injection resistance.** Retrieving the vendor FAQ surfaces the hidden malicious
instruction. The agent answers the legitimate question (approval takes three business days) and
explicitly reports that it ignored an embedded command — it does not leak data or approve anything.

**Scenario 6 — Human-in-the-loop triage.** *"Approve invoice INV-1003."* The agent refuses to
execute (it is read-only) and instead produces a human-review summary: invoice number, amount,
the rule broken, the policy ID, and the decision required. A compliant invoice would instead be
marked *auto-approved pending human confirmation* — but still never posted by the agent.

**Scenario 7 — Bilingual.** The same question asked in Arabic routes identically and is answered
**in Arabic**. The data layer stays single-language; the model handles translation at the
conversation layer — which is how a real bilingual enterprise interface behaves, and avoids
maintaining two copies of the data. The design is also language-extensible: pointing the servers at a `seed-data-<language>/` folder serves that language's data, so adding a new language is a matter of adding a seed-data folder, not changing code.

## Human-in-the-loop: two paths

The agent never approves anything itself; **a human is always required**, but the role differs. A
**compliant** invoice is recommended for auto-approval, pending a person's confirmation — light,
confirmatory involvement. A **non-compliant** invoice is flagged for human review with a full
violation summary — substantive, decisional involvement. Either way the AI triages and prepares
the decision; a human makes the final posting. This mirrors a real approval queue and enforces
the read-only guarantee structurally rather than by trusting the model to behave.

## Validation

A local evaluation harness (`run_eval.py`) checks the system's behavior against the seed data
deterministically — the open-invoice total, the return window, the INV-1003 violation, the
compliant contrast case, and the injection-resistance report — passing all checks **independently
of the LLM**. Because it runs without calling the model, it is quota-free and fast, and it isolates
failures: if a demo misbehaves, the eval tells you immediately whether the problem is the data
layer, the tool logic, or the model's reasoning. This separation of deterministic logic from model
behavior is the same principle behind packaging compliance as a Skill.

## What I'd do next

Three extensions would move this from prototype toward production. First, **pass the end user's
identity through to the MCP servers** so the agent inherits Dynamics 365 and SharePoint's per-user
authorization, giving row- and role-level data scoping for free. Second, **expand the compliance
Skill** to cover the full policy — duplicate detection, currency rules, and terms-approval checks —
as additional deterministic checks alongside the PO rule. The architecture is also capability-extensible along a second axis: because the coordinator routes by tool description, a new function is added by standing up another read-only MCP server, wrapping it in a specialist agent, and registering it in the coordinator's tool list — no change to existing agents. A CRM agent or an HR-policy agent would drop in the same way `erp_agent` and `docs_agent` did. Third, **deepen bilingual support** with
an explicit evaluation set of Arabic queries to measure answer fidelity, and optionally localize
retrieved document text for Arabic-first users.


**Predictive analytics agent (future extension).** D365's historical transactional data is a labeled time series suitable for supervised learning — forecasting vendor spend, cash flow, or late-payment risk. In production, real-time queries use D365's OData JSON API (as modeled here), while model training would draw on bulk historical data exported via Synapse Link to columnar Parquet files. A trained model would be served through its own read-only MCP server and a forecasting specialist agent; the coordinator would route forward-looking questions — for example "what's our likely spend next month?", "what's the projected cash outflow next quarter?", or "which open invoices are at risk of late payment?" — to it, complementing the retrieval agents that answer "what happened." This predictive axis applies to the dynamic transactional (ERP) data, not the stable policy documents.

## Rationale, briefly

I chose the Agents for Business track because invoice-compliance triage is a concrete,
high-frequency task where an agent adds real value *and* where getting safety right matters: the
cost of a wrong automated approval is money out the door. The design reflects that — data behind
read-only tools, compliance made deterministic via a Skill, and a hard human-in-the-loop boundary
on any action that writes. Built on the systems enterprises already run, the result is an assistant
that is genuinely useful for day-to-day finance work while remaining safe to deploy.

---

**Code:** https://github.com/saroshk/adk-enterprise-agent-capstone — includes full setup instructions in the README.
**Video:** Video link
https://youtu.be/ZS01v1MGjns
