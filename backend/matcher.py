"""
Relevance matching: scans a thread's full text for mentions of a task's
keyword, and returns just the specific sentence(s) that actually mention
it -- this is the whole point of InboxCopilot: surfacing the one buried
line instead of the whole thread.

This is deliberately simple keyword/substring matching for now, not a
limitation we're stuck with. Swapping the inside of find_relevant_sentences
for a call to an LLM ("does this sentence relate to <keyword>?") would
handle fuzzier phrasing -- synonyms, indirect references -- without
changing anything else in job.py that calls it. Keeping it regex-based for
now keeps the project fully free and dependency-light.
"""

import re
import math

# Filler words that shouldn't count when deciding relevance -- someone
# typing "study material related all info" means "study material", not
# literally those five words appearing together.
_STOPWORDS = {
    "a", "an", "the", "of", "to", "in", "on", "for", "and", "or", "any",
    "all", "info", "information", "related", "regarding", "about",
    "everything", "stuff", "my", "our", "is", "are", "with",
}


def split_into_sentences(text):
    # Collapse whitespace/newlines first so line breaks mid-sentence don't
    # confuse the splitter.
    normalized = re.sub(r"\s+", " ", text).strip()
    # Split after ./!/? when followed by a space + capital letter or digit --
    # a reasonable approximation without pulling in a full NLP library.
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", normalized)
    return [s.strip() for s in sentences if s.strip()]


def _significant_words(keyword):
    words = re.findall(r"[a-z0-9]+", keyword.lower())
    significant = [w for w in words if w not in _STOPWORDS and len(w) > 1]
    return significant or words  # fall back to everything if it's all stopwords


def _match_score(sentence_lower, significant_words):
    return sum(1 for w in significant_words if w in sentence_lower)


def find_relevant_sentences(full_text, keyword, context_sentences=1):
    """
    Returns a list of snippets: each is a sentence that mentions enough of
    the keyword's meaningful words, plus `context_sentences` of surrounding
    context. A sentence "matches" if it contains at least half (rounded up)
    of the keyword's significant words -- so "study material" matches a
    sentence containing either word, while a longer phrase like "the Q3
    review deck" still needs a couple of its real words present, not just
    one incidental match. Exact duplicate snippets (common in email threads
    thanks to quoted replies) are filtered out.
    """
    significant_words = _significant_words(keyword)
    if not significant_words:
        return []

    threshold = max(1, math.ceil(len(significant_words) / 2))

    sentences = split_into_sentences(full_text)
    matches = []
    seen = set()

    for i, sentence in enumerate(sentences):
        score = _match_score(sentence.lower(), significant_words)
        if score >= threshold:
            start = max(0, i - context_sentences)
            end = min(len(sentences), i + context_sentences + 1)
            snippet = " ".join(sentences[start:end])
            if snippet not in seen:
                seen.add(snippet)
                matches.append(snippet)

    return matches
