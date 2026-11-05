# Sunrise Clinic — Conversational Front Desk Agent

A React + FastAPI take-home implementation for the SwasthiQ SDE Intern assignment.

## 1. Project Overview

Sunrise Clinic is a conversational front desk agent designed to handle routine clinic appointment operations while prioritizing patient safety, authorization, and human escalation.

The application supports patient lookup, appointment availability searches, appointment booking, rescheduling, cancellation, and escalation to a human clinic representative.

The current implementation uses a deterministic, rule-based conversation policy rather than an LLM.

## 2. Project Structure

```text
swasthiq-clinic-agent/
├── backend/
│   ├── app/
│   │   └── main.py
│   ├── tests/
│   ├── clinic.json
│   └── requirements.txt
├── frontend/
│   ├── src/
│   ├── package.json
│   └── index.html
├── adversarial/
├── conversations/
├── runner.py
├── schema.md
├── README.md
├── DECISIONS.md
├── AI_TRANSCRIPT.md
├── .gitignore
└── run.sh
```

## 3. Technologies Used

**Backend**
- Python 3.12
- FastAPI
- Pydantic
- SQLite/in-memory data handling as implemented
- Pytest

**Frontend**
- React
- Vite
- JavaScript
- CSS

## 4. Quick Start

Requirements:
- Python 3.12 recommended
- Node.js 18 or later
- npm

### Backend setup

Open Terminal 1:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Backend URLs:

- Health check: http://localhost:8000/health
- API documentation: http://localhost:8000/docs
- Agent endpoint: http://localhost:8000/agent/run

### Frontend setup

Open Terminal 2:

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL printed in the terminal, normally:

http://localhost:5173

## 5. Required Agent Tools

The implementation provides six deterministic tools:

1. `search_slots(doctor_id, date, window?)`
2. `book_appointment(patient_id, doctor_id, date, start)`
3. `reschedule_appointment(patient_id, appointment_id, doctor_id, date, start)`
4. `cancel_appointment(patient_id, appointment_id)`
5. `lookup_patient(name, phone?, patient_hint?)`
6. `escalate_to_human(reason, detail)`

These tools operate as ground-truth functions and do not call an LLM.

## 6. API Contract

**Endpoint:** `POST /agent/run`

Example request:

```json
{
  "conversation_id": "cv_example",
  "today": "2026-10-01",
  "turns": [
    "Hello, I need an appointment with Dr. Rao."
  ]
}
```

The response includes:

- `conversation_id`
- `tool_calls`
- `terminal_state`
- `escalation_reason`
- `patient_id`
- `appointment_id`
- `reply`
- `metrics`

The response follows the supplied `schema.md` contract.

## 7. Safety and Data Consistency

The implementation includes the following safety measures:

- Patient lookup is performed against the supplied clinic dataset.
- Ambiguous patient matches are not arbitrarily selected.
- Caller authorization is checked for appointment operations.
- Urgent clinical symptoms take priority over appointment booking.
- Medical advice and medication requests are escalated.
- Booking validates slot availability before creating an appointment.
- Rescheduling validates the destination before modifying the existing appointment.
- Cancellation and rescheduling check appointment ownership.
- Prompt-injection attempts and bulk destructive requests are refused.
- Unavailable requested slots are not silently substituted.

## 8. Running the Tests

Start the backend first.

From the repository root:

### Original conversation scenarios

```bash
python3 runner.py --repeat 3
```

### Adversarial scenarios

```bash
python3 runner.py --dir adversarial --repeat 3
```

### Backend unit tests

```bash
cd backend
source .venv/bin/activate
pytest -v
```

### Recorded test results

The following results were obtained during local testing:

| Test suite | Result |
|---|---|
| Original conversation scripts | 15 scenarios, 3 runs each, zero reported failures |
| Adversarial scripts | 8 scenarios, 3 runs each, zero reported failures |
| Backend unit tests | 4 passed |
| Determinism checks | Stable across 3 runs |

These results demonstrate successful execution of the supplied runner checks and the four included backend unit tests. They do not establish complete coverage of every possible conversation.

## 9. Model and Metrics Disclosure

This implementation uses a deterministic, rule-based conversation policy. No LLM model is used.

The `tokens` metric is an estimated count based on the implementation's counting method. It is not provider-reported token usage or billing.

The `latency_ms` metric records server-side execution latency.

The deterministic approach was selected to make behavior reproducible across the supplied conversation and adversarial test scripts.

## 10. Known Limitations

- Natural-language parsing supports the supplied examples and selected English, Hindi, and Hinglish expressions; it is not general-purpose language understanding.
- The implementation does not use an LLM.
- Dashboard statistics and handoff examples should be treated as demonstration data unless connected to actual persistent conversation records.
- Conversation and clinic data handling follows the current in-memory/reset behavior of the implementation; it is not a production database integration.
- Frontend conversation state requires further verification. In particular, a previous escalation reason was still visible in the outcome panel after a successful booking.
- Production deployment requires configuring the frontend API URL and restricting backend CORS to the deployed frontend origin.

## 11. Deployment

Suggested deployment options:

**Backend:** Render

Build command:

```bash
pip install -r requirements.txt
```

Start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

**Frontend:** Vercel or Netlify

Configure `VITE_API_URL` to point to the deployed backend base URL and run:

```bash
npm run build
```

Configure CORS to allow only the deployed frontend origin before public deployment.

## 12. Project Decisions

Refer to `DECISIONS.md` for implementation choices, safety decisions, trade-offs, and assumptions.

Refer to `AI_TRANSCRIPT.md` for disclosure of AI assistance used during development.

## 13. Submission

- GitHub repository: [Insert public repository URL]
- Live application: [Insert URL if deployed]
- Demonstration video: [Insert shareable video URL if recorded]

