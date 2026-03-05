
# Agent Demandes d’Achat — Excel (Streamlit)

**But** : Interroger un fichier Excel de DA (CODE DA, Poste, Article, Désignation, Quantité, Unité, Status, CODE DOC)  
**Règle** : Toutes les réponses proviennent **exclusivement** du fichier Excel.

## 1) Lancer dans GitHub Codespaces (recommandé)
- Crée un repo GitHub et pousse ces fichiers.
- Ouvre le repo → **Code → Codespaces → Create Codespace** (aucun droit admin requis).
- Dans le terminal :
  ```bash
  pip install -r requirements.txt
  streamlit run app.py
