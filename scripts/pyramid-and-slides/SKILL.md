---
name: pyramid-and-slides
description: "Structure a blog post, article or guide with Minto's full Pyramid Principle, then derive a companion deck (Slides artifact, pptx, Marp Markdown, or frontend-slides HTML) from the same argument using 2026-updated presentation rules. Use for 'write this + a deck', 'turn into slides', 'make this a Marp deck', 'structure this article/guide'."
---

# Pyramid + Deck Structure

Two-part method. Part 1 builds the pyramid for the written piece correctly (not just "answer first"). Part 2 derives the accompanying deck from that same pyramid instead of re-verbalizing the article as slides.

## Part 1: The Pyramid (article, blog post, guide)

**Governing thought.** The top of the pyramid must be a complete sentence making a claim, never a topic label. "Organizational issues" is not a governing thought; "our reporting structure is causing duplicated work" is. If you can't write it as a sentence with a verb, you haven't found it yet.

**Vertical logic (the actual engine of the method).** Every point you make raises an implicit question in the reader's mind (why is that true? how does that work? so what?). The point(s) directly beneath it exist only to answer that specific question — nothing else belongs there. Before adding any bullet, ask "what question does the point above this raise, and does this bullet answer exactly that question?"

**Horizontal logic — pick one per group:**
- *Deductive*: premise, premise, conclusion. Each point necessitates the next; the order is fixed and can't be reshuffled.
- *Inductive*: same-kind items (reasons, risks, steps, regions, time periods) summarized by one inferred sentence — not a label like "three reasons." Test every inductive group against MECE: no two items overlap, and nothing relevant to the group is missing. Order inductive groups by whichever is honest: time, structure (parts of a whole), or degree/comparison.

**SCQA to derive (not just introduce) the governing thought.** Situation: what the reader already accepts as true. Complication: what disturbed it or created tension. Question: the open question that tension raises. Answer: your governing thought. If you can't state a Complication, you probably don't have a real Question yet, which means the "Answer" you've drafted is asserted, not earned — go back a step.

**Building order.** Top-down when the answer is already clear: state it, then find the 3-5 things that would have to be true for it to hold, and MECE-test them. Bottom-up when unsure: list everything you know, cluster into MECE groups, then for each cluster ask "so what does this group, taken together, actually claim?" — that inferred sentence, not a category name, is the Level-2 point.

**Quality gate before drafting prose.** Write the top three levels as sentences only, no labels. Any node that's a noun phrase instead of a claim isn't finished.

## Part 2: The Companion Deck

The deck is the same pyramid re-encoded for a different medium and pace — never a slide-by-slide restatement of the article's paragraphs.

**Step 1 — decide the deck's job before designing anything.** Speaker-led (you talk, slides support and stay light) or reading-first (sent async, must stand alone). This one decision determines correct text density more than any visual rule below — ask the user if it isn't obvious from context.

**Step 2 — map the pyramid onto slides.**
- Opening slide(s): compress SCQA's Complication/Question, not the governing thought — the audience hasn't earned the answer yet (exception: recommendation memos and exec summaries, where answer-first is correct on slide one too, same as in the write-up).
- One slide (or short contiguous run) per Level-2 argument. Never combine two arguments on one slide; never split one argument's evidence across non-adjacent slides.
- Level 3-4 evidence becomes the slide body: a native chart, one meaningful image, or a tight list — not paragraphs lifted from the article.
- Closing slide restates the governing thought, now earned, plus the ask or next step.

**Step 3 — visual rules, reassessed for 2026** (source: TED Blog, "10 Tips for Better Slide Decks," Aaron Weyenberg, ~2014):
- *Still fully valid*: build the argument before touching slide design; one consistent visual identity (type/color/imagery) with a deliberately distinct treatment for section/transition slides; disable video autoplay; recreate charts natively in the slide tool instead of pasting flat images (more true now, since native charts stay editable and accessible).
- *Valid but density-dependent*: "minimize text" is correct for speaker-led decks (1-3 bullets, one idea per slide) and wrong applied blindly to reading-first decks, which correctly carry more self-contained detail (roughly 4-8 bullets or a few structured cards per slide) — don't strip a reading deck down out of habit, and don't cram a speaker-led deck up out of laziness.
- *Still valid, mechanism modernized*: the original's manual "dupe-and-mask" image technique and manual vertical panning of oversized screenshots were 2014-era Keynote/PowerPoint workarounds. The underlying goal — draw the eye without shrinking text to illegibility — still holds; do it with whatever your build tool now does natively (crop/zoom/spotlight/annotate, or an interactive HTML deck that can pan and zoom itself) rather than the manual trick, unless the tool genuinely lacks a better option.
- *New failure mode the original list couldn't have named*: don't let generic AI-generated stock imagery substitute for "meaningful photographs." A generic AI photo that doesn't specifically reinforce the point fails the original's own test ("speaks strongly to the concept, isn't compositionally complex") exactly as badly as a bad stock photo did in 2014 — judge AI-generated images by the same test, don't exempt them from it.
- Effects and transitions: keep minimal and consistent — unchanged.

