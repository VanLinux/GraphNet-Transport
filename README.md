# GraphNet Transport — versión 1.0.0

**Graph Theory & Network Optimization** · Software libre · GNU GPL v3.0

**Desarrollador:** Héctor Alonso Benítez García  
**Repositorio:** https://github.com/VanLinux/GraphNet-Transport

Aplicación de escritorio en Python para analizar matrices de redes y cadenas de Markov. El motor científico se puede utilizar también desde Python, independientemente de la interfaz PySide6.

## Instalación (Fedora, Ubuntu, Windows y macOS)

Requiere **Python 3.10+** y un entorno de escritorio. En Fedora, si falta Qt, instale antes los componentes de escritorio pertinentes.

```bash
git clone https://github.com/VanLinux/GraphNet-Transport.git
cd GraphNet-Transport
python -m venv .venv
source .venv/bin/activate  # En PowerShell: .venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
graphnet
```

Alternativamente: `python -m graphnet_transport`. Para realizar pruebas: `python -m pytest -q`.

## Funcionalidades de v1.0.0

- Editor matricial, apertura y guardado de matrices numéricas CSV y redes GraphML.
- Grados, conectividad débil/fuerte, densidad, centralidades, puntos de articulación, puentes, matrices de adyacencia, grados, Laplaciana y alcanzabilidad.
- Conectividad algebraica para redes no dirigidas.
- Dijkstra, Bellman-Ford, Floyd-Warshall, Prim, Kruskal; flujo máximo y corte mínimo.
- Asignación óptima, ciclo del viajante aproximado, equilibrio de Wardrop en rutas paralelas con costos afines no decrecientes.
- Resumen de arcos por modo y enlaces de transbordo etiquetados en GraphML; ruta intermodal óptima con penalización constante de cambio de modo.
- Cadenas de Markov: validación, espectro propio, evolución P^n, distribuciones estacionarias de clases cerradas, irreducibilidad, aperiodicidad y análisis de absorción.
- Exportación JSON de resultados. Créditos visibles en barra de estado y ventana «Acerca de».

## Cómo ingresar una matriz

Las celdas vacías indican ausencia de arco. Un cero fuera de la diagonal representa un arco real de costo cero. Los ceros diagonales se consideran marcadores sin bucle. CSV utiliza números sin encabezados y columnas vacías para arcos ausentes. Para Markov complete todas las posiciones, incluidas las diagonales, y asegúrese de que cada fila sume uno. Para grafos no dirigidos marque la casilla correspondiente y use matriz simétrica. El formato GraphML puede conservar atributos `weight`, `capacity`, `mode` y `transfer` mientras no edite la matriz importada.

Para **Wardrop**, la primera fila de la matriz contiene tiempos libres `a_i` de cada ruta; en «Pendientes» introduzca `b_i`, separados por comas, y en «Demanda» el volumen total. Se resuelve únicamente el caso de rutas paralelas y costos `t_i = a_i + b_i x_i` con `a_i,b_i >= 0`.

## Alcance y limitaciones documentadas

Esta edición implementa las operaciones que aparecen en el selector de la interfaz. No se presentan como terminados modelos completos VRP/CVRP, optimización intermodal dependiente de horarios, ni asignación de tráfico sobre redes generales. El resumen intermodal necesita atributos adecuados en GraphML; un CSV matricial no contiene información modal. El cálculo TSP es heurístico y no promete optimalidad. Para la matriz de un multigrafo, la representación tabular solo conserva el menor peso de los arcos paralelos, aunque los atributos originales permanecen disponibles hasta editarla.

**Seguridad:** importe solamente GraphML de procedencia confiable; es un formato XML y la importación utiliza el lector de NetworkX. Evite archivos de origen desconocido.

## Validación

Los tests comprueban algoritmos sobre ejemplos numéricos conocidos y validación de errores. La interfaz necesita PySide6 y una sesión gráfica; ejecutar los tests del motor no constituye una prueba de empaquetado en cada sistema operativo.

## Licencia y autoría

Copyright © 2026 Héctor Alonso Benítez García. El código se publica bajo **GNU GPL v3.0** (`GPL-3.0-only`). Se admiten contribuciones conservando los avisos aplicables y respetando las licencias de las dependencias.
