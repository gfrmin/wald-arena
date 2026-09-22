# Questions for the owner

Numbers and rulings the brief leaves open. Nothing below is defaulted in code; each blocks only what it names.

## Raised in session 1 (the oracle)

1. **Ladder.** The brief names the US 15-rung ladder, $100 → $1,000,000, safe havens at Q5 ($1,000) and Q10
   ($32,000). `proto.py`'s ladder is different: $500 … $1,000k at Q14 and **$10,000k at Q15**, havens at $5k and $50k.
   The oracle was proved on the prototype's ladder (that is where $294.5k comes from). Which ladder does play use?
2. **Lifeline money prices.** `phone` and `audience` are model calls, so each costs real dollars. The prototype
   charged them nothing (only `llm` was priced, $1/read). Should their API cost × λ_usd be charged too, on top of
   the option value? The oracle takes a price per instrument, so either works; it needs the number.
3. **The LLM read after a 50:50.** The oracle, like the prototype and the brief, models every read as conditionally
   independent of the 50:50 given the truth: the LLM's report still ranges over all four options. In play, is the
   LLM (and the friend, and the audience) shown the reduced question after a 50:50? If yes, the kernel after a
   50:50 is a different instrument and needs its own calibration.
