from itertools import repeat
import random
from flask import Flask, jsonify, request, session
import datetime
from tomo import tomo_day
from flask_login import LoginManager, UserMixin, current_user
from flask.helpers import make_response
from flask_login import login_required, login_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import redirect


app = Flask(__name__)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.session_protection = "strong"


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
app.config['SECRET_KEY'] = '2dd950527bc44a56fbb5697b9f2448b3a'
db = SQLAlchemy(app)


class User(UserMixin,db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer(), primary_key=True)
    public_id = db.Column(db.Integer(), unique=True, nullable=False)
    username = db.Column(db.String(20), unique=True)
    firstname = db.Column(db.String(15), nullable=False)
    lastname = db.Column(db.String(15), nullable=False)
    password = db.Column(db.String(), nullable=False)
    emailaddress = db.Column(db.String(30), nullable=False, unique=True)

    def get_id(self):
        return self.public_id


    def __repr__(self) -> str:
        return f'''
        id : {self.id}
        public_id = {self.public_id}
        username : {self.username}
        email : {self.emailaddress}
        firstname  : {self.firstname}
        lastname : {self.lastname}'''

@login_manager.user_loader
def load_user(user_id) :
    return User.query.get(int(user_id))

class Task(UserMixin,db.Model):
    __tablename__ = 'tasks'

    id = db.Column(db.Integer(), primary_key=True, unique=True)
    user_id = db.Column(db.Integer())
    title = db.Column(db.String())
    note = db.Column(db.String())
    date = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)

    def get_id(self):
        return self.user_id

    def __repr__(self) -> str:
        return f'''
        id : {self.user_id}
        title : {self.title}
        date : {self.date}'''

class Status(UserMixin, db.Model) :
    __tablename__ = 'status'

    id = db.Column(db.Integer(), primary_key=True)
    status_id = db.Column(db.Integer())
    task_id = db.Column(db.Integer())
    user_id = db.Column(db.Integer())
    completed = db.Column(db.Boolean(), default=False, nullable=False) 
    d_repeats = db.Column(db.Boolean(), nullable=False) 
    m_repeats = db.Column(db.Boolean(), nullable=False) 
    y_repeats = db.Column(db.Boolean(), nullable=False) 
    deadline = db.Column(db.DateTime(), default=tomo_day) 
    remainders = db.Column(db.String())

    def get_id(self):
        return self.user_id

    def __repr__(self) -> str:
        return f'''
        status_id : {self.status_id}
        completed : {self.completed}
        remainders : {self.remainders}
        deadline : {self.deadline}'''

db.create_all()


@app.route('/home', methods=['GET'])
def home():

    if not ('public_id' in session ):
        return jsonify({
            'Message' : 'Login to access this page'
        }),401
    
    output = []
    users = User.query.all()

    for user in users :
        home = {}
        home['id'] = user.id
        home['public_id'] = user.public_id
        home['username'] = user.username
        home['emailaddress'] = user.emailaddress
        output.append(home)

    return jsonify({'home':{
        'Users':output
        }})

@app.route('/register', methods=['POST'])
def post_register():
    data = request.get_json(force=True)
    hashed_password = generate_password_hash(data['password'], method='sha256')

    if not data :
        return jsonify({
            'message' : 'No data provided'
        })
    
    user = User.query.filter_by(username=data['username']).first()
    if user :
        return jsonify({
            'message' : 'Username already taken..'
        })

    user = User.query.filter_by(emailaddress=data['emailaddress']).first()
    if user :
        return jsonify({
            'message' : 'Email address already taken..'
        })

    user = User(
        public_id = int(random.randint(1,50000)),
        firstname = data['firstname'],
        lastname = data['lastname'],
        emailaddress = data['emailaddress'],
        password = hashed_password,
        username = data['username']
    )

    db.session.add(user)
    db.session.commit()
    return jsonify({
        'Status' : f"Added the user {data['username']}..",
        'id' : f"{user.public_id}"
    })


@app.route('/login', methods=['POST'])
def signin() :
    data = request.get_json(force=True)
    if not data :
        return jsonify({
            'message' : 'No data provided'
        })

    user = User.query.filter_by(emailaddress=data['emailaddress']).first()

    if not user:
        return jsonify({
            'Message' : "No such user."
        })

    if check_password_hash(user.password, data['password']) :
        # login_user(user, remember=True, force=True)
        print(login_user(user))
        print(current_user,'\n\n')
        session['emailaddress'] = data['emailaddress']
        session['public_id'] = user.public_id
        next = request.args.get('next')

        return jsonify({
            'Message' : 'You are logged in',
            'next' : f'{redirect(next)}'
        }),200

    return jsonify({
        'Message' : "Emailaddress or Password does not match"
    })


@app.route('/logout')
def user() :
    if not ('public_id' in session ):
        return jsonify({
            'Message' : 'Login to access this page'
        }),401

    session.pop('public_id')
    session.pop('emailaddress')

    return make_response('logged out user', 200)
    

