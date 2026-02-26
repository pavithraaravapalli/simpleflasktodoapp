from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, FileField, TextAreaField, SelectField, DateField, PasswordField
from wtforms.validators import DataRequired, Length, Optional, EqualTo
from flask_wtf.file import FileAllowed

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(3, 80)],
        render_kw={"class": "form-control", "placeholder": "Choose a username"})
    email = StringField('Email', validators=[DataRequired(), Length(5, 120)],
        render_kw={"class": "form-control", "placeholder": "your@email.com"})
    password = PasswordField('Password', validators=[DataRequired(), Length(6, 100)],
        render_kw={"class": "form-control", "placeholder": "At least 6 characters"})
    confirm = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')],
        render_kw={"class": "form-control", "placeholder": "Repeat password"})
    submit = SubmitField('Create Account', render_kw={"class": "btn btn-primary"})


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()],
        render_kw={"class": "form-control", "placeholder": "Enter username"})
    password = PasswordField('Password', validators=[DataRequired()],
        render_kw={"class": "form-control", "placeholder": "Enter password"})
    submit = SubmitField('Sign In', render_kw={"class": "btn btn-primary"})


class TodoForm(FlaskForm):
    task = StringField('Task', validators=[DataRequired(), Length(min=1, max=200)],
        render_kw={"class": "form-control", "placeholder": "What needs to be done?"})
    description = TextAreaField('Description', validators=[Optional()],
        render_kw={"class": "form-control", "placeholder": "Add more details (optional)...", "rows": 3})
    image = FileField('Upload an image (Optional)', validators=[Optional(), FileAllowed(['jpg','jpeg','png','gif'], 'Images only')],
        render_kw={"class": "form-control"})
    priority = SelectField('Priority', choices=[('low','Low'), ('medium','Medium'), ('high','High')],
        default='medium', render_kw={"class": "form-select"})
    status = SelectField('Status', choices=[('pending','Pending'), ('in_progress','In Progress'), ('completed','Completed')],
        default='pending', render_kw={"class": "form-select"})
    due_date = DateField('Due Date', validators=[Optional()], format='%Y-%m-%d',
        render_kw={"class": "form-control"})
    category_id = SelectField('Category', coerce=int, validators=[Optional()],
        render_kw={"class": "form-select"})
    submit = SubmitField('Add Task', render_kw={"class": "btn btn-primary"})


class CategoryForm(FlaskForm):
    name = StringField('Category Name', validators=[DataRequired(), Length(1, 50)],
        render_kw={"class": "form-control", "placeholder": "e.g. Work, Personal, Shopping..."})
    color = StringField('Color', default='#6c757d',
        render_kw={"class": "form-control"})
    submit = SubmitField('Save Category', render_kw={"class": "btn btn-primary"})