from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from flask_mail import Mail, Message
from wtforms import StringField, PasswordField, TextAreaField, SelectField, DateField, FileField, BooleanField
from wtforms.validators import DataRequired, Length, EqualTo, Optional
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, date, timedelta
from itsdangerous import URLSafeTimedSerializer
from apscheduler.schedulers.background import BackgroundScheduler
import csv, io, os

app = Flask(__name__)
app.config['SECRET_KEY'] = "supersecretkey"
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///todo.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = "static/uploads"
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'aravapallipavithrashetty.com'
app.config['MAIL_PASSWORD'] = 'your_app_password'
app.config['MAIL_DEFAULT_SENDER'] = 'aravapallipavithrashetty.com'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}

db = SQLAlchemy(app)
mail = Mail(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    profile_pic = db.Column(db.String(300), nullable=True)
    bio = db.Column(db.String(300), nullable=True)
    email_reminders = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    todos = db.relationship('Todo', backref='owner', lazy=True, cascade='all, delete-orphan')
    categories = db.relationship('Category', backref='owner', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    color = db.Column(db.String(20), default='#6c757d')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    todos = db.relationship('Todo', backref='category', lazy=True)


class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task = db.Column(db.String(400), nullable=False)
    description = db.Column(db.Text, nullable=True)
    image = db.Column(db.String(300), nullable=True)
    priority = db.Column(db.String(10), default='medium')
    status = db.Column(db.String(20), default='pending')
    due_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)

    @property
    def is_overdue(self):
        return self.due_date and self.due_date < date.today() and self.status != 'completed'


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(3, 80)])
    email = StringField('Email', validators=[DataRequired(), Length(5, 120)])
    password = PasswordField('Password', validators=[DataRequired(), Length(6, 100)])
    confirm = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])

class ForgotPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Length(5, 120)])

class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[DataRequired(), Length(6, 100)])
    confirm = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])

class ProfileForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(3, 80)])
    email = StringField('Email', validators=[DataRequired(), Length(5, 120)])
    bio = TextAreaField('Bio', validators=[Optional(), Length(max=300)])
    profile_pic = FileField('Profile Picture', validators=[Optional()])
    email_reminders = BooleanField('Receive due date email reminders')
    current_password = PasswordField('Current Password', validators=[Optional()])
    new_password = PasswordField('New Password (leave blank to keep current)', validators=[Optional(), Length(min=6)])

class TodoForm(FlaskForm):
    task = StringField('Task', validators=[DataRequired(), Length(1, 400)])
    description = TextAreaField('Description', validators=[Optional()])
    image = FileField('Image', validators=[Optional()])
    priority = SelectField('Priority', choices=[('low','Low'),('medium','Medium'),('high','High')], default='medium')
    status = SelectField('Status', choices=[('pending','Pending'),('in_progress','In Progress'),('completed','Completed')], default='pending')
    due_date = DateField('Due Date', validators=[Optional()], format='%Y-%m-%d')
    category_id = SelectField('Category', coerce=int, validators=[Optional()])

class CategoryForm(FlaskForm):
    name = StringField('Category Name', validators=[DataRequired(), Length(1, 50)])
    color = StringField('Color', default='#6c757d')


def send_password_reset_email(user):
    token = serializer.dumps(user.email, salt='password-reset')
    reset_url = url_for('reset_password', token=token, _external=True)
    msg = Message('Reset Your TaskFlow Password', recipients=[user.email])
    msg.html = f"""
    <div style="font-family:Inter,sans-serif;max-width:500px;margin:auto;padding:32px;">
      <div style="background:#6366f1;color:white;padding:20px;border-radius:10px 10px 0 0;text-align:center;">
        <h2 style="margin:0;">Reset Your Password</h2>
      </div>
      <div style="background:white;padding:28px;border:1px solid #e2e8f0;border-radius:0 0 10px 10px;">
        <p>Hi <strong>{user.username}</strong>,</p>
        <p>Click the button below to reset your password. This link expires in <strong>1 hour</strong>.</p>
        <div style="text-align:center;margin:28px 0;">
          <a href="{reset_url}" style="background:#6366f1;color:white;padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:600;">
            Reset Password
          </a>
        </div>
        <p style="color:#64748b;font-size:13px;">If you didn't request this, ignore this email.</p>
      </div>
    </div>
    """
    mail.send(msg)


