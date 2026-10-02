
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
    ("utilize", "use"),
    ("utilizes", "uses"),
    ("utilized", "used"),
    ("utilizing", "using"),
    ("utilization", "use"),
    ("facilitate", "help"),
    ("facilitates", "helps"),
    ("commenced", "started"),
    ("subsequently", "then"),
    ("ascertain", "find out"),
    ("pertaining to", "about"),
    ("in order to", "to"),
    ("in the event that", "if"),
    ("prior to", "before"),
    ("subsequent to", "after"),
    ("with regard to", "about"),
    ("in terms of", "for"),
    ("serves as", "acts as"),
    ("has become", "is now"),
    ("in the ever-evolving", "in the changing"),
    ("ever-evolving", "changing"),
    ("pivotal", "key"),
    ("robust", "solid"),
    ("multifaceted", "layered"),
    ("seamlessly", "smoothly"),
    ("holistic", "well-rounded"),
    ("notably", "strikingly"),
    ("foster", "build"),
    ("fostering", "building"),
    ("fosters", "builds"),
    ("leverage", "use"),
    ("leveraging", "using"),
    ("navigating", "handling"),
    ("navigate", "handle"),
    ("journey", "path"),
    ("testament to", "proof of"),
    ("cutting-edge", "advanced"),
    ("in essence", "at its core"),
    ("comprehensive", "complete"),
    ("utilize", "use"),
    ("moreover", ""),
    ("furthermore", ""),
    ("additionally", ""),
    ("in conclusion", "to wrap up"),
    ("overall,", ""),
    ("in the realm of", "in"),
    ("realm of", "world of"),
    
]

HEDGES = ["honestly", "frankly", "pretty much", "at least", "in my experience",
          "if I'm being honest", "more or less", "to be fair", "basically"]

OPENERS = ["Look,", "Here's the thing:", "That said,", "Still,", "Now,",
           "Truth is,", "In practice,", "Either way,", "Oddly enough,"]


