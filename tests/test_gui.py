import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication, QInputDialog, QMessageBox
from graphnet_transport.gui import GROUPS, TASKS, MainWindow
from graphnet_transport import reports


def set_algorithm(window, group, algorithm):
    window.category.setCurrentText(group)
    window.task.setCurrentText(algorithm)


def test_categorized_ui_and_calculations(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(QMessageBox, "critical", lambda _parent, _title, detail: pytest.fail(str(detail)))
    w = MainWindow()
    try:
        assert len(GROUPS) >= 7
        assert len(TASKS) == 16
        assert not w.report_button.isEnabled()
        set_algorithm(w, "Caminos mínimos", "Dijkstra")
        assert w.source.isVisible() is False or not w.isVisible()  # window not shown
        assert "costos" in w.data_help.text()
        w.calculate()
        result = json.loads(w.output.toPlainText())
        assert result["costo"] == 5.0
        assert result["ruta"] == ["1", "3", "4"]
        assert w.report_button.isEnabled()
        w.source.setText("2")
        assert not w.report_button.isEnabled()
        w.source.setText("1")
        w.calculate()
        assert json.loads(w.output.toPlainText())["costo"] == 5.0

        set_algorithm(w, "Cadenas de Markov", "Valores propios, estacionariedad y evolución")
        assert w.table.rowCount() == 2
        assert w.table.columnCount() == 2
        assert "fila" in w.data_help.text()
        w.calculate()
        result = json.loads(w.output.toPlainText())
        assert result["lambda_2"] == pytest.approx(0.7)
        assert result["converges_unique"] is True

        set_algorithm(w, "Optimización combinatoria", "Asignación óptima")
        w.set_matrix([[4,1,3],[2,0,5],[3,2,2]])
        w.columns.setValue(4)
        w.resize_matrix()
        assert w.table.rowCount() == 3
        assert w.table.columnCount() == 4
        w.table.setItem(0, 3, w.table.item(0, 0).clone())
        w.table.setItem(1, 3, w.table.item(1, 0).clone())
        w.table.setItem(2, 3, w.table.item(2, 0).clone())
        w.calculate()
        assert json.loads(w.output.toPlainText())["costo"] == 5.0

        set_algorithm(w, "Equilibrio de transporte", "Equilibrio de Wardrop: rutas paralelas")
        assert w.table.rowCount() == 2
        w.calculate()
        result = json.loads(w.output.toPlainText())
        assert sum(result["flujos"]) == pytest.approx(12)
        set_algorithm(w, "Caminos mínimos", "Dijkstra")
        assert w.table.rowCount() == 4
        assert w.table.columnCount() == 4
        w.calculate()
        assert json.loads(w.output.toPlainText())["costo"] == 5.0
    finally:
        w.close()


def test_export_latex_from_gui(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(QMessageBox, "critical", lambda _parent, _title, detail: pytest.fail(str(detail)))
    w = MainWindow()
    try:
        set_algorithm(w, "Caminos mínimos", "Dijkstra")
        w.calculate()
        assert w.report_button.isEnabled()
        monkeypatch.setattr(QInputDialog, "getText", lambda *args: ("Camino óptimo #1", True))
        monkeypatch.setattr(reports, "default_report_dir", lambda: tmp_path)
        monkeypatch.setattr(QMessageBox, "information", lambda *args: None)
        w.export_latex()
        created = tmp_path / "Camino_optimo_1.tex"
        assert created.exists()
        text = created.read_text(encoding="utf-8")
        assert "GraphNet Transport" in text
        assert "Dijkstra" in text
        assert "Desarrollador:" in text
        assert "Camino óptimo \\#1" in text
        assert "Caminos mínimos" in text
        w.export_latex()
        assert (tmp_path / "Camino_optimo_1_2.tex").exists()
    finally:
        w.close()
