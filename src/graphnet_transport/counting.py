"""Exact-length network traversal counting, independent of the Qt interface.

A^k counts walks (revisiting vertices/edges is allowed), not simple paths.
Parallel edges are counted as distinct choices. Integers have arbitrary precision.
"""
from __future__ import annotations

from functools import lru_cache
from numbers import Integral
import networkx as nx


def count_routes(G: nx.Graph, source: str, target: str, length: int,
                 kind: str = "walks") -> dict:
    """Count exact-length walks or vertex-simple paths from source to target.

    The simple-path counter uses a memoized visited-vertex bitmask and is bounded
    to 16 vertices. The sample is an illustrative route, never an exhaustive list.
    """
    if source not in G or target not in G:
        raise ValueError("El origen y el destino deben existir en la red.")
    if isinstance(length, bool) or not isinstance(length, Integral) or not 0 <= length <= 100:
        raise ValueError("La longitud debe ser un entero entre 0 y 100 aristas.")
    if kind not in {"walks", "simple"}:
        raise ValueError("El tipo de conteo debe ser 'walks' o 'simple'.")
    nodes = list(G.nodes)
    n = len(nodes)
    if kind == "simple" and n > 16:
        raise ValueError("El conteo exacto de caminos simples está limitado a 16 nodos; no se informa un cero sin comprobarlo.")
    if kind == "walks" and n > 500:
        raise ValueError("El conteo de recorridos admite hasta 500 nodos.")
    pos = {name: i for i, name in enumerate(nodes)}
    src, dst = pos[source], pos[target]
    neighbors = [[] for _ in nodes]
    for u in nodes:
        for v in G.neighbors(u):
            # In multigraphs, distinct parallel edges produce distinct traversals.
            mult = G.number_of_edges(u, v) if G.is_multigraph() else 1
            neighbors[pos[u]].append((pos[v], mult))

    if kind == "walks":
        # Equivalent to the (s,t) entry of A**length, calculated using O(k|E|)
        # integer operations instead of materializing possibly enormous matrices.
        vector = [0] * n
        vector[src] = 1
        for _ in range(length):
            next_vector = [0] * n
            for u, amount in enumerate(vector):
                if amount:
                    for v, multiplicity in neighbors[u]:
                        next_vector[v] += amount * multiplicity
            vector = next_vector
        total = vector[dst]
        @lru_cache(None)
        def possible(u, remaining):
            return u == dst if remaining == 0 else any(
                possible(v, remaining - 1) for v, _ in neighbors[u])
        sample = None
        if total:
            walk = [src]
            u = src
            for remaining in range(length, 0, -1):
                u = next(v for v, _ in neighbors[u] if possible(v, remaining - 1))
                walk.append(u)
            sample = [str(nodes[v]) for v in walk]
        return {"tipo": "Recorridos (se permiten repeticiones)",
                "origen": str(source), "destino": str(target), "longitud": int(length),
                "total": total, "ruta_ejemplo": sample,
                "interpretacion": "Se cuentan secuencias de aristas de longitud exacta, incluso si se repiten nodos o aristas. El total equivale a (A^k)[origen,destino]."}

    if length > n - 1 or (source == target and length > 0):
        total, sample = 0, None
    else:
        @lru_cache(None)
        def count(u, seen, remaining):
            if remaining == 0:
                return 1 if u == dst else 0
            if u == dst:
                return 0  # A simple path cannot pass through its destination.
            return sum(mult * count(v, seen | (1 << v), remaining-1)
                       for v, mult in neighbors[u] if not (seen & (1 << v)))
        total = count(src, 1 << src, length)
        sample = None
        if total:
            chosen = [src]
            u, seen = src, 1 << src
            for remaining in range(length, 0, -1):
                v = next(v for v, mult in neighbors[u]
                         if not (seen & (1 << v)) and mult and
                         count(v, seen | (1 << v), remaining - 1))
                chosen.append(v)
                seen |= 1 << v
                u = v
            sample = [str(nodes[v]) for v in chosen]
    return {"tipo": "Caminos simples (sin repetir nodos)",
            "origen": str(source), "destino": str(target), "longitud": int(length),
            "total": total, "ruta_ejemplo": sample,
            "interpretacion": "Se cuentan caminos de longitud exacta sin repetir vértices. Este total NO se obtiene en general mediante potencias de A."}
