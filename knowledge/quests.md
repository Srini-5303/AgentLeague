# Eldervale — Quests

**Type:** Quest
**Tags:** quests, main-quest, story, stages, eldervale

## Main Quest: The Shards of Máni
Find the Shards of the broken moon and bring them to the Well of Urðr before Kael Thorn, the Hollow Court, or the sky itself decides the fate of Eldervale. Four stages, branching outcomes.

### Stage 1 — The Ruined Chapel
The party investigates the burned hof-mission and finds the ancient **eye-sigil** above the altar. Reading it (Lyra, Arcana) reveals it is a map to the Moonlit Gate and a clue to the three truths the Gate demands. Complication: the Hollow Court's dead also seek the sigil, and missionaries want it destroyed.
**Advances when:** the sigil is deciphered (`world_flags.sigil_read = true`).

### Stage 2 — The Moonlit Gate
The party journeys to the Well of Urðr beneath the glacier and must **speak three conflicting truths** into the well to open the Gate. Each truth must cost the speaker something real. Comforting lies open it the wrong way (see secrets). Rivals and factions converge here.
**Advances when:** the three truths are spoken truly (`world_flags.gate_open = true`).

### Stage 3 — The Memory Vault
Through the open Gate lies the frozen pre-Shatter world, where the last whole **Shard of Máni** waits among the motionless dead. The party must move through a past that resists remembering, and choose what to take and what to leave.
**Advances when:** the Shard is recovered (`world_flags.shard_taken = true`).

### Stage 4 — The Reckoning
With the Shard at the Well, the party decides Eldervale's fate. Multiple endings (see below). Kael Thorn, the Order, and the Hollow Court each press their case.
**Completes when:** the player chooses an ending (`world_flags.ending` set).

## Endings (Stage 4)
- **Re-Seal the Sky** — Máni is made whole; fate returns; the dead lie down again. But fate restored means Ragnarök proceeds as prophesied. A peace that ends.
- **Leave the Wound Open** — The future stays unwritten and free, but the dead and the giants keep spilling through. A freedom that bleeds.
- **Claim the Shard's Power** — The player takes Máni's power for themselves (or yields it to Kael), becoming something more than mortal to hold the sky by will alone. A throne over an uncertain world.

## Side Quests (unlocked by world_flags)
- **The Champion of Two Seas** — win a holmgang against Gunnar Two-Seas to claim the Shard buried under Hedeby Reach. (`world_flags.hedeby_shard`)
- **The Burning Grove** — defend an Order of the Silver Root grove from missionaries; earns Old Yrsa's trust. (`world_flags.yrsa_trust`)
- **An Oath to the Dead** — bargain with Astrid Hel-tongue for safe passage; costs a secret or a grave-debt. (`world_flags.court_pact`)

## Secrets
- [GM ONLY] The "correct" three truths for Stage 2 are personal to the party: one truth each that the speaker would rather not admit (e.g., Bran's guilt that his jarl's hall burned because he was away; Lyra's pride; the player's own buried regret elicited in play). The GM should weave these from established history, not a fixed script.
- [GM ONLY] Recovering the Shard in Stage 3 forces a choice: taking it wakes one of the frozen dead (Astrid's origin). Leaving a grave-good in exchange lets the party pass unharmed.
- [GM ONLY] If Kael is at "ally" trust by Stage 4, a fourth ending unlocks: the party and Kael split Máni's power and hold the Wound half-open together — the only ending that is neither doom nor bleeding, but it costs the life of one named companion, chosen by the player (a HITL-gated, irreversible act).
