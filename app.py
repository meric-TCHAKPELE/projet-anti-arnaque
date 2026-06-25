"""
Guardia : Système de Détection d'Arnaques
Interface de démonstration (Streamlit).

Lancement :   python -m streamlit run app.py
Prérequis :   model.pkl + vectorizer.pkl dans le même dossier
              (et, en option, logo.png pour le logo de la barre latérale).
"""

import os
import re
import pickle
import streamlit as st

# ----------------------------------------------------------------------
# Configuration de la page (DOIT être le premier appel Streamlit)
# ----------------------------------------------------------------------
st.set_page_config(
    page_title="Guardia : Détection d'Arnaques",
    page_icon="🛡️",
    layout="wide",
)

# ----------------------------------------------------------------------
# Style des encadrés de la barre latérale
# ----------------------------------------------------------------------
st.markdown(
    """
    <style>
      .box-assistance {
          border: 1px solid #e74c3c;
          background: rgba(231, 76, 60, 0.08);
          border-radius: 8px;
          padding: 12px;
          color: #ff8a80;
          font-size: 0.85rem;
          line-height: 1.4;
      }
      .box-dev {
          border: 1px solid #2ea043;
          background: rgba(46, 160, 67, 0.15);
          border-radius: 8px;
          padding: 10px;
          color: #7ee787;
          text-align: center;
          font-size: 0.85rem;
          margin-top: 16px;
      }
      .verdict {
          border-radius: 10px;
          padding: 18px;
          font-size: 1.15rem;
          font-weight: 700;
          margin-top: 10px;
      }
      .v-arnaque  { background: rgba(231,76,60,0.15);  border:1px solid #e74c3c; color:#ff8a80; }
      .v-suspect  { background: rgba(243,156,18,0.15); border:1px solid #f39c12; color:#ffc46b; }
      .v-legitime { background: rgba(46,160,67,0.15);  border:1px solid #2ea043; color:#7ee787; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------
# Seuil de prudence (zone « Suspect » entre SEUIL et 1-SEUIL)
# ----------------------------------------------------------------------
SEUIL = 0.65

# ----------------------------------------------------------------------
# Nettoyage du texte
# ⚠️ DOIT ÊTRE IDENTIQUE à la fonction utilisée à l'entraînement.
# ----------------------------------------------------------------------
def clean_text_expert(text):
    text = str(text).lower()
    text = re.sub(r'http\S+|www\S+', ' [url_detecte] ', text)
    text = re.sub(r'\d+', ' [montant_chiffre] ', text)
    text = re.sub(r'[^a-zàâçéèêëîïôûùÿñæœ\[\]\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# ----------------------------------------------------------------------
# Chargement du modèle (mis en cache : chargé une seule fois)
# ----------------------------------------------------------------------
@st.cache_resource
def charger_modele():
    with open("model.pkl", "rb") as f:
        model = pickle.load(f)
    with open("vectorizer.pkl", "rb") as f:
        vectorizer = pickle.load(f)
    return model, vectorizer

def analyser(message, model, vectorizer):
    texte_propre = clean_text_expert(message)
    X = vectorizer.transform([texte_propre])
    proba = model.predict_proba(X)[0]
    classes = list(model.classes_)
    p_arnaque = float(proba[classes.index("arnaque")])
    return texte_propre, p_arnaque

# ======================================================================
# BARRE LATÉRALE
# ======================================================================
with st.sidebar:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)

    st.markdown("## Sécurité & Support")

    st.markdown(
        """
        <div class="box-assistance">
        🆘 <b>Assistance Immédiate</b><br>
        Si vous avez un doute sur un message important,
        contactez : <a href="mailto:contact@cda.tg">contact@cda.tg</a>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### 🛡️ Bons Réflexes :")
    st.markdown(
        "- 🏛️ **Origine Officielle :** Vérifiez toujours si le message provient "
        "réellement d'un établissement officiel (Banque, Opérateur, Service Public).\n"
        "- 🔑 **Mots de passe :** Ne partagez **jamais** aucun mot de passe ou code "
        "PIN, même à un agent officiel.\n"
        "- 🚩 **Vérifiez le numéro :** Une institution n'utilisera jamais de "
        "numéros personnels (+228...).\n"
        "- 🚩 **L'urgence est suspecte :** Les fraudeurs créent un faux sentiment "
        "d'urgence."
    )

    st.markdown(
        '<div class="box-dev">Développé par Méric TCHAKPELE</div>',
        unsafe_allow_html=True,
    )

# ======================================================================
# PAGE PRINCIPALE
# ======================================================================
st.title("🛡️ Guardia : Système de Détection d'Arnaques")
st.markdown("Analysez vos SMS ou emails suspects grâce à l'Intelligence Artificielle.")

# Vérifie la présence des fichiers du modèle
if not (os.path.exists("model.pkl") and os.path.exists("vectorizer.pkl")):
    st.error(
        "❌ Fichiers **model.pkl** et **vectorizer.pkl** introuvables. "
        "Lance d'abord ta cellule d'entraînement dans le notebook."
    )
    st.stop()

model, vectorizer = charger_modele()

message = st.text_area(
    "Collez le message reçu ici :",
    placeholder="Ex: Félicitations, vous avez gagné...",
    height=160,
)

if st.button("Lancer l'Analyse", type="primary"):
    if not message.strip():
        st.warning("Veuillez d'abord coller un message à analyser.")
    else:
        texte_propre, p_arnaque = analyser(message, model, vectorizer)

        if p_arnaque >= SEUIL:
            st.markdown(
                '<div class="verdict v-arnaque">🔴 ARNAQUE PROBABLE — '
                'méfiez-vous de ce message.</div>',
                unsafe_allow_html=True,
            )
        elif p_arnaque <= (1 - SEUIL):
            st.markdown(
                '<div class="verdict v-legitime">🟢 MESSAGE LÉGITIME — '
                'rien de suspect détecté.</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="verdict v-suspect">🟠 SUSPECT — À VÉRIFIER. '
                "Dans le doute, ne cliquez sur aucun lien et ne partagez "
                'aucune information personnelle.</div>',
                unsafe_allow_html=True,
            )

        st.write("")
        st.metric("Probabilité d'arnaque", f"{p_arnaque * 100:.0f} %")
        st.progress(p_arnaque)

        with st.expander("🔎 Voir le texte analysé par l'IA (après nettoyage)"):
            st.code(texte_propre or "(vide)")

st.markdown("---")
st.caption("Projet de soutenance IPNET - IA & Cybersécurité - 2026")