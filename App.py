from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
import os
import mysql.connector
print(">>> THIS IS MY APP.PY <<<")

app = Flask(__name__)
app.secret_key = 'your_secret_key'
# --------- LOGIN SYSTEM ---------
users = {"test@example.com": "password123"}
# --------- FILE UPLOAD FOLDER ---------
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# --------- LOST & FOUND UPLOAD FOLDER ---------
LOST_UPLOAD_FOLDER = "static/lost_uploads"
os.makedirs(LOST_UPLOAD_FOLDER, exist_ok=True)
# --------- MYSQL CONNECTION ---------
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Monisha@1234",
    database="campus_connect"
)
cursor = db.cursor(dictionary=True)
# ---------------- ROUTES ----------------
@app.route('/')
def home():
    return render_template('login.html')
@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']
    if email in users and users[email] == password:
        session['user'] = email
        return redirect(url_for('welcome'))
    return "Invalid login. <a href='/'>Try again</a>"

# ---------------- USER REGISTRATION ----------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fullname = request.form['fullname']
        mobile = request.form['mobile']
        email = request.form['email']
        password = request.form['password']
        confirm = request.form['confirm_password']
        # Password match check
        if password != confirm:
            return "Passwords do not match!"
        # Insert user into database
        cursor.execute(
            "INSERT INTO users (fullname, mobile, email, password) VALUES (%s, %s, %s, %s)",
            (fullname, mobile, email, password)
        )
        db.commit()
        # Auto Login & Go To Welcome Page
        session['user'] = email
        return redirect(url_for('welcome'))
    return render_template("register.html")


@app.route('/welcome')
def welcome():
    if 'user' in session:
        cursor.execute("SELECT * FROM announcements ORDER BY id DESC LIMIT 5")
        ann = cursor.fetchall()
        return render_template('welcome.html', announcements=ann)
    return redirect(url_for('home'))

@app.route('/departments')
def departments():
    if 'user' not in session:
        return redirect(url_for('home'))
    return render_template('departments.html')

@app.route('/year_sem')
def year_sem():
    if 'user' not in session:
        return redirect(url_for('home'))
    dept = request.args.get('dept')
    return render_template('year_sem.html', department=dept)
@app.route('/subjects')
def subjects():
    if 'user' not in session:
        return redirect(url_for('home'))
    dept = request.args.get('department')
    year = request.args.get('year')
    semester = request.args.get('semester')
    query = """
        SELECT * FROM notes
        WHERE department = %s AND year = %s AND semester = %s
    """
    cursor.execute(query, (dept, year, semester))
    notes_list = cursor.fetchall()
    return render_template(
        'subjects.html',
        department=dept,
        year=year,
        semester=semester,
        notes=notes_list
    )
