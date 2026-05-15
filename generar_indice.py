import os
import sys
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
import json
import re
import asyncio
import io
import base64
from datetime import datetime
from PIL import Image
from hydrogram import Client
from dotenv import load_dotenv

# Configuración inicial
load_dotenv()
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
CHANNEL_ID = -1002923573607
HTML_OUTPUT = "indice_libros.html"
DB_FILE = "indice_libros.json"

# Para asegurarnos de que usa la sesión existente en src/
# Pasamos la ruta relativa "src/my_session", o el STRING_SESSION si estamos en GitHub
SESSION_STRING = os.getenv('SESSION_STRING')
if SESSION_STRING:
    app = Client("memory_session", session_string=SESSION_STRING, api_id=API_ID, api_hash=API_HASH)
else:
    app = Client("src/my_session", api_id=API_ID, api_hash=API_HASH)

DEFAULT_IMAGE_B64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAJYAAADIAQMAAAAwS4omAAAAA1BMVEWAgICQdD0xAAAANUlEQVR42u3BAQ0AAADCoPdPbQ8HFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAB8GzXDAAHTSjU2AAAAAElFTkSuQmCC" # Placeholder gris

def optimize_image_b64(raw_data):
    try:
        img = Image.open(io.BytesIO(raw_data))
        if img.mode in ("RGBA", "P"): 
            img = img.convert("RGB")
        img.thumbnail((240, 360), Image.Resampling.LANCZOS)
        output = io.BytesIO()
        img.save(output, format="JPEG", quality=65, optimize=True)
        return f"data:image/jpeg;base64,{base64.b64encode(output.getvalue()).decode('utf-8')}"
    except Exception as e:
        print(f"Error optimizando imagen: {e}")
        return None

def extract_title_and_desc(text):
    if not text:
        return "Sin título", ""
    lines = text.strip().split('\n')
    title = lines[0].strip()
    # Eliminar emojis o hashtags al inicio del título si se desea, por ahora se deja tal cual
    desc = '<br>'.join(line.strip() for line in lines[1:] if line.strip())
    return title, desc

def generate_html(items):
    # Generador de HTML con diseño "Premium"
    json_data = json.dumps(items)
    
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Catálogo de Lectura</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;500;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-color: #0f172a;
            --surface-color: rgba(30, 41, 59, 0.7);
            --surface-hover: rgba(51, 65, 85, 0.9);
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --accent: #38bdf8;
            --accent-glow: rgba(56, 189, 248, 0.5);
            --border: rgba(255, 255, 255, 0.08);
        }}
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; font-family: 'Inter', sans-serif; transition: all 0.25s ease; }}
        
        body {{
            background: radial-gradient(circle at top right, #1e293b, var(--bg-color));
            color: var(--text-main);
            min-height: 100vh;
            padding-bottom: 50px;
        }}

        header {{
            background: rgba(15, 23, 42, 0.8);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--border);
            padding: 20px 40px;
            display: flex;
            flex-direction: column;
            align-items: center;
            position: sticky;
            top: 0;
            z-index: 100;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }}
        
        .header-content {{
            display: flex;
            align-items: center;
            gap: 25px;
            margin-bottom: 15px;
        }}

        .header-logo {{
            width: 80px;
            height: 80px;
            border-radius: 50%;
            object-fit: cover;
            border: 2px solid var(--accent);
            box-shadow: 0 0 15px var(--accent-glow);
        }}

        .header-text {{
            display: flex;
            flex-direction: column;
            justify-content: center;
        }}

        h1 {{ font-size: 2.5rem; font-weight: 800; letter-spacing: -1px; margin-bottom: 5px; color: #fff; }}
        .subtitle {{ color: var(--accent); font-weight: 500; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 3px; }}
        
        .search-container {{
            margin-top: 25px;
            width: 100%;
            max-width: 600px;
            position: relative;
        }}

        #search {{
            width: 100%;
            padding: 16px 24px;
            border-radius: 50px;
            background: var(--surface-color);
            border: 1px solid var(--border);
            color: white;
            font-size: 1.1rem;
            outline: none;
            box-shadow: 0 4px 20px rgba(0,0,0,0.2);
        }}

        #search:focus {{
            border-color: var(--accent);
            box-shadow: 0 0 20px var(--accent-glow);
            background: rgba(30, 41, 59, 0.9);
        }}

        .alphabet {{
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 8px;
            padding: 20px 40px;
            max-width: 1000px;
            margin: 0 auto;
        }}

        .letter-btn {{
            background: var(--surface-color);
            border: 1px solid var(--border);
            color: var(--text-main);
            padding: 10px 15px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 800;
            font-size: 1rem;
        }}

        .letter-btn:hover, .letter-btn.active {{
            background: var(--accent);
            color: #000;
            transform: translateY(-3px);
            box-shadow: 0 5px 15px var(--accent-glow);
        }}

        .info-bar {{
            text-align: center;
            padding: 10px;
            color: var(--text-muted);
            font-size: 0.9rem;
        }}

        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 25px;
            padding: 20px 40px;
            max-width: 1400px;
            margin: 0 auto;
        }}

        .card {{
            background: var(--surface-color);
            border: 1px solid var(--border);
            border-radius: 16px;
            overflow: hidden;
            position: relative;
            cursor: pointer;
            box-shadow: 0 10px 20px rgba(0,0,0,0.3);
            display: flex;
            flex-direction: column;
            text-decoration: none;
        }}

        .card:hover {{
            transform: translateY(-10px);
            border-color: var(--accent);
            box-shadow: 0 20px 40px rgba(0,0,0,0.5), 0 0 15px var(--accent-glow);
        }}

        .card-img {{
            width: 100%;
            aspect-ratio: 2/3;
            background-color: #000;
            background-size: cover;
            background-position: center;
            position: relative;
        }}

        .card-content {{
            padding: 15px;
            background: linear-gradient(to top, rgba(15,23,42,1) 0%, rgba(15,23,42,0.8) 100%);
            flex-grow: 1;
            display: flex;
            align-items: center;
        }}

        .card-title {{
            font-size: 0.95rem;
            font-weight: 500;
            color: white;
            line-height: 1.3;
            display: -webkit-box;
            -webkit-line-clamp: 3;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }}

        @media (max-width: 600px) {{
            .grid {{ grid-template-columns: repeat(2, 1fr); padding: 15px; gap: 15px; }}
            header {{ padding: 20px; }}
            h1 {{ font-size: 1.8rem; }}
        }}
    </style>
