from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta

from werkzeug.security import generate_password_hash

from models import db, User, Message
from responses import get_response_and_domain
import json
from sqlalchemy import func, extract

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'

db.init_app(app)

# Initialisation de la base de données et gestion du compte admin
with app.app_context():
    db.create_all()

    # Attribution rôle admin à 'prosper' si aucun admin n'existe
    if not User.query.filter_by(role='admin').first():
        utilisateur = User.query.filter_by(username='prosper').first()
        if utilisateur:
            utilisateur.role = 'admin'
            db.session.commit()
            print("✅ Le rôle 'admin' a été attribué à 'prosper'.")
        else:
            # Crée un compte admin par défaut uniquement si aucun n'existe
            admin_user = User(
                username='admin',
                email='admin@example.com',
                role='admin'
            )
            admin_user.set_password('admin123')  # Change le mot de passe après le premier lancement
            db.session.add(admin_user)
            db.session.commit()
            print("✅ Compte admin créé : username='admin', password='admin123'")

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def enregistrer_message(user_id, sender, content, domaine):
    if isinstance(content, dict):
        content = json.dumps(content, ensure_ascii=False)
    msg = Message(sender=sender, content=content, domaine=domaine, user_id=user_id)
    db.session.add(msg)


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
            email=email
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash("Inscription réussie. Vous pouvez maintenant vous connecter.", "success")
        return redirect(url_for('login'))

    return render_template('auth/register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            session.pop('domaine', None)
            flash("Connexion réussie.", "success")
            return redirect(url_for('chat'))
        else:
            flash("Adresse email ou mot de passe incorrect.", "danger")

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
    domaine = session.get('domaine')
    if domaine:
        Message.query.filter_by(user_id=current_user.id, domaine=domaine).delete()
    else:
        Message.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()

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
            domaine_choisi = message.lower()
            session['domaine'] = domaine_choisi
            robot_reponse = {
                "etapes": {"1": f"Domaine choisi : {domaine_choisi}"},
                "conclusion": "Merci, vous pouvez maintenant poser votre question."
            }
        else:
            response_data = get_response_and_domain(message, domaine)
            robot_reponse = response_data.get("reponse", {
                "etapes": {"1": "Erreur inattendue."},
                "conclusion": ""
            })

        enregistrer_message(current_user.id, "client", message, session.get('domaine'))
        enregistrer_message(current_user.id, "robot", robot_reponse, session.get('domaine'))
        db.session.commit()

        return redirect(url_for('chat'))

    domaine = session.get('domaine')
    query = Message.query.filter_by(user_id=current_user.id)
    if domaine:
        query = query.filter_by(domaine=domaine)

    messages = query.order_by(Message.created_at.desc()).limit(50).all()
    messages.reverse()

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


@app.route('/users')
@login_required
def users():
    if not current_user.is_admin:
        return redirect('/')
    search_query = request.args.get('search', '')
    if search_query:
        all_users = User.query.filter(User.username.ilike(f"%{search_query}%")).order_by(User.date_created.desc()).all()
    else:
        all_users = User.query.order_by(User.date_created.desc()).all()
    return render_template('admin/users.html', users=all_users, search_query=search_query)


@app.route('/users/<int:user_id>')
@login_required
def view_user(user_id):
    if not current_user.is_admin:
        return redirect('/')
    user = User.query.get_or_404(user_id)
    return render_template('admin/user_detail.html', user=user)


@app.route('/users/add', methods=['GET', 'POST'])
@login_required
def add_user():
    if not current_user.is_admin:
        return redirect('/')
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form.get('role', 'client')

        if User.query.filter_by(email=email).first():
            flash('Cet email est déjà utilisé.', 'danger')
            return redirect(url_for('add_user'))

        new_user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            role=role
        )
        db.session.add(new_user)
        db.session.commit()
        flash('Utilisateur ajouté avec succès.', 'success')
        return redirect(url_for('users'))

    return render_template('admin/add_user.html')


@app.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if not current_user.is_admin:
        return redirect('/')
    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        user.username = request.form['username']
        user.email = request.form['email']
        role = request.form.get('role')
        if role in ['client', 'admin']:
            user.role = role

        # Mot de passe facultatif
        password = request.form.get('password')
        if password:
            user.password_hash = generate_password_hash(password)

        db.session.commit()
        flash('Utilisateur mis à jour.', 'success')
        return redirect(url_for('users'))

    return render_template('admin/edit_user.html', user=user)


@app.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
def delete_user(user_id):
    if not current_user.is_admin:
        return redirect('/')
    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash("Vous ne pouvez pas supprimer votre propre compte.", "danger")
        return redirect(url_for('users'))

    db.session.delete(user)
    db.session.commit()
    flash("Utilisateur supprimé.", "success")
    return redirect(url_for('users'))


from flask import render_template, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import func
from datetime import datetime
from collections import OrderedDict


@app.route('/admin')
@login_required
def dashboard():
    if not current_user.is_admin:
        return redirect(url_for('index'))

    total_messages = Message.query.count()
    total_users = User.query.count()
    total_clients = User.query.filter_by(role='client').count()
    total_robots = Message.query.filter_by(sender='robot').count()  # compte les messages 'robot'

    now = datetime.utcnow()
    one_year_ago = now - timedelta(days=365)

    messages_per_month = (
        db.session.query(
            func.strftime('%Y-%m', Message.created_at).label('month'),
            func.count(Message.id)
        )
        .filter(Message.created_at >= one_year_ago)
        .group_by('month')
        .order_by('month')
        .all()
    )

    months_labels = []
    counts_by_month = OrderedDict()
    for i in range(11, -1, -1):
        dt = now.replace(day=1) - timedelta(days=30 * i)
        label = dt.strftime('%b %Y')
        month_str = dt.strftime('%Y-%m')
        months_labels.append(label)
        counts_by_month[month_str] = 0

    for month, count in messages_per_month:
        if month in counts_by_month:
            counts_by_month[month] = count

    monthly_counts = list(counts_by_month.values())
    months = months_labels

    messages_per_domain = (
        db.session.query(
            Message.domaine,
            func.count(Message.id)
        )
        .group_by(Message.domaine)
        .all()
    )
    domains = [domain if domain else 'Non défini' for domain, _ in messages_per_domain]
    domain_counts = [count for _, count in messages_per_domain]

    return render_template(
        'admin/dashboard.html',
        total_messages=total_messages,
        total_users=total_users,
        total_clients=total_clients,
        total_robots=total_robots,
        months=months,
        monthly_counts=monthly_counts,
        domains=domains,
        domain_counts=domain_counts
    )


if __name__ == '__main__':
    app.run(debug=True)
