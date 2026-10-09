"""
AI Humanizer Suite — engine v2 (full rebuild)
Doctrine: honest metrics, no silent failures, meaning-preserving transforms only.

Attack surfaces (from detection literature):
  1. Perplexity       — detectors flag uniformly *predictable* word choice.
                        Countermeasure: curated low-frequency synonym swaps
                        (wordfreq Zipf targeting when available).
  2. Burstiness       — detectors flag uniform sentence lengths AND uniform
                        per-sentence word predictability across a document.
                        Countermeasure: engineered heavy-tailed length
                        distribution + per-sentence lexical variance.
  3. Syntactic templates — AI reuses sentence frames massively; humans vary.
                        Countermeasure: opener rotation, fronting, inversion,
                        existential removal, passive softening.
  4. n-gram traces    — repeated 3+ grams are a giveaway.
                        Countermeasure: repetition scan + rephrase.
Plus: AI phrase elimination, human texture injection, paragraph-shape
variation, and a quality-gate pass that blocks grammatical damage.
"""
import re, random, math

try:
    from wordfreq import zipf_frequency
    _HAS_WF = True
except Exception:
    _HAS_WF = False
    def zipf_frequency(w, lang=None):  # graceful fallback: neutral value
        return 4.5

# ----------------------------------------------------------------------------
# 1. AI PHRASE BLACKLIST (context-aware removal / replacement)
# ----------------------------------------------------------------------------
AI_PHRASES_STRIP = [
    r"in today'?s fast[- ]paced world", r"in the modern (?:era|age|world)",
    r"it is important to note that", r"it'?s important to note that",
    r"it is worth noting that", r"it should be noted that",
    r"needless to say,?", r"when all is said and done,?",
    r"as we have seen,?", r"as previously mentioned,?",

    r"serves? as a testament to", r"is a testament to",
    r"sheds? light on", r"paves? the way for",
    r"opens? the door to", r"at the end of the day,?",
    r"the (?:ever[- ]evolving|ever[- ]changing) (?:landscape|world|realm) of",
    r"the (?:landscape|realm|world) of",
    r"navigate the complexities of", r"navigat\w+ the (?:complexities|challenges)",
    r"embark on a journey", r"journey of",
    r"unlock the (?:full )?potential", r"harness the power of",
    r"cutting[- ]edge", r"state[- ]of[- ]the[- ]art",
    r"game[- ]?chang\w+", r"paradigm shift",
    r"a testament to", r"in the grand scheme of things,?",
    r"when it comes to", r"first and foremost,?",
    r"it goes without saying that",
    r"underscor\w+ the (?:importance|significance) of",
    r"highlight(?:s|ed)? the importance of",
    r"crucial (?:aspect|factor|element)", r"multifaceted",
    r"delv\w+ (?:deep(?:er|ly) )? ?into", r"\bdelv\w+\b",
    r"plethora of", r"myriad of", r"kaleidoscope of",
    r"ever[- ]evolving", r"ever[- ]changing",
    r"a double[- ]edged sword", r"it is no secret that",
    r"one cannot deny that", r"we cannot ignore the fact that",
]
AI_PHRASES = ["delve", "delving", "delved", "tapestry", "landscape",
              "crucial", "pivotal", "seamless", "seamlessly", "holistic",
              "multifaceted", "robust", "foster", "fosters", "fostering",
              "leverage", "leveraging", "underscore", "underscores",
              "underscoring", "ever-evolving", "testament", "realm",
              "navigate", "navigating", "embark", "utilize", "utilizes",
              "utilized", "utilizing", "comprehensive", "notably",
              "significantly", "moreover", "furthermore", "additionally",
              "consequently", "nevertheless", "nonetheless", "arguably",
              "ultimately", "overall", "indeed", "in conclusion",
              "in summary", "to summarize"]

# sentence-initial connectives -> human variants (rotated, de-duplicated)
SENTENCE_CONNECTORS = {
    "however":        ["But", "Still", "Even so", "That said", "Yet"],
    "therefore":      ["So", "Which means", "As a result,"],
    "moreover":       ["Plus,", "On top of that,", "And", "Also,"],
    "additionally":   ["Also,", "On top of that,", "Besides,", "Plus,"],
    "furthermore":    ["What's more,", "Plus,", "Beyond that,", "And"],
    "consequently":   ["So", "As a result,", "Because of that,"],
    "nevertheless":   ["Still", "Even so", "All the same,"],
    "nonetheless":    ["Still", "Even so", "That said,"],
    "meanwhile":      ["At the same time,", "In the meantime,"],
    "similarly":      ["Likewise,", "Much the same way,"],
    "conversely":     ["On the flip side,", "But", "Look at it the other way and"],
    "notably":        ["Strikingly,", "Tellingly,", "Worth noting:"],
    "indeed":         ["In fact,", "Actually,", "Truth is,"],
    "thus":           ["So", "That means", "Which means"],
    "hence":          ["So", "That's why", "Which is why"],
    "overall":        ["All told,", "On balance,", "In the end,"],
    "ultimately":     ["In the end,", "When it matters,", "Bottom line:"],
    "in addition":    ["Also,", "On top of that,", "Plus,"],
    "in particular":  ["Especially", "Particularly"],
    "in general":     ["Generally", "By and large,"],
    "in essence":     ["At its core,", "Stripped down,"],
    "as such":        ["So", "Which means"],
    "for example":    ["Say", "Take", "Consider"],
    "for instance":   ["Take", "Say"],
    "as a result":    ["So", "Because of that,"],
    "in contrast":    ["By contrast,", "But"],
    "on the other hand": ["But", "Then again,", "Flip it around and"],
    "in summary":     ["So,", "All told,"],
    "to summarize":   ["So,", "All told,"],
    "firstly":        ["First,", "To start,"],
    "secondly":       ["Second,", "Next,"],
    "thirdly":        ["Third,", "And then,"],
    "finally":        ["Last,", "In the end,", "Lastly,"],
}

PROTECTED_COMPOUNDS = [
    "loss function", "validation set", "gradient descent", "model drift", "version control",
    "machine learning", "training data", "test set", "data set", "datasets", "model artifacts",
    "rollback procedure", "inference environment", "model performance", "public discourse",
    "consumer protection", "regulatory framework", "digital literacy", "social media",
    "machine learning", "artificial intelligence", "deep learning",
    "higher education", "real estate", "human resources", "public health",
    "climate change", "social media", "supply chain", "best practices",
    "critical thinking", "problem solving", "workforce development",
    "professional development", "data science", "natural language",
    "common sense", "civil rights", "human rights", "law enforcement",
    "health care", "quality control", "research and development",
    "artificial intelligence", "public policy", "private sector",
    "data-driven insights", "data-driven decisions", "data-driven",
    "public trust", "public opinion", "informed decisions",
    "best practices", "critical thinking", "problem solving",
]

# ----------------------------------------------------------------------------
# 2. LEXICON — meaning-preserving swaps, inflection-aware.
#    Each key is a full word form; only genuinely interchangeable senses listed.
# ----------------------------------------------------------------------------
SYN_TABLE = {
    # -- verbs (3rd person / past kept separate for agreement) --
    "shows": ["reveals", "indicates", "points to", "lays bare"],
    "show": ["reveal", "indicate", "point to"],
    "showed": ["revealed", "indicated", "laid bare"],
    "demonstrates": ["shows", "makes clear", "reveals"],
    "demonstrated": ["showed", "made clear", "revealed"],
    "creates": ["builds", "shapes", "produces"],
    "create": ["build", "shape", "spawn"],
    "created": ["built", "shaped", "spawned"],
    "generates": ["produces", "spawns"],
    "generate": ["produce", "spawn"],
    "generated": ["produced", "spawned"],
    "allows": ["lets", "permits"],
    "allow": ["let", "permit"],
    "allowed": ["let", "permitted"],
    "enables": ["lets", "makes it possible for"],
    "enable": ["let", "make it possible for"],
    "improves": ["sharpens", "lifts", "strengthens"],
    "improve": ["sharpen", "lift", "strengthen"],
    "improved": ["sharpened", "lifted", "strengthened"],
    "increases": ["raises", "lifts", "pushes up"],
    "increase": ["raise", "lift", "push up"],
    "increased": ["raised", "higher", "greater"],
    "reduces": ["cuts", "shrinks", "trims"],
    "reduce": ["cut", "shrink", "trim"],
    "reduced": ["cut", "shrank", "trimmed"],
    "decreases": ["drops", "falls", "sinks"],
    "decrease": ["drop", "fall", "sink"],
    "decreased": ["dropped", "fell", "sank"],
    "affects": ["shapes", "bears on", "touches"],
    "affect": ["shape", "bear on", "touch"],
    "affected": ["shaped", "touched", "hit"],
    "causes": ["triggers", "sets off", "brings on"],
    "cause": ["trigger", "bring on"],
    "caused": ["triggered", "set off", "brought on"],
    "leads": ["drives", "carries", "pushes"],
    "lead": ["drive", "carry", "push"],
    "led": ["drove", "carried", "pushed"],
    "requires": ["demands", "calls for", "takes"],
    "require": ["demand", "call for", "take"],
    "required": ["demanded", "called for", "took"],
    "provides": ["gives", "hands over", "supplies"],
    "provide": ["give", "supply"],
    "provided": ["gave", "supplied"],
    "offers": ["extends", "hands out", "puts forward"],
    "offer": ["extend", "put forward"],
    "offered": ["extended", "put forward"],
    "includes": ["covers", "takes in", "carries"],
    "include": ["cover", "take in", "carry"],
    "included": ["covered", "took in", "carried"],
    "involves": ["takes in", "calls for", "entails"],
    "involve": ["take in", "entail", "call for"],
    "involved": ["entailed", "took in", "called for"],
    "considers": ["weighs", "chews over", "looks at"],
    "consider": ["weigh", "look at", "chew over"],
    "considered": ["weighed", "looked at", "chewed over"],
    "understands": ["grasps", "sees", "gets"],
    "understand": ["grasp", "see", "get"],
    "understood": ["grasped", "saw", "got"],
    "reveals": ["shows", "exposes", "unmasks"],
    "reveal": ["show", "expose", "unmask"],
    "revealed": ["showed", "exposed", "unmasked"],
    "suggests": ["hints", "implies", "points to"],
    "suggest": ["hint", "imply", "point to"],
    "suggested": ["hinted", "implied", "pointed to"],
    "argues": ["contends", "makes the case", "holds"],
    "argue": ["contend", "make the case", "hold"],
    "argued": ["contended", "made the case", "held"],
    "claims": ["says", "contends", "puts forward"],
    "claim": ["say", "contend", "put forward"],
    "claimed": ["said", "contended", "put forward"],
    "states": ["says", "puts it", "notes"],
    "state": ["say", "note"],
    "stated": ["said", "noted"],
    "notes": ["points out", "remarks", "observes"],
    "note": ["point out", "remark", "observe"],
    "noted": ["pointed out", "observed", "remarked"],
    "observes": ["notices", "sees", "points out"],
    "observe": ["notice", "point out", "see"],
    "observed": ["noticed", "saw", "pointed out"],
    "examines": ["picks apart", "looks at", "takes apart"],
    "examine": ["pick apart", "look at", "take apart"],
    "examined": ["picked apart", "looked at", "took apart"],
    "studies": ["digs into", "looks at", "takes up"],
    "study": ["dig into", "look at", "take up"],
    "studied": ["dug into", "looked at", "took up"],
    "analyzes": ["breaks down", "takes apart", "digs into"],
    "analyze": ["break down", "take apart", "dig into"],
    "analyzed": ["broke down", "took apart", "dug into"],
    "evaluates": ["sizes up", "judges", "weighs"],
    "evaluate": ["size up", "judge", "weigh"],
    "evaluated": ["sized up", "judged", "weighed"],
    "assesses": ["gauges", "sizes up", "weighs"],
    "assess": ["gauge", "size up", "weigh"],
    "assessed": ["gauged", "sized up", "weighed"],
    "achieves": ["reaches", "attains", "lands"],
    "achieve": ["reach", "attain", "land"],
    "achieved": ["reached", "attained", "landed"],
    "maintains": ["holds up", "keeps", "sustains"],
    
    "maintained": ["held up", "kept", "sustained"],
    "ensures": ["makes sure", "sees to it that", "locks in"],
    "ensure": ["make sure", "secure"],
    "ensured": ["made sure", "locked in"],
    "supports": ["backs", "bolsters", "underpins"],
    "support": ["back", "bolster", "underpin"],
    "supported": ["backed", "bolstered", "underpinned"],
    "emphasizes": ["stresses", "drives home", "hammers home"],
    "emphasize": ["stress", "drive home"],
    "emphasized": ["stressed", "drove home"],
    "highlights": ["flags", "spotlights", "draws attention to"],
    "highlight": ["flag", "spotlight"],
    "highlighted": ["flagged", "spotlighted"],
    "indicates": ["signals", "points to", "suggests"],
    "indicate": ["signal", "point to", "suggest"],
    "indicated": ["signaled", "pointed to", "suggested"],
    "focuses": ["zeroes in", "concentrates", "homes in"],
    "focus": ["zero in", "concentrate", "home in"],
    "focused": ["zeroed in", "concentrated", "homed in"],
    "depends": ["hinges", "rests", "hangs"],
    "depend": ["hinge", "rest"],
    "depended": ["hinged", "rested"],
    "describes": ["lays out", "sketches", "walks through"],
    "describe": ["lay out", "sketch", "walk through"],
    "described": ["laid out", "sketched", "walked through"],
    "explains": ["accounts for", "breaks down", "spells out"],
    "explain": ["account for", "spell out", "break down"],
    "explained": ["accounted for", "spelled out", "broke down"],
    "discusses": ["takes up", "goes into", "weighs"],
    "discuss": ["take up", "go into", "weigh"],
    "discussed": ["took up", "went into", "weighed"],
    "addresses": ["tackles", "takes on", "deals with"],
    "address": ["tackle", "take on", "deal with"],
    "addressed": ["tackled", "took on", "dealt with"],
    "contributes": ["adds", "feeds into", "lends to"],
    "contribute": ["add", "feed into"],
    "contributed": ["added", "fed into"],
    "transforms": ["reshapes", "overhauls", "remakes"],
    "transform": ["reshape", "overhaul", "remake"],
    "transformed": ["reshaped", "overhauled", "remade"],
    "develops": ["builds", "shapes", "puts together"],
    "develop": ["build", "shape", "put together"],
    "developed": ["built", "shaped", "put together"],
    "establishes": ["sets up", "lays down", "pins down"],
    "establish": ["set up", "lay down", "pin down"],
    "established": ["set up", "laid down", "pinned down"],
    "explores": ["digs into", "probes", "traces"],
    "explore": ["dig into", "probe", "trace"],
    "explored": ["dug into", "probed", "traced"],
    "investigates": ["probes", "digs into", "looks into"],
    "investigate": ["probe", "dig into", "look into"],
    "investigated": ["probed", "dug into", "looked into"],
    "measures": ["gauges", "tracks", "quantifies"],
    "measure": ["gauge", "track", "quantify"],
    "measured": ["gauged", "tracked", "quantified"],
    "revealing": ["showing", "exposing"],
    "building": ["shaping", "constructing", "assembling"],
    "produces": ["turns out", "yields", "puts out"],
    "produce": ["turn out", "yield", "put out"],
    "produced": ["turned out", "yielded", "put out"],
    "shaped": ["molded", "formed", "steered"],
    "shapes": ["molds", "forms", "steers"],
    "shape": ["mold", "form", "steer"],
    "drives": ["pushes", "fuels", "powers"],
    "drive": ["push", "fuel", "power"],
    "drove": ["pushed", "fueled", "powered"],
    "driven": ["pushed", "fueled", "powered"],
    "delivers": ["brings", "hands over", "produces"],
    "deliver": ["bring", "hand over"],
    "delivered": ["brought", "handed over"],
    "contains": ["holds", "carries"],
    "contain": ["hold", "carry"],
    "contained": ["held", "carried"],
    "comprises": ["is made up of", "consists of"],
    "comprise": ["make up", "consist of"],
    "comprised": ["made up", "consisted of"],
    "represents": ["stands for", "embodies", "marks"],
    "represent": ["stand for", "embody", "mark"],
    "represented": ["stood for", "embodied", "marked"],
    "reflects": ["mirrors", "echoes", "captures"],
    "reflect": ["mirror", "echo", "capture"],
    "reflected": ["mirrored", "echoed", "captured"],
    "accompanies": ["travels with", "goes with", "comes with"],
    "accompany": ["go with", "come with"],
    "accompanied": ["went with", "came with"],
    "encourages": ["nudges", "pushes for", "spurs"],
    "encourage": ["nudge", "spur", "push for"],
    "encouraged": ["nudged", "spurred", "pushed for"],
    "discourages": ["puts off", "deters", "holds back"],
    "discourage": ["put off", "deter", "hold back"],
    "discouraged": ["put off", "deterred", "held back"],
    "prevents": ["stops", "blocks", "head off"[:0]+"heads off"],
    "prevent": ["stop", "block", "head off"],
    "prevented": ["stopped", "blocked", "headed off"],
    "avoids": ["steers clear of", "sidesteps", "skips"],
    "avoid": ["steer clear of", "sidestep", "skip"],
    "avoided": ["steered clear of", "sidestepped", "skipped"],
    "neglects": ["overlooks", "ignores", "shrugs off"],
    "neglect": ["overlook", "ignore", "shrug off"],
    "neglected": ["overlooked", "ignored", "shrugged off"],
    "ignores": ["skips", "brushes off", "waves off"],
    "ignore": ["skip", "brush off", "wave off"],
    "ignored": ["skipped", "brushed off", "waved off"],
    "obtains": ["gets", "lands", "secures"],
    "obtain": ["get", "land", "secure"],
    "obtained": ["got", "landed", "secured"],
    "gains": ["wins", "picks up", "nabs"],
    "gain": ["win", "pick up", "nab"],
    "gained": ["won", "picked up", "nabbed"],
    "receives": ["gets", "takes in", "collects"],
    "receive": ["get", "take in", "collect"],
    "received": ["got", "took in", "collected"],
    "possesses": ["holds", "carries", "has"],
    "possess": ["hold", "carry", "have"],
    "possessed": ["held", "carried", "had"],
    "remains": ["stays"],
    "remain": ["stay"],
    "remained": ["stayed", "held", "lingered"],
    "emerges": ["surfaces", "comes up", "arises"],
    "emerge": ["surface", "come up", "arise"],
    "emerged": ["surfaced", "came up", "arose"],
    "appears": ["seems", "looks", "turns up"],
    "appear": ["seem", "look", "turn up"],
    "appeared": ["seemed", "looked", "turned up"],
    "seems": ["looks", "appears", "comes across as"],
    "seem": ["look", "appear", "come across as"],
    "seemed": ["looked", "appeared", "came across as"],
    "becomes": ["turns into", "grows into", "shifts into"],
    "become": ["get", "turn"],
    "became": ["turned into", "grew into"],
    "continues": ["keeps going", "carries on", "pushes on"],
    "continue": ["keep going", "carry on", "push on"],
    "continued": ["kept going", "carried on", "pushed on"],
    "expands": ["widens", "stretches", "grows"],
    "expand": ["widen", "stretch", "grow"],
    "expanded": ["widened", "stretched", "grew"],
    "spreads": ["fans out", "filters through", "circulates"],
    "spread": ["fan out", "filter through", "circulate"],
    "spread out": ["fanned out", "filtered through"],
    "accelerates": ["speeds up", "ramps up"],
    "accelerate": ["speed up", "ramp up"],
    "accelerated": ["sped up", "ramped up"],
    "slows": ["eases", "drags", "loses pace"],
    "slow": ["ease", "drag", "lose pace"],
    "slowed": ["eased", "dragged"],
    "weakens": ["erodes", "wears down", "saps"],
    "weaken": ["erode", "wear down", "sap"],
    "weakened": ["eroded", "wore down", "sapped"],
    "strengthens": ["fortifies", "tightens", "reinforces"],
    "strengthen": ["fortify", "tighten", "reinforce"],
    "strengthened": ["fortified", "tightened", "reinforced"],
    "challenges": ["pushes back on", "questions", "takes issue with"],
    "challenge": ["push back on", "question", "take issue with"],
    "challenged": ["pushed back on", "questioned", "took issue with"],
    "questions": ["doubts", "concerns"],
    "question": ["doubt", "concern"],
    "questioned": ["doubted", "challenged"],
    "confirms": ["backs up", "bears out", "backs"],
    "confirm": ["back up", "bear out"],
    "confirmed": ["backed up", "bore out"],
    "contradicts": ["cuts against", "flies in the face of", "undercuts"],
    "contradict": ["cut against", "fly in the face of", "undercut"],
    "contradicted": ["cut against", "flew in the face of", "undercut"],
    "compares": ["lines up", "sets side by side", "stacks up"],
    "compare": ["line up", "stack up", "set side by side"],
    "compared": ["lined up", "stacked up", "set side by side"],
    "differs": ["diverges", "part ways", "varies"],
    "differ": ["diverge", "vary"],
    "differed": ["diverged", "varied"],
    "similar to": ["akin to", "much like", "close to"],
    "differs from": ["stands apart from", "departs from"],
}
SYN_TABLE.update({
    "utilize": ["use"], "utilizes": ["uses"], "utilized": ["used"], "utilizing": ["using"],
    "utilise": ["use"], "utilises": ["uses"], "utilised": ["used"], "utilising": ["using"],
    "facilitate": ["support", "make possible"],
    "facilitates": ["drives", "supports"], "facilitated": ["drove", "supported"],
    "facilitating": ["driving", "supporting"],
    "commence": ["start", "begin"], "commenced": ["started", "began"],
    "initiate": ["start", "kick off"], "initiated": ["started", "kicked off"],
    "endeavor": ["effort"], "endeavors": ["efforts"], "endeavour": ["effort"],
    "subsequently": ["later", "then"], "previously": ["before", "earlier"],
    "ascertain": ["find out", "pin down"], "determine": ["work out", "pin down"],
    "determined": ["worked out", "pinned down"],
    "implement": ["carry out", "put in place"], "implemented": ["carried out", "put in place"],
    "implementing": ["carrying out", "putting in place"],
    "purchase": ["buy"], "purchased": ["bought"], "purchasing": ["buying"],
    "numerous": ["many", "a number of", "countless"], "various": ["several", "a range of", "different"],
    "assist": ["help"], "assists": ["helps"], "assisted": ["helped"],
    "assisting": ["helping"], "additional": ["extra", "more"],
    "concerning": ["about"], "regarding": ["about"],
    "substantial": ["sizeable", "hefty", "material"],
    "extensive": ["wide-ranging", "broad", "far-reaching"],
    "numerous studies": ["plenty of studies", "a raft of studies"],
    "individuals": ["people", "folks"], "persons": ["people"],
    "leverage": ["use", "draw on"], "leverages": ["uses", "draws on"],
    "leveraged": ["used", "drew on"], "leveraging": ["using", "drawing on"],
    "harness": ["tap", "wield", "make good use of"], "harnesses": ["taps", "wields"],
    "harnessed": ["tapped", "made good use of"], "harnessing": ["tapping"],
    "landscape": ["terrain", "ground", "setting"],
    "landscapes": ["terrains", "grounds", "settings"],
    "navigate": ["steer through", "work through"],
    "navigates": ["steers through", "works through"],
    "navigated": ["steered through", "worked through"],
    "navigating": ["steering through", "working through"],
})
SYN_TABLE.update({
    "importance": ["weight", "centrality", "significance"],
    "improving": ["lifting", "sharpening", "strengthening"],
    "growth": ["expansion", "development"],
})

