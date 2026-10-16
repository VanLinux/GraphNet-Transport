"""Testable numerical engine independent of the desktop GUI.

Matrix convention: NaN / empty = missing arc; off-diagonal zero is a real
zero-weight arc. Diagonal zero is treated as an identity placeholder (no loop).
For multigraphs, GraphML import preserves parallel edges; matrix views select
minimum-weight parallel arcs, and thus are explicitly lossy.
"""
from __future__ import annotations

import csv
from pathlib import Path
import math
import numpy as np
import networkx as nx
from scipy.optimize import brentq, linear_sum_assignment


def check_matrix(matrix):
    a = np.asarray(matrix, dtype=float)
    if a.ndim != 2 or a.shape[0] != a.shape[1] or a.shape[0] == 0:
        raise ValueError("Se requiere una matriz cuadrada no vacía.")
    if np.any(np.isinf(a)):
        raise ValueError("Utilice celdas vacías o NaN para arcos ausentes, no infinito.")
    return a


def matrix_to_graph(matrix, directed=True, labels=None):
    a = check_matrix(matrix)
    n = len(a)
    labels = [str(x) for x in (labels if labels is not None else range(1, n + 1))]
    if len(labels) != n or len(set(labels)) != n:
        raise ValueError("Las etiquetas de nodos deben ser únicas y corresponder a la matriz.")
    G = nx.DiGraph() if directed else nx.Graph()
    G.add_nodes_from(labels)
    for i in range(n):
        for j in range(n):
            if not directed and j < i:
                continue
            value = a[i, j]
            if i == j and (np.isnan(value) or value == 0):
                continue
            if not directed and i != j:
                other = a[j, i]
                if np.isfinite(value) and np.isfinite(other) and not np.isclose(value, other):
                    raise ValueError("La matriz de un grafo no dirigido debe ser simétrica.")
                if np.isnan(value):
                    value = other
            if np.isfinite(value):
                G.add_edge(labels[i], labels[j], weight=float(value))
    return G


def graph_to_matrix(G, attribute="weight"):
    nodes = list(G.nodes)
    a = np.full((len(nodes), len(nodes)), np.nan)
    np.fill_diagonal(a, 0)
    index = {name: pos for pos, name in enumerate(nodes)}
    for u, v, data in G.edges(data=True):
        raw = data.get(attribute, data.get("weight", 1))
        try:
            val = float(raw)
        except (ValueError, TypeError):
            raise ValueError(f"Peso no numérico en arco {u!r} → {v!r}.") from None
        if not math.isfinite(val):
            raise ValueError("Los pesos deben ser finitos.")
        i, j = index[u], index[v]
        a[i, j] = min(a[i, j], val) if np.isfinite(a[i, j]) and i != j else val
        if not G.is_directed():
            a[j, i] = a[i, j]
    return a, [str(x) for x in nodes]


def load_csv(path):
    """Numeric square adjacency matrix: empty cells mean absent arcs."""
    with open(path, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.reader(fh))
    rows = [r for r in rows if any(x.strip() for x in r)]
    try:
        matrix = [[float(x) if x.strip() else np.nan for x in row] for row in rows]
        return check_matrix(matrix)
    except (ValueError, TypeError) as exc:
        raise ValueError("CSV inválido. Use matriz cuadrada numérica sin encabezados.") from exc


def save_csv(path, matrix):
    a = check_matrix(matrix)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        for row in a:
            writer.writerow([format(x, ".12g") if np.isfinite(x) else "" for x in row])


def load_graphml(path):
    """Use only trusted local GraphML: XML may be unsafe when untrusted."""
    return nx.read_graphml(path)


def save_graphml(path, G):
    nx.write_graphml(G, path)


def network_metrics(G):
    if G.number_of_nodes() == 0:
        raise ValueError("La red no tiene nodos.")
    H = nx.Graph(G)
    result = {
        "nodos": G.number_of_nodes(), "arcos": G.number_of_edges(),
        "dirigido": G.is_directed(), "densidad": nx.density(G),
        "componentes_debiles": nx.number_weakly_connected_components(G) if G.is_directed() else nx.number_connected_components(G),
        "grado": dict(G.degree()),
        "grado_entrada": dict(G.in_degree()) if G.is_directed() else dict(G.degree()),
        "grado_salida": dict(G.out_degree()) if G.is_directed() else dict(G.degree()),
        "intermediacion": nx.betweenness_centrality(G, weight=None),
        "centralidad_grado": nx.degree_centrality(G),
        "componentes_fuertes": nx.number_strongly_connected_components(G) if G.is_directed() else nx.number_connected_components(G),
        "puntos_articulacion": list(nx.articulation_points(H)),
        "puentes": list(nx.bridges(H)),
    }
    return result


