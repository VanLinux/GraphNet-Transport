import numpy as np
import networkx as nx
import pytest
from graphnet_transport import __version__
from graphnet_transport import core as c


def example():
    return np.array([[0,4,2,np.nan],[np.nan,0,1,5],[np.nan,np.nan,0,3],[np.nan,np.nan,np.nan,0]])


def test_version(): assert __version__ == '1.0.0'

def test_graph_and_path():
    G=c.matrix_to_graph(example())
    assert c.shortest_path(G,'1','4')['costo'] == 5
    assert c.shortest_path(G,'1','4')['ruta'] == ['1','3','4']
    assert c.shortest_path(G,'1','4','bellman-ford')['costo']==5
    assert c.all_pairs(G)['1']['4']==5
    assert c.network_metrics(G)['componentes_debiles']==1
    assert c.graph_matrices(G)['adyacencia'].shape==(4,4)


def test_undirected_laplacian_and_tree():
    a=np.array([[0,1,4],[1,0,2],[4,2,0]],float)
    G=c.matrix_to_graph(a,False)
    assert c.spanning_tree(G)['costo']==3
    assert c.spanning_tree(G,'prim')['costo']==3
    assert c.algebraic_connectivity(G)==pytest.approx(3)
    assert c.graph_matrices(G)['laplaciana'].sum()==0


def test_missing_and_zero_weight():
    a=np.array([[0,0,np.nan],[np.nan,0,2],[np.nan,np.nan,0]])
    G=c.matrix_to_graph(a)
    assert G.has_edge('1','2') and G['1']['2']['weight']==0
    assert c.shortest_path(G,'1','3')['costo']==2


def test_flow():
    a=np.array([[0,3,2,np.nan],[np.nan,0,1,2],[np.nan,np.nan,0,3],[np.nan,np.nan,np.nan,0]])
    result=c.maximum_flow(c.matrix_to_graph(a),'1','4')
    assert result['flujo_maximo']==5
    assert result['corte_minimo']==5


def test_assignment():
    r=c.assignment([[4,1,3],[2,0,5],[3,2,2]])
    assert r['costo']==5
    assert len(r['asignaciones'])==3


def test_tsp():
    G=c.matrix_to_graph([[0,1,1],[1,0,1],[1,1,0]],False)
    r=c.approximate_tsp(G,'1')
    assert r['recorrido'][0]==r['recorrido'][-1]=='1'
    assert r['costo']==3


def test_wardrop():
    r=c.wardrop_parallel([10,12],[1,0.5],12)
    assert sum(r['flujos'])==pytest.approx(12)
    assert r['tiempos'][0]==pytest.approx(r['tiempos'][1])
    r=c.wardrop_parallel([10,12],[0,1],100)
    assert sum(r['flujos'])==pytest.approx(100)
    assert r['flujos'][0]>=98


def test_markov():
    P=[[0.8,0.2],[0.1,0.9]]
    r=c.markov_analysis(P,10)
    assert r['lambda_1']==pytest.approx(1)
    assert r['lambda_2']==pytest.approx(0.7)
    assert r['stationary_distributions'][0]==pytest.approx([1/3,2/3])
    assert r['converges_unique']
    assert sum(r['distribution'])==pytest.approx(1)


def test_absorbing():
    P=[[1,0,0],[0.5,0.5,0],[0.2,0.3,0.5]]
    r=c.absorbing_chain(P)
    assert r['absorbentes']==[1]
    assert r['tiempos_absorcion']==pytest.approx([2,3.2])
    assert np.asarray(r['probabilidades_absorcion'])==pytest.approx(np.ones((2,1)))


def test_file_io(tmp_path):
    file=tmp_path/'network.csv'
    a=example()
    c.save_csv(file,a)
    assert np.allclose(c.load_csv(file),a,equal_nan=True)
    gfile=tmp_path/'network.graphml'
    c.save_graphml(gfile,c.matrix_to_graph(a))
    G=c.load_graphml(gfile)
    assert c.shortest_path(G,'1','4')['costo']==5


def test_errors():
    with pytest.raises(ValueError): c.validate_markov([[0.6,0.3],[0.2,0.8]])
    with pytest.raises(ValueError): c.matrix_to_graph([[0,1],[2,0]],False)
    G=c.matrix_to_graph([[0,-1], [np.nan,0]])
    with pytest.raises(ValueError): c.shortest_path(G,'1','2')


def test_intermodal():
    G=nx.DiGraph()
    G.add_edge("A","B",weight=2,mode="metro")
    G.add_edge("B","C",weight=2,mode="bus")
    G.add_edge("A","C",weight=7,mode="metro")
    assert c.intermodal_shortest_path(G,"A","C",1)["costo_generalizado"]==5
    assert c.intermodal_shortest_path(G,"A","C",5)["costo_generalizado"]==7


def test_undirected_flow_and_examples():
    G=c.matrix_to_graph([[0,3,1],[3,0,2],[1,2,0]],False)
    assert c.maximum_flow(G,'1','3')['flujo_maximo']==3
    example_file=__import__('pathlib').Path(__file__).parents[1]/'examples'/'red_intermodal.graphml'
    other=c.load_graphml(example_file)
    assert c.multimodal_summary(other)['enlaces_transbordo']==[('B','C')]
    assert c.intermodal_shortest_path(other,'A','C',1)['costo_generalizado']==5
