from . import db
from flask_login import UserMixin
from datetime import datetime

class User(db.Model, UserMixin):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=True)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), default="Developer")
    owned_projects = db.relationship("Project", backref="owner", lazy=True)
    tasks = db.relationship("Task", backref="assigned_user", lazy=True)
    memberships = db.relationship("ProjectMembership", back_populates="user")
    @property
    def all_projects(self):
        owned = set(self.owned_projects)
        member = set([m.project for m in self.memberships])
        return list(owned.union(member))




class Project(db.Model):
    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    sprints = db.relationship("Sprint", backref="project", lazy=True)
    tasks = db.relationship("Task", backref="project", lazy=True)
    user_stories = db.relationship("UserStory", backref="project", lazy=True)
    memberships = db.relationship("ProjectMembership", back_populates="project")




class Sprint(db.Model):
    __tablename__ = "sprint"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    goal = db.Column(db.Text)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    tasks = db.relationship("Task", backref="sprint", lazy=True)
    user_stories = db.relationship("UserStory", backref="sprint", lazy=True)




class Task(db.Model):
    __tablename__ = "task"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(50), default="To Do")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    sprint_id = db.Column(db.Integer, db.ForeignKey("sprint.id"), nullable=True)
    assigned_to = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)


class UserStory(db.Model):
    __tablename__ = "user_stories"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="To Do")
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    sprint_id = db.Column(db.Integer, db.ForeignKey('sprint.id'))


    def __repr__(self):
        return f"<UserStory {self.title}>"

class ProjectMembership(db.Model):
    __tablename__ = "project_memberships"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    role = db.Column(db.String(50), nullable=False, default="Developer")
    user = db.relationship("User", back_populates="memberships")
    project = db.relationship("Project", back_populates="memberships")