from datetime import datetime   
@app.route('/upload_notes', methods=['GET', 'POST'])
def upload_notes():
    if 'user' not in session:
        return redirect(url_for('home'))
    if request.method == 'POST':
        title = request.form['title']
        subject = request.form['subject']
        department = request.form['department']
        year = request.form.get('year')
        semester = request.form.get('semester')
        stream = request.form.get('stream')
        uploader_type = request.form.get('uploader_type')
        roll_no = request.form.get('roll_no')  # empty for teacher
        
        file = request.files['notes_file']
        if file:
            filepath = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(filepath)
        # ⭐ DO NOT insert upload_time because DB already has uploaded_at auto timestamp
        query = """
            INSERT INTO notes 
            (title, subject, filename, department, year, semester, stream, uploader_type, roll_no)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            title, subject, file.filename, department, year, semester,
            stream, uploader_type, roll_no
        )
        cursor.execute(query, values)
        db.commit()
        return render_template(
            "success.html",
            title=title,
            department=department,
            filename=file.filename
        )
    return render_template("upload.html")

@app.route('/notes_list')
def notes_list():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Monisha@1234",
        database="campus_connect"
    )
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM notes")
    notes = cur.fetchall()
    conn.close()
    return render_template("notes_list.html", notes=notes)
@app.route('/uploads/<filename>')
def download_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)
@app.route('/view_note/<filename>')
def view_note(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)
@app.route("/delete_note/<int:id>")
def delete_note(id):
    cursor.execute("DELETE FROM notes WHERE id=%s", (id,))
    db.commit()
    return redirect(request.referrer or url_for("subjects"))

@app.route('/lost_found')
def lost_found():
    if 'user' not in session:
        return redirect(url_for('home'))
    return render_template('lost_found.html')
# Lost & Found Menu (two choices: Report or View)
@app.route('/lost_found_menu')
def lost_found_menu():
    if 'user' not in session:
        return redirect(url_for('home'))
    return render_template('lost_found_menu.html')


# ---------------- LOST ITEM SUBMISSION ----------------
@app.route("/submit_lost", methods=["POST"])
def submit_lost():
    if 'user' not in session:
        return redirect(url_for('home'))
    item_name = request.form.get("item_name")
    phone_number = request.form.get("phone_number")
    location = request.form.get("location")
    date_lost = request.form.get("date_lost")
    image_file = request.files.get("image")
    filename = None
    if image_file and image_file.filename != "":
        filename = image_file.filename
        image_path = os.path.join(LOST_UPLOAD_FOLDER, filename)
        image_file.save(image_path)
    query = """
        INSERT INTO lost_items (item_name, phone_number, location, date_lost, image_filename)
        VALUES (%s, %s, %s, %s, %s)
    """
    values = (item_name, phone_number, location, date_lost, filename)
    cursor.execute(query, values)
    db.commit()
    return redirect(url_for("view_lost_items"))

# ---------------- SHOW LOST ITEMS + SEARCH ----------------
@app.route("/view_lost_items")
def view_lost_items():
    search_query = request.args.get("search", "")
    if search_query:
        cursor.execute("SELECT * FROM lost_items WHERE item_name LIKE %s ORDER BY id DESC",
                       ("%" + search_query + "%",))
    else:
        cursor.execute("SELECT * FROM lost_items ORDER BY id DESC")
    items = cursor.fetchall()
    return render_template("view_lost_items.html", items=items, search_query=search_query)
@app.route("/delete_lost_item/<int:id>")
def delete_lost_item(id):
    cursor.execute("DELETE FROM lost_items WHERE id=%s", (id,))
    db.commit()
    return redirect(url_for("view_lost_items"))



# -------------- NOTES PAGE ---------------
@app.route('/notes')
def notes():
    return render_template("notes.html")
# ================= ADMIN ANNOUNCEMENTS =================
from datetime import datetime
@app.route('/announcements')
def announcements_page():
    cursor.execute("SELECT * FROM announcements ORDER BY id DESC")
    data = cursor.fetchall()
    
    return render_template(
        "announcements.html",
        announcements=data,
        current_time=datetime.now()   # <-- REQUIRED
    )
    

# Admin Dashboard Page
@app.route("/admin/announcements")
def admin_announcements():
    cursor.execute("SELECT * FROM announcements ORDER BY id DESC")
    data = cursor.fetchall()
    return render_template("admin_announcements.html", announcements=data)
@app.route("/admin/add_announcement", methods=["POST"])
def add_announcement():
    message = request.form.get("message")
    file = request.files.get("poster")
    file_path = None
    if file:
        file_path = file.filename
        file.save(os.path.join("static/uploads", file_path))
    cursor.execute(
        "INSERT INTO announcements (message, file_path) VALUES (%s, %s)",
        (message, file_path)
    )
    db.commit()
    return redirect(url_for("admin_announcements"))
@app.route("/admin/delete_announcement/<int:id>")
def delete_announcement(id):
    cursor.execute("DELETE FROM announcements WHERE id=%s", (id,))
    db.commit()
    return redirect(url_for("admin_announcements"))

@app.route("/test-static")
def test_static():
    return "STATIC ROUTE WORKING"

@app.route("/test-image")
def test_image():
    return app.send_static_file("images/study_bg.png")




if __name__ == '__main__':
    app.run(debug=True)
