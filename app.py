import streamlit as st
import pickle
import re

# 1. Fonction de nettoyage rigoureuse
def clean_text_pro(text):
    text = text.lower()
    # Remplacement des URLs et des montants pour l'IA
    text = re.sub(r'http\S+|www\S+', ' [url_détecté] ', text)
    text = re.sub(r'\d+', ' [montant_chiffré] ', text)
    # Conservation des caractères essentiels
    text = re.sub(r'[^a-zàâçéèêëîïôûùÿñæœ\[\]\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# 2. Chargement optimisé des fichiers pkl
@st.cache_resource
def load_assets():
    try:
        with open('model.pkl', 'rb') as f:
            model = pickle.load(f)
        with open('vectorizer.pkl', 'rb') as f:
            vectorizer = pickle.load(f)
        return model, vectorizer
    except Exception:
        return None, None

# --- INTERFACE GRAPHIQUE ---
st.set_page_config(page_title="Guardia IA", page_icon="🛡️")

st.title("🛡️ Guardia : Mon IA Anti-Arnaque")
st.markdown("### Analyse de messages suspects par Intelligence Artificielle")
st.write("Projet de fin de cycle présenté par **TCHAKPELE Koboyo Méric**.")

model, vectorizer = load_assets()

if model is None:
    st.error("❌ Erreur critique : Les fichiers du modèle sont introuvables sur le serveur.")
else:
    # Zone de saisie
    user_input = st.text_area("Collez ici le SMS ou l'e-mail à vérifier :", height=150, placeholder="Ex: Urgent virement, vous avez gagné...")

    if st.button("Lancer l'Analyse"):
        if user_input.strip():
            # Traitement
            cleaned_message = clean_text_pro(user_input)
            input_tfidf = vectorizer.transform([cleaned_message])
            prediction = model.predict(input_tfidf)[0]
            
            # Résultat visuel
            st.divider()
            if str(prediction).lower() in ['arnaque', '1', '1.0']:
                st.error("### ⚠️ VERDICT : ARNAQUE DÉTECTÉE")
                st.write("Cette analyse se base sur des motifs suspects (urgence, gain financier, liens frauduleux).")
            else:
                st.success("### ✅ VERDICT : MESSAGE LÉGITIME")
                st.write("Le message ne semble pas présenter de risques majeurs selon les critères de l'IA.")
        else:
            st.warning("Veuillez saisir un texte avant de lancer l'analyse.")

st.divider()
st.caption("© 2026 - Soutenance IPNET - Technologie Machine Learning (Naive Bayes)")