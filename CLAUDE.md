# Project conventions

## No emoji in backend code or logs

Never put emoji in Python `print()`/logging calls anywhere under `BackEnd/`. This backend runs on Windows, where `stdout`/`stderr` default to the system codepage (`cp950` for Traditional Chinese Windows) when not attached to a UTF-8 console — that codepage cannot encode emoji, so any `print()` containing one raises an unhandled `UnicodeEncodeError` and crashes the request with a 500.

This already happened in production code: `BackEnd/api_v2/routes/reports.py`'s `get_batch_reports()` had a `print(f"...✅ Returning...")` debug line that made `POST /api/v2/reports/batch` fail 100% of the time on Windows, even though the endpoint's actual logic had already computed the correct response. Fixed by stripping the emoji; same class of bug was also present in `BackEnd/api_v2/asgi.py`.

Use plain text markers (`[OK]`, `ERROR:`, `[Batch Reports]`) instead of ✅ ❌ ⚠️ 🔥 in any `print`/logging call.
