# Token Usage by Account -- Findings

Generated: 2026-07-15 13:52:02
Test window checked: 2026-06-26 - 2026-06-30 (TW local)

## Headline finding: chat_messages cannot explain the vendor bill's size

Combined UAT+PRD `chat_messages` total for the billed days (excluding the test window): **372,675 tokens**.
DeepSeek vendor-billed total for the same billed days: **104,912,880 tokens**.

DB-tracked chat activity is only **~0.36%** of what the vendor billed for the same billed days. The daily shapes match exactly against the customer's existing xlsx/html report (same source table), so the DB query itself is correct -- it simply cannot be the (or even a significant part of the) source of the vendor's token count.

**Implication**: the account breakdown below reliably explains who is behind the test-window spike and every other data point *inside* `chat_messages`, but it cannot explain why the vendor invoice is orders of magnitude larger. That gap must come from something outside the `/chat` code path entirely -- candidates worth checking next: other backend calls to the DeepSeek API that don't write to `chat_messages` (e.g. RAG/report-generation calls in `context_builder.py`, embeddings, retries), a batch/background job, or the DeepSeek API key being used by something other than this application. This needs to be investigated on the DeepSeek account/API-key side, not the chat database, before the "why did usage exceed expectations" question can be fully answered.

## Accounts responsible for the 2026-06-26-2026-06-30 test window (414,563 tokens)

| Account (user_id) | Tokens in window | % of account's total tokens | Environments |
|---|---|---|---|
| evah0806@gmail.com | 344,216 | 85.3% | PRD, UAT |
| contact@wepredict.io | 70,347 | 45.8% | PRD, UAT |

## Top 10 accounts by total tokens (whole period)

| Account (user_id) | Total tokens | Sessions | Environments |
|---|---|---|---|
| evah0806@gmail.com | 403,718 | 5 | PRD, UAT |
| contact@wepredict.io | 153,707 | 5 | PRD, UAT |
| evaforeva2862@gmail.com | 149,766 | 6 | PRD |
| eva.wepredict@gmail.com | 80,047 | 8 | UAT |
| test@test.com | 0 | 1 | UAT |

## Notes on the accounts seen

- 5 distinct `user_id` values appear in `chat_messages` across the whole period, across both databases. There is no evidence in this data of any account outside this set -- i.e. no unidentified/external end-user traffic shows up in `chat_messages` for this period.
- Accounts appearing in short, high-volume bursts on only a handful of days (rather than steady daily use) are more consistent with manual or automated testing sessions than ongoing product usage. Whether specific addresses map to WePredict team members, an internal tester, or something else needs to be confirmed with whoever has visibility into who was assigned each address -- this data only shows the email string itself.
