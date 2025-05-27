from fast_sigma import _load_rules, Matcher, CACHE_FILE

def ensure_sigma_cache():
    """
    .sigma_cache.pkl mavjud bo‘lmasa – yaratadi.
    """
    if not CACHE_FILE.exists():
        print("[i] .sigma_cache.pkl topilmadi — kompilyatsiya…")
    _load_rules()           # yaratadi yoki kechdan o‘qiydi

# --- global matcher (asosiy kodga import bo‘ladi) ---
RULES   = _load_rules()
MATCHER = Matcher(RULES)

def analyze_log(log: dict):
    """
    Log (dict) ni past-case qilib, barcha mos rule’larning meta’sini qaytaradi.
    """
    low = {k.lower(): str(v).lower() for k, v in log.items()}
    return [
        r["meta"]
        for r in MATCHER.rules
        if all(fn(low.get(f, "")) for f, fn in r["checks"])
    ]
