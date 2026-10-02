"""Sistema de inferencia difusa (Mamdani) para evaluar el riesgo de infarto.

Entradas: edad (años) y peso (kg). Salida: riesgo de 0 a 10 (centroide).
El archivo se divide en tres bloques independientes:
    1. Lógica difusa   -> universos, conjuntos, reglas y `evaluar_riesgo`.
    2. Visualización   -> figura 2x2 con tema claro (sin depender de tkinter).
    3. Interfaz        -> ventana tkinter que une los dos bloques anteriores.
"""

import math
import tkinter as tk
from tkinter import ttk

import numpy as np
import skfuzzy as fuzz
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.figure import Figure
from skfuzzy import control as ctrl

# =============================================================================
# 1. LÓGICA DIFUSA
# =============================================================================

# Rangos y resolución de cada universo de discurso: (mínimo, máximo, paso).
RANGO_EDAD = (0, 100, 0.1)
RANGO_PESO = (30, 180, 0.1)
RANGO_RIESGO = (0, 10, 0.01)

# Parámetros de las funciones de pertenencia: 4 valores = trapmf, 3 = trimf.
CONJUNTOS_EDAD = {
    "Joven": [0, 0, 20, 32],
    "Adulto Joven": [26, 37, 48],
    "Adulto Maduro": [43, 54, 65],
    "Mayor": [58, 68, 78],
    "Anciano": [72, 82, 100, 100],
}
CONJUNTOS_PESO = {  # categorías IMC de la OMS
    "Bajo Peso": [30, 30, 48, 62],
    "Saludable": [55, 68, 82],
    "Sobrepeso": [76, 90, 104],
    "Obesidad 1": [98, 112, 126],
    "Obesidad 2": [118, 132, 180, 180],
}
CONJUNTOS_RIESGO = {
    "Muy Bajo": [0, 0, 1, 2.5],
    "Bajo": [1.5, 3, 4.5],
    "Moderado": [3.5, 5, 6.5],
    "Alto": [5.5, 7, 8.5],
    "Muy Alto": [7.5, 9, 10, 10],
}

# Matriz de reglas 5x5: para cada peso, el riesgo según la edad
# (en el orden Joven, Adulto Joven, Adulto Maduro, Mayor, Anciano).
MATRIZ_REGLAS = {
    "Bajo Peso": ("Bajo", "Bajo", "Moderado", "Alto", "Alto"),
    "Saludable": ("Muy Bajo", "Muy Bajo", "Bajo", "Moderado", "Moderado"),
    "Sobrepeso": ("Bajo", "Moderado", "Alto", "Alto", "Muy Alto"),
    "Obesidad 1": ("Moderado", "Alto", "Muy Alto", "Muy Alto", "Muy Alto"),
    "Obesidad 2": ("Moderado", "Alto", "Muy Alto", "Muy Alto", "Muy Alto"),
}


def _universo(minimo, maximo, paso):
    """Crea un universo uniforme que incluye exactamente ambos extremos."""
    return np.linspace(minimo, maximo, round((maximo - minimo) / paso) + 1)


def _definir_conjuntos(variable, definiciones):
    """Asigna a `variable` un conjunto difuso (trapezoidal o triangular) por nombre."""
    for nombre, parametros in definiciones.items():
        funcion = fuzz.trapmf if len(parametros) == 4 else fuzz.trimf
        variable[nombre] = funcion(variable.universe, parametros)


EDAD = ctrl.Antecedent(_universo(*RANGO_EDAD), "edad")
PESO = ctrl.Antecedent(_universo(*RANGO_PESO), "peso")
RIESGO = ctrl.Consequent(_universo(*RANGO_RIESGO), "riesgo", defuzzify_method="centroid")
_definir_conjuntos(EDAD, CONJUNTOS_EDAD)
_definir_conjuntos(PESO, CONJUNTOS_PESO)
_definir_conjuntos(RIESGO, CONJUNTOS_RIESGO)

