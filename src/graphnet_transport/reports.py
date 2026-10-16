"""Scientific Spanish LaTeX reports with letter paper, mathematics and network diagrams.

All user text is escaped; the TikZ diagram uses indexed node identifiers rather than
user content as TeX control sequences.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import math
import re
import unicodedata

import numpy as np

from . import __author__, __version__

_ESCAPE = {
    "\\": r"\textbackslash{}", "{": r"\{", "}": r"\}", "#": r"\#", "$": r"\$",
    "%": r"\%", "&": r"\&", "_": r"\_", "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}", "ᵢ": r"\textsubscript{i}",
    "→": r"\ensuremath{\rightarrow}", "←": r"\ensuremath{\leftarrow}",
    "λ": r"\ensuremath{\lambda}", "π": r"\ensuremath{\pi}",
    "μ": r"\ensuremath{\mu}", "σ": r"\ensuremath{\sigma}",
    "Δ": r"\ensuremath{\Delta}", "α": r"\ensuremath{\alpha}",
    "β": r"\ensuremath{\beta}", "∞": r"\ensuremath{\infty}",
    "≥": r"\ensuremath{\geq}", "≤": r"\ensuremath{\leq}",
    "±": r"\ensuremath{\pm}", "×": r"\ensuremath{\times}",
    "–": "--", "—": "---", "•": r"\textbullet{}", "−": "$-$",
}


def escape_latex(value: object) -> str:
    return "".join(_ESCAPE.get(ch, ch if 32 <= ord(ch) <= 255 else "?") for ch in str(value))


def report_filename(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name)
    stem = re.sub(r"[^a-zA-Z0-9_-]+", "_", normalized.encode("ascii", "ignore").decode()).strip("._-")[:90]
    if not stem:
        raise ValueError("Introduzca un nombre con letras o números para el reporte.")
    return stem + ".tex"


def default_report_dir() -> Path:
    home = Path.home()
    user_dirs = home / ".config" / "user-dirs.dirs"
    if user_dirs.is_file():
        try:
            config = user_dirs.read_text(encoding="utf-8")
            m = re.search(r'^XDG_DOWNLOAD_DIR="([^"]+)"', config, flags=re.MULTILINE)
            if m:
                raw = m.group(1)
                if raw == "$HOME" or raw.startswith("$HOME/"):
                    target = home / raw.removeprefix("$HOME/") if raw != "$HOME" else home
                    if target.is_dir():
                        return target
        except OSError:
            pass
    for folder in ("Downloads", "Descargas"):
        if (home / folder).is_dir():
            return home / folder
    return home


def write_report(name: str, tex: str, directory: Path | None = None) -> Path:
    folder = Path(directory) if directory is not None else default_report_dir()
    folder.mkdir(parents=True, exist_ok=True)
    requested = Path(report_filename(name))
    for idx in range(1, 10001):
        target = folder / (requested.name if idx == 1 else f"{requested.stem}_{idx}.tex")
        try:
            with target.open("x", encoding="utf-8", newline="\n") as f:
                f.write(tex)
            return target
        except FileExistsError:
            continue
    raise FileExistsError("No se pudo generar un nombre único.")


def _matrix_table(matrix, row_labels=None, column_labels=None) -> str:
    a = np.asarray(matrix, dtype=object)
    if a.ndim != 2:
        raise ValueError("Los datos de entrada deben ser una matriz bidimensional.")
    nr, nc = min(a.shape[0], 30), min(a.shape[1], 16)
    rows = [str(x) for x in (row_labels if row_labels is not None else range(1, a.shape[0]+1))]
    cols = [str(x) for x in (column_labels if column_labels is not None else range(1, a.shape[1]+1))]
    out = [r"\begin{center}", r"\begin{adjustbox}{max width=\linewidth}", "\\begin{tabular}{l" + "r" * nc + "}", r"\toprule"]
    out.append(" & ".join(["Fila / columna"] + [escape_latex(x) for x in cols[:nc]]) + r" \\")
    out.append(r"\midrule")
    for i in range(nr):
        items = []
        for x in a[i, :nc]:
            try:
                v = float(x)
                string = format(v, ".9g") if np.isfinite(v) else "--"
            except (TypeError, ValueError):
                string = str(x)
            items.append(escape_latex(string))
        out.append(" & ".join([escape_latex(rows[i])] + items) + r" \\")
    out.extend([r"\bottomrule", r"\end{tabular}", r"\end{adjustbox}", r"\end{center}"])
    if a.shape[0] > nr or a.shape[1] > nc:
        out.append(r"\emph{Vista truncada en el reporte: " + f"{nr} de {a.shape[0]} filas y {nc} de {a.shape[1]} columnas" + r".}")
    return "\n".join(out)


def _result_block(value, level=0) -> str:
    if isinstance(value, dict):
        parts = []
        for key, entry in value.items():
            head = r"\subsection*" if level == 0 else r"\paragraph*"
            parts.extend((head + "{" + escape_latex(str(key).replace("_", " ")) + "}", _result_block(entry, level+1)))
        return "\n".join(parts) if parts else r"\emph{Sin resultados.}"
    if isinstance(value, (list, tuple)):
        if value and all(isinstance(x, (list, tuple)) for x in value):
            try:
                return _matrix_table(value)
            except (TypeError, ValueError):
                pass
        if not value:
            return r"\emph{Sin elementos.}"
        pieces = [r"\begin{itemize}"]
        pieces.extend(r"\item " + _result_block(x, level+1) for x in value[:60])
        if len(value) > 60:
            pieces.append(r"\item \emph{Lista truncada a 60 elementos.}")
        pieces.append(r"\end{itemize}")
        return "\n".join(pieces)
    if value is None:
        return r"\emph{No determinado.}"
    if isinstance(value, bool):
        return "Sí" if value else "No"
    if isinstance(value, float):
        if math.isnan(value):
            return r"\emph{No definido}"
        if math.isinf(value):
            return r"\ensuremath{\infty}"
        value = format(value, ".10g")
    return r"\noindent " + escape_latex(value) + r"\par"



def _compact_table(headers, rows):
    """A compact booktabs layout for report results (never one subsection per value)."""
    headers = list(headers)
    rows = list(rows)
    layout = 'l' + 'r' * (len(headers)-1)
    result = [r'\begin{center}', r'\small', r'\begin{adjustbox}{max width=\linewidth}',
              r'\begin{tabular}{' + layout + '}', r'\toprule',
              ' & '.join(escape_latex(v) for v in headers) + r' \\', r'\midrule']
    for row in rows:
        result.append(' & '.join(escape_latex(_format_scalar(v)) for v in row) + r' \\')
    result += [r'\bottomrule', r'\end{tabular}', r'\end{adjustbox}', r'\end{center}']
    return '\n'.join(result)


def _format_scalar(value):
    if isinstance(value, bool):
        return 'Sí' if value else 'No'
    if value is None:
        return 'No determinado'
    if isinstance(value, (float, np.floating)):
        return f'{value:.6g}' if math.isfinite(value) else 'No definido'
    return str(value)


def _metrics_report(result, params):
    directed = bool(result['dirigido'])
    n, m = result['nodos'], result['arcos']
    maximum = result.get('aristas_maximas', n*(n-1) if directed else n*(n-1)//2)
    formula = r'\frac{m}{n(n-1)}' if directed else r'\frac{2m}{n(n-1)}'
    actual = (fr'\frac{{{m}}}{{{n}({n}-1)}}' if directed else
              fr'\frac{{2\cdot{m}}}{{{n}({n}-1)}}')
    score = result['densidad']
    connected = result.get('conexa', result['componentes_fuertes'] == 1 if directed else result['componentes_debiles'] == 1)
    status = ('fuertemente conexa' if directed else 'conexa') if connected else ('no fuertemente conexa' if directed else 'no conexa')
    rows = ([('Nodos (n)', n), ('Arcos (m)', m), ('Arcos posibles', maximum),
             ('Componentes fuertes', result['componentes_fuertes']),
             ('Componentes débiles', result['componentes_debiles']),
             ('Densidad', f'{100*score:.2f}%')]
            if directed else
            [('Nodos (n)', n), ('Aristas (m)', m), ('Aristas posibles', maximum),
             ('Componentes conexas', result['componentes_debiles']),
             ('Densidad', f'{100*score:.2f}%')])
    lines = [r'\subsection{Resumen de la red}', _compact_table(['Indicador', 'Resultado'], rows),
             r'\subsection{Cálculo de la densidad}']
    if n < 2:
        lines.append('La densidad se informa como cero por convención para menos de dos vértices; '
                     'la fórmula usual tiene denominador nulo.')
    else:
        lines += ['Para una red '+('dirigida' if directed else 'no dirigida') +
                  ' simple y sin lazos se emplea la relación entre conexiones existentes y posibles.',
                  r'\begin{equation}',
                  r'D = ' + formula + r' = ' + actual + fr' \approx {score:.4f} = {100*score:.2f}\%',
                  r'\end{equation}']
    lines.append(r'\subsection{Indicadores por vértice}')
    degree = result['grado']
    nodes = list(degree)
    if directed:
        lines.append(_compact_table(['Nodo','Entrada', 'Salida', 'Total'],
                    [(node, result['grado_entrada'][node], result['grado_salida'][node], degree[node]) for node in nodes]))
    else:
        lines.append(_compact_table(['Nodo', 'Grado', 'Centralidad de grado'],
                    [(node, degree[node], result['centralidad_grado'][node]) for node in nodes]))
    lines += [r'\subsection{Interpretación de ingeniería}',
              f'La red es {status}. La densidad expresa la proporción de conexiones topológicas existentes; '
              'no representa capacidad de circulación, demanda, confiabilidad ni tiempo de viaje.']
    note = result.get('nota_densidad', '')
    if 'lazos' in note or 'paralelos' in note:
        lines.append(escape_latex(note))
    if nodes:
        winner = max(nodes, key=lambda x:degree[x])
        lines.append('El vértice con mayor grado es '+escape_latex(winner)+
                     ' ('+escape_latex(degree[winner])+' conexiones contadas según la convención del grafo).')
    return '\n'.join(lines)


def _count_report(result):
    simple = str(result['tipo']).startswith('Caminos simples')
    lines = [r'\subsection{Conteo de longitud exacta}',
             _compact_table(['Parámetro','Valor'], [('Origen', result['origen']),
                 ('Destino', result['destino']), ('Longitud (aristas)',result['longitud']),
                 ('Tipo', result['tipo']), ('Cantidad exacta',result['total'])]),
             r'\subsection{Interpretación}', escape_latex(result['interpretacion'])]
    if result.get('ruta_ejemplo'):
        lines += [r'\subsection{Un camino de ejemplo}',
                 r'\begin{center}\colorbox{graphlight}{\parbox{0.91\linewidth}{\centering ' +
                 r' $\rightarrow$ '.join(escape_latex(x) for x in result['ruta_ejemplo'])+
                 r'}}\end{center}',
                 'La trayectoria mostrada es solamente un ejemplo, no la enumeración completa.']
    if simple:
        lines.append('En caminos simples no se permite visitar un vértice más de una vez, '
                     'por lo que la potencia de la matriz de adyacencia no proporciona directamente este conteo.')
    else:
        lines.append('La potencia de la matriz de adyacencia permite obtener la cantidad de recorridos '
                     'entre el vértice de origen y el de destino con exactamente k aristas.')
    return '\n'.join(lines)


def _compact_generic(value):
    if not isinstance(value, dict):
        return _result_block(value)
    simple = [(key, v) for key, v in value.items() if not isinstance(v,(dict,list,tuple))]
    parts = [_compact_table(['Indicador','Resultado'], [(str(k).replace('_',' ').capitalize(),v) for k,v in simple])] if simple else []
    for key, v in value.items():
        if isinstance(v, dict) and all(not isinstance(x,(dict,list,tuple)) for x in v.values()):
            parts += [r'\subsection{'+escape_latex(str(key).replace('_',' '))+'}',
                      _compact_table(['Elemento','Valor'],v.items())]
        elif isinstance(v, (list,tuple)):
            parts.append(r'\subsection{'+escape_latex(str(key).replace('_',' '))+'}')
            if v and all(not isinstance(x,(dict,list,tuple)) for x in v):
                parts.append(_compact_table(['N.º','Valor'], [(i+1,x) for i,x in enumerate(v[:60])]))
            else:
                parts.append(_result_block(v))
        elif isinstance(v, dict):
            parts += [r'\subsection{'+escape_latex(str(key).replace('_',' '))+'}', _result_block(v)]
    return '\n'.join(parts)

# Notes include explicit assumptions so interpretation is not silently generalized.
_MATH = {
    "metrics": ("Grados y densidad de la red", r"D=\frac{m}{m_{\max}},\qquad k_i=\sum_j A_{ij} \quad \text{(red no dirigida)}.",
                "Para redes dirigidas se distinguen grados de entrada y salida. La conectividad topológica no mide capacidad de transporte."),
    "counting": ("Recorridos de longitud exacta", r"W_{ij}^{(k)}=(A^k)_{ij},\qquad W_{ij}^{(k+1)}=\sum_r W_{ir}^{(k)}A_{rj}.",
                 "La potencia de adyacencia cuenta recorridos, que pueden repetir nodos o aristas. Los caminos simples se cuentan separadamente."),
    "dijkstra": ("Ruta de costo mínimo", r"d(v)=\min_{(u,v)\in E}\left\{d(u)+c_{uv}\right\}.",
                 "Dijkstra utiliza costos no negativos. La ruta reportada minimiza la suma de pesos."),
    "bellman-ford": ("Relajación de arcos", r"d^{(k)}(v)=\min\left(d^{(k-1)}(v),\min_{(u,v)\in E}\{d^{(k-1)}(u)+c_{uv}\}\right).",
                      "Se admiten arcos de costo negativo, siempre que el problema no tenga ciclos negativos relevantes."),
    "floyd": ("Distancias de todos los pares", r"d_{ij}^{(k)}=\min\{d_{ij}^{(k-1)},\ d_{ik}^{(k-1)}+d_{kj}^{(k-1)}\}.",
              "La matriz presenta los costos mínimos entre cada par de nodos."),
    "euler": ("Recorridos eulerianos", r"\forall v\in V:\ \deg(v)\equiv 0\pmod 2\quad\text{(circuito no dirigido)}.",
              "Un recorrido euleriano utiliza cada arista una sola vez. Además de los grados se requiere conectividad; en redes dirigidas se comparan entradas y salidas."),
    "hamilton": ("Recorridos hamiltonianos", r"v_1\to v_2\to\cdots\to v_n\to v_1,\qquad |\{v_1,\ldots,v_n\}|=n.",
                 "Un ciclo hamiltoniano visita cada vértice exactamente una vez y retorna al origen. No existe un criterio general simple de grados que sea suficiente; la búsqueda es exacta dentro del límite indicado."),
    "kruskal": ("Árbol de expansión mínima", r"\min_{T\subseteq E}\ \sum_{e\in T}c_e,\quad T\text{ es un árbol generador}.",
                "Si la red no es conexa, el resultado representa un bosque de expansión mínima."),
    "prim": ("Árbol de expansión mínima", r"\min_{T\subseteq E}\ \sum_{e\in T}c_e,\quad T\text{ conecta los nodos}.",
             "El método selecciona aristas de costo mínimo que amplían el árbol; una red desconectada produce un bosque."),
    "flow": ("Conservación de flujo", r"\max\sum_{(s,v)\in E} f_{sv},\quad 0\leq f_{uv}\leq K_{uv},\quad \sum_u f_{uv}=\sum_w f_{vw}.",
             "Se respetan capacidades y conservación de flujo en nodos internos; el flujo máximo coincide con la capacidad del corte mínimo."),
    "wardrop": ("Equilibrio del usuario", r"t_i(x_i)=a_i+b_ix_i,\qquad x_i>0\Rightarrow t_i(x_i)=t^*.",
                "Modelo de rutas paralelas con demanda fija y tiempos afines no decrecientes."),
    "markov": ("Evolución de una cadena de Markov", r"\boldsymbol{\pi}^{(n)}=\boldsymbol{\pi}^{(0)}P^n,\qquad \boldsymbol{\pi}^*P=\boldsymbol{\pi}^*.",
               "Cada fila de P suma uno. Convergencia a distribución estacionaria única requiere condiciones adicionales, como irreducibilidad y aperiodicidad."),
    "absorption": ("Cadena absorbente", r"N=(I-Q)^{-1},\qquad \mathbf{t}=N\mathbf{1},\qquad B=NR.",
                   "Estas expresiones se aplican cuando los estados transitorios son absorbidos con probabilidad uno."),
    "intermodal_route": ("Costo generalizado", r"C(r)=\sum_{e\in r}c_e+\tau\,N_{\mathrm{transbordos}}(r).",
                         "Se añaden penalizaciones por cambios de modo para seleccionar la ruta."),
    "algebraic": ("Conectividad algebraica", r"L=D-A,\qquad \lambda_2(L)>0\iff G\text{ es conexo}.",
                  "Identidad válida para el Laplaciano combinatorio de redes no dirigidas con pesos no negativos."),
    "assignment": ("Asignación de costo mínimo", r"\min\sum_{i,j}c_{ij}x_{ij},\quad x_{ij}\in\{0,1\}.",
                   "Una fila y una columna pueden participar a lo sumo en una pareja del resultado."),
    "tsp": ("Problema del viajante", r"\min\sum_{(i,j)\in r}c_{ij},\qquad r\text{ visita todos los nodos}.",
            "El algoritmo disponible es heurístico: no garantiza optimalidad."),
}


def _math_section(algorithm, description):
    key = algorithm.lower()
    lookup = {
        "grado": "metrics", "conteo de caminos": "counting",
        "dijkstra": "dijkstra", "bellman": "bellman-ford", "floyd": "floyd",
        "euler": "euler", "hamilton": "hamilton", "kruskal": "kruskal", "prim": "prim",
        "flujo máximo": "flow", "wardrop": "wardrop", "valores propios": "markov",
        "estados absorbentes": "absorption", "transbordo": "intermodal_route",
        "conectividad algebraica": "algebraic", "asignación": "assignment", "viajante": "tsp"
    }
    which = next((v for k, v in lookup.items() if k in key), None)
    data = _MATH.get(which)
    if not data:
        return (r"\section{Fundamento del análisis}", escape_latex(description))
    title, expression, note = data
    return (r"\section{Fundamento matemático}", r"\textbf{"+escape_latex(title)+r".} " +escape_latex(description),
            r"\begin{equation}"+expression+r"\end{equation}", escape_latex(note))


def _edges_in_route(results):
    result = results if isinstance(results, dict) else {}
    route = result.get("ruta") or result.get("recorrido") or result.get("ruta_ejemplo") or []
    return [(str(u), str(v)) for u, v in zip(route, route[1:])] if isinstance(route, (tuple, list)) else []


def _diagram(matrix, *, labels=None, directed=True, route_edges=(), title="Red de entrada") -> str:
    """Embed weighted graph directly in a .tex file using TikZ; no external image."""
    a = np.asarray(matrix, dtype=float)
    if a.ndim != 2 or a.shape[0] != a.shape[1]:
        return ""  # Assignment / Wardrop are not adjacency matrices.
    n = len(a)
    if n > 16:
        return r"\emph{Diagrama omitido: más de 16 nodos; se conserva la matriz de entrada.}"
    labels = list(map(str, labels if labels is not None else range(1, n+1)))
    if len(labels) != n:
        return ""
    route_set = set(route_edges)
    if not directed:
        route_set |= {(v, u) for u, v in route_set}
    radius = 2.25 if n <= 6 else 2.9
    diagram = [r"\begin{figure}[H]", r"\centering", r"\begin{tikzpicture}[>=Stealth,scale=1, every node/.style={font=\small}]" ]
    for i, label in enumerate(labels):
        angle = 90-360*i/max(n,1)
        diagram.append(fr"\node[circle,draw=graphblue,fill=graphlight,thick,minimum size=9mm] (n{i}) at ({angle}:{radius}) {{{escape_latex(label)}}};")
    edges = []
    for i in range(n):
        for j in range(n):
            if not directed and j < i:
                continue
            weight = a[i,j]
            if i == j and (np.isnan(weight) or weight == 0):
                continue
            if not directed and np.isnan(weight):
                weight = a[j,i]
            if np.isfinite(weight):
                edges.append((i, j, float(weight)))
    # Keep the graph readable and compact; the matrix still documents all arcs.
    if len(edges) > 48:
        return r"\emph{Diagrama omitido: red densa con más de 48 arcos; consulte la matriz.}"
    for i, j, weight in edges:
        highlighted = (labels[i], labels[j]) in route_set
        color = "routegreen" if highlighted else "graphgray"
        arrow = "->" if directed else "-"
        dash = "line width=1.9pt" if highlighted else "line width=.8pt"
        loop = "loop above" if i == j else ""
        opposite = directed and i != j and np.isfinite(a[j,i])
        bend = "bend left=17" if opposite else ""
        ops = ",".join(x for x in (arrow, f"draw={color}", dash, bend, loop) if x)
        # Do not put a label on every edge in dense graphs.
        weight_label = (fr" node[pos=.48,fill=white,inner sep=1pt,font=\tiny] {{{escape_latex(f'{weight:.5g}')}}}" if len(edges) <= 24 else "")
        if loop:
            diagram.append(fr"\path[{ops}] (n{i}) edge{weight_label} (n{j});")
        else:
            diagram.append(fr"\draw[{ops}] (n{i}) to{weight_label} (n{j});")
    diagram.extend([r"\end{tikzpicture}", r"\caption{"+escape_latex(title)+(". Los arcos verdes representan el recorrido destacado." if route_set else ".")+r"}", r"\end{figure}"])
    return "\n".join(diagram)


def build_latex_report(*, name, category, algorithm, description, input_help, matrix, results,
                       parameters=None, row_labels=None, column_labels=None, generated_at=None, graph_matrix=None):
    if not str(name).strip():
        raise ValueError("El reporte necesita un nombre.")
    when = generated_at or datetime.now()
    params = parameters or {}
    directed = str(params.get("Red dirigida", "Sí")).strip().lower() not in ("no", "false")
    route_edges = _edges_in_route(results)
    doc = [
        r"\documentclass[11pt,letterpaper]{article}",
        r"\usepackage[T1]{fontenc}", r"\usepackage[utf8]{inputenc}", r"\usepackage[spanish]{babel}",
        r"\usepackage{amsmath,amssymb}", r"\usepackage{geometry,booktabs,graphicx,longtable,adjustbox}",
        r"\usepackage[dvipsnames]{xcolor}", r"\usepackage{tikz}", r"\usetikzlibrary{arrows.meta,babel}",
        r"\usepackage{fancyhdr,float}", r"\geometry{letterpaper,margin=2.15cm,headheight=15pt}",
        r"\definecolor{graphblue}{HTML}{234F77}", r"\definecolor{graphlight}{HTML}{E9F3FB}",
        r"\definecolor{graphgray}{HTML}{75899B}", r"\definecolor{routegreen}{HTML}{008A6B}",
        r"\definecolor{inkgray}{HTML}{475569}",
        r"\pagestyle{fancy}", r"\fancyhf{}", r"\fancyhead[L]{\small\color{graphblue}\bfseries GraphNet Transport}",
        r"\fancyhead[R]{\small\color{inkgray} Informe científico}",
        r"\fancyfoot[L]{\scriptsize Desarrollador: " + escape_latex(__author__) + r" \textbullet\ GPL-3.0-only}", r"\fancyfoot[R]{\thepage}",
        r"\setlength{\parskip}{0.25em}", r"\setlength{\parindent}{0pt}",
        r"\begin{document}",
        r"\begin{center}", r"{\color{graphblue}\rule{\linewidth}{1.7pt}}\\[.35em]",
        r"{\LARGE\color{graphblue}\bfseries GraphNet Transport}\\[.3em]",
        r"{\normalsize Informe técnico de análisis de redes}\\[.35em]",
        r"{\Large\bfseries " + escape_latex(name.strip()) + r"}\\[.3em]",
        r"{\small Versión " + escape_latex(__version__) + r"}\\[.2em]",
        escape_latex(when.strftime("%Y-%m-%d %H:%M")) + r"\\[.2em]",
        r"{\color{graphblue}\rule{\linewidth}{1.7pt}}",
        r"\end{center}",
        r"\section{Objeto del análisis}",
        r"\textbf{Categoría:} " + escape_latex(category) + r"\par",
        r"\textbf{Algoritmo:} " + escape_latex(algorithm) + r"\par",
        escape_latex(description) + r"\par",
        r"\textbf{Interpretación de los datos:} " + escape_latex(input_help),
        *_math_section(algorithm, description),
        r"\section{Datos y configuración}",
    ]
    if params:
        doc.append(_compact_table(["Parámetro", "Valor"], params.items()))
    else:
        doc.append("No se utilizaron parámetros adicionales.")
    doc += [r"\subsection{Matriz de entrada}", _matrix_table(matrix, row_labels, column_labels)]
    # For Markov matrices and rectangular formulations a graph diagram may be misleading.
    if category not in ("Cadenas de Markov", "Equilibrio de transporte", "Optimización combinatoria"):
        diagram = _diagram(graph_matrix if graph_matrix is not None else matrix,
                           labels=row_labels, directed=directed, route_edges=route_edges,
                           title="Red analizada y solución resaltada" if route_edges else "Grafo de entrada")
        if diagram:
            doc.extend([r"\subsection{Representación de la red}", diagram])
    if route_edges and not (isinstance(results, dict) and 'ruta_ejemplo' in results):
        doc.extend([r"\section{Recorrido identificado}",
                    r"\begin{center}\colorbox{graphlight}{\parbox{0.91\linewidth}{\centering\large\bfseries " +
                    r"\ $\rightarrow$\ ".join(escape_latex(x) for x in (results.get("ruta") or results.get("recorrido"))) +
                    r"}}\end{center}"])
    if isinstance(results, dict) and 'densidad' in results and 'grado' in results:
        computed = _metrics_report(results, params)
    elif isinstance(results, dict) and 'longitud' in results and 'total' in results:
        computed = _count_report(results)
    else:
        computed = _compact_generic(results)
    scope = ("Este informe documenta un conteo exacto para el origen, destino y longitud indicados."
             if isinstance(results, dict) and 'longitud' in results and 'total' in results else
             "Los indicadores de conectividad representan la estructura topológica de la matriz y no expresan capacidad vial."
             if isinstance(results, dict) and 'densidad' in results and 'grado' in results else
             "Los resultados corresponden a los datos suministrados y las hipótesis del algoritmo.")
    special_result = isinstance(results, dict) and (('densidad' in results and 'grado' in results)
                   or ('longitud' in results and 'total' in results))
    doc += [r"\section{Resultados numéricos}", computed]
    if not special_result:
        doc += [r"\section{Interpretación y alcance}", scope]
    doc += [r"\end{document}"]
    return "\n".join(doc) + "\n"
