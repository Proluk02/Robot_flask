# responses.py

import connaissances  # importe le dictionnaire CONNAISSANCES depuis connaissances.py

def charger_connaissances(domaine):
    """
    Charge les connaissances depuis le module Python, selon le domaine.
    """
    return connaissances.CONNAISSANCES.get(domaine, [])


def nettoyer_texte(texte):
    """
    Nettoie et normalise un texte pour la comparaison.
    """
    return texte.strip().lower()


def similarite(message, question):
    """
    Retourne True si la question semble similaire au message utilisateur.
    Compare les mots clés principaux.
    """
    mots_message = set(nettoyer_texte(message).split())
    mots_question = set(nettoyer_texte(question).split())
    correspondances = mots_message & mots_question
    # On considère une similarité si au moins la moitié des mots de la question sont dans le message
    return len(correspondances) >= max(1, len(mots_question) // 2)


def get_response_and_domain(message, domaine):
    """
    Analyse un message utilisateur et retourne une réponse structurée selon le domaine.

    Args:
        message (str): Message de l'utilisateur.
        domaine (str): Domaine sélectionné.

    Returns:
        dict: Dictionnaire contenant la réponse structurée et un type.
    """
    base = charger_connaissances(domaine)

    if not base:
        return {
            "reponse": {
                "etapes": {
                    "1": "❌ Domaine introuvable ou aucune connaissance chargée."
                },
                "conclusion": "Veuillez vérifier le domaine ou réessayer plus tard."
            },
            "type": "erreur"
        }

    message_clean = nettoyer_texte(message)

    for item in base:
        if not isinstance(item, dict):
            continue

        question = item.get("question", "")
        if not question:
            continue

        # Vérifie si la question correspond exactement ou est similaire
        if message_clean == nettoyer_texte(question) or similarite(message, question):
            reponse = item.get("reponse", None)

            if not reponse or not isinstance(reponse, dict) or "etapes" not in reponse or "conclusion" not in reponse:
                reponse = {
                    "etapes": {
                        "1": "🔍 Réponse trouvée mais incomplète."
                    },
                    "conclusion": "La réponse n’a pas pu être extraite complètement."
                }

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