# --- Synonym dictionary: multiple options per word; RNG picks one per occurrence.
# Care taken: only genuinely interchangeable senses listed.
SYN_DICT = {
    "important": ["vital", "key", "major", "big"],
    "significant": ["major", "serious", "big", "meaningful"],
    "very": ["really", "quite", "highly", "so"],
    "many": ["a lot of", "plenty of", "lots of", "countless"],
    "much": ["plenty of", "a good deal of"],
    "several": ["a few", "a handful of", "some"],
    "shows": ["demonstrates", "reveals", "indicates", "points to"],
    "show": ["demonstrate", "reveal", "indicate", "point to"],
    "showed": ["demonstrated", "revealed", "indicated"],
    "demonstrates": ["shows", "makes clear", "reveals"],
    "demonstrated": ["showed", "made clear", "revealed"],
    "creates": ["builds", "forms", "produces", "generates"],
    "create": ["build", "form", "produce", "generate"],
    "created": ["built", "formed", "produced", "generated"],
    "helped": ["aided", "supported", "assisted"],
    "allows": ["lets", "enables", "makes it possible for"],
    "allow": ["let", "enable", "make it possible for"],
    "allows for": ["permits", "makes room for"],
    "enables": ["allows", "lets", "makes possible"],
    "enable": ["allow", "let", "make possible"],
    "improves": ["boosts", "strengthens", "raises", "betters"],
    "improve": ["boost", "make better", "strengthen", "build on"],
    "improved": ["boosted", "strengthened", "raised"],
    "increase": ["rise", "grow", "climb", "go up"],
    "increases": ["rises", "grows", "climbs", "goes up"],
    "increased": ["rose", "grew", "climbed", "went up"],
    "reduce": ["cut", "lower", "bring down", "shrink"],
    "reduces": ["cuts", "lowers", "brings down", "shrinks"],
    "reduced": ["cut", "lowered", "brought down", "shrank"],
    "decrease": ["drop", "fall", "go down"],
    "decreases": ["drops", "falls", "goes down"],
    "decreased": ["dropped", "fell", "went down"],
    "difficult": ["hard", "tough", "challenging", "tricky"],
    "difficulties": ["problems", "troubles", "hurdles", "snags"],
    "challenges": ["problems", "obstacles", "hurdles", "difficulties"],
    "challenge": ["problem", "obstacle", "hurdle", "difficulty"],
    "problem": ["issue", "difficulty", "trouble", "obstacle"],
    "problems": ["issues", "difficulties", "troubles", "obstacles"],
    "solution": ["answer", "fix", "way forward", "remedy"],
    "solutions": ["answers", "fixes", "remedies", "ways forward"],
    "approach": ["method", "way", "strategy", "tactic"],
    "approaches": ["methods", "ways", "strategies", "tactics"],
    "strategy": ["plan", "approach", "game plan", "scheme"],
    "strategies": ["plans", "approaches", "game plans"],
    "method": ["way", "approach", "technique", "means"],
    "methods": ["ways", "approaches", "techniques", "means"],
    "technique": ["method", "way", "approach"],
    "techniques": ["methods", "ways", "approaches"],
    "process": ["procedure", "method", "steps", "workflow"],
    "processes": ["procedures", "methods", "workflows"],
    "system": ["setup", "scheme", "structure", "framework"],
    "systems": ["setups", "structures", "frameworks"],
    "framework": ["structure", "system", "setup", "scheme"],
    "frameworks": ["structures", "systems", "setups"],
    "structure": ["setup", "framework", "organization", "makeup"],
    "structures": ["setups", "frameworks", "systems"],
    "benefit": ["advantage", "gain", "upside", "plus"],
    "benefits": ["advantages", "gains", "upsides", "pluses"],
    "advantage": ["benefit", "edge", "upside", "plus"],
    "advantages": ["benefits", "edges", "upsides", "pluses"],
    "drawback": ["downside", "disadvantage", "weakness", "catch"],
    "drawbacks": ["downsides", "disadvantages", "weaknesses", "catches"],
    "advantageous": ["helpful", "useful", "beneficial", "favorable"],
    "beneficial": ["helpful", "useful", "advantageous", "good"],
    "effective": ["efficient", "successful", "workable", "solid"],
    "ineffective": ["weak", "useless", "poor"],
    "efficient": ["effective", "productive", "streamlined"],
    "efficiently": ["effectively", "smoothly", "well"],
    "effectively": ["efficiently", "successfully", "well"],
    "necessary": ["needed", "essential", "required", "a must"],
    "essential": ["necessary", "vital", "crucial", "key"],
    "vital": ["essential", "crucial", "critical", "key"],
    "critical": ["crucial", "vital", "key", "decisive"],
    "crucial": ["critical", "vital", "key", "decisive"],
    "fundamental": ["basic", "core", "essential", "underlying"],
    "central": ["core", "main", "key", "principal"],
    "primary": ["main", "chief", "leading", "principal"],
    "main": ["primary", "chief", "principal", "leading"],
    "major": ["big", "large", "serious", "sizable"],
    "minor": ["small", "slight", "lesser", "modest"],
    "large": ["big", "substantial", "sizable", "considerable"],
    "small": ["little", "modest", "slight", "minor"],
    "big": ["large", "substantial", "major", "considerable"],
    "huge": ["enormous", "massive", "vast", "immense"],
    "enormous": ["huge", "massive", "vast"],
    "massive": ["huge", "enormous", "vast", "sizable"],
    "rapid": ["fast", "quick", "swift", "speedy"],
    "fast": ["quick", "rapid", "swift", "speedy"],
    "quick": ["fast", "rapid", "swift", "prompt"],
    "slow": ["gradual", "sluggish", "unhurried"],
    "gradual": ["slow", "step-by-step", "steady"],
    "sudden": ["abrupt", "sharp", "unexpected"],
    "abrupt": ["sudden", "sharp", "quick"],
    "new": ["fresh", "novel", "recent", "newer"],
    "novel": ["new", "fresh", "original", "unusual"],
    "original": ["initial", "first", "earliest", "source"],
    "modern": ["current", "present-day", "up-to-date", "contemporary"],
    "current": ["present", "existing", "ongoing", "today's"],
    "traditional": ["conventional", "classic", "old-school", "standard"],
    "conventional": ["traditional", "standard", "usual", "orthodox"],
    "standard": ["normal", "regular", "typical", "usual"],
    "typical": ["usual", "normal", "standard", "common"],
    "common": ["typical", "widespread", "usual", "frequent"],
    "rare": ["uncommon", "scarce", "seldom seen"],
    "unique": ["distinctive", "special", "one-of-a-kind", "singular"],
    "complex": ["complicated", "intricate", "involved", "layered"],
    "complicated": ["complex", "involved", "knotty", "convoluted"],
    "simple": ["easy", "straightforward", "plain", "basic"],
    "easy": ["simple", "straightforward", "effortless", "painless"],
    "difficult": ["hard", "tough", "tricky", "demanding"],
    "evident": ["clear", "obvious", "plain", "apparent"],
    "clear": ["evident", "obvious", "plain", "apparent"],
    "obvious": ["clear", "evident", "plain to see", "apparent"],
    "apparent": ["evident", "clear", "obvious", "visible"],
    "unclear": ["vague", "murky", "fuzzy", "ambiguous"],
    "vague": ["unclear", "fuzzy", "imprecise", "loose"],
    "precise": ["exact", "accurate", "spot-on", "specific"],
    "accurate": ["precise", "exact", "correct", "spot-on"],
    "correct": ["right", "accurate", "proper", "sound"],
    "wrong": ["incorrect", "mistaken", "off", "flawed"],
    "mistake": ["error", "slip", "misstep", "blunder"],
    "mistakes": ["errors", "slips", "missteps", "blunders"],
    "error": ["mistake", "slip", "fault", "blunder"],
    "errors": ["mistakes", "slips", "faults", "blunders"],
    "result": ["outcome", "consequence", "effect", "upshot"],
    "results": ["outcomes", "consequences", "effects", "findings"],
    "outcome": ["result", "consequence", "effect", "end product"],
    "outcomes": ["results", "consequences", "effects"],
    "consequence": ["result", "outcome", "effect", "aftermath"],
    "consequences": ["results", "outcomes", "effects", "repercussions"],
    "effect": ["impact", "result", "consequence", "influence"],
    "effects": ["impacts", "results", "consequences", "influences"],
    "impact": ["effect", "influence", "consequence", "bearing"],
    "impacts": ["effects", "influences", "consequences"],
    "influence": ["effect", "impact", "sway", "bearing"],
    "influences": ["effects", "impacts", "shapes"],
    "affected": ["influenced", "shaped", "touched", "impacted"],
    "affects": ["influences", "shapes", "touches", "impacts"],
    "affect": ["influence", "shape", "touch", "impact"],
    "influenced": ["affected", "shaped", "guided", "swayed"],
    "change": ["shift", "alteration", "transformation", "turn"],
    "changes": ["shifts", "alterations", "transformations"],
    "changed": ["shifted", "altered", "transformed", "turned"],
    "transform": ["change", "alter", "reshape", "convert"],
    "transformation": ["change", "shift", "overhaul", "makeover"],
    "development": ["growth", "progress", "advancement", "evolution"],
    "develop": ["grow", "advance", "build up", "evolve"],
    "develops": ["grows", "advances", "builds up", "evolves"],
    "developed": ["grew", "advanced", "built up", "evolved"],
    "growth": ["expansion", "development", "rise", "increase"],
    "progress": ["advancement", "headway", "development", "movement"],
    "advance": ["progress", "move forward", "push ahead"],
    "advancement": ["progress", "development", "headway"],
    "improvement": ["progress", "gains", "upgrading", "betterment"],
    "improvements": ["gains", "upgrades", "refinements"],
    "quality": ["caliber", "standard", "grade", "level"],
    "performance": ["output", "results", "showing", "effectiveness"],
    "achievement": ["accomplishment", "success", "attainment", "win"],
    "achievements": ["accomplishments", "successes", "wins"],
    "success": ["achievement", "win", "triumph", "victory"],
    "failure": ["shortcoming", "collapse", "breakdown", "defeat"],
    "failures": ["shortcomings", "breakdowns", "defeats"],
    "successes": ["wins", "achievements", "triumphs"],
    "goals": ["aims", "objectives", "targets", "purposes"],
    "purpose": ["goal", "aim", "intent", "point"],
    "aim": ["goal", "objective", "target", "intent"],
    "focus": ["emphasis", "attention", "concentration", "spotlight"],
    "focuses": ["concentrates", "centers", "zeroes in"],
    "focused": ["concentrated", "centered", "zeroed in", "honed in"],
    "requires": ["demands", "calls for", "needs", "takes"],
    "require": ["demand", "call for", "need", "take"],
    "required": ["needed", "demanded", "called for", "necessary"],
    "demands": ["requires", "calls for", "needs"],
    "demand": ["require", "call for", "need"],
    "needs": ["requires", "calls for", "wants", "must have"],
    "need": ["require", "call for", "want", "must have"],
    "needed": ["required", "necessary", "called for"],
    "provide": ["give", "supply", "offer", "deliver"],
    "provides": ["gives", "supplies", "offers", "delivers"],
    "provided": ["gave", "supplied", "offered", "delivered"],
    "supply": ["provide", "give", "deliver", "furnish"],
    "supplies": ["provides", "gives", "delivers", "furnishes"],
    "offer": ["provide", "give", "present", "extend"],
    "offers": ["provides", "gives", "presents", "extends"],
    "delivers": ["provides", "gives", "supplies", "brings"],
    "deliver": ["provide", "give", "supply", "bring"],
    "produces": ["generates", "creates", "yields", "makes"],
    "produce": ["generate", "create", "yield", "make"],
    "generated": ["produced", "created", "yielded", "made"],
    "generates": ["produces", "creates", "yields", "makes"],
    "generate": ["produce", "create", "yield", "make"],
    "includes": ["covers", "contains", "comprises", "involves"],
    "include": ["cover", "contain", "comprise", "involve"],
    "included": ["covered", "contained", "comprised", "involved"],
    "contains": ["includes", "holds", "comprises", "carries"],
    "involve": ["include", "entail", "require", "call for"],
    "involves": ["includes", "entails", "requires", "calls for"],
    "involved": ["included", "entailed", "required", "engaged"],
    "consider": ["think about", "weigh", "take into account", "mull over"],
    "considers": ["thinks about", "weighs", "takes into account"],
    "considered": ["thought about", "weighed", "took into account", "regarded"],
    "understand": ["grasp", "comprehend", "get", "see"],
    "understands": ["grasps", "comprehends", "gets", "sees"],
    "understood": ["grasped", "comprehended", "got", "saw"],
    "understanding": ["grasp", "comprehension", "insight", "takeaway"],
    "know": ["realize", "recognize", "be aware"],
    "knows": ["realizes", "recognizes", "is aware"],
    "knew": ["realized", "recognized", "was aware"],
    "realize": ["recognize", "understand", "see", "come to see"],
    "recognize": ["realize", "acknowledge", "see", "admit"],
    "acknowledge": ["recognize", "admit", "accept", "concede"],
    "reveal": ["show", "disclose", "expose", "uncover"],
    "reveals": ["shows", "discloses", "exposes", "uncovers"],
    "revealed": ["showed", "disclosed", "exposed", "uncovered"],
    "disclose": ["reveal", "show", "make known", "share"],
    "expose": ["reveal", "uncover", "lay bare", "show"],
    "emphasize": ["stress", "highlight", "underline", "point up"],
    "emphasizes": ["stresses", "highlights", "underscores", "points up"],
    "emphasized": ["stressed", "highlighted", "underscored", "pointed up"],
    "highlight": ["stress", "underline", "emphasize", "flag"],
    "highlights": ["stresses", "underlines", "emphasizes", "flags"],
    "highlighted": ["stressed", "underlined", "emphasized", "flagged"],
    "support": ["back", "back up", "bolster", "shore up"],
    "supports": ["backs", "backs up", "bolsters", "shores up"],
    "supported": ["backed", "backed up", "bolstered"],
    "suggest": ["imply", "indicate", "hint at", "point to"],
    "suggests": ["implies", "indicates", "hints at", "points to"],
    "suggested": ["implied", "indicated", "hinted at", "pointed to"],
    "indicate": ["suggest", "show", "signal", "point to"],
    "indicates": ["suggests", "shows", "signals", "points to"],
    "indicated": ["suggested", "showed", "signaled", "pointed to"],
    "ensure": ["make sure", "guarantee", "see to it", "secure"],
    "ensures": ["makes sure", "guarantees", "sees to it"],
    "ensured": ["made sure", "guaranteed", "saw to it"],
    "maintain": ["keep up", "sustain", "preserve", "hold"],
    "maintains": ["keeps up", "sustains", "preserves", "holds"],
    "maintained": ["kept up", "sustained", "preserved", "held"],
    "achieve": ["reach", "attain", "accomplish", "pull off"],
    "achieves": ["reaches", "attains", "accomplishes", "pulls off"],
    "achieved": ["reached", "attained", "accomplished", "pulled off"],
    "gain": ["obtain", "get", "acquire", "earn"],
    "gains": ["obtains", "gets", "acquires", "earns"],
    "gained": ["obtained", "got", "acquired", "earned"],
    "obtain": ["get", "gain", "acquire", "secure"],
    "obtains": ["gets", "gains", "acquires", "secures"],
    "acquire": ["get", "gain", "obtain", "pick up"],
    "acquires": ["gets", "gains", "obtains", "picks up"],
    "however": ["still", "yet", "even so", "that said"],
    "therefore": ["so", "as a result", "thus", "because of that"],
    "thus": ["so", "therefore", "as a result", "hence"],
    "hence": ["so", "therefore", "as a result", "that's why"],
    "because": ["since", "as", "given that", "for the simple reason that"],
    "although": ["though", "even though", "while", "granted"],
    "though": ["although", "even though", "while"],
    "while": ["although", "whereas", "even as", "as"],
    "whereas": ["while", "although", "but", "compared to where"],
    "despite": ["in spite of", "even with", "regardless of"],
    "instead": ["rather", "in place of that", "alternatively"],
    "rather": ["instead", "preferably", "more accurately"],
    "particularly": ["especially", "notably", "mainly", "above all"],
    "especially": ["particularly", "mainly", "notably", "above all"],
    "primarily": ["mainly", "chiefly", "mostly", "largely"],
    "mainly": ["primarily", "mostly", "chiefly", "largely"],
    "mostly": ["mainly", "largely", "for the most part", "primarily"],
    "usually": ["typically", "generally", "normally", "as a rule"],
    "generally": ["usually", "typically", "broadly", "by and large"],
    "typically": ["usually", "normally", "generally", "as a rule"],
    "often": ["frequently", "regularly", "a lot", "time and again"],
    "frequently": ["often", "regularly", "repeatedly", "time and again"],
    "sometimes": ["at times", "now and then", "occasionally", "every so often"],
    "occasionally": ["sometimes", "at times", "now and then", "every so often"],
    "always": ["invariably", "at all times", "every time", "without exception"],
    "never": ["not once", "at no point", "at no time"],
    "currently": ["right now", "at present", "these days", "now"],
    "presently": ["currently", "right now", "at the moment"],
    "recently": ["lately", "of late", "not long ago", "just now"],
    "eventually": ["in the end", "finally", "sooner or later", "at some point"],
    "finally": ["in the end", "eventually", "at last", "ultimately"],
    "immediately": ["right away", "at once", "straightaway", "on the spot"],
    "quickly": ["fast", "rapidly", "swiftly", "in short order"],
    "slowly": ["gradually", "steadily", "at a slow pace", "bit by bit"],
    "carefully": ["cautiously", "with care", "methodically", "attentively"],
    "significantly": ["markedly", "substantially", "considerably", "to a real degree"],
    "substantially": ["significantly", "considerably", "markedly", "greatly"],
    "considerably": ["substantially", "significantly", "greatly", "markedly"],
    "slightly": ["somewhat", "a bit", "marginally", "a little"],
    "somewhat": ["slightly", "a bit", "to some degree", "rather"],
    "extremely": ["very", "highly", "incredibly", "exceptionally"],
    "highly": ["very", "extremely", "notably", "markedly"],
    "absolutely": ["completely", "entirely", "totally", "wholly"],
    "completely": ["entirely", "totally", "fully", "wholly"],
    "entirely": ["completely", "totally", "wholly", "in full"],
    "totally": ["completely", "entirely", "wholly", "utterly"],
    "nearly": ["almost", "practically", "just about", "close to"],
    "almost": ["nearly", "practically", "just about", "virtually"],
    "approximately": ["about", "roughly", "around"],
    "appear": ["seem", "look", "come across as"],
    "appears": ["seems", "looks", "comes across as"],
    "appeared": ["seemed", "looked", "came across as"],
    "seem": ["appear", "look", "come across as"],
    "seems": ["appears", "looks", "comes across as"],
    "seemed": ["appeared", "looked", "came across as"],
    "believe": ["think", "hold", "reckon", "suspect"],
    "believes": ["thinks", "holds", "reckons", "suspects"],
    "believed": ["thought", "held", "reckoned", "suspected"],
    "think": ["believe", "reckon", "figure", "feel"],
    "thinks": ["believes", "reckons", "figures", "feels"],
    "thought": ["believed", "reckoned", "figured", "felt"],
    "argue": ["claim", "contend", "hold", "maintain"],
    "argues": ["claims", "contends", "holds", "maintains"],
    "argued": ["claimed", "contended", "held", "maintained"],
    "claim": ["argue", "contend", "assert", "maintain"],
    "claims": ["argues", "contends", "asserts", "maintains"],
    "claimed": ["argued", "contended", "asserted", "maintained"],
    "assert": ["claim", "contend", "state", "maintain"],
    "asserts": ["claims", "contends", "states", "maintains"],
    "state": ["say", "note", "mention", "declare"],
    "states": ["says", "notes", "mentions", "declares"],
    "stated": ["said", "noted", "mentioned", "declared"],
    "note": ["observe", "point out", "mention", "remark"],
    "notes": ["observes", "points out", "mentions", "remarks"],
    "observed": ["noted", "noticed", "saw", "remarked"],
    "observe": ["note", "notice", "see", "remark"],
    "observes": ["notes", "notices", "sees", "remarks"],
    "examines": ["looks at", "studies", "investigates", "analyzes"],
    "examine": ["look at", "study", "investigate", "analyze"],
    "examined": ["looked at", "studied", "investigated", "analyzed"],
    "study": ["examine", "look at", "investigate", "analyze"],
    "studies": ["examines", "looks at", "investigates", "analyzes"],
    "studied": ["examined", "looked at", "investigated", "analyzed"],
    "investigate": ["examine", "study", "look into", "probe"],
    "investigates": ["examines", "studies", "looks into", "probes"],
    "investigated": ["examined", "studied", "looked into", "probed"],
    "explore": ["examine", "look into", "investigate", "dig into"],
    "explores": ["examines", "looks into", "investigates", "digs into"],
    "explored": ["examined", "looked into", "investigated", "dug into"],
    "analyze": ["examine", "study", "break down", "dissect"],
    "analyzes": ["examines", "studies", "breaks down", "dissects"],
    "analyzed": ["examined", "studied", "broke down", "dissected"],
    "assess": ["evaluate", "judge", "gauge", "measure"],
    "assesses": ["evaluates", "judges", "gauges", "measures"],
    "assessed": ["evaluated", "judged", "gauged", "measured"],
    "evaluate": ["assess", "judge", "gauge", "weigh"],
    "evaluates": ["assesses", "judges", "gauges", "weighs"],
    "evaluated": ["assessed", "judged", "gauged", "weighed"],
    "measure": ["gauge", "assess", "evaluate", "quantify"],
    "measures": ["gauges", "assesses", "evaluates", "quantifies"],
    "measured": ["gauged", "assessed", "evaluated", "quantified"],
    "factor": ["element", "aspect", "component", "piece"],
    "factors": ["elements", "aspects", "components", "pieces"],
    "element": ["component", "part", "piece", "aspect"],
    "elements": ["components", "parts", "pieces", "aspects"],
    "aspect": ["element", "facet", "angle", "side"],
    "aspects": ["elements", "facets", "angles", "sides"],
    "component": ["element", "part", "piece", "building block"],
    "components": ["elements", "parts", "pieces", "building blocks"],
    "feature": ["trait", "characteristic", "quality", "hallmark"],
    "features": ["traits", "characteristics", "qualities", "hallmarks"],
    "characteristic": ["trait", "feature", "quality", "attribute"],
    "characteristics": ["traits", "features", "qualities", "attributes"],
    "attribute": ["trait", "characteristic", "feature", "quality"],
    "attributes": ["traits", "characteristics", "features", "qualities"],
    "role": ["part", "function", "job", "position"],
    "roles": ["parts", "functions", "jobs", "positions"],
    "function": ["role", "purpose", "job", "task"],
    "functions": ["roles", "purposes", "jobs", "tasks"],
    "part": ["piece", "portion", "segment", "share"],
    "parts": ["pieces", "portions", "segments", "shares"],
    "area": ["field", "domain", "sphere", "zone"],
    "areas": ["fields", "domains", "spheres", "zones"],
    "field": ["area", "domain", "sphere", "sector"],
    "fields": ["areas", "domains", "spheres", "sectors"],
    "domain": ["area", "field", "sphere", "realm"],
    "domains": ["areas", "fields", "spheres"],
    "sector": ["area", "field", "industry", "segment"],
    "sectors": ["areas", "fields", "industries", "segments"],
    "topic": ["subject", "theme", "issue", "matter"],
    "topics": ["subjects", "themes", "issues", "matters"],
    "subject": ["topic", "theme", "issue", "matter"],
    "subjects": ["topics", "themes", "issues", "matters"],
    "theme": ["topic", "subject", "motif", "thread"],
    "themes": ["topics", "subjects", "motifs", "threads"],
    "issue": ["matter", "question", "concern", "problem"],
    "issues": ["matters", "questions", "concerns", "problems"],
    "matter": ["issue", "concern", "question", "affair"],
    "matters": ["issues", "concerns", "questions", "affairs"],
    "concern": ["worry", "issue", "matter", "anxiety"],
    "concerns": ["worries", "issues", "matters", "anxieties"],
    "leader": ["chief", "head", "boss", "top official"],
    "leaders": ["chiefs", "heads", "bosses", "top officials"],
    "leadership": ["command", "direction", "stewardship", "guidance"],
    "organization": ["institution", "body", "entity", "outfit"],
    "organizations": ["institutions", "bodies", "entities", "outfits"],
    "institution": ["organization", "body", "establishment", "entity"],
    "institutions": ["organizations", "bodies", "establishments", "entities"],
    "company": ["firm", "business", "enterprise", "outfit"],
    "companies": ["firms", "businesses", "enterprises", "outfits"],
    "business": ["company", "firm", "enterprise", "operation"],
    "businesses": ["companies", "firms", "enterprises", "operations"],
    "enterprise": ["company", "firm", "venture", "business"],
    "enterprises": ["companies", "firms", "ventures", "businesses"],
    "student": ["learner", "pupil", "trainee"],
    "students": ["learners", "pupils", "trainees"],
    "teacher": ["instructor", "educator", "tutor", "lecturer"],
    "teachers": ["instructors", "educators", "tutors", "lecturers"],
    "employee": ["worker", "staff member", "team member", "personnel"],
    "employees": ["workers", "staff members", "team members", "personnel"],
    "worker": ["employee", "staffer", "team member", "laborer"],
    "workers": ["employees", "staffers", "team members", "laborers"],
    "manager": ["supervisor", "boss", "administrator", "chief"],
    "managers": ["supervisors", "bosses", "administrators", "chiefs"],
    "customer": ["client", "patron", "buyer", "consumer"],
    "customers": ["clients", "patrons", "buyers", "consumers"],
    "client": ["customer", "patron", "buyer", "account"],
    "clients": ["customers", "patrons", "buyers", "accounts"],
    "consumer": ["customer", "buyer", "user", "shopper"],
    "consumers": ["customers", "buyers", "users", "shoppers"],
    "user": ["consumer", "customer", "person", "individual"],
    "users": ["consumers", "customers", "people", "individuals"],
    "person": ["individual", "human being", "someone", "soul"],
    "people": ["individuals", "folks", "persons", "men and women"],
    "individual": ["person", "human being", "someone", "party"],
    "individuals": ["people", "persons", "folks", "human beings"],
    "society": ["community", "the public", "social order", "culture"],
    "communities": ["neighborhoods", "societies", "local areas", "circles"],
    "community": ["neighborhood", "society", "local area", "circle"],
    "government": ["administration", "authority", "state", "regime"],
    "economy": ["economic system", "market", "financial system"],
    "market": ["marketplace", "sector", "arena", "trading ground"],
    "markets": ["marketplaces", "sectors", "arenas"],
    "industry": ["sector", "trade", "business", "line of work"],
    "industries": ["sectors", "trades", "businesses", "lines of work"],
    "technology": ["tech", "technical systems", "innovation"],
    "innovation": ["fresh ideas", "invention", "new approaches"],
    "innovations": ["inventions", "breakthroughs", "novelties", "new developments"],
    "research": ["study", "investigation", "inquiry", "fieldwork"],
    "data": ["figures", "numbers", "information", "statistics"],
    "information": ["data", "details", "facts", "material"],
    "knowledge": ["understanding", "expertise", "know-how", "insight"],
    "skill": ["ability", "competence", "talent", "knack"],
    "skills": ["abilities", "competencies", "talents", "knacks"],
    "ability": ["capacity", "capability", "skill", "knack"],
    "abilities": ["capacities", "capabilities", "skills", "knacks"],
    "capacity": ["ability", "capability", "room", "potential"],
    "capacities": ["abilities", "capabilities", "potentials"],
    "opportunity": ["chance", "opening", "possibility", "shot"],
    "opportunities": ["chances", "openings", "possibilities", "shots"],
    "chance": ["opportunity", "possibility", "shot", "odds"],
    "possibility": ["chance", "prospect", "option", "likelihood"],
    "possibilities": ["chances", "prospects", "options", "likelihoods"],
    "risk": ["danger", "threat", "hazard", "exposure"],
    "risks": ["dangers", "threats", "hazards", "exposures"],
    "threat": ["danger", "risk", "hazard", "menace"],
    "threats": ["dangers", "risks", "hazards", "menaces"],
    "danger": ["threat", "risk", "hazard", "peril"],
    "dangers": ["threats", "risks", "hazards", "perils"],
    "trend": ["pattern", "movement", "direction", "drift"],
    "trends": ["patterns", "movements", "directions", "drifts"],
    "pattern": ["trend", "shape", "arrangement", "motif"],
    "patterns": ["trends", "shapes", "arrangements", "motifs"],
    "example": ["instance", "case", "sample", "illustration"],
    "examples": ["instances", "cases", "samples", "illustrations"],
    "instance": ["example", "case", "occurrence", "sample"],
    "instances": ["examples", "cases", "occurrences", "samples"],
    "case": ["instance", "example", "situation", "scenario"],
    "cases": ["instances", "examples", "situations", "scenarios"],
    "situation": ["scenario", "circumstance", "condition", "state of affairs"],
    "situations": ["scenarios", "circumstances", "conditions"],
    "scenario": ["situation", "case", "circumstance", "state of play"],
    "scenarios": ["situations", "cases", "circumstances"],
    "condition": ["state", "situation", "status", "shape"],
    "conditions": ["states", "situations", "circumstances"],
    "environment": ["setting", "surroundings", "context", "milieu"],
    "environments": ["settings", "surroundings", "contexts", "milieus"],
    "context": ["setting", "background", "framework", "circumstances"],
    "contexts": ["settings", "backgrounds", "frameworks", "circumstances"],
    "perspective": ["viewpoint", "view", "angle", "standpoint"],
    "perspectives": ["viewpoints", "views", "angles", "standpoints"],
    "viewpoint": ["perspective", "view", "angle", "standpoint"],
    "view": ["perspective", "viewpoint", "angle", "take"],
    "views": ["perspectives", "viewpoints", "angles", "takes"],
    "opinion": ["view", "belief", "stance", "position"],
    "opinions": ["views", "beliefs", "stances", "positions"],
    "idea": ["notion", "concept", "thought", "conception"],
    "ideas": ["notions", "concepts", "thoughts", "conceptions"],
    "concept": ["idea", "notion", "principle", "construct"],
    "concepts": ["ideas", "notions", "principles", "constructs"],
    "notion": ["idea", "concept", "belief", "impression"],
    "notions": ["ideas", "concepts", "beliefs", "impressions"],
    "principle": ["rule", "tenet", "standard", "guideline"],
    "principles": ["rules", "tenets", "standards", "guidelines"],
    "rule": ["regulation", "principle", "norm", "guideline"],
    "rules": ["regulations", "principles", "norms", "guidelines"],
    "regulation": ["rule", "law", "directive", "ordinance"],
    "regulations": ["rules", "laws", "directives", "ordinances"],
    "policy": ["guideline", "rule", "strategy", "line"],
    "policies": ["guidelines", "rules", "strategies", "lines"],
    "practice": ["custom", "routine", "habit", "procedure"],
    "practices": ["customs", "routines", "habits", "procedures"],
    "methodology": ["method", "approach", "system", "procedure"],
    "methodologies": ["methods", "approaches", "systems", "procedures"],
    "analysis": ["examination", "study", "review", "assessment"],
    "analyses": ["examinations", "studies", "reviews", "assessments"],
    "review": ["examination", "assessment", "look at", "appraisal"],
    "reviews": ["examinations", "assessments", "appraisals"],
    "assessment": ["evaluation", "appraisal", "review", "judgment"],
    "assessments": ["evaluations", "appraisals", "reviews", "judgments"],
    "evaluation": ["assessment", "appraisal", "review", "judgment"],
    "evaluations": ["assessments", "appraisals", "reviews", "judgments"],
    "reason": ["cause", "basis", "grounds", "explanation"],
    "reasons": ["causes", "bases", "grounds", "explanations"],
    "cause": ["reason", "source", "origin", "root"],
    "causes": ["reasons", "sources", "origins", "roots"],
    "source": ["origin", "root", "basis", "wellspring"],
    "sources": ["origins", "roots", "bases", "wellsprings"],
    "origin": ["source", "root", "beginning", "starting point"],
    "origins": ["sources", "roots", "beginnings", "starting points"],
    "beginning": ["start", "outset", "onset", "origin"],
    "beginnings": ["starts", "outsets", "onsets", "origins"],
    "start": ["beginning", "outset", "kickoff", "launch"],
    "starts": ["begins", "commences", "kicks off", "launches"],
    "end": ["conclusion", "finish", "outcome"],
    "ends": ["conclusions", "finishes", "closes", "wrap-ups"],
    "conclusion": ["end", "finish", "close", "outcome"],
    "conclusions": ["ends", "finishes", "closes", "outcomes"],
    "summary": ["recap", "overview", "round-up", "digest"],
    "summaries": ["recaps", "overviews", "digests"],
    "overview": ["summary", "recap", "big picture", "outline"],
    "overviews": ["summaries", "recaps", "outlines"],
    "outline": ["sketch", "overview", "framework"],
    "outlines": ["sketches", "overviews", "frameworks"],
    "detail": ["particular", "specific", "nuance", "fine point"],
    "details": ["particulars", "specifics", "nuances", "fine points"],
    "particular": ["specific", "certain", "given", "distinct"],
    "particulars": ["details", "specifics", "nuances", "fine points"],
    "point": ["aspect", "issue", "matter"],
    "points": ["aspects", "issues", "items", "matters"],
    "goal": ["aim", "objective", "target", "end goal"],
    "target": ["goal", "objective", "aim", "mark"],
    "targets": ["goals", "objectives", "aims", "marks"],
    "objective": ["goal", "aim", "target", "purpose"],
    "plan": ["strategy", "scheme", "blueprint", "road map"],
    "plans": ["strategies", "schemes", "blueprints", "road maps"],
    "program": ["initiative", "scheme", "effort", "plan"],
    "programs": ["initiatives", "schemes", "efforts", "plans"],
    "project": ["initiative", "undertaking", "effort", "scheme"],
    "projects": ["initiatives", "undertakings", "efforts", "schemes"],
    "initiative": ["program", "project", "effort", "drive"],
    "initiatives": ["programs", "projects", "efforts", "drives"],
    "effort": ["attempt", "push", "drive", "work"],
    "efforts": ["attempts", "pushes", "drives", "work"],
    "attempt": ["effort", "try", "bid", "push"],
    "attempts": ["efforts", "tries", "bids", "pushes"],
    "try": ["attempt", "effort", "bid", "shot"],
    "tries": ["attempts", "efforts", "bids", "shots"],
    "way": ["manner", "means", "method", "route"],
    "ways": ["manners", "means", "methods", "routes"],
    "means": ["method", "way", "manner", "channel"],
    "manner": ["way", "means", "fashion", "style"],
    "fashion": ["manner", "way", "style", "mode"],
    "style": ["manner", "approach", "fashion", "mode"],
    "type": ["kind", "sort", "category", "variety"],
    "types": ["kinds", "sorts", "categories", "varieties"],
    "kind": ["type", "sort", "category", "variety"],
    "kinds": ["types", "sorts", "categories", "varieties"],
    "sort": ["type", "kind", "category", "breed"],
    "sorts": ["types", "kinds", "categories", "breeds"],
    "category": ["type", "kind", "class", "group"],
    "categories": ["types", "kinds", "classes", "groups"],
    "class": ["category", "type", "group", "bracket"],
    "classes": ["categories", "types", "groups", "brackets"],
    "group": ["cluster", "set", "category", "batch"],
    "groups": ["clusters", "sets", "categories", "batches"],
    "set": ["group", "collection", "series", "batch"],
    "sets": ["groups", "collections", "series", "batches"],
    "collection": ["set", "group", "series", "gathering"],
    "collections": ["sets", "groups", "series", "gatherings"],
    "series": ["sequence", "set", "chain", "run"],
    "sequence": ["series", "order", "chain", "progression"],
    "order": ["sequence", "arrangement", "order of things", "pecking order"],
    "level": ["tier", "grade", "stage", "degree"],
    "levels": ["tiers", "grades", "stages", "degrees"],
    "stage": ["phase", "step", "level", "point"],
    "stages": ["phases", "steps", "levels", "points"],
    "phase": ["stage", "period", "step", "chapter"],
    "phases": ["stages", "periods", "steps", "chapters"],
    "step": ["stage", "phase", "move", "measure"],
    "steps": ["stages", "phases", "moves", "measures"],
    "measure": ["step", "action", "move", "initiative"],
    "measures": ["steps", "actions", "moves", "initiatives"],
    "action": ["step", "move", "measure", "initiative"],
    "actions": ["steps", "moves", "measures", "initiatives"],
    "activity": ["task", "undertaking", "exercise", "operation"],
    "activities": ["tasks", "undertakings", "exercises", "operations"],
    "task": ["job", "assignment", "duty", "chore"],
    "tasks": ["jobs", "assignments", "duties", "chores"],
    "job": ["task", "role", "position", "post"],
    "jobs": ["tasks", "roles", "positions", "posts"],
    "duty": ["responsibility", "obligation", "task", "charge"],
    "duties": ["responsibilities", "obligations", "tasks", "charges"],
    "responsibility": ["duty", "obligation", "charge", "burden"],
    "responsibilities": ["duties", "obligations", "charges", "burdens"],
    "obligation": ["duty", "responsibility", "commitment", "requirement"],
    "obligations": ["duties", "responsibilities", "commitments", "requirements"],
    "commitment": ["dedication", "obligation", "pledge", "promise"],
    "commitments": ["dedications", "pledges", "promises"],
    "dedication": ["commitment", "devotion", "loyalty", "diligence"],
    "motivation": ["drive", "drive to act", "impetus", "motive"],
    "motivated": ["driven", "inspired", "energized", "stirred"],
    "inspire": ["motivate", "encourage", "spark", "galvanize"],
    "inspires": ["motivates", "encourages", "sparks", "galvanizes"],
    "encourage": ["motivate", "urge", "spur", "back"],
    "encourages": ["motivates", "urges", "spurs", "backs"],
    "discourage": ["deter", "put off", "dishearten"],
    "discourages": ["deters", "puts off", "disheartens"],
    "attitude": ["mindset", "outlook", "stance", "posture"],
    "attitudes": ["mindsets", "outlooks", "stances", "postures"],
    "mindset": ["attitude", "outlook", "mentality", "frame of mind"],
    "mindsets": ["attitudes", "outlooks", "mentalities"],
    "outlook": ["perspective", "attitude", "view", "mindset"],
    "outlooks": ["perspectives", "attitudes", "views", "mindsets"],
    "behavior": ["conduct", "actions", "habits", "manner"],
    "behaviors": ["conducts", "habits", "manners"],
    "habit": ["routine", "practice", "custom", "pattern"],
    "habits": ["routines", "practices", "customs", "patterns"],
    "routine": ["habit", "practice", "schedule", "custom"],
    "routines": ["habits", "practices", "schedules", "customs"],
    "culture": ["values", "ethos", "environment", "traditions"],
    "values": ["standards", "principles", "beliefs", "ideals"],
    "belief": ["conviction", "view", "faith", "creed"],
    "beliefs": ["convictions", "views", "faiths", "creeds"],
    "conviction": ["belief", "certainty", "faith", "persuasion"],
    "convictions": ["beliefs", "certainties", "faiths"],
    "worth": ["value", "merit", "usefulness", "benefit"],
    "value": ["worth", "merit", "usefulness", "benefit"],
    "values": ["worths", "merits", "usefulness", "benefits"],
    "merit": ["worth", "value", "strength", "virtue"],
    "merits": ["worths", "values", "strengths", "virtues"],
    "strength": ["strong point", "asset", "advantage", "forte"],
    "strengths": ["strong points", "assets", "advantages", "fortes"],
    "weakness": ["shortcoming", "failing", "flaw", "soft spot"],
    "weaknesses": ["shortcomings", "failings", "flaws", "soft spots"],
    "flaw": ["defect", "fault", "weakness", "shortcoming"],
    "flaws": ["defects", "faults", "weaknesses", "shortcomings"],
    "defect": ["flaw", "fault", "imperfection", "blemish"],
    "defects": ["flaws", "faults", "imperfections", "blemishes"],
    "problem": ["issue", "difficulty", "trouble", "obstacle"],
    "obstacle": ["barrier", "hurdle", "block", "roadblock"],
    "obstacles": ["barriers", "hurdles", "blocks", "roadblocks"],
    "barrier": ["obstacle", "block", "hurdle", "wall"],
    "barriers": ["obstacles", "blocks", "hurdles", "walls"],
    "hurdle": ["obstacle", "barrier", "block", "snag"],
    "hurdles": ["obstacles", "barriers", "blocks", "snags"],
    "limitation": ["constraint", "restriction", "drawback", "limit"],
    "limitations": ["constraints", "restrictions", "drawbacks", "limits"],
    "constraint": ["limitation", "restriction", "limit", "boundary"],
    "constraints": ["limitations", "restrictions", "limits", "boundaries"],
    "restriction": ["limitation", "constraint", "rule", "cap"],
    "restrictions": ["limitations", "constraints", "rules", "caps"],
    "limit": ["cap", "restriction", "bound", "ceiling"],
    "limits": ["caps", "restrictions", "bounds", "ceilings"],
    "boundary": ["border", "edge", "limit", "line"],
    "boundaries": ["borders", "edges", "limits", "lines"],
    "border": ["boundary", "edge", "frontier", "margin"],
    "borders": ["boundaries", "edges", "frontiers", "margins"],
    "edge": ["border", "boundary", "margin", "rim"],
    "edges": ["borders", "boundaries", "margins", "rims"],
    "potential": ["promise", "capability", "capacity", "prospects"],
    "capability": ["capacity", "ability", "competence", "power"],
    "capabilities": ["capacities", "abilities", "competencies", "powers"],
    "power": ["strength", "force", "authority", "might"],
    "powers": ["strengths", "forces", "authorities", "might"],
    "force": ["power", "strength", "energy", "driving force"],
    "forces": ["powers", "strengths", "energies"],
    "energy": ["vigor", "drive", "vitality", "strength"],
    "vitality": ["energy", "vigor", "liveliness", "life"],
    "vigor": ["energy", "vitality", "force", "spirit"],
    "spirit": ["vitality", "drive", "morale", "essence"],
    "morale": ["spirit", "drive", "motivation", "mood"],
    "mood": ["spirit", "atmosphere", "temper", "vibe"],
    "atmosphere": ["mood", "ambience", "environment", "feel"],
    "ambience": ["atmosphere", "mood", "feel", "setting"],
    "environment": ["setting", "surroundings", "context", "milieu"],
    "quality": ["caliber", "standard", "grade", "level"],
    "feature": ["trait", "characteristic", "quality", "hallmark"],
}

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

