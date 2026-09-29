import re
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory

# Initialize Sastrawi stemmer and stopword remover
factory_stemmer = StemmerFactory()
stemmer = factory_stemmer.create_stemmer()

# Abbreviation mapping for modern Indonesian slang
ABBREVIATIONS = {
    "ga": "tidak",
    "engga": "tidak",
    "ngga": "tidak",
    "kagak": "tidak",
    "kgk": "tidak",
    "gk": "tidak",
    "g": "tidak",
    "gpp": "tidak apa apa",
    "yg": "yang",
    "krn": "karena",
    "jg": "juga",
    "tdk": "tidak",
    "udh": "sudah",
    "aja": "saja",
}

# Negation words and key tokens to preserve during stopword removal
NEGATION_WORDS = {"tidak", "tak", "nggak", "ga", "gak", "bukan", "belum", "jangan", "enggak"}
KEYWORD_STOPWORDS = {"ada", "guna", "lagi", "saja"}
PRESERVE = NEGATION_WORDS | KEYWORD_STOPWORDS

_SASTRAWI_SW = set(StopWordRemoverFactory().get_stop_words())
STOPWORDS_SAFE = _SASTRAWI_SW - PRESERVE

# Dictionary of keywords: stem/phrase -> (weight, zone, kw_type, category)
KAMUS = {
    # ===== YELLOW ZONE =====
    "hampa":       (4, "Yellow", "single_neutral",       "Hopelessness"),
    "kosong":      (4, "Yellow", "single_neutral",       "Hopelessness"),
    "sendiri":     (3, "Yellow", "single_neutral",       "Hopelessness"),
    "putus asa":   (6, "Yellow", "single_neutral",       "Hopelessness"),
    "ada harap":   (6, "Yellow", "phrase_with_negation", "Hopelessness"),   # "ga ada harapan"
    "ada guna":    (6, "Yellow", "phrase_with_negation", "Worthlessness"),  # "tidak ada gunanya"
    "beban":       (4, "Yellow", "single_neutral",       "Worthlessness"),
    "susah":       (4, "Yellow", "single_neutral",       "Worthlessness"),  # dari "menyusahkan"
    "gagal":       (3, "Yellow", "single_neutral",       "Worthlessness"),
    "bodoh":       (3, "Yellow", "single_neutral",       "Worthlessness"),
    "lelah hidup": (7, "Yellow", "single_neutral",       "Hopelessness"),
    "capek hidup": (7, "Yellow", "single_neutral",       "Hopelessness"),
    "bosan hidup": (7, "Yellow", "single_neutral",       "Hopelessness"),
    "serah":       (5, "Yellow", "single_neutral",       "Hopelessness"),   # dari "menyerah"
    "puruk":       (4, "Yellow", "single_neutral",       "Hopelessness"),   # dari "terpuruk"
    "harga":       (4, "Yellow", "phrase_with_negation", "Worthlessness"),  # "tidak dihargai"

    # ===== RED ZONE =====
    "bunuh diri":      (10, "Red", "single_negative",      "Direct Suicidal Ideation"),
    "gantung diri":    (10, "Red", "single_negative",      "Direct Suicidal Ideation"),
    "akhir hidup":     (10, "Red", "single_negative",      "Direct Suicidal Ideation"),  # "akhiri hidup"
    "mati saja":       (9,  "Red", "single_negative",      "Death Wish"),
    "mau mati":        (9,  "Red", "single_negative",      "Death Wish"),
    "hilang nyawa":    (10, "Red", "single_negative",      "Direct Suicidal Ideation"),  # "hilangkan nyawa"
    "sayat":           (9,  "Red", "single_negative",      "Self-Harm Indication"),
    "luka diri":       (9,  "Red", "single_negative",      "Self-Harm Indication"),      # "melukai diri"
    "sakit diri":      (8,  "Red", "single_negative",      "Self-Harm Indication"),      # "sakiti diri"
    "overdosis":       (9,  "Red", "single_negative",      "Self-Harm Indication"),
    "racun":           (7,  "Red", "single_negative",      "Self-Harm Indication"),
    "selamat tinggal": (8,  "Red", "single_neutral",       "Pre-Suicide Indicators"),
    "akhir kali":      (7,  "Red", "single_neutral",       "Pre-Suicide Indicators"),    # "terakhir kalinya"
    "ada lagi":        (8,  "Red", "phrase_with_negation", "Pre-Suicide Indicators"),    # "tidak akan ada lagi"
}