def graph_matrices(G):
    nodes = list(G.nodes)
    A = nx.to_numpy_array(G, nodelist=nodes, weight=None, dtype=float)
    D = np.diag(A.sum(axis=1))
    return {"adyacencia": A, "grados": D, "laplaciana": D-A,
            "alcanzabilidad": (nx.to_numpy_array(nx.transitive_closure(G), nodelist=nodes, weight=None) > 0).astype(int)}


def algebraic_connectivity(G):
    if G.is_directed():
        raise ValueError("Conectividad algebraica requiere una red no dirigida.")
    if G.number_of_nodes() < 2:
        return 0.0
    A = nx.to_numpy_array(G, weight=None)
    L = np.diag(A.sum(axis=1)) - A
    return float(np.linalg.eigvalsh(L)[1])


def shortest_path(G, source, target, algorithm="dijkstra"):
    for node in (source, target):
        if node not in G:
            raise ValueError(f"Nodo desconocido: {node}")
    if algorithm == "dijkstra":
        if any(float(d.get("weight", 1)) < 0 for _, _, d in G.edges(data=True)):
            raise ValueError("Dijkstra no acepta pesos negativos; use Bellman-Ford.")
        path = nx.dijkstra_path(G, source, target, weight="weight")
        cost = nx.dijkstra_path_length(G, source, target, weight="weight")
    elif algorithm == "bellman-ford":
        path = nx.bellman_ford_path(G, source, target, weight="weight")
        cost = nx.bellman_ford_path_length(G, source, target, weight="weight")
    else:
        raise ValueError("Algoritmo de camino mínimo desconocido.")
    return {"ruta": path, "costo": float(cost)}


def all_pairs(G):
    return dict(nx.floyd_warshall(G, weight="weight"))


def spanning_tree(G, algorithm="kruskal"):
    if G.is_directed():
        raise ValueError("El árbol de expansión mínima requiere red no dirigida.")
    T = nx.minimum_spanning_tree(G, weight="weight", algorithm=algorithm)
    return {"aristas": [(u, v, d.get("weight", 1)) for u, v, d in T.edges(data=True)],
            "costo": sum(float(d.get("weight", 1)) for _, _, d in T.edges(data=True)),
            "componentes": nx.number_connected_components(T)}


def maximum_flow(G, source, sink):
    if source not in G or sink not in G or source == sink:
        raise ValueError("Seleccione fuente y sumidero diferentes y existentes.")
    H = nx.DiGraph()
    H.add_nodes_from(G)
    for u, v, d in G.edges(data=True):
        capacity = float(d.get("capacity", d.get("weight", 1)))
        if capacity < 0 or not math.isfinite(capacity):
            raise ValueError("Las capacidades deben ser finitas y no negativas.")
        if H.has_edge(u, v):
            H[u][v]["capacity"] += capacity
        else:
            H.add_edge(u, v, capacity=capacity)
    value, flow = nx.maximum_flow(H, source, sink, capacity="capacity")
    cut, partition = nx.minimum_cut(H, source, sink, capacity="capacity")
    return {"flujo_maximo": value, "flujo_por_arco": flow,
            "corte_minimo": cut, "particion": [list(x) for x in partition]}


def assignment(cost_matrix):
    a = np.asarray(cost_matrix, dtype=float)
    if a.ndim != 2 or a.size == 0 or np.any(np.isnan(a)):
        raise ValueError("La asignación requiere una matriz rectangular sin celdas vacías.")
    i, j = linear_sum_assignment(a)
    return {"asignaciones": [(int(x + 1), int(y + 1)) for x, y in zip(i, j)], "costo": float(a[i,j].sum())}


def approximate_tsp(G, start=None):
    if len(G) < 2:
        raise ValueError("TSP requiere al menos dos nodos.")
    if any(float(d.get("weight", 1)) < 0 for _, _, d in G.edges(data=True)):
        raise ValueError("TSP requiere costos no negativos.")
    if not (nx.is_strongly_connected(G) if G.is_directed() else nx.is_connected(G)):
        raise ValueError("Para TSP la red debe ser conexa (fuertemente si es dirigida).")
    path = nx.approximation.traveling_salesman_problem(G, weight="weight", cycle=True)
    if start is not None:
        if start not in path:
            raise ValueError("Nodo inicial no encontrado.")
        pos = path.index(start)
        path = path[pos:-1] + path[:pos] + [start]
    total = sum(float(nx.shortest_path_length(G,u,v,weight="weight")) for u,v in zip(path,path[1:]))
    return {"recorrido": path, "costo": total, "metodo": "heurístico; no garantiza optimalidad"}


