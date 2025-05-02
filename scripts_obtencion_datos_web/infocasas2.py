import requests
import time
from pymongo import MongoClient
from pymongo.errors import BulkWriteError
from pymongo.server_api import ServerApi

# Configuración de MongoDB
uri = "mongodb+srv://ucom:x5QQCZj.LENr2mF@cluster0.xmqhzxd.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(uri, server_api=ServerApi('1'))
db = client['infocasas']
collection = db['properties_terrenos']  # Nueva colección
collection.create_index([('id', 1)], unique=True)  # Índice único para evitar duplicados

# Headers según el curl proporcionado
headers = {
    'Accept-Encoding': 'gzip, deflate, br',
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'Connection': 'keep-alive',
    'DNT': '1',
    'Origin': 'file://',
    'accept': '*/*',
    'accept-language': 'es-ES,es;q=0.9',
    'content-type': 'application/json',
    'x-origin': 'www.infocasas.com.py',
    'Referer': 'https://www.infocasas.com.py/',
    'ic-user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...'
}

# Query base para obtener 25 elementos por página
query_template = """
query {
  oldSearchListing(
    params: {
      page: %d
      order: 2
      bedroomsExactMode: false
      bathroomsExactMode: false
      operation_type_id: 1
      property_type_id: [3]
      season: null
      dateFrom: null
      dateTo: null
      currencyID: 1
      m2Currency: 1
      rooms: null
      floors: null
      dispositionID: null
      bedrooms: null
      bathrooms: null
      constStatesID: null
      facilitiesGroup: null
      projects: null
      minPrice: null
      maxPrice: null
      commonExpenses: null
    }
    first: 25
    page: %d
  ) {
    data {
      id
      title
      typeID
      address
      showAddress
      country_id
      description
      code
      code2
      finances
      imgSize
      barter
      m2
      created_at
      updated_at
      latitude
      source
      img
      color
      longitude
      pausd
      pointType
      zoom
      highlight
      active
      deleted
      leadsCount
      relevance
      construction_year
      notes
      sold
      soldDate
      discount
      draft
      sign
      guarantee
      facilitiesNotApply
      ceCurrencyID
      m2Terrain
      m2Built
      m2Terrace
      garage
      office
      dispositionID
      bathrooms
      bedrooms
      rooms
      seaDistanceID
      seaDistanceName
      seaview
      livingPlace
      condominium
      frontLength
      floorsCount
      m2apto
      apartmentsPerFloor
      floor
      neighborhood_id
      estate_id
      farmhouse
      allowedHeight
      hectares
      guests
      highlightDate
      price {
        amount
        currency {
          id
          name
          rate
        }
        hidePrice
      }
      isExternal
      link
      price_variation {
        difference
        percentage
        amount
        currency {
          id
          name
          rate
        }
        date
      }
      temporal_price
      temporal_currency{
        id
        name
        rate
      }
      estate{
        id
        country_id
        name
        order
      }
      property_type{
        id
        name
        plural
        show_in_home
        show_in_register
        order
      }
      operation_type{
        id
        name
        show_in_home
        show_in_register
        order
      }
      neighborhood{
        id
        name
        order
        lat
        long
        estate{
          id
          country_id
          name
          order
        }
      }
      country{
        id
        name
      }
      price_amount_usd
      isFavorite
      image_count
    }
    paginatorInfo {
      count
      currentPage
      firstItem
      hasMorePages
      lastItem
      lastPage
      perPage
      total
    }
  }
}
"""

url = 'https://graph.infocasas.com.uy/graphql'
current_page = 1
total_properties = 0

print("Iniciando extracción de datos...")

while True:
    try:
        # Crear el query para la página actual
        query = query_template % (current_page, current_page)
        payload = {"query": query}
        
        print(f"Solicitando página {current_page}...")
        
        # Realizar la solicitud POST
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        # Procesar la respuesta
        data = response.json()
        search_data = data['data']['oldSearchListing']
        properties = search_data['data']
        paginator_info = search_data['paginatorInfo']
        
        # Información de la página actual
        print(f"Página {current_page}/{paginator_info['lastPage']}: Obtenidos {len(properties)} propiedades")
        
        # Insertar en MongoDB
        if properties:
            try:
                result = collection.insert_many(properties, ordered=False)
                inserted_count = len(result.inserted_ids)
                total_properties += inserted_count
                print(f"Insertados {inserted_count} propiedades")
            except BulkWriteError as e:
                # Contar documentos insertados vs duplicados
                inserted_count = len(properties) - len(e.details["writeErrors"])
                total_properties += inserted_count
                print(f"Insertados {inserted_count} propiedades, {len(e.details['writeErrors'])} duplicados omitidos")
        
        # Verificar si hay más páginas
        if not paginator_info.get('hasMorePages', False):
            print("No hay más páginas disponibles")
            break
        
        current_page += 1
        
        # Esperar 2 segundos entre solicitudes
        print("Esperando 2 segundos...")
        time.sleep(2)
        
    except requests.exceptions.HTTPError as e:
        print(f'Error HTTP en página {current_page}: {str(e)}')
        print(f'Respuesta: {response.text}')
        break
    except Exception as e:
        print(f'Error general en página {current_page}: {str(e)}')
        break

print(f"Proceso completado. Total de propiedades insertadas: {total_properties}")