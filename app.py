from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os

app = Flask(__name__)
CORS(app)

raw_db_url = os.getenv("DATABASE_URL", "sqlite:///local.db")
if raw_db_url.startswith("postgres://"):
    raw_db_url = raw_db_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = raw_db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

class Task(db.Model):
    id   = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(120), nullable=False)
    done = db.Column(db.Boolean, default=False)
    def as_dict(self):
        return {
            "id": self.id,
            "text": self.text,
            "done": self.done
        }

@app.get("/api/tasks")
def get_tasks():
    return jsonify([t.as_dict() for t in Task.query.all()])

@app.post("/api/tasks")
def add_task():
    task = Task(text=request.json["text"])
    db.session.add(task)
    db.session.commit()
    return jsonify(task.as_dict()), 201

@app.delete("/api/tasks/<int:task_id>")
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    return jsonify({"status": "ok"})

@app.patch("/api/tasks/<int:task_id>")
def toggle_done(task_id):
    task = Task.query.get_or_404(task_id)
    task.done = not task.done
    db.session.commit()
    return jsonify(task.as_dict())

if __name__ == "__main__":
    if app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite"):
        with app.app_context():
            db.create_all()
    app.run(debug=True)
