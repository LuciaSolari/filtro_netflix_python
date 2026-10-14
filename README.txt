BUSCADOR WEB DE PELÍCULAS Y SERIES (Python + Flask + MySQL)

La web consulta la base proyectoFinalDB_v2 y la tabla dataset, basada en los archivos SQL que compartiste.
Permite filtrar por:
- texto en título, director, elenco o descripción
- tipo (Movie / TV Show)
- país
- clasificación (rating)
- categoría/género
- año desde y año hasta
Incluye resultados paginados.

REQUISITOS
- Python 3.10 o superior
- MySQL iniciado
- Base de datos proyectoFinalDB_v2 creada y tabla dataset cargada

INSTALACIÓN EN WINDOWS (PowerShell o CMD)
1. Descomprimí el ZIP en una carpeta.
2. Abrí una terminal dentro de esa carpeta.
3. Creá un entorno virtual (opcional, recomendado):
   python -m venv .venv
4. Activá el entorno:
   PowerShell: .\.venv\Scripts\Activate.ps1
   CMD:        .venv\Scripts\activate.bat
5. Instalá dependencias:
   pip install -r requirements.txt
6. Revisá la conexión en app.py. Valores predeterminados:
   host=localhost, port=3306, user=root, password vacío,
   database=proyectoFinalDB_v2.
   Si tu MySQL usa otra contraseña, editá DB_CONFIG o definí DB_PASSWORD.
7. Iniciá la web:
   python app.py
8. Abrí en el navegador:
   http://127.0.0.1:5000

IMPORTANTE SOBRE LA BASE
El archivo "Dataset.txt" contiene SQL para crear/cargar la tabla dataset, pero la carga usa
el CSV netflix_titles.csv desde /var/lib/mysql-files/netflix_titles.csv. Esa ruta corresponde
a un entorno Linux/MySQL y puede no funcionar directamente en XAMPP/Windows.
Primero asegurate de importar el CSV en tu base y comprobar que dataset tenga registros.
El archivo "Tipos.txt" crea la tabla tipos a partir de dataset. La web obtiene los tipos
directamente de dataset, así que la tabla tipos no es obligatoria para que funcione.

Si aparece un error de conexión, revisá que MySQL esté iniciado y que la base y la tabla
existan. La página muestra el detalle del error para ayudarte a corregirlo.
