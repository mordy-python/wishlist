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

app = Flask(__name__)
app.config["SECRET_KEY"] = (
    "2327c5e2393ebea60b04e62d35842dde185284f0f163c29888d110c2c4e48d2d3e70f525"
)
db_config = {
    "host": "localhost",
    "user": "admin",
    "password": "admin",
    "database": "wishlist",
}


@app.context_processor
def length():
    return dict(length=lambda x: len(x), enumerate=enumerate)


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
            JOIN users ON lists.user_id = %s
            GROUP BY lists.id;
        """
        cursor.execute(query, (id,))

        # Fetch all results
        lists = cursor.fetchall()
        return lists
    except mysql.connector.Error as err:
        # Handle database errors
        print(f"Error: {err}")
        return []
    finally:
        # Close the cursor and connection
        cursor.close()
        conn.close()


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
            cursor.execute(
                "SELECT * FROM wishlist.users WHERE username = %s", (username,)
            )
            user = cursor.fetchone()

            if user and check_password_hash(user[2], password):
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
        finally:
            cursor.close()
            conn.close()

    return render_template("login.html", title="Log In to Wishlist")


@app.route("/signup", methods=["GET", "POST"])
@logout_required
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        hashed = generate_password_hash(password)

        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()

            # Check if the username already exists
            cursor.execute(
                "SELECT * FROM wishlist.users WHERE username = %s", (username,)
            )
            user_exists = cursor.fetchone()

            if user_exists:
                flash("Username is taken, please choose another")
                return redirect(url_for("signup"))

            query = "INSERT INTO users (username, password) VALUES (%s, %s)"
            cursor.execute(query, (username, hashed))

            conn.commit()
            flash("You have been signed up")
            return redirect(url_for("login"))
        except Exception as e:
            print("ERRROR")
            print(e)
        finally:
            cursor.close()
            conn.close()

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
                (request.form["list-name"], request.form["emoji"], id),
            )
            conn.commit()
            if length != 0:
                for i in range(1, length + 1):
                    name = request.form[f"item-name-{i}"]
                    link = request.form[f"item-link-{i}"]
                    price = request.form[f"item-price-{i}"]
                    desc = request.form[f"item-description-{i}"]
                    if i <= startLength:
                        item_id = request.form[f"item-id-{i}"]
                        updated_query = """
                            UPDATE list_items 
                            SET name = %s, url = %s, price = %s, description = %s
                            WHERE id = %s
                        """
                        print(updated_query % (name, link, price, desc, item_id))
                        cursor.execute(
                            updated_query, (name, link, price, desc, item_id)
                        )
                    else:
                        insert_query = """
                            INSERT INTO list_items (list_id, name, url, price, description) 
                            VALUES (%s, %s, %s, %s, %s)
                        """
                        cursor.execute(insert_query, (id, name, link, price, desc))
            else:
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
            conn.commit()
        except mysql.connector.Error as err:
            # Handle database errors
            print(f"Error: {err}")
        except Exception as err:
            raise err
        finally:
            cursor.close()
            conn.close()
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

    except mysql.connector.Error as err:
        # Handle database errors
        print(f"Error: {err}")
        wishlist = None
        list_items = []
    finally:
        cursor.close()
        conn.close()
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
    except mysql.connector.Error as err:
        # Handle database errors
        print(f"Error: {err}")
        wishlist = None
    finally:
        cursor.close()
        conn.close()
    return render_template(
        "view.html",
        wishlist=wishlist,
        list_items=list_items,
        title=f"{wishlist[3]} {wishlist[2]}",
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
            emoji = request.form["emoji"]
            query = "INSERT INTO lists  (user_id, name, emoji) VALUES (%s, %s, %s)"
            cursor.execute(query, (user_id, name, emoji))
            conn.commit()
        except mysql.connector.Error as err:
            # Handle database errors
            print(f"Error: {err}")
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for("index"))
    return render_template("new_list.html")


@app.route(
    "/delete/<id>",
)
@login_required
def delete(id):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        query = "DELETE FROM lists WHERE id = %s"
        cursor.execute(query, (id,))
        conn.commit()
    except mysql.connector.Error as err:
        # Handle database errors
        print(f"Error: {err}")
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for("index"))


@app.route("/account")
@login_required
def account():
    return render_template("account.html", title="Wishlist - Account")


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
