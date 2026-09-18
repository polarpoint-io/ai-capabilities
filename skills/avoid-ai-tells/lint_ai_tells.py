#!/usr/bin/env python3
"""
lint_ai_tells.py — scan a piece of writing for mechanically-detectable
signs of AI writing, drawn from Wikipedia's "Signs of AI writing" essay.

Usage:
    python3 lint_ai_tells.py <file>
    cat draft.md | python3 lint_ai_tells.py

Exits 0 always (this is advisory, not a hard gate) but prints a report
and a summary "tell density" score to help decide whether a rewrite
pass is warranted.
"""

import re
import sys
from collections import defaultdict

# ── Phrase lists (sourced from the Wikipedia essay's "Words to watch" boxes) ──

AI_VOCAB_WORDS = [
    "additionally", "align with", "boasts", "bolstered", "crucial", "delve", "delves", "delving",
    "emphasizing", "enduring", "enhance", "enhances", "enhancing", "fostering", "fosters",
    "garner", "garnered", "garners", "highlight", "highlights", "highlighting", "interplay",
    "intricate", "intricacies", "meticulous", "meticulously", "pivotal", "robust", "showcase",
    "showcases", "showcasing", "tapestry", "testament", "underscore", "underscores",
    "underscoring", "vibrant",
]

IMPORTANCE_INFLATION_PHRASES = [
    "stands as a testament", "serves as a testament", "is a testament to", "is a reminder of",
    "plays a vital role", "plays a significant role", "plays a crucial role", "plays a pivotal role",
    "underscores its importance", "underscores its significance", "highlights its importance",
    "highlights its significance", "reflects broader", "symbolizing its ongoing",
    "symbolizing its enduring", "symbolizing its lasting", "setting the stage for",
    "marking a shift", "represents a shift", "key turning point", "evolving landscape",
    "focal point", "indelible mark", "deeply rooted",
]

NOTABILITY_PHRASES = [
    "independent coverage", "regional media outlets", "national media outlets",
    "trade publications", "profiled in", "written by a leading expert",
    "active social media presence",
]

PROMOTIONAL_PHRASES = [
    "boasts a", "natural beauty", "nestled in", "in the heart of", "groundbreaking",
    "renowned", "diverse array", "commitment to excellence",
]

WEASEL_PHRASES = [
    "industry reports", "observers have cited", "experts argue", "some critics argue",
    "several sources", "several publications",
]

CHALLENGES_TEMPLATE_PHRASES = [
    "despite its", "despite these challenges", "faces several challenges",
]

COPULATIVE_AVOIDANCE_PHRASES = [
    "serves as a", "serves as an", "stands as a", "stands as an", "represents a",
    "represents an", "boasts a", "boasts an", "features a", "features an",
    "maintains a", "maintains an", "offers a", "offers an",
]

COLLABORATIVE_LEFTOVER_PHRASES = [
    "i hope this helps", "of course!", "certainly!", "you're absolutely right",
    "would you like me to", "is there anything else", "let me know if you",
    "here is a more detailed", "more detailed breakdown",
]

KNOWLEDGE_CUTOFF_PHRASES = [
    "as of my last training update", "as of my last knowledge update",
    "up to my last training update", "while specific details are limited",
    "while specific details are scarce", "not widely documented",
    "not widely available", "not widely disclosed", "based on available information",
]

EDITORIALIZING_PHRASES = [
    "it's important to note", "it is important to note", "it's crucial to note",
    "it's important to remember", "worth noting that",
    "no discussion would be complete without",
]

SECTION_SUMMARY_PHRASES = [
    "in summary,", "in conclusion,", "overall,",
]

NEGATIVE_PARALLELISM_PATTERNS = [
    (r"\bnot only\b.{0,60}\bbut\b", "not only X, but Y"),
    (r"\bit'?s not (just |only )?.{0,40}\bit'?s\b", "it's not X, it's Y"),
    (r"\bnot .{0,40},? but .{0,40}", "not X, but Y"),
    (r"\bno\b.{0,30},\s*no\b.{0,30}(—|-|,)\s*just\b", "no X, no Y — just Z"),
]

# Bracketed placeholder text left unedited — a strong tell that AI output was
# pasted in without review (e.g. "[Your Name]", "[Company Name]", "[Insert X]")
PLACEHOLDER_PATTERN = r"\[\s*(your|company|insert|client|customer)\b[^\]]{0,30}\]"

RULE_OF_THREE_PATTERN = r"\b(\w+),\s+(\w+),?\s+and\s+(\w+)\b"

CATEGORY_LABELS = {
    "ai_vocab": "High-density AI vocabulary",
    "importance": "Importance/legacy inflation",
    "notability": "Canned notability/attribution claims",
    "promotional": "Promotional / travel-brochure language",
    "weasel": "Vague attributions (weasel words)",
    "challenges": "Formulaic 'Challenges' section template",
    "copulative": "Avoidance of plain is/are",
    "collaborative": "Leftover chatbot correspondence",
    "cutoff": "Knowledge-cutoff disclaimers",
    "editorializing": "Editorializing insertions",
    "summary": "Mechanical section summaries",
    "negative_parallelism": "Negative-parallelism constructions",
    "placeholder": "Unedited placeholder text (e.g. [Your Name])",
    "rule_of_three": "Rule-of-three triads",
    "em_dash": "Em dash usage",
    "curly_quotes": "Curly quotation marks/apostrophes",
    "title_case": "Title-case headings",
    "bold": "Boldface density",
}


