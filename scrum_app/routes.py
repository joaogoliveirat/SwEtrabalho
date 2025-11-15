from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from . import db, login_manager
from .models import User, Project, UserStory, Sprint, Task, ProjectMembership
from datetime import datetime

main = Blueprint('main', __name__)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@main.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('main.login'))


@main.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])

        if User.query.filter_by(username=username).first():
            flash('Usuário já existe!', 'danger')
        else:
            user = User(username=username, password=password)
            db.session.add(user)
            db.session.commit()
            flash('Conta criada com sucesso!', 'success')
            return redirect(url_for('main.login'))
    return render_template('register.html')


@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('main.dashboard'))
        else:
            flash('Credenciais inválidas!', 'danger')
    return render_template('login.html')


@main.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.login'))

@main.route('/dashboard')
@login_required
def dashboard():
    projects = current_user.all_projects
    return render_template('dashboard.html', projects=projects)



@main.route('/project/new', methods=['POST'])
@login_required
def new_project():
    name = request.form['name']
    if not name or not name.strip():
        flash('Nome inválido.', 'warning')
        return redirect(url_for('main.dashboard'))

    project = Project(name=name.strip(), owner_id=current_user.id)
    db.session.add(project)
    db.session.commit()
    membership = ProjectMembership(
    project_id=project.id,
    user_id=current_user.id,
    role="Product Owner"
)
    db.session.add(membership)
    db.session.commit()
    flash('Projeto criado!', 'success')
    return redirect(url_for('main.dashboard'))


@main.route('/project/<int:project_id>')
@login_required
def view_project(project_id):
    project = Project.query.get_or_404(project_id)

    if not user_has_access(project):
        flash("Acesso negado.", "danger")
        return redirect(url_for('main.dashboard'))

    sprints = project.sprints
    user_stories = project.user_stories
    tasks = project.tasks

    return render_template(
        'project.html',
        project=project,
        sprints=sprints,
        user_stories=user_stories,
        tasks=tasks
    )


@main.route('/project/<int:project_id>/sprint/new', methods=['GET', 'POST'])
@login_required
def new_sprint(project_id):
    project = Project.query.get_or_404(project_id)

    if not user_has_access(project):
        flash("Acesso negado.", "danger")
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        goal = request.form.get('goal', '').strip()
        start_raw = request.form.get('start_date', '')
        end_raw = request.form.get('end_date', '')

        if not name:
            flash("Nome da sprint é obrigatório.", "warning")
            return render_template('new_sprint.html', project=project)

        start = None
        end = None
        try:
            if start_raw:
                start = datetime.strptime(start_raw, "%Y-%m-%d").date()
            if end_raw:
                end = datetime.strptime(end_raw, "%Y-%m-%d").date()
        except ValueError:
            flash("Formato de data inválido. Use YYYY-MM-DD.", "warning")
            return render_template('new_sprint.html', project=project)

        sprint = Sprint(
            name=name,
            start_date=start,
            end_date=end,
            goal=goal,
            project_id=project_id
        )

        db.session.add(sprint)
        db.session.commit()
        flash("Sprint criada!", "success")
        return redirect(url_for('main.view_project', project_id=project_id))

    return render_template('new_sprint.html', project=project)