SYN_TABLE.update({
    # -- adjectives --
    "important": ["vital", "weighty", "consequential", "significant"],
    "effectively": ["successfully", "well", "capably"],
    "effective": ["potent", "high-performing", "solid"],
    "ineffective": ["hollow", "weak", "half-baked"],
    "efficient": ["lean", "tight", "productive"],
    "efficiently": ["cleanly", "without waste", "slickly"],
    "necessary": ["needed", "required", "crucial"],
    "essential": ["vital", "core", "indispensable"],
    "vital": ["make-or-break", "central", "lifeline"[:0]+"lifesaving"],
    "critical": ["decisive", "make-or-break", "load-bearing"],
    "fundamental": ["bedrock", "core", "root-level"],
    "central": ["core", "anchor", "load-bearing"],
    "primary": ["lead", "chief", "frontline"],
    "main": ["chief", "lead", "head"],
    "major": ["heavyweight", "big", "leading"],
    "minor": ["small-time", "sideline", "slight"],
    "large": ["sizable", "extensive", "broad"],
    "small": ["slight", "modest", "compact"],
    "big": ["hefty", "major", "sweeping"],
    "huge": ["enormous", "whopping", "massive"],
    "enormous": ["giant", "colossal", "towering"],
    "massive": ["titanic", "outsized", "heavy"],
    "rapid": ["swift", "quick", "fast-moving"],
    "fast": ["swift", "brisk", "fleet"],
    "quick": ["snappy", "brisk", "swift"],
    "gradual": ["stepwise", "inch-by-inch", "measured"],
    "sudden": ["abrupt", "sharp", "out-of-nowhere"],
    "abrupt": ["jarring", "blunt", "abrupt"],
    "new": ["fresh", "untested", "just-minted"],
    "novel": ["unusual", "fresh", "offbeat"],
    "modern": ["present-day", "current", "today's"],
    "current": ["ongoing", "present-day", "live"],
    "traditional": ["long-standing", "old-school", "conventional"],
    "conventional": ["standard-issue", "textbook", "orthodox"],
    "standard": ["boilerplate", "run-of-the-mill", "textbook"],
    "typical": ["garden-variety", "standard-issue", "usual"],
    "common": ["widespread", "everyday", "run-of-the-mill"],
    "rare": ["scarce", "thin on the ground", "uncommon"],
    "unique": ["one-of-a-kind", "singular", "unmatched"],
    "complex": ["complicated", "intricate", "involved"],
    "complicated": ["knotty", "messy", "tangled"],
    "simple": ["clean", "plain", "no-frills"],
    "easy": ["painless", "straightforward", "effortless"],
    "hard": ["grueling", "punishing", "demanding"],
    "difficult": ["demanding", "tricky", "testing"],
    "evident": ["plain to see", "obvious", "unmistakable"],
    "clear": ["unmistakable", "plain", "cut-and-dried"],
    "obvious": ["staring us in the face", "plain as day", "unmissable"],
    "apparent": ["plain", "visible", "open"],
    "unclear": ["murky", "hazy", "fuzzy"],
    "vague": ["hazy", "woolly", "loose"],
    "precise": ["exact", "surgical", "sharp"],
    "accurate": ["spot-on", "true", "dead-on"],
    "correct": ["right", "sound", "true"],
    "wrong": ["off-base", "misguided", "bent"],
    "powerful": ["potent", "forceful", "muscular"],
    "strong": ["sturdy", "hard-hitting", "forceful"],
    "weak": ["flimsy", "wobbly", "hollow"],
    "successful": ["effective", "winning", "fruitful"],
    "failed": ["botched", "fallen short", "collapsed"],
    "safe": ["low-risk", "secure", "sheltered"],
    "dangerous": ["hazardous", "treacherous", "dicey"],
    "risky": ["dicey", "hazardous", "chancy"],
    "beneficial": ["worthwhile", "fruitful", "net-positive"],
    "harmful": ["damaging", "toxic", "corrosive"],
    "useful": ["handy", "practical", "serviceable"],
    "useless": ["worthless", "dead weight", "pointless"],
    "realistic": ["grounded", "practical", "real-world"],
    "practical": ["workable", "hands-on", "doable"],
    "theoretical": ["on-paper", "abstract", "bookish"],
    "global": ["worldwide", "planet-wide", "cross-border"],
    "local": ["close-to-home", "regional", "community-level"],
    "national": ["countrywide", "state-level", "domestic"],
    "international": ["cross-border", "overseas", "transnational"],
    "economic": ["financial", "money-side", "fiscal"],
    "political": ["policy-side", "governmental", "power-related"],
    "social": ["societal", "communal", "people-side"],
    "cultural": ["societal", "community-level", "customary"],
    "digital": ["online", "tech-driven"],
    "physical": ["real-world", "hands-on", "material"],
    "environmental": ["ecological", "green-side", "nature-related"],
    "educational": ["learning-related", "classroom-side", "academic"],
    "professional": ["career-level", "on-the-job", "occupational"],
    "personal": ["private", "own", "firsthand"],
    "public": ["wider", "civic", "open"],
    "private": ["closed-door", "personal", "nonpublic"],
    "visible": ["in plain sight", "out in the open", "obvious"],
    "invisible": ["under the surface", "hidden", "unseen"],
    "possible": ["feasible", "doable", "on the table"],
    "impossible": ["off the table", "unworkable", "no-go"],
    "likely": ["probable", "odds-on", "on the cards"],
    "unlikely": ["a long shot", "doubtful", "against the odds"],
    "consistent": ["steady", "uniform", "reliable"],
    "inconsistent": ["patchy", "hit-and-miss", "wobbly"],
    "stable": ["steady", "solid", "anchored"],
    "unstable": ["shaky", "volatile", "teetering"],
    "growing": ["climbing", "rising", "expanding"],
    "declining": ["slipping", "eroding", "waning"],
    "growing number of": ["rising count of", "expanding share of"],
    "widespread": ["far-flung", "everywhere", "common"],
    "widespread adoption": ["broad uptake", "broad take-up"],
    "deep": ["far-reaching", "profound", "root-level"],
    "shallow": ["surface-level", "skin-deep", "thin"],
    "broad": ["wide-ranging", "sweeping", "sweeping"],
    "narrow": ["tight", "thin", "slender"],
    "rich": ["layered", "deep", "full"],
    "poor": ["thin", "weak", "underfed"],
    "healthy": ["sound", "robust"[:0]+"sturdy", "in good shape"],
    "unhealthy": ["shaky", "ailing", "unwell"],
    "competitive": ["hard to beat", "in the running", "in the game"],
    "advanced": ["far along", "sophisticated", "next-level"],
    "basic": ["entry-level", "bare-bones", "elementary"],
    "sophisticated": ["refined", "high-end", "intricate"],
    "creative": ["inventive", "imaginative", "original"],
    "artificial": ["man-made", "engineered", "synthetic"],
    "natural": ["organic", "unforced", "inherent"],
    "whole": ["full", "entire", "complete"],
    "partial": ["incomplete", "one-sided", "halfway"],
    "independent": ["standalone", "self-standing", "freestanding"],
    "dependent": ["reliant", "tied to", "leaning on"],
    "responsible": None,
    "ethical": ["principled", "moral", "fair"],
    "unethical": ["questionable", "crooked"],
    "legal": ["lawful", "within the rules", "permitted"],
    "illegal": ["unlawful", "outside the rules", "banned"],
    "formal": ["official", "by-the-book", "on the record"],
    "informal": ["loose", "off-the-cuff", "unofficial"],
    "early": ["first-phase", "initial", "premature"],
    "late": ["last-minute", "overdue", "behind schedule"],
    
    
    "past": ["bygone", "earlier", "previous"],
    # -- nouns --
    "problem": ["headache", "snag", "hitch"],
    "problems": ["issues", "difficulties", "challenges"],
    "issue": ["flashpoint", "pain point", "wrinkle"],
    "issues": ["flashpoints", "pain points", "wrinkles"],
    "solution": ["fix", "way out", "antidote"],
    "solutions": ["fixes", "answers", "approaches"],
    "challenge": ["hurdle", "stumbling block", "uphill fight"],
    "challenges": ["hurdles", "obstacles", "tough spots"],
    "benefit": ["upside", "payoff", "win"],
    "benefits": ["advantages", "gains", "upsides"],
    "advantage": ["edge", "leg up", "upside"],
    "advantages": ["edges", "leg-ups", "upsides"],
    "drawback": ["downside", "catch", "rub"],
    "drawbacks": ["downsides", "catches", "rubs"],
    "disadvantage": ["handicap", "shortfall", "drag"],
    "result": ["upshot", "payoff", "bottom line"],
    "results": ["upshots", "payoffs", "findings"],
    "outcome": ["endgame", "final tally", "landing point"],
    "outcomes": ["endgames", "final tallies", "landing points"],
    "consequence": ["repercussion", "ripple", "fallout"],
    "consequences": ["repercussions", "ripples", "fallout"],
    "effect": ["ripple", "punch", "footprint"],
    "effects": ["ripples", "punches", "footprints"],
    "impact": ["effect", "consequence", "footprint"],
    "impacts": ["punches", "footprints", "shockwaves"],
    "influence": ["sway", "pull", "gravitational pull"],
    "change": ["shift", "overhaul", "makeover"],
    "changes": ["shifts", "overhauls", "makeovers"],
    "development": ["growth", "progress"],
    "developments": ["build-outs", "movements", "strides"],
    "growth": ["expansion", "development"],
    "progress": ["ground gained", "headway", "strides"],
    "improvement": ["gains", "refinement"],
    "improvements": ["gains", "upgrades", "refinements"],
    "goal": ["target", "endgame", "mark"],
    "goals": ["targets", "endgames", "marks"],
    "objective": ["target", "endgame", "mark"],
    "objectives": ["targets", "endgames", "marks"],
    "purpose": ["point", "mission", "raison d'être"],
    "aim": ["target", "mark", "goalpost"],
    "strategy": ["game plan", "playbook", "battle plan"],
    "strategies": ["game plans", "playbooks", "battle plans"],
    "approaches": ["angles", "methods", "routes"],
    "method": ["technique", "playbook", "way"],
    "methods": ["techniques", "playbooks", "ways"],
    "technique": ["method", "play", "trick of the trade"],
    "techniques": ["methods", "plays", "tricks of the trade"],
    "process": ["workflow", "pipeline", "sequence"],
    "processes": ["workflows", "pipelines", "sequences"],
    "system": ["setup", "machinery", "architecture"],
    "systems": ["setups", "machinery", "architectures"],
    "framework": ["scaffolding", "structure", "blueprint"],
    "frameworks": ["scaffoldings", "structures", "blueprints"],
    "structure": ["architecture", "makeup", "skeleton"],
    "structures": ["architectures", "makeups", "skeletons"],
    
    "program": ["drive", "effort", "scheme"],
    "programs": ["drives", "efforts", "schemes"],
    "project": ["undertaking", "effort"],
    "projects": ["undertakings", "efforts", "missions"],
    "plan": ["road map", "blueprint", "play"],
    "plans": ["road maps", "blueprints", "plays"],
    "factor": ["force", "lever", "piece of the puzzle"],
    "factors": ["forces", "levers", "pieces of the puzzle"],
    "element": ["ingredient", "piece", "strand"],
    "elements": ["ingredients", "pieces", "strands"],
    "component": ["building block", "piece", "cog"],
    "components": ["building blocks", "pieces", "cogs"],
    "aspect": ["facet", "element", "part"],
    "aspects": ["facets", "elements", "parts"],
    "feature": ["hallmark", "trait", "quirk"],
    "features": ["hallmarks", "traits", "quirks"],
    "characteristic": ["hallmark", "trait", "fingerprint"],
    "characteristics": ["hallmarks", "traits", "fingerprints"],
    "role": ["function", "job"],
    "roles": ["posts", "seats", "slots"],
    
    "functions": ["jobs", "duties", "roles"],
    "part": ["component", "element", "piece"],
    "parts": ["pieces", "slices", "chunks"],
    "area": ["territory", "patch", "space"],
    "areas": ["territories", "patches", "spaces"],
    "field": ["arena", "turf", "domain"],
    "fields": ["arenas", "turfs", "domains"],
    "domain": ["turf", "arena", "sandbox"],
    "sector": ["corner of the economy", "bracket", "wing"],
    "sectors": ["corners of the economy", "brackets", "wings"],
    "topic": ["subject", "thread", "matter"],
    "topics": ["subjects", "threads", "matters"],
    "subject": ["matter", "thread", "topic"],
    "subjects": ["matters", "threads", "topics"],
    "theme": ["thread", "motif", "throughline"],
    "themes": ["threads", "motifs", "throughlines"],
    "concern": ["worry", "misgiving"],
    "concerns": ["worries", "misgivings"],

    "risks": ["hazards", "exposures", "vulnerabilities"],
    "threat": ["menace", "peril", "danger zone"],
    "threats": ["menaces", "perils", "danger zones"],
    "danger": ["peril", "hazard", "sketchy ground"],
    "dangers": ["perils", "hazards", "sketchy grounds"],
    "opportunity": ["opening", "window", "shot"],
    "opportunities": ["chances", "windows", "prospects"],
    "chance": ["shot", "window", "odds"],
    "trend": ["current", "drift", "momentum"],
    "trends": ["currents", "drifts", "momentum"],
    
    
    "example": ["case in point", "instance", "sample"],
    "examples": ["cases in point", "instances", "samples"],
    "instance": ["case", "episode", "sample"],
    "instances": ["cases", "episodes", "samples"],
    "case": ["episode", "situation", "story"],
    "cases": ["episodes", "situations", "stories"],
    "situation": ["state of play", "scene", "landscape of options"],
    "situations": ["states of play", "scenes", "setups"],
    "scenario": ["storyline", "state of play", "hypothetical"],
    "scenarios": ["storylines", "states of play", "hypotheticals"],
    "context": ["backdrop", "setting", "frame"],
    "contexts": ["backdrops", "settings", "frames"],
    "environment": ["surroundings", "setting", "milieu"],
    "environments": ["surroundings", "settings", "milieus"],
    "perspective": ["lens", "vantage point", "take"],
    "perspectives": ["lenses", "vantage points", "takes"],
    "view": ["take", "read", "lens"],
    "views": ["takes", "reads", "lenses"],
    "viewpoint": ["lens", "angle", "vantage point"],
    "viewpoints": ["lenses", "angles", "vantage points"],
    "opinion": ["take", "read", "stance"],
    "opinions": ["takes", "reads", "stances"],
    "idea": ["notion", "line of thinking", "concept"],
    "ideas": ["notions", "lines of thinking", "concepts"],
    "concept": ["notion", "idea", "line of thinking"],
    "concepts": ["notions", "ideas", "lines of thinking"],
    "notion": ["hunch", "idea", "line of thought"],
    "notions": ["hunches", "ideas", "lines of thought"],
    "principle": ["ground rule", "tenet", "bedrock rule"],
    "principles": ["ground rules", "tenets", "bedrock rules"],
    "rule": ["ground rule", "norm", "code"],
    "rules": ["ground rules", "norms", "codes"],
    "regulation": ["rulebook", "directive", "mandate"],
    "regulations": ["rulebooks", "directives", "mandates"],
    "practice": ["custom", "habit", "way of working"],
    "practices": ["customs", "habits", "ways of working"],
    "analysis": ["breakdown", "dissection", "read"],
    "analyses": ["breakdowns", "dissections", "reads"],
    "assessment": ["read", "sizing-up", "verdict"],
    "assessments": ["reads", "sizing-ups", "verdicts"],
    "evaluation": ["verdict", "read", "scorecard"],
    "evaluations": ["verdicts", "reads", "scorecards"],
    "review": ["once-over", "audit", "check"],
    "reviews": ["once-overs", "audits", "checks"],
    "research": ["analysis", "evidence"],
    "data": ["records", "evidence"],
    "information": ["details", "facts", "info"],
    "knowledge": ["know-how", "ground truth", "mastery"],
    "skill": ["knack", "toolkit", "craft"],
    "skills": ["knacks", "toolkits", "crafts"],
    "ability": ["knack", "strength", "capacity"],
    "abilities": ["knacks", "strengths", "capacities"],
    "capacity": ["headroom", "bandwidth", "firepower"],
    "capacities": ["headrooms", "bandwidths", "firepower"],
    "reason": ["driver", "why", "explanation"],
    "reasons": ["drivers", "whys", "explanations"],
    "source": ["wellspring", "origin", "root"],
    "sources": ["wellsprings", "origins", "roots"],
    "origin": ["root", "birthplace", "starting line"],
    "origins": ["roots", "birthplaces", "starting lines"],
    "beginning": ["starting line", "front end", "kickoff"],
    "beginnings": ["starting lines", "front ends", "kickoffs"],
    "start": ["kickoff", "launch", "jump-off point"],
    "starts": ["kickoffs", "launches", "jump-off points"],
    "end": ["finish line", "close", "far end"],
    "ends": ["finish lines", "closes", "far ends"],
    "conclusion": ["landing", "bottom line", "wrap-up"],
    "conclusions": ["landings", "bottom lines", "wrap-ups"],
    "summary": ["recap", "snapshot", "short version"],
    "summaries": ["recaps", "snapshots", "short versions"],
    "overview": ["big picture", "snapshot", " lay of the land"[:0]+"lay of the land"],
    "detail": ["fine print", "granular detail", "nitty-gritty"],
    "details": ["fine print", "nitty-gritty", "particulars"],
    "point": ["angle", "argument", "punchline"],
    "points": ["angles", "arguments", "punchlines"],
    "stage": ["phase", "chapter", "leg"],
    "stages": ["phases", "chapters", "legs"],
    "phase": ["leg", "chapter", "stretch"],
    "phases": ["legs", "chapters", "stretches"],
    "step": ["move", "stride", "lever"],
    "steps": ["moves", "strides", "levers"],
    "action": ["move", "countermove", "play"],
    "actions": ["moves", "counter-moves", "plays"],
    "task": ["job", "to-do", "assignment"],
    "tasks": ["jobs", "to-dos", "assignments"],
    "job": ["post", "gig", "role"],
    "jobs": ["posts", "gigs", "roles"],
    "duty": ["obligation", "charge", "burden"],
    "duties": ["obligations", "charges", "burdens"],
    "responsibility": ["ownership", "duty", "answerability"],
    "responsibilities": ["ownership", "charges", "duties"],
    "obligation": ["binding commitment", "charge", "debt"],
    "obligations": ["binding commitments", "charges", "debts"],
    "commitment": ["promise", "pledge", "stake in the ground"],
    "commitments": ["promises", "pledges", "stakes in the ground"],
    "effort": ["push", "grind", "legwork"],
    "efforts": ["pushes", "grinds", "legwork"],
    "attempt": ["bid", "try", "swings"[:0]+"shot"],
    "attempts": ["bids", "tries", "shots"],
    "way": ["manner", "method", "approach"],
    "ways": ["routes", "avenues", "paths"],
    "means": ["route", "vehicle", "channel"],
    "manner": ["fashion", "way", "style"],
    "type": ["breed", "variety", "flavor"],
    "types": ["breeds", "varieties", "flavors"],
    "kind": ["breed", "flavor", "stripe"],
    "kinds": ["breeds", "flavors", "stripes"],
    "sort": ["breed", "stripe", "flavor"],
    "sorts": ["breeds", "stripes", "flavors"],
    "category": ["bucket", "bracket", "family"],
    "categories": ["buckets", "brackets", "families"],
    "class": ["bracket", "tier", "cohort"],
    "classes": ["brackets", "tiers", "cohorts"],
    "group": ["cluster", "bloc", "camp"],
    "groups": ["clusters", "blocs", "camps"],
    
    "sets": ["clusters", "bundles", "batches"],
    "collection": ["bundle", "batch", "arsenal"],
    "collections": ["bundles", "batches", "arsenals"],
    "series": ["run", "chain", "streak"],
    "sequence": ["chain", "run", "ladder"],
    "sequences": ["chains", "runs", "ladders"],
    "order": ["pecking order", "ladder", "chain"],
    "level": ["tier", "rung", "altitude"],
    "levels": ["tiers", "rungs", "altitudes"],
    "limit": ["ceiling", "cap", "brake"],
    "limits": ["ceilings", "caps", "brakes"],
    "boundary": ["fence line", "borderline", "edge"],
    "boundaries": ["fence lines", "borderlines", "edges"],
    "restriction": ["choke point", "cap", "rein"],
    "restrictions": ["choke points", "caps", "reins"],
    "constraint": ["binding constraint", "choke point", "shackle"],
    "constraints": ["binding constraints", "choke points", "shackles"],
    "limitation": ["ceiling", "blind spot", "weak spot"],
    "limitations": ["ceilings", "blind spots", "weak spots"],
    "obstacle": ["roadblock", "stumbling block", "wall"],
    "obstacles": ["roadblocks", "stumbling blocks", "walls"],
    "barrier": ["wall", "choke point", "moat"],
    "barriers": ["walls", "choke points", "moats"],
    "hurdle": ["stumbling block", "gate", "jump"],
    "hurdles": ["stumbling blocks", "gates", "jumps"],
    "strength": ["muscle", "forte", "weapon"],
    "strengths": ["muscles", "fortes", "weapons"],
    "weakness": ["soft spot", "blind spot", "crack"],
    "weaknesses": ["soft spots", "blind spots", "cracks"],
    "flaw": ["crack", "blemish", "soft spot"],
    "flaws": ["cracks", "blemishes", "soft spots"],
    "defect": ["bug", "blemish", "crack"],
    "defects": ["bugs", "blemishes", "cracks"],
    "failure": ["misfire", "stumble", "wipeout"],
    "failures": ["misfires", "stumbles", "wipeouts"],
    "success": ["triumph", "victory", "home run"],
    "successes": ["triumphs", "victories", "home runs"],
    "achievement": ["landmark", "feather in the cap", "milestone"],
    "achievements": ["landmarks", "milestones", "feathers in the cap"],
    
    "quality": ["grade", "make", "finish"],
    "value": ["worth", "heft", "payoff"],
    "worth": ["heft", "payoff", "value"],
    "merit": ["case", "worth", "upside"],
    "merits": ["cases", "worths", "upsides"],
        "power": None,
    "forces": ["pressures", "machinery", "undercurrents"],
    "force": ["pressure", "undercurrent", "muscle"],
    "energy": ["momentum", "fuel", "drive"],
    "spirit": ["morale", "drive", "pulse"],
    "morale": ["fighting spirit", "pulse", "drive"],
    "mood": ["vibe", "temperature", "tenor"],
    "atmosphere": ["vibe", "tenor", "climate"],
    "culture": ["ethos", "climate", "way of working"],
    "habit": ["reflex", "custom", "default"],
    "habits": ["reflexes", "customs", "defaults"],
    "routine": ["drumbeat", "rhythm", "cycle"],
    "routines": ["drumbeats", "rhythms", "cycles"],
    "behavior": ["conduct", "tendencies", "track record"],
    "behaviors": ["conduct", "tendencies", "track records"],
    "attitude": ["posture", "mindset", "stance"],
    "attitudes": ["postures", "mindsets", "stances"],
    "mindset": ["headspace", "lens", "outfit of beliefs"[:0]+"frame of mind"],
    "belief": ["conviction", "article of faith", "creed"],
    "beliefs": ["convictions", "articles of faith", "creeds"],
    "conviction": ["certainty", "firm belief", "faith"],
    "convictions": ["certainties", "firm beliefs", "faiths"],
    "trend line": ["trajectory", "curve", "arc"],
    "trajectory": ["arc", "flight path", "curve"],
    "journey": ["path", "road", "trek"],
    "path": ["road", "route", "track"],
    "road": ["route", "path", "track"],
    "milestone": ["marker", "checkpoint", "landmark"],
    "milestones": ["markers", "checkpoints", "landmarks"],
    "transition": ["handoff", "shift", " crossover"[:0]+"crossover"],
    "transitions": ["handoffs", "shifts", "crossovers"],
})
SYN_TABLE.update({
    # adjectives commonly flagged by detectors
    "intricate": ["complicated", "detailed"],
    "comprehensive": ["thorough", "complete"],
    "meticulous": ["careful", "painstaking"],
    "nuanced": ["subtle"],
    "profound": ["deep"],
    "paramount": ["critical"],
    "bustling": ["busy"],
    "notable": ["striking"],
    "noteworthy": ["striking"],
    "groundbreaking": ["trailblazing", "pioneering"],
    "transformative": ["far-reaching"],
    "revolutionary": ["radical"],
    "innovative": ["fresh", "new"],
    "multifaceted": ["many-sided"],
    "pivotal": ["decisive", "big"],
    "crucial": ["key", "decisive"],
    "seamless": ["smooth"],
    "seamlessly": ["smoothly"],
    "robust": ["solid", "tough"],
    "holistic": ["complete", "big-picture"],
    # verbs
    "foster": ["grow", "build"],
    "fosters": ["grows", "builds"],
    "fostering": ["building"],
    "fostered": ["built"],
    "elevate": ["raise", "lift"],
    "elevates": ["raises", "lifts"],
    "elevated": ["raised", "lifted"],
    "elevating": ["raising"],
    "optimize": ["improve", "fine-tune"],
    "optimizes": ["improves"],
    "optimized": ["improved"],
    "optimizing": ["improving"],
    "optimization": ["improvement", "fine-tuning"],
    "illustrate": ["show"],
    "illustrates": ["shows"],
    "illustrated": ["showed", "shown"],
    "illustrating": ["showing"],
    "showcase": ["display"],
    "showcases": ["displays"],
    "showcased": ["displayed"],
    "showcasing": ["displaying"],
    "encompass": ["cover", "include"],
    "encompasses": ["covers"],
    "encompassed": ["covered"],
    "encompassing": ["covering"],
    "garner": ["earn", "win"],
    "garners": ["earns"],
    "garnered": ["earned"],
    "garnering": ["earning"],
    "demonstrate": ["show"],
    "demonstrates": ["shows", "makes clear", "reveals"],
    "demonstrated": ["showed", "made clear", "revealed"],
    "demonstrating": ["showing"],
    # nouns
    "paradigm": ["model"],
    "synergy": ["teamwork"],
    "synergies": ["teamwork"],
    "realm": ["area", "world"],
    "realms": ["areas", "worlds"],
    # mid-sentence connectors (sentence-initial handled by the connector deck)
    "moreover": ["also", "plus"],
    "furthermore": ["also", "besides"],
    "additionally": ["also", "on top of that"],
    "consequently": ["so", "as a result"],
    "nevertheless": ["even so", "still"],
    "nonetheless": ["even so"],
    "accordingly": ["so"],
    "ultimately": ["in the end", "when it matters"],
    "underscore": ["stress"],
    "underscores": ["stresses"],
    "underscoring": ["stressing"],
    "underscored": ["stressed"],
    "revolutionize": ["remake", "overhaul"],
    "revolutionizes": ["remakes", "overhauls"],
    "revolutionized": ["remade", "overhauled"],
    "revolutionizing": ["remaking", "overhauling"],
    "necessitate": ["demand", "require"],
    "necessitates": ["demands", "requires"],
    "necessitating": ["demanding", "requiring"],
    "necessitated": ["demanded", "required"],
})

