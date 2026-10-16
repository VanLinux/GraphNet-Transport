"""Compact scientific HTML results for Qt; data is escaped, never raw TeX."""
from __future__ import annotations

from html import escape
import math

ROUTE_KEYS = ("ruta", "recorrido", "ruta_ejemplo")
HIGHLIGHTS = {"costo", "costo_generalizado", "flujo_maximo", "corte_minimo", "lambda_2",
              "lambda_1", "tiempo_equilibrio", "nodos", "arcos", "euleriano", "hamiltoniano",
              "camino_euleriano", "camino_hamiltoniano", "tipo", "determinado", "total"}
STYLE = """<style>
body {font-family:'DejaVu Sans',sans-serif;color:#213349;background:#fff;font-size:12px;}
h2 {color:#173e62;font-size:19px;margin:3px 0;} h3 {color:#26455f;font-size:14px;margin:10px 0 5px;}
p {margin:5px 0;} .muted {color:#67798c;} .card {background:#eef5fc;padding:9px;margin:4px 0;}
.big {font-size:18px;font-weight:bold;color:#12577e;} .good {color:#097b60;font-weight:bold;}
.note {background:#edf7f4;padding:8px;margin:8px 0;} table {border-collapse:collapse;width:100%;margin:6px 0 12px;}
th {background:#dceaf5;color:#18446e;font-weight:bold;text-align:left;padding:6px;border:1px solid #c4d5e2;}
td {padding:5px 7px;border:1px solid #d8e3ec;} tr.alt {background:#f2f6fa;}
.station {color:#086651;font-weight:bold;} .arrow {color:#148c76;font-weight:bold;}
</style>"""


def _nice(label):
    return str(label).replace("_", " ").strip().capitalize()


def _value(value):
    if isinstance(value, bool):
        return "Sí" if value else "No"
    if value is None:
        return "No determinado"
    if isinstance(value, float):
        if math.isnan(value):
            return "No definido"
        if math.isinf(value):
            return "∞" if value > 0 else "−∞"
        return f"{value:.5g}"
    return str(value)


def _cell(value):
    return escape(_value(value))


def _table(headers, rows):
    head = '<tr>' + ''.join('<th>'+escape(str(h))+'</th>' for h in headers) + '</tr>'
    body = ''.join('<tr'+(' class="alt"' if i % 2 else '')+'>' +
                   ''.join('<td>'+_cell(x)+'</td>' for x in row) + '</tr>'
                   for i, row in enumerate(rows))
    return '<table>'+head+body+'</table>'


def _render(value, *, level=0):
    if isinstance(value, dict):
        if not value:
            return '<p class="muted">Sin datos.</p>'
        scalars = [(k, v) for k, v in value.items() if not isinstance(v, (dict, list, tuple))]
        rest = [(k, v) for k, v in value.items() if isinstance(v, (dict, list, tuple))]
        result = _table(["Indicador", "Valor"], [(_nice(k), v) for k, v in scalars]) if scalars else ''
        for k, v in rest:
            if isinstance(v, dict) and all(not isinstance(x, (dict, list, tuple)) for x in v.values()):
                result += '<h3>'+escape(_nice(k))+'</h3>'+_table(['Nodo', 'Valor'], v.items())
            else:
                result += '<h3>'+escape(_nice(k))+'</h3>'+_render(v, level=level+1)
        return result
    if isinstance(value, (list, tuple)):
        if not value:
            return '<span class="muted">Sin elementos</span>'
        if all(isinstance(row, (list, tuple)) for row in value):
            if len(value) <= 60 and max(map(len, value)) <= 32:
                return _table([str(i+1) for i in range(max(map(len, value)))], value)
        if all(not isinstance(x, (dict, list, tuple)) for x in value):
            return ', '.join(_cell(x) for x in value[:100]) + (' …' if len(value)>100 else '')
        return _table(['Índice', 'Valor'], [(i+1, str(x)) for i, x in enumerate(value[:50])])
    return _cell(value)


