"""Offscreen desktop smoke tests; skipped only if Qt isn't installed."""
import os
import json
import numpy as np
import pytest

os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
pytest.importorskip('PySide6')
from PySide6.QtWidgets import QApplication
from graphnet_transport.gui import MainWindow


def test_gui_can_calculate_shortest_path_and_markov():
    app=QApplication.instance() or QApplication([])
    w=MainWindow()
    try:
        w.task.setCurrentText('Camino mínimo: Dijkstra')
        w.calculate()
        result=json.loads(w.output.toPlainText())
        assert result['costo']==5.0
        assert result['ruta']==['1','3','4']
        w.set_matrix([[0.8,0.2],[0.1,0.9]])
        w.task.setCurrentText('Markov: valores propios y evolución')
        w.calculate()
        result=json.loads(w.output.toPlainText())
        assert result['lambda_2']==pytest.approx(0.7)
        assert result['converges_unique'] is True
    finally:
        w.close()
