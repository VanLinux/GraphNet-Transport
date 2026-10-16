import numpy as np
import networkx as nx
import pytest
from graphnet_transport import core
from graphnet_transport.counting import count_routes
from graphnet_transport.presentation import render_result
from graphnet_transport.reports import build_latex_report


def example():
    a = np.array([[0, 1, 1, np.nan],
                  [1, 0, 1, np.nan],
                  [1, 1, 0, 1],
                  [np.nan, np.nan, 1, 0]], dtype=float)
    return core.matrix_to_graph(a, directed=False, labels=['A','B','C','D'])


def test_density_from_notebook():
    g = example()
    r = core.network_metrics(g)
    assert (r['nodos'], r['arcos'], r['aristas_maximas']) == (4,4,6)
    assert r['densidad'] == pytest.approx(2/3)
    assert r['densidad_porcentaje'] == pytest.approx(66.6666667)
    assert r['conexa'] and r['grado'] == {'A':2,'B':2,'C':3,'D':1}
    rendered = render_result('Estructura y matrices','Grados, conectividad y centralidad',r)
    assert '66.67%' in rendered and '4 de 6' in rendered
    assert '<th>Nodo</th>' in rendered and '<th>Grado</th>' in rendered
    assert 'Grado entrada' not in rendered
    report = build_latex_report(name='Ejercicio',category='Estructura y matrices',algorithm='Grados, conectividad y centralidad',
                                description='Análisis',input_help='Matriz simétrica',
                                matrix=core.graph_to_matrix(g)[0], row_labels=list(g),
                                parameters={'Red dirigida':'No'},results=r)
    assert r'\frac{2m}{n(n-1)}' in report
    assert r'\frac{2\cdot4}{4(4-1)}' in report
    assert r'66.67\%' in report and r'\begin{tabular}' in report
    assert 'Desarrollador:' in report


def test_walks_and_simple_paths_different():
    g = example()
    a = nx.to_numpy_array(g,nodelist=list(g),weight=None,dtype=int)
    for k in range(5):
        r = count_routes(g,'A','D',k,'walks')
        assert r['total'] == int(np.linalg.matrix_power(a,k)[0,3])
    assert count_routes(g,'A','D',2,'walks')['total'] == 1
    assert count_routes(g,'A','D',3,'simple')['total'] == 1
    assert count_routes(g,'A','A',2,'walks')['total'] == 2
    assert count_routes(g,'A','A',2,'simple')['total'] == 0
    assert count_routes(g,'A','A',0,'simple')['total'] == 1
    assert count_routes(g,'A','D',3,'simple')['ruta_ejemplo'] == ['A','B','C','D']


def test_walks_exact_length_and_zero_weights():
    a = [[0,0,np.nan],[np.nan,0,1],[np.nan,np.nan,0]]
    g = core.matrix_to_graph(a)
    assert count_routes(g,'1','3',2,'walks')['total'] == 1
    assert count_routes(g,'1','3',2,'simple')['total'] == 1
    assert count_routes(g,'1','3',1,'walks')['total'] == 0


def test_multigraph_parallel_edges_and_big_ints():
    g = nx.MultiDiGraph()
    g.add_edges_from([('A','B'),('A','B'),('B','C')])
    assert count_routes(g,'A','C',2,'walks')['total'] == 2
    assert count_routes(g,'A','C',2,'simple')['total'] == 2
    huge = nx.DiGraph()
    huge.add_edges_from([('A','B'),('A','C'),('B','A'),('B','C'),('C','A'),('C','B')])
    assert count_routes(huge,'A','A',100,'walks')['total'] > 2**63


def test_validation_and_limits():
    g = example()
    for k in (-1,101,2.5,True):
        with pytest.raises(ValueError): count_routes(g,'A','D',k)
    with pytest.raises(ValueError): count_routes(g,'A','z',2)
    with pytest.raises(ValueError): count_routes(nx.path_graph(17),0,2,3,'simple')


def test_count_report_has_formula_and_example():
    g = example()
    a, labels = core.graph_to_matrix(g)
    r = count_routes(g,'A','D',3,'walks')
    report = build_latex_report(name='Caminos longitud 3', category='Estructura y matrices',
         algorithm='Conteo de caminos de longitud k',description='Conteo de caminos',
         input_help='Matriz de adyacencia', matrix=a, row_labels=labels,
         parameters={'Red dirigida':'No','Longitud k':3},results=r)
    assert '(A^k)_{ij}' in report
    assert 'Cantidad exacta' in report and 'Longitud (aristas)' in report
    assert 'ruta_ejemplo' not in report
    assert 'draw=routegreen' in report
    assert 'Versión 3.1.0' in report


def test_adjacency_zeros_are_absence_only_when_requested():
    a = [[0,1,1,0], [1,0,1,0], [1,1,0,1], [0,0,1,0]]
    adjacency = core.matrix_to_graph(a, directed=False, zero_is_absent=True)
    weighted = core.matrix_to_graph(a, directed=False, zero_is_absent=False)
    assert adjacency.number_of_edges() == 4
    assert core.network_metrics(adjacency)['densidad'] == pytest.approx(2/3)
    assert weighted.number_of_edges() == 6
    assert core.network_metrics(weighted)['densidad'] == 1
    with pytest.raises(ValueError, match='simétrica'):
        core.matrix_to_graph([[0,1],[0,0]],directed=False,zero_is_absent=True)
    assert core.matrix_to_graph([[0,0],[float('nan'),0]], directed=True).number_of_edges() == 1


def test_directed_complete_density_and_single_vertex_report():
    binary = np.ones((4, 4)) - np.eye(4)
    g = core.matrix_to_graph(binary, directed=True, zero_is_absent=True)
    data = core.network_metrics(g)
    assert data['arcos'] == 12
    assert data['aristas_maximas'] == 12
    assert data['densidad'] == 1
    one = core.matrix_to_graph([[0]], directed=False, zero_is_absent=True)
    data = core.network_metrics(one)
    tex = build_latex_report(name='Nodo aislado', category='Estructura y matrices',
      algorithm='Grados, conectividad y centralidad', description='Un nodo',
      input_help='Matriz',matrix=[[0]],parameters={'Red dirigida':'No'},results=data)
    assert 'denominador nulo' in tex and '0(0-1)' not in tex
