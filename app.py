from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

# Initialize Flask app
app = Flask(__name__)

# Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(100), nullable=False)

class Form(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    subtitle = db.Column(db.String(100), nullable=False)

class FormQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    question = db.Column(db.String(500), nullable=False)
    question_type = db.Column(db.String(50), nullable=False)
    options = db.Column(db.String(50))

class FormResponse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    question_title = db.Column(db.String(100), nullable=False)
    answer = db.Column(db.String(100), nullable=False)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Redirect users to login if not authenticated
app.secret_key = 'your_secret_key'  # Required for session management

# Create database tables
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        hashed_password = generate_password_hash("admin123", method='pbkdf2:sha256')
        admin_user = User(username='admin', password=hashed_password)
        db.session.add(admin_user)
        db.session.commit()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash('Invalid credentials', 'danger')
    
    return render_template('Auth/login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# Routes
@app.route('/')
def home():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    return render_template('Main.html')

@app.route('/create-form', methods=['GET', 'POST'])
@login_required
def create_form():
    if request.method == 'POST':
        title = request.form.get('title')
        subtitle = request.form.get('subtitle')
        question_list = request.form.getlist('question_list')
        question_type_list = request.form.getlist('question_type_list')
        option_list = request.form.getlist('option_list')
        
        new_form = Form(title=title, subtitle=subtitle)
        db.session.add(new_form)

        for question, question_type, option in zip(question_list, question_type_list, option_list):
            new_form_question = FormQuestion(title=title, question=question, question_type=question_type, options=option)
            db.session.add(new_form_question)
        
        db.session.commit()
        return redirect(url_for('create_form'))
    else:
        return render_template('Create/Form.html')
    
@app.route('/view-forms')
def view_forms():
    forms = Form.query.all()
    return render_template('View/AllForms.html', forms=forms)

@app.route('/view-form-questions/<string:title>')
def view_form_questions(title):
    form_questions = FormQuestion.query.filter_by(title=title).all()
    print("Form Questions :", form_questions)
    return render_template('View/AllFormQuestions.html', form_questions=form_questions, title=title)

@app.route('/submit_form', methods=['POST'])
def submit_form():
    try:
        data = request.form  # Get form data
        name = data.get('name')
        email = data.get('email')
        title = data.get('title')

        print('title :', title)

        if not name or not email:
            return jsonify({'error': 'Name and Email are required'}), 400

        responses = []
        for key, value in data.items():
            if key.startswith("question_"):  # Handle dynamic questions
                question_index = key.split("_")[1]  # Extract index from "question_X"
                question_text = request.form.get(f"question_text_{question_index}")  # Get the actual question
                
                if not question_text:
                    continue  # Skip if question text is missing

                # Handle checkboxes (multiple answers)
                if isinstance(value, list):
                    value = ", ".join(value)  # Store multiple choices as CSV

                response = FormResponse(name=name, email=email,title=title, question_title=question_text, answer=value)
                db.session.add(response)
                responses.append({'question': question_text, 'answer': value})

        db.session.commit()
        return render_template('View/form_success.html')

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/responses')
@login_required
def view_responses():
    forms = Form.query.all()
    return render_template('View/responses.html', forms=forms)

@app.route('/view-question-responses/<string:title>')
@login_required
def view_question_responses(title):
    form_responses = FormResponse.query.filter_by(title=title).all()

    # Collect unique names and emails
    unique_entries = set()
    for form_details in form_responses:
        unique_entries.add((form_details.name, form_details.email))

    return render_template('View/form_responses.html', title=title, entries=list(unique_entries))

@app.route('/person-responses/<string:title>/<string:email>')
@login_required
def person_responses(title, email):
    responses = FormResponse.query.filter_by(title=title, email=email).all()
    
    return render_template('View/person_responses.html', responses=responses, email=email)


if __name__ == '__main__':
    app.run(debug=True)