# SI edad Y peso ENTONCES riesgo, generadas a partir de la matriz.
REGLAS = [
    ctrl.Rule(EDAD[edad] & PESO[peso], RIESGO[riesgo])
    for peso, fila in MATRIZ_REGLAS.items()
    for edad, riesgo in zip(CONJUNTOS_EDAD, fila)
]
SISTEMA = ctrl.ControlSystem(REGLAS)


def evaluar_riesgo(edad, peso):
    """Devuelve el riesgo de infarto (0-10) para una edad (años) y un peso (kg)."""
    simulacion = ctrl.ControlSystemSimulation(SISTEMA)
    simulacion.input["edad"] = edad
    simulacion.input["peso"] = peso
    simulacion.compute()
    return float(simulacion.output["riesgo"])


def conjunto_dominante(variable, valor):
    """Devuelve (nombre, grado) del conjunto con mayor pertenencia en `valor`."""
    grados = {
        nombre: fuzz.interp_membership(variable.universe, termino.mf, valor)
        for nombre, termino in variable.terms.items()
    }
    nombre = max(grados, key=grados.get)
    return nombre, float(grados[nombre])


# =============================================================================
# 2. VISUALIZACIÓN
# =============================================================================

# Paleta clínica: blanco y azul. Edad y peso usan tonos azules/turquesa; el riesgo
# conserva el semáforo verde -> rojo para que se lea de un vistazo.
COLOR_FONDO = "#eef5fb"
COLOR_PANEL = "#ffffff"
COLOR_TEXTO = "#12304d"
COLOR_TEXTO_SUAVE = "#5f7a94"
COLOR_REJILLA = "#d3e2f0"

COLORES_EDAD = ["#26c6da", "#1e88e5", "#3949ab", "#7e57c2", "#1a237e"]
COLORES_PESO = ["#4dd0e1", "#26a69a", "#1976d2", "#5c6bc0", "#0d47a1"]
COLORES_RIESGO = ["#2e9e5b", "#7cb342", "#f9a825", "#ef6c00", "#d32f2f"]
CENTROS_RIESGO = (1, 3, 5, 7, 9)  # centro de cada nivel en la barra del panel final

# Gradiente verde -> rojo; cada color queda centrado bajo el nombre de su nivel.
MAPA_RIESGO = LinearSegmentedColormap.from_list(
    "riesgo",
    [(0, COLORES_RIESGO[0])]
    + [(c / RANGO_RIESGO[1], col) for c, col in zip(CENTROS_RIESGO, COLORES_RIESGO)]
    + [(1, COLORES_RIESGO[-1])],
)


def _estilo_ejes(ax, titulo):
    """Aplica el tema claro a unos ejes."""
    ax.set_facecolor(COLOR_PANEL)
    ax.set_title(titulo, color=COLOR_TEXTO, fontsize=11, fontweight="bold")
    ax.tick_params(colors=COLOR_TEXTO_SUAVE, labelsize=8)
    ax.grid(color=COLOR_REJILLA, alpha=0.5, linewidth=0.6)
    for borde in ax.spines.values():
        borde.set_color(COLOR_REJILLA)


