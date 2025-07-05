

from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import unicodedata
import re
import difflib


aplicacion = Flask(__name__)

DB_PATH = "BaseLeyes.db"
TABLA = "articulos"

def normalizar(texto):
    if not isinstance(texto, str):
        return ''
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    ).lower()

def generar_frases(texto, max_palabras=3):
    palabras = texto.split()
    frases = []
    for n in range(2, max_palabras + 1):
        for i in range(len(palabras) - n + 1):
            frase = ' '.join(palabras[i:i + n])
            if len(frase) > 5:  # evitar palabras muy cortas como "de la"
                frases.append(frase)
    return frases

def formatear_descripcion(texto):
    texto = texto.replace("\n", "<br><br>")
    return texto

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

@aplicacion.route("/", methods=["GET", "POST"])
def index():
    palabra   = request.form.get("palabra", "").strip()
    ley_id    = request.form.get("ley_id", "")
    articulo  = request.form.get("articulo", "")
    resultados = []
    resultados_sql = []
    sugerencia = ""


    if palabra:
        palabra_normalizada = normalizar(palabra)
        resultados_sql = sql(f"SELECT * FROM {TABLA}")
        resultados = []
        frases_posibles = []

        for fila in resultados_sql:
            r = dict(fila)
            texto_original = r["descripcion"] or ""
            texto_normalizado = normalizar(texto_original)

            if palabra_normalizada in texto_normalizado:
                index = texto_normalizado.find(palabra_normalizada)
                frase_aproximada = texto_original[index:index+len(palabra)]

                try:
                    texto_resaltado = re.sub(
                        re.escape(frase_aproximada),
                        f"<span style='background-color: yellow; font-weight: bold;'>{frase_aproximada}</span>",
                        texto_original,
                        flags=re.IGNORECASE
                    )
                except:
                    texto_resaltado = texto_original

                r["descripcion"] = formatear_descripcion(texto_resaltado)
                resultados.append(r)
            else:
                frases = generar_frases(texto_original)
                for f in frases:
                    frases_posibles.append((f, texto_original))

        if not resultados and frases_posibles:
            frases_norm = list(set(normalizar(f[0]) for f in frases_posibles if f[0]))
            sugeridas = difflib.get_close_matches(palabra_normalizada, frases_norm, n=1, cutoff=0.75)
            if sugeridas:
                frase_elegida = sugeridas[0]
                for f, fuente in frases_posibles:
                    if normalizar(f) == frase_elegida:
                        sugerencia = f
                        break

    elif ley_id and articulo:
        resultados_sql = sql(f"""
            SELECT * FROM {TABLA} 
            WHERE ley_id = ? AND articulo = ?
            ORDER BY articulo, numero, letra
        """, (ley_id, articulo))

        resultados = [dict(r) for r in resultados_sql]
        for r in resultados:
            r["descripcion"] = formatear_descripcion(r["descripcion"])


    elif ley_id:
        resultados_sql = sql(f"""
            SELECT * FROM {TABLA} 
            WHERE ley_id = ?
            ORDER BY articulo, numero, letra
        """, (ley_id,))

        resultados = [dict(r) for r in resultados_sql]
        for r in resultados:
            r["descripcion"] = formatear_descripcion(r["descripcion"])


    leyes = sql(f"SELECT DISTINCT ley_id, nombre_ley FROM {TABLA} ORDER BY nombre_ley")
    articulos = sql(f"SELECT DISTINCT articulo FROM {TABLA} WHERE ley_id = ? ORDER BY articulo", (ley_id,)) if ley_id else []


    return render_template("index.html",
        palabra=palabra,
        ley_id=ley_id,
        articulo=articulo,
        leyes=leyes,
        articulos=articulos,
        resultados=resultados,
        sugerencia=sugerencia
    )

@aplicacion.route("/actualizar", methods=["POST"])
def actualizar():
    ley_id      = request.form["ley_id"]
    articulo    = request.form["articulo"]
    explicacion = request.form["explicacion"]

    sql_exec(f"""
        UPDATE {TABLA} SET explicacion = ?
        WHERE ley_id = ? AND articulo = ?
    """, (explicacion, ley_id, articulo))

    return redirect(url_for("index", ley_id=ley_id, articulo=articulo))

if __name__ == "__main__":
    aplicacion.run(debug=True)