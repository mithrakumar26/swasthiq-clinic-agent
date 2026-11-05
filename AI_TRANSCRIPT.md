# AI Transcript

The following is a concise record of the coding-assistant directions used to create this implementation.

1. "Read the SwasthiQ assignment and starter pack first. Implement exactly the six named tools and the POST /agent/run schema. Preserve the supplied clinic.json and conversation scripts."
2. "Prioritise deterministic safety: emergency escalation must pre-empt scheduling, ambiguous patients must not be guessed, and unauthorised third-party changes must be escalated."
3. "Implement booking and rescheduling with slot validation and atomic mutation. Never claim success unless the tool returns the resulting appointment."
4. "Build the two React views shown in the assignment: Handoff Queue and Conversation Detail, with a shared sidebar and inline tool-call transcript."
5. "Add eight adversarial conversation scripts in the supplied runner schema, tests, DECISIONS.md, and clear local run instructions."
