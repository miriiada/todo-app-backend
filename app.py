from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os

app = Flask(__name__)
CORS(app)

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///local.db")
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
    tasks = Task.query.all()
    return jsonify([t.as_dict() for t in tasks])

@app.post("/api/tasks")
def add_task():
    data = request.json
    task = Task(text=data["text"])
    db.session.add(task)
    db.session.commit()
    return jsonify(task.as_dict()), 201

@app.delete("/api/tasks/<int:task_id>")
def delete_task(task_id):
    t = Task.query.get_or_404(task_id)
    db.session.delete(t)
    db.session.commit()
    return jsonify({"status": "ok"})

@app.patch("/api/tasks/<int:task_id>")
def toggle_done(task_id):
    task = Task.query.get_or_404(task_id)
    task.done = not task.done
    db.session.commit()
    return jsonify(task.as_dict())


if __name__ == "__main__":
    app.run(debug=True)