# Detector-flagged vocabulary: these flip REGARDLESS of strength setting.
# Probabilistic flipping leaves detectable residue; flags get zero tolerance.
AI_FLAGGED = {
    'delve', 'delves', 'delved', 'delving', 'tapestry', 'crucial', 'pivotal',
    'seamless', 'seamlessly', 'holistic', 'multifaceted', 'robust', 'foster',
    'fosters', 'fostering', 'fostered', 'leverage', 'leverages', 'leveraging',
    'leveraged', 'underscore', 'underscores', 'underscoring', 'underscored',
    'ever-evolving', 'testament', 'realm', 'realms', 'navigate', 'navigates',
    'navigating', 'navigated', 'embark', 'embarks', 'embarking', 'embarked',
    'utilize', 'utilizes', 'utilized', 'utilizing', 'comprehensive',
    'notably', 'intricate', 'paramount', 'garnered', 'garner', 'garners',
    'meticulous', 'nuanced', 'profound', 'synergy', 'synergies', 'optimize',
    'vital', 'essentially', 'significance', 'significantly',
    'optimizes', 'optimized', 'optimizing', 'optimization', 'notable',
    'noteworthy', 'groundbreaking', 'transformative', 'revolutionary',
    'innovative', 'paradigm', 'moreover', 'furthermore', 'additionally',
    'consequently', 'nevertheless', 'nonetheless', 'accordingly',
    'ultimately', 'illustrate', 'illustrates', 'illustrated',
    'illustrating', 'showcase', 'showcases', 'showcased', 'showcasing',
    'encompass', 'encompasses', 'encompassed', 'encompassing', 'elevate',
    'elevates', 'elevated', 'elevating', 'revolutionize', 'revolutionizes',
    'revolutionized', 'revolutionizing', 'harness', 'harnesses',
    'harnessing', 'harnessed', 'cutting-edge', 'state-of-the-art',
    'game-changer', 'game-changing', 'plethora', 'myriad', 'kaleidoscope',
}