PROTECTED_COMPOUNDS = [
    "machine learning", "artificial intelligence", "deep learning",
    "higher education", "real estate", "human resources", "public health",
    "climate change", "social media", "supply chain", "best practices",
    "critical thinking", "problem solving", "workforce development",
    "professional development", "data science", "natural language",
    "common sense", "civil rights", "human rights", "law enforcement",
    "health care", "quality control", "research and development",
]

def _flip_synonyms(text, rng, strength):
    """Single-pass synonym flip: each word flipped at most once (no chained
    replacements). Multiword compounds are masked out first."""
    for i, comp in enumerate(PROTECTED_COMPOUNDS):
        text = text.replace(comp, "\x00%d\x00" % i)
    keys = sorted(SYN_DICT.keys(), key=len, reverse=True)
    pattern = re.compile(r'\b(' + '|'.join(re.escape(k) for k in keys) + r')\b', re.I)
    def repl(match):
        word = match.group(0)
        key = word.lower()
        options = SYN_DICT.get(key)
        if not options or rng.random() > strength:
            return word
        choice = rng.choice(options)
        if not choice:
            return word
        if word[0].isupper():
            return choice[0].upper() + choice[1:]
        return choice
    out = pattern.sub(repl, text)
    for i, comp in enumerate(PROTECTED_COMPOUNDS):
        out = out.replace("\x00%d\x00" % i, comp)
    return out

