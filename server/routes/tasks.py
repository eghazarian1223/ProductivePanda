from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from server.extensions import db
from server.models.task import Task
import logging

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

task_controller = Blueprint('task_controller', __name__)


@task_controller.route('/', methods=['GET'])
@login_required
def get_tasks():
    tasks = Task.query.filter_by(user_id=current_user.id).order_by(Task.created_at.desc()).all()
    return jsonify([t.to_dict() for t in tasks])


@task_controller.route('/add', methods=['POST'])
@login_required
def add_task():
    data = request.get_json()
    title = (data or {}).get('title', '').strip()
    priority = (data or {}).get('priority', 3)
    if not title:
        return jsonify({'error': 'Title is required'}), 400
    task = Task(user_id=current_user.id, title=title, priority=int(priority))
    db.session.add(task)
    db.session.commit()
    return jsonify(task.to_dict()), 201


@task_controller.route('/<int:task_id>/complete', methods=['POST'])
@login_required
def complete_task(task_id):
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    task.completed = not task.completed
    db.session.commit()
    return jsonify(task.to_dict())


@task_controller.route('/<int:task_id>', methods=['DELETE'])
@login_required
def delete_task(task_id):
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    db.session.delete(task)
    db.session.commit()
    return jsonify({'deleted': task_id})


def reorganize_tasks_based_on_mood(tasks, mood_score):
    """Sort tasks based on mood: negative = easiest first, positive = highest priority first."""
    if not tasks:
        return tasks
    if mood_score > 0.25:
        return sorted(tasks, key=lambda t: t.priority, reverse=True)
    elif mood_score < -0.25:
        return sorted(tasks, key=lambda t: t.priority)
    return tasks
