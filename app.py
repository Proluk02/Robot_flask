from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from models import db, User, Message
from responses import get_response_and_domain
import os
from functools import wraps
from collections import Counter

app = Flask(__name__)
app.secret_key = 'secret_key_robot_server'

# Config DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Flask-Login Setup
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)


# ========= DÉCORATEUR ADMIN =========
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            abort(403)
        return f(*args, **kwargs)

    return decorated


# Flag d'initialisation pour la création unique
init_done = False


@app.before_request
def create_admin_once():
    global init_done
    if not init_done:
        db.create_all()
        if not User.query.filter_by(email="admin@example.com").first():
            admin = User(
                username="admin",
                email="admin@example.com",
                password_hash=generate_password_hash("admin123"),
                role="admin"
            )
            db.session.add(admin)
            db.session.commit()
        init_done = True


# Flask-Login user loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ====== AUTHENTIFICATION ======
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        if User.query.filter_by(email=email).first():
            flash("Email existe déjà", "danger")
            return redirect(url_for("register"))

        hashed_pw = generate_password_hash(password)
        new_user = User(username=username, email=email, password_hash=hashed_pw)
        db.session.add(new_user)
        db.session.commit()

        flash("Compte créé avec succès! Connectez-vous.", "success")
        return redirect(url_for("login"))

    return render_template("auth/register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            flash("Connexion réussie!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Email ou mot de passe incorrect", "danger")
            return redirect(url_for("login"))

    return render_template("auth/login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Vous vous êtes déconnecté.", "info")
    return redirect(url_for("login"))


# ========= CHAT =========
@app.route("/", methods=["GET", "POST"])
def chat():
    if request.method == "POST":
        user_msg = request.form["message"]
        response, domaine = get_response_and_domain(user_msg)

        db.session.add(Message(sender="client", content=user_msg, domaine=domaine))
        db.session.add(Message(sender="robot", content=response, domaine=domaine))
        db.session.commit()

        return redirect(url_for("chat"))

    messages = Message.query.order_by(Message.id).all()
    return render_template("client/chat.html", messages=messages)


# ========= DASHBOARD =========
@app.route("/admin")
@login_required
@admin_required
def dashboard():
    messages = Message.query.order_by(Message.id.desc()).all()
    users = User.query.all()

    total_messages = len(messages)
    total_users = len(users)
    total_clients = len([m for m in messages if m.sender == 'client'])
    total_robots = len([m for m in messages if m.sender == 'robot'])

    monthly_counts = [0] * 12
    for m in messages:
        if hasattr(m, 'created_at') and m.created_at:
            monthly_counts[m.created_at.month - 1] += 1

    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    domain_data = Counter([m.domaine or "Inconnu" for m in messages])
    domains = list(domain_data.keys())
    domain_counts = list(domain_data.values())

    return render_template("admin/dashboard.html",
                           messages=messages,
                           total_messages=total_messages,
                           total_users=total_users,
                           total_clients=total_clients,
                           total_robots=total_robots,
                           months=months,
                           monthly_counts=monthly_counts,
                           domains=domains,
                           domain_counts=domain_counts
                           )


# ========= UTILISATEURS =========
@app.route("/users")
@login_required
@admin_required
def users():
    all_users = User.query.all()
    return render_template("admin/users.html", users=all_users)


@app.route("/users/delete/<int:user_id>")
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == "admin":
        flash("Impossible de supprimer un administrateur.", "danger")
        return redirect(url_for("users"))

    db.session.delete(user)
    db.session.commit()
    flash("Utilisateur supprimé avec succès.", "success")
    return redirect(url_for("users"))


if __name__ == "__main__":
    if not os.path.exists("database.db"):
        with app.app_context():
            db.create_all()
    app.run(debug=True)
