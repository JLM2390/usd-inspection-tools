import open3d as o3d
import shutil, os

# Descarga automática de la nube de ejemplo (sala de estar, con color)
dataset = o3d.data.PLYPointCloud()
print(f"Descargada en: {dataset.path}")

# Copiar a tu carpeta de trabajo con un nombre claro
destino = os.path.join("own_test_files", "livingroom.ply")
shutil.copy(dataset.path, destino)
print(f"Copiada a: {destino}")