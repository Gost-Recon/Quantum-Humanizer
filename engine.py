
"""
AI Humanizer Suite - deterministic text humanization engine
Doctrine: no fake scores, no silent failures. Heuristic metrics are labeled as heuristics.
"""
import re, random, math

AI_MARKERS = [
    "delve", "delving", "tapestry", "in today's fast-paced world",
    "in the realm of", "it is important to note", "it's important to note",
    "moreover", "furthermore", "additionally", "in conclusion",
    "overall,", "crucial", "pivotal", "landscape", "navigate",
    "navigating", "foster", "fostering", "leverage", "leveraging",
    "robust", "seamless", "seamlessly", "holistic", "multifaceted",
    "underscore", "underscores", "embark", "journey", "testament to",
    "ever-evolving", "cutting-edge", "game-changer", "paradigm shift",
    "in essence", "ultimately", "notably", "significantly",
]

CONTRACTIONS = [
    ("do not", "don't"), ("does not", "doesn't"), ("did not", "didn't"),
    ("cannot", "can't"), ("can not", "can't"), ("will not", "won't"),
    ("would not", "wouldn't"), ("is not", "isn't"), ("are not", "aren't"),
    ("was not", "wasn't"), ("were not", "weren't"), ("has not", "hasn't"),
    ("have not", "haven't"), ("had not", "hadn't"), ("it is", "it's"),
    ("that is", "that's"), ("there is", "there's"), ("what is", "what's"),
    ("let us", "let's"), ("you are", "you're"), ("they are", "they're"),
    ("we are", "we're"), ("i am", "I'm"), ("you will", "you'll"),
    ("we will", "we'll"), ("they will", "they'll"), ("it will", "it'll"),
]

SIMPLE_SWAPS = [
    ("utilize", "use"), ("utilizes", "uses"), ("utilized", "used"),
    ("utilizing", "using"), ("utilization", "use"),
    ("facilitate", "help"), ("facilitates", "helps"), ("facilitated", "helped"),
    ("commence", "start"), ("commenced", "started"),
    ("terminate", "end"), ("subsequently", "then"),
    ("endeavor", "try"), ("endeavors", "tries"),
    ("ascertain", "find out"), ("demonstrate", "show"),
    ("demonstrates", "shows"), ("demonstrated", "showed"),
    ("numerous", "many"), ("individuals", "people"),
    ("pertaining to", "about"), ("in order to", "to"),
    ("due to the fact that", "because"), ("a plethora of", "many"),
    ("a multitude of", "many"), ("in the event that", "if"),
    ("prior to", "before"), ("subsequent to", "after"),
    ("with regard to", "about"), ("in terms of", "for"),
    ("it is worth noting that", "worth noting:"),
    ("plays a pivotal role in", "is central to"), ("plays a crucial role in", "is central to"),
    ("serves as", "acts as"), ("a wide range of", "many"),
    ("has become", "is now"), ("the significance of", "how much ... matters"[:0] + "the value of"),
    ("in the ever-evolving", "in the changing"), ("ever-evolving", "changing"),
    ("pivotal", "key"), ("crucial", "key"), ("robust", "solid"),
    ("multifaceted", "layered"), ("landscape", "field"), ("seamlessly", "smoothly"),
    ("holistic", "well-rounded"), ("notably", ""), ("significantly", "markedly"),
    ("underscore", "highlight"), ("underscores", "highlights"),
    ("foster", "build"), ("fostering", "building"), ("fosters", "builds"),
    ("leverage", "use"), ("leveraging", "using"), ("navigating", "handling"),
    ("navigate", "handle"), ("embark on", "start"), ("journey", "path"),
    ("testament to", "proof of"), ("cutting-edge", "advanced"),
    ("game-changer", "big change"), ("paradigm shift", "major shift"),
    ("in essence", "at its core"), ("ultimately", "in the end"),
    ("comprehensive", "complete"), ("enhance", "improve"), ("enhances", "improves"),
    ("enhanced", "improved"), ("utilize", "use"), ("moreover", ""),
    ("furthermore", ""), ("additionally", ""), ("in conclusion", "to wrap up"),
    ("overall,", ""), ("in the realm of", "in"), ("realm of", "world of"),
]

HEDGES = ["honestly", "frankly", "pretty much", "at least", "in my experience",
          "if I'm being honest", "more or less", "to be fair", "basically"]

OPENERS = ["Look,", "Here's the thing:", "That said,", "Still,", "Now,",
           "Truth is,", "In practice,", "Either way,", "Oddly enough,"]

def _sentence_split(text):
    parts = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in parts if s.strip()]

def _find_ai_markers(text):
    low = text.lower()
    found = {}
    for m in AI_MARKERS:
        n = low.count(m)
        if n: found[m] = n
    return found

