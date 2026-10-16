import numpy as np
from graphnet_transport.reports import build_latex_report


def test_letter_paper_and_math_and_color_route():
    text = build_latex_report(
        name='Trayecto óptimo', category='Caminos mínimos', algorithm='Dijkstra',
        description='Ruta mínima', input_help='Vacío implica ausencia',
        matrix=np.array([[0, 1, np.nan], [np.nan, 0, 2], [np.nan, np.nan, 0]]),
        row_labels=['A', 'B', 'C'], column_labels=['A', 'B', 'C'],
        parameters={'Origen':'A', 'Destino':'C', 'Red dirigida':'Sí'},
        results={'ruta':['A','B','C'], 'costo':3.0},
    )
    assert r'\documentclass[11pt,letterpaper]{article}' in text
    assert r'\usepackage{tikz}' in text
    assert r'\begin{tikzpicture}' in text
    assert r'draw=routegreen' in text
    assert r'\begin{equation}' in text and r'\min_' in text
    assert 'Héctor Alonso Benítez García' in text
    assert 'Versión 3.1.0' in text


def test_large_graph_has_honest_omission():
    a = np.diag(np.zeros(17))
    text = build_latex_report(name='Red grande', category='Recorridos de grafos', algorithm='Análisis hamiltoniano',
                              description='Prueba',input_help='Grafo',matrix=a,results={'hamiltoniano': None})
    assert 'más de 16 nodos' in text
    assert 'No determinado' in text