def _graficar_conjuntos(ax, variable, colores, titulo, etiqueta_x, valor,
                        marcar_dominante=True, etiqueta_valor=None):
    """Dibuja los conjuntos de `variable` y una línea blanca discontinua en `valor`.

    Con `marcar_dominante` añade el punto y el grado del conjunto dominante.
    """
    _estilo_ejes(ax, titulo)
    x = variable.universe
    colores_por_nombre = dict(zip(variable.terms, colores))
    for nombre, termino in variable.terms.items():
        color = colores_por_nombre[nombre]
        ax.plot(x, termino.mf, color=color, linewidth=2, label=nombre)
        ax.fill_between(x, termino.mf, color=color, alpha=0.15)

    ax.axvline(valor, color=COLOR_TEXTO, linestyle="--", linewidth=1.5, label=etiqueta_valor)

    if marcar_dominante:
        nombre, grado = conjunto_dominante(variable, valor)
        color = colores_por_nombre[nombre]
        ax.hlines(grado, x[0], valor, colors=color, linestyles=":", linewidth=1.3)
        ax.plot(valor, grado, "o", color=color, markersize=8,
                markeredgecolor=COLOR_PANEL, markeredgewidth=1.5, zorder=5)
        a_la_derecha = valor < x[0] + 0.8 * (x[-1] - x[0])
        ax.annotate(f"{grado:.2f}", (valor, grado), color=COLOR_TEXTO, fontweight="bold",
                    fontsize=9, xytext=(7 if a_la_derecha else -7, 7),
                    textcoords="offset points", ha="left" if a_la_derecha else "right")

    ax.set_xlim(x[0], x[-1])
    ax.set_ylim(0, 1.4)  # espacio libre arriba para la leyenda
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1])
    ax.set_xlabel(etiqueta_x, color=COLOR_TEXTO_SUAVE, fontsize=9)
    ax.set_ylabel("Pertenencia", color=COLOR_TEXTO_SUAVE, fontsize=9)
    ax.legend(loc="upper center", ncol=3, fontsize=8, facecolor=COLOR_FONDO,
              edgecolor=COLOR_REJILLA, labelcolor=COLOR_TEXTO)


def _graficar_resultado(ax, riesgo):
    """Panel final: barra verde-rojo con flecha, puntaje y nivel de riesgo."""
    nivel, _ = conjunto_dominante(RIESGO, riesgo)
    color = dict(zip(RIESGO.terms, COLORES_RIESGO))[nivel]
    maximo = RANGO_RIESGO[1]

    ax.set_facecolor(COLOR_PANEL)
    ax.set_title("Resultado del Paciente", color=COLOR_TEXTO, fontsize=11, fontweight="bold")
    ax.axis("off")

    ax.imshow(np.linspace(0, 1, 256).reshape(1, -1), cmap=MAPA_RIESGO, aspect="auto",
              extent=(0, maximo, 4.4, 5.4))
    for nombre, centro, col in zip(RIESGO.terms, CENTROS_RIESGO, COLORES_RIESGO):
        ax.text(centro, 5.7, nombre, color=col, ha="center", va="bottom",
                fontsize=9, fontweight="bold")
    ax.text(-0.4, 4.9, "0", color=COLOR_TEXTO_SUAVE, ha="center", va="center", fontsize=9)
    ax.text(maximo + 0.4, 4.9, "10", color=COLOR_TEXTO_SUAVE, ha="center", va="center", fontsize=9)
    ax.annotate("", xy=(riesgo, 4.35), xytext=(riesgo, 3.2),
                arrowprops=dict(arrowstyle="-|>", color=COLOR_TEXTO, linewidth=2.5, mutation_scale=22))

    ax.text(maximo / 2, 2.1, f"{riesgo:.2f} / 10", color=color, ha="center", va="center",
            fontsize=30, fontweight="bold")
    ax.text(maximo / 2, 0.8, nivel.capitalize(), color=color, ha="center", va="center",
            fontsize=20, fontweight="bold")
    ax.set_xlim(-1, maximo + 1)
    ax.set_ylim(0, 7)


def dibujar_evaluacion(fig, edad, peso, riesgo):
    """Redibuja en `fig` la evaluación completa (figura 2x2)."""
    fig.clf()
    fig.set_facecolor(COLOR_FONDO)
    fig.suptitle(f"Evaluación de Paciente — Edad: {edad:g} años | Peso: {peso:g} kg",
                 color=COLOR_TEXTO, fontsize=14, fontweight="bold")
    (ax_edad, ax_peso), (ax_riesgo, ax_resultado) = fig.subplots(2, 2)

    _graficar_conjuntos(ax_edad, EDAD, COLORES_EDAD, "Edad", "Edad (años)", edad)
    _graficar_conjuntos(ax_peso, PESO, COLORES_PESO, "Peso", "Peso (kg)", peso)
    _graficar_conjuntos(ax_riesgo, RIESGO, COLORES_RIESGO, "Riesgo de infarto",
                        "Riesgo (0-10)", riesgo, marcar_dominante=False,
                        etiqueta_valor=f"Resultado ({riesgo:.2f})")
    _graficar_resultado(ax_resultado, riesgo)


