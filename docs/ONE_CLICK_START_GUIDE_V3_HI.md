# Advait v3 — one-click provider check

1. Open https://github.com/kautilyamehra4436-cmyk/my-brain/actions/workflows/advait-one-click-start-check-v3.yml
2. Press **Run workflow**; keep branch `main`.
3. Keep the default model `nvidia/nemotron-3.5-lightning:free`.
4. Press the green **Run workflow** button.

This run executes the unit tests and compile check, then makes exactly one non-sensitive text request to the selected OpenRouter `:free` model. The request disables reasoning to reserve the small output budget for a text reply. The script accepts plain text and text-block content, detects API-level errors, and records only hashes/status/usage/latency/error metadata. It never prints or stores the API key, prompt, or generated answer.

A green run means this one provider call worked. It does not mean the autonomous worker, scheduler, customer outreach, bounty execution, or payments are live. No paid fallback or scheduled runs are enabled.
