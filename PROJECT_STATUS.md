# Path 2 Skill — Status: DONE, WIRED, CONFIRMED WORKING

**Skill:** `.agent/skills/policy-compliance-check/scripts/check_invoice.py`
Entrypoint: `check_compliance(amount, po_number, payment_terms) -> dict`. Both smoke tests pass.

**Wired into:** `enterprise_agent/agent.py` as tool `check_invoice_compliance`
(added to `root_agent.tools`; coordinator instruction prefers the Skill for compliance checks).
Constants: `SKILL_SCRIPT_NAME = "scripts/check_invoice.py"`, `SKILL_ENTRYPOINT = "check_compliance"`.

**Confirmed working live in ADK:** direct call
"Run the compliance check skill directly with amount 12500, po None, terms Net45"
-> returned VIOLATION verdict citing POL-PROC-002, "FLAG FOR HUMAN REVIEW" (event #14).
Screenshot saved: demo-screenshots/scenario4-skill-compliance-violation.png

**How routing works:** coordinator (LLM) picks a tool by matching the request against each
tool's name + description. Compliance-verdict requests match check_invoice_compliance;
totals match erp_agent; policy-text match docs_agent. Earlier scenarios (1, 2, 3, security)
are untouched and still valid — the Skill is additive, not a replacement.

**Note (optional, later):** erp_agent looks up invoices by vendor account number (e.g. US-001),
not invoice number, so the direct Skill call is the reliable demo path. A fuller
"ERP fetches -> Skill judges" chain would need a small tweak to erp_server.py. Not required.

**DO NOT regenerate agent.py — it works.**

**Remaining:** optionally note Skill as 4th concept in README/CONCEPT_MAPPING, then submit (July 6).