@main.route('/sprint/<int:sprint_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_sprint(sprint_id):
    sprint = Sprint.query.get_or_404(sprint_id)
    project = sprint.project

    if not user_has_access(project):
        flash("Acesso negado.", "danger")
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        sprint.name = request.form.get('name', sprint.name).strip()
        sprint.goal = request.form.get('goal', sprint.goal).strip()
        start_raw = request.form.get('start_date', '')
        end_raw = request.form.get('end_date', '')

        try:
            if start_raw:
                sprint.start_date = datetime.strptime(start_raw, "%Y-%m-%d").date()
            else:
                sprint.start_date = None
            if end_raw:
                sprint.end_date = datetime.strptime(end_raw, "%Y-%m-%d").date()
            else:
                sprint.end_date = None
        except ValueError:
            flash("Formato de data inválido. Use YYYY-MM-DD.", "warning")
            return render_template('edit_sprint.html', sprint=sprint)

        db.session.commit()
        flash("Sprint atualizada!", "success")
        return redirect(url_for('main.view_project', project_id=project.id))

    return render_template('edit_sprint.html', sprint=sprint)

@main.route('/sprint/<int:sprint_id>')
@login_required
def sprint_details(sprint_id):
    sprint = Sprint.query.get_or_404(sprint_id)
    project = sprint.project

    if not user_has_access(project):
        flash("Acesso negado.", "danger")
        return redirect(url_for('main.dashboard'))

    sprint_stories = UserStory.query.filter_by(
        project_id=project.id,
        sprint_id=sprint.id
        ).all()

    available_stories = UserStory.query.filter_by(
        project_id=project.id,
        sprint_id=None
        ).all()


    return render_template(
        'sprint_details.html',
        sprint=sprint,
        sprint_stories=sprint_stories,
        available_stories=available_stories,
        project=project
    )


@main.route('/sprint/<int:sprint_id>/delete', methods=['POST'])
@login_required
def delete_sprint(sprint_id):
    sprint = Sprint.query.get_or_404(sprint_id)
    project = sprint.project

    if project.owner_id != current_user.id:
        flash("Acesso negado.", "danger")
        return redirect(url_for('main.dashboard'))
    db.session.delete(sprint)
    db.session.commit()
    flash("Sprint excluída!", "danger")
    return redirect(url_for('main.view_project', project_id=project.id))



@main.route('/project/<int:project_id>/userstory/new', methods=['GET', 'POST'])
@login_required
def new_userstory(project_id):
    project = Project.query.get_or_404(project_id)

    if not user_has_access(project):
        flash("Acesso negado.", "danger")
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        desc = request.form.get('description', '').strip()

        if not title:
            flash("Título obrigatório.", "warning")
            return render_template('new_userstory.html', project=project)

        us = UserStory(title=title, description=desc, project_id=project_id)
        db.session.add(us)
        db.session.commit()

        flash("User Story criada!", "success")
        return redirect(url_for('main.view_project', project_id=project_id))

    return render_template('new_userstory.html', project=project)


@main.route('/project/<int:project_id>/task/new', methods=['GET', 'POST'])
@login_required
def new_task(project_id):
    project = Project.query.get_or_404(project_id)

    if not user_has_access(project):
        flash("Acesso negado.", "danger")
        return redirect(url_for('main.dashboard'))

    sprints = Sprint.query.filter_by(project_id=project_id).all()
    users = User.query.all()

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        desc = request.form.get('description', '').strip()
        sprint_id = request.form.get('sprint_id') or None
        assigned_to = request.form.get('assigned_to') or None

        task = Task(
            title=title,
            description=desc,
            project_id=project_id,
            sprint_id=(int(sprint_id) if sprint_id else None),
            assigned_to=(int(assigned_to) if assigned_to else None)
        )

        db.session.add(task)
        db.session.commit()
        flash("Task criada!", "success")
        return redirect(url_for('main.view_project', project_id=project_id))

    return render_template('new_task.html', project=project, sprints=sprints, users=users)

@main.route('/project/<int:project_id>/userstory/<int:us_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_userstory(project_id, us_id):
    project = Project.query.get_or_404(project_id)
    if project.owner_id != current_user.id:
        flash("Acesso negado.", "danger")
        return redirect(url_for('main.dashboard'))

    us = UserStory.query.get_or_404(us_id)
    if request.method == 'POST':
        us.title = request.form.get('title', us.title).strip()
        us.description = request.form.get('description', us.description).strip()
        us.status = request.form.get('status', us.status)
        db.session.commit()
        flash("User Story atualizada!", "success")
        return redirect(url_for('main.view_project', project_id=project_id))

    return render_template('edit_userstory.html', project=project, us=us)

@main.route('/project/<int:project_id>/userstory/<int:us_id>/delete', methods=['POST'])
@login_required
def delete_userstory(project_id, us_id):
    project = Project.query.get_or_404(project_id)
    if project.owner_id != current_user.id:
        flash("Acesso negado.", "danger")
        return redirect(url_for('main.dashboard'))

    us = UserStory.query.get_or_404(us_id)
    db.session.delete(us)
    db.session.commit()
    flash("User Story excluída!", "danger")
    return redirect(url_for('main.view_project', project_id=project_id))

@main.route('/project/<int:project_id>/task/<int:task_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_task(project_id, task_id):
    project = Project.query.get_or_404(project_id)
    if project.owner_id != current_user.id:
        flash("Acesso negado.", "danger")
        return redirect(url_for('main.dashboard'))

    task = Task.query.get_or_404(task_id)
    sprints = Sprint.query.filter_by(project_id=project_id).all()
    users = User.query.all()

    if request.method == 'POST':
        task.title = request.form.get('title', task.title).strip()
        task.description = request.form.get('description', task.description).strip()
        sprint_id = request.form.get('sprint_id') or None
        assigned_to = request.form.get('assigned_to') or None
        task.sprint_id = int(sprint_id) if sprint_id else None
        task.assigned_to = int(assigned_to) if assigned_to else None
        task.status = request.form.get('status', task.status)
        db.session.commit()
        flash("Task atualizada!", "success")
        return redirect(url_for('main.view_project', project_id=project_id))

    return render_template('edit_task.html', project=project, task=task, sprints=sprints, users=users)


@main.route('/project/<int:project_id>/task/<int:task_id>/delete', methods=['POST'])
@login_required
def delete_task(project_id, task_id):
    project = Project.query.get_or_404(project_id)
    if project.owner_id != current_user.id:
        flash("Acesso negado.", "danger")
        return redirect(url_for('main.dashboard'))

    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    flash("Task excluída!", "danger")
    return redirect(url_for('main.view_project', project_id=project_id))


@main.route('/sprint/<int:sprint_id>/add_us', methods=['POST'])
@login_required
def add_us_to_sprint(sprint_id):
    sprint = Sprint.query.get_or_404(sprint_id)
    project = sprint.project

    if project.owner_id != current_user.id:
        flash("Acesso negado.", "danger")
        return redirect(url_for('main.dashboard'))

    us_id = request.form.get('userstory_id')

    if not us_id:
        flash("Nenhuma user story selecionada.", "warning")
        return redirect(url_for('main.sprint_details', sprint_id=sprint_id))

    us = UserStory.query.get_or_404(us_id)
    us.sprint_id = sprint_id

    db.session.commit()
    flash("User Story adicionada à Sprint!", "success")
    return redirect(url_for('main.sprint_details', sprint_id=sprint_id))


@main.route('/sprint/<int:sprint_id>/remove_us/<int:us_id>', methods=['POST'])
@login_required
def remove_us_from_sprint(sprint_id, us_id):
    sprint = Sprint.query.get_or_404(sprint_id)
    project = sprint.project

    if project.owner_id != current_user.id:
        flash("Acesso negado.", "danger")
        return redirect(url_for('main.dashboard'))

    us = UserStory.query.get_or_404(us_id)
    us.sprint_id = None

    db.session.commit()
    flash("User Story removida da Sprint.", "warning")
    return redirect(url_for('main.sprint_details', sprint_id=sprint_id))

@main.route('/project/<int:project_id>/board')
@login_required
def kanban_board(project_id):
    project = Project.query.get_or_404(project_id)

    tasks_todo = Task.query.filter_by(project_id=project_id, status="To Do").all()
    tasks_doing = Task.query.filter_by(project_id=project_id, status="Doing").all()
    tasks_done = Task.query.filter_by(project_id=project_id, status="Done").all()

    return render_template(
        'kanban.html',
        project=project,
        tasks_todo=tasks_todo,
        tasks_doing=tasks_doing,
        tasks_done=tasks_done
    )

@main.route('/task/<int:task_id>/status/<string:new_status>', methods=['POST'])
@login_required
def update_task_status(task_id, new_status):
    task = Task.query.get_or_404(task_id)

    if new_status not in ["To Do", "Doing", "Done"]:
        flash("Status inválido!", "danger")
        return redirect(request.referrer)

    task.status = new_status
    db.session.commit()
    flash("Status atualizado!", "success")

    return redirect(request.referrer)

@main.route('/project/<int:project_id>/members')
@login_required
def project_members(project_id):
    project = Project.query.get_or_404(project_id)

    if project.owner_id != current_user.id:
        flash("Acesso negado.", "danger")
        return redirect(url_for('main.dashboard'))

    existing_user_ids = [m.user_id for m in project.memberships]
    available_users = User.query.filter(User.id.not_in(existing_user_ids)).all()

    return render_template(
        'project_members.html',
        project=project,
        available_users=available_users
    )

@main.route('/project/<int:project_id>/members/add', methods=['POST'])
@login_required
def add_project_member(project_id):
    project = Project.query.get_or_404(project_id)

    if project.owner_id != current_user.id:
        flash("Acesso negado.", "danger")
        return redirect(url_for('main.dashboard'))

    user_id = request.form.get('user_id')
    role = request.form.get('role')

    if not user_id or not role:
        flash("Selecione usuário e papel.", "warning")
        return redirect(url_for('main.project_members', project_id=project_id))

    membership = ProjectMembership(
        project_id=project_id,
        user_id=user_id,
        role=role
    )

    db.session.add(membership)
    db.session.commit()

    flash("Membro adicionado!", "success")
    return redirect(url_for('main.project_members', project_id=project_id))

@main.route('/project/<int:project_id>/members/<int:member_id>/delete', methods=['POST'])
@login_required
def delete_project_member(project_id, member_id):
    project = Project.query.get_or_404(project_id)

    if project.owner_id != current_user.id:
        flash("Acesso negado.", "danger")
        return redirect(url_for('main.dashboard'))

    membership = ProjectMembership.query.get_or_404(member_id)

    if membership.user_id == project.owner_id:
        flash("Não é possível remover o Product Owner do projeto.", "danger")
        return redirect(url_for('main.project_members', project_id=project_id))

    db.session.delete(membership)
    db.session.commit()

    flash("Membro removido!", "warning")
    return redirect(url_for('main.project_members', project_id=project_id))

def user_has_access(project):
    return (
        project.owner_id == current_user.id or
        any(m.user_id == current_user.id for m in project.memberships)
    )





