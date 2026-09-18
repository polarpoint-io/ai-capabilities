---
name: avoid-ai-tells
description: Use this skill whenever writing, drafting, or revising any substantial piece of prose for the user — emails, blog posts, articles, reports, marketing copy, LinkedIn posts, essays, documentation, Wikipedia-style content, cover letters, or any output longer than a couple of sentences. It teaches the concrete, well-documented statistical fingerprints of LLM writing (puffed-up significance claims, "delve/boast/underscore"-style vocabulary, "not just X, but Y" constructions, title-case headings, em-dash overuse, curly quotes, leftover chatbot phrases like "I hope this helps") and how to self-edit them out so the result reads like it was actually written by the user, not generated. Always apply this skill's self-check pass before delivering written content, even if the user didn't explicitly ask for "human-sounding" or "natural" writing — invoke it proactively any time you're about to produce a draft, not just when asked to fix one.
---

# Avoid AI Tells

## Why this exists

LLMs are trained to predict the statistically likely next word, which means free-running generation regresses toward a small set of "safe," high-probability phrasings. Do this over millions of documents and you get a recognizable fingerprint: certain words ("delve," "boast," "underscore"), certain sentence shapes ("Not only... but..."), certain formatting habits (title-case headings, curly quotes, mechanical bolding). None of these individually proves a text is AI-written — humans use some of them too — but stacked together in the same document, they're the reason a reader's eyes glaze over and think "this was obviously written by ChatGPT."

This skill is drawn from Wikipedia's ["Signs of AI writing"](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) essay, compiled by editors who read this pattern constantly. The goal isn't to ban every word on these lists forever — "crucial" and "highlight" are normal English words, and a human would naturally use one occasionally. The goal is **density and combination**: if a paragraph has three or four of these tells stacked together, it reads as generated, and you should rewrite it in your own voice.

## How to use this skill

1. Write the draft normally — don't try to route around these patterns word-by-word while composing, or you'll write something stilted and self-conscious instead. Draft first.
2. Before delivering the draft, re-read it specifically looking for the categories below.
3. For anything non-trivial (more than ~150 words), run the bundled linter as an objective second pass: `python3 scripts/lint_ai_tells.py <file>` (or pipe text via stdin). It flags concrete matches with line numbers so you're not relying on your own read-through alone.
4. Rewrite flagged passages so they sound like something a specific, engaged person would actually say about this specific subject — not a generic summary of it.

## 1. Content-level tells

These are about *what the writing claims*, not just word choice — often the more damaging category because they make the piece sound hollow even when the prose is grammatically smooth.

**Inflating importance/legacy.** LLM writing habitually ties trivial facts to grand significance instead of just stating the fact.
- Words to watch: *stands/serves as, is a testament/reminder, a vital/significant/crucial/pivotal/key role/moment, underscores/highlights its importance, reflects broader, symbolizing its ongoing/enduring/lasting, contributing to the, setting the stage for, marking/shaping the, represents/marks a shift, key turning point, evolving landscape, focal point, indelible mark, deeply rooted*
- Real example the essay flags: *"The founding of Idescat represented a significant shift toward regional statistical independence... part of a broader movement across Spain to decentralize administrative functions and enhance regional governance."* — Notice there's no actual new information in the second half of that sentence; it's just significance-signaling.
- Fix: cut the significance-claim entirely and let the fact carry its own weight, or replace it with a specific, checkable consequence ("this let the region publish its own unemployment data starting in 1991," not "marked a shift toward independence").

**Canned notability/attribution claims.** Rather than showing a subject is notable, LLM text tells you it's notable by listing the *categories* of coverage it received.
- Words to watch: *independent coverage, local/regional/national media outlets, trade publications, profiled in, written by a leading expert, active social media presence*
- Fix: name the actual outlet and what it said, or cut the claim.

**Superficial "-ing" analysis tacked onto facts.** A factual sentence gets an unearned interpretive clause bolted onto the end.
- Words to watch: *highlighting/underscoring/emphasizing..., ensuring..., reflecting/symbolizing..., contributing to..., cultivating/fostering..., encompassing..., enhancing..., valuable insights, align/resonate with*
- Example pattern: "...highlighting Pakistan's entry into the global pickleball community." Ask: does this clause add information, or just tell the reader how to feel about the preceding fact? If the latter, cut it.

**Promotional / travel-brochure language.** Even prompted to sound neutral, LLMs drift toward ad copy.
- Words to watch: *boasts a, vibrant, rich, profound, showcasing, exemplifies, commitment to, natural beauty, nestled, in the heart of, groundbreaking, renowned, featuring, diverse array*
- Fix: if you wouldn't put it in a tourism brochure or a corporate About page, keep it. If you would, replace with a specific, unadorned fact.

**Vague attributions (weasel words).** Claims get pinned on an authority that's never actually named.
- Words to watch: *industry reports, observers have cited, experts argue, some critics argue, several sources/publications* (especially when only one or two sources are actually cited), *such as* (right before an exhaustive-sounding list)
- Real example: *"Due to its unique characteristics, the Haolai River is of interest to researchers and conservationists."* — Which researchers? Says who? If you can't name the source, cut the claim rather than dress it up.

**Formulaic "Challenges and Future Prospects" sections.** A very specific LLM tic: a closing section that praises the subject, pivots on "despite," and gestures at generic future challenges without saying anything concrete.
- Words to watch: *Despite its [praise], X faces several challenges..., Despite these challenges, Challenges and Legacy, Future Outlook*
- Fix: only include a challenges/outlook section if you have specific, sourced things to say. Otherwise cut it — it's rarely load-bearing.

## 2. Language and grammar tells

