import os
from flask import Flask, render_template, request, url_for
import requests
from functools import lru_cache
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "root"),
    "database": os.getenv("DB_NAME", "proyectofinaldb_v2"),
    "charset": "utf8mb4",
}

PER_PAGE = 20


TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
TMDB_BASE_URL = "https://api.themoviedb.org/3"


@lru_cache(maxsize=500)
def buscar_portada(titulo, tipo, anio):
    if not TMDB_API_KEY or not titulo:
        return None

    tipo_normalizado = (tipo or "").strip().lower()

    tipo_tmdb = (
    "movie"
    if "pel" in tipo_normalizado or "movie" in tipo_normalizado
    else "tv"
)

    try:
        respuesta = requests.get(
            f"{TMDB_BASE_URL}/search/{tipo_tmdb}",
            params={
                "api_key": TMDB_API_KEY,
                "query": titulo,
                "language": "es-ES",
                "year" if tipo_tmdb == "movie" else "first_air_date_year":
                    anio if anio else None,
            },
            timeout=8,
        )
        respuesta.raise_for_status()
        datos = respuesta.json()

        resultados_tmdb = datos.get("results", [])
        if not resultados_tmdb:
            return None

        # Usamos el primer resultado encontrado.
        poster_path = resultados_tmdb[0].get("poster_path")

        if poster_path:
            return f"https://image.tmdb.org/t/p/w500{poster_path}"

    except (requests.RequestException, ValueError):
        return None

    return None


def get_connection():
    return mysql.connector.connect(**DB_CONFIG)


def get_filter_options():
    conn = get_connection()

    try:
        cur = conn.cursor(dictionary=True)

        try:
            cur.execute("""
                SELECT id_tipo AS id, tipo_de_show AS nombre
                FROM tipos
                ORDER BY tipo_de_show
            """)
            tipos = cur.fetchall()

            cur.execute("""
                SELECT id_pais AS id, nombre_pais AS nombre
                FROM paises
                ORDER BY nombre_pais
            """)
            paises = cur.fetchall()

            cur.execute("""
                SELECT id_clasificacion AS id, clasificacion AS nombre
                FROM clasificaciones
                ORDER BY clasificacion
            """)
            ratings = cur.fetchall()

            cur.execute("""
                SELECT id_categoria AS id, categoria AS nombre
                FROM categorias
                ORDER BY categoria
            """)
            categorias = cur.fetchall()

            cur.execute("""
                SELECT id_actor AS id, nombre_actor AS nombre
                FROM actores
                ORDER BY nombre_actor
            """)
            actores = cur.fetchall()

            cur.execute("""
                SELECT id_director AS id, nombre_director AS nombre
                FROM directores
                ORDER BY nombre_director
            """)
            directores = cur.fetchall()

            return tipos, paises, ratings, categorias, actores, directores

        finally:
            cur.close()

    finally:
        conn.close()