def dibujar_inicio(fig):
    """Muestra un mensaje de bienvenida antes de la primera evaluación."""
    fig.clf()
    fig.set_facecolor(COLOR_FONDO)
    fig.text(0.5, 0.5, "Ingrese la edad y el peso del paciente\ny presione «Evaluar riesgo»",
             color=COLOR_TEXTO_SUAVE, ha="center", va="center", fontsize=15)


# =============================================================================
# 3. INTERFAZ (tkinter)
# =============================================================================

COLOR_ACENTO = "#1976d2"
COLOR_ACENTO_HOVER = "#2f8be6"
COLOR_ERROR = "#d32f2f"


class CampoNumerico(ttk.Frame):
    """Slider sincronizado con un campo numérico, con validación de rango."""

    def __init__(self, padre, nombre, minimo, maximo, inicial):
        super().__init__(padre)
        self.nombre, self.minimo, self.maximo = nombre, minimo, maximo
        self._sincronizando = False
        self._texto = tk.StringVar(value=f"{inicial:g}")
        self._posicion = tk.DoubleVar(value=inicial)

        ttk.Label(self, text=f"{nombre} ({minimo}–{maximo})").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))
        ttk.Scale(self, from_=minimo, to=maximo, variable=self._posicion,
                  command=self._al_mover).grid(row=1, column=0, sticky="ew")
        self._entrada = ttk.Entry(self, textvariable=self._texto, width=7, justify="center")
        self._entrada.grid(row=1, column=1, padx=(10, 0))
        self._entrada.bind("<KeyRelease>", self._al_escribir)
        self.columnconfigure(0, weight=1)

    def _al_mover(self, valor):
        """Slider -> campo numérico (valores enteros)."""
        if not self._sincronizando:
            self._texto.set(str(round(float(valor))))
            self.marcar_error(False)

    def _al_escribir(self, _evento):
        """Campo numérico -> slider (solo si el texto es un valor válido)."""
        try:
            valor = self.valor()
        except ValueError:
            return
        self._sincronizando = True
        self._posicion.set(valor)
        self._sincronizando = False
        self.marcar_error(False)

    def valor(self):
        """Devuelve el número escrito o lanza ValueError con un mensaje legible."""
        try:
            valor = float(self._texto.get().strip().replace(",", "."))
        except ValueError:
            raise ValueError(f"{self.nombre}: ingrese un número válido.") from None
        if not math.isfinite(valor) or not self.minimo <= valor <= self.maximo:
            raise ValueError(f"{self.nombre}: debe estar entre {self.minimo} y {self.maximo}.")
        return valor

    def marcar_error(self, hay_error):
        """Resalta u oculta el borde rojo del campo numérico."""
        self._entrada.configure(style="Error.TEntry" if hay_error else "TEntry")


