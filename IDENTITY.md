# What Osaka Is

This page is the test every change is checked against, from a bug fix to a
new feature to the 2.0 release. If a change makes Osaka more like every
other language at the cost of one of the four parts below, it is the wrong
change, even if it is convenient.

## The four parts

### 1. Truth and grain

Every value carries how certain it is. `truthaboutgrain` values are
trusted; `grainsoftruth` values are not yet. Certainty flows through
expressions: mixing in grain makes the result grain.

Control flow only acts on truth. An `if` or `while` whose condition is
grain is an error, not a guess. To act on uncertain data you must vouch for
it: `Americaya(x)` promotes one value, `Getittogether()` stabilises all
unresolved grain.

*Why it matters:* the language makes you say out loud when you decide to
trust something. That is the core idea, and the reason to use Osaka.

### 2. Mutation as a ritual

Changing something is a deliberate act, not a side effect.

| Keyword | Meaning |
| --- | --- |
| `Ah(x)` | Acknowledge that `x` is about to change. Without it, a change is warned about. |
| `Hecho(x)` | Freeze `x`. Later changes are blocked. |
| `Ivebeengot(x)` | Lock `x` as legacy. Later changes are blocked. |
| `youknowsealsright(x)` | Assume `x` is fine; change it without ceremony. |
| `Ohmygah(x)` | A soft, non-fatal alarm about `x`. |

### 3. The Osaka voice

`Say`, `Americaya`, `SataAndagi`, `Ohmygah`, `Getittogether`, `Escalator`,
`Elevator`. The names are whimsical; the meanings are real. The voice is
what makes an Osaka program recognisably Osaka.

### 4. Proof over trust

Osaka does not ask to be believed:

- the Python interpreter and the bytecode VM run the same programs and are
  checked against each other (the Equivalence Lock);
- the compiler, written in Osaka, compiles itself to a byte-identical
  fixed point (Gate C), on the Osaka VM (Gate D), and on the native VM
  with no Python at all (Gate E);
- every recorded result says which compiler produced it.

## Rules that protect the identity

1. **Never rename or remove an identity keyword.** No plain-English
   synonyms either: no `const` beside `Hecho`, no `trust()` beside
   `Americaya`. Aliases dilute the voice.
2. **Fix friction by making identity features smarter, not optional.**
   When truth and grain get in the way (the "Americaya tax"), the answer is
   better kind tracking, not a switch that turns kinds off.
3. **Give no-op identity features real meaning instead of letting them
   rot.** `Escalator` and `Elevator` are parsed but do nothing today; they
   get a meaning (planned: strictness levels), not a deprecation.
4. **Plain syntax stays plain.** `if`, `while`, `func`, `return` are fine.
   The personality lives in the meaning, not in making everything strange.
5. **Osaka names are for Osaka concepts.** A new feature gets an Osaka name
   only when it is an Osaka idea (like a strictness level). Ordinary
   utilities such as `split` or `join` keep ordinary names.
6. **Outside data is not truth.** Anything from outside the program (files,
   arguments, randomness, key presses) should arrive as grain and be vouched
   for before it drives control flow.
7. **No optimisation without proof.** Every performance change must keep
   the compiler reproducing itself byte for byte and keep the backends in
   agreement.

## How to use this page

When reviewing a change, ask:

- Does it remove, rename, or add a synonym for an identity keyword? → No.
- Does it solve a truth/grain annoyance by weakening the rule? → Find the
  smarter fix instead.
- Does it introduce a new behaviour the interpreter and VM disagree on? →
  Not mergeable; CI's known-divergence list may only shrink.
- Does it change the compiler? → Re-run the gates; results must name the
  compiler hash that produced them.
