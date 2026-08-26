
from flask import Flask, render_template, request, redirect, session
import sqlite3

app = Flask(__name__)

app.secret_key = "campuscare-secret-key-2026"

DATABASE = "campuscare.db"


# =========================================================
# DATABASE
# =========================================================

def get_db():

    conn = sqlite3.connect(DATABASE)

    conn.row_factory = sqlite3.Row

    return conn


def init_db():

    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS reports (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            problem TEXT NOT NULL,

            location TEXT NOT NULL,

            category TEXT NOT NULL,

            priority TEXT NOT NULL,

            department TEXT NOT NULL,

            status TEXT DEFAULT 'Pending'

        )
    """)

    conn.commit()

    conn.close()


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    return render_template("index.html")


# =========================================================
# ANALYZE / SUBMIT REPORT
# =========================================================

@app.route("/analyze", methods=["POST"])
def analyze():

    problem = request.form.get("problem", "").strip()

    location = request.form.get("location", "").strip()

    if not problem:

        return "Please enter the problem.", 400

    if not location:

        return "Please enter the location.", 400

    text = problem.lower()


    # SAFETY

    if any(word in text for word in [
        "fire",
        "smoke",
        "electric shock",
        "shock",
        "gas",
        "emergency"
    ]):

        category = "Safety / Electrical"

        priority = "CRITICAL"

        department = "Safety & Maintenance"


    # WATER

    elif any(word in text for word in [
        "water",
        "leak",
        "leakage",
        "pipe",
        "tap",
        "flood"
    ]):

        category = "Water / Plumbing"

        priority = "HIGH"

        department = "Maintenance"


    # ELECTRICAL

    elif any(word in text for word in [
        "fan",
        "light",
        "ac",
        "computer",
        "switch",
        "socket",
        "power"
    ]):

        category = "Electrical / Equipment"

        priority = "MEDIUM"

        department = "Maintenance"


    # CLEANLINESS

    elif any(word in text for word in [
        "toilet",
        "clean",
        "cleaning",
        "dust",
        "garbage",
        "bin",
        "dirty",
        "waste"
    ]):

        category = "Cleanliness"

        priority = "LOW"

        department = "Housekeeping"


    # FURNITURE

    elif any(word in text for word in [
        "chair",
        "desk",
        "bench",
        "door",
        "table",
        "window",
        "furniture"
    ]):

        category = "Furniture"

        priority = "LOW"

        department = "Maintenance"


    # GENERAL

    else:

        category = "General"

        priority = "MEDIUM"

        department = "Administration"


    # SAVE

    conn = get_db()

    cursor = conn.execute("""
        INSERT INTO reports
        (
            problem,
            location,
            category,
            priority,
            department,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        problem,
        location,
        category,
        priority,
        department,
        "Pending"
    ))

    report_id = cursor.lastrowid

    conn.commit()

    conn.close()


    return render_template(
        "result.html",
        report_id=report_id,
        problem=problem,
        location=location,
        category=category,
        priority=priority,
        department=department
    )


