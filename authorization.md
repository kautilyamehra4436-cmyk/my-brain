# 🚦 4 Authorization Gates

## Gate 1: Tier
| Tier | काम | Approval |
|---|---|---|
| 1 | पढ़ना, draft, search | Auto |
| 2 | email, file update | Telegram |
| 3 | payment, delete, sign | Face ID |

## Gate 2: Money 💰
- < ₹500 → Telegram
- ₹500–₹5,000 → Face ID + amount
- > ₹5,000 → Face ID + "I APPROVE [amount]" + 10-min cooling
- Recurring → हमेशा Tier 3

## Gate 3: Legal ⚖️
- पहले पूरा summary
- Face ID + "I SIGN [name]"
- High-risk → 24-hour cooling
- AI कभी खुद sign नहीं

## Gate 4: Dead-Man's Switch
- 24 घंटे approval नहीं → सब रुको
- 30 दिन नहीं आए → Legacy Mode (legacy.md)

## Emergency
- Telegram `/stop` (out-of-band)
- GitHub Actions → Cancel all