def send_due_date_reminders():
    with app.app_context():
        tomorrow = date.today() + timedelta(days=1)
        todos = Todo.query.filter_by(due_date=tomorrow, status='pending').all()
        for todo in todos:
            user = db.session.get(User, todo.user_id)
            if user and user.email_reminders:
                msg = Message('Task Due Tomorrow – TaskFlow', recipients=[user.email])
                msg.html = f"""
                <div style="font-family:Inter,sans-serif;max-width:500px;margin:auto;padding:32px;">
                  <div style="background:#f59e0b;color:white;padding:20px;border-radius:10px 10px 0 0;text-align:center;">
                    <h2 style="margin:0;">Task Due Tomorrow!</h2>
                  </div>
                  <div style="background:white;padding:28px;border:1px solid #e2e8f0;border-radius:0 0 10px 10px;">
                    <p>Hi <strong>{user.username}</strong>, your task is due tomorrow:</p>
                    <div style="background:#fef3c7;padding:16px;border-radius:8px;border-left:4px solid #f59e0b;">
                      <strong>{todo.task}</strong>
                    </div>
                    <div style="text-align:center;margin-top:24px;">
                      <a href="{url_for('index', _external=True)}" style="background:#6366f1;color:white;padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:600;">
                        View Task
                      </a>
                    </div>
                  </div>
                </div>
                """
                try:
                    mail.send(msg)
                except Exception as e:
                    print(f"Reminder failed for {user.email}: {e}")


scheduler = BackgroundScheduler()
scheduler.add_job(send_due_date_reminders, 'cron', hour=8, minute=0)
scheduler.start()


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash('Username already taken.', 'danger')
        elif User.query.filter_by(email=form.email.data).first():
            flash('Email already registered.', 'danger')
        else:
            user = User(username=form.username.data, email=form.email.data)
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            for name, color in [('Work','#4e73df'),('Personal','#1cc88a'),('Shopping','#f6c23e'),('Health','#e74a3b')]:
                db.session.add(Category(name=name, color=color, user_id=user.id))
            db.session.commit()
            flash('Account created! Please log in.', 'success')
            return redirect(url_for('login'))
    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(url_for('index'))
        flash('Invalid username or password.', 'danger')
    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            try:
                send_password_reset_email(user)
                flash('Password reset email sent! Check your inbox.', 'success')
            except Exception as e:
                flash(f'Failed to send email: {str(e)}', 'danger')
        else:
            flash('No account found with that email.', 'danger')
    return render_template('forgot_password.html', form=form)


