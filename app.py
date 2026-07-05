import sqlite3
import database

from flask import Flask, render_template, request, redirect, session

app = Flask(__name__)
app.secret_key = "student_management_secret"


# ==========================
# Database Connection
# ==========================

def get_connection():
    conn = sqlite3.connect("students.db")
    conn.row_factory = sqlite3.Row
    return conn


# ==========================
# Add Student
# ==========================

def add_student_db(name, roll, branch):

    conn = get_connection()

    conn.execute(
        "INSERT INTO students(name, roll, branch) VALUES (?, ?, ?)",
        (name, roll, branch)
    )

    conn.commit()
    conn.close()


# ==========================
# Get All Students
# ==========================

def get_students():

    conn = get_connection()

    students = conn.execute(
        "SELECT * FROM students ORDER BY id DESC"
    ).fetchall()

    conn.close()

    return students


# ==========================
# Search Students
# ==========================

def search_students(search):

    conn = get_connection()

    students = conn.execute(
        """
        SELECT * FROM students
        WHERE name LIKE ? OR roll LIKE ?
        ORDER BY id DESC
        """,
        ('%' + search + '%', '%' + search + '%')
    ).fetchall()

    conn.close()

    return students


# ==========================
# Get One Student
# ==========================

def get_student(id):

    conn = get_connection()

    student = conn.execute(
        "SELECT * FROM students WHERE id = ?",
        (id,)
    ).fetchone()

    conn.close()

    return student


# ==========================
# Delete Student
# ==========================

def delete_student(id):

    conn = get_connection()

    conn.execute(
        "DELETE FROM students WHERE id = ?",
        (id,)
    )

    conn.commit()
    conn.close()


# ==========================
# Total Students
# ==========================

def total_students():

    conn = get_connection()

    total = conn.execute(
        "SELECT COUNT(*) FROM students"
    ).fetchone()[0]

    conn.close()

    return total


# ==========================
# Login
# ==========================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        if username == "admin" and password == "admin123":

            session["user"] = username

            return redirect("/")

        return render_template(
            "login.html",
            error="Invalid Username or Password"
        )

    return render_template("login.html")


# ==========================
# Home
# ==========================

@app.route("/", methods=["GET", "POST"])
def home():

    if "user" not in session:
        return redirect("/login")

    if request.method == "POST":

        name = request.form["name"]
        roll = request.form["roll"]
        branch = request.form["branch"]

        add_student_db(name, roll, branch)

        return redirect("/")

    search = request.args.get("search")

    if search:
        students = search_students(search)
    else:
        students = get_students()

    total = total_students()

    return render_template(
        "index.html",
        students=students,
        total=total
    )


# ==========================
# Delete
# ==========================

@app.route("/delete/<int:id>")
def delete(id):

    if "user" not in session:
        return redirect("/login")

    delete_student(id)

    return redirect("/")


# ==========================
# Edit
# ==========================

@app.route("/edit/<int:id>")
def edit(id):

    if "user" not in session:
        return redirect("/login")

    student = get_student(id)

    return render_template(
        "edit.html",
        student=student
    )


# ==========================
# Update
# ==========================

@app.route("/update/<int:id>", methods=["POST"])
def update(id):

    if "user" not in session:
        return redirect("/login")

    name = request.form["name"]
    roll = request.form["roll"]
    branch = request.form["branch"]

    conn = get_connection()

    conn.execute(
        """
        UPDATE students
        SET name = ?, roll = ?, branch = ?
        WHERE id = ?
        """,
        (name, roll, branch, id)
    )

    conn.commit()
    conn.close()

    return redirect("/")


# ==========================
# Logout
# ==========================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


# ==========================
# Run Application
# ==========================

if __name__ == "__main__":
    app.run(debug=True)