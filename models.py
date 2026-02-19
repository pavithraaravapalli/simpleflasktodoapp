from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
db=SQLAlchemy()
class Todo(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    task=db.Column(db.String(400),nullable=False)
    image=db.Column(db.String(300),nullable=True)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Todo {self.task}>"