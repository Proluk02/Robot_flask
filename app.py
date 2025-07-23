from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import datetime
from models import db, User, Message
from responses import get_response_and_domain  # correction ici, import correct de la fonction
import json
from werkzeug.security import generate_password_hash


app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'

db.init_app(app)

with app.app_context():
    db.create_all()

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
def index():
    return redirect(url_for('chat'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        if User.query.filter_by(username=username).first():
            flash("Nom d'utilisateur déjà utilisé.", "warning")
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash("Email déjà utilisé.", "warning")
            return redirect(url_for('register'))

        new_user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password)
        )
        db.session.add(new_user)
        db.session.commit()
        flash("Inscription réussie. Vous pouvez maintenant vous connecter.", "success")
        return redirect(url_for('login'))

    return render_template('auth/register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            session.pop('domaine', None)  # réinitialiser le domaine à la connexion
            flash("Connexion réussie.", "success")
            return redirect(url_for('chat'))
        else:
            flash("Nom d'utilisateur ou mot de passe incorrect.", "danger")

    return render_template('auth/login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Vous avez été déconnecté.", "info")
    return redirect(url_for('login'))


@app.route('/changer_domaine')
@login_required
def changer_domaine():
    session.pop('domaine', None)
    flash("Veuillez sélectionner un nouveau domaine.", "info")
    return redirect(url_for('chat'))


@app.route('/nouveau_chat', methods=['POST'])
@login_required
def nouveau_chat():
    # Supprimer les messages actuels (dans le domaine si défini, sinon tout)
    domaine = session.get('domaine')
    if domaine:
        Message.query.filter_by(user_id=current_user.id, domaine=domaine).delete()
    else:
        Message.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    # Supprimer le domaine stocké en session pour forcer la re-sélection
    session.pop('domaine', None)
    flash("Nouvelle conversation démarrée. Veuillez écrire un message pour choisir un nouveau domaine.", "info")
    return redirect(url_for('chat'))


@app.route('/refresh', methods=['GET'])
@login_required
def refresh():
    return redirect(url_for('chat'))


@app.route('/chat', methods=['GET', 'POST'])
@login_required
def chat():
    if request.method == 'POST':
        message = request.form['message'].strip()
        domaine = session.get('domaine')

        if not domaine:
            # L'utilisateur choisit un domaine après le premier message
            domaine_choisi = message.lower()
            session['domaine'] = domaine_choisi
            robot_reponse = {
                "etapes": {"1": f"Domaine choisi : {domaine_choisi}"},
                "conclusion": "Merci, vous pouvez maintenant poser votre question."
            }
        else:
            # Obtenir la réponse via la fonction get_response_and_domain
            response_data = get_response_and_domain(message, domaine)
            robot_reponse = response_data.get("reponse", {
                "etapes": {"1": "Erreur inattendue."},
                "conclusion": ""
            })

        # Enregistrer les messages utilisateur et robot
        db.session.add(Message(
            sender="client",
            content=message,
            domaine=session.get('domaine'),
            user_id=current_user.id
        ))
        db.session.add(Message(
            sender="robot",
            content=json.dumps(robot_reponse, ensure_ascii=False),
            domaine=session.get('domaine'),
            user_id=current_user.id
        ))
        db.session.commit()

        return redirect(url_for('chat'))

    # GET : afficher l'historique des messages pour l'utilisateur et domaine
    domaine = session.get('domaine')
    query = Message.query.filter_by(user_id=current_user.id)
    if domaine:
        query = query.filter_by(domaine=domaine)
    messages = query.order_by(Message.created_at).all()

    formatted_messages = []
    for msg in messages:
        content = msg.content
        if msg.sender == 'robot':
            try:
                content = json.loads(content)
            except json.JSONDecodeError:
                pass
        formatted_messages.append({
            "sender": msg.sender,
            "content": content,
            "domaine": msg.domaine,
            "created_at": msg.created_at.strftime('%Y-%m-%d %H:%M')
        })

    return render_template('chat.html', messages=formatted_messages, domaine=domaine)


if __name__ == '__main__':
    app.run(debug=True)
