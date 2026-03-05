import streamlit as st
import pandas as pd

from utils import load_excel, export_csv, now_str
from da_agent import interpret_query, filter_dataframe, summarize

# ---------------------------
# Page config
# ---------------------------
st.set_page_config(
    page_title="Agent DA (Excel)",
    layout="wide",
    page_icon="🧾"
)

# ---------------------------
# Modern CSS
# ---------------------------
def inject_css():
    st.markdown(
        """
        <style>
        /* Global */
        .block-container { padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1200px; }
        [data-testid="stSidebar"] { border-right: 1px solid rgba(120,120,120,.25); }

        /* Header */
        .app-header {
            display:flex; align-items:center; justify-content:space-between;
            padding: 14px 16px; border-radius: 16px;
            background: linear-gradient(135deg, rgba(99,102,241,.20), rgba(16,185,129,.18));
            border: 1px solid rgba(120,120,120,.25);
            margin-bottom: 14px;
        }
        .app-title { font-size: 1.25rem; font-weight: 800; margin: 0; }
        .app-subtitle { opacity: .85; margin: 0; margin-top: 4px; font-size: .95rem; }

        /* Cards */
        .card {
            padding: 14px 14px;
            border-radius: 16px;
            border: 1px solid rgba(120,120,120,.25);
            background: rgba(255,255,255,.02);
        }
        .muted { opacity:.8; font-size:.92rem; }
        .pill {
            display:inline-block; padding: 4px 10px; border-radius: 999px;
            border: 1px solid rgba(120,120,120,.25);
            background: rgba(99,102,241,.12);
            margin-right: 8px; margin-bottom: 8px;
            font-size:.85rem;
        }

        /* Chat bubbles spacing */
        [data-testid="stChatMessage"] { padding: 8px 0; }

        /* Buttons */
        .stButton>button {
            border-radius: 12px !important;
            padding: 0.55rem 0.9rem !important;
        }
        .stDownloadButton>button {
            border-radius: 12px !important;
            padding: 0.55rem 0.9rem !important;
        }

        /* Dataframe container */
        .dataframe-container {
            border-radius: 16px;
            border: 1px solid rgba(120,120,120,.25);
            padding: 8px;
            background: rgba(255,255,255,.02);
        }
        </style>
        """,
        unsafe_allow_html=True
    )

inject_css()

# ---------------------------
# Session state init
# ---------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "df" not in st.session_state:
    st.session_state.df = None
if "last_result" not in st.session_state:
    st.session_state.last_result = None
if "last_summary" not in st.session_state:
    st.session_state.last_summary = None

# ---------------------------
# Cached loader (important for perf)
# ---------------------------
@st.cache_data(show_spinner=False)
def load_excel_cached(uploaded_file):
    # `load_excel` gère None => sample
    return load_excel(uploaded_file)

# ---------------------------
# Header
# ---------------------------
st.markdown(
    """
    <div class="app-header">
      <div>
        <p class="app-title">🧾 Agent Demandes d’Achat — Excel</p>
        <p class="app-subtitle">Réponses exactes basées exclusivement sur le fichier Excel fourni (aucune supposition).</p>
      </div>
      <div class="muted">UI moderne • Chat • Filtres • Analyse</div>
    </div>
    """,
    unsafe_allow_html=True
)

