import os
import pandas as pd
import numpy as np
from datetime import datetime

REQUIRED_COLS = [
    "CODE DA", "Poste", "Article", "Désignation",
    "Quantité", "Unité", "Status", "CODE DOC"
]

DATA_DIR = "data"
SAMPLE_PATH = os.path.join(DATA_DIR, "DA_sample.xlsx")

def ensure_data_folder():
    os.makedirs(DATA_DIR, exist_ok=True)

def create_sample_if_missing(path=SAMPLE_PATH):
    """Crée un petit fichier de test si aucun Excel n'est fourni."""
    ensure_data_folder()
    if os.path.exists(path):
        return path

    rng = np.random.default_rng(42)
    sample = pd.DataFrame({
        "CODE DA": [f"DA{1000+i}" for i in range(1, 31)],
        "Poste": rng.integers(1, 6, size=30),
        "Article": [f"ART-{rng.integers(100,199)}" for _ in range(30)],
        "Désignation": rng.choice(
            ["Pompe", "Joint", "Filtre", "Capteur", "Vanne", "Câble réseau", "PC Portable", "Ecran 24\""],
            size=30
        ),
        "Quantité": rng.integers(1, 50, size=30),
        "Unité": rng.choice(["U", "pcs"], size=30),
        "Status": rng.choice(
            ["En cours", "En cours de validation technique", "Validé", "Rejeté", "Clôturé", "Annulé"],
            size=30,
            p=[0.25, 0.2, 0.25, 0.1, 0.1, 0.1]
        ),
        "CODE DOC": [f"DOC-{rng.integers(5000, 7000)}" for _ in range(30)]
    })
    # Sauvegarde
    sample.to_excel(path, index=False, engine="openpyxl")
    return path

def load_excel(file_or_path):
    """
    Charge un Excel en respectant les colonnes requises.
    - file_or_path : str (chemin) OU fichier streamlit uploader.
    """
    if file_or_path is None:
        path = create_sample_if_missing()
        df = pd.read_excel(path, engine="openpyxl")
    elif isinstance(file_or_path, str):
        df = pd.read_excel(file_or_path, engine="openpyxl")
    else:
        # Uploaded file-like object
        df = pd.read_excel(file_or_path, engine="openpyxl")

    df = normalize_columns(df)
    validate_columns(df)
    df = postprocess(df)
    return df

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Uniformise les noms de colonnes (accents/casses) et gère quelques alias communs."""
    mapping_candidates = {
        "code da": "CODE DA",
        "code_da": "CODE DA",
        "da": "CODE DA",
        "poste": "Poste",
        "article": "Article",
        "designation": "Désignation",
        "désignation": "Désignation",
        "quantite": "Quantité",
        "quantité": "Quantité",
        "unite": "Unité",
        "unité": "Unité",
        "status": "Status",
        "statut": "Status",
        "code doc": "CODE DOC",
        "code_doc": "CODE DOC",
        "doc": "CODE DOC",
    }
    new_cols = {}
    for c in df.columns:
        key = str(c).strip().lower()
        new_cols[c] = mapping_candidates.get(key, c)
    df = df.rename(columns=new_cols)
    return df

def validate_columns(df: pd.DataFrame):
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(
            "Le fichier Excel est incomplet. Colonnes manquantes : "
            + ", ".join(missing) +
            ".\nAttendu : " + ", ".join(REQUIRED_COLS)
        )

def postprocess(df: pd.DataFrame) -> pd.DataFrame:
    """Nettoyage léger et typage."""
    # Trim strings
    for c in ["CODE DA", "Article", "Désignation", "Unité", "Status", "CODE DOC"]:
        df[c] = df[c].astype(str).str.strip()

    # Types numériques
    if "Poste" in df.columns:
        df["Poste"] = pd.to_numeric(df["Poste"], errors="coerce").astype("Int64")
    if "Quantité" in df.columns:
        df["Quantité"] = pd.to_numeric(df["Quantité"], errors="coerce")

    # Ajoute une colonne DA simple (pour groupby)
    if "CODE DA" in df.columns:
        df["CODE_DA_SIMPLE"] = df["CODE DA"].astype(str)

    return df

def export_csv(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M")
