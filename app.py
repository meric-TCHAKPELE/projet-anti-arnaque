"""
Guardia : Système de Détection d'Arnaques
Streamlit + Google Safe Browsing (liens) + Signalement communautaire (Google Sheets).

Lancement :   python -m streamlit run app.py
Prérequis :   model.pkl + vectorizer.pkl dans le même dossier
Secrets :     .streamlit/secrets.toml (local) ou Settings > Secrets (Streamlit Cloud)
              - SAFE_BROWSING_KEY  : clé API Google Safe Browsing (option)
              - [gcp_service_account] : compte de service pour Google Sheets (option)
              - SHEET_NAME : nom du Google Sheet des signalements (option)
Chaque couche externe est NON BLOQUANTE : si un secret manque ou une API
échoue, Guardia continue avec le modèle seul.
"""

import os
import re
import pickle
from datetime import datetime

import requests
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
# Styles
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
# Paramètres
# ----------------------------------------------------------------------
SEUIL = 0.75  # zone « Suspect » entre (1-SEUIL) et SEUIL — calibré après tests

# ----------------------------------------------------------------------
# Nettoyage du texte — IDENTIQUE à l'entraînement (ne jamais diverger)
# ----------------------------------------------------------------------
def clean_text_expert(text):
    text = str(text).lower()
    text = re.sub(r'http\S+|www\S+', ' [url_detecte] ', text)
    text = re.sub(r'\d+', ' [montant_chiffre] ', text)
    text = re.sub(r'[^a-zàâçéèêëîïôûùÿñæœ\[\]\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# ----------------------------------------------------------------------
# COUCHE 1 : le modèle (le cœur de Guardia)
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

# ----------------------------------------------------------------------
# COUCHE 2 : Google Safe Browsing (réputation des liens)
# ----------------------------------------------------------------------
URL_REGEX = re.compile(
    r'(https?://\S+|www\.\S+|\b[a-z0-9-]+(?:\.[a-z0-9-]+)+/[^\s]*)',
    re.IGNORECASE,
)

def extraire_liens(message):
    liens = URL_REGEX.findall(message)
    return [l if l.lower().startswith("http") else "http://" + l for l in liens]

def verifier_liens_safe_browsing(liens):
    """Retourne (liens_dangereux, api_ok). Jamais bloquant."""
    api_key = st.secrets.get("SAFE_BROWSING_KEY", None)
    if not api_key or not liens:
        return [], False
    endpoint = f"https://safebrowsing.googleapis.com/v4/threatMatches:find?key={api_key}"
    corps = {
        "client": {"clientId": "guardia-ipnet", "clientVersion": "1.0"},
        "threatInfo": {
            "threatTypes": [
                "MALWARE",
                "SOCIAL_ENGINEERING",
                "UNWANTED_SOFTWARE",
                "POTENTIALLY_HARMFUL_APPLICATION",
            ],
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": l} for l in liens],
        },
    }
    try:
        r = requests.post(endpoint, json=corps, timeout=5)
        r.raise_for_status()
        matches = r.json().get("matches", [])
        return sorted({m["threat"]["url"] for m in matches}), True
    except Exception:
        return [], False

# ----------------------------------------------------------------------
# COUCHE 3 : signalement communautaire -> Google Sheets (file de validation)
# ----------------------------------------------------------------------
@st.cache_resource
def connecter_sheet():
    """Connexion au Google Sheet des signalements. Retourne la feuille ou None."""
    try:
        import gspread
        creds = dict(st.secrets["gcp_service_account"])
        client = gspread.service_account_from_dict(creds)
        nom = st.secrets.get("SHEET_NAME", "guardia_signalements")
        return client.open(nom).sheet1
    except Exception:
        return None

def envoyer_signalement(sheet, message, verdict_modele, p_arnaque, avis_utilisateur):
    """Ajoute une ligne dans la file de validation. Retourne True si OK."""
    try:
        sheet.append_row(
            [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                message,
                verdict_modele,
                f"{p_arnaque * 100:.0f}%",
                avis_utilisateur,
                "EN ATTENTE",  # statut de validation (à changer à la main)
            ],
            value_input_option="RAW",
        )
        return True
    except Exception:
        return False

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

# --- Analyse : le résultat est stocké en session pour survivre aux reruns ---
if st.button("Lancer l'Analyse", type="primary"):
    if not message.strip():
        st.warning("Veuillez d'abord coller un message à analyser.")
        st.session_state.pop("resultat", None)
    else:
        texte_propre, p_arnaque = analyser(message, model, vectorizer)
        liens = extraire_liens(message)
        liens_dangereux, api_ok = verifier_liens_safe_browsing(liens)

        if liens_dangereux:
            verdict = "arnaque (lien malveillant confirmé)"
        elif p_arnaque >= SEUIL:
            verdict = "arnaque"
        elif p_arnaque <= (1 - SEUIL):
            verdict = "legitime"
        else:
            verdict = "suspect"

        st.session_state["resultat"] = {
            "message": message,
            "texte_propre": texte_propre,
            "p_arnaque": p_arnaque,
            "liens": liens,
            "liens_dangereux": liens_dangereux,
            "api_ok": api_ok,
            "verdict": verdict,
        }
        st.session_state["signale"] = False  # nouveau message => nouveau signalement possible

# --- Affichage du verdict (depuis la session) ---
res = st.session_state.get("resultat")
if res:
    if res["liens_dangereux"]:
        st.markdown(
            '<div class="verdict v-arnaque">🔴 ARNAQUE CONFIRMÉE — '
            "ce message contient un lien signalé comme dangereux par "
            "Google Safe Browsing.</div>",
            unsafe_allow_html=True,
        )
        for l in res["liens_dangereux"]:
            st.error(f"⛔ Lien malveillant détecté : `{l}`")
        st.metric("Probabilité d'arnaque (modèle)", f"{res['p_arnaque'] * 100:.0f} %")
    else:
        if res["verdict"] == "arnaque":
            st.markdown(
                '<div class="verdict v-arnaque">🔴 ARNAQUE PROBABLE — '
                "méfiez-vous de ce message.</div>",
                unsafe_allow_html=True,
            )
        elif res["verdict"] == "legitime":
            st.markdown(
                '<div class="verdict v-legitime">🟢 MESSAGE LÉGITIME — '
                "rien de suspect détecté.</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="verdict v-suspect">🟠 SUSPECT — À VÉRIFIER. '
                "Dans le doute, ne cliquez sur aucun lien et ne partagez "
                "aucune information personnelle.</div>",
                unsafe_allow_html=True,
            )
        st.write("")
        st.metric("Probabilité d'arnaque", f"{res['p_arnaque'] * 100:.0f} %")
        st.progress(res["p_arnaque"])

        if res["liens"] and res["api_ok"]:
            st.info(
                f"🔍 {len(res['liens'])} lien(s) vérifié(s) via Google Safe Browsing : "
                "non répertorié(s) comme malveillant(s). Prudence néanmoins : un lien "
                "très récent peut ne pas encore être répertorié."
            )
        elif res["liens"] and not res["api_ok"]:
            st.caption(
                "ℹ️ Lien détecté, mais vérification de réputation indisponible "
                "(analyse effectuée par le modèle seul)."
            )

    with st.expander("🔎 Voir le texte analysé par l'IA (après nettoyage)"):
        st.code(res["texte_propre"] or "(vide)")

    # ------------------------------------------------------------------
    # Signalement communautaire (file de validation, jamais direct)
    # ------------------------------------------------------------------
    sheet = connecter_sheet()
    if sheet is not None:
        st.markdown("---")
        st.markdown("### 📨 Aider Guardia à s'améliorer")
        if st.session_state.get("signale"):
            st.success(
                "✅ Merci ! Votre signalement a été transmis. Il sera examiné "
                "par un humain avant d'enrichir l'entraînement de Guardia."
            )
        else:
            st.markdown(
                "Ce message est une arnaque réelle que vous avez reçue ? "
                "Signalez-le : après **validation humaine**, il renforcera Guardia."
            )
            avis = st.radio(
                "Selon vous, ce message est :",
                ["arnaque", "legitime", "je ne sais pas"],
                horizontal=True,
            )
            if st.button("📨 Envoyer le signalement"):
                ok = envoyer_signalement(
                    sheet, res["message"], res["verdict"], res["p_arnaque"], avis
                )
                if ok:
                    st.session_state["signale"] = True
                    st.rerun()
                else:
                    st.error(
                        "Le signalement n'a pas pu être transmis. "
                        "Réessayez plus tard."
                    )

st.markdown("---")
st.caption("Projet de soutenance IPNET - IA & Cybersécurité - 2026")