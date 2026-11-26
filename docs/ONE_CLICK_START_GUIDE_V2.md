# Advait v32.0 — One-Click Start Check v2

## Run
1. Open: https://github.com/kautilyamehra4436-cmyk/my-brain/actions/workflows/advait-one-click-start-check-v2.yml
2. Press **Run workflow**.
3. Keep branch `main` and the default model `nvidia/nemotron-3.5-lightning:free`.
4. Press the green **Run workflow** button.

## What it does
Runs the complete unit tests, compiles core/tests, validates the configured GitHub Actions secret, then sends exactly one fixed, non-sensitive smoke request to the selected OpenRouter model ending in `:free`. The workflow sets `PYTHONPATH=.` so the smoke script can import the repository's `core` package when launched from the `scripts` directory.

## Safety boundary
- API key is read only from the `OPENROUTER_API_KEY` Actions secret; never paste it into chat.
- No paid model, paid fallback, purchase, payment, transfer, customer outreach, or bounty execution.
- Contents permission is read-only.
- Only metadata audit DB is uploaded, with 7-day retention.
- This is a readiness/provider check, not a 24/7 autonomous Advait runtime.

## Result
Green means unit tests + compile + one actual free-provider smoke call succeeded. Red means inspect the failing step in the Actions logs. A generic provider response is not shown or stored by this workflow.
