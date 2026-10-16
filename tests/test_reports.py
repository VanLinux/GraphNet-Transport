import numpy as np
import pytest
from graphnet_transport.reports import (escape_latex, report_filename, build_latex_report, write_report)


def test_safe_filename_and_escaping():
    assert report_filename("Diagnóstico de conexión #1") == "Diagnostico_de_conexion_1.tex"
    assert report_filename("../../report\\bad") == "report_bad.tex"
    with pytest.raises(ValueError):
        report_filename("...!!!")
    assert escape_latex(r"&%$_{}#~^\\") == r"\&\%\$\_\{\}\#\textasciitilde{}\textasciicircum{}\textbackslash{}\textbackslash{}"


def test_latex_includes_inputs_results_and_metadata(tmp_path):
    tex = build_latex_report(
        name="Ensayo A_1%", category="Caminos mínimos", algorithm="Dijkstra",
        description="Ruta con costo mínimo", input_help="Arcos vacíos = sin conexión",
        matrix=np.array([[0, 2], [np.nan, 0]]),
        row_labels=["a_1", "b#2"], column_labels=["a_1", "b#2"],
        parameters={"Origen": "a_1", "Destino": "b#2"},
        results={"costo": 2.0, "ruta": ["a_1", "b#2"]},
    )
    assert r"\documentclass" in tex
    assert r"Ensayo A\_1\%" in tex
    assert r"a\_1" in tex
    assert r"b\#2" in tex
    assert "costo" in tex and "\n2\n" not in tex
    assert "Héctor Alonso Benítez García" in tex
    assert "Versión 3.0.0" in tex
    path = write_report("Ensayo A_1%", tex, tmp_path)
    assert path.exists()
    second = write_report("Ensayo A_1%", tex, tmp_path)
    assert second != path
    assert second.read_text(encoding="utf-8") == tex


def test_report_large_matrix_truncated_with_notice():
    tex = build_latex_report(
        name="Matriz", category="Estructura", algorithm="Matrices",
        description="Cálculo", input_help="Cuadrada",
        matrix=np.zeros((31, 17)), results={"matriz": np.zeros((2, 2)).tolist()}
    )
    assert "Vista truncada" in tex
    assert "30 de 31 filas" in tex
