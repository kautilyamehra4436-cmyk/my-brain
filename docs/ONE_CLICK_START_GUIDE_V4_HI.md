# Advait v4 — one-click provider check

1. Open https://github.com/kautilyamehra4436-cmyk/my-brain/actions/workflows/advait-one-click-start-check-v4.yml
2. Press **Run workflow**; keep branch `main`.
3. Keep default model `nvidia/nemotron-3.5-lightning:free`.
4. Press the green **Run workflow** button.

v4 runs unit tests and compile checks, then makes at most two identical, generic, non-sensitive OpenRouter `:free` requests. Each network attempt has a 90-second timeout and a three-second delay before one retry. Reasoning is disabled. The script handles text and text-block content and records only metadata/hashes, never credentials, prompt or answer text.

A green run proves this bounded provider check only. It does not activate the autonomous worker, scheduler, bounty execution, browser operations, customer outreach or payments. No paid fallback or scheduled execution is enabled.
