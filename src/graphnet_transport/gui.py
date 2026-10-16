"""GraphNet Transport desktop application (Spanish interface)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QTableWidget, QTableWidgetItem, QSplitter, QGroupBox, QLabel, QLineEdit,
    QSpinBox, QCheckBox, QPushButton, QComboBox, QPlainTextEdit, QFileDialog,
    QMessageBox, QHeaderView, QAbstractItemView
)

from . import __version__, __author__
from . import core

TASKS = {
    "Estructura y conectividad": "metrics",
    "Matrices de la red": "matrices",
    "Conectividad algebraica": "algebraic",
    "Camino mínimo: Dijkstra": "dijkstra",
    "Camino mínimo: Bellman-Ford": "bellman-ford",
    "Todos los caminos: Floyd-Warshall": "floyd",
    "Árbol mínimo: Kruskal": "kruskal",
    "Árbol mínimo: Prim": "prim",
    "Flujo máximo y corte mínimo": "flow",
    "Viajante (TSP, aproximación)": "tsp",
    "Asignación óptima": "assignment",
    "Equilibrio Wardrop (rutas paralelas)": "wardrop",
    "Resumen intermodal": "multimodal",
    "Ruta intermodal (cambio de modo)": "intermodal_route",
    "Markov: valores propios y evolución": "markov",
    "Markov: estados absorbentes": "absorption",
}


def as_text(value):
    if isinstance(value, np.ndarray):
        return as_text(value.tolist())
    if isinstance(value, dict):
        return {str(k): as_text(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [as_text(x) for x in value]
    if isinstance(value, complex):
        return {"real": float(value.real), "imaginario": float(value.imag)}
    if isinstance(value, (np.integer,)): return int(value)
    if isinstance(value, (np.floating,)): return float(value)
    return value


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"GraphNet Transport — v{__version__}")
        self.resize(1180, 750)
        self._graph = None
        self._graph_labels = None
        self._dirty = True
        self._result = None
        self._building = False
        self._init_ui()
        self.set_matrix(np.array([[0,4,2,np.nan],[np.nan,0,1,5],[np.nan,np.nan,0,3],[np.nan,np.nan,np.nan,0]], dtype=float))
        self.statusBar().showMessage(f"GraphNet Transport v{__version__} · Desarrollador: {__author__}")

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        header = QHBoxLayout()
        title = QLabel(f"GraphNet Transport  •  v{__version__}")
        title.setStyleSheet("font-size: 20px; font-weight: 700;")
        header.addWidget(title)
        header.addStretch()
        for label, callback in [
            ("Abrir CSV", self.open_csv), ("Abrir GraphML", self.open_graphml),
            ("Guardar CSV", self.save_csv), ("Guardar GraphML", self.save_graphml),
            ("Acerca de", self.about)
        ]:
            button=QPushButton(label); button.clicked.connect(callback); header.addWidget(button)
        root.addLayout(header)
        splitter=QSplitter(Qt.Horizontal)
        root.addWidget(splitter)
        side=QWidget(); side.setMinimumWidth(275); side.setMaximumWidth(360)
        controls=QVBoxLayout(side)
        group=QGroupBox("Análisis")
        form=QFormLayout(group)
        self.task=QComboBox(); self.task.addItems(TASKS)
        form.addRow("Operación",self.task)
        self.directed=QCheckBox("Red dirigida"); self.directed.setChecked(True)
        form.addRow(self.directed)
        self.source=QLineEdit("1"); self.target=QLineEdit("4")
        self.source.setPlaceholderText("Nodo inicial / fuente")
        self.target.setPlaceholderText("Nodo final / sumidero")
        form.addRow("Origen",self.source); form.addRow("Destino",self.target)
        self.steps=QSpinBox(); self.steps.setRange(0,1_000_000); self.steps.setValue(10)
        form.addRow("Pasos Markov",self.steps)
        self.demand=QLineEdit("100")
        form.addRow("Demanda Wardrop",self.demand)
        self.penalty=QLineEdit("5")
        form.addRow("Penal. transbordo",self.penalty)
        self.slopes=QLineEdit("0.5, 0.2, 0.3, 0.1")
        self.slopes.setToolTip("Pendiente b_i de t_i=a_i+b_i·x_i. Los tiempos libres se toman de la primera fila.")
        form.addRow("Pendientes",self.slopes)
        self.run_button=QPushButton("▶ Ejecutar cálculo")
        self.run_button.setStyleSheet("background: #225d8f; color: white; padding: 12px; font-weight: bold;")
        self.run_button.clicked.connect(self.calculate)
        form.addRow(self.run_button)
        controls.addWidget(group)
        count_group=QGroupBox("Editor de matrices")
        count_layout=QHBoxLayout(count_group)
        self.n=QSpinBox(); self.n.setRange(1,500); self.n.setValue(4)
        count_layout.addWidget(QLabel("Nodos:")); count_layout.addWidget(self.n)
        resize_btn=QPushButton("Redimensionar"); resize_btn.clicked.connect(self.resize_matrix)
        count_layout.addWidget(resize_btn)
        controls.addWidget(count_group)
        notes=QLabel("Entrada: celdas vacías = sin arco.\n"
                     "Un 0 fuera de la diagonal = arco de costo cero.\n"
                     "Markov: todas las celdas deben contener\nprobabilidades y cada fila sumar 1.\n\n"
                     "Para Wardrop: la primera fila contiene\nlos tiempos libres de cada ruta.")
        notes.setWordWrap(True)
        notes.setStyleSheet("color: #6b7280; font-size: 11px;")
        controls.addWidget(notes)
        controls.addStretch()
        splitter.addWidget(side)
        workspace=QWidget(); workspace_layout=QVBoxLayout(workspace)
        workspace_layout.addWidget(QLabel("Matriz de entrada (doble clic para editar; Ctrl+V para pegado manual no integrado)"))
        self.table=QTableWidget(4,4)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.itemChanged.connect(self._on_edit)
        workspace_layout.addWidget(self.table,3)
        results_title=QHBoxLayout()
        results_title.addWidget(QLabel("Resultados")); results_title.addStretch()
        export=QPushButton("Exportar resultado JSON"); export.clicked.connect(self.export_result)
        results_title.addWidget(export)
        workspace_layout.addLayout(results_title)
        self.output=QPlainTextEdit(); self.output.setReadOnly(True)
        self.output.setPlaceholderText("Seleccione un análisis y pulse Ejecutar cálculo.")
        workspace_layout.addWidget(self.output,2)
        splitter.addWidget(workspace)
        splitter.setSizes([300,880])
        self.task.currentIndexChanged.connect(self._update_task)
        self._update_task()

    def _on_edit(self):
        if not self._building:
            self._dirty=True

    def _update_task(self):
        task=TASKS[self.task.currentText()]
        self.steps.setEnabled(task in ("markov",))
        self.demand.setEnabled(task=="wardrop")
        self.penalty.setEnabled(task=="intermodal_route")
        self.slopes.setEnabled(task=="wardrop")
        self.target.setEnabled(task in ("dijkstra","bellman-ford","flow","intermodal_route"))
        self.source.setEnabled(task in ("dijkstra","bellman-ford","flow","markov","tsp","intermodal_route"))

    def set_matrix(self, matrix, labels=None, preserve_graph=False):
        a=core.check_matrix(matrix)
        if len(a)>500:
            raise ValueError("La interfaz admite como máximo 500 nodos (el motor permite más).")
        self._building=True
        try:
            self.table.setRowCount(len(a)); self.table.setColumnCount(len(a)); self.n.setValue(len(a))
            labels=[str(x) for x in (labels if labels is not None else range(1,len(a)+1))]
            self._graph_labels=labels
            self.table.setHorizontalHeaderLabels(labels); self.table.setVerticalHeaderLabels(labels)
            for i in range(len(a)):
                for j in range(len(a)):
                    v=a[i,j]
                    self.table.setItem(i,j,QTableWidgetItem(f"{v:.12g}" if np.isfinite(v) else ""))
            self.source.setText(labels[0]); self.target.setText(labels[-1])
            if not preserve_graph: self._graph=None
            self._dirty=not preserve_graph
        finally:
            self._building=False

    def read_matrix(self):
        n=self.table.rowCount()
        values=np.full((n,n),np.nan)
        for i in range(n):
            for j in range(n):
                item=self.table.item(i,j)
                text=item.text().strip().replace(",", ".") if item else ""
                if text:
                    try: values[i,j]=float(text)
                    except ValueError: raise ValueError(f"Valor inválido en fila {i+1}, columna {j+1}: {text}") from None
        return core.check_matrix(values)

    def current_graph(self):
        if not self._dirty and self._graph is not None:
            return self._graph
        return core.matrix_to_graph(self.read_matrix(), self.directed.isChecked(), self._graph_labels)

    def resize_matrix(self):
        old=self.read_matrix(); n=self.n.value()
        new=np.full((n,n), np.nan)
        np.fill_diagonal(new,0)
        k=min(n,len(old)); new[:k,:k]=old[:k,:k]
        labels=(self._graph_labels[:k] if self._graph_labels else [str(j+1) for j in range(k)])
        labels+= [str(j+1) for j in range(k,n)]
        self.set_matrix(new, labels=labels)

    def _action(self, callback):
        try: callback()
        except Exception as exc:
            QMessageBox.critical(self,"GraphNet Transport",str(exc))
            self.statusBar().showMessage(f"Error: {exc}",8000)

    def open_csv(self):
        path,_=QFileDialog.getOpenFileName(self,"Abrir matriz CSV","","CSV (*.csv)")
        if path: self._action(lambda:self.set_matrix(core.load_csv(path)))

    def open_graphml(self):
        path,_=QFileDialog.getOpenFileName(self,"Abrir red GraphML confiable","","GraphML (*.graphml)")
        if not path: return
        def load():
            G=core.load_graphml(path)
            matrix,labels=core.graph_to_matrix(G)
            self.directed.setChecked(G.is_directed())
            self._graph=G
            self.set_matrix(matrix,labels,preserve_graph=True)
            self.output.setPlainText("GraphML importado. Los atributos y arcos paralelos se conservan hasta que se edite la matriz. La vista matricial reduce arcos paralelos al peso mínimo.")
        self._action(load)

    def save_csv(self):
        path,_=QFileDialog.getSaveFileName(self,"Guardar matriz CSV","red.csv","CSV (*.csv)")
        if path: self._action(lambda:core.save_csv(path,self.read_matrix()))

    def save_graphml(self):
        path,_=QFileDialog.getSaveFileName(self,"Guardar red GraphML","red.graphml","GraphML (*.graphml)")
        if path: self._action(lambda:core.save_graphml(path,self.current_graph()))

    def calculate(self):
        def calculate_inner():
            action=TASKS[self.task.currentText()]
            matrix=self.read_matrix()
            if action in ("markov","absorption"):
                if action=="markov":
                    result=core.markov_analysis(matrix,self.steps.value(),
                        initial=np.eye(len(matrix))[self._source_index()])
                else: result=core.absorbing_chain(matrix)
            elif action=="assignment":
                result=core.assignment(matrix)
            elif action=="wardrop":
                slopes=[float(v.strip()) for v in self.slopes.text().split(",")]
                result=core.wardrop_parallel(matrix[0],slopes,float(self.demand.text()))
            else:
                G=self.current_graph()
                src=self.source.text().strip(); tgt=self.target.text().strip()
                if action=="metrics": result=core.network_metrics(G)
                elif action=="matrices": result=core.graph_matrices(G)
                elif action=="algebraic": result={"lambda_2":core.algebraic_connectivity(G)}
                elif action in ("dijkstra","bellman-ford"):
                    result=core.shortest_path(G,src,tgt,action)
                elif action=="floyd": result=core.all_pairs(G)
                elif action in ("kruskal","prim"): result=core.spanning_tree(G,action)
                elif action=="flow": result=core.maximum_flow(G,src,tgt)
                elif action=="tsp": result=core.approximate_tsp(G,src if src in G else None)
                elif action=="multimodal": result=core.multimodal_summary(G)
                elif action=="intermodal_route": result=core.intermodal_shortest_path(G,src,tgt,float(self.penalty.text()))
                else: raise ValueError("Operación no implementada.")
            self._result=as_text(result)
            self.output.setPlainText(json.dumps(self._result,indent=2,ensure_ascii=False,allow_nan=True))
            self.statusBar().showMessage(f"Cálculo completado: {self.task.currentText()}",7000)
        self._action(calculate_inner)

    def _source_index(self):
        labels=self._graph_labels or [str(i+1) for i in range(self.table.rowCount())]
        src=self.source.text().strip()
        if src not in labels:
            raise ValueError("El estado inicial debe corresponder a una etiqueta de fila.")
        return labels.index(src)

    def export_result(self):
        if self._result is None:
            QMessageBox.information(self,"GraphNet Transport","Primero ejecute un cálculo.")
            return
        path,_=QFileDialog.getSaveFileName(self,"Exportar resultados","resultado.json","JSON (*.json)")
        if path:
            self._action(lambda:Path(path).write_text(json.dumps(self._result,indent=2,ensure_ascii=False),encoding="utf-8"))

    def about(self):
        QMessageBox.about(self,"Acerca de GraphNet Transport",
            f"<h3>GraphNet Transport — versión {__version__}</h3>"
            "<p>Teoría de grafos, optimización de redes y cadenas de Markov.</p>"
            f"<p><b>Desarrollador:</b> {__author__}</p>"
            "<p>Software libre · GNU GPL v3.0</p>")


def main():
    app=QApplication(sys.argv)
    app.setStyle("Fusion")
    window=MainWindow(); window.show()
    sys.exit(app.exec())
