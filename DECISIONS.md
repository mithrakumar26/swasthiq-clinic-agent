# DECISIONS.md

## Scope and architecture
- The evaluator's `/agent/run` contract is authoritative. The implementation uses a deterministic conversation policy rather than a probabilistic LLM so that the supplied replay scripts have stable outcomes. This is explicitly named in the README; no LLM is called from the tool layer.
- `clinic.json` is reloaded into a fresh in-memory copy for every `/agent/run`, matching the starter schema's explicit reset-between-conversations rule.
- The six required tools are implemented as methods on `ClinicTools`. Each invocation is recorded, including failed tool calls.
- The web dashboard uses synthetic counters and synthetic handoff rows. It does not expose or fabricate real patient records.

## Safety decisions
- Urgent symptom detection runs before any scheduling intent. A detected emergency calls only `escalate_to_human`; it never proceeds to booking, rescheduling, or cancellation.
- Medical-advice requests are escalated. The agent does not recommend medicines, doses, diagnoses, or expected recovery times.
- A generic surname returns every matching patient candidate. Multiple matches trigger `ambiguous_patient`.
- A third-party adult record cannot be changed based only on knowing the patient's name. A matching registered phone or explicit listed-guardian relationship is required.
- Prompt-injection and bulk-operation requests are refused. The six-tool contract does not expose bulk cancellation.
- Requested unavailable slots are not silently replaced by a different time.

## Consistency
- Booking and rescheduling validate the destination slot while holding a re-entrant lock. Rescheduling validates the new slot before mutating the original appointment, so a failed move leaves the original intact.
- A booking is only reported after `book_appointment` returns a created appointment object.
- Each appointment is a 15-minute interval. The tool checks the exact start time against generated free slots.

## Ambiguities and limitations
- The brief describes "two appointment windows per day each", while `clinic.json` contains day-specific windows that can include multiple windows and, for Dr. Rao on Monday, overlapping windows (11:45–12:00 overlaps the 09:00–12:00 window only at the boundary). We preserve the supplied doctor windows as the source of truth and do not normalize them.
- The examples use Hindi, English, and Hinglish. Relative date/time parsing is a deliberately small deterministic vocabulary, not a general natural-language parser. Unrecognised or incomplete dates are not guessed.
- `runner.py` resets data for every conversation. Therefore cross-request persistence is intentionally not provided by the evaluation endpoint. In production, a transactional persistent store would be required.
- The UI requirements show a handoff queue and a conversation detail view. The React app implements both, sharing a persistent sidebar. Dashboard counters and handoff queue content are demo-only synthetic data; live submitted conversations are rendered from the API response.
- Token and latency figures are best-effort estimates. This baseline uses no external LLM, so token count is a deterministic character/tool-payload estimate and latency is measured server-side. Do not present these as provider-billed token usage.
- The assignment's sample date is 2026-10-01. The API always uses the request's `today` field for relative dates and never uses the server clock.
