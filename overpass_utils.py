import requests

def get_bounding_box(ciudad):
    """
    Retorna un bounding box (lat_min, lon_min, lat_max, lon_max)
    específico para cada ciudad en República Dominicana.
    """
    bounding_boxes = {
        "Santo Domingo": (18.40, -70.05, 18.55, -69.75),
        "Santiago": (19.40, -70.80, 19.55, -70.60),
        "La Romana": (18.40, -68.98, 18.50, -68.85),
        "San Pedro": (18.42, -69.40, 18.50, -69.25),
        "La Vega": (19.20, -70.60, 19.30, -70.40),
        "San Francisco de Macorís": (19.25, -70.30, 19.35, -70.20),
        "Puerto Plata": (19.70, -70.75, 19.80, -70.60)
    }

    return bounding_boxes.get(ciudad, None)

def obtener_negocios(categoria, ciudad):
    bbox = get_bounding_box(ciudad)
    if not bbox:
        raise ValueError(f"No hay bounding box definido para la ciudad: {ciudad}")

    lat_min, lon_min, lat_max, lon_max = bbox

    query = f"""
    [out:json][timeout:25];
    (
      node["amenity"="{categoria}"]({lat_min},{lon_min},{lat_max},{lon_max});
      way["amenity"="{categoria}"]({lat_min},{lon_min},{lat_max},{lon_max});
      relation["amenity"="{categoria}"]({lat_min},{lon_min},{lat_max},{lon_max});
    );
    out center;
    """

    url = "http://overpass-api.de/api/interpreter"
    response = requests.post(url, data=query)
    response.raise_for_status()

    return response.json()


def extraer_coordenadas(elementos):
    negocios = []

    for el in elementos:
        tags = el.get("tags", {})
        lat = el.get("lat")
        lon = el.get("lon")

        if lat and lon:
            nombre = tags.get("name", "Sin nombre")
            ciudad = el.get("ciudad", "Desconocido")

            negocios.append({
                "nombre": nombre,
                "lat": lat,
                "lon": lon,
                "ciudad": ciudad
            })
    return negocios