**Step 4 — build only after structure is settled.** Hand off to whichever output the user actually needs:
- Deliverable pptx: the Slides artifact type, or the pptx skill.
- The written piece: docx, or a Claude Docs document.
- Browser-based, animation-rich HTML deck: the community `frontend-slides` skill (github.com/zarazhangrui/frontend-slides, ~29k stars) — worth installing separately for the build mechanics (its density-mode split mirrors Step 1 above); it governs HTML/CSS execution, not the argument structure, which stays governed by this skill.
- Markdown-native deck (Marp): when the user wants a plain-text, git-diffable, dev-friendly deck, or explicitly asks for Marp — write the deck as Marp Markdown instead of pptx/HTML. See "Marp specifics" below. Marp exports the same source to PDF, PPTX, HTML or PNG via `marp-cli`, so a Marp source is also a fast path to a pptx deliverable when the user wants text-first authoring but a pptx at the end. This repo already has a working Marp pipeline at `scripts/marp/` (front matter conventions, a `Makefile` with `html`/`pdf`/`pptx` targets, and PlantUML-generated diagrams) — match its front-matter style (`theme`, `transition`, `size: "16:9"`, `paginate`, `header`) rather than inventing a new one.

### Marp specifics

Marp decks are plain Markdown with YAML front matter, so they carry the pyramid structure unusually transparently — each `---`-separated section IS one slide, so Step 2's "one slide per Level-2 argument" maps almost literally onto the file's own section breaks.

- **Front matter** starts every deck:
  ```
  ---
  marp: true
  theme: default
  paginate: true
  ---
  ```
  `theme` is `default`, `gaia`, `uncover`, or a custom CSS theme file — pick one and hold it for the whole deck; this is how Marp satisfies the "consistent visual identity" rule.
- **New slide** = a line containing only `---`.
- **Per-slide overrides** go in an HTML comment right after that slide's break, e.g. `<!-- backgroundColor: black -->` or `<!-- class: invert -->` for a section/transition slide with a genuinely different treatment — Marp's answer to Step 3's "distinct treatment for section slides," since it has no separate template system.
- **Meaningful images**: `![bg fit](path-or-url)` for a full-bleed image slide, `![w:400](path)` for inline — choose images by the same test as any other build target (reinforces the point, not compositionally complex, no generic AI-slop).
- **Known Marp limitations** — design around these rather than fighting them:
  - No click-by-click progressive bullet reveal and no native transitions/animation; Marp is a static exporter. If a speaker-led deck genuinely needs progressive disclosure, split that one slide into a short run of near-identical slides instead — still "one Level-2 argument, one slide-run" per Step 2.
  - No live/native charts — Marp doesn't execute JS. Render the chart to SVG/PNG first (the dataviz skill's palette/clarity rules still apply to that render) and embed it as an image, or use the `marp-cli` Mermaid integration for simple diagrams.
  - Speaker notes: an HTML comment on its own line at the end of a slide, e.g. `<!-- note: mention the Q3 number here -->`.
- **Export**: `marp deck.md --pdf` / `--pptx` / `--html` via `marp-cli` — or `make html` / `make pdf` / `make pptx` if building on this repo's existing `scripts/marp/Makefile` pattern.

## Consistency check (run before delivering either piece)

- Say the deck's arc from title slide to closing slide out loud: does it match the article's governing thought and Level-2 arguments, in the same order?
- Does any slide assert something the article doesn't support, or vice versa?
- Would someone who only saw the deck, and someone who only read the article, walk away with the same governing thought?

## References

Barbara Minto, *The Pyramid Principle: Logic in Writing and Thinking* — governing thought, vertical Q&A logic, MECE, SCQA.
TED Blog, "10 Tips for Better Slide Decks" (Aaron Weyenberg) — visual/tactical deck rules, reassessed above for 2026 practice.
Marp (marp.app / marpit + marp-cli) — Markdown-native deck authoring and export.
