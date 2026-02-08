import streamlit as st
import pickle
import re

# --- 1. FONCTION DE NETTOYAGE (Identique à l'entraînement) ---
def clean_text_pro(text):
    text = text.lower()
    # Remplacement des URLs
    text = re.sub(r'http\S+|www\S+', ' [url_détecté] ', text)
    # Remplacement des montants financiers (crucial)
    text = re.sub(r'\d+', ' [montant_chiffré] ', text)
    # Conservation des lettres et des tags [ ]
    text = re.sub(r'[^a-zàâçéèêëîïôûùÿñæœ\[\]\s]', ' ', text)
    # Suppression des espaces multiples
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# --- 2. CHARGEMENT DES ASSETS ---
@st.cache_resource # Pour charger une seule fois et gagner en vitesse
def load_assets():
    try:
        with open('model.pkl', 'rb') as f:
            model = pickle.load(f)
        with open('vectorizer.pkl', 'rb') as f:
            vectorizer = pickle.load(f)
        return model, vectorizer
    except Exception:
        return None, None

# --- 3. INTERFACE UTILISATEUR ---
st.set_page_config(page_title="Guardia IA", page_icon="🛡️")

st.title("🛡️ Guardia : Mon IA Anti-Arnaque")
st.write("Analyse de messages suspect par Intelligence Artificielle (Soutenance IPNET)")

model, vectorizer = load_assets()

if model is None:
    st.error("❌ Erreur : Fichiers du modèle introuvables. Vérifiez GitHub.")
else:
    user_input = st.text_area("Collez le message reçu ici :", height=150)

    if st.button("Lancer l'Analyse"):
        if user_input.strip():
            # NETTOYAGE AVANT PRÉDICTION
            cleaned_message = clean_text_pro(user_input)
            
            # Vectorisation
            input_tfidf = vectorizer.transform([cleaned_message])
            
            # Prédiction
            prediction = model.predict(input_tfidf)[0]
            
            st.subheader("Verdict de l'IA :")
            
            # Vérification souple du label (texte ou chiffre)
            if prediction in ['arnaque', 1, '1']:
                st.error("⚠️ ALERTE : Ce message présente des caractéristiques d'une ARNAQUE !")
                st.info("Indices détectés : Promesse de gain inhabituel, demande de coordonnées ou sentiment d'urgence.")
            else:
                st.success("✅ Ce message semble légitime.")
        else:
            st.warning("Veuillez saisir un texte à analyser.")

st.divider()
st.caption("Projet de fin de cycle - TCHAKPELE Koboyo Méric")