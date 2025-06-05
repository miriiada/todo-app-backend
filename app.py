from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from passlib.hash import bcrypt
import os

app = Flask(__name__)
CORS(app)

raw_db_url = os.getenv("DATABASE_URL", "sqlite:///local.db")
if raw_db_url.startswith("postgres://"):
    raw_db_url = raw_db_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = raw_db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "super-secret-key")

db = SQLAlchemy(app)
migrate = Migrate(app, db)
jwt = JWTManager(app)

with app.app_context():
    db.create_all()

class User(db.Model):
    __tablename__ = "users"  # чтобы таблица называлась именно так

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    # Сериализация пользователя (можно отдавать в /me)
    def as_dict(self):
        return {"id": self.id, "username": self.username}

    def set_password(self, password):
        self.password_hash = bcrypt.hash(password)

    def check_password(self, password):
        return bcrypt.verify(password, self.password_hash)

class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(120), nullable=False)
    done = db.Column(db.Boolean, default=False)

    # Добавляем внешнее поле, ссылающееся на пользователя
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    # Опционально: связь «каждая задача принадлежит одному пользователю»
    owner = db.relationship("User", backref=db.backref("tasks", lazy=True))

    def as_dict(self):
        return {
            "id": self.id,
            "text": self.text,
            "done": self.done,
            "owner_id": self.owner_id,
        }


# ─── Регистрация пользователя ────────────────────────────────
@app.post("/api/auth/register")
def register():
    data = request.json or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    # Минимальная валидация
    if not username or not password:
        return jsonify({"msg": "Username and password are required"}), 400

    # Проверяем, существует ли уже пользователь с таким username
    if User.query.filter_by(username=username).first():
        return jsonify({"msg": "Username already exists"}), 400

    # Создаем и хешируем пароль
    new_user = User(username=username)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    access_token = create_access_token(identity=new_user.id)
    return jsonify({ "access_token": access_token, "user": new_user.as_dict() }), 201
    

# ─── Вход (логин) пользователя ─────────────────────────────────
@app.post("/api/auth/login")
def login():
    data = request.json or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        return jsonify({"msg": "Username and password are required"}), 400

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({"msg": "Bad username or password"}), 401

    access_token = create_access_token(identity=user.id)
    return jsonify({ "access_token": access_token, "user": user.as_dict() }), 200


@app.get("/api/tasks")
@jwt_required()
def get_tasks():
    # Получаем ID текущего пользователя из токена
    current_user_id = get_jwt_identity()
    # Забираем только задачи, принадлежащие этому пользователю
    tasks = Task.query.filter_by(owner_id=current_user_id).all()
    return jsonify([t.as_dict() for t in tasks])

@app.post("/api/tasks")
@jwt_required()
def add_task():
    current_user_id = get_jwt_identity()
    data = request.json or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"msg": "Text cannot be empty"}), 400

    task = Task(text=text, owner_id=current_user_id)
    db.session.add(task)
    db.session.commit()
    return jsonify(task.as_dict()), 201

# ─── PUT /api/tasks/<id> ──────────────────────────────────────────
@app.put("/api/tasks/<int:task_id>")
@jwt_required()
def update_task(task_id):
    current_user_id = get_jwt_identity()
    # Ищем задачу, принадлежащую именно этому пользователю
    task = Task.query.filter_by(id=task_id, owner_id=current_user_id).first_or_404()
    data = request.json or {}
    if "text" in data:
        task.text = data["text"]
    if "done" in data:
        task.done = data["done"]
    db.session.commit()
    return jsonify(task.as_dict())

# ─── PATCH /api/tasks/<id> ─────────────────────────────────────────
@app.patch("/api/tasks/<int:task_id>")
@jwt_required()
def toggle_done(task_id):
    current_user_id = get_jwt_identity()
    task = Task.query.filter_by(id=task_id, owner_id=current_user_id).first_or_404()
    task.done = not task.done
    db.session.commit()
    return jsonify(task.as_dict())

# ─── DELETE /api/tasks/<id> ────────────────────────────────────────
@app.delete("/api/tasks/<int:task_id>")
@jwt_required()
def delete_task(task_id):
    current_user_id = get_jwt_identity()
    task = Task.query.filter_by(id=task_id, owner_id=current_user_id).first_or_404()
    db.session.delete(task)
    db.session.commit()
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(debug=True)
