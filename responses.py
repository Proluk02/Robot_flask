def get_response_and_domain(message):
    msg = message.lower()

    if "cours" in msg or "étudier" in msg or "école" in msg:
        return "Voici nos cours disponibles : math, physique, info...", "enseignement"
    elif "malade" in msg or "médecin" in msg or "consultation" in msg:
        return "Merci pour votre demande médicale. Veuillez préciser vos symptômes.", "santé"
    elif "installer" in msg or "application" in msg:
        return "Nous vous guiderons pour l’installation. De quelle application s’agit-il ?", "installation"
    elif "voiture" in msg or "panne" in msg or "entretien" in msg:
        return "Entretien : contrôle technique, vidange ou pneus ?", "entretien"
    elif "acheter" in msg or "prix" in msg or "article" in msg:
        return "Nous avons plusieurs articles disponibles. Que cherchez-vous ?", "achat"
    else:
        return "Je n’ai pas compris. Pouvez-vous reformuler ?", "inconnu"