class AppRiesgo(tk.Tk):
    """Ventana principal: panel lateral de entradas y gráfica de resultados."""

    def __init__(self):
        super().__init__()
        self.title("Evaluación de Riesgo de Infarto")
        ancho = min(1280, int(self.winfo_screenwidth() * 0.9))
        alto = min(760, int(self.winfo_screenheight() * 0.85))
        self.geometry(f"{ancho}x{alto}")
        self.minsize(980, 620)
        self.configure(bg=COLOR_FONDO)
        self._configurar_estilos()
        self._crear_panel_lateral()
        self._crear_grafica()
        self.bind("<Return>", lambda _evento: self._evaluar())

    def _configurar_estilos(self):
        """Tema claro (blanco y azul) personalizado para los widgets ttk."""
        estilo = ttk.Style(self)
        estilo.theme_use("clam")
        estilo.configure(".", background=COLOR_FONDO, foreground=COLOR_TEXTO,
                         font=("Segoe UI", 10))
        estilo.configure("Panel.TFrame", background=COLOR_PANEL)
        estilo.configure("Panel.TLabel", background=COLOR_PANEL)
        estilo.configure("Titulo.TLabel", background=COLOR_PANEL, foreground=COLOR_ACENTO,
                         font=("Segoe UI", 17, "bold"))
        estilo.configure("Sub.TLabel", background=COLOR_PANEL, foreground=COLOR_TEXTO_SUAVE,
                         font=("Segoe UI", 9))
        estilo.configure("Error.TLabel", background=COLOR_PANEL, foreground=COLOR_ERROR)
        for nombre, borde in (("TEntry", COLOR_REJILLA), ("Error.TEntry", COLOR_ERROR)):
            estilo.configure(nombre, fieldbackground=COLOR_FONDO, foreground=COLOR_TEXTO,
                             insertcolor=COLOR_TEXTO, bordercolor=borde,
                             lightcolor=borde, darkcolor=borde, padding=4)
        estilo.configure("Horizontal.TScale", background=COLOR_ACENTO,
                         troughcolor=COLOR_FONDO, bordercolor=COLOR_PANEL)
        estilo.map("Horizontal.TScale", background=[("active", COLOR_ACENTO_HOVER)])
        estilo.configure("Acento.TButton", background=COLOR_ACENTO, foreground="white",
                         font=("Segoe UI", 11, "bold"), padding=10, borderwidth=0)
        estilo.map("Acento.TButton", background=[("active", COLOR_ACENTO_HOVER)])

    def _crear_panel_lateral(self):
        """Panel izquierdo: título, campos de edad y peso, botón y mensaje de error."""
        panel = ttk.Frame(self, style="Panel.TFrame", padding=24, width=300)
        panel.grid(row=0, column=0, sticky="ns")
        panel.grid_propagate(False)
        panel.columnconfigure(0, weight=1)

        ttk.Label(panel, text="Riesgo de\nInfarto", style="Titulo.TLabel").grid(
            row=0, column=0, sticky="w")
        ttk.Label(panel, text="Inferencia difusa Mamdani", style="Sub.TLabel").grid(
            row=1, column=0, sticky="w", pady=(2, 28))

        self.campo_edad = CampoNumerico(panel, "Edad", RANGO_EDAD[0], RANGO_EDAD[1], 40)
        self.campo_peso = CampoNumerico(panel, "Peso", RANGO_PESO[0], RANGO_PESO[1], 70)
        self.campo_edad.grid(row=2, column=0, sticky="ew", pady=(0, 22))
        self.campo_peso.grid(row=3, column=0, sticky="ew", pady=(0, 28))
        for campo in (self.campo_edad, self.campo_peso):
            campo.configure(style="Panel.TFrame")
            for hijo in campo.winfo_children():
                if isinstance(hijo, ttk.Label):
                    hijo.configure(style="Panel.TLabel")

        ttk.Button(panel, text="Evaluar riesgo", style="Acento.TButton",
                   command=self._evaluar).grid(row=4, column=0, sticky="ew")

        self._mensaje_error = tk.StringVar()
        ttk.Label(panel, textvariable=self._mensaje_error, style="Error.TLabel",
                  wraplength=250, justify="left").grid(row=5, column=0, sticky="w", pady=16)

    def _crear_grafica(self):
        """Lienzo de matplotlib incrustado en la ventana (se redimensiona con ella)."""
        self.figura = Figure(layout="constrained")
        self.lienzo = FigureCanvasTkAgg(self.figura, master=self)
        self.lienzo.get_tk_widget().grid(row=0, column=1, sticky="nsew")
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        dibujar_inicio(self.figura)
        self.lienzo.draw_idle()

    def _evaluar(self):
        """Valida las entradas, evalúa el riesgo y actualiza la gráfica."""
        valores, errores = [], []
        for campo in (self.campo_edad, self.campo_peso):
            try:
                valores.append(campo.valor())
                campo.marcar_error(False)
            except ValueError as error:
                errores.append(str(error))
                campo.marcar_error(True)
        self._mensaje_error.set("\n".join(errores))
        if errores:
            return

        edad, peso = valores
        dibujar_evaluacion(self.figura, edad, peso, evaluar_riesgo(edad, peso))
        self.lienzo.draw_idle()


if __name__ == "__main__":
    AppRiesgo().mainloop()
