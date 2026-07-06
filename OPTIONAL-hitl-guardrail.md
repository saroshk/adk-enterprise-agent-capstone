# OPTIONAL — Human-in-the-loop (HITL) enhancement

> This is an **optional** enhancement mirroring Day 4's expense-triage pattern. It changes
> how the agent handles action requests: instead of a flat refusal, it *escalates to a human*
> with a prepared summary. Your three required concepts are already met without this — only
> add it if you want the extra Day-4 credit and have time. It will change the wording of your
> refusal demo, so you'd re-capture that one screenshot.

## What changes and why

Right now, "Approve invoice INV-1003" gets a flat refusal: *"I cannot approve invoices. I have
read-only access."* That's correct and safe. The HITL version keeps the safety (the agent still
never acts) but reframes the response as **triage**: it declines to act itself, states that the
action needs human approval, and hands the human a ready-made summary of what to decide. That is
exactly the human-in-the-loop pattern from Day 4 — the agent prepares the decision, a person makes
it.

This is an instruction-level change only. No new tools, no risk to the read-only guarantee.

## How to apply (in an editor — no terminal needed)

Open `enterprise_agent/agent.py`. Find the `GUARDRAIL = """ ... """` block (around lines 59–69)
and replace the single read-only rule with the HITL version below.

**Find this line inside GUARDRAIL:**
```
- You have READ-ONLY access. You cannot create, modify, approve, or pay anything.
  If asked to take such an action, refuse and explain that this assistant is read-only.
```

**Replace it with:**
```
- You have READ-ONLY access. You cannot create, modify, approve, or pay anything yourself.
  If asked to take such an action (e.g. approve or pay an invoice), do NOT perform it. Instead,
  escalate to a human: state clearly that this action requires human approval and cannot be done
  by this assistant, then provide a short HUMAN REVIEW SUMMARY the approver needs -- the item in
  question, any relevant facts you can look up read-only (amount, PO, policy compliance), and the
  specific decision required. Never take the action; only prepare it for a person.
```

That's the whole change. Save the file and restart `adk web`.

## Expected new behavior (for your re-captured demo)

Prompt: **Approve invoice INV-1003**

Instead of a flat refusal, the agent should now respond along these lines: it can't approve the
invoice itself as it's read-only, this needs human approval, and here is what the reviewer needs —
INV-1003, USD 12,500, no purchase order, which violates the procurement policy (POL-PROC-002)
requiring a PO for invoices of USD 10,000+. Decision required: approve as exception, or reject.

Note: it may now call `erp_agent`/`docs_agent` to gather the summary facts, so the trace will show
tool calls (unlike the flat-refusal version, which called nothing). Both behaviors are valid
security stories; the HITL one is richer.

## Writeup angle

If you adopt this, describe it as: "The agent enforces read-only safety but, for action requests,
performs human-in-the-loop triage — it refuses to act and instead escalates with a prepared review
summary, mirroring an approval-workflow handoff." That ties your security concept to Day 4's
ambient-agent triage pattern.
