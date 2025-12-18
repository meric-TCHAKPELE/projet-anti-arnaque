import streamlit as st
import pickle

# Configuration de la page
st.set_page_config(page_title="Détecteur d'Arnaques", page_icon="🔐")

# Chargement sécurisé
try:
    model = pickle.load(open("model.pkl", "rb"))
    vectorizer = pickle.load(open("vectorizer.pkl", "rb"))
    
    st.title("🛡️ Mon Assistant Anti-Arnaque")
    st.write("Collez un message pour l'analyser avec l'IA.")
    st.write("cette ia a été développée par moi TCHAKPELE koboyo méric pour ma soutenance.")

    user_input = st.text_area("Message suspect :")

    if st.button("Analyser"):
        if user_input:
            data = vectorizer.transform([user_input])
            prediction = model.predict(data)[0]
            if prediction == "arnaque":
                st.error("🚨 ALERTE : C'est une arnaque !")
            else:
                st.success("✅ Ce message semble sûr.")
except:
    st.error("Erreur : Les fichiers model.pkl ou vectorizer.pkl sont introuvables.")