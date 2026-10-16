"""Human-readable and safe results as HTML for QTextBrowser (never raw TeX/JSON)."""
from __future__ import annotations

from html import escape
import math

ROUTE_KEYS = ("ruta", "recorrido")
HIGHLIGHTS = {"costo", "costo_generalizado", "flujo_maximo", "corte_minimo", "lambda_2", "lambda_1", "tiempo_equilibrio", "nodos", "arcos", "euleriano", "hamiltoniano", "camino_euleriano", "camino_hamiltoniano", "tipo", "determinado"}


def _nice(label):
    return str(label).replace("_", " ").strip().capitalize()


def _value(value):
    if isinstance(value, bool):
        return "Sí" if value else "No"
    if value is None:
        return "No determinado"
    if isinstance(value, float):
        return f"{value:.6g}" if math.isfinite(value) else "∞" if value > 0 else "−∞"
    return str(value)


def _cell(value):
    return escape(_value(value))


def _render(value, *, level=0):
    if isinstance(value, dict):
        if not value:
            return '<p class="muted">Sin datos disponibles.</p>'
        rows = []
        for key, child in value.items():
            rows.append('<div class="entry"><div class="entry-label">' + escape(_nice(key)) +
                        '</div><div class="entry-value">' + _render(child, level=level + 1) + '</div></div>')
        return '<div class="entries">' + ''.join(rows) + '</div>'
    if isinstance(value, (list, tuple)):
        if not value:
            return '<span class="muted">Sin elementos</span>'
        if all(isinstance(row, (list, tuple)) for row in value):
            if len(value) <= 60 and max(map(len, value)) <= 32:
                return '<div class="table-wrap"><table>' + ''.join(
                    '<tr>' + ''.join(f'<td>{_render(item, level=level+1)}</td>' for item in row) + '</tr>' for row in value
                ) + '</table></div>'
        return '<div class="list">' + ''.join('<div class="list-item">' + _render(item, level=level+1) + '</div>' for item in value[:200]) + ('<p>Lista truncada.</p>' if len(value) > 200 else '') + '</div>'
    return _cell(value)


def render_result(category: str, algorithm: str, result: dict) -> str:
    """Produce visible card summaries and a route ribbon when provided by the engine."""
    cards = []
    for key, value in result.items():
        if key in HIGHLIGHTS and not isinstance(value, (list, dict)):
            color = '#0d7562' if value is True else '#a94b1b' if value is False else '#184c81'
            cards.append(f'<div class="card"><span>{escape(_nice(key))}</span><strong style="color:{color}">{_cell(value)}</strong></div>')
    route = next((result.get(k) for k in ROUTE_KEYS if isinstance(result.get(k), list) and result.get(k)), None)
    route_html = ''
    if route is not None:
        blocks = ['<span class="station">'+escape(str(node))+'</span>' for node in route]
        route_html = ('<section class="route"><h3>Recorrido obtenido</h3>' +
                      '<div class="stations">' + '<span class="connector">→</span>'.join(blocks) +
                      '</div><p class="muted">Orden de visita de los nodos. La representación matemática completa está en el reporte.</p></section>')
    details = {key: value for key, value in result.items() if key not in HIGHLIGHTS and key not in ROUTE_KEYS}
    style = """<style>
    body {font-family:'Sans Serif'; color:#213349; background:#fff; font-size:13px;}
    h2 {font-size:19px; color:#173e62; margin-bottom:3px;} h3 {color:#26455f; font-size:15px;}
    p.muted, span.muted {color:#68798c;} .sub {color:#708096;}
    .cards {margin:14px 0;} .card {display:inline-block; vertical-align:top; background:#eef5fc; border:1px solid #d3e3f2;
      border-radius:7px; padding:10px; margin:3px;} .card span{display:block;color:#465d73;font-size:11px;}
    .card strong{display:block;font-size:19px;margin-top:5px;}
    .route {background:#eaf7f3;border:1px solid #9ad9c7; padding:12px; margin:12px 0;}
    .stations {padding:6px 0; } .station{font-weight:700;color:#075e52;background:#fff;border:1px solid #83c5b6;padding:6px 9px;}
    .connector{font-weight:700;color:#138876; padding:0 5px;}
    .entries{margin-top:8px;} .entry{border-bottom:1px solid #e5eaf0;padding:7px 0;}
    .entry-label{font-weight:600;color:#345372;margin-bottom:4px;}.entry-value{margin-left:10px;}
    .list-item{padding:2px 0;} table{border-collapse:collapse; margin:5px 0;}
    td{border:1px solid #cbd8e5; padding:5px 10px; text-align:right;} tr:nth-child(even){background:#f1f6fc;}
    </style>"""
    return (style + '<h2>'+escape(algorithm)+'</h2><p class="sub">'+escape(category)+'</p>'+
            '<div class="cards">'+''.join(cards)+'</div>'+route_html+
            '<h3>Detalle del cálculo</h3>'+_render(details))