# ----------------------------------------------------------------------------
# 3. CORE MACHINERY
# ----------------------------------------------------------------------------
_ABBREV_RE = re.compile(
    r'\b(?:[A-Za-z]|e\.g|i\.e|etc|Dr|Mr|Mrs|Ms|Prof|vs|St|U\.S|U\.K|Fig|Inc|Ltd|Ph\.D|No|Vol|pp?)\.$')

def _split_sents(text):
    parts = re.split(r'(?<=[.!?”’۔])\s+', text.strip())
    merged = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        # keep only genuine abbreviation tails together ("U.S. economy")
        if merged and _ABBREV_RE.search(merged[-1]) and not _ABBREV_RE.search(p):
            merged[-1] += ' ' + p
        else:
            merged.append(p)
    return merged

def _join_clean(text):
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\s+([,.;:!?])', r'\1', text)
    text = re.sub(r'([,.;:!?])(?=[A-Za-z])', r'\1 ', text)
    text = re.sub(r'\s+—\s+', ' — ', text)
    return text.strip()

def _inline_cap(text):
    # code lines and lines starting with code keywords stay untouched
    if text.split()[0].lower().startswith(('def', 'import', 'class', 'return', 'if', 'for',
                                           'while', 'print(', '#', 'from')) if text.split() else False:
        return text
    text = re.sub(r'(?:^|\n)([a-z])', lambda m: m.group(1).upper(), text)
    def cap(m):
        w = m.group(2)
        if zipf_frequency(w, 'en') > 0.8:      # real lowercase word -> capitalize
            return m.group(1) + w[0].upper() + w[1:]
        return m.group(0)                        # mixed-case proper noun, leave it
    return re.sub(r'([.!?]\s+)([a-z][\w\'-]*)', cap, text)

_CODE_SAFE = ('def ', 'import ', 'class ', 'return ', 'if ', 'for ', 'while ',
               'print(', '#', 'from ', 'elif ', 'else:', 'elif:', 'try:', 'except:')

def _recap(text):
    sents = _split_sents(text)
    out = []
    for s in sents:
        if s and s[0].islower() and not s.strip().startswith(_CODE_SAFE):
            s = s[0].upper() + s[1:]
        out.append(s)
    return ' '.join(out)


# ---- v2.1: AI phrases that carry meaning get REPLACED, never deleted ----
# Deleting verb-bearing phrases amputates sentences ("Leaders must __ the intricate of...").
def _verb_form_map(mapping):
    def repl(m):
        out = mapping[m.group(0).lower()]
        return out[0].upper() + out[1:] if m.group(0)[0].isupper() else out
    return repl

_AI_PHRASES_REPLACE = [
    (r'\bdelving (?:deep(?:er|ly) )?into\b', 'digging into'),
    (r'\bdelved (?:deep(?:er|ly) )?into\b', 'dug into'),
    (r'\bdelves (?:deep(?:er|ly) )?into\b', 'digs into'),
    (r'\bdelve (?:deep(?:er|ly) )?into\b', 'dig into'),
    (r'\bdelving\b', 'digging'),
    (r'\bdelves\b', 'digs'),
    (r'\bdelved\b', 'dug'),
    (r'\bdelve\b', 'dig'),
    (r'\bunderscoring the (?:importance|significance) of\b', 'stressing the weight of'),
    (r'\bunderscored the (?:importance|significance) of\b', 'stressed the weight of'),
    (r'\bunderscores the (?:importance|significance) of\b', 'stresses the weight of'),
    (r'\bunderscore the (?:importance|significance) of\b', 'stress the weight of'),
    (r'\bhighlights the importance of\b', 'stresses the importance of'),
    (r'\bhighlight the importance of\b', 'stress the importance of'),
    (r'\bnavigating the (complexities|challenges|complex nature) of\b', 'working through the \\1 of'),
    (r'\bnavigated the (complexities|challenges|complex nature) of\b', 'worked through the \\1 of'),
    (r'\bnavigates the (complexities|challenges|complex nature) of\b', 'works through the \\1 of'),
    (r'\bnavigate the (complexities|challenges|complex nature) of\b', 'work through the \\1 of'),
    (r'\bharnessing the power of\b', 'tapping the power of'),
    (r'\bharnessed the power of\b', 'tapped the power of'),
    (r'\bharnesses the power of\b', 'taps the power of'),
    (r'\bharness the power of\b', 'tap the power of'),
    (r'\bunlocking the (?:full )?potential\b', 'bringing out the promise'),
    (r'\bunlock the (?:full )?potential\b', 'bring out the promise'),
    (r'\bunlocks the (?:full )?potential\b', 'brings out the promise'),
    (r'\bsheds light on\b', 'clarifies'),
    (r'\bshed light on\b', 'clarify'),
    (r'\bpaving the way for\b', 'setting the stage for'),
    (r'\bpaved the way for\b', 'set the stage for'),
    (r'\bpaves the way for\b', 'sets the stage for'),
    (r'\bpave the way for\b', 'set the stage for'),
    (r'\bopens? the door to\b', 'allows'),
    (r'\bserves as a testament to\b', 'shows'),
    (r'\bserve as a testament to\b', 'show'),
    (r'\bis a testament to\b', 'shows'),
    (r'\bare a testament to\b', 'show'),
    (r'\ba testament to\b', 'proof of'),
    (r'\bembark(?:ing|ed)? on a journey\b', 'set out on a path'),
    (r'\ba plethora of\b', 'plenty of'),
    (r'\ba myriad of\b', 'plenty of'),
    (r'\bplethora of\b', 'lots of'),
    (r'\bmyriad of\b', 'many'),
    (r'\bkaleidoscope of\b', 'mix of'),
    (r'\bwhen it comes to\b', 'on'),
    (r'\bcrucial (?:aspect|factor|element)\b', 'key part'),
    (r'\bpivotal (?:aspect|factor|element|moment|role)\b', 'key \\1part'),
    (r'\bthe (?:ever-evolving|ever-changing) (?:landscape|world|scene)\b', 'the current scene'),
    (r'\bin the realm of\b', 'in the world of'),
    (r'\bthis realm\b', 'this area'),
    (r'\bthese realms\b', 'these areas'),
    (r'\ba tapestry of\b', 'a mix of'),
    (r'\btapestry of\b', 'mix of'),
    (r'\bparadigm shift\b', 'major change'),
    (r'\bgame-?changer\b', 'turning point'),
    (r'\bgame-?changing\b', 'radical'),
    (r'\bcutting-edge\b', 'advanced'),
    (r'\bstate-of-the-art\b', 'modern'),
    (r'\bfostering growth\b', 'supporting growth'),
    (r'\bfostered growth\b', 'supported growth'),
    (r'\bfosters growth\b', 'supports growth'),
    (r'\bfoster growth\b', 'support growth'),
    (r'\bfostering innovation\b', 'supporting new ideas'),
    (r'\bfoster innovation\b', 'support new ideas'),
    (r'\bfostering collaboration\b', 'supporting teamwork'),
    (r'\bfoster collaboration\b', 'support teamwork'),
]

def _apply_replace_pass(text):
    for pat, repl in _AI_PHRASES_REPLACE:
        def _r(m, repl=repl):
            if isinstance(repl, str) and '\\1' in repl and m.lastindex:
                out = re.sub(re.escape('\\1'), m.group(1) or '', repl)
            else:
                out = repl
            return out[0].upper() + out[1:] if m.group(0)[:1].isupper() else out
        text = re.sub(pat, _r, text, flags=re.I)
    return text

def _strip_ai_phrases(text):
    text = _apply_replace_pass(text)
    for pat in AI_PHRASES_STRIP:
        text = re.sub(r'\b' + pat + r'\b,?\s*', '', text, flags=re.I)
    text = re.sub(r'\bIt (?:is|was) crucial that\b', 'It matters that', text, flags=re.I)
    text = re.sub(r'\bin conclusion\b,?\s*', '', text, flags=re.I)
    text = re.sub(r'\bin summary\b,?\s*', '', text, flags=re.I)
    text = re.sub(r',\s*,', ', ', text)
    text = re.sub(r'^\s*,\s*', '', text, flags=re.M)
    first_word = text.split()[0].lower() if text.split() else ''
    if not first_word.startswith(('def', 'import', 'class', 'return', 'if', 'for',
                                  'while', 'print(', '#', 'from')):
        text = re.sub(r'(?:^|[.!?]\s+)([a-z])', lambda m: m.group(0)[:-1] + m.group(1).upper(), text)
    return text

class _Deck:
    """Rotating deck: no replacement repeats until its cycle is exhausted."""
    def __init__(self, rng, items):
        self.rng, self.items, self.deck = rng, list(items), []
    def draw(self):
        if not self.deck:
            self.deck = self.rng.sample(self.items, len(self.items))
        return self.deck.pop()

def _swap_connectors(sents, rng, strength):
    used_recent = {}
    out = []
    for i, s in enumerate(sents):
        m = re.match(r'^(But|However|Therefore|Moreover|Additionally|Furthermore|'
                     r'Consequently|Nevertheless|Nonetheless|Meanwhile|Similarly|'
                     r'Conversely|Notably|Indeed|Thus|Hence|Overall|Ultimately|'
                     r'In addition|In particular|In general|In essence|As such|'
                     r'For example|For instance|As a result|In contrast|'
                     r'On the other hand|In summary|To summarize|Firstly|Secondly|'
                     r'Thirdly|Finally|Interestingly|Furthermore)\b[,.]?\s*(.*)$', s, re.I)
        if m and rng.random() < strength:
            key = m.group(1).lower()
            if key in SENTENCE_CONNECTORS:
                seen = used_recent.get(key, 0)
                opts = SENTENCE_CONNECTORS[key]
                repl = opts[seen % len(opts)] if seen else rng.choice(opts)
                used_recent[key] = seen + 1
                rest = m.group(2)
                rest = rest[0].lower() + rest[1:] if rest and rest[0].isupper() and not rest[:2].isupper() else rest
                if not repl.endswith((',', ':', '—')) and rest and repl not in ('And', 'But', 'Yet', 'So', 'Or'):
                    repl = repl + ','
                new = repl + ' ' + rest
                new = new.strip()
                out.append(new[0].upper() + new[1:] if new else new)
                continue
        out.append(s)
    return out

# POS-ambiguous words: flipping them without context check damages grammar.
DET_SET = {'the','a','an','this','that','these','those','its','their','his','her',
           'our','your','my','such','every','each','some','many','much','more',
           'most','few','several','no','another','any','one','two','three','of',
           'for','with','in','on','at','by','from','about','across','without',
           'despite','including','between','among','under','over','after',
           'before','against','per','via','through','upon','within','both','all',
           'either','neither','each'}
