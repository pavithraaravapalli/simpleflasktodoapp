from flask import Flask,render_template,redirect,url_for
from models import db,Todo
from forms import TodoForm
import os
from werkzeug.utils import secure_filename
app=Flask(__name__)
app.config['SECRET_KEY']="supersecretkey"
app.config['SQLALCHEMY_DATABASE_URI'] ="sqlite:///todo.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS']=False
app.config['UPLOAD_FOLDER']="static/uploads"
os.makedirs(app.config['UPLOAD_FOLDER'],exist_ok=True)
db.init_app(app)
with app.app_context():
    db.create_all()
@app.route('/',methods=["GET","POST"])
def index():
    form=TodoForm()
    if form.validate_on_submit():
        image_filename = None
        if form.image.data:
            file=form.image.data
            filename=secure_filename(file.filename)
            file_path=os.path.join(app.config['UPLOAD_FOLDER'],filename)
            file.save(file_path)
            image_filename=filename
        new_task=Todo(task=form.task.data,image = image_filename)
        db.session.add(new_task)
        db.session.commit()
        return redirect(url_for("index"))
    todos=Todo.query.order_by(Todo.created_at.desc()).all()
    return render_template("index.html",todos=todos,form=form)
@app.route('/delete/<int:id>')
def delete(id):
    todo=Todo.query.get_or_404('id')
     # Delete image file if exists
    if todo.image:
        image_path = os.path.join(app.config["UPLOAD_FOLDER"], todo.image)
        if os.path.exists(image_path):
            os.remove(image_path)
    db.session.delete(todo)
    db.session.commit()
    return redirect(url_for("index"))
if __name__=="__main__":
    app.run(debug=True)