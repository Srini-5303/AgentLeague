# Eldervale — Homebrew Rules

**Type:** Rules
**Tags:** rules, mechanics, dice, combat, eldervale

These rules tell the GM and the rule engine how Eldervale resolves uncertainty. The dice are law (see dice.py / rules.py).

## Checks
All uncertain actions resolve as **d20 + modifier vs a Difficulty Class (DC)**.
- **Success:** total ≥ DC.
- **Partial:** total within 4 below DC (you get part of what you wanted, with a cost).
- **Failure:** total more than 4 below DC.
- **Natural 20** always succeeds; **natural 1** always fails (the Norns' jest).

**DC bands:** trivial 6 · easy 9 · medium 12 · hard 15 · very hard 18 · legendary 21.

## Common Checks by Class
- **Warrior (Bran):** Might, Athletics, Attack — never seiðr.
- **Mage (Lyra):** Arcana, rune-lore, seiðr — never brawling.
- **Rogue (Sable):** Stealth, Sleight of Hand, Perception, Insight.
- **Healer (Mirra):** Medicine, Insight, Religion — never thievery or front-line combat.
- **Rival (Kael):** Persuasion, Deception, Attack — as the scene demands.

## Seiðr Backlash (the Shatter Tax)
Since the Shatter, magic is treacherous. When the Mage casts and rolls a **natural 1–3**, the spell backlashes: apply a minor condition (e.g., "rattled", "drained") to the caster in addition to the failure. Great power, real risk.

## Combat
- **Initiative:** each combatant rolls d20; act in descending order.
- **Attack:** d20 + ATK vs target's AC. Success deals full damage, partial deals half, failure deals none. (Engine: ATTACK_DAMAGE = success 6 / partial 3 / failure 0; scale per bestiary.)
- **Down at 0 HP:** a character at 0 HP is out of the fight (unconscious or dying), not auto-dead. Death of a named character is a HITL-gated, irreversible event.

## Oaths and Trust
- Oath-rings bind alliances; keeping an oath to Kael Thorn moves his **trust_level** up (hostile → uncertain → neutral → ally); breaking one drops it to hostile permanently.
- Mercy to a yielding foe and honesty in a bargain raise NPC trust; cruelty and broken oaths lower it.

## The Invisible Clock
The longer the Wound stays open, the bolder the dead and the sky-wolves grow. The GM may escalate encounter scale over many turns. Speed has a cost; so does haste.

## Human-in-the-Loop
Truly irreversible acts — killing a companion, betraying the party, destroying a Shard — pause for explicit player confirmation before they resolve. The saga remembers what you choose.

## Secrets
- [GM ONLY] Do not surface DCs or raw mechanics to the player in narration; describe difficulty in fiction ("the lock is wickedly old") and let the dice events carry the numbers to the UI.
- [GM ONLY] The three-truths puzzle at the Moonlit Gate is roleplay, not a roll: judge whether each truth genuinely costs the speaker. Honest, costly truths open the Gate cleanly; evasions tear the Wound.