@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    try:
        email = serializer.loads(token, salt='password-reset', max_age=3600)
    except Exception:
        flash('The reset link is invalid or has expired.', 'danger')
        return redirect(url_for('forgot_password'))
    user = User.query.filter_by(email=email).first_or_404()
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Password reset successfully! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('reset_password.html', form=form)


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm(obj=current_user)
    if request.method == 'GET':
        form.email_reminders.data = current_user.email_reminders
    if form.validate_on_submit():
        if form.current_password.data:
            if not current_user.check_password(form.current_password.data):
                flash('Current password is incorrect.', 'danger')
                return render_template('profile.html', form=form)
        if form.profile_pic.data and form.profile_pic.data.filename:
            file = form.profile_pic.data
            if allowed_file(file.filename):
                filename = secure_filename(f"profile_{current_user.id}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                current_user.profile_pic = filename
        current_user.username = form.username.data
        current_user.email = form.email.data
        current_user.bio = form.bio.data
        current_user.email_reminders = form.email_reminders.data
        if form.new_password.data:
            current_user.set_password(form.new_password.data)
        db.session.commit()
        flash('Profile updated!', 'success')
        return redirect(url_for('profile'))
    all_todos = Todo.query.filter_by(user_id=current_user.id).all()
    stats = {
        'total': len(all_todos),
        'completed': sum(1 for t in all_todos if t.status == 'completed'),
        'pending': sum(1 for t in all_todos if t.status == 'pending'),
        'overdue': sum(1 for t in all_todos if t.is_overdue),
    }
    return render_template('profile.html', form=form, stats=stats)


@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    form = TodoForm()
    categories = Category.query.filter_by(user_id=current_user.id).all()
    form.category_id.choices = [(0, 'No Category')] + [(c.id, c.name) for c in categories]

    if form.validate_on_submit():
        image_filename = None
        if form.image.data and form.image.data.filename:
            file = form.image.data
            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_filename = filename
        new_task = Todo(
            task=form.task.data,
            description=form.description.data,
            image=image_filename,
            priority=form.priority.data,
            status=form.status.data,
            due_date=form.due_date.data,
            user_id=current_user.id,
            category_id=form.category_id.data if form.category_id.data != 0 else None
        )
        db.session.add(new_task)
        db.session.commit()
        flash('Task added!', 'success')
        return redirect(url_for('index'))

    search = request.args.get('search', '').strip()
    filter_priority = request.args.get('priority', '')
    filter_status = request.args.get('status', '')
    filter_category = request.args.get('category', '')

    query = Todo.query.filter_by(user_id=current_user.id)
    if search:
        query = query.filter((Todo.task.ilike(f'%{search}%')) | (Todo.description.ilike(f'%{search}%')))
    if filter_priority:
        query = query.filter_by(priority=filter_priority)
    if filter_status:
        query = query.filter_by(status=filter_status)
    if filter_category:
        query = query.filter_by(category_id=int(filter_category))

    todos = query.order_by(Todo.created_at.desc()).all()
    all_todos = Todo.query.filter_by(user_id=current_user.id).all()

    stats = {
        'total': len(all_todos),
        'completed': sum(1 for t in all_todos if t.status == 'completed'),
        'pending': sum(1 for t in all_todos if t.status == 'pending'),
        'in_progress': sum(1 for t in all_todos if t.status == 'in_progress'),
        'overdue': sum(1 for t in all_todos if t.is_overdue),
        'high_priority': sum(1 for t in all_todos if t.priority == 'high' and t.status != 'completed'),
    }

    priority_data = {
        'labels': ['High', 'Medium', 'Low'],
        'values': [
            sum(1 for t in all_todos if t.priority == 'high'),
            sum(1 for t in all_todos if t.priority == 'medium'),
            sum(1 for t in all_todos if t.priority == 'low'),
        ]
    }
    status_data = {
        'labels': ['Pending', 'In Progress', 'Completed'],
        'values': [stats['pending'], stats['in_progress'], stats['completed']]
    }
    category_data = {
        'labels': [c.name for c in categories],
        'values': [Todo.query.filter_by(user_id=current_user.id, category_id=c.id).count() for c in categories],
        'colors': [c.color for c in categories]
    }

    return render_template('index.html',
        todos=todos, form=form, categories=categories, stats=stats,
        search=search, filter_priority=filter_priority,
        filter_status=filter_status, filter_category=filter_category,
        priority_data=priority_data, status_data=status_data, category_data=category_data
    )


@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    todo = Todo.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    form = TodoForm(obj=todo)
    categories = Category.query.filter_by(user_id=current_user.id).all()
    form.category_id.choices = [(0, 'No Category')] + [(c.id, c.name) for c in categories]
    if form.validate_on_submit():
        if form.image.data and form.image.data.filename:
            if todo.image:
                old_path = os.path.join(app.config['UPLOAD_FOLDER'], todo.image)
                if os.path.exists(old_path):
                    os.remove(old_path)
            file = form.image.data
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            todo.image = filename
        todo.task = form.task.data
        todo.description = form.description.data
        todo.priority = form.priority.data
        todo.status = form.status.data
        todo.due_date = form.due_date.data
        todo.category_id = form.category_id.data if form.category_id.data != 0 else None
        todo.updated_at = datetime.utcnow()
        db.session.commit()
        flash('Task updated!', 'success')
        return redirect(url_for('index'))
    if todo.category_id:
        form.category_id.data = todo.category_id
    return render_template('todo_form.html', form=form, title='Edit Task', todo=todo)


@app.route('/delete/<int:id>')
@login_required
def delete(id):
    todo = Todo.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    if todo.image:
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], todo.image)
        if os.path.exists(image_path):
            os.remove(image_path)
    db.session.delete(todo)
    db.session.commit()
    flash('Task deleted.', 'info')
    return redirect(url_for('index'))


