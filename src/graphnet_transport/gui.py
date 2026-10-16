"""GraphNet Transport 3.0 — scientific GUI with visual results and reports."""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QTableWidget, QTableWidgetItem, QSplitter, QGroupBox, QLabel, QLineEdit,
    QSpinBox, QCheckBox, QPushButton, QComboBox, QTextBrowser, QFileDialog,
    QMessageBox, QHeaderView, QInputDialog,
)

from . import __version__, __author__, core, reports, traversals, presentation

# Algorithm identifiers remain stable regardless of translations or grouping.
# Every entry has a short, algorithm-specific input instruction.
GROUPS = {
    "Estructura y matrices": {
        "intro": "Estudia la forma, conectividad y estructura matemática de una red.",
        "data": "Matriz cuadrada: celdas vacías = sin conexión; valores numéricos = pesos. Indique si la red es dirigida.",
        "algorithms": [
            ("Grados, conectividad y centralidad", "metrics", "Obtenga grados, componentes, densidad, centralidad, puentes y articulaciones."),
            ("Matrices de adyacencia y Laplaciana", "matrices", "Genere las matrices de adyacencia, grados, Laplaciana y alcanzabilidad."),
            ("Conectividad algebraica", "algebraic", "Requiere red NO dirigida. Calcula el segundo valor propio de la Laplaciana."),
        ],
    },
    "Recorridos de grafos": {
        "intro": "Comprueba recorridos que atraviesan cada arista o visitan cada nodo.",
        "data": "Matriz cuadrada de adyacencia: los valores numéricos indican aristas; celdas vacías = arista ausente. Seleccione red dirigida o no dirigida. El costo no afecta estas propiedades.",
        "algorithms": [
            ("Análisis euleriano", "euler", "Determina si existe circuito que utilice cada arista una vez, o solo camino euleriano abierto; devuelve el recorrido cuando existe."),
            ("Análisis hamiltoniano", "hamilton", "Busca un ciclo que visite cada nodo una vez; también identifica caminos abiertos. La decisión exacta se limita a 16 nodos, o devuelve «No determinado»."),
        ],
    },
    "Caminos mínimos": {
        "intro": "Calcula caminos óptimos y distancias entre nodos.",
        "data": "Matriz cuadrada de costos o tiempos: vacío = sin arco; 0 fuera de diagonal = conexión de costo cero.",
        "algorithms": [
            ("Dijkstra", "dijkstra", "Indique origen y destino. Los costos no pueden ser negativos."),
            ("Bellman-Ford", "bellman-ford", "Indique origen y destino. Admite arcos negativos si no hay ciclos negativos relevantes."),
            ("Floyd-Warshall", "floyd", "Calcula distancias mínimas entre todos los pares; no necesita origen ni destino."),
        ],
    },
    "Árboles de expansión": {
        "intro": "Encuentra árboles de expansión mínima en grafos no dirigidos.",
        "data": "Matriz de costos simétrica. Desmarque «Red dirigida». Las celdas vacías representan conexiones ausentes.",
        "algorithms": [
            ("Kruskal", "kruskal", "Obtiene las aristas y el costo total del árbol o bosque mínimo."),
            ("Prim", "prim", "Obtiene las aristas y el costo total del árbol o bosque mínimo."),
        ],
    },
    "Flujos y cortes": {
        "intro": "Modela capacidad y flujo a través de una red.",
        "data": "Matriz cuadrada de capacidades: introduzca valores no negativos para cada arco.",
        "algorithms": [
            ("Flujo máximo y corte mínimo", "flow", "Indique nodo fuente y sumidero. El valor en cada celda es la capacidad del arco."),
        ],
    },
    "Optimización combinatoria": {
        "intro": "Resuelve problemas de recorridos y asignación de costos.",
        "data": "El formato de la matriz cambia según el algoritmo seleccionado.",
        "algorithms": [
            ("Viajante (TSP aproximado)", "tsp", "Matriz cuadrada de distancias o costos no negativos; admite origen opcional. Resultado heurístico."),
            ("Asignación óptima", "assignment", "Matriz RECTANGULAR de costos: filas = agentes, columnas = tareas. Todas las celdas deben contener un número."),
        ],
    },
    "Equilibrio de transporte": {
        "intro": "Estudia la distribución de demanda entre rutas de transporte.",
        "data": "Dos filas: primera = tiempos libres aᵢ; segunda = pendientes bᵢ. Cada columna corresponde a una ruta.",
        "algorithms": [
            ("Equilibrio de Wardrop: rutas paralelas", "wardrop", "Introduzca demanda total y parámetros de tᵢ(xᵢ)=aᵢ+bᵢxᵢ, con aᵢ, bᵢ no negativos."),
        ],
    },
    "Redes intermodales": {
        "intro": "Examina conexiones y transbordos entre modos de transporte.",
        "data": "Importe preferentemente GraphML con atributos weight, mode y transfer. El CSV solo conserva pesos.",
        "algorithms": [
            ("Resumen intermodal", "multimodal", "Requiere atributos de modo y transferencias en GraphML para distinguirlos."),
            ("Ruta con penalización por transbordo", "intermodal_route", "Indique origen, destino y penalización por cambio de modo."),
        ],
    },
    "Cadenas de Markov": {
        "intro": "Analiza procesos estocásticos discretos y estados de un sistema.",
        "data": "Matriz de transición CUADRADA: todas las celdas entre 0 y 1, cada fila debe sumar 1.",
        "algorithms": [
            ("Valores propios, estacionariedad y evolución", "markov", "Indique el estado inicial y el número de pasos para obtener la distribución tras n transiciones."),
            ("Estados absorbentes", "absorption", "Identifica estados absorbentes, probabilidades y tiempos de absorción si existen."),
        ],
    },
}

