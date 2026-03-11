from flask import Flask, render_template, request, redirect, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "secret123"

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # ensure folder exists
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# DATABASE CONNECTION
def db():
    # timeout=10 avoids "database is locked" errors
    conn = sqlite3.connect("forum.db", timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


# INITIALIZE DATABASE
def init_db():
    with db() as conn:
        c = conn.cursor()
        # USERS TABLE
        c.execute("""
        CREATE TABLE IF NOT EXISTS users(
            username TEXT PRIMARY KEY,
            password TEXT,
            name TEXT,
            university TEXT,
            address TEXT,
            phone TEXT,
            email TEXT,
            profile_pic TEXT
        )
        """)
        # POSTS TABLE
        c.execute("""
        CREATE TABLE IF NOT EXISTS posts(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content TEXT,
            subject TEXT,
            image TEXT,
            username TEXT,
            likes INTEGER DEFAULT 0
        )
        """)
        # COMMENTS TABLE
        c.execute("""
        CREATE TABLE IF NOT EXISTS comments(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER,
            username TEXT,
            comment TEXT
        )
        """)
        conn.commit()


init_db()


# LOGIN
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        with db() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
            user = c.fetchone()

        if user:
            session["user"] = username
            return redirect("/home")

    return render_template("login.html")


# SIGNUP
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        name = request.form["name"]
        university = request.form["university"]
        address = request.form["address"]
        phone = request.form["phone"]
        email = request.form["email"]

        profile = request.files.get("profile_pic")
        filename = ""

        if profile and profile.filename:
            filename = profile.filename
            profile.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        try:
            with db() as conn:
                c = conn.cursor()
                c.execute("""
                INSERT INTO users(username,password,name,university,address,phone,email,profile_pic)
                VALUES(?,?,?,?,?,?,?,?)
                """, (username, password, name, university, address, phone, email, filename))
                conn.commit()
        except sqlite3.IntegrityError:
            return "Username already exists!"

        return redirect("/")

    return render_template("signup.html")


# HOME
@app.route("/home")
def home():
    if "user" not in session:
        return redirect("/")

    with db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM posts ORDER BY id DESC")
        posts = c.fetchall()

    return render_template("home.html", posts=posts)


# CREATE POST
@app.route("/create", methods=["GET", "POST"])
def create():
    if "user" not in session:
        return redirect("/")

    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]
        subject = request.form["subject"]

        image = request.files.get("image")
        filename = ""

        if image and image.filename:
            filename = image.filename
            image.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        with db() as conn:
            c = conn.cursor()
            c.execute("""
            INSERT INTO posts(title,content,subject,image,username)
            VALUES(?,?,?,?,?)
            """, (title, content, subject, filename, session["user"]))
            conn.commit()

        return redirect("/home")

    return render_template("create.html")


# VIEW POST
@app.route("/post/<int:id>", methods=["GET", "POST"])
def post(id):
    if "user" not in session:
        return redirect("/")

    if request.method == "POST":
        comment = request.form["comment"]
        with db() as conn:
            c = conn.cursor()
            c.execute("""
            INSERT INTO comments(post_id,username,comment)
            VALUES(?,?,?)
            """, (id, session["user"], comment))
            conn.commit()
        return redirect(f"/post/{id}")

    with db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM posts WHERE id=?", (id,))
        post = c.fetchone()

        c.execute("SELECT * FROM comments WHERE post_id=?", (id,))
        comments = c.fetchall()

    return render_template("post.html", post=post, comments=comments)


# LIKE POST
@app.route("/like/<int:id>")
def like(id):
    with db() as conn:
        c = conn.cursor()
        c.execute("UPDATE posts SET likes = likes + 1 WHERE id=?", (id,))
        conn.commit()
    return redirect("/home")


# PROFILE
@app.route("/profile")
def profile():
    if "user" not in session:
        return redirect("/")

    with db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=?", (session["user"],))
        user = c.fetchone()

        c.execute("SELECT * FROM posts WHERE username=?", (session["user"],))
        posts = c.fetchall()

    return render_template("profile.html", user=user, posts=posts)


# LOGOUT
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)