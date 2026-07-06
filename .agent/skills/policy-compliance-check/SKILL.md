------
name: policy-compliance-check
description: Use this skill when the user asks to check whether a specific vendor invoice complies with the procurement policy, or to validate compliance for a given amount, purchase order status, and payment terms. Returns a deterministic verdict citing the specific policy rule broken (if any). Do not use for retrieval-only questions about invoices or policy text; use for compliance verdicts only.
---

# Procurement Policy Compliance Check

## Goal
Deterministically verify whether an invoice complies with the Procurement & Invoice Approval Policy (Document ID: POL-PROC-002). Return a structured verdict that identifies compliance status, any violated rule, the cited policy document, and a recommendation (auto-approve, flag for review, or reject).

## Instructions
- Analyze the user's request to extract three inputs about the invoice in question:
  1. `amount` (in USD, numeric)
  2. `purchase_order_number` (string or null if none)
  3. `payment_terms` (e.g., "Net30", "Net45")
- If any of the three inputs are unclear or missing from the request, first look them up using the erp_agent tool, then proceed.
- Use the script `scripts/check_invoice.py` to perform the deterministic policy check.
- Command: `python scripts/check_invoice.py --amount <amount> --po <po_number_or_None> --terms <terms>`
- Present the verdict to the user with the four fields: status, rule broken (if any), cited policy document, and recommended action.

## Examples

Example 1 (violation — no PO for large invoice):
Input: amount=12500.0, po=None, terms=Net45
Output: {"status": "VIOLATION", "rule_broken": "Purchase order requirement for invoices >= USD 10,000", "cited_policy": "POL-PROC-002", "recommended_action": "FLAG FOR HUMAN REVIEW"}

Example 2 (compliant — small invoice with PO):
Input: amount=6000.0, po="PO-6001", terms=Net30
Output: {"status": "COMPLIANT", "rule_broken": null, "cited_policy": "POL-PROC-002", "recommended_action": "AUTO-APPROVE PENDING HUMAN CONFIRMATION"}

## Constraints
- Never invent invoice details. If the request lacks explicit amount, PO, or terms, use the erp_agent tool to fetch them before calling the script.
- Never perform an actual approval action. This skill returns a verdict only; the coordinator is responsible for the HITL escalation flow.
- Do not paraphrase or reinterpret the policy rules — return only what the script outputs.
- Cite the policy document ID exactly as returned (POL-PROC-002).