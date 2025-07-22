import json
import os
import unicodedata
import string
from difflib import get_close_matches


def normaliser_texte(texte):
    if not isinstance(texte, str):
        return ""
    texte = texte.lower()
    texte = ''.join(
        c for c in unicodedata.normalize('NFD', texte)
        if unicodedata.category(c) != 'Mn'
    )
    texte = texte.translate(str.maketrans('', '', string.punctuation))
    return texte.strip()


def charger_connaissances(domaine):
    chemin = f"connaissances/{domaine}.json"
    if os.path.exists(chemin):
        with open(chemin, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def trouver_reponse(message, base_connaissance):
    msg_norm = normaliser_texte(message)
    questions_norm = [normaliser_texte(item.get("question", "")) for item in base_connaissance if isinstance(item, dict) and "question" in item]
    correspondance = get_close_matches(msg_norm, questions_norm, n=1, cutoff=0.6)

    if correspondance:
        for item in base_connaissance:
            if isinstance(item, dict) and normaliser_texte(item.get("question", "")) == correspondance[0]:
                return {"reponse": item.get("reponse", ""), "type": "base"}
    return None


def recherche_par_mots_cles(message, base_connaissance):
    msg_norm = normaliser_texte(message)
    for item in base_connaissance:
        if not isinstance(item, dict):
            continue
        question_norm = normaliser_texte(item.get("question", ""))
        mots_utiles = [mot for mot in question_norm.split() if len(mot) > 3]
        if any(mot in msg_norm for mot in mots_utiles):
            return {"reponse": item.get("reponse", ""), "type": "mots_cles"}
    return None


def reponse_guidee_par_domaine(message, base_connaissance=None):
    # base_connaissance non utilisé ici mais gardé pour signature uniforme
    msg = normaliser_texte(message)

    # Exemples simples de guide par domaine
    if "malade" in msg:
        return {"reponse": "Mes compassions. Pourriez-vous décrire vos symptômes précisément ?", "type": "guide"}
    elif "toux" in msg or "fievre" in msg:
        return {"reponse": "Depuis combien de temps avez-vous ces symptômes ?", "type": "guide"}

    if "installer" in msg or "installation" in msg:
        return {"reponse": "Quel type d'installation souhaitez-vous effectuer ?", "type": "guide"}
    elif "logiciel" in msg:
        return {"reponse": "Quel est le nom du logiciel que vous souhaitez installer ?", "type": "guide"}

    if "etudier" in msg:
        return {"reponse": "Sur quel sujet souhaitez-vous étudier aujourd'hui ?", "type": "guide"}

    if "panne" in msg:
        return {"reponse": "Quelle panne avez-vous constatée sur votre véhicule ?", "type": "guide"}

    if "acheter" in msg:
        return {"reponse": "Quel produit souhaitez-vous acheter ?", "type": "guide"}

    return None


def get_response_and_domain(message):
    msg = normaliser_texte(message)

    # Détection du domaine selon mots-clés
    if any(mot in msg for mot in ["cours", "etudier", "ecole", "professeur", "matiere"]):
        domaine = "enseignement"
    elif any(mot in msg for mot in ["malade", "medecin", "consultation", "ordonnance", "sante", "symptome", "toux", "fievre", "douleur", "fatigue", "infection"]):
        domaine = "consultation"
    elif any(mot in msg for mot in ["installer", "installation", "configurer", "logiciel", "mise en place"]):
        domaine = "installation"
    elif any(mot in msg for mot in ["voiture", "panne", "entretien", "maintenance", "revision"]):
        domaine = "entretien"
    elif any(mot in msg for mot in ["acheter", "prix", "article", "commande", "produit", "achat"]):
        domaine = "achats"
    else:
        return {
            "reponse": "Je n’ai pas compris. Pouvez-vous reformuler ou préciser votre demande ? "
                       "Vous pouvez aussi choisir un domaine : enseignement, consultation, installation, entretien, achats.",
            "type": "erreur"
        }, "inconnu"

    base_connaissance = charger_connaissances(domaine)

    # Essayer successivement les différentes méthodes de recherche
    for recherche in [trouver_reponse, lambda msg, base: reponse_guidee_par_domaine(msg, base), recherche_par_mots_cles]:
        result = recherche(message, base_connaissance)
        if isinstance(result, dict):
            return result, domaine

    return {
        "reponse": "Je suis désolé, je n’ai pas trouvé de réponse claire à votre question. "
                   "Pouvez-vous reformuler ou préciser ?",
        "type": "aucune"
    }, domaine