THRESHOLD_YELLOW = 5
THRESHOLD_RED_ESCALATION = 15

KATA_NEGASI = {"tidak", "tak", "nggak", "ga", "gak", "bukan", "belum", "jangan", "enggak"}
NEGATION_RADIUS = 3


def normalize_abbreviations(text: str) -> str:
    """Normalize common Indonesian abbreviations in text."""
    for abbr, full in ABBREVIATIONS.items():
        text = re.sub(r"\b" + re.escape(abbr) + r"\b", full, text)
    return text


def preprocess_appiks(text: str) -> list:
    """
    Preprocess Indonesian text: case folding, abbreviation normalization,
    cleaning punctuation, removing safe stopwords, and stemming root words.
    """
    if not text:
        return []
    text = text.lower()
    text = normalize_abbreviations(text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    tokens = [t for t in text.split() if t]
    tokens = [t for t in tokens if t not in STOPWORDS_SAFE]
    tokens = [stemmer.stem(t) for t in tokens]
    return [t for t in tokens if t]


def is_negated(tokens: list, position: int, radius: int = NEGATION_RADIUS) -> bool:
    """Check if token at position is preceded by a negation word within radius."""
    start = max(0, position - radius)
    return any(t in KATA_NEGASI for t in tokens[start:position])


def generate_ngrams(tokens: list, n: int) -> list:
    """Generate n-grams with starting position: [(pos, 'token1 token2'), ...]"""
    return [(i, " ".join(tokens[i : i + n])) for i in range(len(tokens) - n + 1)]


def _kamus_per_ngram(kamus: dict) -> dict:
    grouped = {1: {}, 2: {}, 3: {}}
    for stem, meta in kamus.items():
        n = len(stem.split())
        if n in grouped:
            grouped[n][stem] = meta
    return grouped


KAMUS_BY_NGRAM = _kamus_per_ngram(KAMUS)


def detect_keyword(tokens: list, kamus_ngram: dict, n: int) -> list:
    """Detect n-gram keywords and handle negation based on Keyword Type."""
    results = []
    for pos, ngram in generate_ngrams(tokens, n):
        if ngram in kamus_ngram:
            weight, zone, kw_type, category = kamus_ngram[ngram]
            base = {
                "stem": ngram,
                "weight": weight,
                "zone": zone,
                "category": category,
                "type": kw_type,
                "position": pos,
            }

            if kw_type == "single_negative" and is_negated(tokens, pos):
                results.append({**base, "triggered": False, "reason": "skipped_negation"})
                continue
            if kw_type == "phrase_with_negation" and not is_negated(tokens, pos):
                results.append({**base, "triggered": False, "reason": "requires_negation_absent"})
                continue

            results.append({**base, "triggered": True, "reason": "matched"})
    return results


def classify_weighted(text: str):
    """
    Classify distress level of text using the revised 3-layer weighted scoring algorithm (Approach C).

    Returns tuple: (zone_status, matched_keywords, total_score, breakdown)
    """
    tokens = preprocess_appiks(text)

    all_matches = []
    for n in [1, 2, 3]:
        all_matches.extend(detect_keyword(tokens, KAMUS_BY_NGRAM[n], n))

    triggered = [m for m in all_matches if m["triggered"]]
    skipped = [m for m in all_matches if not m["triggered"]]

    total_score = sum(m["weight"] for m in triggered)
    has_red_keyword = any(m["zone"] == "Red" for m in triggered)

    if has_red_keyword:
        zone = "Red Zone"
        reason = "red_keyword_override"
    elif total_score >= THRESHOLD_RED_ESCALATION:
        zone = "Red Zone"
        reason = "yellow_accumulation_escalation"
    elif total_score >= THRESHOLD_YELLOW:
        zone = "Yellow Zone"
        reason = "yellow_threshold"
    else:
        zone = "No Trigger"
        reason = "below_threshold"

    matched_keywords = [
        {
            "stem": m["stem"],
            "weight": m["weight"],
            "zone": m["zone"],
            "category": m["category"],
            "type": m["type"],
            "position": m["position"],
            "reason": m["reason"],
        }
        for m in triggered
    ]

    breakdown = {
        "total_score": total_score,
        "has_red_keyword": has_red_keyword,
        "reason": reason,
        "categories": sorted({m["category"] for m in triggered}),
        "triggered": triggered,
        "skipped": skipped
    }

    return zone, matched_keywords, total_score, breakdown
