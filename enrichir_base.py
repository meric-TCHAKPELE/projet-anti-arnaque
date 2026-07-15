"""
enrichir_base.py — Enrichissement de la base d'entraînement de Guardia
depuis la file de validation Google Sheets.

CIRCUIT :
  Feuille "Signalements" (statut VALIDÉ uniquement)
      -> fusion dans data/messages.csv (déduplication)
      -> marquage INTÉGRÉ dans la feuille (pour ne jamais réimporter)

GARDE-FOU : seules les lignes validées par un humain sont intégrées.
Les signalements "EN ATTENTE" sont ignorés (parade à l'empoisonnement).

Usage :        python enrichir_base.py
Prérequis :    pip install gspread pandas
Identifiants : le fichier JSON du compte de service, chemin ci-dessous.
"""

import os
import sys
import re
import pandas as pd
import gspread

# ----------------------------------------------------------------------
# CONFIGURATION — adapte ces 3 lignes à ta machine
# ----------------------------------------------------------------------
CHEMIN_JSON  = "guardia-501622-45cfa2e91af2.json"   # ton fichier JSON du compte de service
NOM_FEUILLE  = "Signalements"                        # le nom exact du Google Sheet
CHEMIN_CSV   = "data/messages.csv"                   # ta base d'entraînement

# ----------------------------------------------------------------------
def canon(valeur):
    """Forme canonique d'une cellule : espaces (y compris insécables),
    casse et accents neutralisés. Rend le script tolérant aux
    copier-coller et aux libellés approximatifs."""
    v = str(valeur).replace("\u00a0", " ").strip().lower()
    for a, b in (("é","e"), ("è","e"), ("ê","e"), ("à","a"), ("î","i")):
        v = v.replace(a, b)
    return v

def normaliser(texte):
    """Forme canonique d'un message pour la déduplication :
    minuscules + espaces normalisés."""
    texte = str(texte).lower().strip()
    return re.sub(r"\s+", " ", texte)

def trouver_colonne(entetes, cible):
    """Trouve l'index (0-based) de la colonne dont l'en-tête canonisé
    commence par la cible ('statut' matche aussi 'Statut du message')."""
    for idx, h in enumerate(entetes):
        if canon(h).startswith(cible):
            return idx
    return None

def main():
    # --- 1. Connexion à la feuille -----------------------------------
    if not os.path.exists(CHEMIN_JSON):
        sys.exit(f"❌ Fichier d'identifiants introuvable : {CHEMIN_JSON}")
    client = gspread.service_account(filename=CHEMIN_JSON)
    try:
        feuille = client.open(NOM_FEUILLE).sheet1
    except gspread.SpreadsheetNotFound:
        sys.exit(f"❌ Feuille « {NOM_FEUILLE} » introuvable (nom exact ? partage ?).")

    valeurs = feuille.get_all_values()          # toutes les cellules, brutes
    if len(valeurs) < 2:
        sys.exit("ℹ️ La feuille est vide, rien à faire.")

    # --- 2. Détection automatique des colonnes ------------------------
    entetes = valeurs[0]
    idx_msg    = trouver_colonne(entetes, "message")
    idx_avis   = trouver_colonne(entetes, "avis")
    idx_statut = trouver_colonne(entetes, "statut")
    if None in (idx_msg, idx_avis, idx_statut):
        sys.exit(f"❌ Colonnes introuvables. En-têtes lus : {entetes}\n"
                 "   Il faut une colonne Message, une colonne Avis et une colonne Statut.")
    def lettre(i):  # index -> lettre de colonne (A, B, C...)
        return chr(ord("A") + i)
    print(f"🧭 Colonnes détectées : Message={lettre(idx_msg)}, "
          f"Avis={lettre(idx_avis)}, Statut={lettre(idx_statut)}")

    lignes = valeurs[1:]
    print(f"📥 {len(lignes)} signalement(s) lu(s) dans la feuille.")

    # --- 3. Filtrage : uniquement les VALIDÉ, avec un avis exploitable
    a_integrer, ignores = [], {"attente": 0, "integre": 0, "avis": 0}
    for i, l in enumerate(lignes, start=2):        # ligne 1 = en-têtes
        def cellule(idx):
            return l[idx] if idx < len(l) else ""
        statut = canon(cellule(idx_statut)).upper()
        avis   = canon(cellule(idx_avis))
        msg    = str(cellule(idx_msg)).strip()

        if statut == "INTEGRE":
            ignores["integre"] += 1
            continue
        if statut != "VALIDE":
            ignores["attente"] += 1                # EN ATTENTE, REJETÉ, etc.
            continue
        if avis not in ("arnaque", "legitime") or not msg:
            ignores["avis"] += 1                   # "je ne sais pas" -> inutilisable
            continue
        a_integrer.append({"ligne": i, "message": msg, "label": avis})

    print(f"   ✅ validés à intégrer : {len(a_integrer)}"
          f"   ⏸ en attente/rejetés : {ignores['attente']}"
          f"   🔁 déjà intégrés : {ignores['integre']}"
          f"   ❓ sans avis clair : {ignores['avis']}")
    if not a_integrer:
        sys.exit("ℹ️ Aucun nouveau signalement validé à intégrer.")

    # --- 4. Chargement du CSV + déduplication ------------------------
    if os.path.exists(CHEMIN_CSV):
        base = pd.read_csv(CHEMIN_CSV)
    else:
        base = pd.DataFrame(columns=["message", "label"])
    deja_vus = set(base["message"].map(normaliser))

    nouveaux, doublons = [], 0
    for item in a_integrer:
        cle = normaliser(item["message"])
        if cle in deja_vus:
            doublons += 1
            continue
        deja_vus.add(cle)
        nouveaux.append(item)

    print(f"   ➕ nouveaux uniques : {len(nouveaux)}   ♻️ doublons écartés : {doublons}")

    # --- 5. Sauvegarde (avec copie de sûreté) -------------------------
    if nouveaux:
        base.to_csv(CHEMIN_CSV + ".bak", index=False)   # filet de sécurité
        ajout = pd.DataFrame(
            [{"message": n["message"], "label": n["label"]} for n in nouveaux]
        )
        base = pd.concat([base, ajout], ignore_index=True)
        base.to_csv(CHEMIN_CSV, index=False)
        print(f"💾 {CHEMIN_CSV} : {len(base)} messages "
              f"({(base['label']=='arnaque').sum()} arnaques, "
              f"{(base['label']=='legitime').sum()} légitimes). "
              f"Copie de sûreté : {CHEMIN_CSV}.bak")

    # --- 6. Marquage INTÉGRÉ dans la feuille --------------------------
    for item in a_integrer:
        feuille.update_cell(item["ligne"], idx_statut + 1, "INTÉGRÉ")
    print(f"🏷️ {len(a_integrer)} ligne(s) marquée(s) INTÉGRÉ dans la feuille.")

    print("\n✅ Terminé. Prochaine étape : relancer la cellule d'entraînement "
          "du notebook pour réentraîner le modèle, VÉRIFIER les scores, "
          "puis pousser les nouveaux .pkl si (et seulement si) ils conviennent.")

if __name__ == "__main__":
    main()