# =========================================================
# ADMIN LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        ).strip()


        if username == "admin" and password == "admin123":

            session["admin_logged_in"] = True

            return redirect("/admin")


        return render_template(
            "login.html",
            error="Invalid username or password."
        )


    return render_template("login.html")


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.pop(
        "admin_logged_in",
        None
    )

    return redirect("/login")


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@app.route("/admin")
def admin():

    if not session.get("admin_logged_in"):

        return redirect("/login")


    search = request.args.get(
        "search",
        ""
    ).strip()

    status = request.args.get(
        "status",
        "All"
    )

    priority = request.args.get(
        "priority",
        "All"
    )


    conn = get_db()


    query = """
        SELECT *
        FROM reports
        WHERE 1=1
    """

    params = []


    # SEARCH

    if search:

        query += """
            AND (
                problem LIKE ?
                OR location LIKE ?
                OR category LIKE ?
                OR department LIKE ?
            )
        """

        value = "%" + search + "%"

        params.extend([
            value,
            value,
            value,
            value
        ])


    # STATUS FILTER

    if status != "All":

        query += """
            AND status = ?
        """

        params.append(status)


    # PRIORITY FILTER

    if priority != "All":

        query += """
            AND priority = ?
        """

        params.append(priority)


    query += """
        ORDER BY id DESC
    """


    reports = conn.execute(
        query,
        params
    ).fetchall()


    # STATISTICS

    total = conn.execute("""
        SELECT COUNT(*)
        FROM reports
    """).fetchone()[0]


    pending = conn.execute("""
        SELECT COUNT(*)
        FROM reports
        WHERE status = 'Pending'
    """).fetchone()[0]


    in_progress = conn.execute("""
        SELECT COUNT(*)
        FROM reports
        WHERE status = 'In Progress'
    """).fetchone()[0]


    resolved = conn.execute("""
        SELECT COUNT(*)
        FROM reports
        WHERE status = 'Resolved'
    """).fetchone()[0]


    critical_count = conn.execute("""
        SELECT COUNT(*)
        FROM reports
        WHERE priority = 'CRITICAL'
    """).fetchone()[0]


    high_count = conn.execute("""
        SELECT COUNT(*)
        FROM reports
        WHERE priority = 'HIGH'
    """).fetchone()[0]


    medium_count = conn.execute("""
        SELECT COUNT(*)
        FROM reports
        WHERE priority = 'MEDIUM'
    """).fetchone()[0]


    low_count = conn.execute("""
        SELECT COUNT(*)
        FROM reports
        WHERE priority = 'LOW'
    """).fetchone()[0]


    conn.close()


    return render_template(
        "admin.html",
        reports=reports,
        total=total,
        pending=pending,
        in_progress=in_progress,
        resolved=resolved,
        critical_count=critical_count,
        high_count=high_count,
        medium_count=medium_count,
        low_count=low_count,
        search=search,
        status=status,
        priority=priority
    )


# =========================================================
# UPDATE STATUS
# =========================================================

@app.route(
    "/update_status/<int:report_id>",
    methods=["POST"]
)
def update_status(report_id):

    if not session.get("admin_logged_in"):

        return redirect("/login")


    new_status = request.form.get("status")


    valid_statuses = [
        "Pending",
        "In Progress",
        "Resolved"
    ]


    if new_status not in valid_statuses:

        return "Invalid status", 400


    conn = get_db()


    conn.execute("""
        UPDATE reports
        SET status = ?
        WHERE id = ?
    """, (
        new_status,
        report_id
    ))


    conn.commit()

    conn.close()


    return redirect("/admin")


# =========================================================
# REPORT DETAILS
# =========================================================

@app.route("/report/<int:report_id>")
def report_details(report_id):

    conn = get_db()


    report = conn.execute("""
        SELECT *
        FROM reports
        WHERE id = ?
    """, (
        report_id,
    )).fetchone()


    conn.close()


    if report is None:

        return "Report not found", 404


    return render_template(
        "report.html",
        report=report
    )


# =========================================================
# STUDENT DASHBOARD
# =========================================================

@app.route("/student")
def student_dashboard():

    conn = get_db()


    reports = conn.execute("""
        SELECT *
        FROM reports
        ORDER BY id DESC
    """).fetchall()


    total = conn.execute("""
        SELECT COUNT(*)
        FROM reports
    """).fetchone()[0]


    in_progress = conn.execute("""
        SELECT COUNT(*)
        FROM reports
        WHERE status = 'In Progress'
    """).fetchone()[0]


    resolved = conn.execute("""
        SELECT COUNT(*)
        FROM reports
        WHERE status = 'Resolved'
    """).fetchone()[0]


    conn.close()


    return render_template(
        "student.html",
        reports=reports,
        total=total,
        in_progress=in_progress,
        resolved=resolved
    )


# =========================================================
# TRACK PAGE
# =========================================================

@app.route("/track")
def track_page():

    return render_template(
        "track.html"
    )


# =========================================================
# TRACK REPORT
# =========================================================

@app.route(
    "/track_report",
    methods=["POST"]
)
def track_report():

    report_id = request.form.get(
        "report_id",
        ""
    ).strip()


    if not report_id:

        return render_template(
            "track.html",
            error="Please enter Report ID."
        )


    try:

        report_id = int(report_id)

    except ValueError:

        return render_template(
            "track.html",
            error="Please enter a valid Report ID."
        )


    conn = get_db()


    report = conn.execute("""
        SELECT *
        FROM reports
        WHERE id = ?
    """, (
        report_id,
    )).fetchone()


    conn.close()


    if report is None:

        return render_template(
            "track.html",
            error="Report not found."
        )


    return render_template(
        "track.html",
        report=report
    )


# =========================================================
# START APPLICATION
# =========================================================

if __name__ == "__main__":

    init_db()

app.run(
    host="0.0.0.0",
    port=5000,
    debug=False
)