def multimodal_summary(G):
    modes = {}
    transfers = []
    for u, v, d in G.edges(data=True):
        mode = str(d.get("mode", "sin_especificar"))
        modes[mode] = modes.get(mode, 0) + 1
        if bool(d.get("transfer", False)) or mode.lower() in ("transfer", "transbordo"):
            transfers.append((str(u), str(v)))
    return {"arcos_por_modo": modes, "enlaces_transbordo": transfers,
            "nota": "La accesibilidad depende de tiempo, espera y penalización de transbordo."}


def wardrop_parallel(free_times, slopes, demand):
    """Wardrop user equilibrium for separable affine parallel routes t_i=a_i+b_i*x_i.

    If b_i=0, zero-slope routes can absorb any residual demand at the
    equilibrium time. Floating-point tolerance handles equality.
    """
    a = np.asarray(free_times, dtype=float)
    b = np.asarray(slopes, dtype=float)
    if a.ndim != 1 or b.shape != a.shape or a.size == 0:
        raise ValueError("Tiempos y pendientes deben ser vectores del mismo tamaño.")
    if not np.all(np.isfinite(a)) or not np.all(np.isfinite(b)) or np.any(a<0) or np.any(b<0) or not np.isfinite(demand) or demand<0:
        raise ValueError("Los parámetros deben ser finitos y no negativos.")
    demand = float(demand)
    if demand == 0:
        return {"flujos": [0.0]*len(a), "tiempo_equilibrio": float(np.min(a)), "tiempos": list(map(float,a))}
    fixed = np.where(b == 0)[0]
    limit = float(np.min(a[fixed])) if fixed.size else float("inf")
    def volume(t):
        return float(np.sum(np.maximum(0.0, (t-a[b>0])/b[b>0])))
    low=float(np.min(a))
    if limit < float("inf") and volume(limit) <= demand:
        t=limit
    else:
        high = max(float(np.max(a)), low+1.0)
        while volume(high)<demand:
            high = max(high*2,high+1)
        t=brentq(lambda x: volume(x)-demand, low, high, xtol=1e-12)
    flows = np.zeros_like(a)
    positive = b>0
    flows[positive] = np.maximum(0, (t-a[positive])/b[positive])
    residual = max(0.0, demand-flows.sum())
    if residual>1e-9:
        choices = [j for j in fixed if abs(a[j]-t)<1e-8]
        if not choices:
            raise ArithmeticError("No fue posible distribuir el flujo de equilibrio.")
        flows[choices[0]] += residual
    times=a+b*flows
    return {"flujos": flows.tolist(), "tiempo_equilibrio": float(t), "tiempos": times.tolist()}


def validate_markov(matrix, tolerance=1e-10):
    P = check_matrix(matrix)
    if np.isnan(P).any() or np.any(P < -tolerance) or np.any(P > 1+tolerance) or not np.allclose(P.sum(axis=1), 1, atol=tolerance, rtol=0):
        raise ValueError("Matriz de Markov inválida: probabilidades en [0,1] y filas con suma 1.")
    return np.clip(P, 0, 1)


def markov_analysis(matrix, steps=10, initial=None):
    P = validate_markov(matrix)
    steps = int(steps)
    if steps < 0 or steps > 1000000:
        raise ValueError("Número de pasos fuera de rango [0, 1 000 000].")
    if initial is None:
        initial = np.eye(len(P))[0]
    initial = np.asarray(initial, dtype=float)
    if initial.shape != (len(P),) or np.any(initial<0) or not np.isclose(initial.sum(),1):
        raise ValueError("La distribución inicial debe sumar 1 y ser no negativa.")
    eigenvalues = np.linalg.eigvals(P)
    powers = np.linalg.matrix_power(P, steps)
    G = nx.DiGraph()
    G.add_nodes_from(range(len(P)))
    G.add_edges_from((i,j) for i in range(len(P)) for j in range(len(P)) if P[i,j] > 1e-12)
    sccs = list(nx.strongly_connected_components(G))
    closed = [sorted(c) for c in sccs if all(v in c for u in c for v in G.successors(u))]
    irreducible = len(sccs)==1
    aperiodic = irreducible and nx.is_aperiodic(G)
    stationary = []
    for c in closed:
        sub = P[np.ix_(c,c)]
        # Stationary distribution from constrained linear least squares.
        M = sub.T-np.eye(len(c))
        M[-1,:] = 1
        rhs = np.zeros(len(c)); rhs[-1]=1
        probs = np.linalg.solve(M,rhs)
        probs = np.maximum(probs,0); probs /= probs.sum()
        full = np.zeros(len(P)); full[c] = probs
        stationary.append(full.tolist())
    moduli = sorted((abs(z) for z in eigenvalues), reverse=True)
    return {"eigenvalues": eigenvalues.tolist(), "magnitudes": moduli,
            "lambda_1": moduli[0], "lambda_2": moduli[1] if len(moduli)>1 else None,
            "distribution": (initial@powers).tolist(), "power": powers.tolist(),
            "stationary_distributions": stationary,
            "irreducible": irreducible, "aperiodic": aperiodic,
            "closed_classes": [[i+1 for i in c] for c in closed],
            "converges_unique": bool(irreducible and aperiodic)}


