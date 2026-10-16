# GraphNet Transport — versión 2.0.0

**Graph Theory & Network Optimization** · Software libre · GNU GPL v3.0

**Desarrollador:** Héctor Alonso Benítez García  
**Repositorio:** https://github.com/VanLinux/GraphNet-Transport

Aplicación científica de escritorio, desarrollada íntegramente en Python, para teoría de grafos, optimización de redes, transporte intermodal y cadenas de Markov. Su motor matemático puede utilizarse independientemente de la interfaz PySide6.

## Instalación

Requiere **Python 3.10+** y un entorno gráfico (Fedora, Ubuntu, Windows o macOS).

```bash
git clone https://github.com/VanLinux/GraphNet-Transport.git
cd GraphNet-Transport
python3 -m venv .venv
source .venv/bin/activate    # En Windows/PowerShell: .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
graphnet
```

Para obtener los últimos cambios desde una copia existente:

```bash
cd ~/GraphNet-Transport
git pull --ff-only
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m pytest -q
graphnet
```

También puede iniciarse mediante `python -m graphnet_transport`.

## Novedades de la versión 2.0.0

La interfaz ahora tiene **dos selectores jerárquicos**: primero el **tipo de cálculo** y luego el **algoritmo**. Se muestran instrucciones breves sobre los datos necesarios y únicamente los campos de parámetros relevantes para cada operación. El editor adopta una matriz diferente según la modalidad (red, costos de asignación, rutas paralelas o probabilidades de transición) y **recuerda los datos de cada modalidad** al cambiar de grupo.

**Categorías disponibles:**

1. **Estructura y matrices**: grados, densidad, conectividad, matrices de adyacencia/Laplaciana y conectividad algebraica.
2. **Caminos mínimos**: Dijkstra, Bellman-Ford y Floyd-Warshall.
3. **Árboles de expansión**: Kruskal y Prim.
4. **Flujos y cortes**: flujo máximo y corte mínimo.
5. **Optimización combinatoria**: TSP aproximado y asignación óptima de una matriz de costos rectangular.
6. **Equilibrio de transporte**: Wardrop para rutas paralelas de tiempos afines no decrecientes.
7. **Redes intermodales**: resumen modal y ruta con penalización por transbordo.
8. **Cadenas de Markov**: análisis espectral/evolución y estados absorbentes.

### Formatos de entrada

- **Redes**: matriz cuadrada de arcos ponderados. Vacío = sin arco. Un cero fuera de la diagonal representa un arco real de costo cero. Para red no dirigida, introduzca una matriz simétrica.
- **Asignación**: matriz rectangular **agentes × tareas**, con todos los costos numéricos. Elija las dimensiones en el panel izquierdo.
- **Wardrop**: matriz de **2 filas × número de rutas**. Fila 1: tiempos libres `a_i`; fila 2: pendientes `b_i`; introduzca la demanda total en su campo. Modelo `t_i(x_i)=a_i+b_i x_i`.
- **Markov**: matriz cuadrada de probabilidades, todas entre 0 y 1 y con suma por fila igual a 1.
- **Intermodalidad**: se recomienda GraphML con atributos `weight`, `mode` y `transfer`. Un CSV no contiene atributos de modo.

Es posible pegar datos desde Excel/LibreOffice con **Ctrl+V**, redimensionar matrices y abrir/guardar archivos CSV; para redes también se dispone de GraphML. Los archivos GraphML deben proceder de fuentes confiables.

## Reportes LaTeX por algoritmo

Después de pulsar **«Ejecutar cálculo»**, se habilita **«Descargar reporte LaTeX (.tex)»** para cualquier algoritmo implementado. El programa **solo solicita el nombre del reporte**. A continuación genera automáticamente el archivo `.tex` en la carpeta **Descargas** (`~/Downloads`) o, si no existe, en la carpeta personal del usuario.

El reporte incluye:

- Título personalizado, nombre del cálculo y versión **2.0.0**.
- Categoría, algoritmo, instrucciones de entrada y parámetros utilizados.
- Matriz usada para el cálculo, con etiquetas de filas/columnas.
- Resultados reales calculados, sin sustituirlos por datos de ejemplo.
- Crédito discreto al desarrollador y referencia GPL v3.0.

Se puede compilar con **pdfLaTeX** y los paquetes comunes `babel` (español), `geometry`, `graphicx`, `booktabs` y `longtable`. Si ya existe un reporte con ese nombre, se añade un sufijo numérico para **no sobrescribirlo**. Para matrices con más de 30 filas o 16 columnas, la tabla de entrada del reporte se trunca de forma explícita para conservar legibilidad. La salida JSON sigue disponible por separado.

## Ejemplos

- `examples/red_rutas.csv`: Dijkstra de 1 a 4, costo mínimo esperado: 5.
- `examples/markov.csv`: espectro, distribución y evolución de una cadena de tres estados.
- `examples/red_intermodal.graphml`: ruta de A a C, penalización por transbordo 1, costo generalizado esperado: 5.

## Pruebas

```bash
python -m pytest -q
```

Los tests del motor y de reportes no requieren interfaz gráfica; `tests/test_gui.py` necesita PySide6 y ejecuta pruebas con el sistema Qt *offscreen*. La integración continua verifica ambos en Linux. También se ha probado la compilación de un reporte representativo con pdfLaTeX. La comprobación de ejecución real en Fedora y otros escritorios debe efectuarse sobre cada plataforma.

## Alcance

Se mantienen las restricciones de la versión anterior: TSP es heurístico, Wardrop resuelve rutas paralelas (no redes generales), los archivos CSV carecen de información modal, y una matriz no conserva todas las propiedades de un multigrafo importado de GraphML. Los modelos completos VRP/CVRP y los modelos de asignación para redes generales permanecen fuera de esta entrega; no aparecen como algoritmos terminados.

## Licencia y autoría

Copyright © 2026 Héctor Alonso Benítez García. Código fuente bajo **GNU GPL v3.0** (`GPL-3.0-only`). Consulte `LICENSE` y `AUTHORS.md`.
