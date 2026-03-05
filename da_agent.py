import re
import pandas as pd
from typing import Dict, List, Tuple
from rapidfuzz import process, fuzz

# Groupes de mots-clés pour "Status" (flexibles)
STATUS_KEYWORDS = {
    "en cours": ["en cours", "en-cours", "encours", "progress", "en traitement", "situation en cours"],
    "validation": ["validation", "valider", "en validation", "en cours de validation", "à valider"],
    "validation technique": ["validation technique", "technique", "tech", "vt"],
    "validé": ["validé", "approuvé", "approuve", "ok"],
    "rejeté": ["rejeté", "rejete", "refusé", "refuse"],
    "clôturé": ["clôturé", "cloture", "clôture", "clos", "fermé"],
    "annulé": ["annulé", "annule", "cancel"]
}

def _flatten_keywords() -> List[str]:
    all_kw = []
    for v in STATUS_KEYWORDS.values():
        all_kw.extend(v)
    return list(set(all_kw))

ALL_STATUS_WORDS = _flatten_keywords()

def fuzzy_status_filter(df: pd.DataFrame, user_terms: List[str], col="Status",
                        score_cutoff=80) -> pd.DataFrame:
    """
    Filtre 'Status' si la cellule contient un terme proche des mots clés saisis.
    - utilise RapidFuzz partial_ratio pour robustesse.
    """
    if not user_terms:
        return df

    def match_any(cell: str) -> bool:
        text = str(cell).lower()
        # Essaye d'abord match direct
        for t in user_terms:
            if t in text:
                return True
        # Sinon approximation
        for t in user_terms:
            sc = fuzz.partial_ratio(t, text)
            if sc >= score_cutoff:
                return True
        # Essaie aussi contre nos mots clés connus
        for t in user_terms:
            cand, score, _ = process.extractOne(t, ALL_STATUS_WORDS, scorer=fuzz.WRatio)
            if score >= 85 and cand in text:
                return True
        return False

    mask = df[col].fillna("").astype(str).str.lower().apply(match_any)
    return df[mask]

def filter_dataframe(
    df: pd.DataFrame,
    code_da: str = None,
    code_doc: str = None,
    poste: str = None,
    article: str = None,
    designation: str = None,
    status_terms: List[str] = None,
    tri_col: str = None,
    tri_asc: bool = True
) -> pd.DataFrame:
    """Filtrage multi-critères basique + tri."""
    out = df.copy()

    def contains(col, val):
        if val is None or str(val).strip() == "":
            return out
        return out[out[col].astype(str).str.contains(str(val), case=False, na=False)]

    out = contains("CODE DA", code_da)
    out = contains("CODE DOC", code_doc)
    out = contains("Poste", poste)
    out = contains("Article", article)
    out = contains("Désignation", designation)

    if status_terms:
        # normalise termes
        terms = [t.strip().lower() for t in status_terms if t and str(t).strip() != ""]
        out = fuzzy_status_filter(out, terms)

    if tri_col and tri_col in out.columns:
        out = out.sort_values(by=tri_col, ascending=tri_asc, na_position="last")

    return out

def summarize(df: pd.DataFrame, limit_top=10) -> str:
    """Produit un court résumé textuel des résultats."""
    n_rows = len(df)
    if n_rows == 0:
        return "Selon le fichier Excel, aucun résultat ne correspond à ces critères."

    # Comptes par status
    st_counts = df["Status"].fillna("N/A").value_counts().head(8)
    # Top articles
    top_art = df["Article"].value_counts().head(5)
    # Somme quantités
    total_q = df["Quantité"].sum()

    parts = [
        f"Selon le fichier Excel, {n_rows} lignes correspondent aux critères.",
        "Par statut : " + "; ".join([f"{k}: {v}" for k, v in st_counts.items()]),
        f"Quantité totale demandée : {int(total_q) if pd.notna(total_q) else 0}",
        "Top articles : " + "; ".join([f"{k} ({v})" for k, v in top_art.items()])
    ]
    return "\n".join(parts)

# ---------- Interprétation d'une requête en français (sans LLM) ----------

STATUS_HINTS = [kw for group in STATUS_KEYWORDS.values() for kw in group]

def interpret_query(q: str) -> Dict:
    """
    Transforme une requête utilisateur en paramètres de filtre.
    Règles simples, robustes aux cas usuels.
    """
    if not q or str(q).strip() == "":
        return {"ambiguous": True, "message": "Formule ta demande (ex. 'liste les DA en cours de validation technique')."}

    text = q.strip().lower()

    # Extraire codes éventuels
    code_da = _first_match(text, r"(da[0-9]{3,})")
    code_doc = _first_match(text, r"(doc[-\s]?[0-9]{3,})")

    # Poste (numérique)
    poste = _first_match(text, r"(poste\s*:?[\s]*[0-9]{1,})")
    if poste:
        poste = re.findall(r"[0-9]+", poste)[0]

    # Article (pattern simple)
    article = _first_match(text, r"(art[-\s]?[0-9]{2,4})")

    # Désignation : on tente d'extraire des mots après 'désignation' ou 'article'
    designation = None
    m = re.search(r"(désignation|designation|article)\s*:?[\s]*([a-z0-9\"' \-_/]{3,})", text)
    if m:
        designation = m.group(2).strip()

    # Status : liste de termes présents
    status_terms = []
    for kw in STATUS_HINTS:
        if kw in text:
            status_terms.append(kw)
    # Ajoute 'en cours' si l'utilisateur dit 'en cours' tout court
    if "en cours" in text and "en cours" not in status_terms:
        status_terms.append("en cours")

    params = {
        "code_da": code_da,
        "code_doc": code_doc,
        "poste": poste,
        "article": article,
        "designation": designation,
        "status_terms": list(dict.fromkeys(status_terms))  # unique et ordre conservé
    }

    # Ambigu si rien d'exploitable
    if not any([code_da, code_doc, poste, article, designation]) and len(params["status_terms"]) == 0:
        return {
            "ambiguous": True,
            "message": ("Ta demande est ambiguë. Précise au moins un critère (ex. 'DA en cours', "
                        "'Article ART-123', 'Désignation filtre', 'CODE DOC 6001').")
        }

    return {"ambiguous": False, "params": params}

def _first_match(text: str, pattern: str):
    m = re.search(pattern, text)
    return m.group(1).replace(" ", "").upper() if m else None