# ---------------------------
# Sidebar: Upload + Filters
# ---------------------------
with st.sidebar:
    st.subheader("📂 Source Excel")
    uploaded = st.file_uploader(
        "Dépose ton fichier .xlsx (sinon un fichier de test sera utilisé)",
        type=["xlsx"]
    )

    try:
        df = load_excel_cached(uploaded)
        st.session_state.df = df
        st.success("Fichier chargé ✅")
    except Exception as e:
        st.error(f"Erreur de chargement : {e}")
        st.stop()

    with st.expander("👀 Aperçu & colonnes", expanded=False):
        st.caption("Colonnes détectées :")
        st.write(", ".join(list(df.columns)))
        st.dataframe(df.head(8), use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("🧰 Filtres (optionnels)")

    f_code_da = st.text_input("CODE DA", placeholder="ex: DA1003")
    f_code_doc = st.text_input("CODE DOC", placeholder="ex: DOC-6200")
    f_poste = st.text_input("Poste", placeholder="ex: 3")
    f_article = st.text_input("Article", placeholder="ex: ART-150")
    f_designation = st.text_input("Désignation contient", placeholder="ex: filtre")

    status_terms_raw = st.text_input(
        "Mots-clés Status (séparés par ,)",
        placeholder="ex: en cours, validation technique"
    )
    status_terms = [s.strip().lower() for s in status_terms_raw.split(",") if s.strip() != ""]

    st.caption("🔃 Tri")
    tri_col = st.selectbox("Tri par", options=["-- Aucun --"] + list(df.columns))
    tri_col = None if tri_col == "-- Aucun --" else tri_col
    tri_asc = st.toggle("Croissant", value=True)

    st.divider()
    st.caption("⚡ Quick prompts")
    qp1 = st.button("DA en situation en cours")
    qp2 = st.button("DA en validation technique")
    qp3 = st.button("Top 10 articles demandés")
    qp4 = st.button("DA par statut (résumé)")

# ---------------------------
# KPI Row (cards)
# ---------------------------
df = st.session_state.df

total_rows = len(df)
unique_da = df["CODE DA"].nunique() if "CODE DA" in df.columns else 0
total_qty = int(df["Quantité"].sum()) if "Quantité" in df.columns and pd.notna(df["Quantité"].sum()) else 0
unique_status = df["Status"].nunique() if "Status" in df.columns else 0

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(f'<div class="card"><div class="muted">Lignes</div><div style="font-size:1.6rem;font-weight:800;">{total_rows}</div></div>', unsafe_allow_html=True)
with k2:
    st.markdown(f'<div class="card"><div class="muted">DA uniques</div><div style="font-size:1.6rem;font-weight:800;">{unique_da}</div></div>', unsafe_allow_html=True)
with k3:
    st.markdown(f'<div class="card"><div class="muted">Quantité totale</div><div style="font-size:1.6rem;font-weight:800;">{total_qty}</div></div>', unsafe_allow_html=True)
with k4:
    st.markdown(f'<div class="card"><div class="muted">Statuts</div><div style="font-size:1.6rem;font-weight:800;">{unique_status}</div></div>', unsafe_allow_html=True)

st.write("")

# ---------------------------
# Helper: build params from NL + guided filters
# ---------------------------
def build_params(query_text: str):
    interp = interpret_query(query_text)

    # Base params from NL (or empty if ambiguous)
    if interp.get("ambiguous", False):
        base_params = {
            "code_da": None,
            "code_doc": None,
            "poste": None,
            "article": None,
            "designation": None,
            "status_terms": []
        }
        ambiguous_msg = interp["message"]
    else:
        base_params = interp["params"]
        ambiguous_msg = None

    # Guided filters fill in (without overwriting meaningful NL)
    base_params["code_da"] = base_params.get("code_da") or (f_code_da or None)
    base_params["code_doc"] = base_params.get("code_doc") or (f_code_doc or None)
    base_params["poste"] = base_params.get("poste") or (f_poste or None)
    base_params["article"] = base_params.get("article") or (f_article or None)
    base_params["designation"] = base_params.get("designation") or (f_designation or None)

    # Merge status terms
    merged_status = list(dict.fromkeys((base_params.get("status_terms") or []) + (status_terms or [])))
    base_params["status_terms"] = merged_status

    return base_params, ambiguous_msg

def run_query(query_text: str):
    params, ambiguous_msg = build_params(query_text)

    if ambiguous_msg:
        st.warning("Selon le fichier Excel, la demande est ambiguë : " + ambiguous_msg)

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
    summary = summarize(result_df)
    return result_df, summary, params

# ---------------------------
# Chat Area + Tabs
# ---------------------------
tabs = st.tabs(["💬 Agent", "🧾 Résultats", "📊 Analyses"])

# ---- Tab: Agent (chat UI)
with tabs[0]:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### 💬 Pose ta question")
    st.caption("Exemples : “Cite les DA en situation en cours”, “DA DA1003”, “Article ART-150”, “CODE DOC DOC-6200”")

    # Show pills for context
    st.markdown(
        """
        <span class="pill">Source: Excel</span>
        <span class="pill">Aucune supposition</span>
        <span class="pill">Statuts flexibles</span>
        <span class="pill">Export CSV</span>
        """,
        unsafe_allow_html=True
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # Render previous messages
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    # Quick prompts from sidebar
    quick_query = None
    if qp1:
        quick_query = "Cite-moi les DA en situation en cours"
    elif qp2:
        quick_query = "Liste les DA en statut en cours de validation technique"
    elif qp3:
        quick_query = "Quels sont les top 10 articles demandés ?"
    elif qp4:
        quick_query = "Fais un résumé des DA par statut"

    # Chat input
    user_text = st.chat_input("Écris ta demande ici…")

    if quick_query and not user_text:
        user_text = quick_query

    if user_text:
        # Push user message
        st.session_state.messages.append({"role": "user", "content": user_text})
        with st.chat_message("user"):
            st.markdown(user_text)

        # Agent response
        with st.chat_message("assistant"):
            with st.spinner("Analyse du fichier Excel en cours…"):
                # Special case: if user asks top 10 articles, show analysis text-only + store results
                # We'll still rely ONLY on Excel.
                result_df, summary, params = run_query(user_text)

                st.session_state.last_result = result_df
                st.session_state.last_summary = summary

                # Build a clean response
                response_lines = [summary]

                # If user asked "top 10 articles" explicitly, add info from df
                if "top 10" in user_text.lower() and "article" in user_text.lower():
                    top_articles = df["Article"].value_counts().head(10)
                    response_lines.append("\n**Top 10 articles (selon le fichier Excel)** :")
                    response_lines.append("\n".join([f"- {a} : {c} occurrence(s)" for a, c in top_articles.items()]))

                # Add filter recap for transparency
                applied = []
                for k, v in params.items():
                    if v and v != []:
                        applied.append(f"{k}={v}")
                if applied:
                    response_lines.append("\n**Filtres appliqués** : " + ", ".join(applied))

                response = "\n".join(response_lines)
                st.markdown(response)

        st.session_state.messages.append({"role": "assistant", "content": response})

# ---- Tab: Résultats
with tabs[1]:
    st.subheader("🧾 Résultats (basés sur le fichier Excel)")
    if st.session_state.last_summary:
        st.info(st.session_state.last_summary)

    res = st.session_state.last_result
    if res is None:
        st.caption("Aucun résultat pour l’instant. Pose une question dans l’onglet **Agent**.")
    else:
        if len(res) == 0:
            st.warning("Selon le fichier Excel, aucun résultat ne correspond aux critères.")
        else:
            st.markdown('<div class="dataframe-container">', unsafe_allow_html=True)
            st.dataframe(res, use_container_width=True, hide_index=True)
            st.markdown('</div>', unsafe_allow_html=True)

            st.download_button(
                "💾 Exporter les résultats en CSV",
                data=export_csv(res),
                file_name=f"resultats_DA_{now_str().replace(' ','_').replace(':','')}.csv",
                mime="text/csv"
            )

# ---- Tab: Analyses
with tabs[2]:
    st.subheader("📊 Analyses complémentaires (selon le fichier Excel)")
    c1, c2 = st.columns(2)

    with c1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("**Comptage par statut**")
        by_status = df.groupby("Status", dropna=False)["CODE DA"].count().sort_values(ascending=False)
        st.dataframe(by_status.rename("Nombre").reset_index(), use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("**Top 10 articles demandés**")
        top_articles = df["Article"].value_counts().head(10).rename_axis("Article").reset_index(name="Occurrences")
        st.dataframe(top_articles, use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.write("")
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("**Conseils**")
    st.caption("Tu peux demander : 'Classe les DA par Quantité décroissante', 'Articles les plus fréquents en cours', 'DA pour un DOC spécifique', etc.")
    st.markdown("</div>", unsafe_allow_html=True)