@app.route("/", methods=["GET"])
def index():
    filtros = {
        "q": request.args.get("q", "").strip(),
        "tipo": request.args.get("tipo", "").strip(),
        "pais": request.args.get("pais", "").strip(),
        "rating": request.args.get("rating", "").strip(),
        "categoria": request.args.get("categoria", "").strip(),
        "actor": request.args.get("actor", "").strip(),
        "director": request.args.get("director", "").strip(),
        "desde": request.args.get("desde", "").strip(),
        "hasta": request.args.get("hasta", "").strip(),
    }

    tipos = []
    paises = []
    ratings = []
    categorias = []
    actores = []
    directores = []
    resultados = []
    total = 0
    total_general = 0
    page = 1
    pages = 1
    error = None

    try:
        (
            tipos,
            paises,
            ratings,
            categorias,
            actores,
            directores,
        ) = get_filter_options()

        where = []
        params = []

        # Buscador por título, descripción, actor y director.
        if filtros["q"]:
            like = f"%{filtros['q']}%"

            where.append("""
                (
                    s.titulo LIKE %s
                    OR s.descripcion LIKE %s
                    OR EXISTS (
                        SELECT 1
                        FROM shows_actores sa
                        JOIN actores a ON a.id_actor = sa.id_actor
                        WHERE sa.id_show = s.id_show
                        AND a.nombre_actor LIKE %s
                    )
                    OR EXISTS (
                        SELECT 1
                        FROM shows_directores sd
                        JOIN directores d ON d.id_director = sd.id_director
                        WHERE sd.id_show = s.id_show
                        AND d.nombre_director LIKE %s
                    )
                )
            """)
            params.extend([like, like, like, like])

        # Filtro por tipo.
        if filtros["tipo"].isdigit():
            where.append("s.id_tipo = %s")
            params.append(int(filtros["tipo"]))

        # Filtro por país.
        if filtros["pais"].isdigit():
            where.append("""
                EXISTS (
                    SELECT 1
                    FROM shows_paises sp
                    WHERE sp.id_show = s.id_show
                    AND sp.id_pais = %s
                )
            """)
            params.append(int(filtros["pais"]))

        # Filtro por clasificación.
        if filtros["rating"].isdigit():
            where.append("s.id_clasificacion = %s")
            params.append(int(filtros["rating"]))

        # Filtro por categoría.
        if filtros["categoria"].isdigit():
            where.append("""
                EXISTS (
                    SELECT 1
                    FROM shows_categorias sc
                    WHERE sc.id_show = s.id_show
                    AND sc.id_categoria = %s
                )
            """)
            params.append(int(filtros["categoria"]))

        # Filtro por actor.
        if filtros["actor"].isdigit():
            where.append("""
                EXISTS (
                    SELECT 1
                    FROM shows_actores sa
                    WHERE sa.id_show = s.id_show
                    AND sa.id_actor = %s
                )
            """)
            params.append(int(filtros["actor"]))

        # Filtro por director.
        if filtros["director"].isdigit():
            where.append("""
                EXISTS (
                    SELECT 1
                    FROM shows_directores sd
                    WHERE sd.id_show = s.id_show
                    AND sd.id_director = %s
                )
            """)
            params.append(int(filtros["director"]))

        # Filtro por año de lanzamiento.
        if filtros["desde"].isdigit():
            where.append("s.anio_salida >= %s")
            params.append(int(filtros["desde"]))

        if filtros["hasta"].isdigit():
            where.append("s.anio_salida <= %s")
            params.append(int(filtros["hasta"]))

        where_sql = ""
        if where:
            where_sql = " WHERE " + " AND ".join(where)

        conn = get_connection()

        try:
            cur = conn.cursor(dictionary=True)

            try:
                # Cantidad de resultados que cumplen los filtros.
                cur.execute(
                    "SELECT COUNT(*) AS total FROM shows s" + where_sql,
                    params,
                )
                total = cur.fetchone()["total"]

                # Cantidad total de registros de la tabla shows.
                cur.execute("SELECT COUNT(*) AS total FROM shows")
                total_general = cur.fetchone()["total"]

                # Paginación.
                page = max(1, request.args.get("page", default=1, type=int))
                pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
                page = min(page, pages)
                offset = (page - 1) * PER_PAGE

                # Consulta de resultados y datos relacionados.
                consulta = """
                    SELECT
                        s.id_show,
                        s.titulo,
                        t.tipo_de_show AS tipo,
                        s.fecha_aniadido,
                        s.anio_salida,
                        cl.clasificacion,
                        s.duracion,
                        s.descripcion,

                        (
                            SELECT GROUP_CONCAT(
                                DISTINCT a.nombre_actor
                                ORDER BY a.nombre_actor
                                SEPARATOR ', '
                            )
                            FROM shows_actores sa
                            JOIN actores a
                                ON a.id_actor = sa.id_actor
                            WHERE sa.id_show = s.id_show
                        ) AS actores,

                        (
                            SELECT GROUP_CONCAT(
                                DISTINCT d.nombre_director
                                ORDER BY d.nombre_director
                                SEPARATOR ', '
                            )
                            FROM shows_directores sd
                            JOIN directores d
                                ON d.id_director = sd.id_director
                            WHERE sd.id_show = s.id_show
                        ) AS directores,

                        (
                            SELECT GROUP_CONCAT(
                                DISTINCT p.nombre_pais
                                ORDER BY p.nombre_pais
                                SEPARATOR ', '
                            )
                            FROM shows_paises sp
                            JOIN paises p
                                ON p.id_pais = sp.id_pais
                            WHERE sp.id_show = s.id_show
                        ) AS paises,

                        (
                            SELECT GROUP_CONCAT(
                                DISTINCT c.categoria
                                ORDER BY c.categoria
                                SEPARATOR ', '
                            )
                            FROM shows_categorias sc
                            JOIN categorias c
                                ON c.id_categoria = sc.id_categoria
                            WHERE sc.id_show = s.id_show
                        ) AS categorias

                    FROM shows s
                    LEFT JOIN tipos t
                        ON t.id_tipo = s.id_tipo
                    LEFT JOIN clasificaciones cl
                        ON cl.id_clasificacion = s.id_clasificacion
                """ + where_sql + """
                    ORDER BY s.titulo
                    LIMIT %s OFFSET %s
                """

                cur.execute(
                    consulta,
                    params + [PER_PAGE, offset],
                )
                resultados = cur.fetchall()

                for item in resultados:
                 item["portada"] = buscar_portada(
                 item["titulo"],
                 item.get("tipo"),
                 item.get("anio_salida"),
              )

            finally:
                cur.close()

        finally:
            conn.close()

    except Error as exc:
        error = (
            "No se pudo consultar la base de datos. "
            "Comprobá que MySQL esté iniciado y que las tablas y "
            "columnas tengan los nombres esperados. "
            f"Detalle: {exc}"
        )

    return render_template(
        "index.html",
        resultados=resultados,
        filtros=filtros,
        tipos=tipos,
        paises=paises,
        ratings=ratings,
        categorias=categorias,
        actores=actores,
        directores=directores,
        total=total,
        total_general=total_general,
        page=page,
        pages=pages,
        error=error,
    )


if __name__ == "__main__":
    app.run(debug=True)