@app.route('/task', methods=['POST'])
def post_task():
    if not ('public_id' in session ):
        return jsonify({
            'Message' : 'Login to access this page'
        }),401

    data = request.get_json()
    
    new_task = Task(
    title = data['title'],
    note = data['note'],
    user_id = session['public_id']
    )

    db.session.add(new_task)
    db.session.commit()
    
    if not 'd_repeats' in data :
        data['d_repeats'] = False
    if not 'deadline' in data :
        data['deadline'] = tomo_day()
    if not 'm_repeats' in data :
        data['m_repeats'] = False
    if not 'y_repeats' in data :
        data['y_repeats'] = False
    if not 'remainders' in data :
        data['remainders'] = 'Remainder for you'
    
 
    task_status = Status(
    status_id = random.randint(1, 50000),
    task_id = new_task.id,
    user_id = session['public_id'],
    deadline = data['deadline'],
    d_repeats = data['d_repeats'],
    m_repeats = data['m_repeats'],
    y_repeats = data['y_repeats'],
    remainders = data['remainders']
    )

    db.session.add(task_status)
    db.session.commit()
    return jsonify({'message' : 'task created'})

@app.route('/task', methods=['GET'])
def get_task():

    if not ('public_id' in session ):
        return jsonify({
            'Message' : 'Login to access this page'
        }),401


    all_task = Task.query.filter_by(user_id=session['public_id']).all()
    output = []

    for task in all_task :
        task_dict = {}
        task_dict['note'] = task.note
        task_dict['id'] = task.id
        task_dict['user_id'] = task.user_id
        task_dict['date'] = task.date
        output.append(task_dict)
    
    return jsonify({
        'tasks' : output
    })


@app.route('/task/<task_id>', methods=['PUT'])
def complete_task(task_id):

    if not ('public_id' in session ):
        return jsonify({
            'Message' : 'Login to access this page'
        }),401

    data = request.get_json(force=True)
    task = Task(id=task_id, user_id=session['public_id']).first()
    status = Status.query.filter_by(task_id=task_id, user_id=session['public_id']).first()
    
    if not task :
        return jsonify({
            'message' : 'No task found!!',
        })

    if not status :
        return jsonify({
        'message' : 'no status assosiated to the task found!'
    })

    if data['note'] :
        task.note = data['note']
    if data['title'] :
        task.title = data['title']
    if data['completed'] :
        status.completed = data['completed']
    if data['deadline'] :
        status.deadline = data['deadline']
    if data['d_repeats'] :
        status.deadline = data['d_repeats']
    if data['m_repeats'] :
        status.deadline = data['m_repeats']
    if data['y_repeats'] :
        status.deadline = data['y_repeats']
    if data['remainders'] :
        status.remainders = data['remainders']
    db.session.commit()

    return jsonify({
        'Task' : "task is updated!!!",
        'Status' : 'status is updated'
    })

@app.route('/task/<task_id>', methods=['DELETE'])
def delete_task(task_id):

    if not ('public_id' in session ):
        return jsonify({
            'Message' : 'Login to access this page'
        }),401


    task = Task.query.filter_by(id=task_id, user_id=session['public_id']).first()
    status = Status.query.filter_by(task_id=task_id, user_id=session['public_id']).first()
    if not task :
        return jsonify({
            'message' : 'no task found!'
        })

    if not status :
        return jsonify({
            'message' : 'no status assosiated to the task found!'
        })
        
    db.session.delete(task)
    db.session.delete(status)
    db.session.commit()
    return jsonify({
        'message' : 'Task item deleted!'
    })


@app.route('/status')
def task_status() :

    if not ('public_id' in session ):
        return jsonify({
            'Message' : 'Login to access this page'
        }),401
    
    user_status = Status.query.filter_by(user_id=session['public_id']).all()
    user_task = Task.query.filter_by(user_id=session['public_id']).all()
    output = []

    for status,task in zip(user_status, user_task) :
        status_dict = {}
        status_dict['task_id'] = status.task_id
        status_dict['d_repeats'] = status.d_repeats
        status_dict['m_repeats'] = status.m_repeats
        status_dict['y_repeats'] = status.y_repeats
        status_dict['status_id'] = status.status_id
        status_dict['user_id'] = status.user_id
        status_dict['deadline'] = status.deadline
        status_dict['completed'] = status.completed
        status_dict['remainders'] = status.remainders
        status_dict['title'] = task.title
        status_dict['note'] = task.note
        status_dict['date'] = task.date
        if datetime.datetime.now() >= status.deadline :
            status_dict['remind_alert'] = True
        status_dict['remind_alert'] = False
        output.append(status_dict)
    
    return jsonify({
        'Profile' : output
    })

if __name__ == "__main__":
    app.run(debug=True)
