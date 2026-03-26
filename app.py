from flask import Flask, request, redirect, url_for
import sqlite3
import qrcode
import io, base64
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
    receiver_name TEXT,
    status TEXT,
    image TEXT,
    created_at TEXT
)
''')
conn.commit()

# ================= TOKEN =================
SECRET_TOKEN = "RAED_SECURE_123"

def generate_token(mail_id):
    today = datetime.now().strftime("%Y-%m-%d")
    raw = f"{mail_id}-{today}-{SECRET_TOKEN}"
    return hashlib.sha256(raw.encode()).hexdigest()

def generate_qr(url):
    qr = qrcode.make(url)
    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

# ================= STYLE =================
STYLE = """
<style>
body {font-family: Arial; background:#0b1f3a; color:white;}
input {padding:10px; margin:5px; width:100%;}
button {background:red; color:white; padding:10px; border:none;}
.card {background:#132f57; padding:15px; margin:10px;}
img {border-radius:10px;}
</style>
"""

# ================= ADMIN =================
@app.route("/", methods=["GET","POST"])
def index():

    if request.method == "POST":
        name = request.form["name"]
        address = request.form["address"]
        receiver = request.form["receiver"]

        now = datetime.now().strftime("%Y-%m-%d")

        c.execute("INSERT INTO mails (name,address,receiver_name,status,created_at) VALUES (?,?,?,?,?)",
                  (name,address,receiver,"عالِق",now))
        conn.commit()

    search = request.args.get("search","")
    status_filter = request.args.get("status","all")

    c.execute("SELECT * FROM mails ORDER BY id DESC")
    mails = c.fetchall()

    html = STYLE + """

    <h2>إضافة بريد</h2>
    <form method="POST">
        <input name="name" placeholder="اسم العميل">
        <input name="address" placeholder="العنوان">
        <input name="receiver" placeholder="يسلم لــ">
        <button>حفظ</button>
    </form>

    <h3>فلترة:</h3>
    <a href='/?status=all'><button>الكل</button></a>
    <a href='/?status=عالِق'><button>عالِق</button></a>
    <a href='/?status=منتهي'><button>منتهي</button></a>

    <form>
        <input name="search" placeholder="بحث">
    </form>
    """

    # 📊 إحصائية اليوم
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("SELECT COUNT(*) FROM mails WHERE status='منتهي' AND created_at=?", (today,))
    done_today = c.fetchone()[0]

    html = f"<h2>📊 تسليمات اليوم: {done_today}</h2>" + html

    for m in mails:

        if search.lower() not in str(m).lower():
            continue

        if status_filter != "all" and m[4] != status_filter:
            continue

        token = generate_token(m[0])
        url = request.host_url + f"view/{m[0]}?token={token}"
        qr = generate_qr(url)

        image_html = ""
        if m[5]:
            image_html = f"<br><img src='data:image/png;base64,{m[5]}' width='120'>"

        html += f"""
        <div class="card">
        <b>{m[1]}</b><br>
        {m[2]}<br>
        يسلم ل: {m[3]}<br>
        الحالة: {m[4]}<br>

        <img src="data:image/png;base64,{qr}" width="120"><br>

        {image_html}
        </div>
        """

    return html

# ================= MOBILE =================
@app.route("/view/<int:id>", methods=["GET","POST"])
def view(id):

    token = request.args.get("token")

    if token != generate_token(id):
        return "❌ رابط غير صالح"

    c.execute("SELECT * FROM mails WHERE id=?", (id,))
    m = c.fetchone()

    if not m:
        return "غير موجود"

    if request.method == "POST":

        if m[4] == "منتهي":
            return "✔ تم مسبقاً"

        file = request.files["image"]
        if file:
            img = base64.b64encode(file.read()).decode()

            c.execute("UPDATE mails SET image=?, status='منتهي' WHERE id=?", (img,id))
            conn.commit()

            return STYLE + "<h2 style='color:lime;'>✔ تم التسليم</h2>"

    return STYLE + f"""
    <div class="card">
    <h2>بيانات التسليم</h2>

    الاسم: {m[1]}<br>
    العنوان: {m[2]}<br>
    يسلم ل: {m[3]}<br><br>

    <form method="POST" enctype="multipart/form-data">
        <input type="file" name="image" accept="image/*" capture="camera"><br><br>
        <button>رفع الصورة والتأكيد</button>
    </form>

    </div>
    """

# ================= RUN =================
if __name__ == "__main__":
    app.run()