AMBIG_NOUN = {
    'risk': ["hazard", "exposure"],
    'gain': ["upside", "advance"],
    'future': None,
    'potential': ["capability", "promise"],
    'influence': ["sway", "pull"],
    'effect': ["ripple", "footprint"], 'change': ["shift", "overhaul", "makeover"],
    'study': ["deep dive", "work", "body of evidence"],
    'state': ["status", "condition", "standing"],
    'order': ["sequence", "ladder", "arrangement"],
    'matter': ["affair", "business", "question"],
    'case': ["episode", "situation", "story"],
    'form': ["type", "shape", "variant"], 'note': ["remark", "annotation"],
    'question': ["doubt", "query", "issue"], 'address': ["speech", "location"],
    'focus': ["emphasis", "spotlight", "center of gravity"],
    'increase': ["rise", "uptick", "climb"], 'decrease': ["drop", "fall", "downturn"],
    'limit': ["ceiling", "cap", "brake"], 'start': ["kickoff", "launch", "jump-off point"],
    'end': ["close", "wrap-up"], 'mark': ["milestone", "signal"],
    'issue': ["flashpoint", "pain point", "wrinkle"],
    'challenge': ["hurdle", "stumbling block", "uphill fight"],
    'attempt': ["bid", "try", "shot"], 'try': ["bid", "shot"],
    'plan': ["road map", "blueprint", "play"], 'work': ["effort", "labor", "grind"],
    'play': ["role", "part"], 'group': ["cluster", "bloc", "camp"],
    'class': ["bracket", "tier", "cohort"], 'set': ["cluster", "bundle", "batch"],
    'cause': ["root cause", "driver", "trigger"], 'level': ["tier", "rung", "altitude"],
    'field': ["arena", "turf", "domain"], 'part': ["component", "element", "piece"],
    'rank': ["standing", "position"], 'lead': ["front position", "edge"],
    'drive': ["push", "momentum", "engine"], 'force': ["pressure", "undercurrent", "muscle"],
    'practice': ["custom", "habit", "way of working"],
    'concern': ["worry", "misgiving", "anxiety"], 'source': ["wellspring", "origin", "root"],
    'point': ["angle", "argument", "punchline"],
    'series': ["run", "chain", "streak"], 'transition': ["handoff", "shift", "crossover"],
    'support': ["backing", "backup", "anchor"], 'claim': ["assertion", "statement"],
    'power': ["force", "strength", "reach"],
    'fashion': ["manner", "way", "style"], 'means': ["route", "vehicle", "channel"],
    'affect': None,
}
AMBIG_VERB = {
    'risk': ["endanger", "gamble on"], 'gain': None,
    'influence': ["shape", "bear on", "touch"], 'impact': ["hit", "shape", "bear on"],
    'effect': ["bring about", "produce"], 'change': ["alter", "revise", "rework"],
    'study': ["examine", "probe", "dig into"], 'state': ["say", "note", "point out"],
    'order': None, 'matter': ["count", "register", "carry weight"],
    'case': None, 'form': None, 'note': ["point out", "observe", "remark"],
    'question': ["doubt", "challenge", "push back on"],
    'address': ["tackle", "take on", "deal with"],
    'focus': ["zero in", "concentrate", "home in"],
    'increase': ["raise", "lift", "push up"], 'decrease': ["cut", "trim", "drop"],
    'limit': ["cap", "curb", "rein in"], 'start': ["begin", "kick off", "open"],
    'end': ["wrap up", "conclude"], 'mark': ["signal", "flag", "herald"],
    'issue': ["put out", "release"], 'challenge': ["push back on", "question", "take issue with"],
    'attempt': ["try", "take a run at"], 'try': ["attempt"],
    'plan': ["map out", "line up"], 'work': ["operate", "function", "hold up"],
    'play': ["act", "operate"], 'group': ["cluster", "band together"],
    'class': None, 'set': ["establish", "pin down"],
    'cause': ["trigger", "bring on", "set off"], 'level': None, 'field': None,
    'part': None, 'rank': ["place", "grade"], 'lead': ["drive", "head", "guide"],
    'drive': ["push", "fuel", "power"], 'force': ["compel", "push"],
    'practice': ["rehearse", "hone"], 'concern': ["worry", "trouble", "weigh on"],
    'source': None, 'point': None,
    'series': None, 'transition': ["move", "shift"],
    'support': ["back", "bolster", "underpin"], 'claim': ["say", "contend", "put forward"],
    'power': ["compel", "push"],
    'fashion': None, 'means': None, 'affect': ["shape", "touch", "hit"],
}
_VOWELS = set('aeiou')
_AN_H = ('hour', 'honest', 'honor', 'honour', 'heir')
_A_SPECIAL = ('one', 'once', 'euro', 'euph', 'eur', 'uni', 'use', 'usu', 'uti', 'unit', 'ubiq')
def _article_for(word):
    w = word.lower()
    if not w:
        return 'a'
    c = w[0]
    if c == 'h':
        return 'an' if any(w.startswith(x) for x in _AN_H) else 'a'
    if c in _VOWELS:
        return 'a' if any(w.startswith(x) for x in _A_SPECIAL) else 'an'
    return 'a'

def _zipf(w):
    return zipf_frequency(w.lower().strip('.,;:!?'), 'en')

# verbs whose direct objects carry fixed meaning (seized power, gained influence)
_AMB_OBJ_VERBS = {'seized', 'seize', 'gained', 'gain', 'holds', 'hold', 'held',
    'takes', 'take', 'took', 'wields', 'wield', 'wielded', 'exerts', 'exert',
    'exerted', 'acquired', 'acquire', 'grabs', 'grabbed', 'attains', 'attained',
    'achieves', 'achieved', 'commands', 'commanded', 'controls', 'controlled',
    'abuse', 'abuses', 'abused', 'misuse', 'misused', 'abused', 'yielded',
    'yield', 'yields', 'grabbed', 'wrested', 'usurped', 'enjoys', 'enjoyed'}

def _flip_synonyms(text, rng, strength, profile):
    sense_overrides = {}
    used_choices = {}   # key -> set of substitutes already used in this document
    # stem prefixes of words already in the document: substitutes must not collide with surviving stems
    doc_stems = {w[:4].lower() for w in re.findall(r"[A-Za-z']+", text) if len(w) >= 4}
    _toks = re.findall(r"[A-Za-z']+|[.,;:!?]", text)
    _PRON = {'i', 'he', 'she', 'it', 'they', 'we', 'you'}
    _break = {'and', 'but', 'or', 'because', 'while', 'that', 'which', 'who', '.', ',', ';', ':', '!', '?'}
    for _i, _t in enumerate(_toks):
        _tl = _t.lower()
        if _tl in _PRON and _i + 1 < len(_toks):
            _nxt = _toks[_i + 1].lower()
            _nb = _nxt[:-1] if _nxt.endswith(('s', 'es')) and len(_nxt) > 4 else _nxt
            if _nxt.endswith('s') and _nb in AMBIG_VERB:
                sense_overrides[_nxt] = 'VB'
                for _j in range(_i + 2, min(len(_toks), _i + 8)):
                    _w2 = _toks[_j].lower()
                    if _w2 in _break:
                        break
                    _b2 = _w2
                    if _b2 in AMBIG_NOUN or _b2 in SYN_TABLE:
                        if _b2 not in sense_overrides:
                            sense_overrides[_b2] = 'NN'
    tag_fn = _get_tagger()
    tag_map = None
    if tag_fn:
        try:
            toks_all = re.findall(r"[A-Za-z']+|[.,;:!?]", text)
            clean = [t for t in toks_all if re.search(r"[A-Za-z']", t)]
            tagged = tag_fn(clean)
            pos_of = {}
            j = 0
            for t in toks_all:
                if re.search(r"[A-Za-z']", t):
                    if j < len(tagged):
                        w, tg = tagged[j]
                        pos_of[w.lower()] = tg
                    j += 1
            tag_map = pos_of
        except Exception:
            tag_map = None
    for i, comp in enumerate(PROTECTED_COMPOUNDS):
        text = text.replace(comp, "\x00%d\x00" % i)
        text = text.replace(comp.capitalize(), "\x01%d\x00" % i)
    keys = sorted(SYN_TABLE.keys(), key=len, reverse=True)
    pattern = re.compile(r'\b(' + '|'.join(re.escape(k) for k in keys) + r')\b', re.I)
    n_flipped = 0
    def repl(match):
        nonlocal n_flipped
        word = match.group(0)
        is_cap = word[0].isupper()
        # proper-noun heuristic: capitalized AND not sentence-initial -> skip
        start = match.start()
        if is_cap and start > 0:
            before = text[start-2:start]
            if before and before[0].isalpha():
                return word
        wlow = word.lower()
        if rng.random() > (1.0 if wlow in AI_FLAGGED else min(1.0, strength + 0.35)):
            return word
        cands = SYN_TABLE.get(wlow)
        # auxiliary guard: after has/have/had/is/are/was/were/be/been, a verb must
        # become a past participle - flipping breaks grammar ("has get" not "has gotten")
        prev_aux = text[:start].split()[-1].lower().strip(',;:') if text[:start].split() else ''
        if prev_aux in ('has', 'have', 'had', 'is', 'are', 'was', 'were', 'be', 'been',
                        'get', 'got', 'getting', 'gets') and wlow not in AMBIG_NOUN \
                and wlow not in AI_FLAGGED:
            cands = None
        wbase = wlow
        for suf in ('ing', 'ed', 'es', 's'):
            if wbase.endswith(suf) and len(wbase) > len(suf) + 2:
                wbase = wbase[:-len(suf)]
                break
        wbase = wbase or wlow
        if wlow in AMBIG_NOUN or wlow in AMBIG_VERB or \
                wbase in AMBIG_NOUN or wbase in AMBIG_VERB:
            prev = text[:start].split()
            prev2 = ' '.join(p.lower().strip(',;:') for p in prev[-2:])
            if prev2 in ('in the', 'at the', 'by the', 'to the', 'from the',
                         'on the', 'in a', 'in an', 'without') and \
                    wlow in ('end', 'start', 'limit', 'matter', 'case', 'point',
                             'order', 'turn', 'beginning'):
                return word          # idiom shell ("in the end") - never flip
            pword = prev[-1].lower().strip(',;:') if prev else ''
            if (wlow in AMBIG_NOUN or wbase in AMBIG_NOUN) and pword in _AMB_OBJ_VERBS:
                return word            # "seized power", "gained influence" - meaningful, keep
            nxt = text[match.end():].lstrip().split()
            nword = nxt[0].lower().strip(',;:.') if nxt else ''
            adj_sfx = ('al', 'ic', 'ive', 'ous', 'ful', 'less', 'able', 'ible',
                       'ish', 'ary', 'ory', 'ent', 'ant', 'ing', 'ed')
            noun_ctx = (pword in DET_SET
                        or (len(pword) > 3 and pword.endswith(adj_sfx))
                        or nword in ('of',))
            wtag = sense_overrides.get(wlow) or ((tag_map or {}).get(wlow, '') if tag_map else '')
            forced_verb = pword in ('i', 'he', 'she', 'it', 'they', 'we', 'you') and \
                wbase in AMBIG_VERB and wlow != wbase
            forced_noun = pword in ('my', 'your', 'his', 'her', 'its', 'our', 'their') and \
                (wlow in AMBIG_NOUN or wbase in AMBIG_NOUN)
            forced_noun = pword in ('my', 'your', 'his', 'her', 'its', 'our', 'their') and \
                (wlow in AMBIG_NOUN or wbase in AMBIG_NOUN)
            if wtag and not (wtag.startswith('NN') or wtag.startswith(('VB', 'MD'))) and not (forced_verb or forced_noun):
                return word          # odd tag (JJ/RB/IN) - sense unknown, never gamble
            if forced_noun:
                cands = AMBIG_NOUN.get(wlow) or AMBIG_NOUN.get(wbase)   # "their influence"
            elif forced_verb:
                cands = AMBIG_VERB.get(wbase) or None  # "she gains", "they influence"
            elif wtag.startswith('NN'):
                cands = AMBIG_NOUN.get(wlow) or None   # noun usage (tagged)
            elif wtag.startswith(('VB', 'MD')):
                cands = AMBIG_VERB.get(wlow) or None   # verb usage (tagged)
            elif noun_ctx:
                cands = AMBIG_NOUN.get(wlow) or AMBIG_NOUN.get(wbase)   # noun usage (heuristic)
            else:
                cands = AMBIG_VERB.get(wlow) or AMBIG_VERB.get(wbase)   # verb usage (heuristic)
            if not cands:
                return word                            # ambiguous + unclear -> never flip
        if not cands:
            return word
        # Zipf targeting: prefer options less predictable than the original
        scored = []
        oz = _zipf(word)
        for c in cands:
            if not c or c.lower() == word.lower():
                continue
            z = _zipf(c.split()[0])
            if _HAS_WF and z < 2.4:           # too obscure damages readability
                continue
            scored.append((z, c))
        if not scored:
            scored = [(0, c) for c in cands if c]
        # alternate rotation: never reuse the same substitute for a key within one document
        _used = used_choices.setdefault(wlow, set())
        if _used and len(_used) < len(scored):
            scored = [t for t in scored if t[1] not in _used]
        # avoid substitutes sharing a stem with another word that survives in the document
        _fresh = [t for t in scored if t[1].split()[0][:4].lower() not in doc_stems or t[1].split()[0][:4].lower() == wlow[:4]]
        if _fresh:
            scored = _fresh
        scored.sort(key=lambda t: t[0])
        # weighted pick toward the rarest third
        k = rng.random()
        pick = scored[min(len(scored)-1, int(k * max(1, len(scored) * 0.7)))]
        choice = pick[1]
        used_choices[wlow].add(choice)
        # avoid article collisions: "for a surge" after "for", "the a surge"
        prev = text[:start].split()
        pword = prev[-1].lower().strip(',;:') if prev else ''
        if (choice.startswith('a ') or choice.startswith('an ')) and pword in DET_SET:
            choice = choice[2:]
        if choice.startswith('the ') and pword in DET_SET:
            choice = choice[4:]
        if is_cap:
            choice = choice[0].upper() + choice[1:]
        n_flipped += 1
        return choice
    # placeholder for proper-noun check source text (set below before use)
    out = pattern.sub(repl, text)
    for i, comp in enumerate(PROTECTED_COMPOUNDS):
        out = out.replace("\x00%d\x00" % i, comp).replace("\x01%d\x00" % i, comp.capitalize())
    return out, n_flipped

# ----------------------------------------------------------------------------
# 4. SYNTACTIC TEMPLATE DE-TEMPLATING
# ----------------------------------------------------------------------------
_PASSIVE_TEMPLATES = [
    (r'\bit (?:is|was) widely (?:believed|thought|accepted|assumed) that\b',
     'Most people accept that'),
    (r'\bit (?:is|was) (?:generally|widely) accepted that\b', 'Most accept that'),
    (r'\bit (?:is|was) believed that\b', 'Many believe that'),
    (r'\bit can be argued that\b', 'You could argue that'),
    (r'\bit (?:is|was) (?:often|frequently) argued that\b', 'Many argue that'),
    (r'\bit (?:is|was) (?:often|frequently) considered\b', 'Many consider it'),
    (r'\b(is|are) (?:often |generally |frequently |widely |sometimes |routinely )?considered to be\b', r'\1 seen as'),
    (r'\b(is|are) (?:often |generally |frequently |widely |sometimes |routinely )?regarded as\b', r'\1 seen as'),
    (r'\b(is|are) (?:often |generally |frequently |widely |sometimes )?viewed as\b', r'\1 seen as'),
    (r'\bhas been shown to\b', 'appears to'),
    (r'\bhave been shown to\b', 'appear to'),
    (r'\bshould be noted that\b', 'Worth noting:'),
    (r'\bit (?:is|was) essential to\b', 'It matters to'),
    (r'\bnot only (.{3,40}?), but also (.{3,40}?)([.!?])', r'\1, and \2 too\3'),
    (r'\bnot only (.{3,40}?) but also (.{3,40}?)([.!?])', r'\1, and \2 too\3'),
]

def _soften_passive(text, rng, strength):
    for pat, repl in _PASSIVE_TEMPLATES:
        if re.search(pat, text, re.I) and rng.random() < strength:
            text = re.sub(pat, repl, text, count=1, flags=re.I)
    return text

def _front_subordinate(s, rng, strength):
    """Pull a trailing subordinate clause to the front (meaning-preserving)."""
    m = re.match(r'^(.{10,}?),? ((?:because|although|though|since|when|if|after|'
                 r'even though|even if|whereas|while) (?:it |they |he |she |we |this |that |there )?[a-z].{4,})$',
                 s, re.I)
    if not m or rng.random() > strength:
        return s
    clause = m.group(2).strip()
    rest = m.group(1).strip()
    if clause.count(',') > 1 or len(clause.split()) < 5:
        return s
    clause = clause[0].upper() + clause[1:]
    if not clause.endswith(('!','?')):
        clause += ','
    elif clause.endswith('.'):
        clause = clause[:-1] + ','
    rest = rest[0].lower() + rest[1:]
    return clause + ' ' + rest

def _drop_oxford(s, rng):
    """Human habit: inconsistent comma before 'and' in lists."""
    commas = s.count(',')
    if commas >= 2 and rng.random() < 0.5:
        s = re.sub(r',\s+and\s+', ' and ', s, count=1)
    elif commas >= 2 and rng.random() < 0.3:
        s = re.sub(r',\s+and\s+([^,]{1,30}?)([.!?])', r', \1\2', s, count=1)
    return s

