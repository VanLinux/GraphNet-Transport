# Registro de cambios

## 3.1.0 — 2026-10-16

- Corregida la interpretación de ceros en matrices de adyacencia: un 0 indica ausencia de conexión, con modo seleccionable para preservar arcos de peso cero.
- Validación de simetría para matrices de redes no dirigidas.
- Rediseño de las salidas de grados, densidad y conectividad: resúmenes y tablas en vez de listados extensos.
- Conteo exacto de recorridos mediante potencias de la matriz de adyacencia y de caminos simples mediante programación dinámica (hasta 16 nodos).
- Parámetros específicos de longitud y clase de recorrido, con ejemplo de ruta cuando existe.
- Informes .tex compactos en papel carta, con tablas, sustitución numérica de densidad, modelo matemático, interpretación, diagrama coherente con las aristas calculadas y créditos en pie de página.
- Añadido caso de referencia de cuatro estaciones y pruebas de coherencia para grafos dirigidos/no dirigidos y convenios de ceros.

## 3.0.0 — 2026-10-16

- Añadidos los análisis euleriano (circuitos/caminos) y hamiltoniano (ciclos/caminos) sobre redes dirigidas y no dirigidas.
- Prueba hamiltoniana exacta para hasta 16 nodos y estado explícito «No determinado» para redes mayores.
- Panel de resultados visual con indicadores, tablas y rutas destacadas en lugar de JSON sin formato.
- Informes LaTeX en papel carta, con diseño científico, formulación matemática, gráficos TikZ y arcos de solución coloreados.
- Ampliadas las pruebas de teoría de grafos, interfaz, representación HTML y generación LaTeX.

## 2.0.0 — 2026-10-16

- Se reorganizaron 16 algoritmos y cálculos en ocho categorías temáticas.
- Se añadieron explicaciones de datos de entrada y parámetros específicos por algoritmo.
- El editor permite matrices rectangulares para asignación y tablas de dos filas para Wardrop.
- La interfaz conserva matrices y atributos importados al cambiar entre modalidades.
- Se incorporó la exportación de reportes LaTeX (.tex) por operación, con nombre solicitado al usuario, datos y resultados de la ejecución, créditos y nombres de archivo únicos.
- Se mantuvo la exportación JSON y se añadieron pruebas automáticas del generador de informes y de la interacción GUI.

## 1.0.0 — 2026-10-16

- Versión inicial del editor matricial, algoritmos de grafos, transporte y cadenas de Markov.