</head>
<body>

    <header>
        <div class="header-content">
            <img src="template/avatar.jpg" alt="Logo" class="header-logo">
            <div class="header-text">
                <h1>BIBLIOTECA - ME GUSTA LEER</h1>
                <div class="subtitle">El canal con todas las novedades en formato epub</div>
            </div>
        </div>
        <div class="search-container">
            <input type="text" id="search" placeholder="Buscar por título, autor o palabra clave...">
        </div>
    </header>

    <div class="alphabet" id="alphabet"></div>
    <div class="info-bar" id="counter-info">Cargando...</div>

    <div class="grid" id="grid"></div>

    <script>
        const allItems = {json_data};
        let filteredItems = allItems;
        let currentFilter = 'ALL';

        const alphabetContainer = document.getElementById('alphabet');
        const searchInput = document.getElementById('search');
        const grid = document.getElementById('grid');
        const counterInfo = document.getElementById('counter-info');

        // Generar botones A-Z
        const letters = ['TODO', '#', ...'ABCDEFGHIJKLMNOPQRSTUVWXYZ'];
        letters.forEach(l => {{
            const btn = document.createElement('button');
            btn.className = 'letter-btn';
            if (l === 'TODO') btn.classList.add('active');
            btn.innerText = l;
            btn.onclick = () => filterByLetter(l, btn);
            alphabetContainer.appendChild(btn);
        }});

        function filterByLetter(letter, btnElement) {{
            document.querySelectorAll('.letter-btn').forEach(b => b.classList.remove('active'));
            btnElement.classList.add('active');
            currentFilter = letter;
            searchInput.value = ''; // Limpiar buscador
            applyFilters();
        }}

        searchInput.addEventListener('input', () => {{
            document.querySelectorAll('.letter-btn').forEach(b => b.classList.remove('active'));
            document.querySelector('.letter-btn').classList.add('active'); // Seleccionar 'TODO' visualmente
            currentFilter = 'SEARCH';
            applyFilters();
        }});

        function applyFilters() {{
            const term = searchInput.value.toLowerCase().trim();
            
            filteredItems = allItems.filter(item => {{
                // Filtro de búsqueda
                if (currentFilter === 'SEARCH' || term) {{
                    return item.title.toLowerCase().includes(term) || item.description.toLowerCase().includes(term);
                }}
                
                // Filtro por letras
                if (currentFilter === 'TODO') return true;
                
                const firstChar = item.title.charAt(0).toUpperCase();
                if (currentFilter === '#') {{
                    return /^[0-9\\W]/.test(firstChar); // Número o símbolo
                }}
                return firstChar === currentFilter;
            }});

            // Ordenar alfabéticamente
            filteredItems.sort((a, b) => a.title.localeCompare(b.title));
            renderGrid();
        }}

        function renderGrid() {{
            grid.innerHTML = '';
            const fragment = document.createDocumentFragment();
            
            filteredItems.forEach(item => {{
                // El card completo es un enlace que abre en otra pestaña
                const card = document.createElement('a');
                card.className = 'card';
                card.href = item.telegram_url;
                card.target = '_blank';
                
                card.innerHTML = `
                    <div class="card-img" style="background-image: url('${{item.image}}')"></div>
                    <div class="card-content">
                        <div class="card-title">${{item.title}}</div>
                    </div>
                `;
                fragment.appendChild(card);
            }});
            
            grid.appendChild(fragment);
            counterInfo.innerText = `Mostrando ${{filteredItems.length}} de ${{allItems.length}} publicaciones`;
        }}

        // Inicializar
        applyFilters();
    </script>
