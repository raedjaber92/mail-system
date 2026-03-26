import sqlite3
from flask import Flask, request, render_template_string, redirect, url_for
import qrcode
import io
import base64
from datetime import datetime
import hashlib

app = Flask(__name__)

# ================= DATABASE =================
conn = sqlite3.connect("data.db", check_same_thread=False)
c = conn.cursor()

c.execute('''
CREATE TABLE IF NOT EXISTS mails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    address TEXT,
    delivery_date TEXT,
    content TEXT,
    delivered_to TEXT,
    receiver_name TEXT,
    status TEXT
)
''')
conn.commit()

# ================= SETTINGS =================
SECRET_TOKEN = "RAED_SECURE_TOKEN_123"  # تقدر تغيره
BASE_URL = ""  # يتغير مع ngrok

# ================= STYLE =================
STYLE = """
<style>
body {
    font-family: Arial;
    background-color: #0b1f3a;
    color: white;
}
input, textarea {
    width: 100%;
    padding: 10px;
    margin: 5px;
}
button {
    background-color: red;
    color: white;
    padding: 10px;
    border: none;
}
.card {
    background: #132f57;
    padding: 15px;
    margin: 10px;
}
</style>
"""

# ================= HELPER =================
def generate_daily_token(mail_id):
    today = datetime.now().strftime("%Y-%m-%d")
    raw = f"{mail_id}-{today}-{SECRET_TOKEN}"
    return hashlib.sha256(raw.encode()).hexdigest()

def generate_qr(url):
    qr = qrcode.make(url)
    buffer = io.BytesIO()
    qr.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()

# ================= MAIN PAGE =================
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        name = request.form["name"]
        address = request.form["address"]
        delivery_date = request.form["delivery_date"]
        content = request.form["content"]
        delivered_to = request.form["delivered_to"]
        receiver_name = request.form["receiver_name"]

        c.execute("INSERT INTO mails (name,address,delivery_date,content,delivered_to,receiver_name,status) VALUES (?,?,?,?,?,?,?)",
                  (name,address,delivery_date,content,delivered_to,receiver_name,"عالِق"))
        conn.commit()

    c.execute("SELECT * FROM mails ORDER BY id DESC")
    mails = c.fetchall()

    html = STYLE + """
    <h2>إضافة بريد</h2>
    <form method="POST">
        <input name="name" placeholder="اسم العميل">
        <input name="address" placeholder="العنوان">
        <input name="delivery_date" placeholder="تاريخ التسليم">
        <textarea name="content" placeholder="محتوى البريد"></textarea>
        <input name="delivered_to" placeholder="يسلم ليد">
        <input name="receiver_name" placeholder="اسم المستلم">
        <button type="submit">حفظ</button>
    </form>

    <h2>الأرشيف</h2>
    <form method="GET">
        <input name="search" placeholder="بحث بالاسم او التاريخ">
    </form>
    """

    search = request.args.get("search", "")

    for m in mails:
        if search.lower() in str(m).lower():
            token = generate_daily_token(m[0])
            url = request.host_url + f"view/{m[0]}?token={token}"
            qr = generate_qr(url)

            html += f"""
            <div class="card">
                <b>{m[1]}</b><br>
                {m[2]}<br>
                الحالة: {m[7]}<br>
                <img src="data:image/png;base64,{qr}" width="150"><br>
                <a href="/done/{m[0]}">تعيين منتهي</a>
            </div>
            """

    return html

# ================= MOBILE VIEW =================
@app.route("/view/<int:mail_id>")
def view(mail_id):
    token = request.args.get("token")
    valid_token = generate_daily_token(mail_id)

    if token != valid_token:
        return "❌ الرابط غير صالح أو منتهي"

    c.execute("SELECT * FROM mails WHERE id=?", (mail_id,))
    m = c.fetchone()

    if not m:
        return "غير موجود"

    return STYLE + f"""
    <div class="card">
    <h2>بيانات البريد</h2>
    الاسم: {m[1]}<br>
    العنوان: {m[2]}<br>
    <h3 style="color:lime;">✔ تم المسح بنجاح</h3>
    </div>
    """

# ================= DONE =================
@app.route("/done/<int:mail_id>")
def done(mail_id):
    c.execute("UPDATE mails SET status='منتهي' WHERE id=?", (mail_id,))
    conn.commit()
    return redirect(url_for("index"))

# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)