def _route_html(route, title='Recorrido obtenido'):
    if not isinstance(route, (tuple, list)) or not route:
        return ''
    chain = '<span class="arrow"> → </span>'.join('<span class="station">'+escape(str(x))+'</span>' for x in route)
    return '<h3>'+escape(title)+'</h3><div class="note">'+chain+'</div>'


def _metrics_html(result):
    n, m = int(result['nodos']), int(result['arcos'])
    directed = bool(result['dirigido'])
    possible = int(result.get('aristas_maximas', n*(n-1) if directed else n*(n-1)//2))
    density = float(result['densidad'])
    if directed:
        components = result['componentes_fuertes']
        connection = 'fuertemente conexa' if components == 1 else 'no fuertemente conexa'
        comp_label = 'Componentes fuertes'
    else:
        components = result['componentes_debiles']
        connection = 'conexa' if components == 1 else 'no conexa'
        comp_label = 'Componentes'
    header = ('<div class="card"><span class="muted">Densidad de conexiones</span>'
              f'<p class="big">{100*density:.2f}%</p><p>{m} de {possible} conexiones posibles'
              f' · {"Red dirigida" if directed else "Red no dirigida"}</p>'
              f'<p><b>Estado:</b> {escape(connection.capitalize())} · {comp_label}: {components}</p></div>')
    nodes = list(result['grado'])
    if directed:
        rows = [(node, result['grado_entrada'][node], result['grado_salida'][node], result['grado'][node]) for node in nodes]
        table = _table(['Nodo','Grado de entrada','Grado de salida','Grado total'], rows)
    else:
        table = _table(['Nodo','Grado','Centralidad de grado'],
                       [(node, result['grado'][node], round(result['centralidad_grado'][node],4)) for node in nodes])
    if nodes:
        best = max(nodes, key=lambda node: result['grado'][node])
        interpretation = (f'El nodo {best} presenta el mayor grado ({result["grado"][best]}). '
                          'La densidad describe conexiones topológicas, no la capacidad vial ni la accesibilidad temporal.')
    else:
        interpretation = 'No se identificaron nodos.'
    note = result.get('nota_densidad', '')
    return (header + '<h3>Conexiones por nodo</h3>' + table +
            '<div class="note"><b>Interpretación:</b> '+escape(interpretation)+
            '<p class="muted">'+escape(note)+'</p></div>'+
            '<p class="muted">Intermediación, puentes y articulaciones se conservan en el archivo JSON; '
            'se omiten aquí para priorizar los indicadores esenciales.</p>')


def _count_html(result):
    return ('<div class="card"><span class="muted">Total de caminos de longitud exacta '
            + _cell(result['longitud']) + '</span><p class="big">' + _cell(result['total']) +
            '</p><p>' + _cell(result['tipo']) + '</p></div>' +
            _table(['Origen','Destino','Longitud (aristas)'],
                   [(result['origen'], result['destino'], result['longitud'])]) +
            _route_html(result.get('ruta_ejemplo'), 'Ejemplo de secuencia encontrada') +
            '<div class="note">'+escape(result['interpretacion'])+'</div>')


def render_result(category: str, algorithm: str, result: dict) -> str:
    if not isinstance(result, dict):
        result = {'resultado': result}
    headline = '<h2>'+escape(algorithm)+'</h2><p class="muted">'+escape(category)+'</p>'
    if category == 'Estructura y matrices' and 'densidad' in result and 'grado' in result:
        return STYLE + headline + _metrics_html(result)
    if 'longitud' in result and 'total' in result and 'ruta_ejemplo' in result:
        return STYLE + headline + _count_html(result)
    cards = ''.join('<div class="card"><b>'+escape(_nice(k))+':</b> <span class="big">'+_cell(v)+'</span></div>'
                    for k, v in result.items() if k in HIGHLIGHTS and not isinstance(v, (list, dict)))
    route = next((result.get(k) for k in ROUTE_KEYS if isinstance(result.get(k), list) and result.get(k)), None)
    details = {k: v for k, v in result.items() if k not in HIGHLIGHTS and k not in ROUTE_KEYS}
    return STYLE + headline + cards + _route_html(route) + ('<h3>Detalle</h3>'+_render(details) if details else '')
