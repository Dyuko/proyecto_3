import requests
import time
from bs4 import BeautifulSoup
from pymongo import MongoClient
from urllib.parse import urljoin
import re
from pymongo.server_api import ServerApi

# Configuración de MongoDB
uri = "mongodb+srv://ucom:x5QQCZj.LENr2mF@cluster0.xmqhzxd.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(uri, server_api=ServerApi('1'))
db = client['clasipar']
collection = db['properties']
collection.create_index([('NrodeAnuncio', 1)], unique=True)  # Índice único para evitar duplicados

# Headers para las solicitudes
headers = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'accept-language': 'en-US,en;q=0.9,es-ES;q=0.8,es;q=0.7',
    'cache-control': 'no-cache',
    'pragma': 'no-cache',
    'priority': 'u=0, i',
    'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'same-origin',
    'sec-fetch-user': '?1',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'
}

# Cookies (extraídas del curl)
cookies = {
    'SL_G_WPT_TO': 'es',
    'SL_GWPT_Show_Hide_tmp': '1',
    'clp_v2': 'ifYFN3jHJXcBJC0XGhf4GBrJaVvfL32MrW_uZITYfzL4AP98bBiqvpAB6OlvfpdEaJYA7iFW2pYBpbZ3560gZAXcZiekEPZ663SRaOTePd8nrvzuwZ_HxjsFf7L15YFMgR8lQBE88CfnrndkTgYWlY3HjjnRtTr_6xq9tmuV9nJ6ZDm8NDT8kIGB3aOwbHBrSoGp0fcd-XXt1s1a1Pj0-XUxzz9zC3pX5xYW3iPGdlM',
    'SL_wptGlobTipTmp': '1',
    'clpw': '8vaw66do3h8jaz1rk382s6dh3kmp5eo1y8p0u5oh9c3t2ltduy0c7v64oi1waij7'
}

def clean_text(text):
    """Limpia el texto eliminando espacios extras y caracteres especiales"""
    if text is None:
        return ""
    text = re.sub(r'<span.*?</span>', '', text, flags=re.DOTALL)  # Elimina spans con estilos
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_property_details(url):
    """Extrae los detalles de una propiedad individual"""
    try:
        response = requests.get(url, headers=headers, cookies=cookies)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extraer título
        titulo = soup.find('h1', class_='tit-anuncio')
        titanuncio = clean_text(titulo.get_text()) if titulo else ""
        
        # Extraer precio
        precio = soup.find('h3', class_='user-price')
        userprice = precio.get_text().strip() if precio else ""
        
        # Extraer detalles
        detalles = {}
        grid_items = soup.find_all('div', class_='grid__item')
        for item in grid_items:
            span = item.find('span')
            if span:
                key = span.get_text().replace(':', '').strip()
                h6 = item.find('h6')
                value = h6.get_text().strip() if h6 else ""
                detalles[key] = value
        
        # Crear el objeto JSON
        property_data = {
            "titanuncio": titanuncio,
            "userprice": userprice,
            "Departamento": detalles.get("Departamento", ""),
            "Ciudad": detalles.get("Ciudad", ""),
            "NrodeAnuncio": detalles.get("Nro. de Anuncio", ""),
            "Zona": detalles.get("Zona", ""),
            "NrodeVisitas": detalles.get("Nro. de Visitas", ""),
            "Publicadoel": detalles.get("Publicado el", ""),
            "url": url
        }
        
        return property_data
    
    except Exception as e:
        print(f"Error al procesar {url}: {str(e)}")
        return None

def scrape_page(page_num):
    """Scrapea una página de resultados y devuelve los enlaces a propiedades"""
    base_url = f'https://clasipar.paraguay.com/inmuebles/terrenos/page{page_num}'
    try:
        response = requests.get(base_url, headers=headers, cookies=cookies)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        property_links = []
        anuncios = soup.find_all('div', class_='box-anuncio__descripcion')
        
        for anuncio in anuncios:
            link = anuncio.find('a', class_='titAnuncio')
            if link and 'href' in link.attrs:
                full_url = urljoin(base_url, link['href'])
                property_links.append(full_url)
        
        return property_links
    
    except Exception as e:
        print(f"Error al scrapear página {page_num}: {str(e)}")
        return []

def main():
    total_pages = 733
    for page_num in range(500, total_pages + 1):
        print(f"Procesando página {page_num} de {total_pages}")
        
        # Obtener enlaces de propiedades en esta página
        property_links = scrape_page(page_num)
        
        if not property_links:
            print(f"No se encontraron propiedades en la página {page_num}")
            continue
        
        # Procesar cada propiedad
        for link in property_links:
            try:
                # Extraer detalles de la propiedad
                property_data = extract_property_details(link)
                
                if property_data and property_data.get('NrodeAnuncio'):
                    # Guardar en MongoDB
                    try:
                        collection.update_one(
                            {'NrodeAnuncio': property_data['NrodeAnuncio']},
                            {'$set': property_data},
                            upsert=True
                        )
                        print(f"Guardado anuncio {property_data['NrodeAnuncio']}")
                    except Exception as e:
                        print(f"Error al guardar en MongoDB: {str(e)}")
                
                #time.sleep(1)  # Espera entre solicitudes a propiedades
                
            except Exception as e:
                print(f"Error al procesar propiedad {link}: {str(e)}")
        
        #time.sleep(3)  # Espera adicional después de cada página

if __name__ == "__main__":
    main()