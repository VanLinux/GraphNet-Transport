"""LaTeX scientific reports for every implemented GraphNet Transport algorithm.

All user-provided strings are escaped; reports do not embed raw LaTeX input.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
import unicodedata

import numpy as np

from . import __author__, __version__

_ESCAPE = {
    "\\": r"\textbackslash{}", "{": r"\{", "}": r"\}",
    "#": r"\#", "$": r"\$", "%": r"\%", "&": r"\&",
    "_": r"\_", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
    "ᵢ": r"\textsubscript{i}",
    "→": r"\ensuremath{\rightarrow}", "←": r"\ensuremath{\leftarrow}",
    "λ": r"\ensuremath{\lambda}", "π": r"\ensuremath{\pi}",
    "μ": r"\ensuremath{\mu}", "σ": r"\ensuremath{\sigma}",
    "Δ": r"\ensuremath{\Delta}", "α": r"\ensuremath{\alpha}",
    "β": r"\ensuremath{\beta}", "∞": r"\ensuremath{\infty}",
    "≥": r"\ensuremath{\geq}", "≤": r"\ensuremath{\leq}",
    "±": r"\ensuremath{\pm}", "×": r"\ensuremath{\times}",
    "–": "--", "—": "---", "•": r"\textbullet{}",
}


def escape_latex(value: object) -> str:
    """Quote all TeX special characters rather than trusting arbitrary names."""
    return "".join(_ESCAPE.get(char, char if 32 <= ord(char) <= 255 else "?") for char in str(value))


def report_filename(name: str) -> str:
    """Generate an ASCII filesystem-safe base name from the report title."""
    normalized = unicodedata.normalize("NFKD", name)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    stem = re.sub(r"[^a-zA-Z0-9_-]+", "_", ascii_name).strip("._-")[:90]
    if not stem:
        raise ValueError("Introduzca un nombre con letras o números para el reporte.")
    return stem + ".tex"


def default_report_dir() -> Path:
    """Respect the freedesktop Downloads folder (including Spanish Descargas)."""
    home = Path.home()
    user_dirs = home / ".config" / "user-dirs.dirs"
    if user_dirs.is_file():
        try:
            config = user_dirs.read_text(encoding="utf-8")
            match = re.search(r'^XDG_DOWNLOAD_DIR="([^"]+)"', config, flags=re.MULTILINE)
            if match:
                raw = match.group(1)
                if raw == "$HOME" or raw.startswith("$HOME/"):
                    target = home / raw.removeprefix("$HOME/") if raw != "$HOME" else home
                    if target.is_dir():
                        return target
        except OSError:
            pass
    for folder in ("Downloads", "Descargas"):
        target = home / folder
        if target.is_dir():
            return target
    return home


def write_report(name: str, tex: str, directory: Path | None = None) -> Path:
    """Save without overwriting an existing report; filename is from its title."""
    folder = Path(directory) if directory is not None else default_report_dir()
    folder.mkdir(parents=True, exist_ok=True)
    requested = Path(report_filename(name))
    stem = requested.stem
    for index in range(1, 10001):
        target = folder / (requested.name if index == 1 else f"{stem}_{index}.tex")
        try:
            with target.open("x", encoding="utf-8", newline="\n") as file:
                file.write(tex)
            return target
        except FileExistsError:
            continue
    raise FileExistsError("No se pudo generar un nombre de archivo único.")


def _matrix_table(matrix, row_labels=None, column_labels=None) -> str:
    data = np.asarray(matrix, dtype=object)
    if data.ndim != 2:
        raise ValueError("Los datos de entrada deben ser una matriz bidimensional.")
    rows, cols = data.shape
    max_rows, max_cols = 30, 16
    nr, nc = min(rows, max_rows), min(cols, max_cols)
    row_labels = [str(x) for x in (row_labels or [str(i + 1) for i in range(rows)])]
    column_labels = [str(x) for x in (column_labels or [str(i + 1) for i in range(cols)])]
    out = [r"\begin{center}", r"\resizebox{\linewidth}{!}{%", "\\begin{tabular}{l" + "r" * nc + "}", r"\toprule"]
    out.append(" & ".join(["Fila / columna"] + [escape_latex(x) for x in column_labels[:nc]]) + r" \\")
    out.append(r"\midrule")
    for i in range(nr):
        row = []
        for x in data[i, :nc]:
            try:
                val = float(x)
                value = format(val, ".10g") if np.isfinite(val) else "--"
            except (TypeError, ValueError):
                value = str(x)
            row.append(escape_latex(value))
        out.append(" & ".join([escape_latex(row_labels[i])] + row) + r" \\")
    out.extend([r"\bottomrule", r"\end{tabular}%", "}", r"\end{center}"])
    if rows > nr or cols > nc:
        out.append(r"\emph{Vista truncada en el reporte: " + f"{nr} de {rows} filas y {nc} de {cols} columnas" + r".}")
    return "\n".join(out)


def _result_block(value, level=0) -> str:
    if isinstance(value, dict):
        chunks = []
        for key, item in value.items():
            prefix = r"\subsection*" if level == 0 else r"\paragraph*"
            chunks.append(prefix + "{" + escape_latex(str(key).replace("_", " ")) + "}")
            chunks.append(_result_block(item, level + 1))
        return "\n".join(chunks)
    if isinstance(value, (list, tuple)):
        if value and all(isinstance(row, (list, tuple)) for row in value):
            try:
                return _matrix_table(value)
            except (ValueError, TypeError):
                pass
        if not value:
            return r"\noindent Sin elementos.\par"
        return "\n".join([r"\begin{itemize}"] + [r"\item " + _result_block(x, level + 1) for x in value] + [r"\end{itemize}"])
    if isinstance(value, float):
        value = format(value, ".12g")
    return r"\noindent " + escape_latex(value) + r"\par"


def build_latex_report(
    *, name: str, category: str, algorithm: str, description: str,
    input_help: str, matrix, results, parameters=None,
    row_labels=None, column_labels=None, generated_at=None,
) -> str:
    """Create a standalone, human-readable .tex document from the actual calculation."""
    if not name.strip():
        raise ValueError("El reporte necesita un nombre.")
    when = generated_at if generated_at is not None else datetime.now()
    doc = [
        r"\documentclass[11pt,a4paper]{article}",
        r"\usepackage[T1]{fontenc}",
        r"\usepackage[utf8]{inputenc}",
        r"\usepackage[spanish]{babel}",
        r"\usepackage{geometry,booktabs,graphicx,longtable}",
        r"\geometry{margin=2.5cm}",
        r"\setlength{\parskip}{0.5em}",
        r"\begin{document}",
        r"\begin{center}",
        r"{\LARGE\bfseries GraphNet Transport}\\[0.4em]",
        r"{\large Versión " + escape_latex(__version__) + r"}\\[0.9em]",
        r"{\Large " + escape_latex(name.strip()) + r"}\\[0.7em]",
        escape_latex(when.strftime("%Y-%m-%d %H:%M")) + r"\\",
        r"\end{center}",
        r"\section*{Identificación del cálculo}",
        r"\noindent\textbf{Categoría:} " + escape_latex(category) + r"\par",
        r"\noindent\textbf{Algoritmo:} " + escape_latex(algorithm) + r"\par",
        r"\noindent\textbf{Descripción:} " + escape_latex(description) + r"\par",
        r"\noindent\textbf{Datos requeridos:} " + escape_latex(input_help) + r"\par",
        r"\section*{Parámetros}",
    ]
    if parameters:
        for key, value in parameters.items():
            doc.append(r"\noindent\textbf{" + escape_latex(key) + "}: " + escape_latex(value) + r"\par")
    else:
        doc.append(r"\noindent Sin parámetros adicionales.\par")
    doc.extend([r"\section*{Matriz de entrada}", _matrix_table(matrix, row_labels, column_labels),
                r"\section*{Resultados}", _result_block(results),
                r"\vfill", r"\hrule", r"\smallskip",
                r"\noindent\footnotesize Desarrollador: " + escape_latex(__author__) + r".\par",
                r"\noindent\footnotesize GraphNet Transport --- Software libre, GNU GPL v3.0.\par",
                r"\end{document}"])
    return "\n".join(doc) + "\n"
