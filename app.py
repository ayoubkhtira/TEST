import streamlit as st
import pandas as pd

from utils import load_excel, export_csv, create_sample_if_missing, now_str, REQUIRED_COLS
from da_agent import interpret_query, filter_dataframe, summarize

st.set_page_config(page_title="Agent DA (Excel)", layout="wide")

st.title("📘 Agent Demandes d’Achat — Excel")
st.caption("Toutes les réponses sont exclusivement basées sur le fichier Excel fourni.")

# --------- Chargement du fichier ---------
with st.sidebar:
    st.header("📂 Fichier Excel")
    uploaded = st.file_uploader("Dépose ton fichier .xlsx (sinon un fichier de test sera utilisé)",
                                type=["xlsx"])
    try:
        df = load_excel(uploaded)
        st.success("Fichier chargé.")
    except Exception as e:
        st.error(f"Erreur de chargement : {e}")
        st.stop()

    st.markdown("**Colonnes détectées :** " + ", ".join(df.columns))

st.write("### 🔎 Requête en langage naturel")
query = st.text_input(
    "Exemples: "
    "1) 'Cite les DA en situation en cours', "
    "2) 'Liste DA en statut en cours de validation technique', "
    "3) 'DA DA1003', "
    "4) 'Article ART-150', "
    "5) 'Désignation filtre', "
    "6) 'CODE DOC DOC-6200'"
)

# Panneau de filtres guidés
with st.expander("🧰 Filtres guidés (optionnels)"):
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        f_code_da = st.text_input("CODE DA")
    with c2:
        f_code_doc = st.text_input("CODE DOC")
    with c3:
        f_poste = st.text_input("Poste")
    with c4:
        f_article = st.text_input("Article")

    f_designation = st.text_input("Désignation contient")

    status_terms = st.text_input("Mots-clés Status (séparés par ,) ex: en cours, validation technique")
    status_terms = [s.strip().lower() for s in status_terms.split(",") if s.strip() != ""]

    tri_col = st.selectbox("Tri par", options=["-- Aucun --"] + list(df.columns))
    tri_col = None if tri_col == "-- Aucun --" else tri_col
    tri_asc = st.toggle("Tri croissant", value=True)

# Boutons d’actions
cA, cB, cC = st.columns([1,1,2])
run_btn = cA.button("▶️ Exécuter")
reset_btn = cB.button("🔄 Réinitialiser")

if reset_btn:
    st.experimental_rerun()

result_df = None
explanation = ""

if run_btn:
    # 1) Interprétation de la requête NL
    interp = interpret_query(query)
    if interp.get("ambiguous", False):
        st.warning("Selon le fichier Excel, la demande est ambiguë : " + interp["message"])
        # On continue quand même avec filtres guidés, s'il y en a
        params = {
            "code_da": f_code_da or None,
            "code_doc": f_code_doc or None,
            "poste": f_poste or None,
            "article": f_article or None,
            "designation": f_designation or None,
            "status_terms": status_terms or []
        }
    else:
        params = interp["params"]
        # Les filtres guidés complètent sans écraser
        params["code_da"] = params["code_da"] or (f_code_da or None)
        params["code_doc"] = params["code_doc"] or (f_code_doc or None)
        params["poste"] = params["poste"] or (f_poste or None)
        params["article"] = params["article"] or (f_article or None)
        params["designation"] = params["designation"] or (f_designation or None)
        params["status_terms"] = list(dict.fromkeys(params["status_terms"] + (status_terms or [])))

    # 2) Application des filtres
    result_df = filter_dataframe(
        df,
        code_da=params.get("code_da"),
        code_doc=params.get("code_doc"),
        poste=params.get("poste"),
        article=params.get("article"),
        designation=params.get("designation"),
        status_terms=params.get("status_terms"),
        tri_col=tri_col,
        tri_asc=tri_asc
    )

    # 3) Explications + résumé
    st.subheader("🧾 Résultats")
    st.write(summarize(result_df))

    # 4) Table
    if len(result_df) == 0:
        st.info("Selon le fichier Excel, aucune DA ne correspond à ces critères. "
                "Vérifie les termes ou élargis la recherche.")
    else:
        st.dataframe(result_df, use_container_width=True, hide_index=True)

        # 5) Export
        st.download_button(
            "💾 Exporter en CSV",
            data=export_csv(result_df),
            file_name=f"resultats_DA_{now_str().replace(' ','_').replace(':','')}.csv",
            mime="text/csv"
        )

# Panneau d’analyses complémentaires
with st.expander("📊 Analyses complémentaires (selon le fichier Excel)"):
    col1, col2 = st.columns(2)
    with col1:
        by_status = df.groupby("Status", dropna=False)["CODE_DA_SIMPLE"].count().sort_values(ascending=False)
        st.write("Comptage par statut :")
        st.dataframe(by_status.rename("Nombre").reset_index(), use_container_width=True)
    with col2:
        top_articles = df["Article"].value_counts().head(10).rename_axis("Article").reset_index(name="Occurrences")
        st.write("Top 10 articles demandés :")
        st.dataframe(top_articles, use_container_width=True)
