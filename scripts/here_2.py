import math
import requests
import os
from PIL import Image, ImageDraw
from shapely.geometry import LineString

# === CONFIGURACIÓN GENERAL ===

coordenadas = [
    (-99.63067, 19.26921),
    (-99.63059, 19.26927),
    (-99.63054, 19.27009),
    (-99.63052, 19.27025),
    (-99.63043, 19.27081),
]

zoom = 16
tile_size = 512
tile_format = "png"
api_key = "<TU_API_KEY>"
folder = "tiles_output"

PERCFRREF = 0.5         # 50% sobre la línea
POI_ST_SD = "right"     # Lado del POI ("left" o "right")

# === FUNCIONES DE TILES ===

def lat_lon_to_tile(lat, lon, zoom):
    lat = max(min(lat, 85.05113), -85.05113)
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    n = 2.0 ** zoom
    x = int((lon_rad + math.pi) / (2 * math.pi) * n)
    y = int((1 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2 * n)
    return (x, y)

def tile_coords_to_lat_lon(x, y, zoom):
    n = 2.0 ** zoom
    lon_deg = x / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    lat_deg = math.degrees(lat_rad)
    return (lat_deg, lon_deg)

def latlon_to_pixel(lat, lon, zoom, x_min, y_min, tile_size):
    lat = max(min(lat, 85.05113), -85.05113)
    x_tile = (lon + 180.0) / 360.0 * 2 ** zoom
    lat_rad = math.radians(lat)
    y_tile = (1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * 2 ** zoom
    px = int((x_tile - x_min) * tile_size)
    py = int((y_tile - y_min) * tile_size)
    return (px, py)

def download_tile(x, y, zoom, tile_format, tile_size, api_key, folder):
    os.makedirs(folder, exist_ok=True)
    url = f'https://maps.hereapi.com/v3/base/mc/{zoom}/{x}/{y}/{tile_format}&style=satellite.day&size={tile_size}?apiKey={api_key}'
    response = requests.get(url)
    if response.status_code == 200:
        filename = os.path.join(folder, f"tile_z{zoom}_x{x}_y{y}.{tile_format}")
        with open(filename, 'wb') as f:
            f.write(response.content)
        return filename
    else:
        print(f"Failed to download tile z{zoom} x{x} y{y} — Status code: {response.status_code}")
        return None

# === OBTENER TILES NECESARIOS ===

x_values = []
y_values = []

for lon, lat in coordenadas:
    x, y = lat_lon_to_tile(lat, lon, zoom)
    x_values.append(x)
    y_values.append(y)

x_min, x_max = min(x_values), max(x_values)
y_min, y_max = min(y_values), max(y_values)

tiles = []
for x in range(x_min, x_max + 1):
    for y in range(y_min, y_max + 1):
        path = download_tile(x, y, zoom, tile_format, tile_size, api_key, folder)
        if path:
            tiles.append((x, y, path))

# === UNIR TILES EN MOSAICO ===

mosaic_width = (x_max - x_min + 1) * tile_size
mosaic_height = (y_max - y_min + 1) * tile_size
mosaic = Image.new('RGB', (mosaic_width, mosaic_height))

for x, y, path in tiles:
    tile_img = Image.open(path)
    offset_x = (x - x_min) * tile_size
    offset_y = (y - y_min) * tile_size
    mosaic.paste(tile_img, (offset_x, offset_y))

# === DIBUJAR PUNTOS Y LÍNEA ===

draw = ImageDraw.Draw(mosaic)
pixeles = []
for lon, lat in coordenadas:
    px, py = latlon_to_pixel(lat, lon, zoom, x_min, y_min, tile_size)
    pixeles.append((px, py))
    draw.ellipse((px - 5, py - 5, px + 5, py + 5), fill="red", outline="black")

draw.line(pixeles, fill="yellow", width=2)

# === CALCULAR Y DIBUJAR POI ===

line_geo = LineString(coordenadas)  # (lon, lat) para shapely (x, y)

# Punto base en línea
total_length = line_geo.length
poi_point_geo = line_geo.interpolate(PERCFRREF * total_length)

# Dirección local
p1 = line_geo.interpolate(PERCFRREF * total_length - 0.0001)
p2 = line_geo.interpolate(PERCFRREF * total_length + 0.0001)
dx = p2.x - p1.x
dy = p2.y - p1.y
norm = math.hypot(dx, dy)
nx = -dy / norm
ny = dx / norm

# Desplazamiento lateral
offset_mts = 10
offset_deg = offset_mts / 111320  # aproximación
side_factor = 1 if POI_ST_SD.lower() == "left" else -1

poi_lat = poi_point_geo.y + side_factor * ny * offset_deg
poi_lon = poi_point_geo.x + side_factor * nx * offset_deg

poi_px, poi_py = latlon_to_pixel(poi_lat, poi_lon, zoom, x_min, y_min, tile_size)

# Dibujar POI
draw.ellipse((poi_px - 6, poi_py - 6, poi_px + 6, poi_py + 6), fill="blue", outline="white")
draw.text((poi_px + 8, poi_py - 10), "POI", fill="white")

# === GUARDAR IMAGEN FINAL ===

mosaic.save("mosaico_con_poi.png")
print("✅ Imagen guardada como 'mosaico_con_poi.png'")