from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json  # ← Import pour gérer JSON
from responses import get_response_and_domain

app = Flask(__name__)
app.secret_key = 'ma-cle-secrete'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///base.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)


# --------- Models ---------

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password_hash = db.Column(db.String(200))


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    contenu = db.Column(db.Text)
    reponse = db.Column(db.Text)  # On stocke ici une chaîne JSON
    domaine = db.Column(db.String(50))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


# --------- Flask-Login ---------

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# --------- Helpers ---------

def handle_chat(domaine, template_name):
    """
    Fonction générique pour gérer les chats par domaine
    """
    if request.method == 'POST':
        message = request.form.get('message', '').strip()
        if not message:
            flash("Le message ne peut pas être vide.", "warning")
            return redirect(url_for(f"{domaine}_chat"))

        reponse_dict, domaine_reponse = get_response_and_domain(message)

        # 🔧 Convertir la réponse dict en JSON string
        reponse_json = json.dumps(reponse_dict, ensure_ascii=False)

        nouveau_message = Message(
            utilisateur_id=current_user.id,
            contenu=message,
            reponse=reponse_json,
            domaine=domaine
        )
        db.session.add(nouveau_message)
        db.session.commit()
        return redirect(url_for(f"{domaine}_chat"))

    messages = Message.query.filter_by(utilisateur_id=current_user.id, domaine=domaine) \
                .order_by(Message.timestamp.asc()).all()

    return render_template(template_name, messages=messages, current_page=domaine)


# --------- Routes ---------

@app.route('/')
def home():
    return redirect(url_for('chat'))


@app.route('/chat', methods=['GET', 'POST'])
@login_required
def chat():
    return handle_chat('general', 'client/chat.html')


@app.route('/enseignement', methods=['GET', 'POST'])
@login_required
def enseignement_chat():
    return handle_chat('enseignement', 'client/enseignement.html')


@app.route('/consultation', methods=['GET', 'POST'])
@login_required
def consultation_chat():
    return handle_chat('consultation', 'client/consultation.html')


@app.route('/installation', methods=['GET', 'POST'])
@login_required
def installation_chat():
    return handle_chat('installation', 'client/installation.html')


@app.route('/entretien', methods=['GET', 'POST'])
@login_required
def entretien_chat():
    return handle_chat('entretien', 'client/entretien.html')


@app.route('/achats', methods=['GET', 'POST'])
@login_required
def achats_chat():
    return handle_chat('achats', 'client/achats.html')


# --------- Authentification ---------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash("Connexion réussie.", "success")
            return redirect(url_for("chat"))
        else:
            flash("Identifiants invalides. Veuillez réessayer.", "danger")

    return render_template("auth/login.html")


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Déconnexion réussie.", "info")
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        nom = request.form.get("nom", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if User.query.filter_by(email=email).first():
            flash("Email déjà utilisé.", "warning")
            return redirect(url_for("register"))

        user = User(nom=nom, email=email, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        flash("Inscription réussie. Connectez-vous maintenant.", "success")
        return redirect(url_for("login"))

    return render_template("auth/register.html")


# --------- Admin Dashboard ---------

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.email != "admin@example.com":
        flash("Accès refusé", "danger")
        return redirect(url_for("chat"))

    total_utilisateurs = User.query.count()
    total_messages = Message.query.count()
    par_domaine = db.session.query(Message.domaine, db.func.count(Message.id)).group_by(Message.domaine).all()

    return render_template("admin/dashboard.html", total_utilisateurs=total_utilisateurs,
                           total_messages=total_messages, par_domaine=par_domaine)


# --------- Init ---------

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