TASKS = {label: algorithm for group in GROUPS.values() for label, algorithm, _ in group["algorithms"]}
TASK_LABELS = {algorithm: label for label, algorithm in TASKS.items()}
ALGORITHM_HELP = {algorithm: help_text for group in GROUPS.values() for _, algorithm, help_text in group["algorithms"]}


def input_mode(algorithm: str) -> str:
    if algorithm == "assignment":
        return "assignment"
    if algorithm == "wardrop":
        return "wardrop"
    if algorithm in ("markov", "absorption"):
        return "markov"
    return "graph"


def as_text(value):
    if isinstance(value, np.ndarray):
        return as_text(value.tolist())
    if isinstance(value, dict):
        return {str(k): as_text(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [as_text(x) for x in value]
    if isinstance(value, complex):
        return {"real": float(value.real), "imaginario": float(value.imag)}
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    return value


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"GraphNet Transport — v{__version__}")
        self.resize(1200, 790)
        self._graph = None
        self._graph_labels = None
        self._dirty = True
        self._result = None
        self._report_snapshot = None
        self._building = False
        self._mode = None
        self._drafts = {}
        self._init_ui()
        self._switch_mode("graph")
        self._update_task()
        self.statusBar().showMessage(f"GraphNet Transport v{__version__} · Desarrollador: {__author__}")

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(14, 12, 14, 10)
        root.setSpacing(12)
        central.setStyleSheet("""
            QWidget {font-family: 'Noto Sans', 'DejaVu Sans', sans-serif; font-size: 12px;}
            QGroupBox {font-size:13px; font-weight: 650; color:#244b70; border:1px solid #d4e0ec;
                       border-radius:8px; margin-top:13px; padding-top:13px; background:#f8fbff;}
            QGroupBox::title {subcontrol-origin:margin; left:11px; padding:0 5px;}
            QComboBox, QLineEdit, QSpinBox {padding:5px; border:1px solid #c2d3e2; border-radius:5px; background:white;}
            QPushButton {background:#e9f2fa; border:1px solid #c3d8e9; border-radius:6px; padding:7px; color:#214c72;}
            QPushButton:hover {background:#d8eafa;} QPushButton:disabled {color:#9aa7b4;}
            QTableWidget {gridline-color:#dfebf5; alternate-background-color:#f4f9fe; selection-background-color:#b6dbee;}
            QTextBrowser {background:white; border:1px solid #d8e4ee; border-radius:8px; padding:10px;}
        """)
        header = QHBoxLayout()
        title = QLabel(f"GraphNet Transport  •  v{__version__}")
        title.setStyleSheet("font-size: 20px; font-weight: 700;")
        header.addWidget(title)
        header.addStretch()
        for label, callback in [
            ("Abrir CSV", self.open_csv), ("Abrir GraphML", self.open_graphml),
            ("Guardar CSV", self.save_csv), ("Guardar GraphML", self.save_graphml),
            ("Acerca de", self.about),
        ]:
            button = QPushButton(label)
            button.clicked.connect(callback)
            if label == "Guardar GraphML":
                self.save_graphml_button = button
            header.addWidget(button)
        root.addLayout(header)

        splitter = QSplitter(Qt.Horizontal)
        root.addWidget(splitter)
        side = QWidget()
        side.setMinimumWidth(310)
        side.setMaximumWidth(410)
        controls = QVBoxLayout(side)
        group = QGroupBox("Seleccione el tipo de cálculo")
        form = QFormLayout(group)
        self.category = QComboBox()
        self.category.addItems(GROUPS)
        form.addRow("Categoría", self.category)
        self.task = QComboBox()
        form.addRow("Algoritmo", self.task)
        self.category_help = QLabel()
        self.category_help.setWordWrap(True)
        form.addRow(self.category_help)
        self.algorithm_help = QLabel()
        self.algorithm_help.setWordWrap(True)
        form.addRow(self.algorithm_help)

        self.directed = QCheckBox("Red dirigida")
        self.directed.setChecked(True)
        form.addRow(self.directed)
        self.source = QLineEdit("1")
        self.target = QLineEdit("4")
        self.source_label = QLabel("Origen")
        self.target_label = QLabel("Destino")
        form.addRow(self.source_label, self.source)
        form.addRow(self.target_label, self.target)
        self.steps = QSpinBox()
        self.steps.setRange(0, 1_000_000)
        self.steps.setValue(10)
        self.steps_label = QLabel("Pasos")
        form.addRow(self.steps_label, self.steps)
        self.demand = QLineEdit("12")
        self.demand_label = QLabel("Demanda total")
        form.addRow(self.demand_label, self.demand)
        self.penalty = QLineEdit("5")
        self.penalty_label = QLabel("Penalización de transbordo")
        form.addRow(self.penalty_label, self.penalty)
        self.run_button = QPushButton("▶ Ejecutar cálculo")
        self.run_button.setStyleSheet("background: #225d8f; color: white; padding: 12px; font-weight: bold;")
        self.run_button.clicked.connect(self.calculate)
        form.addRow(self.run_button)
        controls.addWidget(group)

        count_group = QGroupBox("Dimensiones de la matriz")
        count_layout = QHBoxLayout(count_group)
        self.row_label = QLabel("Nodos")
        self.n = QSpinBox()
        self.n.setRange(1, 500)
        self.n.setValue(4)
        self.col_label = QLabel("Columnas")
        self.columns = QSpinBox()
        self.columns.setRange(1, 500)
        self.columns.setValue(4)
        count_layout.addWidget(self.row_label)
        count_layout.addWidget(self.n)
        count_layout.addWidget(self.col_label)
        count_layout.addWidget(self.columns)
        resize_btn = QPushButton("Aplicar")
        resize_btn.clicked.connect(self.resize_matrix)
        count_layout.addWidget(resize_btn)
        controls.addWidget(count_group)
        self.data_help = QLabel()
        self.data_help.setWordWrap(True)
        self.data_help.setStyleSheet("color: #697384; padding: 6px;")
        controls.addWidget(self.data_help)
        controls.addStretch()
        splitter.addWidget(side)

        workspace = QWidget()
        workspace_layout = QVBoxLayout(workspace)
        self.matrix_title = QLabel("Matriz de entrada · doble clic para editar · Ctrl+V para pegar desde una hoja de cálculo")
        self.matrix_title.setWordWrap(True)
        workspace_layout.addWidget(self.matrix_title)
        self.table = QTableWidget(4, 4)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.itemChanged.connect(self._on_edit)
        self.paste_shortcut = QShortcut(QKeySequence.Paste, self.table)
        self.paste_shortcut.activated.connect(self.paste_matrix)
        workspace_layout.addWidget(self.table, 3)
        results_title = QHBoxLayout()
        results_title.addWidget(QLabel("Resultados"))
        results_title.addStretch()
        export_json = QPushButton("Exportar JSON")
        export_json.clicked.connect(self.export_result)
        results_title.addWidget(export_json)
        self.report_button = QPushButton("Generar informe científico (.tex)")
        self.report_button.setToolTip("Solicita un nombre y guarda un .tex en Descargas, sin sobrescribir archivos.")
        self.report_button.setEnabled(False)
        self.report_button.clicked.connect(self.export_latex)
        results_title.addWidget(self.report_button)
        workspace_layout.addLayout(results_title)
        self.output = QTextBrowser()
        self.output.setReadOnly(True)
        self.output.setOpenExternalLinks(False)
        self.output.setPlaceholderText("Seleccione un algoritmo, introduzca sus datos y ejecute el cálculo para ver un resumen visual.")
        workspace_layout.addWidget(self.output, 2)
        splitter.addWidget(workspace)
        splitter.setSizes([355, 845])

        self.category.currentTextChanged.connect(self._on_category_changed)
        self.task.currentIndexChanged.connect(self._update_task)
        self.directed.toggled.connect(self._on_edit)
        for widget in (self.source, self.target, self.demand, self.penalty):
            widget.textChanged.connect(self._on_parameters_edit)
        self.steps.valueChanged.connect(self._on_parameters_edit)
        self._on_category_changed()

    def _invalidate_result(self):
        self._result = None
        self._report_snapshot = None
        self.report_button.setEnabled(False)
        self.output.setPlainText("Los datos o el algoritmo cambiaron. Ejecute nuevamente el cálculo.")

    def _on_edit(self, *_):
        if self._building:
            return
        self._dirty = True
        self._invalidate_result()

    def _on_parameters_edit(self, *_):
        if not self._building:
            self._invalidate_result()

    def _on_category_changed(self, *_):
        group = GROUPS[self.category.currentText()]
        self.task.blockSignals(True)
        try:
            self.task.clear()
            for label, task, _ in group["algorithms"]:
                self.task.addItem(label, task)
        finally:
            self.task.blockSignals(False)
        self._update_task()

    def _snapshot_grid(self):
        return {
            "values": [[self.table.item(i, j).text() if self.table.item(i, j) else ""
                        for j in range(self.table.columnCount())] for i in range(self.table.rowCount())],
            "rows": [self.table.verticalHeaderItem(i).text() if self.table.verticalHeaderItem(i) else str(i+1)
                     for i in range(self.table.rowCount())],
            "cols": [self.table.horizontalHeaderItem(j).text() if self.table.horizontalHeaderItem(j) else str(j+1)
                     for j in range(self.table.columnCount())],
            "graph": self._graph, "dirty": self._dirty, "directed": self.directed.isChecked(),
        }

    def _set_grid(self, matrix, row_labels=None, column_labels=None, preserve_graph=False):
        a = np.asarray(matrix, dtype=float)
        if a.ndim != 2 or not a.size or a.shape[0] > 500 or a.shape[1] > 500:
            raise ValueError("La interfaz admite matrices de entre 1 y 500 filas/columnas.")
        row_labels = [str(x) for x in (row_labels if row_labels is not None else range(1, a.shape[0] + 1))]
        column_labels = [str(x) for x in (column_labels if column_labels is not None else range(1, a.shape[1] + 1))]
        self._building = True
        try:
            self.table.setRowCount(a.shape[0])
            self.table.setColumnCount(a.shape[1])
            self.n.setValue(a.shape[0])
            self.columns.setValue(a.shape[1])
            self.table.setVerticalHeaderLabels(row_labels)
            self.table.setHorizontalHeaderLabels(column_labels)
            for i in range(a.shape[0]):
                for j in range(a.shape[1]):
                    value = a[i, j]
                    self.table.setItem(i, j, QTableWidgetItem(f"{value:.12g}" if np.isfinite(value) else ""))
            self._graph_labels = row_labels if a.shape[0] == a.shape[1] else None
            self.source.setText(row_labels[0])
            self.target.setText(row_labels[-1])
            if not preserve_graph:
                self._graph = None
            self._dirty = not preserve_graph
        finally:
            self._building = False
        self._invalidate_result()

    def set_matrix(self, matrix, labels=None, preserve_graph=False):
        a = core.check_matrix(matrix)
        self._set_grid(a, labels, labels, preserve_graph=preserve_graph)

    def _restore_draft(self, snapshot):
        values = snapshot["values"]
        self._building = True
        try:
            self.table.setRowCount(len(values))
            self.table.setColumnCount(len(values[0]))
            self.table.setVerticalHeaderLabels(snapshot["rows"])
            self.table.setHorizontalHeaderLabels(snapshot["cols"])
            self.n.setValue(len(values))
            self.columns.setValue(len(values[0]))
            for i, row in enumerate(values):
                for j, value in enumerate(row):
                    self.table.setItem(i, j, QTableWidgetItem(value))
            self._graph = snapshot["graph"]
            self._dirty = snapshot["dirty"]
            self._graph_labels = snapshot["rows"] if len(values) == len(values[0]) else None
            self.directed.setChecked(snapshot["directed"])
            self.source.setText(snapshot["rows"][0])
            self.target.setText(snapshot["rows"][-1])
        finally:
            self._building = False
        self._invalidate_result()

    def _switch_mode(self, mode: str):
        if mode == self._mode:
            return
        if self._mode is not None:
            self._drafts[self._mode] = self._snapshot_grid()
        self._mode = mode
        if mode in self._drafts:
            self._restore_draft(self._drafts[mode])
        elif mode == "graph":
            self._set_grid([[0,4,2,np.nan],[np.nan,0,1,5],[np.nan,np.nan,0,3],[np.nan,np.nan,np.nan,0]])
        elif mode == "assignment":
            self._set_grid([[4,1,3],[2,0,5],[3,2,2]])
        elif mode == "wardrop":
            self._set_grid([[10,12,15],[1,0.5,0.25]], ["Tiempo libre aᵢ", "Pendiente bᵢ"], ["Ruta 1", "Ruta 2", "Ruta 3"])
        else:
            self._set_grid([[0.8,0.2],[0.1,0.9]])
        self._invalidate_result()

    def _update_task(self, *_):
        action = self.task.currentData()
        if not action:
            return
        group = GROUPS[self.category.currentText()]
        mode = input_mode(action)
        self._switch_mode(mode)
        self.category_help.setText(group["intro"])
        self.algorithm_help.setText("Algoritmo: " + ALGORITHM_HELP[action])
        self.data_help.setText("DATOS DE ENTRADA\n" + group["data"] + "\n\n" + ALGORITHM_HELP[action])
        self.matrix_title.setText({
            "graph": "Matriz de red: pesos/capacidades (vacío = sin arco). Ctrl+V para pegar.",
            "markov": "Matriz estocástica P: filas de probabilidad (suma de cada fila = 1). Ctrl+V para pegar.",
            "assignment": "Matriz de costos: filas = agentes, columnas = tareas. Ctrl+V para pegar.",
            "wardrop": "Matriz de rutas paralelas: fila 1 = aᵢ; fila 2 = bᵢ. Ctrl+V para pegar.",
        }[mode])
        show_source = action in ("dijkstra", "bellman-ford", "flow", "intermodal_route", "markov", "tsp")
        show_target = action in ("dijkstra", "bellman-ford", "flow", "intermodal_route")
        for label, widget, visible in [
            (self.source_label, self.source, show_source),
            (self.target_label, self.target, show_target),
            (self.steps_label, self.steps, action == "markov"),
            (self.demand_label, self.demand, action == "wardrop"),
            (self.penalty_label, self.penalty, action == "intermodal_route"),
        ]:
            label.setVisible(visible)
            widget.setVisible(visible)
        self.source_label.setText("Estado inicial" if action == "markov" else "Origen")
        self.directed.setVisible(mode == "graph")
        self.row_label.setText("Rutas / filas" if mode == "assignment" else "Filas" if mode == "wardrop" else "Estados" if mode == "markov" else "Nodos")
        self.col_label.setVisible(mode in ("assignment", "wardrop"))
        self.columns.setVisible(mode in ("assignment", "wardrop"))
        self.n.setEnabled(mode != "wardrop")
        self.save_graphml_button.setEnabled(mode == "graph")
        self._invalidate_result()

    def paste_matrix(self):
        text = QApplication.clipboard().text().strip("\r\n")
        if not text:
            return
        selection = self.table.selectedRanges()
        start_i = selection[0].topRow() if selection else self.table.currentRow()
        start_j = selection[0].leftColumn() if selection else self.table.currentColumn()
        start_i, start_j = max(start_i, 0), max(start_j, 0)
        for di, line in enumerate(text.replace("\r", "").split("\n")):
            delimiter = "\t" if "\t" in line else ";" if ";" in line else ","
            for dj, value in enumerate(line.split(delimiter)):
                if start_i + di < self.table.rowCount() and start_j + dj < self.table.columnCount():
                    self.table.setItem(start_i+di, start_j+dj, QTableWidgetItem(value.strip()))

    def read_matrix(self):
        rows, cols = self.table.rowCount(), self.table.columnCount()
        values = np.full((rows, cols), np.nan)
        for i in range(rows):
            for j in range(cols):
                item = self.table.item(i, j)
                content = item.text().strip().replace(",", ".") if item else ""
                if content:
                    try:
                        values[i, j] = float(content)
                    except ValueError:
                        raise ValueError(f"Valor inválido en fila {i+1}, columna {j+1}: {content}") from None
        if self._mode not in ("wardrop", "assignment"):
            return core.check_matrix(values)
        return values

    def current_graph(self):
        if not self._dirty and self._graph is not None:
            return self._graph
        return core.matrix_to_graph(self.read_matrix(), self.directed.isChecked(), self._graph_labels)

    def resize_matrix(self):
        old = self.read_matrix()
        rows = 2 if self._mode == "wardrop" else self.n.value()
        cols = self.columns.value() if self._mode in ("wardrop", "assignment") else rows
        new = np.full((rows, cols), np.nan)
        if self._mode == "graph":
            np.fill_diagonal(new, 0)
        if self._mode == "markov":
            new[:] = 1 / rows
        keep_rows, keep_cols = min(rows, old.shape[0]), min(cols, old.shape[1])
        new[:keep_rows, :keep_cols] = old[:keep_rows, :keep_cols]
        if self._mode == "wardrop":
            self._set_grid(new, ["Tiempo libre aᵢ", "Pendiente bᵢ"], [f"Ruta {j+1}" for j in range(cols)])
        else:
            labels = self._graph_labels or []
            row_labels = labels[:keep_rows] + [str(i+1) for i in range(keep_rows, rows)]
            if self._mode == "assignment":
                self._set_grid(new)
            else:
                self._set_grid(new, row_labels, row_labels)

    def _action(self, callback):
        try:
            return callback()
        except Exception as exc:
            QMessageBox.critical(self, "GraphNet Transport", str(exc))
            self.statusBar().showMessage(f"Error: {exc}", 8000)
            return None

    def open_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "Abrir matriz CSV", "", "CSV (*.csv)")
        if not path:
            return
        def load():
            if self._mode in ("assignment", "wardrop"):
                with open(path, newline="", encoding="utf-8-sig") as file:
                    rows = [[float(v) if v.strip() else np.nan for v in row]
                            for row in csv.reader(file) if any(v.strip() for v in row)]
                if not rows or any(len(row) != len(rows[0]) for row in rows):
                    raise ValueError("El CSV debe tener filas del mismo tamaño.")
                if self._mode == "wardrop":
                    if len(rows) != 2:
                        raise ValueError("Wardrop requiere exactamente dos filas (aᵢ y bᵢ).")
                    self._set_grid(rows, ["Tiempo libre aᵢ", "Pendiente bᵢ"],
                                   [f"Ruta {i+1}" for i in range(len(rows[0]))])
                else:
                    self._set_grid(rows)
            else:
                self.set_matrix(core.load_csv(path))
        self._action(load)

    def open_graphml(self):
        path, _ = QFileDialog.getOpenFileName(self, "Abrir GraphML confiable", "", "GraphML (*.graphml)")
        if not path:
            return
        def load():
            if self._mode != "graph":
                self.category.setCurrentText("Estructura y matrices")
            G = core.load_graphml(path)
            matrix, labels = core.graph_to_matrix(G)
            self._building = True
            self.directed.setChecked(G.is_directed())
            self._building = False
            self._graph = G
            self.set_matrix(matrix, labels, preserve_graph=True)
            self.output.setPlainText("GraphML importado. Se preservan atributos hasta editar la matriz. "
                                     "Los arcos paralelos se reducen al peso mínimo en la vista tabular.")
        self._action(load)

    def save_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Guardar matriz CSV", "red.csv", "CSV (*.csv)")
        if not path:
            return
        def save():
            if self._mode not in ("assignment", "wardrop"):
                core.save_csv(path, self.read_matrix())
                return
            with open(path, "w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                for row in self.read_matrix():
                    writer.writerow([format(x, ".12g") if np.isfinite(x) else "" for x in row])
        self._action(save)

    def save_graphml(self):
        if self._mode != "graph":
            QMessageBox.information(self, "GraphNet Transport", "GraphML solo está disponible para redes.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Guardar red GraphML", "red.graphml", "GraphML (*.graphml)")
        if path:
            self._action(lambda: core.save_graphml(path, self.current_graph()))

    def _source_index(self):
        labels = self._graph_labels or [str(i+1) for i in range(self.table.rowCount())]
        source = self.source.text().strip()
        if source not in labels:
            raise ValueError("El estado inicial debe coincidir con una etiqueta de fila.")
        return labels.index(source)

    def _parameters(self, action):
        params = {}
        if action in ("dijkstra", "bellman-ford", "flow", "intermodal_route", "tsp", "markov"):
            params["Origen / estado inicial"] = self.source.text().strip()
        if action in ("dijkstra", "bellman-ford", "flow", "intermodal_route"):
            params["Destino"] = self.target.text().strip()
        if action == "markov":
            params["Pasos"] = self.steps.value()
        if action == "wardrop":
            params["Demanda"] = self.demand.text().strip()
        if action == "intermodal_route":
            params["Penalización de transbordo"] = self.penalty.text().strip()
        if self._mode == "graph":
            params["Red dirigida"] = "Sí" if self.directed.isChecked() else "No"
        return params

    def calculate(self):
        def run():
            action = self.task.currentData()
            matrix = self.read_matrix()
            if action in ("markov", "absorption"):
                if action == "markov":
                    result = core.markov_analysis(matrix, self.steps.value(),
                        initial=np.eye(len(matrix))[self._source_index()])
                else:
                    result = core.absorbing_chain(matrix)
            elif action == "assignment":
                result = core.assignment(matrix)
            elif action == "wardrop":
                if matrix.shape[0] != 2 or not np.all(np.isfinite(matrix)):
                    raise ValueError("Wardrop necesita dos filas completas de tiempos libres y pendientes.")
                result = core.wardrop_parallel(matrix[0], matrix[1], float(self.demand.text()))
            else:
                G = self.current_graph()
                src, tgt = self.source.text().strip(), self.target.text().strip()
                if action == "metrics": result = core.network_metrics(G)
                elif action == "matrices": result = core.graph_matrices(G)
                elif action == "algebraic": result = {"lambda_2": core.algebraic_connectivity(G)}
                elif action in ("dijkstra", "bellman-ford"): result = core.shortest_path(G, src, tgt, action)
                elif action == "floyd": result = core.all_pairs(G)
                elif action == "euler": result = traversals.euler_analysis(G)
                elif action == "hamilton": result = traversals.hamilton_analysis(G)
                elif action in ("kruskal", "prim"): result = core.spanning_tree(G, action)
                elif action == "flow": result = core.maximum_flow(G, src, tgt)
                elif action == "tsp": result = core.approximate_tsp(G, src if src in G else None)
                elif action == "multimodal": result = core.multimodal_summary(G)
                elif action == "intermodal_route": result = core.intermodal_shortest_path(G, src, tgt, float(self.penalty.text()))
                else: raise ValueError("Operación no implementada.")
            self._result = as_text(result)
            self._report_snapshot = {
                "category": self.category.currentText(),
                "algorithm": self.task.currentText(),
                "description": ALGORITHM_HELP[action],
                "input_help": GROUPS[self.category.currentText()]["data"],
                "matrix": matrix.copy(),
                "row_labels": [self.table.verticalHeaderItem(i).text() for i in range(self.table.rowCount())],
                "column_labels": [self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount())],
                "parameters": self._parameters(action),
                "results": self._result,
            }
            self.report_button.setEnabled(True)
            self.output.setHtml(presentation.render_result(self.category.currentText(), self.task.currentText(), self._result))
            self.statusBar().showMessage(f"Cálculo completado: {self.task.currentText()}", 7000)
        self._action(run)

    def export_result(self):
        if self._result is None:
            QMessageBox.information(self, "GraphNet Transport", "Primero ejecute un cálculo.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Exportar resultados", "resultado.json", "JSON (*.json)")
        if path:
            self._action(lambda: Path(path).write_text(
                json.dumps(self._result, indent=2, ensure_ascii=False), encoding="utf-8"))

    def export_latex(self):
        """The only required user input is the report's name."""
        if self._report_snapshot is None:
            QMessageBox.information(self, "GraphNet Transport", "Primero ejecute un cálculo.")
            return
        name, accepted = QInputDialog.getText(self, "Nuevo reporte .tex", "Nombre del reporte:")
        if not accepted:
            return
        if not name.strip():
            QMessageBox.warning(self, "GraphNet Transport", "Introduzca un nombre para el reporte.")
            return
        def generate():
            document = reports.build_latex_report(name=name, **self._report_snapshot)
            path = reports.write_report(name, document)
            QMessageBox.information(self, "Reporte LaTeX generado", f"Archivo guardado en:\n{path}")
            self.statusBar().showMessage(f"Reporte .tex generado: {path}", 12000)
        self._action(generate)

    def about(self):
        QMessageBox.about(self, "Acerca de GraphNet Transport",
            f"<h3>GraphNet Transport — versión {__version__}</h3>"
            "<p>Teoría de grafos, optimización de redes y cadenas de Markov.</p>"
            f"<p><b>Desarrollador:</b> {__author__}</p>"
            "<p>Software libre · GNU GPL v3.0</p>")


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
