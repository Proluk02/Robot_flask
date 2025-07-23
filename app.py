from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import datetime
from models import db, User, Message
from responses import get_response_and_domain
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
            session.pop('domaine', None)  # Réinitialiser le domaine
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


@app.route('/chat', methods=['GET', 'POST'])
@login_required
def chat():
    if request.method == 'POST':
        message = request.form['message'].strip()

        domaine = session.get('domaine')

        if not domaine:
            # L'utilisateur choisit son domaine
            session['domaine'] = message.lower()
            robot_reponse = {
                "etapes": {"1": f"Domaine choisi : {session['domaine']}"},
                "conclusion": "Merci, vous pouvez maintenant poser votre question."
            }
        else:
            # Obtenir la réponse du robot à partir du domaine
            response_data = get_response_and_domain(message, domaine)
            robot_reponse = response_data.get("reponse", {})

        # Enregistrement des messages
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

    # GET : affichage des messages par utilisateur + domaine
    domaine = session.get('domaine')
    messages = Message.query.filter_by(user_id=current_user.id)

    if domaine:
        messages = messages.filter_by(domaine=domaine)

    messages = messages.order_by(Message.created_at).all()

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
