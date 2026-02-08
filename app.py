import streamlit as st
import pickle
import re

# --- FONCTION DE NETTOYAGE (Cruciale pour reconnaître les chiffres) ---
def clean_text_pro(text):
    text = text.lower()
    # On remplace les liens
    text = re.sub(r'http\S+|www\S+', ' [url_détecté] ', text)
    # On remplace les chiffres par le tag que l'IA connaît
    text = re.sub(r'\d+', ' [montant_chiffré] ', text) 
    # On garde les lettres et les tags
    text = re.sub(r'[^a-zàâçéèêëîïôûùÿñæœ\[\]\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# --- CHARGEMENT ---
@st.cache_resource
def load_model():
    with open('model.pkl', 'rb') as f:
        m = pickle.load(f)
    with open('vectorizer.pkl', 'rb') as f:
        v = pickle.load(f)
    return m, v

st.title("🛡️ Guardia : Mon IA Anti-Arnaque")
model, vectorizer = load_model()

user_input = st.text_area("Message à analyser :")

if st.button("Lancer l'Analyse"):
    if user_input:
        # ÉTAPE CRUCIALE : On nettoie le message comme dans Jupyter
        cleaned = clean_text_pro(user_input)
        
        # Transformation
        data = vectorizer.transform([cleaned])
        prediction = model.predict(data)[0]
        
        # Affichage (on gère les formats texte 'arnaque' ou chiffre 1)
        if str(prediction).lower() in ['arnaque', '1']:
            st.error("⚠️ ARNAQUE DÉTECTÉE")
        else:
            st.success("✅ MESSAGE LÉGITIME")