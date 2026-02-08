import streamlit as st
import pickle
import re

# 1. Fonction de nettoyage (identique à celle de ton Jupyter)
def clean_text_pro(text):
    text = text.lower()
    # Remplace les liens par un tag
    text = re.sub(r'http\S+|www\S+', ' [url_détecté] ', text)
    # Remplace les chiffres par un tag (essentiel pour ton test 1.000.000 F)
    text = re.sub(r'\d+', ' [montant_chiffré] ', text)
    # Garde uniquement les lettres et les tags
    text = re.sub(r'[^a-zàâçéèêëîïôûùÿñæœ\[\]\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# 2. Chargement des fichiers (Model et Vectorizer)
@st.cache_resource
def load_assets():
    try:
        with open('model.pkl', 'rb') as f:
            model = pickle.load(f)
        with open('vectorizer.pkl', 'rb') as f:
            vectorizer = pickle.load(f)
        return model, vectorizer
    except Exception as e:
        st.error(f"Erreur de chargement : {e}")
        return None, None

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Guardia IA - Anti-Arnaque", page_icon="🛡️", layout="wide")

# --- BARRE LATÉRALE (CONSEILS SÉCURITÉ) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/1162/1162919.png", width=100)
    st.title("Sécurité & Support")
    
    # Message de contact prioritaire
    st.error("""
    **🆘 Assistance Immédiate**
    Si vous avez un doute sur un message important, contactez :
    **contact@cda.tg**
    """)
    
    st.info("""
    **🔐 Bons Réflexes :**
    * 🏛️ **Origine Officielle** : Vérifiez toujours si le message provient réellement d'un établissement officiel (Banque, Opérateur, Service Public).
    * 🔑 **Mots de passe** : Ne partagez **jamais** aucun mot de passe ou code PIN, même à un agent officiel.
    * 🚩 **Vérifiez le numéro** : Une institution n'utilisera jamais de numéros personnels (+228...).
    * 🚩 **L'urgence est suspecte** : Les fraudeurs créent un faux sentiment d'urgence.
    """)
    
    st.success("Développé par Méric TCHAKPELE")

# --- CONTENU PRINCIPAL ---
st.title("🛡️ Guardia : Système de Détection d'Arnaques")
st.write("Analysez vos SMS ou emails suspects grâce à l'Intelligence Artificielle.")

model, vectorizer = load_assets()

if model and vectorizer:
    # Zone de saisie
    user_input = st.text_area("Collez le message reçu ici :", height=150, placeholder="Ex: Félicitations, vous avez gagné...")

    if st.button("Lancer l'Analyse"):
        if user_input.strip():
            # Traitement
            cleaned_text = clean_text_pro(user_input)
            data_vectorized = vectorizer.transform([cleaned_text])
            prediction = model.predict(data_vectorized)[0]
            
            # Affichage du résultat
            st.subheader("Verdict de l'IA :")
            
            # On vérifie si la prédiction est 'arnaque' ou le chiffre 1
            if str(prediction).lower() in ['arnaque', '1', '1.0']:
                st.error("### ⚠️Ce message semble être une ARNAQUE !")
                st.warning("L'IA a détecté des motifs frauduleux. Ne cliquez sur aucun lien.")
            else:
                st.success("### ✅ Ce message semble sûr mais faites attention quand même.")
                st.info("L'IA n'a pas détecté de signes de fraude évidents. Restez vigilant.")
        else:
            st.warning("Veuillez saisir un texte avant de cliquer sur le bouton.")

st.divider()
st.caption("Projet de soutenance IPNET - IA & Cybersécurité - 2026")