@app.route('/toggle/<int:id>', methods=['POST'])
@login_required
def toggle(id):
    todo = Todo.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    todo.status = 'completed' if todo.status != 'completed' else 'pending'
    todo.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'status': todo.status})


@app.route('/calendar')
@login_required
def calendar_view():
    return render_template('calendar_view.html')


@app.route('/api/calendar-events')
@login_required
def calendar_events():
    todos = Todo.query.filter(Todo.user_id == current_user.id, Todo.due_date.isnot(None)).all()
    events = []
    for t in todos:
        color = '#ef4444' if t.priority == 'high' else '#f59e0b' if t.priority == 'medium' else '#22c55e'
        if t.status == 'completed':
            color = '#94a3b8'
        events.append({
            'id': t.id,
            'title': t.task,
            'start': t.due_date.isoformat(),
            'color': color,
            'extendedProps': {
                'status': t.status,
                'priority': t.priority,
                'description': t.description or '',
            }
        })
    return jsonify(events)


@app.route('/export/csv')
@login_required
def export_csv():
    todos = Todo.query.filter_by(user_id=current_user.id).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Task', 'Description', 'Priority', 'Status', 'Due Date', 'Category', 'Created At'])
    for t in todos:
        writer.writerow([
            t.id, t.task, t.description or '', t.priority, t.status,
            t.due_date.isoformat() if t.due_date else '',
            t.category.name if t.category else '',
            t.created_at.strftime('%Y-%m-%d %H:%M')
        ])
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=tasks.csv'
    response.headers['Content-Type'] = 'text/csv'
    return response


@app.route('/categories')
@login_required
def categories():
    cats = Category.query.filter_by(user_id=current_user.id).all()
    return render_template('categories.html', categories=cats)


@app.route('/category/add', methods=['GET', 'POST'])
@login_required
def add_category():
    form = CategoryForm()
    if form.validate_on_submit():
        cat = Category(name=form.name.data, color=form.color.data, user_id=current_user.id)
        db.session.add(cat)
        db.session.commit()
        flash('Category added!', 'success')
        return redirect(url_for('categories'))
    return render_template('category_form.html', form=form, title='Add Category')


@app.route('/category/delete/<int:cat_id>', methods=['POST'])
@login_required
def delete_category(cat_id):
    cat = Category.query.filter_by(id=cat_id, user_id=current_user.id).first_or_404()
    db.session.delete(cat)
    db.session.commit()
    flash('Category deleted.', 'info')
    return redirect(url_for('categories'))


@app.route('/api/todos', methods=['GET'])
@login_required
def api_todos():
    todos = Todo.query.filter_by(user_id=current_user.id).all()
    return jsonify([{
        'id': t.id, 'task': t.task, 'description': t.description,
        'priority': t.priority, 'status': t.status,
        'due_date': t.due_date.isoformat() if t.due_date else None,
        'category': t.category.name if t.category else None,
        'image': t.image, 'is_overdue': t.is_overdue,
        'created_at': t.created_at.isoformat()
    } for t in todos])


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)