_CONNECT = [', and ', ', but ', ', so ', ', yet ', '; ', ', which means ', ' — ', ', though ', ', even so, ', ', still, ', ' — and ']

class _ConnDeck:
    def __init__(self, rng):
        self.rng = rng; self.deck = []
    def draw(self, avoid=None):
        if not self.deck:
            self.deck = self.rng.sample(_CONNECT, len(_CONNECT))
        c = self.deck.pop()
        if avoid and c == avoid and self.deck:
            self.deck.insert(0, c); c = self.deck.pop()
        return c

def _restructure_sentences(sents, rng, strength):
    """Aggressive burstiness: force sentence lengths into an irregular,
    heavy-tailed rhythm. Target lengths are drawn from a deliberately
    uneven profile so the output alternates staccato bursts and long runs."""
    deck = _ConnDeck(rng)
    last_conn = None
    out = []
    i = 0
    while i < len(sents):
        s = sents[i]
        words = s.split()

        # split overly long sentences at the best available break point
        if len(words) > 26 and rng.random() < strength:
            breaks = [m.start() for m in re.finditer(r'[,;:]\s', s)]
            if len(words) > 40:
                breaks += [m.start() for m in re.finditer(r'\s(?:and|but|so|because|which|while|although|whereas|however|therefore|thus|meanwhile)\s', ' ' + s)]
            if breaks:
                mid = min(breaks, key=lambda c: abs(c - len(s)//2))
                a, b = s[:mid].strip().rstrip(',;:'), s[mid:].strip().lstrip(',;: ')
                if a and b and len(a.split()) > 4 and len(b.split()) > 4:
                    b = b[0].upper() + b[1:]
                    if not b.endswith(('.','!','?')):
                        b += '.'
                    out.append(a if a.endswith(('.','!','?')) else a + '.')
                    out.append(b)
                    i += 1
                    continue

        # aggressively merge short-sentence runs: keep rolling until target reached
        if len(words) < 22 and i + 1 < len(sents) and rng.random() < strength:
            merged = s
            merged_n = len(words)
            j = i + 1
            while j < len(sents):
                nxt = sents[j]
                n_nxt = len(nxt.split())
                if merged_n + n_nxt > 26:
                    break
                if rng.random() < strength * 0.85:
                    # if next sentence already opens with a discourse adverb, don't
                    # stack another connector on top ("even so, even so,")
                    if nxt.lower().startswith(('even so', 'even though', 'that said', 'still,', 'though')):
                        conn = deck.draw(avoid=', even so,')
                    else:
                        conn = deck.draw(avoid=last_conn)
                    last_conn = conn
                    merged = merged.rstrip('.!?') + conn + nxt[0].lower() + nxt[1:]
                    merged_n += n_nxt
                    j += 1
                else:
                    break
            if j > i + 1:
                out.append(merged if merged.endswith(('.','!','?')) else merged + '.')
                i = j
                continue

        out.append(s)
        i += 1

    # second pass: fuse any remaining adjacent sub-10-word sentences
    final = []
    k = 0
    while k < len(out):
        if (k + 1 < len(out) and len(out[k].split()) < 10
                and rng.random() < strength * 0.8):
            nxt = out[k+1]
            if nxt.lower().startswith(('even so', 'even though', 'that said', 'still,', 'though')):
                conn = deck.draw(avoid=', even so,')
            else:
                conn = deck.draw()
            fused = out[k].rstrip('.!?') + conn + nxt[0].lower() + nxt[1:]
            final.append(fused if fused.endswith(('.','!','?')) else fused + '.')
            k += 2
        else:
            final.append(out[k])
            k += 1
    # enforcement pass: guarantee real spread between shortest and longest
    def _lens(lst):
        return [len(s.split()) for s in lst]
    guard = 0
    while guard < 6:
        lens = _lens(final)
        if not lens or (max(lens) - min(lens)) >= 12 or not any(l > 13 for l in lens):
            break
        idx = max(range(len(final)), key=lambda j: len(final[j].split()))
        s = final[idx]
        breaks = [m.start() for m in re.finditer(r'[,;:—]\s', s)]
        breaks += [m.start() for m in re.finditer(r'\s(?:and|but|so|because|which|while|although|however|even so|though)\s', s)]
        if not breaks:
            break
        mid = min(breaks, key=lambda c: abs(c - len(s)//2))
        a, b = s[:mid].strip().rstrip(',;:—'), s[mid:].strip().lstrip(',;:— ')
        if not (a and b and len(a.split()) > 3 and len(b.split()) > 3):
            break
        b = b[0].upper() + b[1:]
        if not b.endswith(('.','!','?')):
            b += '.'
        final[idx] = a if a.endswith(('.','!','?')) else a + '.'
        final.insert(idx+1, b)
        guard += 1
    return final

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
    text = _flip_synonyms(text, rng, strength)
    text = _apply_contractions(text, rng, strength)
    sents = _sentence_split(text)
    sents = _restructure_sentences(sents, rng, strength)
    text = ' '.join(sents)
    text = _casualize(text, rng, strength)
    text = _vary_rhythm(text, rng)
    text = _recapitalize(text)
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
