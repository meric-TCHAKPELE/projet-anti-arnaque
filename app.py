import streamlit as st
import pickle

# 1. Fonction de chargement sécurisée
def load_assets():
    try:
        with open('model.pkl', 'rb') as f:
            model = pickle.load(f)
        with open('vectorizer.pkl', 'rb') as f:
            vectorizer = pickle.load(f)
        return model, vectorizer
    except FileNotFoundError:
        return None, None

# --- CONFIGURATION VISUELLE ---
st.set_page_config(page_title="Détecteur d'Arnaques", page_icon="🔐")

st.title("🛡️ Guardia : Mon IA Anti-Arnaque")
st.write("Bienvenue dans mon projet de soutenance. Entrez un message pour vérifier sa fiabilité.")

# Chargement
model, vectorizer = load_assets()

if model is None or vectorizer is None:
    st.error("❌ Erreur : Fichiers du modèle introuvables sur GitHub.")
else:
    # 2. Zone de saisie réelle pour l'utilisateur
    user_input = st.text_area("Collez le message à analyser ici :", placeholder="Ex: Félicitations, vous avez gagné...")

    if st.button("Analyser le message"):
        if user_input:
            # Transformation et prédiction
            data = vectorizer.transform([user_input])
            prediction = model.predict(data)
            
            # 3. Affichage visuel des résultats
            st.subheader("Résultat de l'analyse :")
            
            # ATTENTION : Vérifie si ton label est 'arnaque' ou un chiffre (0/1)
            # Si tu as utilisé le dernier code avec les 40 messages, le label est du texte.
            if prediction[0] == 'arnaque':
                st.error("⚠️ Attention ! Ce message semble être une ARNAQUE !")
            else:
                st.success("✅ Ce message semble légitime.")
        else:
            st.warning("Veuillez saisir un message avant de cliquer sur Analyser.")

    st.divider()
    st.caption("Développé par TCHAKPELE Koboyo Méric pour ma soutenance.")