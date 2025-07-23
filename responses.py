import json
import os


def charger_connaissances(domaine):
    """
    Charge le fichier JSON de connaissances correspondant au domaine.

    Args:
        domaine (str): Nom du domaine (ex : 'enseignement', 'consultation').

    Returns:
        list | None: Liste de questions-réponses si succès, sinon None.
    """
    chemin = os.path.join("connaissances", f"{domaine}.json")
    if not os.path.isfile(chemin):
        print(f"[Erreur] Fichier {chemin} introuvable.")
        return None
    try:
        with open(chemin, "r", encoding="utf-8") as fichier:
            data = json.load(fichier)
            if not isinstance(data, list):
                print(f"[Erreur] Le fichier {chemin} ne contient pas une liste.")
                return None
            return data
    except (json.JSONDecodeError, IOError) as e:
        print(f"[Erreur] Chargement du fichier {chemin} échoué : {e}")
        return None


def get_response_and_domain(message, domaine):
    """
    Analyse un message utilisateur et retourne une réponse selon le domaine.

    Args:
        message (str): Message de l'utilisateur.
        domaine (str): Domaine sélectionné.

    Returns:
        dict: Dictionnaire contenant la réponse et le type de résultat.
    """
    base = charger_connaissances(domaine)

    if not base:
        return {
            "reponse": {
                "etapes": {
                    "1": "❌ Domaine introuvable ou fichier de connaissances invalide."
                },
                "conclusion": "Veuillez vérifier le domaine ou réessayer plus tard."
            },
            "type": "erreur"
        }

    message_lower = message.strip().lower()

    for item in base:
        if not isinstance(item, dict):
            continue  # Ignore les éléments non valides

        question = item.get("question", "").strip().lower()
        if not question:
            continue

        if question in message_lower or message_lower in question:
            reponse = item.get("reponse", {
                "etapes": {
                    "1": "🔍 Réponse trouvée mais incomplète."
                },
                "conclusion": "La réponse n’a pas pu être extraite complètement."
            })
            return {
                "reponse": reponse,
                "type": "trouve"
            }

    # Si aucune correspondance
    return {
        "reponse": {
            "etapes": {
                "1": "🤖 Je n’ai pas compris votre question ou elle ne correspond pas à mes connaissances actuelles."
            },
            "conclusion": "Merci de reformuler ou de poser une autre question."
        },
        "type": "aucune"
    }