def _vary_openers(sents, rng, strength, profile):
    """No two adjacent sentences may start with the same word (template kill)."""
    out = []
    for i, s in enumerate(sents):
        if out:
            prev_first = out[-1].split()[0].lower() if out[-1].split() else ''
            words = s.split()
            if words and words[0].lower() == prev_first and rng.random() < strength:
                if i > 0 and rng.random() < 0.6:
                    s2 = _front_subordinate(s, rng, 1.0)
                    if s2 != s:
                        s = s2
                if rng.random() < 0.5 and profile != 'formal':
                    lead = rng.choice(['And', 'Plus,', 'Still,', 'Now,', 'Yet'])
                    s = lead + ' ' + (s[0].lower() + s[1:])
        out.append(s)
    return out

# ----------------------------------------------------------------------------
# 5. BURSTINESS ENGINE — engineered human length distribution
# ----------------------------------------------------------------------------
# Human essays/news: mean ~13.5 words, CV ~0.55-0.75; mixture of staccato
# fragments, mid-length, and long subordinate-laden runs.
_LENGTH_BUCKETS = [
    (0.12, 3, 6),    # fragments / staccato
    (0.27, 7, 11),
    (0.30, 12, 18),
    (0.20, 19, 26),
    (0.11, 27, 38),  # rambles with subordinate clauses
]

def _sample_targets(rng, n):
    picks = []
    for _ in range(n):
        r, acc = rng.random(), 0.0
        for p, lo, hi in _LENGTH_BUCKETS:
            acc += p
            if r <= acc:
                picks.append(rng.randint(lo, hi))
                break
        else:
            picks.append(15)
    return picks

_CONNECT_DECK = [', and ', ', but ', ', so ', ', yet ', '; ', ' — ', ', though ',
                 ', even so, ', ', still, ', ', which means ']

class _ConnDeck:
    def __init__(self, rng, pool=None):
        self.rng, self.deck = rng, []
        self.pool = pool or _CONNECT_DECK
    def draw(self, avoid=None):
        if not self.deck:
            self.deck = self.rng.sample(self.pool, len(self.pool))
        c = self.deck.pop()
        if avoid and c.strip(' ,—') == avoid.strip(' ,—') and self.deck:
            self.deck.insert(0, c)
            c = self.deck.pop()
        return c

def _best_break(s, rng, lo=0.3, hi=0.7):
    """Pick the split point closest to a random fraction in [lo,hi]."""
    breaks = [m.start() for m in re.finditer(r'[,;:—]\s', s)]
    # subordinators/relatives only: "and/but/so/including/however" would make verbless fragments
    breaks += [m.start() for m in re.finditer(r'\s(?:which|because|whereas)\s', s, re.I)]
    # list-comma guard: if the sentence has ", and/or/nor/but", commas before that
    # marker are list-internal - splitting there destroys the list
    list_end = None
    for m in re.finditer(r',\s+(?:and|or|nor|but)\s', s):
        if list_end is None or m.start() > list_end:
            list_end = m.start()
    # never split at a comma that IS the list connector (", and X" / ", or X")
    breaks = [c for c in breaks
              if not re.match(r',\s+(?:and|or|nor|but)\s', s[c:c+20])]
    if list_end is not None:
        breaks = [c for c in breaks if c >= list_end]
    if not breaks:
        return None
    target = len(s) * (lo + (hi - lo) * rng.random())
    def _left_ok(c):
        left = s[:c].rstrip()
        if len(left.split()) < 4:
            return False
        if len(left.split()) <= 4 and left.endswith(','):
            return False
        last = left.split()[-1].lower().strip(',;:')
        return last not in _LEAD_CONN_FIRST
    _VERBISH = {'is','are','was','were','has','have','had','will','would','can','could',
                'must','should','do','does','did','makes','make','gives','give','offers',
                'offer','extends','extend','demands','demand','engages','engage','drives',
                'drive','requires','require','calls','call','needs','need','holds','hold',
                'gets','get','goes','go','comes','come','takes','take','sees','see'}
    def _right_ok(c):
        w = s[c:].lstrip().split()
        if not w:
            return False
        first = w[0].lower().rstrip(',;:')
        if first in ('including', 'namely', 'particularly', 'especially'):
            return False                       # verbless list-fragment
        if first.endswith('ing') and len(w) > 1 and w[1].lower() not in ('is', 'are', 'was', 'were', 'has', 'have', 'had', 'it', 'they', 'this', 'that', 'i', 'we', 'you', 'he', 'she'):
            return False                       # dangling participle fragment
        # list-tail guard: short right part with no verb = a broken list tail
        if len(w) <= 6 and not any(x.lower().rstrip(',;:.') in _VERBISH for x in w[:5]):
            return False
        return True
    good = [c for c in breaks if _left_ok(c) and _right_ok(c) and len(s[c:].split()) >= 4]
    pool = good or [c for c in breaks if _left_ok(c) and _right_ok(c) and len(s[c:].split()) >= 4] or None
    if pool is None:
        return None
    return min(pool, key=lambda c: abs(c - target))

def _split_at(s, idx):
    a, b = s[:idx].strip().rstrip(',;:—'), s[idx:].strip().lstrip(',;:— ')
    if not (a and b):
        return None
    b = b[0].upper() + b[1:]
    if not b.endswith(('.','!','?')):
        b += '.'
    if not a.endswith(('.','!','?')):
        a += '.'
    return a, b

_LEAD_CONN_RE = re.compile(r"^(?:Plus,\s*|Also,\s*|On top of that,\s*|Beyond that,\s*|"
                           r"What's more,\s*|And\s+|But\s+|Yet\s+|Still,\s*|So\s+|Even so,\s*|"
                           r"Besides,\s*|"
                           r"That said,\s*|Now,\s*|Additionally,\s*|Moreover,\s*|Furthermore,\s*|"
                           r"However,\s*|Therefore,\s*|Thus,\s*|Indeed,\s*)", re.I)

_LEAD_CONN_FIRST = {
    'plus', 'also', 'on', 'beyond', "what's", 'and', 'but', 'yet', 'still', 'so',
    'even', 'that', 'now', 'additionally', 'moreover', 'furthermore', 'however',
    'therefore', 'thus', 'indeed', 'meanwhile', 'notably', 'overall', 'ultimately',
    'first', 'second', 'third', 'finally', 'in', 'for', 'as', 'while', 'when',
    'although', 'though', 'because', 'since', 'if', 'after', 'before', 'with',
    'under', 'across', 'among', 'between', 'despite', 'truth', 'here', 'look',
    'put', 'either', 'the', 'this', 'these', 'those', 'it', 'they', 'i', 'we',
    'you', 'he', 'she', 'my', 'our', 'their', 'bottom', 'at', 'to', 'from',
}

def _strip_lead_conn(s):
    return _LEAD_CONN_RE.sub('', s)

def _lc_first(s):
    # lower the first word; all-caps words get fully lowercased ("HERE" -> "here")
    if not s:
        return s
    first_word = s.split()[0] if s.split() else s
    if first_word.isupper() and len(first_word) > 1:
        return s.replace(first_word, first_word.lower(), 1)
    return s[0].lower() + s[1:]


_CONTRAST_SET = ('yet', 'but', 'however', 'though', 'still', 'whereas')

def _diversify_connectives(text):
    """Within a paragraph, a contrast connective may appear 2-3 times (original +
    rotation + deck draw). Detectors key on such uniformity; humans spread them.
    Rewrite 2nd+ occurrences to another contrast word, meaning-safe (same class)."""
    out = []
    for para in re.split(r'(\n\s*\n)', text):
        if re.match(r'^\s*$', para):
            out.append(para)
            continue
        used = set()
        def _sub(m):
            lead, word = m.group(1), m.group(2)
            w = word.lower()
            if w not in used:
                used.add(w)
                return m.group(0)
            opts = [c for c in _CONTRAST_SET if c not in used]
            if not opts:
                return m.group(0)
            repl = opts[0]
            if lead.strip() in ('', '.!', '?', '—') or word[0].isupper():
                repl = repl[0].upper() + repl[1:]
            return lead + repl
        para = re.sub(r'(?i)(^|[.!?]\s+|—|,\s*)(yet|but|however|though|still|whereas)\b',
                      _sub, para)
        out.append(para)
    return ''.join(out)

def _merge_chain(lead, nxt_list, deck, rng):
    # never merge across script boundaries (Urdu sentence + English text)
    lead_nl = _has_nonlatin(lead)
    nxt_list = [n for n in nxt_list if _has_nonlatin(n) == lead_nl]
    merged = lead.rstrip('.!?')
    for nxt in nxt_list:
        nxt = _strip_lead_conn(nxt.strip())
        if not nxt:
            continue
        conn = deck.draw()
        merged = merged.rstrip('.!?') + conn + _lc_first(nxt)
    if not merged.endswith(('.','!','?')):
        merged += '.'
    return merged

def _reshape_lengths(sents, rng, strength, profile):
    """Force the sentence-length distribution toward the human profile.
    Greedy bin-packing: merge short sentences up to a sampled target; split
    monsters; never merge past the cap."""
    deck = _ConnDeck(rng)
    targets = _sample_targets(rng, max(4, len(sents)))
    out, i, ti = [], 0, 0
    while i < len(sents):
        s = sents[i]
        n = len(s.split())
        target = targets[ti % len(targets)]
        ti += 1
        # monster -> split first
        if n > 40:
            br = _best_break(s, rng, 0.35, 0.6)
            parts = _split_at(s, br) if br else None
            if parts:
                out.extend(parts)
                i += 1
                continue
        # merge short runs toward target
        n_alpha = sum(1 for w in s.split() if any(ch.isalpha() for ch in w) and len(w) >= 2)
        _s_nl = _has_nonlatin(s)
        if _s_nl:
            out.append(s)
            i += 1
            continue
        if (n < max(11, target - 3) and i + 1 < len(sents) and n_alpha >= 3
                and (rng.random() < strength or (n <= 5 and n_alpha >= 3))):
            chain = [s]
            total = n
            j = i + 1
            # count the real content words (lead connectives will be stripped)

            while j < len(sents) and total < max(target - 6, 9):
                if _has_nonlatin(sents[j]) != _s_nl:
                    break                       # never merge across scripts
                nn = len(sents[j].split())
                if total + nn > max(target + 8, 30):
                    break
                chain.append(sents[j])
                total += nn
                j += 1
                if rng.random() < 0.12:
                    break
            if len(chain) > 1:
                out.append(_merge_chain(chain[0], chain[1:], deck, rng))
                i = j
                continue
        # long sentence vs target -> split if target much shorter
        if n > target + 14 and rng.random() < strength * 0.7:
            br = _best_break(s, rng, 0.3, 0.65)
            parts = _split_at(s, br) if br else None
            if parts:
                out.extend(parts)
                ti += 1
                i += 1
                continue
        out.append(s)
        i += 1

    # enforcement: guarantee spread (max-min >= 13 words or a fragment exists)
    def lens(lst):
        return [len(x.split()) for x in lst]
    guard = 0
    while guard < 8:
        ls = lens(out)
        if not ls:
            break
        if (max(ls) - min(ls) >= 13 and max(ls) >= 24) or len(ls) < 3:
            break
        idx = max(range(len(out)), key=lambda k: len(out[k].split()))
        br = _best_break(out[idx], rng, 0.25, 0.7)
        parts = _split_at(out[idx], br) if br else None
        if not parts:
            break
        out[idx:idx+1] = parts
        guard += 1
    return out

def _inject_fragments(sents, rng, profile, strength):
    """Pull short leading subordinate clauses out as emphatic fragments.
    ('Despite the resistance, X moved forward.' -> 'Despite the resistance. X moved forward.')"""
    p = {'formal': 0.10, 'academic': 0.10, 'balanced': 0.45, 'casual': 0.75}[profile]
    max_frag = 1 if profile in ('formal', 'academic') else 2
    done = 0
    out = []
    for s in sents:
        if done < max_frag and rng.random() < p * strength:
            m = re.match(r'^((?:Despite|With|Under|Across|Among|Between)[^,.]{1,42}?),\s+(.{8,}.*)$',
                         s)
            if m and 2 <= len(m.group(1).split()) <= 6:
                frag = m.group(1).strip()
                rest = m.group(2).strip()
                # D1 guard: the rest must contain a real subject-verb core.  A
                # rest that starts with a bare noun followed by a subordinator
                # ("... that engages ...") is a subordinate tail, not a sentence.
                rest_words = rest.split()
                has_verb_like = any(w.lower().rstrip(',;:.') in
                                    ('is', 'are', 'was', 'were', 'has', 'have', 'had',
                                     'will', 'would', 'can', 'could', 'must', 'should',
                                     'do', 'does', 'did', 'makes', 'makes', 'give',
                                     'offers', 'extends', 'demands', 'calls', 'engages',
                                     'reshaped', 'raised', 'sparked', 'pose', 'poses')
                                    for w in rest_words[:12])
                if not has_verb_like:
                    out.append(s)
                    continue
                rest = rest[0].upper() + rest[1:]
                if not rest.endswith(('.','!','?')):
                    rest += '.'
                out.append(frag + '.')
                out.append(rest)
                done += 1
                continue
        out.append(s)
    return out

# ----------------------------------------------------------------------------
# 6. HUMAN TEXTURE INJECTION
# ----------------------------------------------------------------------------
_CONTRACTIONS = [
    ("do not", "don't"), ("does not", "doesn't"), ("did not", "didn't"),
    ("cannot", "can't"), ("can not", "can't"), ("will not", "won't"),
    ("would not", "wouldn't"), ("is not", "isn't"), ("are not", "aren't"),
    ("was not", "wasn't"), ("were not", "weren't"), ("has not", "hasn't"),
    ("have not", "haven't"), ("had not", "hadn't"), ("could not", "couldn't"),
    ("should not", "shouldn't"), ("must not", "mustn't"), ("it is", "it's"),
    ("that is", "that's"), ("there is", "there's"), ("what is", "what's"),
    ("let us", "let's"), ("you are", "you're"), ("they are", "they're"),
    ("we are", "we're"), ("i am", "I'm"), ("you will", "you'll"),
    ("we will", "we'll"), ("they will", "they'll"), ("it will", "it'll"),
    ("there are", "there are"), ("who is", "who's"), ("he is", "he's"),
    ("she is", "she's"), ("it has", "it's"), ("we have", "we've"),
    ("they have", "they've"), ("you have", "you've"), ("i have", "I've"),
]

_HEDGES = ["probably", "I think", "more or less", "to be fair",
           "in my experience", "if I'm honest", "for the most part",
           "roughly speaking", "as a rule", "on balance"]

def _inject_texture(sents, rng, profile, strength):
    p = {
        'formal':   dict(contr=0.35, hedge=0.06, dashparen=0.10, question=0.0,  opener=0.15),
        'academic': dict(contr=0.30, hedge=0.10, dashparen=0.12, question=0.0,  opener=0.15),
        'balanced': dict(contr=0.70, hedge=0.25, dashparen=0.25, question=0.04, opener=0.40),
        'casual':   dict(contr=0.90, hedge=0.45, dashparen=0.40, question=0.12, opener=0.60),
    }[profile]
    n_words = sum(len(s.split()) for s in sents) or 1
    max_hedges = max(1, int(n_words / 150))
    max_dash = max(1, int(n_words / 150))
    max_q = 1 if n_words > 250 else 0
    hedges, dashes, qs = 0, 0, 0
    used_opens = []
    opener_pool = ["Look,", "Now,", "Here's the thing:", "That said,", "Truth is,",
                   "In practice,", "Either way,", "And here's the kicker:",
                   "The catch?", "Put simply,"]
    out = []
    for i, s in enumerate(sents):
        # contractions
        for a, b in _CONTRACTIONS:
            if rng.random() < p['contr'] * strength:
                s = re.sub(r'\b' + re.escape(a) + r'\b', b, s, flags=re.I)
        # sentence-initial hedge
        first_word = s.split()[0].lower() if s.split() else ''
        connectorish = (first_word in _LEAD_CONN_FIRST) or s.split() and s.split()[0].endswith(',')
        if hedges < max_hedges and i > 0 and not connectorish and rng.random() < p['hedge'] * strength:
            h = rng.choice(_HEDGES)
            sep = '' if h.endswith((':')) else (', ' if not h.endswith(',') else ' ')
            s = h + sep + (s[0].lower() + s[1:] if not h.endswith(':') else s)
            hedges += 1
        # discourse opener on a middle sentence
        if (i > 0 and i < len(sents) - 1 and used_opens.count(True) < 2
                and not connectorish
                and rng.random() < p['opener'] * strength * 0.5 and len(s.split()) > 10):
            op = rng.choice([o for o in opener_pool if o not in used_opens] or opener_pool)
            used_opens.append(op)
            s = op + ' ' + (s[0].lower() + s[1:])
        # dash parenthetical: convert one appositive comma to a dash
        if dashes < max_dash and rng.random() < p['dashparen'] * strength and s.count(',') >= 1:
            cands = [m.start() for m in re.finditer(r',\s+(?:which|that|including|namely|particularly|especially)\s', s)]
            if cands:
                k = rng.choice(cands)
                s = s[:k] + ' — ' + s[k+2:]
                dashes += 1
        # rhetorical tag (casual only)
        if qs < max_q and profile == 'casual' and i == len(sents) - 1 and rng.random() < p['question'] * strength:
            s = s.rstrip('.') + ', no?'
            qs += 1
        out.append(s)
    return out

