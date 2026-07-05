import sqlite3
import database

from flask import Flask, render_template, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "student_management_secret"


def get_connection():
    conn = sqlite3.connect("students.db")
    conn.row_factory = sqlite3.Row
    return conn


# ==========================
# Create Users Table
# ==========================

def create_users_table():
    conn = get_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


create_users_table()



# ==========================
# Student Functions
# ==========================

def add_student_db(name, roll, branch, user_id):
    conn = get_connection()

    conn.execute(
         "INSERT INTO students(name, roll, branch, user_id) VALUES (?, ?, ?, ?)",
        (name, roll, branch, user_id)
    )

    conn.commit()
    conn.close()


def get_students(user_id):
    conn = get_connection()

    students = conn.execute(
        "SELECT * FROM students WHERE user_id = ? ORDER BY id DESC",
        (user_id,)
    ).fetchall()

    conn.close()
    return students


def search_students(search, user_id):
    conn = get_connection()

    students = conn.execute(
        """
        SELECT * FROM students
        WHERE user_id = ?
        AND (name LIKE ? OR roll LIKE ?)
        ORDER BY id DESC
        """,
        (user_id, '%' + search + '%', '%' + search + '%')
    ).fetchall()

    conn.close()
    return students


def get_student(id, user_id):
    conn = get_connection()

    student = conn.execute(
        "SELECT * FROM students WHERE id = ? AND user_id = ?",
        (id, user_id)
    ).fetchone()

    conn.close()
    return student


def delete_student(id):
    conn = get_connection()

    conn.execute(
        "DELETE FROM students WHERE id = ?",
        (id,)
    )

    conn.commit()
    conn.close()


def total_students(user_id):
    conn = get_connection()

    total = conn.execute(
        "SELECT COUNT(*) FROM students WHERE user_id = ?",
        (user_id,)
    ).fetchone()[0]

    conn.close()
    return total


# ==========================
# Signup
# ==========================

@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if password != confirm_password:
            return render_template(
                "signup.html",
                error="Passwords do not match"
            )

        hashed_password = generate_password_hash(password)

        conn = get_connection()

        try:
            conn.execute(
                "INSERT INTO users(username, email, password) VALUES (?, ?, ?)",
                (username, email, hashed_password)
            )

            conn.commit()
            return redirect("/login")

        except sqlite3.IntegrityError:
            return render_template(
                "signup.html",
                error="Username or Email already exists"
            )

        finally:
            conn.close()

    return render_template("signup.html")


# ==========================
# Login
# ==========================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_connection()

        user = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()

        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user"] = user["username"]
            session["user_id"] = user["id"]

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

        add_student_db(name, roll, branch, session["user_id"])

        return redirect("/")

    search = request.args.get("search")

    if search:
        students = search_students(search, session["user_id"])
    else:
        students = get_students(session["user_id"])

    total = total_students(session["user_id"])

    return render_template(
        "index.html",
        students=students,
        total=total
    )


@app.route("/delete/<int:id>")
def delete(id):

    if "user" not in session:
        return redirect("/login")

    conn = get_connection()

    conn.execute(
        "DELETE FROM students WHERE id = ? AND user_id = ?",
        (id, session["user_id"])
    )

    conn.commit()
    conn.close()

    return redirect("/")


@app.route("/edit/<int:id>")
def edit(id):

    if "user" not in session:
        return redirect("/login")

    student = get_student(id, session["user_id"])

    return render_template("edit.html", student=student)


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
        WHERE id = ? AND user_id = ?
        """,
        (name, roll, branch, id, session["user_id"])
    )

    conn.commit()
    conn.close()

    return redirect("/")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


if __name__ == "__main__":
    app.run(debug=True)