def absorbing_chain(matrix):
    P=validate_markov(matrix)
    n=len(P)
    absorbing=[i for i in range(n) if np.isclose(P[i,i],1,atol=1e-10) and np.isclose(P[i].sum()-P[i,i],0,atol=1e-10)]
    transient=[i for i in range(n) if i not in absorbing]
    if not absorbing:
        raise ValueError("No existen estados absorbentes.")
    if not transient:
        return {"absorbentes": [i+1 for i in absorbing], "transitorios": [], "matriz_fundamental": [], "tiempos_absorcion": [], "probabilidades_absorcion": []}
    Q=P[np.ix_(transient,transient)]
    R=P[np.ix_(transient,absorbing)]
    if np.max(abs(np.linalg.eigvals(Q))) >= 1-1e-10:
        raise ValueError("No todos los estados no absorbentes alcanzan una absorción con probabilidad 1.")
    N=np.linalg.solve(np.eye(len(Q))-Q,np.eye(len(Q)))
    return {"absorbentes": [i+1 for i in absorbing], "transitorios": [i+1 for i in transient],
            "matriz_fundamental": N.tolist(), "tiempos_absorcion": (N@np.ones(len(Q))).tolist(),
            "probabilidades_absorcion": (N@R).tolist()}


def intermodal_shortest_path(G, source, target, transfer_penalty=0.0):
    """Shortest generalized-cost route with a penalty on mode changes.

    A state is (node, previous_mode), making the optimization exact for
    nonnegative additive edge weights and constant nonnegative transfer penalty.
    Modes come from edge attribute `mode` (default 'sin_especificar').
    """
    import heapq
    if source not in G or target not in G:
        raise ValueError("Origen o destino desconocido.")
    penalty=float(transfer_penalty)
    if not math.isfinite(penalty) or penalty<0:
        raise ValueError("La penalización de transbordo debe ser finita y no negativa.")
    start=(source,None)
    heap=[(0.0,0,start)]
    dist={start:0.0}
    prev={}
    index=0
    winner=None
    while heap:
        cost,_,state=heapq.heappop(heap)
        if cost>dist[state]+1e-12:
            continue
        u,previous_mode=state
        if u==target:
            winner=state
            break
        for _,v,attributes in G.edges(u,data=True):
            # For Graphs / DiGraphs, edges(u) are incident/outgoing respectively.
            if not G.is_directed() and u not in (v,):
                pass
            mode=str(attributes.get('mode','sin_especificar'))
            weight=float(attributes.get('weight',1))
            if not math.isfinite(weight) or weight<0:
                raise ValueError("La ruta intermodal requiere pesos no negativos.")
            extra=penalty if previous_mode is not None and previous_mode!=mode else 0
            state2=(v,mode)
            new=cost+weight+extra
            if new < dist.get(state2,float('inf'))-1e-12:
                dist[state2]=new
                prev[state2]=state
                index+=1
                heapq.heappush(heap,(new,index,state2))
    if winner is None:
        raise nx.NetworkXNoPath(f"No existe ruta de {source} a {target}.")
    states=[]
    current=winner
    while True:
        states.append(current)
        if current==start:
            break
        current=prev[current]
    states.reverse()
    modes=[m for _,m in states[1:]]
    return {'ruta':[str(x) for x,_ in states], 'modos':modes,
            'transbordos':sum(x!=y for x,y in zip(modes,modes[1:])),
            'costo_generalizado':float(dist[winner]),
            'penalizacion_por_transbordo':penalty}