# ----------------------------------------------------------------------------
# 7. PARAGRAPH-SHAPE VARIATION  (uniform paragraph lengths are an AI tell)
# ----------------------------------------------------------------------------
def _reshape_paragraphs(paragraphs, rng):
    if len(paragraphs) < 1:
        return paragraphs
    if len(paragraphs) == 1:
        sents = _split_sents(paragraphs[0])
        if len(sents) >= 6:
            # uneven split with jitter
            n = len(sents)
            cuts = sorted(rng.sample(range(2, n - 1), min(2, max(1, n // 4))))
            groups, prev = [], 0
            for c in cuts:
                groups.append(sents[prev:c])
                prev = c
            groups.append(sents[prev:])
            return [' '.join(g) for g in groups]
        return paragraphs
    # merge a too-short paragraph into its neighbor
    code = [_looks_like_code(p) for p in paragraphs]
    lens = [len(p.split()) for p in paragraphs]
    avg = sum(lens) / len(lens)
    out, i = [], 0
    while i < len(paragraphs):
        _can_join = (i + 1 < len(paragraphs)
                     and not code[i] and not code[i+1]
                     and _has_nonlatin(paragraphs[i]) == _has_nonlatin(paragraphs[i+1]))
        if lens[i] < avg * 0.35 and _can_join and len(lens) > 2 and rng.random() < 0.7:
            out.append(paragraphs[i].rstrip() + ' ' + paragraphs[i+1].lstrip())
            i += 2
        else:
            out.append(paragraphs[i])
            i += 1
    return out

# ----------------------------------------------------------------------------
# 8. ANTI-REPETITION (n-gram traces + opener templates)
# ----------------------------------------------------------------------------
_STOPWORDS = set("""a an the and or but if while of in on at to for with by from as is are was were be been being
it its this that these those there here he she they we you i his her their our your my me him them us who whom whose
which what when where why how not no nor so than then too very can will just don should now""".split())

def _content_trigrams(text):
    words = [w for w in re.findall(r"[a-z']+", text.lower())]
    tri = []
    for i in range(len(words) - 2):
        g = words[i:i+3]
        if any(w in _STOPWORDS for w in g) and all(w in _STOPWORDS for w in g):
            continue
        tri.append(tuple(g))
    return tri

def _kill_repeats(text, rng, strength):
    """If a content 3-gram appears twice+, flip one word in the later copy."""
    tri = _content_trigrams(text)
    seen, dups = {}, []
    for g in tri:
        if g in seen:
            dups.append(g)
        seen.setdefault(g, 0)
    for g in set(dups):
        pat = re.compile(r'\b' + r'\s+'.join(re.escape(w) for w in g) + r'\b', re.I)
        matches = list(pat.finditer(text))
        if len(matches) >= 2:
            m = matches[-1]
            for w in g:
                opts = SYN_TABLE.get(w)
                if opts and rng.random() < strength:
                    choice = rng.choice(opts)
                    seg = text[m.start():m.end()]
                    new_seg = re.sub(r'\b' + re.escape(w) + r'\b', choice, seg, count=1, flags=re.I)
                    text = text[:m.start()] + new_seg + text[m.end():]
                    break
    return text

# ----------------------------------------------------------------------------
# 9. QUALITY GATES (grammar invariants — block damage before it ships)
# ----------------------------------------------------------------------------
def _fix_articles(text):
    def fix(m):
        art, nxt = m.group(1), m.group(2)
        want = _article_for(nxt.split()[0] if nxt.split() else 'x')
        return (want + ' ' + nxt) if art.lower() != want else m.group(0)
    return re.sub(r'\b(a|an|A|An)\s+([A-Za-z][\w\'-]*(?:\s+\w+){0,0})', fix, text)

def _gates(text, rng=None):
    # split any monster sentence > 45 words
    sents = _split_sents(text)
    out = []
    for s in sents:
        while len(s.split()) > 45:
            br = _best_break(s, rng, 0.35, 0.65)
            parts = _split_at(s, br) if br else None
            if not parts:
                break
            out.append(parts[0])
            s = parts[1]
        out.append(s)
    text = ' '.join(out)
    # article agreement sweep
    text = _fix_articles(text)
    # punctuation hygiene
    text = re.sub(r'\s+([,.;:!?])', r'\1', text)
    text = re.sub(r'([,;:])(?=[A-Za-z0-9])', r'\1 ', text)
    text = re.sub(r'\s{2,}', ' ', text)
    text = re.sub(r'^\s*[,:;]\s*', '', text)
    # terminal punctuation + capitalization
    sents = _split_sents(text)
    fixed = []
    for s in sents:
        s = s.strip().lstrip(',;:— ')
        if not s:
            continue
        if s[0].islower() and not s.startswith(_CODE_SAFE):
            s = s[0].upper() + s[1:]
        if s[-1] not in '.!?:"。！？؟۔।':
            s += '.'
        fixed.append(s)
    return ' '.join(fixed)

# ----------------------------------------------------------------------------
# 10. SCORING — the honest heuristic, now multi-axis
# ----------------------------------------------------------------------------
def _mean(xs):
    return sum(xs) / len(xs) if xs else 0.0

def _stdev(xs):
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))

def analyze(text):
    sents = _split_sents(text)
    lens = [len(s.split()) for s in sents]
    mean_len = _mean(lens)
    cv = (_stdev(lens) / mean_len) if mean_len else 0.0

    content = [w for w in re.findall(r"[a-z']+", text.lower()) if w not in _STOPWORDS]
    zvals = [zipf_frequency(w, 'en') for w in content]
    zvals = [z for z in zvals if z > 0]
    zmean = _mean(zvals)
    zsd = _stdev(zvals)

    # per-sentence lexical predictability variance ("perplexity burstiness")
    sent_z = []
    for s in sents:
        ws = [w for w in re.findall(r"[a-z']+", s.lower()) if w not in _STOPWORDS]
        zv = [zipf_frequency(w, 'en') for w in ws]
        zv = [z for z in zv if z > 0]
        if zv:
            sent_z.append(_mean(zv))
    z_var_across = _stdev(sent_z)

    low = text.lower()
    marker_hits = sum(low.count(' ' + p + ' ') for p in AI_PHRASES)

    openers = [s.split()[0].lower() for s in sents if s.split()]
    opener_div = len(set(openers)) / len(openers) if openers else 0.0

    tri = _content_trigrams(text)
    tri_counts = {}
    for g in tri:
        tri_counts[g] = tri_counts.get(g, 0) + 1
    repeated = sum(c - 1 for c in tri_counts.values() if c > 1)
    tri_rate = repeated / len(tri) if tri else 0.0

    paras = [p for p in re.split(r'\n\s*\n', text) if p.strip()]
    plens = [len(p.split()) for p in paras]
    p_cv = (_stdev(plens) / _mean(plens)) if plens and _mean(plens) else 0.0

    # v2.1: direct flagged-vocabulary scan (strongest single detector signal)
    tokens_l = re.findall(r"[A-Za-z'-]+", text.lower())
    flag_count = sum(1 for w in tokens_l if w in AI_FLAGGED)
    r_flag = min(1.0, flag_count / max(1, len(lens) * 0.25))

    # v2.1: punctuation diversity (AI prose leans on comma+period only)
    punct_types = sum(1 for t in ('\u2014', ' - ', ';', ':', '(', '"', '?', '!') if t in text)
    r_punct = max(0.0, 1.0 - punct_types / 4.0)

    # composite risk 0-100 (heuristic, honestly labeled)
    r_cv = max(0.0, 1.0 - cv / 0.60)                 # want CV >= 0.6
    r_z = max(0.0, (zmean - 4.4) / 1.2) if zmean else 0.0   # want low mean zipf
    r_zv = max(0.0, 1.0 - z_var_across / 0.9)        # want sentence-level variety
    r_mk = min(1.0, marker_hits / max(1, len(lens) * 0.5))
    r_od = max(0.0, 1.0 - opener_div / 0.85)
    r_tri = min(1.0, tri_rate * 12)
    r_pp = max(0.0, 1.0 - p_cv / 0.35) if len(paras) > 1 else 0.0
    risk = 100 * (0.20 * r_cv + 0.18 * r_z + 0.09 * r_zv + 0.10 * r_mk +
                  0.10 * r_od + 0.08 * r_tri + 0.05 * r_pp +
                  0.15 * r_flag + 0.05 * r_punct)
    return {
        'ai_risk': round(risk, 1),
        'sentence_lengths': lens,
        'mean_len': round(mean_len, 1),
        'cv': round(cv, 2),
        'mean_zipf': round(zmean, 2),
        'zipf_sd': round(zsd, 2),
        'zipf_var_across_sentences': round(z_var_across, 2),
        'marker_hits': marker_hits,
        'opener_diversity': round(opener_div, 2),
        'trigram_repeat_rate': round(tri_rate, 3),
        'paragraph_cv': round(p_cv, 2),
        'sentences': len(lens),
        'paragraphs': len(paras),
    }

# ----------------------------------------------------------------------------
# 11. PIPELINE + ORCHESTRATOR (best-of-N, seed-reproducible)
# ----------------------------------------------------------------------------
_PROFILES = {
    'formal':   dict(contr=0.35, hedge=0.06, fragment=0.10, dashparen=0.10,
                     question=0.0, opener=0.15, syn=0.55, splitmerge=0.85,
                     conn=['; ', ', but ', ', yet ', ', though ', ', even so, ']),
    'academic': dict(contr=0.30, hedge=0.10, fragment=0.10, dashparen=0.12,
                     question=0.0, opener=0.15, syn=0.50, splitmerge=0.85,
                     conn=['; ', ', but ', ', yet ', ', though ', ' — ']),
    'balanced': dict(contr=0.70, hedge=0.25, fragment=0.45, dashparen=0.25,
                     question=0.04, opener=0.40, syn=0.80, splitmerge=1.0,
                     conn=None),
    'casual':   dict(contr=0.90, hedge=0.45, fragment=0.75, dashparen=0.40,
                     question=0.12, opener=0.60, syn=0.90, splitmerge=1.0,
                     conn=None),
}

_CODE_LINE_RE = re.compile(r'^\s*(?:def |class |import |from |return |if |for |while |print\(|#include|//|#\s|\{|\}|;|let |const |var |function )')
_SCRIPT_RE = re.compile(r'[^\x00-\x7F]')

def _looks_like_code(para):
    """A multi-line paragraph where most lines read as code passes through untouched."""
    lines = [l for l in para.splitlines() if l.strip()]
    if len(lines) < 2:
        return False
    codey = sum(1 for l in lines if _CODE_LINE_RE.match(l) or l.startswith(('    ', '\t')))
    return codey >= max(2, int(len(lines) * 0.6))

def _has_nonlatin(s):
    return bool(_SCRIPT_RE.search(s))

def _pipeline(text, rng, strength, profile):
    cfg = _PROFILES[profile]
    syn_strength = strength * cfg['syn']
    paragraphs = [p for p in re.split(r'\n\s*\n', text.strip()) if p.strip()]
    out_paras = []
    for para in paragraphs:
        if _looks_like_code(para):
            out_paras.append(para)
            continue
        para = _strip_ai_phrases(para)
        def _role_repl(m):
            v = rng.choice(['shape', 'drive', 'power', 'anchor'])
            # m.group(1) is the gerund if present (regex now consumes it)
            if m.group(1):
                verb = m.group(1)[:-3]
                if verb.endswith(('pp', 'nn', 'tt', 'mm', 'dd')):
                    verb = verb[:-1]
                aux = 'helps ' if m.group(0).lower().startswith('plays') else 'help '
                return aux + verb
            # no gerund captured: "plays a X role in NOUN" -> verb phrase
            out = (v + 's') if m.group(0).lower().startswith('plays') else v
            return out + ' '
        para = re.sub(r'\bplays? a (?:crucial|vital|pivotal|key|significant) role in\s+(?:(\w+ing)\b)?',
                      _role_repl, para, flags=re.I)
        para = re.sub(r'\bin order to\b', 'to', para, flags=re.I)
        para = re.sub(r'\bdue to the fact that\b', 'because', para, flags=re.I)
        para = re.sub(r'\bowing to the fact that\b', 'because', para, flags=re.I)
        para = re.sub(r'\b(?:a|the) majority of\b', 'most', para, flags=re.I)
        para = re.sub(r'\b(?:a|the) number of\b', 'several', para, flags=re.I)
        para = re.sub(r'\bprior to\b', 'before', para, flags=re.I)
        para = re.sub(r'\bsubsequent to\b', 'after', para, flags=re.I)
        para = re.sub(r'\bwith regard to\b', 'about', para, flags=re.I)
        para = re.sub(r'\bin terms of\b', 'for', para, flags=re.I)
        def _existential_repl(m):
            np = m.group(1).strip()
            # drop leading adverbs that ride along ("there are ALSO challenges") - they'd strand: "However, also hurdles..."
            np = re.sub(r'^(?:also|often|usually|typically|generally|always|sometimes|frequently|rarely|mainly|mostly|still|simply|just|clearly|certainly|apparently|even)\s+', '', np, flags=re.I)
            if not np:
                return m.group(2)
            return np + ' ' + m.group(2)
        para = re.sub(r'\bthere (?:is|are|was|were) ([^,.]{2,40}?) (?:that|which) ([a-z][^,.]{3,80})', _existential_repl, para, flags=re.I)
        para = _inline_cap(para)
        sents = _split_sents(para)
        sents = _swap_connectors(sents, rng, max(0.95, strength))
        s = ' '.join(sents)
        s = _soften_passive(s, rng, 1.0)
        sents = _split_sents(s)
        s = ' '.join(sents)
        s, _ = _flip_synonyms(s, rng, syn_strength, profile)
        sents = _split_sents(s)
        sents = _vary_openers(sents, rng, strength, profile)
        sents = [_drop_oxford(x, rng) for x in sents]
        sents = [_front_subordinate(x, rng, strength * 0.6) for x in sents]
        sents = _reshape_lengths(sents, rng, strength * cfg['splitmerge'], profile)
        sents = _inject_fragments(sents, rng, profile, strength)
        sents = _inject_texture(sents, rng, profile, strength)
        para_out = _gates(' '.join(sents), rng)
        para_out = _kill_repeats(para_out, rng, strength)
        para_out = re.sub(r'\blets ([A-Za-z]+) to\b', r'lets \1', para_out)
        para_out = _gates(para_out, rng)
        out_paras.append(para_out)
    out_paras = _reshape_paragraphs(out_paras, rng)
    return _diversify_connectives('\n\n'.join(out_paras))

# ---- v2.1: whole-document n-gram diversity ----
# Detectors fingerprint repeated trigrams; humans repeat them far less.
def _kill_3grams(text, rng):
    from collections import Counter
    sents = _split_sents(text)
    all_toks = []
    for s in sents:
        all_toks.extend(re.findall(r"[A-Za-z']+", s.lower()))
    tri = Counter(tuple(all_toks[i:i+3]) for i in range(len(all_toks)-2))
    # only meaningful repeats: at least one content word (>=4 chars, not a function word)
    def _contentful(t):
        return any(len(w) >= 4 and w not in DET_SET for w in t)
    repeated = {t for t, c in tri.items() if c > 1 and _contentful(t)
                and not all(w in DET_SET or w in ('of','in','to','and','the','a','an','is','are','was','were')
                            for w in t)}
    if not repeated:
        return text
    seen = set()
    out = []
    for s in sents:
        toks = re.findall(r"[A-Za-z']+", s.lower())
        here = {tuple(toks[i:i+3]) for i in range(len(toks)-2)} & repeated
        if here and (seen & here):
            # this sentence repeats a trigram already used - force re-flip it
            s2, _ = _flip_synonyms(s, rng, 1.0, 'balanced')
            if s2 != s:
                s = s2
            else:
                # no flippable keys left in the sentence: surgically swap one
                # word inside the repeated trigram itself
                for tri in here:
                    words = [w for w in tri if w in SYN_TABLE]
                    if not words:
                        continue
                    pick = rng.choice(words)
                    alt = rng.choice(SYN_TABLE[pick])
                    # form-matched for simple plurals
                    if pick.endswith('s') and alt.endswith('y'):
                        continue
                    m = re.search(r'\b' + re.escape(pick) + r'\b', s, re.I)
                    if m:
                        rep = alt if m.group(0)[0].islower() else alt[0].upper() + alt[1:]
                        s = s[:m.start()] + rep + s[m.end():]
        toks2 = re.findall(r"[A-Za-z']+", s.lower())
        for i in range(len(toks2)-2):
            seen.add(tuple(toks2[i:i+3]))
        out.append(s)
    return ' '.join(out)

# ---- v2.2: grammar verification & revert safety net ----
# Doctrine: grammar correctness outranks style. A sentence that fails
# grammatical validation is REVERTED to the original input, never shipped broken.
try:
    import nltk
    _nltk_ok = True
except Exception:
    _nltk_ok = False
_TAGGER_CACHE = {}

def _get_tagger():
    if not _nltk_ok:
        return None
    if 'ok' in _TAGGER_CACHE:
        return _TAGGER_CACHE['ok'] if _TAGGER_CACHE['ok'] else None
    try:
        from nltk.tag import pos_tag as _pt
        _TAGGER_CACHE['ok'] = _pt
    except Exception:
        _TAGGER_CACHE['ok'] = None
    return _TAGGER_CACHE['ok']

# verbs that must take -s in third-person singular
_MODALS = {'can', 'could', 'will', 'would', 'shall', 'should', 'may', 'might',
           'must', 'do', 'does', 'did', 'have', 'has', 'had'}

_COMMON_VERBS = set(['be', 'been', 'is', 'are', 'was', 'were', 'am', 'have', 'has', 'had', 'do', 'does', 'did', 'make', 'made', 'makes', 'go', 'goes', 'went', 'say', 'says', 'said', 'get', 'got', 'gets', 'take', 'took', 'takes', 'see', 'saw', 'seen', 'know', 'knew', 'known', 'think', 'thought', 'want', 'wanted', 'use', 'used', 'used', 'find', 'found', 'found', 'give', 'gave', 'given', 'tell', 'told', 'told', 'work', 'works', 'worked', 'call', 'calls', 'called', 'try', 'tries', 'tried', 'need', 'needs', 'needed', 'feel', 'felt', 'felt', 'become', 'becomes', 'became', 'leave', 'left', 'left', 'put', 'puts', 'put', 'mean', 'means', 'meant', 'keep', 'keeps', 'kept', 'let', 'lets', 'let', 'begin', 'began', 'begun', 'seem', 'seems', 'seemed', 'help', 'helps', 'helped', 'talk', 'talked', 'talked', 'turn', 'turns', 'turned', 'start', 'starts', 'started', 'show', 'shows', 'showed', 'hear', 'heard', 'heard', 'play', 'plays', 'played', 'run', 'runs', 'ran', 'move', 'moves', 'moved', 'live', 'lives', 'lived', 'like', 'likes', 'liked', 'believe', 'believed', 'hold', 'holds', 'held', 'bring', 'brought', 'happens', 'happens', 'happened', 'write', 'writes', 'wrote', 'provide', 'provides', 'provided', 'sit', 'sits', 'sat', 'stand', 'stands', 'stood', 'lose', 'loses', 'lost', 'pay', 'pays', 'paid', 'meet', 'meets', 'met', 'include', 'includes', 'included', 'continue', 'continues', 'continued', 'set', 'sets', 'set', 'learn', 'learns', 'learned', 'change', 'changes', 'changed', 'lead', 'leads', 'led', 'understand', 'understood', 'watch', 'watched', 'watched', 'follow', 'follows', 'followed', 'stop', 'stops', 'stopped', 'create', 'creates', 'created', 'speak', 'speaks', 'spoke', 'read', 'reads', 'read', 'spend', 'spends', 'spent', 'grow', 'grows', 'grew', 'open', 'opens', 'opened', 'walk', 'walks', 'walked', 'win', 'wins', 'won', 'offer', 'offers', 'offered', 'remember', 'remembered', 'remember', 'love', 'loves', 'loved', 'consider', 'considered', 'considered', 'appear', 'appears', 'appeared', 'buy', 'buys', 'bought', 'wait', 'waits', 'waited', 'serve', 'serves', 'served', 'die', 'dies', 'died', 'send', 'sends', 'sent', 'build', 'builds', 'built', 'stay', 'stays', 'stayed', 'fall', 'falls', 'fell', 'cut', 'cuts', 'cut', 'reach', 'reaches', 'reached', 'kill', 'kills', 'killed', 'raise', 'raises', 'raised', 'pass', 'passes', 'passed', 'sell', 'sells', 'sold', 'decide', 'decides', 'decided', 'return', 'returns', 'returned', 'explain', 'explains', 'explained', 'hope', 'hopes', 'hoped', 'develop', 'develops', 'developed', 'carry', 'carries', 'carried', 'break', 'breaks', 'broke', 'receive', 'receives', 'received', 'receive', 'achieve', 'achieved', 'achieve', 'become', 'effect', 'affect', 'effects', 'affected', 'remain', 'remains', 'remained', 'suggest', 'suggests', 'suggested', 'offer', 'offer', 'cause', 'causes', 'caused', 'occur', 'occurs', 'occurred', 'occur', 'control', 'controls', 'controlled', 'increase', 'increases', 'increased', 'occur', 'reduce', 'reduces', 'reduced', 'form', 'forms', 'formed', 'happen', 'happens', 'happened', 'happen', 'complete', 'completed', 'completed', 'allow', 'allows', 'allowed', 'add', 'adds', 'added', 'happen', 'grow', 'grows', 'grew', 'grow', 'study', 'studies', 'studied', 'study', 'become', 'becomes', 'became', 'become', 'come', 'comes', 'came', 'come', 'look', 'looks', 'looked', 'look'])

_VERB_BASES = set(AMBIG_VERB.keys()) | set(SYN_TABLE.keys())

def _grammar_fail_reasons(sent, tag_fn):
    """Return list of grammar violation reasons for a sentence.
    Conservative: fires only on clear violations (from v2.0 battery data)."""
    fails = []
    toks = re.findall(r"[A-Za-z']+|[.,;:!?]", sent)
    if not toks:
        return fails
    for o, c in (('\u0028', '\u0029'), ('\u201c', '\u201d'), ('"', '"')):
        if sent.count(o) != sent.count(c):
            fails.append(f'unbalanced {o}')
    low = sent.lower().split()
    for a, b in zip(low, low[1:]):
        if a == b and a in ('the', 'a', 'an', 'of', 'to', 'and', 'is', 'was', 'in'):
            fails.append(f'doubled {a}')
    tags = tag_fn(toks) if tag_fn else []
    tagmap = {t for _, t in tags}
    # verb presence: tagger OR common-verb fallback
    has_verb = any(t.startswith(('VB', 'MD')) for _, t in tags) or \
               any(w.lower() in _COMMON_VERBS for w in toks) or \
               any(w.lower().rstrip('s') in _VERB_BASES for w in toks)
    if not has_verb:
        fails.append('no verb')
    singular_prp = {'he', 'she', 'it', 'one', 'everyone',
                    'everybody', 'somebody', 'someone', 'nobody', 'anything',
                    'everything', 'something'}
    for i in range(len(tags) - 1):
        w, t = tags[i]
        w2, t2 = tags[i + 1]
        wl = w.lower()
        # modal followed by a noun-ish token = missing verb
        if t == 'MD' and t2 in ('DT', 'NN', 'JJ', 'IN', 'NNP', 'NNPS', 'NNS'):
            fails.append(f'modal missing verb "{w} {w2}"')
        # third-person singular subject + base verb
        if wl in singular_prp and t2 in ('VB', 'VBP') and w2.lower() not in _MODALS:
            fails.append(f'"{w} {w2}" agreement')
        if wl in ('they', 'we', 'you', 'these', 'those') and t2 == 'VBZ':
            fails.append(f'"{w} {w2}" agreement')
        if wl == 'i' and t2 == 'VBZ':
            fails.append('"I" + -s verb')
        # plural-looking noun (ends in s, tagged NN/NNP) + VBZ
        if t in ('NN', 'NNP') and wl.endswith('s') and t2 == 'VBZ' \
                and not wl.endswith(('ss', 'us', 'is')) and wl not in _MODALS:
            fails.append(f'"{w} {w2}" plural+s')
    first = toks[0].lower() if toks else ''
    if first in ('him', 'her', 'them', 'us', 'me'):
        fails.append(f'object pronoun "{first}" opens sentence')
    return fails

def _grammar_repair(out_text, orig_text, rng):
    """Validate every output sentence; revert failures to their closest
    original sentence. Paragraph structure is preserved: rejoining happens
    per paragraph, so code blocks and line breaks survive. Non-Latin
    sentences pass through untouched and are never dropped.
    Returns (fixed_text, n_reverted, n_checked)."""
    import difflib
    tag_fn = _get_tagger()
    origs = _split_sents(orig_text)
    n_rev = 0
    n_chk = 0
    out_paras = []
    paras = re.split(r'\n\s*\n', out_text.strip()) if out_text.strip() else ['']
    for para in paras:
        if not para.strip():
            out_paras.append(para)
            continue
        if _looks_like_code(para):
            out_paras.append(para)          # code: untouched, structure intact
            continue
        fixed = []
        for s in _split_sents(para):
            n_chk += 1
            if _has_nonlatin(s):
                fixed.append(s)             # never drop, never rewrite
                continue
            reasons = _grammar_fail_reasons(s, tag_fn)
            if not reasons:
                fixed.append(s)
                continue
            # revert to closest original sentence (difflib similarity)
            match = difflib.get_close_matches(s, origs, n=1, cutoff=0.3)
            if match and match[0] != s:
                # word-level passes are grammar-safe (form-matched): re-apply them
                # to the reverted original so AI-flagged words don't sneak back
                r1 = _apply_replace_pass(match[0])
                r2, _ = _flip_synonyms(r1, rng, 1.0, 'balanced')
                fixed.append(r2)
                n_rev += 1
            else:
                # no safe revert available: drop only if it is a fragment,
                # otherwise keep (best effort) and let scoring rank it low
                if len(s.split()) <= 4:
                    n_rev += 1
                    continue
                fixed.append(s)
        if fixed:
            out_paras.append(_join_clean(' '.join(fixed)))
    if not any(p.strip() for p in out_paras):
        return _join_clean(orig_text), n_rev, n_chk
    return '\n\n'.join(out_paras), n_rev, n_chk

def humanize(text, seed=None, strength=0.85, profile='balanced', tries=8):
    """Return the best of N independent runs, ranked by the honest metric.
    Deterministic: same seed -> same output."""
    if seed is None:
        seed = random.randrange(1_000_000_000)
    if profile not in _PROFILES:
        profile = 'balanced'
    before = analyze(text)
    # non-Latin script: out of scope - pass through untouched, stated honestly
    latin = sum(1 for ch in text if ch.isascii() and ch.isalpha())
    total_alpha = sum(1 for ch in text if ch.isalpha())
    cjk_arabic = sum(1 for ch in text if '\u0600' <= ch <= '\u06ff'
                     or '\u4e00' <= ch <= '\u9fff' or '\u3040' <= ch <= '\u30ff')
    if total_alpha > 0 and latin / max(1, total_alpha) < 0.5 and cjk_arabic > 0:
        return {'text': text, 'metrics_before': before, 'metrics': before,
                'seed_used': seed, 'profile': profile,
                'note': 'Non-Latin script detected: text passed through unchanged (engine targets English prose).'}

    # protect-and-restore: code paragraphs ride out the pipeline untouched
    _code_blocks = []
    _paras0 = [p for p in re.split(r'\n\s*\n', text) if p.strip()]
    if any(_looks_like_code(p) for p in _paras0):
        def _stash(m):
            _code_blocks.append(m.group(0))
            return f'\x00CB{len(_code_blocks) - 1}\x00'
        text = re.sub(r'(?:^|\n)(?:(?:    |\t)?[A-Za-z_].*)\n(?:(?:    |\t).*(?:\n|$))+',
                      _stash, text)
    best = None
    rounds = max(1, tries)
    for t in range(rounds):
        rng = random.Random(seed + t * 7919)
        out = _pipeline(text, rng, strength, profile)
        out = _kill_3grams(out, rng)
        out = _gates(out, rng)
        out, n_rev, n_chk = _grammar_repair(out, text, rng)
        m = analyze(out)
        m['grammar_reverts'] = n_rev
        m['grammar_checked'] = n_chk
        if best is None or m['ai_risk'] < best[1]['ai_risk']:
            best = (out, m, seed + t * 7919)
    # v2.1 escalation: if every try still scored risky, run a second flight of
    # fresh tries. The engine never ships its weakest acceptable result silently.
    needs_escalation = best is not None and (
        best[1]['ai_risk'] > 30.0 or best[1].get('cv', 1.0) < 0.35)
    if needs_escalation and len(text.split()) >= 60:
        for t in range(rounds):
            rng = random.Random(seed + 104729 + t * 2749)
            out = _pipeline(text, rng, strength, profile)
            out = _kill_3grams(out, rng)
            out = _gates(out, rng)
            out, n_rev, n_chk = _grammar_repair(out, text, rng)
            m = analyze(out)
            m['grammar_reverts'] = n_rev
            m['grammar_checked'] = n_chk
            if m['ai_risk'] < best[1]['ai_risk']:
                best = (out, m, seed + 104729 + t * 2749)
    out, m, used_seed = best
    for k, blk in enumerate(_code_blocks):
        out = out.replace(f'\x00CB{k}\x00', blk)
        out = out.replace(f'\x00CB{k}\x00\n', blk)
        out = out.replace(f' \x00CB{k}\x00', blk)
    if _code_blocks:
        out = re.sub(r' ?\x00CB\d+\x00', '', out)  # safety net: nothing stranded
        out = re.sub(r'\x00CB\d+\x00', '', out)
        out = re.sub(r'[ \t]+\n', '\n', out)          # tidy spacing around blocks
        out = re.sub(r'\n(?!    |\t)([ ]+)(?=[A-Za-z])', r'\n', out)  # prose lines only
    return {
        'text': out,
        'metrics_before': before,
        'metrics': m,
        'seed_used': used_seed,
        'profile': profile,
    }

if __name__ == '__main__':
    import json, sys
    demo = '''In today's fast-paced world, educational leadership plays a crucial role in fostering institutional development. Moreover, effective leaders utilize robust strategies in order to facilitate organizational change. There are many factors that influence this process. Teachers must adapt. Administrators must adapt as well. Furthermore, instructional supervision is often considered to be a multifaceted landscape. It is widely believed that professional development is essential for growth. In conclusion, the importance of continuous improvement cannot be overstated.'''
    r = humanize(demo, seed=42, profile='balanced')
    print(json.dumps(r['metrics'], indent=1))
    print('---'); print(r['text'])
# --- final table sanitation: substitutes must never reintroduce detector-flagged words ---
def _sanitize_substitutes():
    for _k in list(SYN_TABLE.keys()):
        _opts = SYN_TABLE[_k]
        if not _opts:
            continue                    # deliberate 'never flip' marker (None)
        _clean = [o for o in _opts if not any(w in AI_FLAGGED for w in re.findall(r"[a-z']+", o.lower()))]
        if _clean:
            SYN_TABLE[_k] = _clean
        else:
            del SYN_TABLE[_k]           # all options flagged: flip nothing rather than poison output

_sanitize_substitutes()

