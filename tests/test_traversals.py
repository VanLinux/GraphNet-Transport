import networkx as nx
from graphnet_transport.traversals import euler_analysis, hamilton_analysis
from graphnet_transport.presentation import render_result


def test_euler_circuit_and_trail_undirected():
    cycle = nx.cycle_graph(5)
    r = euler_analysis(cycle)
    assert r['euleriano'] is True and r['camino_euleriano'] is True
    assert len(r['recorrido']) == 6 and r['recorrido'][0] == r['recorrido'][-1]
    assert r['aristas_recorridas'] == 5
    trail = euler_analysis(nx.path_graph(4))
    assert trail['euleriano'] is False and trail['camino_euleriano'] is True
    assert len(trail['recorrido']) == 4
    star = euler_analysis(nx.star_graph(4))
    assert star['camino_euleriano'] is False


def test_euler_directed_and_disconnected():
    circuit = nx.DiGraph([('A','B'),('B','C'),('C','A')])
    assert euler_analysis(circuit)['euleriano']
    trail = nx.DiGraph([('A','B'),('B','C')])
    assert euler_analysis(trail)['camino_euleriano']
    g = nx.Graph([(0,1),(2,3)])
    assert not euler_analysis(g)['camino_euleriano']


def test_hamilton_directed_and_undirected():
    cycle = hamilton_analysis(nx.cycle_graph(5))
    assert cycle['determinado'] and cycle['hamiltoniano']
    assert len(cycle['recorrido']) == 6
    assert cycle['recorrido'][0] == cycle['recorrido'][-1]
    path = hamilton_analysis(nx.path_graph(5))
    assert not path['hamiltoniano'] and path['camino_hamiltoniano']
    assert len(path['recorrido']) == 5
    star = hamilton_analysis(nx.star_graph(4))
    assert not star['hamiltoniano'] and not star['camino_hamiltoniano']
    d = hamilton_analysis(nx.DiGraph([(0,1),(1,2),(2,0)]))
    assert d['hamiltoniano']


def test_hamilton_larger_graph_explicitly_unknown():
    r = hamilton_analysis(nx.path_graph(17))
    assert not r['determinado'] and r['hamiltoniano'] is None
    assert 'No determinado' in r['tipo']


def test_result_html_is_not_raw_json_and_escapes_names():
    result = {'ruta':['A','B<script>','D'], 'costo':7, 'hamiltoniano':False}
    html = render_result('Caminos mínimos','Dijkstra',result)
    assert 'Recorrido obtenido' in html
    assert '&lt;script&gt;' in html and '<script>' not in html
    assert '7' in html and '→' in html
    assert 'No' in html
