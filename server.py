from flask import Flask, request, redirect, render_template, session, flash
from mysqlconnection import MySQLConnector
import re, md5, os, binascii
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$')
# PASSWORD_REGEX = re.compile(r'\d.*[A-Z]|[A-Z].*\d') #searches for a upper case followed by a number and the |(or operator) looks for a number then a upper case
NAME_REGEX = re.compile(r'\W.*[A-Za-z]|[A-Za-z]\.*\W|\d.*[A-Za-z]|[A-Za-z].*\d')
app = Flask(__name__)
app.secret_key = "SecretBox"
mysql = MySQLConnector(app,'walldb')
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def new_user():
    count = 0
    if request.form['action'] == 'register':
        if len(request.form['email']) < 1:
            flash("Email is blank!", "email")
        elif not EMAIL_REGEX.match(request.form['email']):
            flash("Invalid Email Address!", "email")
        else:
            count += 1
        if len(request.form['first_name']) <1:
            flash("First name is blank!", "first_name")
        elif len(request.form['first_name']) > 0 and len(request.form['first_name']) < 2:
            flash("First name needs to be AT LEAST 2 characters long!", "first_name")
        elif NAME_REGEX.search(request.form['first_name']):
            flash("Invalid First Name!", "first_name")
        else:
            count += 1
        if len(request.form['last_name']) <1:
            flash("Last name is blank!", "last_name")
        elif len(request.form['last_name']) > 0 and len(request.form['last_name']) < 2:
            flash("Last name needs to be AT LEAST 2 characters long!", "first_name")
        elif NAME_REGEX.search(request.form['last_name']):
            flash("Invalid Last Name!", "last_name")
        else:
            count += 1
        if len(request.form['password']) <1:
            flash("Password is blank!", "password")
        elif len(request.form['password']) > 0 and len(request.form['password']) < 9:
            flash("Password is shorter than 8 characters!", "password")
        # elif not PASSWORD_REGEX.match(request.form['password']):
        #     flash("Password needs at least 1 Upper case and 1 number", "password")
        else:
            count += 1
        if len(request.form['confirm_password']) <1:
            flash("Password Confirmation is blank!", "confirm_password")
        elif request.form['confirm_password'] != request.form['password']:
            flash("Password and confirmation password do not match!", "confirm_password")
        else:
            count += 1

        if count == 5:
            email = request.form['email']
            query1 = "SELECT * FROM users WHERE users.email = :email"
            data1 = { 'email': email }
            user = mysql.query_db(query1, data1)
            if len(user) != 0:
                flash("Email has already been registered.  Please try another email!")
            else:
                password = request.form['password']
                salt = binascii.b2a_hex(os.urandom(15))
                hashed_pw = md5.new(password + salt).hexdigest()
                query2 = "INSERT INTO users (first_name, last_name, email, password, salt, created_at, updated_at) VALUES (:first_name, :last_name, :email, :hashed_pw, :salt, NOW(), NOW())"
                data2 = {
                    'first_name': request.form['first_name'],
                    'last_name': request.form['last_name'],
                    'email': email,
                    'hashed_pw': hashed_pw,
                    'salt': salt
                    }
                mysql.query_db(query2, data2)
                flash("Thank you for Registering!")
        else:
            flash("Some fields are missing...")

    elif request.form['action'] == 'login':
        email = request.form['email']
        if len(email) < 1:
            flash("No email address was entered!")
        else:
            session['email'] = email
            password = request.form['password']
            query = "SELECT * FROM users WHERE users.email = :email"
            data = { 'email': email }
            user = mysql.query_db(query, data)
            session['id'] = user[0]['id']
            session['first_name'] = user[0]['first_name']
            session['last_name'] = user[0]['last_name']
            session['first_name'] = str(session['first_name'])
            session['last_name'] = str(session['last_name'])
            if len(user) != 0:
                encrypted_pw = md5.new(password + user[0]['salt']).hexdigest()
                if user[0]['password'] == encrypted_pw:
                    return redirect('/wall')
                else:
                    flash("PASSWORD DOES NOT MATCH!", "login")
            else:
                flash("EMAIL ADDRESS INVALID", "login")

    return redirect('/')

@app.route('/wall')
def success():
    query = 'SELECT users.first_name, users.last_name, messages.id, messages.message, messages.created_at, messages.updated_at FROM users JOIN messages ON users.id = messages.user_id ORDER BY messages.created_at DESC'
    messages = mysql.query_db(query)
    
    query1 = 'SELECT users.first_name, users.last_name, comments.message_id, comments.user_id, comments.comment, comments.created_at, comments.updated_at FROM comments JOIN users ON users.id = comments.user_id JOIN messages ON messages.id = comments.message_id ORDER BY comments.created_at'
    comments = mysql.query_db(query1)

    user_name = session['first_name']+" "+session['last_name']
    print user_name
    return render_template('wall.html', all_messages = messages, all_comments = comments, name = user_name)

@app.route('/posting', methods = ['POST'])
def posting():
    if request.form['action'] == 'posts':
        post_query = "INSERT INTO messages (user_id, message, created_at, updated_at) VALUES (:user_id, :message, NOW(), NOW())"
        post_data = {
            'user_id': session['id'],
            'message': request.form['message']
            }
        mysql.query_db(post_query, post_data)
    elif request.form['action'] == 'comment':
        comment_query = "INSERT INTO comments (message_id, user_id, comment, created_at, updated_at) VALUES (:message_id, :user_id, :comment, NOW(), NOW())"
        comment_data = {
            'message_id': request.form['message_id'],
            'user_id': session['id'],
            'comment': request.form['comment']
            }
        mysql.query_db(comment_query, comment_data)
    elif request.form['action'] == 'delete_post':
        delete_message_query = "DELETE FROM messages WHERE user_id = :user_id AND id = :id"
        delete_message_data = {
            'user_id': session['id'],
            'id': request.form['message_id']
        }
        mysql.query_db(delete_message_query, delete_message_data)
    elif request.form['action'] == 'logout':
        session.clear()
        return redirect('/')
    return redirect('/wall')

app.run(debug=True)