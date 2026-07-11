import os
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, render_template, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
app.secret_key = "student_management_secret"


# ==========================
# Database Connection
# ==========================

def get_connection():
    return psycopg2.connect(
        os.environ.get("DATABASE_URL"),
        cursor_factory=RealDictCursor
    )


# ==========================
# Create Tables
# ==========================

def create_tables():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) UNIQUE NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS students(
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            roll VARCHAR(100) NOT NULL,
            branch VARCHAR(100) NOT NULL,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    cur.close()
    conn.close()


create_tables()


# ==========================
# Student Functions
# ==========================

def add_student_db(name, roll, branch, user_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO students(name, roll, branch, user_id)
        VALUES (%s, %s, %s, %s)
        """,
        (name, roll, branch, user_id)
    )

    conn.commit()
    cur.close()
    conn.close()


def get_students(user_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT * FROM students
        WHERE user_id = %s
        ORDER BY id DESC
        """,
        (user_id,)
    )

    students = cur.fetchall()

    cur.close()
    conn.close()

    return students


def search_students(search, user_id):
    conn = get_connection()
    cur = conn.cursor()

    search_text = "%" + search + "%"

    cur.execute(
        """
        SELECT * FROM students
        WHERE user_id = %s
        AND (name ILIKE %s OR roll ILIKE %s)
        ORDER BY id DESC
        """,
        (user_id, search_text, search_text)
    )

    students = cur.fetchall()

    cur.close()
    conn.close()

    return students


def get_student(id, user_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT * FROM students
        WHERE id = %s AND user_id = %s
        """,
        (id, user_id)
    )

    student = cur.fetchone()

    cur.close()
    conn.close()

    return student


def delete_student(id, user_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        DELETE FROM students
        WHERE id = %s AND user_id = %s
        """,
        (id, user_id)
    )

    conn.commit()
    cur.close()
    conn.close()


def total_students(user_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT COUNT(*) AS total
        FROM students
        WHERE user_id = %s
        """,
        (user_id,)
    )

    result = cur.fetchone()
    total = result["total"]

    cur.close()
    conn.close()

    return total


def roll_exists(roll, user_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id FROM students
        WHERE roll = %s AND user_id = %s
        """,
        (roll, user_id)
    )

    student = cur.fetchone()

    cur.close()
    conn.close()

    return student is not None

        


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
        cur = conn.cursor()

        try:
            cur.execute(
                """
                INSERT INTO users(username, email, password)
                VALUES (%s, %s, %s)
                """,
                (username, email, hashed_password)
            )

            conn.commit()

            return redirect("/login")

        except psycopg2.errors.UniqueViolation:
            conn.rollback()

            return render_template(
                "signup.html",
                error="Username or Email already exists"
            )

        finally:
            cur.close()
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
        cur = conn.cursor()

        cur.execute(
            """
            SELECT * FROM users
            WHERE username = %s
            """,
            (username,)
        )

        user = cur.fetchone()

        cur.close()
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

        if roll_exists(roll, session["user_id"]):

            students = get_students(session["user_id"])
            total = total_students(session["user_id"])

            return render_template(
                "index.html",
                students=students,
                total=total,
                error="Roll number already exists"
            )

        add_student_db(
            name,
            roll,
            branch,
            session["user_id"]
        )

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


# ==========================
# Delete
# ==========================

@app.route("/delete/<int:id>")
def delete(id):

    if "user" not in session:
        return redirect("/login")

    delete_student(
        id,
        session["user_id"]
    )

    return redirect("/")


# ==========================
# Edit
# ==========================

@app.route("/edit/<int:id>")
def edit(id):

    if "user" not in session:
        return redirect("/login")

    student = get_student(
        id,
        session["user_id"]
    )

    if student is None:
        return redirect("/")

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
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE students
        SET name = %s, roll = %s, branch = %s
        WHERE id = %s AND user_id = %s
        """,
        (
            name,
            roll,
            branch,
            id,
            session["user_id"]
        )
    )

    conn.commit()

    cur.close()
    conn.close()

    return redirect("/")



# ==========================
# Profile
# ==========================

@app.route("/profile", methods=["GET", "POST"])
def profile():

    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]

    conn = get_connection()
    cur = conn.cursor()

    if request.method == "POST":
        username = request.form["username"].strip()
        email = request.form["email"].strip()

        try:
            cur.execute(
                """
                UPDATE users
                SET username = %s, email = %s
                WHERE id = %s
                """,
                (username, email, user_id)
            )

            conn.commit()

            session["user"] = username

            cur.close()
            conn.close()

            return redirect("/profile")

        except psycopg2.errors.UniqueViolation:
            conn.rollback()

            cur.execute(
                "SELECT id, username, email FROM users WHERE id = %s",
                (user_id,)
            )
            user = cur.fetchone()

            cur.close()
            conn.close()

            return render_template(
                "profile.html",
                user=user,
                error="Username or email already exists"
            )

    cur.execute(
        "SELECT id, username, email FROM users WHERE id = %s",
        (user_id,)
    )

    user = cur.fetchone()

    cur.close()
    conn.close()

    return render_template("profile.html", user=user)



# ==========================
# Change Password
# ==========================

@app.route("/change-password", methods=["POST"])
def change_password():

    if "user_id" not in session:
        return redirect("/login")

    current_password = request.form["current_password"]
    new_password = request.form["new_password"]
    confirm_password = request.form["confirm_password"]

    if new_password != confirm_password:
        return redirect("/profile?password_error=Passwords do not match")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT password FROM users WHERE id = %s",
        (session["user_id"],)
    )

    user = cur.fetchone()

    if not user or not check_password_hash(
        user["password"],
        current_password
    ):
        cur.close()
        conn.close()

        return redirect("/profile?password_error=Current password is incorrect")

    hashed_password = generate_password_hash(new_password)

    cur.execute(
        "UPDATE users SET password = %s WHERE id = %s",
        (hashed_password, session["user_id"])
    )

    conn.commit()
    cur.close()
    conn.close()

    return redirect("/profile?password_success=Password changed successfully")



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