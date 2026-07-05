from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class WorkflowModel(Base):
    __tablename__ = "workflowmodel"
    id = Column(String, primary_key=True)
    workspace_id = Column(String, primary_key=True)
    finalLifecycleState = Column("finallifecyclestate", String)
    creationdate = Column(DateTime)
    author_workspace_id = Column(String)
    author_login = Column(String)
    acl_id = Column(Integer, ForeignKey("acl.id"))


class Workflow(Base):
    __tablename__ = "workflow"
    id = Column(Integer, primary_key=True)
    aborteddate = Column(DateTime)
    finallifecyclestate = Column(String)


class Activity(Base):
    __tablename__ = "activity"
    step = Column(Integer, primary_key=True)
    workflow_id = Column(Integer, ForeignKey("workflow.id"), primary_key=True)
    dtype = Column(String)
    lifecyclestate = Column(String)
    taskstocomplete = Column(Integer)


class ActivityModel(Base):
    __tablename__ = "activitymodel"
    id = Column(Integer, primary_key=True, autoincrement=True)
    step = Column(Integer)
    dtype = Column(String)
    lifecyclestate = Column(String)
    workflowmodel_id = Column(String, ForeignKey("workflowmodel.id"))
    workspace_id = Column(String)
    taskstocomplete = Column(Integer)


class Task(Base):
    __tablename__ = "task"
    num = Column(Integer, primary_key=True)
    activity_step = Column(Integer, primary_key=True)
    workflow_id = Column(Integer, primary_key=True)
    title = Column(String)
    instructions = Column(Text)
    status = Column(Integer)  # 0=TODO, 1=IN_PROGRESS, 2=APPROVED, 3=REJECTED
    worker_login = Column(String)
    worker_workspace_id = Column(String)
    duration = Column(Integer)
    signature = Column(Text)
    closuredate = Column(DateTime)
    closurecomment = Column(String)
    startdate = Column(DateTime)
    targetiteration = Column(Integer)


class TaskModel(Base):
    __tablename__ = "taskmodel"
    num = Column(Integer, primary_key=True)
    activitymodel_id = Column(Integer, primary_key=True)
    title = Column(String)
    instructions = Column(Text)
    duration = Column(Integer)
    role_workspace_id = Column(String)
    role_name = Column(String)


class WebhookApp(Base):
    __tablename__ = "webhookapp"
    id = Column(Integer, primary_key=True, autoincrement=True)
    dtype = Column(String)  # SIMPLE_HTTP / AWS_SNS
    auth = Column(String)
    method = Column(String)
    uri = Column(String)
    awsaccount = Column(String)
    awssecret = Column(String)
    region = Column(String)
    topicarn = Column(String)


class Webhook(Base):
    __tablename__ = "webhook"
    id = Column(Integer, primary_key=True, autoincrement=True)
    active = Column(Boolean)
    name = Column(String)
    workspace_id = Column(String)
    webhookapp_id = Column(Integer, ForeignKey("webhookapp.id"))
