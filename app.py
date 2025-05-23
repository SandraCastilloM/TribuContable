
from flask import Flask, render_template, request, redirect, url_for
import sqlite3

app = Flask(__name__)

DB_PATH = "Base.db"
TABLA = "articulos"

# Helpers

def sql(query: str, params: tuple = ()): 
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(query, params)
        return cur.fetchall()

def sql_exec(query: str, params: tuple = ()): 
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute(query, params)
        conn.commit()

@app.route("/", methods=["GET", "POST"])
def index():
    palabra   = request.form.get("palabra", "").strip()
    ley_id    = request.form.get("ley_id", "")
    articulo  = request.form.get("articulo", "")

    # Resultado de búsqueda
    resultados = []
    if palabra:
        resultados = sql(f"""
            SELECT * FROM {TABLA} 
            WHERE descripcion LIKE ? 
            ORDER BY ley_id, articulo
        """, (f"%{palabra}%",))

    elif ley_id and articulo:
        resultados = sql(f"""
            SELECT * FROM {TABLA} 
            WHERE ley_id = ? AND articulo = ?
        """, (ley_id, articulo))

    elif ley_id:
        resultados = sql(f"""
            SELECT * FROM {TABLA} 
            WHERE ley_id = ? 
            ORDER BY articulo
        """, (ley_id,))

    # Leyes disponibles para mostrar en el combo
    leyes = sql(f"SELECT DISTINCT ley_id, nombre_ley FROM {TABLA} ORDER BY nombre_ley")
    articulos = sql(f"SELECT DISTINCT articulo FROM {TABLA} WHERE ley_id = ? ORDER BY articulo", (ley_id,)) if ley_id else []

    return render_template("index.html",
        palabra=palabra,
        ley_id=ley_id,
        articulo=articulo,
        leyes=leyes,
        articulos=articulos,
        resultados=resultados
    )

@app.route("/actualizar", methods=["POST"])
def actualizar():
    ley_id      = request.form["ley_id"]
    articulo    = request.form["articulo"]
    explicacion = request.form["explicacion"]

    sql_exec(f"""
        UPDATE {TABLA} SET explicacion = ?
        WHERE ley_id = ? AND articulo = ?
    """, (explicacion, ley_id, articulo))

    return redirect(url_for("index", ley_id=ley_id, articulo=articulo))

@app.route("/agregar", methods=["POST"])
def agregar():
    data = {
        "ley_id":      request.form["n_ley_id"].strip(),
        "nombre_ley":  request.form["n_nombre_ley"].strip(),
        "articulo":    request.form["n_articulo"].strip(),
        "numero":      request.form["n_numero"].strip(),
        "letra":       request.form["n_letra"].strip(),
        "descripcion": request.form["n_descripcion"].strip(),
        "explicacion": request.form["n_explicacion"].strip(),
    }

    # Verificar duplicado
    existe = sql(f"SELECT 1 FROM {TABLA} WHERE ley_id = ? AND articulo = ?", (data["ley_id"], data["articulo"]))
    if existe:
        return "<p>⚠ Ese artículo ya existe. Usa edición.</p><a href='/'>Volver</a>"

    sql_exec(f"""
        INSERT INTO {TABLA} 
        (ley_id, nombre_ley, articulo, numero, letra, descripcion, explicacion)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, tuple(data.values()))

    return redirect(url_for("index", ley_id=data["ley_id"]))

if __name__ == "__main__":
    app.run(debug=True)