</body>
</html>"""
    with open(HTML_OUTPUT, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"✅ HTML generado exitosamente en: {HTML_OUTPUT}")

async def main():
    print("🚀 Iniciando Gestor de Colecciones Telegram...")
    
    # Cargar base de datos existente para no procesar todo desde cero
    existing_data = []
    indexed_ids = set()
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
                for item in existing_data:
                    indexed_ids.add(str(item['id']))
            print(f"📦 Base de datos cargada con {len(existing_data)} elementos.")
        except:
            print("⚠️ Base de datos corrupta o vacía. Se creará una nueva.")

    new_items_count = 0
    
    async with app:
        print("📡 Conectando a Telegram...")
        try:
            chat = await app.get_chat(CHANNEL_ID)
            print(f"✅ Conectado al canal: {chat.title}")
            
            pending_documents = []
            
            # Recorrer historial (de más reciente a más antiguo)
            async for message in app.get_chat_history(CHANNEL_ID):
                msg_id = str(message.id)
                
                # Si encontramos el ID en la base de datos, significa que ya leímos esto y todo lo más antiguo
                if msg_id in indexed_ids:
                    break
                    
                # Si es un documento, lo guardamos en la lista de pendientes
                if message.document:
                    title = message.document.file_name.rsplit('.', 1)[0] if message.document.file_name else "Sin Título"
                    desc = message.caption or message.text or ""
                    telegram_url = f"https://t.me/c/{str(chat.id)[4:]}/{msg_id}" if str(chat.id).startswith("-100") else f"https://t.me/{chat.id}/{msg_id}"
                    
                    pending_documents.append({
                        "id": msg_id,
                        "title": title,
                        "description": desc,
                        "telegram_url": telegram_url,
                        "date": message.date.isoformat()
                    })
                    
                # Si es una foto y tenemos documentos pendientes, asociamos la foto a los documentos
                elif message.photo and pending_documents:
                    img_b64 = None
                    try:
                        img_data = await message.download(in_memory=True)
                        if img_data:
                            img_b64 = optimize_image_b64(img_data.getbuffer())
                    except Exception as e:
                        print(f"⚠️ Error al descargar imagen del msg {msg_id}: {e}")
                        
                    if not img_b64:
                        img_b64 = DEFAULT_IMAGE_B64
                        
                    img_text = message.caption or message.text
                    
                    for doc in pending_documents:
                        doc["image"] = img_b64
                        # Si la imagen tiene texto (sinopsis), lo usamos
                        if img_text and not doc["description"]:
                            doc["description"] = img_text
                        elif not doc["description"]:
                            doc["description"] = "Archivo sin descripción adjunta."
                            
                        existing_data.append(doc)
                        print(f"➕ Añadido: {doc['title']}")
                        new_items_count += 1
                        
                    # Limpiamos los documentos pendientes listos para el siguiente libro
                    pending_documents = []
                
        except Exception as e:
            print(f"❌ Error fatal: {e}")
            
    # Guardar en JSON
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(existing_data, f, ensure_ascii=False, indent=4)
        
    print(f"💾 Se han guardado {new_items_count} elementos nuevos.")
    
    # Generar HTML
    generate_html(existing_data)
    
if __name__ == "__main__":
    app.run(main())
