import streamlit as st
import pickle

# 1. Fonction de chargement du modèle et du vectorizer
def load_assets():
    try:
        with open('model.pkl', 'rb') as f:
            model = pickle.load(f)
        with open('vectorizer.pkl', 'rb') as f:
            vectorizer = pickle.load(f)
        return model, vectorizer
    except FileNotFoundError:
        print("Erreur : Fichiers .pkl manquants. Assurez-vous que model.pkl et vectorizer.pkl sont dans le dossier.")
        return None, None

# Configuration de la page
    st.set_page_config(page_title="Détecteur d'Arnaques", page_icon="🔐")

# Chargement
model, vectorizer = load_assets()

if model and vectorizer:
    # 2. Zone de saisie (remplace le texte ci-dessous pour tester)
    print("🛡️Guardia: Mon ia anti-arnaque")
    user_input = "Félicitations, vous avez gagné un cadeau ! Cliquez ici." 
    
    if user_input:
        # Transformation et prédiction
        data = vectorizer.transform([user_input])
        prediction = model.predict(data)
        
        # 3. Affichage du résultat dans la console
        print(f"Message analysé : {user_input}")
        if prediction[0] == 1:
            print("⚠️ Résultat : Attention! Ce message semble être une ARNAQUE !")
        else:
            print("✅ Résultat : Ce message semble sûr mais méfiez-vous.")
    
    print("\n---")
    print("Développé par TCHAKPELE Koboyo Méric pour ma soutenance.")