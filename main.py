from flask import (
    Flask,
    abort,
    render_template,
    session,
    flash,
    redirect,
    request,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
import mysql.connector
from dotenv import load_dotenv
import os

load_dotenv(".env")

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
db_config = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASS"),
    "database": os.getenv("DB_DB"),
}


@app.context_processor
def processor():
    def emoji_decode(x):
        return x.decode()

    return dict(length=lambda x: len(x), decode=emoji_decode, enumerate=enumerate)


def login_required(f):
    @wraps(f)
    def is_logged_in(*args, **kwargs):
        if "username" in session:
            return f(*args, **kwargs)
        else:
            flash("You must be logged in to access this page")
            return redirect(url_for("login", next=request.path))

    return is_logged_in


def logout_required(f):
    @wraps(f)
    def is_logged_in(*args, **kwargs):
        if "username" in session:
            return redirect(url_for("index"))
        else:
            return f(*args, **kwargs)

    return is_logged_in


@app.route("/")
@login_required
def index():
    user_id = session["user_id"]
    wishlists = get_list_by_user(user_id)
    print(wishlists)
    return render_template("index.html", title="Wishlist - Home", wishlists=wishlists)


def get_list_by_user(id):
    try:
        # Connect to the database
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        # Execute the query to get lists and their item counts
        query = """
            SELECT lists.id, lists.name, lists.emoji, COUNT(list_items.id) AS item_count
            FROM lists
            LEFT JOIN list_items ON lists.id = list_items.list_id
            JOIN users ON lists.user_id = users.id
            WHERE user_id = %s
            GROUP BY lists.id;
        """

        cursor.execute(query, (id,))

        # Fetch all results
        lists = cursor.fetchall()

        cursor.close()
        conn.close()
        return lists
    except mysql.connector.Error as err:
        # Handle database errors
        print(f"Error: {err}")
        return []


def get_lists():
    try:
        # Connect to the database
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        # Execute the query to get lists and their item counts
        query = """
            SELECT lists.id, lists.name, lists.emoji, users.username, COUNT(list_items.id) AS item_count
            FROM lists
            LEFT JOIN list_items ON lists.id = list_items.list_id
            JOIN users ON lists.user_id = users.id
            GROUP BY lists.id;
        """
        cursor.execute(query)

        # Fetch all results
        lists = cursor.fetchall()

        cursor.close()
        conn.close()
        return lists
    except mysql.connector.Error as err:
        # Handle database errors
        print(f"Error: {err}")
        return []


def get_users():
    try:
        # Connect to the database
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        # Execute the query to get lists and their item counts
        query = """
            SELECT users.username, users.id, COUNT(lists.id) AS list_count
            FROM users
            LEFT JOIN lists ON lists.user_id = users.id
            GROUP BY users.id;
        """
        cursor.execute(query)

        # Fetch all results
        lists = cursor.fetchall()

        cursor.close()
        conn.close()
        return lists
    except mysql.connector.Error as err:
        # Handle database errors
        print(f"Error: {err}")
        return []


@app.route("/login", methods=["GET", "POST"])
@logout_required
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()

            # Check if the username already exists
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()

            cursor.close()
            conn.close()

            if user:
                session["user_id"] = user[0]
                session["username"] = user[1]
                session.permanent = (
                    True if request.form.get("remember-me", "off") == "on" else False
                )
                return redirect(url_for("index"))
            else:
                flash("Invalid username or password")
                return redirect(url_for("login"))
        except Exception as e:
            print("ERRROR")
            print(e)

    return render_template("login.html", title="Log In to Wishlist")


@app.route("/signup", methods=["GET", "POST"])
@logout_required
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()

            # Check if the username already exists
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            user_exists = cursor.fetchone()

            if user_exists:
                flash("Username is taken, please choose another")
                return redirect(url_for("signup"))

            query = "INSERT INTO users (username, password) VALUES (%s, %s)"
            cursor.execute(query, (username, password))

            conn.commit()

            cursor.close()
            conn.close()
            flash("You have been signed up")
            return redirect(url_for("login"))
        except Exception as e:
            print("ERRROR")
            print(e)

    return render_template("signup.html", title="Sign Up for Wishlist")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/edit/<id>", methods=["GET", "POST"])
