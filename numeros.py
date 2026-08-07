"""
numeros.py — Vérification et signalement communautaire de numéros (Guardia).

Logique PARTAGÉE entre l'app Streamlit et le bot WhatsApp (même comportement
des deux côtés). S'appuie sur un onglet 'numeros' d'un Google Sheet :
    colonnes : date | numero | affichage | motif | source | statut

Les fonctions reçoivent une worksheet gspread DÉJÀ ouverte : l'authentification
reste du côté de l'appelant (st.secrets pour l'app, variable d'env pour le bot).
Ainsi ce fichier n'a aucune dépendance à un secret et se copie tel quel dans
les deux dépôts.
"""

import re
from datetime import datetime


def normaliser_numero(brut):
    """Renvoie (cle, chiffres). 'cle' = les 8 derniers chiffres (numéro
    togolais) — permet de faire correspondre '+228 90 00 00 00',
    '90000000', '228-90-00-00-00'… au même numéro. Renvoie (None, ...)
    si l'entrée ne contient pas au moins 8 chiffres."""
    chiffres = re.sub(r"\D", "", str(brut))
    if len(chiffres) < 8:
        return None, chiffres
    return chiffres[-8:], chiffres


def verifier_numero(ws, brut):
    """Cherche le numéro dans la base. Renvoie un dict :
    {valide, total, valides, motifs}. 'valide' est False si le numéro
    est mal formé (moins de 8 chiffres)."""
    cle, _ = normaliser_numero(brut)
    if cle is None:
        return {"valide": False, "total": 0, "valides": 0, "motifs": []}

    total = valides = 0
    motifs = []
    try:
        lignes = ws.get_all_records()
    except Exception:
        lignes = []

    for ligne in lignes:
        num_ligne = re.sub(r"\D", "", str(ligne.get("numero", "")))
        if len(num_ligne) >= 8 and num_ligne[-8:] == cle:
            total += 1
            statut = str(ligne.get("statut", "")).strip().upper()
            if statut in ("VALIDE", "VALIDÉ", "CONFIRME", "CONFIRMÉ"):
                valides += 1
            motif = str(ligne.get("motif", "")).strip()
            if motif and motif not in motifs:
                motifs.append(motif)

    return {"valide": True, "total": total, "valides": valides, "motifs": motifs[:3]}


def signaler_numero(ws, brut, motif="", source=""):
    """Ajoute un signalement (statut EN ATTENTE → validation humaine).
    Renvoie True si l'ajout a réussi."""
    cle, chiffres = normaliser_numero(brut)
    if cle is None:
        return False
    try:
        ws.append_row(
            [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                chiffres,
                str(brut).strip(),
                str(motif)[:200],
                str(source),
                "EN ATTENTE",
            ],
            value_input_option="RAW",
        )
        return True
    except Exception:
        return False


def message_verification(res):
    """Construit le texte de réponse à partir du résultat de verifier_numero.
    Utilisé tel quel par l'app et par le bot pour un message cohérent."""
    if not res.get("valide"):
        return ("❓ Numéro invalide. Donnez un numéro d'au moins 8 chiffres, "
                "par ex. +228 90 00 00 00.")
    if res["total"] == 0:
        return ("🟢 Ce numéro n'est pas dans notre base de signalements. "
                "Restez prudent malgré tout : l'absence de signalement ne "
                "garantit pas qu'il soit sûr.")

    t, v = res["total"], res["valides"]
    texte = f"⚠️ Ce numéro a déjà été signalé {t} fois"
    if v:
        texte += f" (dont {v} confirmé{'s' if v > 1 else ''} par un modérateur)"
    texte += "."
    if res["motifs"]:
        texte += " Motifs indiqués : " + " ; ".join(res["motifs"]) + "."
    texte += " Par prudence : ne rappelez pas, ne cliquez sur aucun lien, "
    texte += "ne partagez aucune information personnelle."
    return texte