def find_phrase_matches(text_lines, phrases):
    """Match whole words/phrases with word boundaries so 'showcase' doesn't
    also fire inside 'showcases', double-counting the same instance."""
    hits = []
    compiled = [(p, re.compile(r"\b" + re.escape(p) + r"\b", re.IGNORECASE)) for p in phrases]
    for lineno, line in enumerate(text_lines, 1):
        matched_spans = []
        for phrase, pattern in compiled:
            for m in pattern.finditer(line):
                # skip if this span is already covered by a longer phrase match on this line
                if any(s <= m.start() and m.end() <= e for s, e in matched_spans):
                    continue
                matched_spans.append((m.start(), m.end()))
                hits.append((lineno, phrase, line.strip()))
    return hits


def find_regex_matches(text_lines, patterns):
    hits = []
    for lineno, line in enumerate(text_lines, 1):
        for pattern, label in patterns:
            for m in re.finditer(pattern, line, re.IGNORECASE):
                hits.append((lineno, label, m.group(0)))
    return hits


def find_title_case_headings(text_lines):
    hits = []
    small_words = {"a", "an", "the", "of", "in", "on", "and", "or", "to", "for", "with", "at", "by"}
    for lineno, line in enumerate(text_lines, 1):
        m = re.match(r"^#{1,6}\s+(.*)", line)
        if not m:
            continue
        heading = m.group(1).strip()
        words = [w for w in re.findall(r"[A-Za-z']+", heading) if w]
        if len(words) < 3:
            continue
        capitalized = [w for w in words if w[0].isupper() and w.lower() not in small_words]
        eligible = [w for w in words if w.lower() not in small_words]
        if eligible and len(capitalized) / len(eligible) >= 0.8:
            hits.append((lineno, "title-case heading", heading))
    return hits


def analyze(text):
    lines = text.splitlines()
    word_count = max(len(re.findall(r"\w+", text)), 1)
    report = defaultdict(list)

    report["ai_vocab"] = find_phrase_matches(lines, [w for w in AI_VOCAB_WORDS])
    report["importance"] = find_phrase_matches(lines, IMPORTANCE_INFLATION_PHRASES)
    report["notability"] = find_phrase_matches(lines, NOTABILITY_PHRASES)
    report["promotional"] = find_phrase_matches(lines, PROMOTIONAL_PHRASES)
    report["weasel"] = find_phrase_matches(lines, WEASEL_PHRASES)
    report["challenges"] = find_phrase_matches(lines, CHALLENGES_TEMPLATE_PHRASES)
    report["copulative"] = find_phrase_matches(lines, COPULATIVE_AVOIDANCE_PHRASES)
    report["collaborative"] = find_phrase_matches(lines, COLLABORATIVE_LEFTOVER_PHRASES)
    report["cutoff"] = find_phrase_matches(lines, KNOWLEDGE_CUTOFF_PHRASES)
    report["editorializing"] = find_phrase_matches(lines, EDITORIALIZING_PHRASES)
    report["summary"] = find_phrase_matches(lines, SECTION_SUMMARY_PHRASES)
    report["negative_parallelism"] = find_regex_matches(lines, NEGATIVE_PARALLELISM_PATTERNS)
    report["placeholder"] = find_regex_matches(lines, [(PLACEHOLDER_PATTERN, "unedited placeholder")])
    report["rule_of_three"] = find_regex_matches(
        lines, [(RULE_OF_THREE_PATTERN, "word, word, and word")]
    )
    report["title_case"] = find_title_case_headings(lines)

    em_dash_count = text.count("—")
    report["em_dash"] = [(0, "—", f"{em_dash_count} occurrence(s), "
                           f"{em_dash_count / word_count * 1000:.1f} per 1000 words")] if em_dash_count else []

    curly_count = len(re.findall(r"[“”‘’]", text))
    report["curly_quotes"] = [(0, "curly quote", f"{curly_count} occurrence(s)")] if curly_count else []

    bold_count = len(re.findall(r"\*\*[^*]+\*\*", text))
    if bold_count:
        density = bold_count / word_count * 1000
        report["bold"] = [(0, "**bold**", f"{bold_count} occurrence(s), {density:.1f} per 1000 words")]
    else:
        report["bold"] = []

    return report, word_count


def print_report(report, word_count):
    total_hits = 0
    print(f"AI-tell lint report ({word_count} words)\n" + "=" * 40)
    for key, label in CATEGORY_LABELS.items():
        hits = report.get(key, [])
        if not hits:
            continue
        total_hits += len(hits)
        print(f"\n[{label}] — {len(hits)} match(es)")
        for lineno, phrase, context in hits[:8]:
            loc = f"line {lineno}" if lineno else "doc-level"
            snippet = context if len(context) <= 100 else context[:97] + "..."
            print(f"  - {loc}: \"{phrase}\"  {('— ' + snippet) if lineno else ('(' + snippet + ')')}")
        if len(hits) > 8:
            print(f"  ... and {len(hits) - 8} more")

    print("\n" + "=" * 40)
    density = total_hits / word_count * 1000
    print(f"Total flags: {total_hits}  ({density:.1f} per 1000 words)")
    if total_hits == 0:
        print("No mechanical AI tells detected. Still worth a manual read for content-level tells")
        print("(hollow significance claims, vague attributions, superficial analysis) — the linter")
        print("can't judge those.")
    elif density < 3:
        print("Low density — likely fine, but skim the flagged lines above.")
    elif density < 8:
        print("Moderate density — worth a revision pass on the flagged categories.")
    else:
        print("High density — this reads as AI-generated. Rewrite the flagged passages before delivering.")
    return total_hits, density


def main():
    if len(sys.argv) > 1:
        with open(sys.argv[1], "r", encoding="utf-8") as f:
            text = f.read()
    else:
        text = sys.stdin.read()

    report, word_count = analyze(text)
    print_report(report, word_count)


if __name__ == "__main__":
    main()
