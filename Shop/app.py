from flask import Flask, render_template, request, redirect, url_for, send_file, flash
import sqlite3
from contextlib import closing
import csv
import io
import os

APP = Flask(__name__)
APP.secret_key = "change_this_to_random_secret"  # change in production
DB_PATH = "shops.db"

def init_db():
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS shops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            address TEXT,
            phone TEXT,
            category TEXT,
            note TEXT,
            url TEXT
        );
        """)
        conn.commit()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@APP.route("/")
def index():
    q = request.args.get("q", "").strip()
    cat = request.args.get("category", "").strip()
    conn = get_db()
    c = conn.cursor()
    sql = "SELECT * FROM shops"
    params = []
    clauses = []
    if q:
        clauses.append("(name LIKE ? OR address LIKE ? OR phone LIKE ? OR note LIKE ?)")
        like = f"%{q}%"
        params.extend([like, like, like, like])
    if cat:
        clauses.append("category = ?")
        params.append(cat)
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY id DESC"
    c.execute(sql, params)
    rows = c.fetchall()
    # get distinct categories for filter dropdown
    c.execute("SELECT DISTINCT category FROM shops WHERE category IS NOT NULL AND category != ''")
    categories = [r["category"] for r in c.fetchall()]
    conn.close()
    return render_template("index.html", shops=rows, q=q, categories=categories, cat_selected=cat)

@APP.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        address = request.form.get("address", "").strip()
        phone = request.form.get("phone", "").strip()
        category = request.form.get("category", "").strip()
        note = request.form.get("note", "").strip()
        url = request.form.get("url", "").strip()
        if not name:
            flash("Please provide shop name.")
            return redirect(url_for("add"))
        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO shops (name,address,phone,category,note,url) VALUES(?,?,?,?,?,?)",
                  (name, address, phone, category, note, url))
        conn.commit()
        conn.close()
        flash("Shop added.")
        return redirect(url_for("index"))
    return render_template("add_edit.html", shop=None, action="Add")

@APP.route("/edit/<int:shop_id>", methods=["GET", "POST"])
def edit(shop_id):
    conn = get_db()
    c = conn.cursor()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        address = request.form.get("address", "").strip()
        phone = request.form.get("phone", "").strip()
        category = request.form.get("category", "").strip()
        note = request.form.get("note", "").strip()
        url = request.form.get("url", "").strip()
        if not name:
            flash("Please provide shop name.")
            return redirect(url_for("edit", shop_id=shop_id))
        c.execute("UPDATE shops SET name=?, address=?, phone=?, category=?, note=?, url=? WHERE id=?",
                  (name, address, phone, category, note, url, shop_id))
        conn.commit()
        conn.close()
        flash("Shop updated.")
        return redirect(url_for("index"))
    c.execute("SELECT * FROM shops WHERE id=?", (shop_id,))
    shop = c.fetchone()
    conn.close()
    if not shop:
        flash("Shop not found.")
        return redirect(url_for("index"))
    return render_template("add_edit.html", shop=shop, action="Edit")

@APP.route("/delete/<int:shop_id>", methods=["POST"])
def delete(shop_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM shops WHERE id=?", (shop_id,))
    conn.commit()
    conn.close()
    flash("Shop deleted.")
    return redirect(url_for("index"))

@APP.route("/export")
def export_csv():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM shops ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "name", "address", "phone", "category", "note", "url"])
    for r in rows:
        writer.writerow([r["id"], r["name"], r["address"], r["phone"], r["category"], r["note"], r["url"]])

    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode("utf-8")),
                     mimetype="text/csv",
                     as_attachment=True,
                     download_name="shops_export.csv")

if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        init_db()
    APP.run(host="0.0.0.0", port=5000, debug=True)
