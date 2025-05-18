import geopandas as gpd
import numpy as np
from shapely.geometry import LineString
from itertools import combinations

# === CARGA TU ARCHIVO ===
# Asegúrate de que el archivo 'nodos.geoJson' esté en el mismo directorio
gdf = gpd.read_file("nodos.geoJson")

# Convertir a CRS proyectado para que los cálculos de ángulos sean precisos (en metros)
gdf = gdf.to_crs(epsg=3857)

# === FUNCIONES ===
def calculate_angle(line):
    """Calcula el ángulo de la línea en grados, sin considerar el sentido."""
    x0, y0 = line.coords[0]
    x1, y1 = line.coords[-1]
    angle_rad = np.arctan2((y1 - y0), (x1 - x0))
    angle_deg = np.degrees(angle_rad) % 180  # solo dirección
    return angle_deg

# Calcular ángulos para todas las geometrías
gdf['angle'] = gdf['geometry'].apply(calculate_angle)

# === DETECCIÓN DE PARALELISMO ===
angle_tolerance = 5  # tolerancia en grados
parallel_pairs = []
parallel_indices = set()

for (i1, row1), (i2, row2) in combinations(gdf.iterrows(), 2):
    diff = abs(row1['angle'] - row2['angle'])
    if diff <= angle_tolerance or abs(diff - 180) <= angle_tolerance:
        parallel_pairs.append((row1.name, row2.name))
        parallel_indices.update([row1.name, row2.name])

# Marcar cuáles tienen al menos una línea paralela
gdf['has_parallel'] = gdf.index.isin(parallel_indices)

# === RESULTADOS ===
print("Líneas con paralelas detectadas:")
print(gdf[gdf['has_parallel']][['angle']])

print("\nLíneas sin paralelas:")
print(gdf[~gdf['has_parallel']][['angle']])

# Opcional: Guardar resultados
gdf.to_file("nodos_resultado.geojson", driver="GeoJSON")
print("\nSe ha guardado 'nodos_resultado.geojson' con la columna 'has_parallel'.")