@login_required
def edit(id):
    if request.method == "POST":
        print(request.form)
        length = int(request.form["length"])
        startLength = int(request.form["startingLength"])
        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()

            cursor.execute(
                "UPDATE lists SET name = %s, emoji = %s WHERE id = %s",
                (request.form["list-name"], request.form["emoji"].encode(), id),
            )
            conn.commit()
            cursor.execute("select id from list_items where list_id = %s", (id,))
            item_ids = {row[0] for row in cursor.fetchall()}

            if length != 0:
                for i in range(1, length + 1):
                    name = request.form[f"item-name-{i}"]
                    link = request.form[f"item-link-{i}"]
                    price = request.form[f"item-price-{i}"]
                    desc = request.form[f"item-description-{i}"]
                    if i <= startLength:
                        item_id = request.form[f"item-id-{i}"]
                        item_ids.remove(int(item_id))
                        updated_query = """
                            UPDATE list_items
                            SET name = %s, url = %s, price = %s, description = %s
                            WHERE id = %s
                        """
                        cursor.execute(
                            updated_query, (name, link, price, desc, item_id)
                        )
                    else:
                        insert_query = """
                            INSERT INTO list_items (list_id, name, url, price, description)
                            VALUES (%s, %s, %s, %s, %s)
                        """
                        cursor.execute(insert_query, (id, name, link, price, desc))
                for item_id in item_ids:
                    query = """DELETE FROM list_items WHERE id = %s"""
                    cursor.execute(query, (item_id,))
            else:
                try:
                    for i in range(0, length + 1):
                        print("In else clause")
                        name = request.form[f"item-name-{i}"]
                        link = request.form[f"item-link-{i}"]
                        price = request.form[f"item-price-{i}"]
                        desc = request.form[f"item-description-{i}"]
                        insert_query = """
                            INSERT INTO list_items (list_id, name, url, price, description)
                            VALUES (%s, %s, %s, %s, %s)
                        """
                        cursor.execute(insert_query, (id, name, link, price, desc))
                except KeyError:
                    pass
            conn.commit()
            cursor.close()
            conn.close()
        except mysql.connector.Error as err:
            # Handle database errors
            print(f"Error: {err}")
        except Exception as err:
            raise err

        return redirect(url_for("edit", id=id))

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        query = """
            SELECT lists.id, lists.name, lists.emoji, users.username
            FROM lists
            JOIN users ON lists.user_id = users.id
            WHERE lists.id = %s
        """
        cursor.execute(query, (id,))
        wishlist = cursor.fetchone()

        if wishlist is None:
            abort(404)

        query = """
            SELECT * FROM list_items
            WHERE list_id = %s
        """
        cursor.execute(query, (id,))
        list_items = cursor.fetchall()

        cursor.close()
        conn.close()
    except mysql.connector.Error as err:
        # Handle database errors
        print(f"Error: {err}")
        wishlist = None
        list_items = []

    return render_template(
        "edit.html",
        list=wishlist,
        list_items=list_items,
        title=f"Edit {wishlist[1]}",
    )


@app.route("/view/<id>")
def view(id):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM lists WHERE id = %s", (id,))
        wishlist = cursor.fetchone()

        query = """
            SELECT * FROM list_items
            WHERE list_id = %s
        """
        cursor.execute(query, (id,))
        list_items = cursor.fetchall()
        print(list_items)

        cursor.close()
        conn.close()
    except mysql.connector.Error as err:
        # Handle database errors
        print(f"Error: {err}")
        wishlist = None

    return render_template(
        "view.html",
        wishlist=wishlist,
        list_items=list_items,
        title=f"{wishlist[3].decode()} {wishlist[2]}",
        list_id=id,
    )


@app.route("/newlist", methods=["GET", "POST"])
@login_required
def new_list():
    if request.method == "POST":
        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()

            user_id = int(session["user_id"])
            name = request.form["list-name"]
            emoji = request.form["emoji"].encode()
            query = "INSERT INTO lists  (user_id, name, emoji) VALUES (%s, %s, %s)"
            cursor.execute(query, (user_id, name, emoji))
            conn.commit()

            cursor.close()
            conn.close()
        except mysql.connector.Error as err:
            # Handle database errors
            print(f"Error: {err}")

        return redirect(url_for("index"))
    return render_template("new_list.html")


@app.route("/delete/<id>")
@login_required
def delete(id):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        query = "DELETE FROM lists WHERE id = %s"
        cursor.execute(query, (id,))
        conn.commit()

        cursor.close()
        conn.close()
    except mysql.connector.Error as err:
        # Handle database errors
        print(f"Error: {err}")
    return redirect(url_for("index"))


@app.route("/account")
@login_required
def account():
    return render_template("account.html", title="Wishlist - Account")


@app.route("/admin")
@app.route("/admin/")
@login_required
def admin():
    if session["user_id"] != 4:
        print(session["username"], "tried to access the admin page without permission")
        return redirect(url_for("index"))

    return render_template("admin/index.html", title="Admin Dashboard")


@app.route("/admin/viewlists")
@app.route("/admin/viewlists/")
@login_required
def view_lists():
    if session["user_id"] != 4:
        print(session["username"], "tried to access the admin page - view lists")
        return redirect(url_for("index"))

    wishlists = get_lists()
    print("Wishlists: ", wishlists)
    return render_template(
        "admin/lists.html", title="Wishlist Admin - View Lists", wishlists=wishlists
    )


@app.route("/admin/viewusers")
@app.route("/admin/viewusers/")
@login_required
def view_users():
    if session["user_id"] != 4:
        print(session["username"], "tried to access the admin page - view users")
        return redirect(url_for("index"))

    users = get_users()
    print("Users: ", users)
    return render_template(
        "admin/users.html", title="Wishlist Admin - View Users", users=users
    )


@app.route("/admin/delete/<id>")
@login_required
def delete_user(id):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        query = "DELETE FROM users WHERE id = %s"
        cursor.execute(query, (id,))
        conn.commit()

        cursor.close()
        conn.close()
    except mysql.connector.Error as err:
        # Handle database errors
        print(f"Error: {err}")
    return redirect(url_for("view_users"))


@app.route("/update_items", methods=["POST"])
def update_items():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        form_data = request.form.to_dict()
        list_id = int(form_data.pop("list_id"))

        # Get all item ids from the relevant list
        cursor.execute("select id from list_items where list_id = %s", (list_id,))
        item_ids = {row[0] for row in cursor.fetchall()}
        bought_item_ids = {
            int(key.split("-")[1])
            for key in form_data.keys()
            if key.startswith("bought-")
        }

        for item_id in bought_item_ids:
            query = "UPDATE list_items SET bought = 1 WHERE id = %s"
            cursor.execute(query, (item_id,))

        unchecked_item_ids = item_ids - bought_item_ids
        for item_id in unchecked_item_ids:
            query = "UPDATE list_items SET bought = 0 WHERE id = %s"
            cursor.execute(query, (item_id,))

        conn.commit()
        cursor.close()
        conn.close()
    except mysql.connector.Error as err:
        # Handle database errors
        print(f"Error: {err}")
    return redirect(url_for("view", id=list_id))


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
