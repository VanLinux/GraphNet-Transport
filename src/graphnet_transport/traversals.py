"""Exact Euler and Hamilton analysis; no heuristic is reported as a proof."""
from __future__ import annotations

from functools import lru_cache
import networkx as nx

# Exact exponential exhaustive search. A larger graph is explicitly undecided.
HAMILTON_EXACT_LIMIT = 16


def euler_analysis(graph):
    """Euler circuit/path existence and a concrete itinerary where possible."""
    if graph.number_of_nodes() == 0:
        raise ValueError("El grafo no contiene nodos.")
    G = graph
    if G.number_of_edges() == 0:
        return {"euleriano": False, "camino_euleriano": False, "tipo": "Sin aristas", "recorrido": [],
                "aristas_recorridas": 0, "razon": "No existen aristas que recorrer."}
    circuit = nx.is_eulerian(G)
    trail = nx.has_eulerian_path(G)
    if circuit:
        edges = list(nx.eulerian_circuit(G))
        classification = "Circuito euleriano"
    elif trail:
        edges = list(nx.eulerian_path(G))
        classification = "Camino euleriano abierto"
    else:
        edges = []
        classification = "No posee recorrido euleriano"
    itinerary = [edges[0][0]] + [v for _, v in edges] if edges else []
    if G.is_directed():
        degree = {str(x): {"entrada": G.in_degree(x), "salida": G.out_degree(x)} for x in G.nodes}
        criterion = "En un circuito, cada nodo cumple grado de entrada = grado de salida; la conexión también importa."
    else:
        degree = {str(x): int(G.degree(x)) for x in G.nodes}
        criterion = "Un circuito requiere grados pares y conectividad; un camino abierto admite exactamente dos nodos impares."
    return {"euleriano": bool(circuit), "camino_euleriano": bool(trail), "tipo": classification,
            "recorrido": [str(x) for x in itinerary], "aristas_recorridas": len(edges),
            "grados": degree, "criterio": criterion}


def hamilton_analysis(graph, max_nodes=HAMILTON_EXACT_LIMIT):
    """Determine exactly whether any Hamiltonian cycle or path exists (small graphs).

    Iterative DFS with memoized failed states. Each state is (last node, visited set).
    A non-conclusive result is explicit for larger networks; never report false.
    """
    G = graph
    nodes = list(G.nodes)
    n = len(nodes)
    if n == 0:
        raise ValueError("El grafo no contiene nodos.")
    if n > max_nodes:
        return {"determinado": False, "hamiltoniano": None, "camino_hamiltoniano": None,
                "tipo": "No determinado", "recorrido": [], "nodos_visitados": 0,
                "nota": f"La comprobación exacta está limitada a {max_nodes} nodos (problema de complejidad exponencial)."}
    index = {node: k for k, node in enumerate(nodes)}
    neighbor_masks = []
    for node in nodes:
        bits = 0
        for adjacent in G.successors(node) if G.is_directed() else G.neighbors(node):
            bits |= 1 << index[adjacent]
        neighbor_masks.append(bits)
    full = (1 << n) - 1

    def seek(need_cycle):
        for start in range(n):
            @lru_cache(maxsize=None)
            def search(last, mask):
                if mask == full:
                    return () if (not need_cycle or (neighbor_masks[last] & (1 << start))) else None
                remaining = neighbor_masks[last] & ~mask
                while remaining:
                    bit = remaining & -remaining
                    remaining -= bit
                    next_node = bit.bit_length() - 1
                    suffix = search(next_node, mask | bit)
                    if suffix is not None:
                        return (next_node,) + suffix
                return None
            result = search(start, 1 << start)
            if result is not None:
                indexes = [start, *result]
                if need_cycle:
                    indexes.append(start)
                return [str(nodes[i]) for i in indexes]
        return None

    # A one-vertex graph is a Hamilton path, but not a nontrivial Hamilton circuit.
    cycle = seek(True) if n >= (2 if G.is_directed() else 3) else None
    path = cycle if cycle is not None else seek(False)
    is_cycle = cycle is not None
    return {"determinado": True, "hamiltoniano": is_cycle,
            "camino_hamiltoniano": path is not None,
            "tipo": ("Ciclo hamiltoniano" if is_cycle else "Camino hamiltoniano abierto" if path else "Sin camino hamiltoniano"),
            "recorrido": path or [], "nodos_visitados": n if path else 0,
            "nota": "Búsqueda exacta: cada vértice aparece una vez, salvo el retorno final al origen en un ciclo."}
