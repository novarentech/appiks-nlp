import re
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory

# Initialize Sastrawi stemmer and stopword remover
factory_stemmer = StemmerFactory()
stemmer = factory_stemmer.create_stemmer()

factory_stopword = StopWordRemoverFactory()
stopword_remover = factory_stopword.create_stop_word_remover()

# Weighted keywords dictionary: {stem: (weight, zone)}
KAMUS_BERBOBOT = {
    # ===== RED ZONE =====
    "bunuh": (10, "Red"),
    "akhir": (9, "Red"),   # "akhiri hidup"
    "sayat": (9, "Red"),
    "luka": (9, "Red"),    # "lukai diri"
    "gantung": (10, "Red"),
    "racun": (8, "Red"),
    "mati": (7, "Red"),

    # ===== YELLOW ZONE - bobot tinggi (distress kuat) =====
    "guna": (5, "Yellow"),    # "ga ada gunanya"
    "peduli": (5, "Yellow"),  # "ga ada yang peduli"
    "harap": (6, "Yellow"),   # "ga ada harapan"
    "nyerah": (5, "Yellow"),
    "beban": (6, "Yellow"),   # "beban orang"

    # ===== YELLOW ZONE - bobot sedang =====
    "kosong": (4, "Yellow"),
    "hampa": (4, "Yellow"),
    "sendiri": (3, "Yellow"),
    "tangis": (5, "Yellow"),  # "menangis terus"

    # ===== YELLOW ZONE - bobot rendah (butuh konteks) =====
    "capek": (1, "Yellow"),
    "lelah": (1, "Yellow"),
    "malas": (1, "Yellow"),
    "bosan": (1, "Yellow"),
}

# Co-occurrence pairs that trigger an additional bonus score
CO_OCCURRENCE_PAIRS = [
    ("capek", "guna"),        # anhedonia + hopelessness
    ("sendiri", "peduli"),    # loneliness + abandonment
    ("kosong", "harap"),      # emptiness + hopelessness
    ("lelah", "beban"),       # fatigue + burden
]

THRESHOLD_YELLOW = 3
THRESHOLD_RED = 10

def preprocess_appiks(text):
    """
    Preprocess Indonesian text: case folding, cleaning punctuation,
    removing stopwords, and stemming root words.
    """
    if not text:
        return []
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    text = stopword_remover.remove(text)
    stemmed_text = stemmer.stem(text)
    tokens = [t for t in stemmed_text.split() if t]
    return tokens

def classify_weighted(text):
    """
    Classify distress level of text using the 3-layer weighted scoring algorithm.
    """
    # Step 1: Preprocess text into stemmed tokens
    tokens = preprocess_appiks(text)

    # Step 2: Match keywords and calculate base score
    matched_keywords = []
    base_score = 0
    has_red_explicit = False

    for token in tokens:
        if token in KAMUS_BERBOBOT:
            weight, zone = KAMUS_BERBOBOT[token]
            matched_keywords.append({
                "stem": token,
                "weight": weight,
                "zone": zone
            })
            base_score += weight

            # Layer 2 override check: explicit red zone keyword with weight >= 9
            if zone == "Red" and weight >= 9:
                has_red_explicit = True

    # Step 3: Co-occurrence pairs check and bonus score
    matched_stems = {m["stem"] for m in matched_keywords}
    bonus_score = 0
    bonus_pairs = []

    for stem1, stem2 in CO_OCCURRENCE_PAIRS:
        if stem1 in matched_stems and stem2 in matched_stems:
            bonus_score += 2
            bonus_pairs.append((stem1, stem2))

    total_score = base_score + bonus_score

    # Step 4: Classify severity zone
    if has_red_explicit or total_score >= THRESHOLD_RED:
        zone = "Red Zone"
    elif total_score >= THRESHOLD_YELLOW:
        zone = "Yellow Zone"
    else:
        zone = "No Trigger"

    breakdown = {
        "base_score": base_score,
        "bonus_score": bonus_score,
        "bonus_pairs": bonus_pairs,
        "total_score": total_score,
        "has_red_explicit": has_red_explicit,
        "threshold_yellow": THRESHOLD_YELLOW,
        "threshold_red": THRESHOLD_RED
    }

    return zone, matched_keywords, total_score, breakdown
