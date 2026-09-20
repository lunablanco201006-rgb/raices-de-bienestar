
import os, sqlite3
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, g

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "cambia-esta-clave-en-produccion")
DB = os.path.join(os.path.dirname(__file__), "bienestar.db")

def db():
    conn=sqlite3.connect(DB)
    conn.row_factory=sqlite3.Row
    return conn

def init_db():
    con=db()
    con.executescript("""
    CREATE TABLE IF NOT EXISTS users(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      email TEXT UNIQUE NOT NULL,
      password TEXT NOT NULL,
      created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS moods(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL,
      mood TEXT NOT NULL,
      score INTEGER NOT NULL,
      note TEXT DEFAULT '',
      created_at TEXT NOT NULL,
      FOREIGN KEY(user_id) REFERENCES users(id)
    );
    """)
    con.commit(); con.close()

def login_required(fn):
    @wraps(fn)
    def wrapper(*a,**kw):
        if not g.user: return redirect(url_for("login"))
        return fn(*a,**kw)
    return wrapper

@app.before_request
def load_user():
    g.user=None
    if "user_id" in session:
        con=db(); g.user=con.execute("SELECT id,name,email FROM users WHERE id=?", (session["user_id"],)).fetchone(); con.close()

@app.route("/")
def index():
    return render_template("index.html", user=g.user)

@app.route("/registro", methods=["GET","POST"])
def register():
    if request.method=="POST":
        from werkzeug.security import generate_password_hash
        name=request.form.get("name","").strip()
        email=request.form.get("email","").strip().lower()
        password=request.form.get("password","")
        if len(name)<2 or "@" not in email or len(password)<6:
            flash("Completa los datos correctamente. La contraseña debe tener al menos 6 caracteres.","error")
            return render_template("register.html")
        con=db()
        try:
            cur=con.execute("INSERT INTO users(name,email,password,created_at) VALUES(?,?,?,?)",
                (name,email,generate_password_hash(password),datetime.now().isoformat(timespec="seconds")))
            con.commit(); session["user_id"]=cur.lastrowid
        except sqlite3.IntegrityError:
            con.close(); flash("Ese correo ya está registrado.","error"); return render_template("register.html")
        con.close(); return redirect(url_for("dashboard"))
    return render_template("register.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        from werkzeug.security import check_password_hash
        email=request.form.get("email","").strip().lower()
        password=request.form.get("password","")
        con=db(); user=con.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone(); con.close()
        if user and check_password_hash(user["password"],password):
            session["user_id"]=user["id"]; return redirect(url_for("dashboard"))
        flash("Correo o contraseña incorrectos.","error")
    return render_template("login.html")

@app.route("/salir")
def logout():
    session.clear(); return redirect(url_for("index"))

@app.route("/panel")
@login_required
def dashboard():
    con=db()
    rows=con.execute("SELECT mood,score,note,created_at FROM moods WHERE user_id=? ORDER BY id DESC LIMIT 20",(g.user["id"],)).fetchall()
    con.close()
    history=[dict(x) for x in rows][::-1]
    return render_template("dashboard.html", user=g.user, history=history)

@app.route("/api/mood", methods=["POST"])
@login_required
def mood():
    data=request.get_json(silent=True) or {}
    mood=data.get("mood",""); score=int(data.get("score",0)); note=data.get("note","").strip()[:500]
    if mood not in ["Muy bien","Bien","Regular","Triste","Muy mal"] or score not in range(1,6):
        return jsonify(ok=False,message="Datos inválidos"),400
    con=db()
    con.execute("INSERT INTO moods(user_id,mood,score,note,created_at) VALUES(?,?,?,?,?)",
      (g.user["id"],mood,score,note,datetime.now().strftime("%Y-%m-%d %H:%M")))
    con.commit(); con.close()
    return jsonify(ok=True)

@app.route("/api/moods")
@login_required
def moods():
    con=db(); rows=con.execute("SELECT mood,score,note,created_at FROM moods WHERE user_id=? ORDER BY id DESC LIMIT 30",(g.user["id"],)).fetchall(); con.close()
    return jsonify([dict(x) for x in rows])

@app.route("/recursos")
def resources():
    return render_template("resources.html", user=g.user)

@app.route("/chat")
def chat():
    return render_template("chat.html", user=g.user)

@app.route("/api/chat", methods=["POST"])
def chat_api():
    data = request.get_json(silent=True) or {}
    original_text = data.get("message", "").strip()
    text = original_text.lower()

    if not original_text:
        return jsonify(reply="Cuéntame un poco más sobre lo que estás sintiendo.")

    # Situaciones de riesgo
    crisis = [
        "suicid", "matarme", "hacerme daño",
        "no quiero vivir", "autoles"
    ]

    if any(k in text for k in crisis):
        return jsonify(reply=(
            "Siento que estés pasando por algo tan difícil. "
            "No estás solo/a. Busca ahora mismo a una persona de confianza "
            "y ayuda profesional. Si existe un peligro inmediato, "
            "contacta a los servicios de emergencia de tu localidad "
            "y no te quedes solo/a."
        ))

    # Clave de Gemini guardada en Render
    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        return jsonify(reply=(
            "En este momento el asistente no está disponible. "
            "Por favor, intenta nuevamente más tarde."
        ))

    prompt = f"""
Eres el asistente de orientación de "Raíces de Bienestar",
una plataforma escolar de apoyo emocional para estudiantes.

Tu función es escuchar, orientar y responder con empatía.

REGLAS:
- Responde en español.
- Usa lenguaje sencillo apropiado para estudiantes.
- Sé amable, empático y respetuoso.
- No diagnostiques enfermedades.
- No sustituyas a la psicóloga ni a profesionales.
- No inventes información.
- Da respuestas breves y claras.
- Si el estudiante cuenta un problema, valida primero lo que siente
  y después ofrece una orientación práctica.
- Si existe una situación de riesgo, recomienda buscar inmediatamente
  ayuda de un adulto de confianza y servicios profesionales.
- No digas que eres una persona.

Mensaje del estudiante:
{original_text}
"""

    url = (
        "https://generativelanguage.googleapis.com/"
        "v1beta/models/gemini-2.5-flash:generateContent"
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": api_key
            },
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))

        reply = (
            result.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text")
        )

        if not reply:
            reply = "No pude generar una respuesta en este momento."

        return jsonify(reply=reply)

    except Exception as e:
        print("ERROR GEMINI:", e)
        return jsonify(reply=(
            "No pude conectarme con el asistente en este momento. "
            "Por favor, intenta nuevamente."
        ))
init_db()
if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
