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

# Dictionary of keywords v1.2 (Validated by Clinical Psychologist): stem/phrase -> (weight, zone, kw_type, category)
KAMUS = {
    # ===== YELLOW ZONE (27 Keywords) =====
    "hampa":           (4.5, "Yellow", "single_neutral",       "Hopelessness"),   # hampa (Hopelessness, 4.5)
    "kosong":          (4.5, "Yellow", "single_neutral",       "Hopelessness"),   # kosong (Hopelessness, 4.5)
    "sendiri":         (3.0, "Yellow", "single_neutral",       "Hopelessness"),   # sendirian -> stem 'sendiri' (Hopelessness, 3.0)
    "putus asa":       (6.5, "Yellow", "single_neutral",       "Hopelessness"),   # putus asa (Hopelessness, 6.5)
    "ada harap":       (6.5, "Yellow", "phrase_with_negation", "Hopelessness"),   # tidak ada harapan -> stem 'ada harap' (Hopelessness, 6.5)
    "ada guna":        (6.5, "Yellow", "phrase_with_negation", "Worthlessness"),  # tidak ada gunanya -> stem 'ada guna' (Worthlessness, 6.5)
    "guna":            (6.0, "Yellow", "phrase_with_negation", "Worthlessness"),  # tidak berguna -> stem 'guna' (Worthlessness, 6.0)
    "beban":           (5.5, "Yellow", "single_neutral",       "Worthlessness"),  # beban (Worthlessness, 5.5)
    "susah":           (5.5, "Yellow", "single_neutral",       "Worthlessness"),  # menyusahkan -> stem 'susah' (Worthlessness, 5.5)
    "gagal":           (4.0, "Yellow", "single_neutral",       "Worthlessness"),  # gagal (Worthlessness, 4.0)
    "bodoh":           (4.0, "Yellow", "single_neutral",       "Worthlessness"),  # bodoh (Worthlessness, 4.0)
    "lelah hidup":     (6.5, "Yellow", "single_neutral",       "Hopelessness"),   # lelah hidup (Hopelessness, 6.5)
    "capek hidup":     (7.0, "Yellow", "single_neutral",       "Hopelessness"),   # capek hidup (Hopelessness, 7.0)
    "bosan hidup":     (7.0, "Yellow", "single_neutral",       "Hopelessness"),   # bosan hidup (Hopelessness, 7.0)
    "serah":           (6.0, "Yellow", "single_neutral",       "Hopelessness"),   # menyerah -> stem 'serah' (Hopelessness, 6.0)
    "puruk":           (4.5, "Yellow", "single_neutral",       "Hopelessness"),   # terpuruk -> stem 'puruk' (Hopelessness, 4.5)
    # Kunci 'harga': menggabungkan 'tidak berharga' (6.0) dan 'tidak dihargai' (4.5) menjadi satu stem 'harga'.
    # Aturan: bila dua kata kunci berbagi bentuk dasar, dipakai bobot tertinggi (6.0), sesuai prinsip mengutamakan recall yang disetujui validator.
    "harga":           (6.0, "Yellow", "phrase_with_negation", "Worthlessness"),  # tidak berharga (6) & tidak dihargai (4.5) -> stem 'harga' (Worthlessness, 6.0)
    "overthinking":    (4.5, "Yellow", "single_neutral",       "Worthlessness"),  # overthinking (Worthlessness, 4.5)
    "mental down":     (4.0, "Yellow", "single_neutral",       "Hopelessness"),   # mental down (Hopelessness, 4.0)
    "burnout":         (5.0, "Yellow", "single_neutral",       "Hopelessness"),   # burnout (Hopelessness, 5.0)
    "bullying":        (7.0, "Yellow", "single_neutral",       "Worthlessness"),  # bullying (Worthlessness, 7.0)
    "harap":           (6.0, "Yellow", "phrase_with_negation", "Hopelessness"),   # tidak berharap -> stem 'harap' (Hopelessness, 6.0)
    "lelah":           (3.0, "Yellow", "single_neutral",       "Hopelessness"),   # lelah (Hopelessness, 3.0)
    "capek":           (3.0, "Yellow", "single_neutral",       "Hopelessness"),   # capek (Hopelessness, 3.0)
    "sepi":            (4.0, "Yellow", "single_neutral",       "Hopelessness"),   # sepi (Hopelessness, 4.0)
    "sia sia":         (4.0, "Yellow", "single_neutral",       "Hopelessness"),   # sia-sia -> stem 'sia sia' (Hopelessness, 4.0)

    # ===== RED ZONE (17 Keywords) =====
    "bunuh diri":      (10.0, "Red", "single_negative",      "Direct Suicidal Ideation"), # bunuh diri (Direct SI, 10.0)
    "gantung diri":    (10.0, "Red", "single_negative",      "Direct Suicidal Ideation"), # gantung diri (Direct SI, 10.0)
    "akhir hidup":     (10.0, "Red", "single_negative",      "Direct Suicidal Ideation"), # akhiri hidup -> stem 'akhir hidup' (Direct SI, 10.0)
    "hilang nyawa":    (10.0, "Red", "single_negative",      "Direct Suicidal Ideation"), # hilangkan nyawa -> stem 'hilang nyawa' (Direct SI, 10.0)
    "mati saja":       (9.0,  "Red", "single_negative",      "Death Wish"),               # mati saja (Death Wish, 9.0)
    "mau mati":        (9.0,  "Red", "single_negative",      "Death Wish"),               # mau mati (Death Wish, 9.0)
    "hilang":          (7.0,  "Red", "single_negative",      "Death Wish"),               # hilang (Death Wish, 7.0)
    "sayat":           (9.5,  "Red", "single_negative",      "Self-Harm Indication"),     # sayat (Self-Harm, 9.5)
    "luka diri":       (9.0,  "Red", "single_negative",      "Self-Harm Indication"),     # melukai diri -> stem 'luka diri' (Self-Harm, 9.0)
    "sakit diri":      (8.5,  "Red", "single_negative",      "Self-Harm Indication"),     # menyakiti diri -> stem 'sakit diri' (Self-Harm, 8.5)
    "overdosis":       (9.5,  "Red", "single_negative",      "Self-Harm Indication"),     # overdosis (Self-Harm, 9.5)
    "racun":           (7.5,  "Red", "single_negative",      "Self-Harm Indication"),     # racun (Self-Harm, 7.5)
    "selamat tinggal": (7.5,  "Red", "single_neutral",       "Pre-Suicide Indicators"),   # selamat tinggal (Pre-Suicide, 7.5)
    "akhir kali":      (7.0,  "Red", "single_neutral",       "Pre-Suicide Indicators"),   # terakhir kalinya -> stem 'akhir kali' (Pre-Suicide, 7.0)
    "ada lagi":        (8.0,  "Red", "phrase_with_negation", "Pre-Suicide Indicators"),   # tidak akan ada lagi -> stem 'ada lagi' (Pre-Suicide, 8.0)
    "pamit lama":      (8.0,  "Red", "single_neutral",       "Pre-Suicide Indicators"),   # pamit selamanya -> stem 'pamit lama' ('selamanya' di-stem Sastrawi jadi 'lama', 8.0)
    "pergi lama":      (8.0,  "Red", "single_neutral",       "Pre-Suicide Indicators"),   # pergi selamanya -> stem 'pergi lama' ('selamanya' di-stem Sastrawi jadi 'lama', 8.0)
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
                "length": n,
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
    Classify distress level of text using the revised 3-layer weighted scoring algorithm (Approach C)
    with token span overlap suppression (longest match priority).

    Returns tuple: (zone_status, matched_keywords, total_score, breakdown)
    """
    tokens = preprocess_appiks(text)

    all_matches = []
    for n in [3, 2, 1]:
        all_matches.extend(detect_keyword(tokens, KAMUS_BY_NGRAM[n], n))

    candidate_triggered = [m for m in all_matches if m["triggered"]]
    skipped_negation = [m for m in all_matches if not m["triggered"]]

    # Longest match priority: sort by token length descending, then position ascending
    candidate_triggered.sort(key=lambda m: (-m["length"], m["position"]))

    triggered = []
    suppressed = []
    occupied_positions = set()

    for m in candidate_triggered:
        span = set(range(m["position"], m["position"] + m["length"]))
        if span & occupied_positions:
            suppressed.append({**m, "triggered": False, "reason": "suppressed_overlap"})
        else:
            occupied_positions.update(span)
            triggered.append(m)

    # Restore natural word appearance order
    triggered.sort(key=lambda m: m["position"])

    skipped = skipped_negation + suppressed

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
        "skipped": skipped,
    }

    return zone, matched_keywords, total_score, breakdown