def _strip_markers(text):
    for m in AI_MARKERS:
        # remove stock connector phrases entirely; soften single words later
        if m in ("moreover", "furthermore", "additionally",
                 "it is important to note", "it's important to note"):
            # remove the phrase plus a dangling connective ("that") and any comma
            text = re.sub(re.escape(m) + r'( that)?[, ]*', '', text, flags=re.I)
    return text.strip()

def _apply_contractions(text, rng, strength):
    out = text
    for a, b in CONTRACTIONS:
        if rng.random() < strength:
            out = re.sub(r'\b' + re.escape(a) + r'\b', b, out, flags=re.I)
    return out

def _apply_swaps(text, rng, strength):
    out = text
    for a, b in SIMPLE_SWAPS:
        if rng.random() < strength:
            out = re.sub(r'\b' + re.escape(a) + r'\b', b, out, flags=re.I)
    return out

def _restructure_sentences(sents, rng, strength):
    """Split long sentences, merge adjacent short ones - inject burstiness."""
    out = []
    i = 0
    while i < len(sents):
        s = sents[i]
        words = s.split()
        if len(words) > 34 and rng.random() < strength and ',' in s:
            idx = max((s.rindex(',') for _ in [0] if ',' in s), default=-1)
            # split at the comma nearest the middle
            commas = [m.start() for m in re.finditer(',', s)]
            if commas:
                mid = min(commas, key=lambda c: abs(c - len(s)//2))
                a, b = s[:mid].rstrip(', ') .strip(), s[mid+1:].strip()
                if a and b and len(a.split()) > 4 and len(b.split()) > 4:
                    b = b[0].upper() + b[1:]
                    end = '' if not b.endswith(('.','!','?')) else b[-1]
                    if end: b = b[:-1]
                    out.append(a if a.endswith(('.','!','?')) else a + '.')
                    out.append((b + ('.' if not end else end)) if end != '' else b)
                    i += 1
                    continue
        # merge two short consecutive sentences sometimes
        if (i + 1 < len(sents) and len(words) < 9 and rng.random() < strength * 0.7):
            nxt = sents[i+1]
            joined = s.rstrip('.!?') + ', and ' + nxt[0].lower() + nxt[1:]
            out.append(joined)
            i += 2
            continue
        out.append(s)
        i += 1
    return out

def _casualize(text, rng, strength):
    out = text
    if rng.random() < strength * 0.6:
        out = out.replace(' — ', ', ').replace(' - ', ', ')
    # occasional sentence-initial casual opener
    sents = _sentence_split(out)
    if len(sents) >= 2 and rng.random() < strength * 0.35:
        k = rng.randrange(len(sents))
        if sents[k][0].isupper() and len(sents[k]) > 30 and k > 0:
            op = rng.choice(OPENERS)
            sents[k] = op + ' ' + sents[k][0].lower() + sents[k][1:]
    out = ' '.join(sents)
    return out

def _vary_rhythm(text, rng):
    """Minor: occasionally drop final 'that' after think/believe etc, fix spacing."""
    text = re.sub(r'\s+([,.;:!?])', r'\1', text)
    text = re.sub(r'([.!?])([A-Z])', r'\1 \2', text)
    return text

def _recapitalize(text):
    sents = _sentence_split(text)
    fixed = []
    for s in sents:
        if s and s[0].islower():
            s = s[0].upper() + s[1:]
        fixed.append(s)
    return ' '.join(fixed)

def humanize(text, seed=None, strength=0.8):
    rng = random.Random(seed)
    orig_len = len(text)
    text = _strip_markers(text)
    text = _recapitalize(text)
    text = _apply_swaps(text, rng, strength)
    text = _apply_contractions(text, rng, strength)
    sents = _sentence_split(text)
    sents = _restructure_sentences(sents, rng, strength)
    text = ' '.join(sents)
    text = _casualize(text, rng, strength)
    text = _vary_rhythm(text, rng)
    metrics = analyze(text)
    return {"text": text.strip(), "original_length": orig_len,
            "markers_removed": _find_ai_markers, "metrics": metrics}

def analyze(text):
    """Heuristic 'AI-likeness' score 0-100. Clearly labeled heuristic - NOT a detector verdict."""
    sents = _sentence_split(text)
    if not sents: return {"ai_likeness": 0, "sentences": 0, "avg_len": 0,
                          "len_variance": 0, "markers": {}}
    lens = [len(s.split()) for s in sents]
    avg = sum(lens)/len(lens)
    var = sum((l-avg)**2 for l in lens)/len(lens)  # burstiness proxy
    markers = _find_ai_markers(text)
    score = 0.0
    score += min(30, 30 * (avg > 24 and 1 or max(0, (avg-14)/16)))
    score += max(0, 30 - min(30, var))           # low sentence-length variance = AI-like
    score += min(30, 6 * len(markers))
    contr = sum(text.count(b) for _, b in CONTRACTIONS)
    score += max(0, 10 - contr)                  # few contractions = AI-like
    return {"ai_likeness": round(min(100, score), 1), "sentences": len(sents),
            "avg_len": round(avg, 1), "len_variance": round(var, 1),
            "markers": markers}