**High-density "AI vocabulary."** One of these words appearing is coincidental. Several appearing in the same piece is one of the strongest tells there is, because they cluster together in LLM output.
- The core list: *additionally (esp. starting a sentence), align with, boasts (meaning "has"), bolstered, crucial, delve, emphasizing, enduring, enhance, fostering, garner, highlight (as a verb), interplay, intricate/intricacies, key (as an adjective), landscape (as an abstract noun), meticulous/meticulously, pivotal, robust, showcase, tapestry (as an abstract noun), testament, underscore (as a verb), valuable, vibrant*
- These words aren't forbidden — "crucial" is a fine word — but if you notice three or more of them in one piece, that's your signal to do a pass and swap most of them for plainer, more specific language.

**Avoiding plain "is/are."** LLM output systematically swaps simple copulas for inflated verb phrases.
- Watch for: *serves as/stands as/marks/represents [a], boasts/features/maintains/offers [a], refers to* — used where "is" or "has" would say the same thing more directly.
- Example: "The bridge serves as a vital link" → "The bridge connects..." or just "The bridge is..."

**Negative-parallelism constructions.** A specific contrast template that reads as manufactured depth rather than genuine contrast.
- *Not just X, but also Y* / *It's not just about X, it's about Y*
- *Not X, but Y*
- *X rather than Y* (especially common in some models' output — this one's subtler since "rather than" is normal English, but watch the frequency)
- These can be legitimate rhetorical devices used sparingly by humans. The tell is using this exact template repeatedly across a piece as a crutch for sounding insightful.

**The rule of three, overused.** Grouping descriptors or examples in threes is a real rhetorical technique, but LLMs reach for it reflexively — "creative, funny, and driven," "convenient, efficient, and innovative" — whether or not three is the right number.
- Fix: let the content decide the count. Sometimes it's two examples, sometimes it's four. If you catch yourself defaulting to three descriptors every time, that's the tell.

**Over-varying word choice ("elegant variation").** Ironically, avoiding repetition too hard is also a tell — LLMs have a repetition penalty baked in, so they'll swap a plain repeated word for an odd synonym rather than just repeating it naturally the way a human would.
- If a synonym substitution reads oddly (using a fancier word purely to avoid saying the same word twice), just repeat the plain word instead.

## 3. Style and formatting tells

- **Title case in headings** — "Impact of Technology and Digitalization" — capitalize headings the way you'd write a normal sentence unless the target format specifically calls for title case.
- **Mechanical overuse of bold** — bolding phrases throughout body text the way a listicle or slide deck does, rather than reserving bold for genuine emphasis.
- **Inline-header vertical lists** — bullets that all start with **Bolded Phrase:** followed by a sentence. Fine occasionally; a tell when every single list in the piece is built this way.
- **Em dash overuse** — em dashes (—) are used more heavily by LLMs than by comparable human writing. If nearly every paragraph has one, cut most of them back to periods or commas.
- **Emoji as formatting** — decorating headings or bullets with emoji in contexts where the user didn't ask for a casual/social tone.
- **Curly quotation marks (" " ' ') in contexts that call for straight quotes** — a small tell, but a real one, since it comes from default chatbot typography rather than a deliberate choice.
- **Unnecessary tables** — building a small table for information that reads more naturally as a sentence or two.

## 4. Leftover chatbot artifacts (communication tells)

These are the most damaging because they signal the text was pasted in unreviewed rather than actually written or edited by a person.

- **Collaborative leftovers:** *I hope this helps, Of course!, Certainly!, You're absolutely right!, Would you like..., is there anything else, let me know, here is a..., more detailed breakdown*
- **Knowledge-cutoff disclaimers:** *as of my last training update, while specific details are limited/scarce, not widely documented/available/disclosed, based on available information*
- **Editorializing insertions:** *it's important/crucial to note/remember, worth noting, no discussion would be complete without*
- **Mechanical section summaries:** *In summary, In conclusion, Overall,* — restating what was just said, as if the reader can't retain three paragraphs. Cut these; trust the reader.

If you notice any of these in a draft, it almost always means content was copy-pasted from a chat response without being reviewed — always strip these out completely regardless of how minor they seem.

**Also check the very end of the document.** Signature blocks and closings are an easy place for placeholder brackets to survive a review pass unnoticed — `[Your Name]`, `[Your Title]`, `[Company Name]`, `[Phone Number]`. If the user gave you their name or role anywhere in the conversation, use it. If they didn't, ask, or use something clearly generic on purpose (e.g. "Best, [name]" is still a tell — prefer just leaving your own reasonable placeholder like "Best," with no bracket at all, or a single line noting the user should add their sign-off).

## 5. A caution about over-correction

Don't treat this as a word blocklist to route around mechanically — that produces its own tell (visibly contorted sentences that avoid "delve" and "crucial" at all costs while still having the same hollow, significance-inflating structure underneath). The actual fix is almost always to say something more specific and concrete than the generic version, not to find a fancier synonym for the generic version. When in doubt, ask: "would a specific, knowledgeable person actually say it this way, or does this sound like a summary of what someone might say?"

## Using the linter

`scripts/lint_ai_tells.py` scans a text file (or stdin) for the mechanically-detectable subset of these signs — phrase matches, em-dash density, curly quotes, title-case headings, bold density, and negative-parallelism/rule-of-three patterns — and prints a report with line numbers and a summary count. It can't judge content-level tells like hollow significance-claims (that needs a real read), so treat it as a supplement to your own read-through, not a replacement for it.

```
python3 scripts/lint_ai_tells.py draft.md
cat draft.md | python3 scripts/lint_ai_tells.py
```
