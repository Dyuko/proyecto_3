import requests
import time
import copy
from pymongo import MongoClient
from pymongo.errors import BulkWriteError
from pymongo.server_api import ServerApi

# Configuración de MongoDB
uri = "mongodb+srv://ucom:x5QQCZj.LENr2mF@cluster0.xmqhzxd.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(uri, server_api=ServerApi('1'))
db = client['infocasas']
collection = db['properties']
collection.create_index([('id', 1)], unique=True)  # Índice único para evitar duplicados

# Headers replicados de la solicitud original
headers = {
    'accept': '*/*',
    'accept-language': 'en-US,en;q=0.9,es-ES;q=0.8,es;q=0.7',
    'cache-control': 'no-cache',
    'content-type': 'application/json',
    'ic-user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
    'origin': 'https://www.infocasas.com.py',
    'pragma': 'no-cache',
    'priority': 'u=1, i',
    'referer': 'https://www.infocasas.com.py/venta/terrenos',
    'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'cross-site',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
    'x-cookiepot': '3',
    'x-origin': 'www.infocasas.com.py',
    'Cookie': 'cookiepot=3'
}

# Payload base modificado para 25 elementos por página
base_payload = [
    {
        "operationName": "ResultsGird_v2",
        "variables": {
            "rows": 25,
            "params": {
                "page": 1,
                "order": 2,
                "bedroomsExactMode": False,
                "bathroomsExactMode": False,
                "operation_type_id": 1,
                "property_type_id": [3],
                "season": None,
                "dateFrom": None,
                "dateTo": None,
                "currencyID": 1,
                "m2Currency": 1,
                "rooms": None,
                "floors": None,
                "dispositionID": None,
                "bedrooms": None,
                "bathrooms": None,
                "constStatesID": None,
                "facilitiesGroup": None,
                "projects": None,
                "minPrice": None,
                "maxPrice": None,
                "commonExpenses": None
            },
            "page": 1,
            "source": 0
        },
        "query": "query ResultsGird_v2($rows: Int!, $params: SearchParamsInput!, $page: Int, $source: Int) {\n  searchFast(params: $params, first: $rows, page: $page, source: $source)\n}\n"
    },
    {
        "operationName": "searchUrl",
        "variables": {
            "params": {
                "page": 1,
                "order": 2,
                "bedroomsExactMode": False,
                "bathroomsExactMode": False,
                "operation_type_id": 1,
                "property_type_id": [3],
                "season": None,
                "dateFrom": None,
                "dateTo": None,
                "currencyID": 1,
                "m2Currency": 1,
                "rooms": None,
                "floors": None,
                "dispositionID": None,
                "bedrooms": None,
                "bathrooms": None,
                "constStatesID": None,
                "facilitiesGroup": None,
                "projects": None,
                "minPrice": None,
                "maxPrice": None,
                "commonExpenses": None
            }
        },
        "query": "query searchUrl($params: SearchParamsInput!) {\n  searchUrl(params: $params) {\n    url\n    __typename\n  }\n}\n"
    }
]

url = 'https://graph.infocasas.com.uy/graphql'
current_page = 1

while True:
    try:
        # Clonar y modificar el payload para la página actual
        modified_payload = copy.deepcopy(base_payload)
        modified_payload[0]['variables']['page'] = current_page
        modified_payload[0]['variables']['params']['page'] = current_page

        # Realizar la solicitud POST
        response = requests.post(url, headers=headers, json=modified_payload)
        response.raise_for_status()

        # Procesar la respuesta
        data = response.json()
        search_data = data[0]['data']['searchFast']
        properties = search_data['data']
        paginator_info = search_data['paginatorInfo']

        # Insertar en MongoDB
        if properties:
            try:
                result = collection.insert_many(properties, ordered=False)
                print(f'Página {current_page}: Insertados {len(result.inserted_ids)} propiedades')
            except BulkWriteError as e:
                print(f'Página {current_page}: {len(e.details["writeErrors"])} duplicados omitidos')

        # Verificar si hay más páginas
        if not paginator_info.get('hasMorePages', False):
            print("No hay más páginas disponibles")
            break

        current_page += 1
        time.sleep(3)  # Espera entre solicitudes

    except requests.exceptions.HTTPError as e:
        print(f'Error HTTP en página {current_page}: {str(e)}')
        break
    except Exception as e:
        print(f'Error general en página {current_page}: {str(e)}')
        break

print("Proceso completado")