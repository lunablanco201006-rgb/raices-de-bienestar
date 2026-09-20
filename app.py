import os
import sqlite3
import json
import urllib.request
from datetime import datetime
from functools import wraps

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    jsonify,
    flash,
    g
)

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "cambia-esta-clave-en-produccion"
)

DB = os.path.join(
    os.path.dirname(__file__),
    "bienestar.db"
)


# =========================================================
# BASE DE DATOS
# =========================================================

def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    con = db()

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

    con.commit()
    con.close()


# =========================================================
# PROTECCIÓN DE RUTAS
# =========================================================

def login_required(fn):

    @wraps(fn)
    def wrapper(*args, **kwargs):

        if not g.user:
            return redirect(url_for("login"))

        return fn(*args, **kwargs)

    return wrapper


# =========================================================
# CARGAR USUARIO
# =========================================================

@app.before_request
def load_user():

    g.user = None

    if "user_id" in session:

        con = db()

        g.user = con.execute(
            """
            SELECT id, name, email
            FROM users
            WHERE id = ?
            """,
            (session["user_id"],)
        ).fetchone()

        con.close()


# =========================================================
# PÁGINA PRINCIPAL
# =========================================================

@app.route("/")
def index():

    return render_template(
        "index.html",
        user=g.user
    )


# =========================================================
# REGISTRO
# =========================================================

