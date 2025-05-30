from flask import Flask, jsonify, request
from flask_cors import CORS
import json, os

app = Flask(__name__)
CORS(app)

DATA = os.path.join(os.path.dirname(__file__), "data.json")

def load_tasks():
    with open(DATA, "r", encoding="utf-8") as f:
        return json.load(f)

def save_tasks(tasks):
    with open(DATA, "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=4, ensure_ascii=False)

@app.get("/api/tasks")
def get_tasks():
    return jsonify(load_tasks())

@app.post("/api/tasks")
def add_task():
    tasks = load_tasks()
    new_id = max([t["id"] for t in tasks]) + 1 if tasks else 1
    tasks.append({"id": new_id, "text": request.json["text"], "done": False})
    save_tasks(tasks)
    return jsonify(tasks[-1]), 201

@app.delete("/api/tasks/<int:task_id>")
def delete_task(task_id):
    tasks = [t for t in load_tasks() if t["id"] != task_id]
    save_tasks(tasks)
    return jsonify({"status": "ok"})

@app.patch("/api/tasks/<int:task_id>")
def toggle_done(task_id):
    tasks = load_tasks()
    for t in tasks:
        if t["id"] == task_id:
            t["done"] = not t["done"]
            break
    save_tasks(tasks)
    return jsonify({"id": task_id, "done": t["done"]})    

if __name__ == "__main__":
    app.run(debug=True)