@app.route("/registro", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        from werkzeug.security import generate_password_hash

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        if (
            len(name) < 2
            or "@" not in email
            or len(password) < 6
        ):

            flash(
                "Completa los datos correctamente. "
                "La contraseña debe tener al menos 6 caracteres.",
                "error"
            )

            return render_template(
                "register.html"
            )

        con = db()

        try:

            cur = con.execute(
                """
                INSERT INTO users
                (name, email, password, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    name,
                    email,
                    generate_password_hash(password),
                    datetime.now().isoformat(
                        timespec="seconds"
                    )
                )
            )

            con.commit()

            session["user_id"] = cur.lastrowid

        except sqlite3.IntegrityError:

            con.close()

            flash(
                "Ese correo ya está registrado.",
                "error"
            )

            return render_template(
                "register.html"
            )

        con.close()

        return redirect(
            url_for("dashboard")
        )

    return render_template(
        "register.html"
    )


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        from werkzeug.security import check_password_hash

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        con = db()

        user = con.execute(
            """
            SELECT *
            FROM users
            WHERE email = ?
            """,
            (email,)
        ).fetchone()

        con.close()

        if user and check_password_hash(
            user["password"],
            password
        ):

            session["user_id"] = user["id"]

            return redirect(
                url_for("dashboard")
            )

        flash(
            "Correo o contraseña incorrectos.",
            "error"
        )

    return render_template(
        "login.html"
    )


# =========================================================
# CERRAR SESIÓN
# =========================================================

@app.route("/salir")
def logout():

    session.clear()

    return redirect(
        url_for("index")
    )


# =========================================================
# PANEL / DASHBOARD
# =========================================================

@app.route("/panel")
@login_required
def dashboard():

    con = db()

    rows = con.execute(
        """
        SELECT mood, score, note, created_at
        FROM moods
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 20
        """,
        (g.user["id"],)
    ).fetchall()

    con.close()

    history = [
        dict(x)
        for x in rows
    ][::-1]

    return render_template(
        "dashboard.html",
        user=g.user,
        history=history
    )


# =========================================================
# GUARDAR ESTADO DE ÁNIMO
# =========================================================

@app.route("/api/mood", methods=["POST"])
@login_required
def mood():

    data = request.get_json(
        silent=True
    ) or {}

    mood_value = data.get(
        "mood",
        ""
    )

    try:
        score = int(
            data.get(
                "score",
                0
            )
        )
    except (TypeError, ValueError):
        score = 0

    note = data.get(
        "note",
        ""
    ).strip()[:500]

    if (
        mood_value not in [
            "Muy bien",
            "Bien",
            "Regular",
            "Triste",
            "Muy mal"
        ]
        or score not in range(1, 6)
    ):

        return jsonify(
            ok=False,
            message="Datos inválidos"
        ), 400

    con = db()

    con.execute(
        """
        INSERT INTO moods
        (user_id, mood, score, note, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            g.user["id"],
            mood_value,
            score,
            note,
            datetime.now().strftime(
                "%Y-%m-%d %H:%M"
            )
        )
    )

    con.commit()
    con.close()

    return jsonify(
        ok=True
    )


# =========================================================
# OBTENER ESTADOS DE ÁNIMO
# =========================================================

@app.route("/api/moods")
@login_required
def moods():

    con = db()

    rows = con.execute(
        """
        SELECT mood, score, note, created_at
        FROM moods
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 30
        """,
        (g.user["id"],)
    ).fetchall()

    con.close()

    return jsonify([
        dict(x)
        for x in rows
    ])


# =========================================================
# RECURSOS
# =========================================================

@app.route("/recursos")
def resources():

    return render_template(
        "resources.html",
        user=g.user
    )


# =========================================================
# PÁGINA DEL CHAT
# =========================================================

@app.route("/chat")
def chat():

    return render_template(
        "chat.html",
        user=g.user
    )


# =========================================================
# CHAT CON GEMINI
# =========================================================

@app.route("/api/chat", methods=["POST"])
def chat_api():

    data = request.get_json(
        silent=True
    ) or {}

    original_text = data.get(
        "message",
        ""
    ).strip()

    text = original_text.lower()

    # -----------------------------------------------------
    # MENSAJE VACÍO
    # -----------------------------------------------------

    if not original_text:

        return jsonify(
            reply=(
                "Cuéntame un poco más sobre "
                "lo que estás sintiendo."
            )
        )


    # -----------------------------------------------------
    # DETECCIÓN DE CRISIS
    # -----------------------------------------------------

    crisis = [
        "suicid",
        "matarme",
        "hacerme daño",
        "hacer daño",
        "no quiero vivir",
        "autoles",
        "quitarme la vida"
    ]

    if any(
        palabra in text
        for palabra in crisis
    ):

        return jsonify(
            reply=(
                "Siento que estés pasando por "
                "algo tan difícil. No estás solo/a. "
                "Busca ahora mismo a una persona de "
                "confianza y ayuda profesional. "
                "Si existe un peligro inmediato, "
                "contacta a los servicios de emergencia "
                "de tu localidad y no te quedes solo/a."
            )
        )


    # -----------------------------------------------------
    # OBTENER API KEY DE GEMINI
    # -----------------------------------------------------

    api_key = os.environ.get(
        "GEMINI_API_KEY"
    )

    if not api_key:

        print(
            "ERROR GEMINI: "
            "No existe GEMINI_API_KEY"
        )

        return jsonify(
            reply=(
                "En este momento el asistente "
                "no está disponible. "
                "Por favor, intenta nuevamente más tarde."
            )
        )


    # -----------------------------------------------------
    # PROMPT DEL ASISTENTE
    # -----------------------------------------------------

    prompt = f"""
Eres el asistente virtual de "Raíces de Bienestar",
una plataforma escolar de apoyo emocional para estudiantes.

Tu función es escuchar y orientar de manera general.

REGLAS IMPORTANTES:

- Responde siempre en español.
- Sé empático, amable y respetuoso.
- Usa lenguaje sencillo y apropiado para estudiantes.
- No diagnostiques enfermedades.
- No digas que eres psicólogo/a.
- No sustituyas a la psicóloga del colegio ni a un profesional.
- No inventes información sobre el estudiante.
- No juzgues al estudiante.
- No respondas siempre de la misma manera.
- Adapta tu respuesta al mensaje que recibas.
- Puedes hacer preguntas suaves para comprender mejor la situación.
- Puedes sugerir hablar con una persona de confianza.
- Puedes sugerir estrategias sencillas como respirar,
  escribir lo que siente, descansar o buscar apoyo.
- Si el estudiante habla de peligro inmediato,
  autolesiones o suicidio, recomienda buscar inmediatamente
  ayuda de un adulto de confianza y servicios de emergencia.

La plataforma se llama:
Raíces de Bienestar.

Mensaje del estudiante:
{original_text}

Responde de forma natural, breve y comprensiva.
"""


    # -----------------------------------------------------
    # URL DE GEMINI
    # -----------------------------------------------------

    url = (
       "https://generativelanguage.googleapis.com/"
    "v1beta/models/gemini-3.6-flash:generateContent"

    )


    # -----------------------------------------------------
    # DATOS QUE ENVIAMOS A GEMINI
    # -----------------------------------------------------

    payload = {

        "contents": [

            {

                "parts": [

                    {
                        "text": prompt
                    }

                ]

            }

        ]

    }


    # -----------------------------------------------------
    # CONEXIÓN CON GEMINI
    # -----------------------------------------------------

    try:

        req = urllib.request.Request(

            url,

            data=json.dumps(
                payload
            ).encode("utf-8"),

            headers={

                "Content-Type":
                    "application/json",

                "x-goog-api-key":
                    api_key

            },

            method="POST"
        )


        with urllib.request.urlopen(
            req,
            timeout=30
        ) as response:

            result = json.loads(
                response.read().decode(
                    "utf-8"
                )
            )


        # -------------------------------------------------
        # OBTENER RESPUESTA DE GEMINI
        # -------------------------------------------------

        reply = (
            result
            .get(
                "candidates",
                [{}]
            )[0]
            .get(
                "content",
                {}
            )
            .get(
                "parts",
                [{}]
            )[0]
            .get(
                "text"
            )
        )


        if not reply:

            reply = (
                "No pude generar una respuesta "
                "en este momento. Intenta nuevamente."
            )


        return jsonify(
            reply=reply
        )


    except urllib.error.HTTPError as e:

        error_body = ""

        try:
            error_body = e.read().decode("utf-8")
        except Exception:
            pass

        print("================================")
        print("ERROR GEMINI HTTP:", e.code)
        print("RESPUESTA DE GOOGLE:", error_body)
        print("================================")

        return jsonify(
            reply=(
                "No pude conectarme con el asistente "
                "en este momento. Intenta nuevamente."
            )
        )

    except Exception as e:

        print(
            "ERROR GEMINI:",
            e
        )

        return jsonify(
            reply=(
                "No pude conectarme con el "
                "asistente en este momento. "
                "Por favor, intenta nuevamente."
            )
        )


# =========================================================
# INICIAR BASE DE DATOS
# =========================================================

init_db()


# =========================================================
# EJECUTAR APLICACIÓN
# =========================================================

if __name__ == "__main__":
    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
    )