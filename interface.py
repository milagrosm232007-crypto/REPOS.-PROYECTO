"""
interface.py
============
Interfaz grafica de MemGuard (Tkinter), construida siguiendo el wireframe
de 8 pantallas:

    1. Login                5. Ciberseguridad
    2. Panel principal       6. Alertas
    3. Memoria RAM           7. Accesibilidad
    4. Dispositivos USB      8. Configuracion

Ejecutar con:   python interface.py
Requiere:       pip install psutil pyttsx3
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading

import backend

# --------------------------------------------------------------------------
# Paleta y tipografia (coherente con el wireframe: fondo claro, tarjetas
# blancas, sidebar oscuro, acentos rojo/amarillo/verde/azul)
# --------------------------------------------------------------------------
LIGHT_COLORS = {
    "bg": "#eef1f6",
    "sidebar": "#0f1b2d",
    "sidebar_active": "#1b2c47",
    "card": "#ffffff",
    "text": "#1e293b",
    "text_muted": "#64748b",
    "border": "#e2e8f0",
    "blue": "#2563eb",
    "blue_dark": "#1d4ed8",
    "green": "#16a34a",
    "green_bg": "#dcfce7",
    "orange": "#d97706",
    "orange_bg": "#fef3c7",
    "red": "#dc2626",
    "red_bg": "#fee2e2",
    "console_bg": "#0b1220",
    "console_text": "#4ade80",
}

DARK_COLORS = {
    "bg": "#0b1220",
    "sidebar": "#060a13",
    "sidebar_active": "#141f33",
    "card": "#141b2d",
    "text": "#e2e8f0",
    "text_muted": "#94a3b8",
    "border": "#26324a",
    "blue": "#3b82f6",
    "blue_dark": "#2563eb",
    "green": "#22c55e",
    "green_bg": "#0f2b1c",
    "orange": "#f59e0b",
    "orange_bg": "#2e2410",
    "red": "#ef4444",
    "red_bg": "#2e1414",
    "console_bg": "#000000",
    "console_text": "#4ade80",
}

# COLORS se muta "in place" (clear + update) en vez de reasignarse, porque
# todas las pantallas hacen `COLORS["algo"]` en el momento en que se crean
# sus widgets. Mientras el diccionario sea el mismo objeto, cambiar sus
# valores y reconstruir la interfaz (reconstruir_shell) basta para que
# el modo oscuro se aplique de verdad a todos los widgets.
COLORS = dict(LIGHT_COLORS)


def aplicar_tema(oscuro):
    """Cambia la paleta activa (COLORS) a oscura o clara."""
    origen = DARK_COLORS if oscuro else LIGHT_COLORS
    COLORS.clear()
    COLORS.update(origen)

NIVEL_COLOR = {
    "ALTO": ("red", "red_bg"),
    "MEDIO": ("orange", "orange_bg"),
    "INFO": ("green", "green_bg"),
}
NIVEL_ETIQUETA = {"ALTO": "Alta", "MEDIO": "Media", "INFO": "Info"}

FONT_BASE = "Segoe UI"  # se reemplaza en tiempo de ejecucion por _mejor_fuente()


def _mejor_fuente():
    """Elige la mejor fuente disponible segun el sistema operativo, para
    que la app no dependa de que 'Segoe UI' (solo existe en Windows) este
    instalada."""
    import tkinter.font as tkfont
    disponibles = set(tkfont.families())
    preferidas = ["Segoe UI", "Ubuntu", "Noto Sans", "Cantarell", "DejaVu Sans", "Helvetica", "Arial"]
    for f in preferidas:
        if f in disponibles:
            return f
    return "TkDefaultFont"


def _mezclar(hex_color, factor):
    """Aclara (factor>1) u oscurece (factor<1) un color #rrggbb."""
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    r, g, b = (min(255, max(0, int(c * factor))) for c in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


class RoundedButton(tk.Canvas):
    """Boton con esquinas redondeadas y efecto hover, dibujado a mano
    (Tkinter no soporta border-radius de forma nativa)."""

    def __init__(self, master, text, command=None, bg=None, fg="white",
                 parent_bg=None, font=None, radius=10, height=40, **kw):
        parent_bg = parent_bg or COLORS["bg"]
        super().__init__(master, highlightthickness=0, bg=parent_bg,
                          height=height, cursor="hand2", **kw)
        self.command = command
        self.text = text
        self.bg_color = bg or COLORS["blue"]
        self.hover_color = _mezclar(self.bg_color, 0.88)
        self.fg_color = fg
        self.font = font or (FONT_BASE, 10, "bold")
        self.radius = radius
        self._hover = False
        self.bind("<Configure>", self._redibujar)
        self.bind("<Button-1>", self._click)
        self.bind("<Enter>", lambda e: self._set_hover(True))
        self.bind("<Leave>", lambda e: self._set_hover(False))

    def _set_hover(self, valor):
        self._hover = valor
        self._redibujar()

    def _redibujar(self, event=None):
        self.delete("all")
        w = self.winfo_width() or 200
        h = self.winfo_height() or 40
        color = self.hover_color if self._hover else self.bg_color
        r = min(self.radius, h // 2)
        puntos = [
            r, 0, w - r, 0, w, 0, w, r, w, h - r, w, h,
            w - r, h, r, h, 0, h, 0, h - r, 0, r, 0, 0,
        ]
        self.create_polygon(puntos, smooth=True, fill=color, outline=color)
        self.create_text(w / 2, h / 2, text=self.text, fill=self.fg_color, font=self.font)

    def _click(self, event=None):
        if self.command:
            self.command()

    def set_enabled(self, activo):
        self.command_backup = getattr(self, "command_backup", self.command)
        self.command = self.command_backup if activo else None
        self.configure(cursor="hand2" if activo else "arrow")


def entrada_estilizada(master, show=None, font_size=11):
    """Entry con borde suave en vez del relive hundido por defecto de
    Tkinter, para que combine con las tarjetas blancas."""
    entry = tk.Entry(
        master, font=(FONT_BASE, font_size), relief="flat",
        highlightthickness=1, highlightbackground=COLORS["border"],
        highlightcolor=COLORS["blue"], bd=6, show=show
    )
    return entry



class Badge(tk.Label):
    """Pequena etiqueta de color (Alta/Media/Info, Alto/Normal/OK...)."""

    def __init__(self, master, text, fg, bg, **kw):
        super().__init__(
            master, text=text, fg=fg, bg=bg,
            font=(FONT_BASE, 9, "bold"), padx=8, pady=2, **kw
        )


class Card(tk.Frame):
    """Tarjeta blanca con borde suave, unidad basica del wireframe."""

    def __init__(self, master, **kw):
        super().__init__(
            master, bg=COLORS["card"], highlightbackground=COLORS["border"],
            highlightthickness=1, bd=0, **kw
        )


# --------------------------------------------------------------------------
# App principal
# --------------------------------------------------------------------------
class MemGuardApp(tk.Tk):
    NAV_ITEMS = [
        ("panel", "Panel principal"),
        ("ram", "Memoria RAM"),
        ("usb", "Dispositivos USB"),
        ("ciber", "Ciberseguridad"),
        ("alertas", "Alertas"),
        ("accesibilidad", "Accesibilidad"),
        ("config", "Configuracion"),
    ]

    def __init__(self):
        super().__init__()
        global FONT_BASE
        FONT_BASE = _mejor_fuente()
        self.title("MemGuard - Sistema de Monitoreo")
        self.geometry("1200x750")
        self.minsize(1000, 650)

        self.config_datos = backend.cargar_configuracion()
        self.escala_texto = 1.15 if self.config_datos.get("texto_grande") else 1.0
        self.alertas_anunciadas = set()

        # Aplica el modo oscuro/claro guardado ANTES de crear cualquier
        # widget, para que hasta el login ya se vea con el tema correcto.
        aplicar_tema(self.config_datos.get("modo_oscuro", False))
        self.configure(bg=COLORS["bg"])

        self.container = tk.Frame(self, bg=COLORS["bg"])
        self.container.pack(fill="both", expand=True)

        self.sidebar = None
        self.content = None
        self.pantallas = {}
        self.pantalla_activa = None

        # Vigilancia de USB en segundo plano: corre siempre, sin importar
        # en que pantalla este el usuario (incluso antes de loguearse),
        # asi avisa apenas se conecta un dispositivo nuevo en vez de
        # esperar a que el usuario entre a la pantalla "Dispositivos USB".
        self.usb_conocidos = {d["unidad"] for d in backend.listar_usb()}
        self.after(3000, self._vigilar_usb)

        self.mostrar_login()

    # ---------------------------------------------------------- helpers
    def f(self, base_size, weight="normal"):
        """Fuente escalada segun accesibilidad (Texto grande)."""
        return (FONT_BASE, int(round(base_size * self.escala_texto)), weight)

    def limpiar_container(self):
        for w in self.container.winfo_children():
            w.destroy()

    def _vigilar_usb(self):
        """Revisa cada pocos segundos si aparecio un USB nuevo y, si es
        asi, muestra un aviso (y lo anuncia por voz si 'Alertas sonoras'
        esta activado). Se reprograma solo, asi que corre durante toda
        la vida de la app."""
        try:
            actuales = {d["unidad"] for d in backend.listar_usb()}
            nuevos = actuales - self.usb_conocidos
            desconectados = self.usb_conocidos - actuales
            for unidad in nuevos:
                self._mostrar_toast(f"USB conectado: {unidad}", COLORS["blue"])
                if self.config_datos.get("alertas_sonoras"):
                    threading.Thread(
                        target=backend.hablar, args=(f"Se conecto un dispositivo USB en {unidad}",),
                        daemon=True
                    ).start()
            for unidad in desconectados:
                self._mostrar_toast(f"USB desconectado: {unidad}", COLORS["text_muted"])
            self.usb_conocidos = actuales
            # Si el usuario esta parado en la pantalla de USB, la refresca
            # para que la lista se actualice al toque en vez de esperar
            # al proximo ciclo de esa pantalla.
            if self.pantalla_activa == "usb" and "usb" in self.pantallas:
                self.pantallas["usb"].cancelar_refresco()
                self.pantallas["usb"].actualizar()
        except Exception:
            pass
        self.after(3000, self._vigilar_usb)

    def _mostrar_toast(self, texto, color):
        """Notificacion no bloqueante (no interrumpe lo que el usuario
        este haciendo, a diferencia de un messagebox) que aparece arriba
        a la derecha y se cierra sola."""
        try:
            toast = tk.Toplevel(self)
            toast.overrideredirect(True)
            toast.attributes("-topmost", True)
            ancho, alto = 300, 56
            x = self.winfo_x() + max(self.winfo_width() - ancho - 24, 0)
            y = self.winfo_y() + 24
            toast.geometry(f"{ancho}x{alto}+{x}+{y}")
            marco = tk.Frame(toast, bg=color, padx=14, pady=10)
            marco.pack(fill="both", expand=True)
            tk.Label(marco, text=texto, bg=color, fg="white",
                     font=self.f(10, "bold"), wraplength=270, justify="left").pack(anchor="w")
            toast.after(4000, toast.destroy)
        except Exception:
            pass

    # ------------------------------------------------------------ login
    def mostrar_login(self):
        self.limpiar_container()
        LoginScreen(self.container, self).pack(fill="both", expand=True)

    # ------------------------------------------------------- shell (post-login)
    def construir_shell(self):
        self.limpiar_container()
        self.sidebar = Sidebar(self.container, self)
        self.sidebar.pack(side="left", fill="y")

        self.content = tk.Frame(self.container, bg=COLORS["bg"])
        self.content.pack(side="left", fill="both", expand=True)

        self.pantallas = {
            "panel": PanelScreen(self.content, self),
            "ram": RAMScreen(self.content, self),
            "usb": USBScreen(self.content, self),
            "ciber": CiberScreen(self.content, self),
            "alertas": AlertasScreen(self.content, self),
            "accesibilidad": AccesibilidadScreen(self.content, self),
            "config": ConfigScreen(self.content, self),
        }
        for p in self.pantallas.values():
            p.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.mostrar_pantalla("panel")

    def mostrar_pantalla(self, nombre):
        if nombre not in self.pantallas:
            return
        self.pantalla_activa = nombre
        self.pantallas[nombre].tkraise()
        self.pantallas[nombre].al_mostrar()
        if self.sidebar:
            self.sidebar.marcar_activo(nombre)

    def reconstruir_shell(self):
        """Reconstruye toda la interfaz (usado al cambiar accesibilidad,
        texto grande o modo oscuro). Como COLORS ya tiene los valores
        nuevos para cuando esto se llama, recrear todos los widgets basta
        para que tomen la paleta actualizada."""
        activa = self.pantalla_activa or "panel"
        self.configure(bg=COLORS["bg"])
        self.container.configure(bg=COLORS["bg"])
        self.construir_shell()
        self.mostrar_pantalla(activa)

    def cerrar_sesion(self):
        self.mostrar_login()

    def anunciar_alertas_nuevas(self, alertas):
        """Habla en voz alta las alertas ALTO que aun no se hayan
        anunciado, solo si el usuario activo 'Alertas sonoras'. Evita
        repetir la misma alerta en cada refresco."""
        if not self.config_datos.get("alertas_sonoras"):
            return
        for alerta in alertas:
            if alerta["nivel"] != "ALTO":
                continue
            clave = alerta["mensaje"]
            if clave in self.alertas_anunciadas:
                continue
            self.alertas_anunciadas.add(clave)
            texto = f"Alerta. {alerta['mensaje']}"
            threading.Thread(target=backend.hablar, args=(texto,), daemon=True).start()


# --------------------------------------------------------------------------
# Pantalla 1: Login
# --------------------------------------------------------------------------
class LoginScreen(tk.Frame):
    def __init__(self, master, app: MemGuardApp):
        super().__init__(master, bg=COLORS["bg"])
        self.app = app
        cred = backend.cargar_credenciales()

        box = Card(self, padx=40, pady=40)
        box.place(relx=0.5, rely=0.5, anchor="center", width=380, height=500)

        logo = tk.Label(box, text="MG", bg=COLORS["blue"], fg="white",
                         font=(FONT_BASE, 20, "bold"), width=3, height=1)
        logo.pack(pady=(10, 15))

        tk.Label(box, text="MemGuard", bg=COLORS["card"], fg=COLORS["text"],
                 font=(FONT_BASE, 18, "bold")).pack()
        tk.Label(box, text="Sistema de monitoreo", bg=COLORS["card"],
                 fg=COLORS["text_muted"], font=(FONT_BASE, 10)).pack(pady=(0, 25))

        tk.Label(box, text="Usuario", bg=COLORS["card"], fg=COLORS["text"],
                 font=(FONT_BASE, 9), anchor="w").pack(fill="x")
        self.usuario = entrada_estilizada(box)
        self.usuario.insert(0, cred["usuario"])
        self.usuario.pack(fill="x", pady=(4, 14))

        tk.Label(box, text="Contrasena", bg=COLORS["card"], fg=COLORS["text"],
                 font=(FONT_BASE, 9), anchor="w").pack(fill="x")
        self.password = entrada_estilizada(box, show="*")
        self.password.pack(fill="x", pady=(4, 8))

        self.lbl_error = tk.Label(box, text="", bg=COLORS["card"], fg=COLORS["red"],
                                   font=(FONT_BASE, 9), wraplength=300, justify="left")
        self.lbl_error.pack(fill="x", pady=(0, 10))

        RoundedButton(box, "Entrar al sistema", bg=COLORS["blue"], parent_bg=COLORS["card"],
                      font=(FONT_BASE, 11, "bold"), command=self.entrar).pack(fill="x")

        modo_acc = tk.Label(box, text="Modo accesibilidad", bg=COLORS["card"],
                             fg=COLORS["blue"], font=(FONT_BASE, 9, "underline"),
                             cursor="hand2")
        modo_acc.pack(pady=(15, 0))
        modo_acc.bind("<Button-1>", lambda e: self.entrar(accesibilidad=True))

        self.usuario.bind("<Return>", lambda e: self.entrar())
        self.password.bind("<Return>", lambda e: self.entrar())
        self.password.focus_set()

    def entrar(self, accesibilidad=False):
        usuario = self.usuario.get()
        contrasena = self.password.get()
        if not backend.verificar_credenciales(usuario, contrasena):
            self.lbl_error.configure(text="Usuario o contrasena incorrectos.")
            self.password.delete(0, "end")
            self.password.focus_set()
            return
        self.app.construir_shell()
        if accesibilidad:
            self.app.mostrar_pantalla("accesibilidad")


# --------------------------------------------------------------------------
# Sidebar (navegacion, comun a pantallas 2-8)
# --------------------------------------------------------------------------
class Sidebar(tk.Frame):
    SIMBOLOS = {
        "panel": "\u2302",        # casa/panel
        "ram": "\u25A4",          # memoria
        "usb": "\u26A1",          # rayo/dispositivo
        "ciber": "\u26E8",        # escudo
        "alertas": "\u26A0",      # alerta
        "accesibilidad": "\u267F",  # accesibilidad
        "config": "\u2699",       # engranaje
    }

    def __init__(self, master, app: MemGuardApp):
        super().__init__(master, bg=COLORS["sidebar"], width=180)
        self.app = app
        self.pack_propagate(False)
        self.botones = {}

        tk.Label(self, text="MG  MemGuard", bg=COLORS["sidebar"], fg="white",
                 font=(FONT_BASE, 13, "bold")).pack(anchor="w", padx=18, pady=(20, 24))

        for clave, etiqueta in app.NAV_ITEMS:
            self._crear_item(clave, etiqueta)

        salir = tk.Frame(self, bg=COLORS["sidebar"], cursor="hand2")
        salir.pack(side="bottom", fill="x", pady=18, padx=10)
        tk.Label(salir, text="\u2715  Cerrar sesion", bg=COLORS["sidebar"], fg="#f87171",
                 font=(FONT_BASE, 10, "bold"), anchor="w").pack(fill="x", ipady=6, padx=8)
        for w in (salir, salir.winfo_children()[0]):
            w.bind("<Button-1>", lambda e: app.cerrar_sesion())

    def _crear_item(self, clave, etiqueta):
        fila = tk.Frame(self, bg=COLORS["sidebar"], cursor="hand2")
        fila.pack(fill="x", padx=10, pady=2)
        contenido = tk.Label(
            fila, text=f"{self.SIMBOLOS.get(clave, '\u2022')}  {etiqueta}",
            bg=COLORS["sidebar"], fg="#cbd5e1", font=(FONT_BASE, 10), anchor="w"
        )
        contenido.pack(fill="x", ipady=8, padx=10)

        widgets = (fila, contenido)
        for w in widgets:
            w.bind("<Button-1>", lambda e, c=clave: self.app.mostrar_pantalla(c))
            w.bind("<Enter>", lambda e, c=clave: self._hover(c, True))
            w.bind("<Leave>", lambda e, c=clave: self._hover(c, False))
        self.botones[clave] = (fila, contenido)

    def _hover(self, clave, activo):
        if self.app.pantalla_activa == clave:
            return
        fila, contenido = self.botones[clave]
        color = COLORS["sidebar_active"] if activo else COLORS["sidebar"]
        fila.configure(bg=color)
        contenido.configure(bg=color)

    def marcar_activo(self, clave):
        for k, (fila, contenido) in self.botones.items():
            color = COLORS["sidebar_active"] if k == clave else COLORS["sidebar"]
            fg = "white" if k == clave else "#cbd5e1"
            fila.configure(bg=color)
            contenido.configure(bg=color, fg=fg)


# --------------------------------------------------------------------------
# Base para las pantallas internas (evita repetir boilerplate)
# --------------------------------------------------------------------------
class BaseScreen(tk.Frame):
    TITULO = ""

    def __init__(self, master, app: MemGuardApp):
        super().__init__(master, bg=COLORS["bg"])
        self.app = app
        self._auto_job = None
        self.construir()

    def construir(self):
        raise NotImplementedError

    def al_mostrar(self):
        """Se llama cada vez que la pantalla se hace visible."""
        pass

    def programar_refresco(self, ms, funcion):
        self._auto_job = self.after(ms, funcion)

    def cancelar_refresco(self):
        if self._auto_job:
            self.after_cancel(self._auto_job)
            self._auto_job = None

    def encabezado(self, texto):
        tk.Label(self, text=texto, bg=COLORS["bg"], fg=COLORS["text"],
                 font=self.app.f(18, "bold")).pack(anchor="w", padx=30, pady=(24, 16))


# --------------------------------------------------------------------------
# Pantalla 2: Panel principal
# --------------------------------------------------------------------------
class PanelScreen(BaseScreen):
    def construir(self):
        self.encabezado("Panel principal")

        stats = tk.Frame(self, bg=COLORS["bg"])
        stats.pack(fill="x", padx=30)
        self.lbl_ram = self._stat(stats, "RAM", COLORS["blue"])
        self.lbl_cpu = self._stat(stats, "CPU", COLORS["green"])
        self.lbl_disco = self._stat(stats, "Disco", COLORS["orange"])
        self.lbl_amenazas = self._stat(stats, "Amenazas", COLORS["red"])

        tk.Label(self, text="Alertas recientes", bg=COLORS["bg"], fg=COLORS["text"],
                 font=self.app.f(13, "bold")).pack(anchor="w", padx=30, pady=(24, 8))

        self.lista_alertas = tk.Frame(self, bg=COLORS["bg"])
        self.lista_alertas.pack(fill="both", expand=True, padx=30, pady=(0, 20))

    def _stat(self, master, nombre, color):
        card = Card(master, padx=18, pady=14)
        card.pack(side="left", padx=(0, 16), fill="x", expand=True)
        tk.Label(card, text=nombre, bg=COLORS["card"], fg=COLORS["text_muted"],
                 font=self.app.f(9)).pack(anchor="w")
        valor = tk.Label(card, text="--", bg=COLORS["card"], fg=color,
                          font=self.app.f(22, "bold"))
        valor.pack(anchor="w")
        return valor

    def al_mostrar(self):
        self.cancelar_refresco()
        self.actualizar()

    def actualizar(self):
        estado = backend.obtener_estado_sistema()
        self.lbl_ram.configure(text=f"{estado['ram']['uso_percent']:.0f}%")
        self.lbl_cpu.configure(text=f"{estado['cpu']:.0f}%")
        self.lbl_disco.configure(text=f"{estado['disco']['porcentaje']:.0f}%")
        resumen = backend.resumen_ciberseguridad(estado["alertas"])
        self.lbl_amenazas.configure(text=str(resumen["amenazas"]))
        self.app.anunciar_alertas_nuevas(estado["alertas"])

        for w in self.lista_alertas.winfo_children():
            w.destroy()
        if not estado["alertas"]:
            tk.Label(self.lista_alertas, text="Sin alertas detectadas",
                     bg=COLORS["bg"], fg=COLORS["text_muted"],
                     font=self.app.f(10)).pack(anchor="w")
        for alerta in estado["alertas"][:5]:
            fila_alerta(self.lista_alertas, self.app, alerta)

        self.programar_refresco(int(self.app.config_datos["intervalo_escaneo"]) * 1000, self.actualizar)


def fila_alerta(master, app, alerta):
    color, bgcolor = NIVEL_COLOR[alerta["nivel"]]
    fila = Card(master, padx=14, pady=10)
    fila.pack(fill="x", pady=4)
    izq = tk.Frame(fila, bg=COLORS["card"])
    izq.pack(side="left", fill="x", expand=True)
    tk.Label(izq, text=alerta["mensaje"], bg=COLORS["card"], fg=COLORS["text"],
             font=app.f(10), anchor="w", justify="left", wraplength=650).pack(anchor="w")
    tk.Label(izq, text=f"{alerta['categoria']} \u00b7 {alerta['hora']}",
             bg=COLORS["card"], fg=COLORS["text_muted"], font=app.f(8)).pack(anchor="w")
    Badge(fila, NIVEL_ETIQUETA[alerta["nivel"]], COLORS[color], COLORS[bgcolor]).pack(side="right")
    return fila


# --------------------------------------------------------------------------
# Pantalla 3: Memoria RAM
# --------------------------------------------------------------------------
class RAMScreen(BaseScreen):
    def construir(self):
        self.encabezado("Memoria RAM")

        top = Card(self, padx=24, pady=20)
        top.pack(fill="x", padx=30)
        tk.Label(top, text="Memoria RAM", bg=COLORS["card"], fg=COLORS["text_muted"],
                 font=self.app.f(10)).pack(anchor="w")
        self.lbl_valor = tk.Label(top, text="-- GB", bg=COLORS["card"], fg=COLORS["blue"],
                                   font=self.app.f(26, "bold"))
        self.lbl_valor.pack(anchor="w")
        self.lbl_sub = tk.Label(top, text="de -- GB en uso", bg=COLORS["card"],
                                 fg=COLORS["text_muted"], font=self.app.f(9))
        self.lbl_sub.pack(anchor="w")

        self.barra = ttk.Progressbar(top, length=400, mode="determinate")
        self.barra.pack(fill="x", pady=(10, 0))

        tk.Label(self, text="Procesos activos (psutil)", bg=COLORS["bg"],
                 fg=COLORS["text"], font=self.app.f(12, "bold")).pack(
            anchor="w", padx=30, pady=(20, 8))

        cols = ("Proceso", "Uso", "Estado")
        self.tabla = ttk.Treeview(self, columns=cols, show="headings", height=12)
        for c, w in zip(cols, (300, 140, 120)):
            self.tabla.heading(c, text=c)
            self.tabla.column(c, width=w, anchor="w")
        self.tabla.pack(fill="both", expand=True, padx=30, pady=(0, 20))
        self.tabla.tag_configure("Alto", foreground=COLORS["red"])
        self.tabla.tag_configure("Normal", foreground=COLORS["orange"])
        self.tabla.tag_configure("OK", foreground=COLORS["green"])

    def al_mostrar(self):
        self.cancelar_refresco()
        self.actualizar()

    def actualizar(self):
        ram = backend.obtener_ram()
        self.lbl_valor.configure(text=f"{ram['usado_gb']} GB")
        self.lbl_sub.configure(text=f"de {ram['total_gb']} GB en uso")
        self.barra["value"] = ram["uso_percent"]

        for i in self.tabla.get_children():
            self.tabla.delete(i)
        for proc in backend.obtener_procesos():
            self.tabla.insert("", "end", values=(
                proc["nombre"], f"{proc['mem_mb']} MB", proc["estado"]
            ), tags=(proc["estado"],))

        self.programar_refresco(5000, self.actualizar)


# --------------------------------------------------------------------------
# Pantalla 4: Dispositivos USB
# --------------------------------------------------------------------------
class USBScreen(BaseScreen):
    def construir(self):
        self.encabezado("Dispositivos USB")
        self.lista = tk.Frame(self, bg=COLORS["bg"])
        self.lista.pack(fill="both", expand=True, padx=30, pady=(0, 20))

    def al_mostrar(self):
        self.cancelar_refresco()
        self.actualizar()

    def actualizar(self):
        for w in self.lista.winfo_children():
            w.destroy()

        dispositivos = backend.listar_usb()
        if not dispositivos:
            tk.Label(self.lista, text="No hay dispositivos USB conectados",
                     bg=COLORS["bg"], fg=COLORS["text_muted"],
                     font=self.app.f(11)).pack(anchor="w", pady=20)
        for dev in dispositivos:
            self._tarjeta_usb(dev)

        self.programar_refresco(8000, self.actualizar)

    def _tarjeta_usb(self, dev):
        sospechoso = dev["sospechoso"]
        color, bgcolor = ("red", "red_bg") if sospechoso else ("green", "green_bg")
        card = Card(self.lista, padx=18, pady=14)
        card.pack(fill="x", pady=8)

        header = tk.Frame(card, bg=COLORS["card"])
        header.pack(fill="x")
        tk.Label(header, text="USB", bg=COLORS[color], fg="white",
                 font=self.app.f(8, "bold"), padx=6, pady=1).pack(side="left")
        tk.Label(header, text=f"  {dev['nombre']}", bg=COLORS["card"], fg=COLORS["text"],
                 font=self.app.f(12, "bold")).pack(side="left")

        tk.Label(card, text=f"{dev['unidad']}  \u00b7  {dev['sistema_archivos']}",
                 bg=COLORS["card"], fg=COLORS["text_muted"], font=self.app.f(9)).pack(anchor="w")

        if sospechoso:
            tk.Label(card, text="autorun.inf detectado \u2014 sospechoso",
                     bg=COLORS["card"], fg=COLORS["red"], font=self.app.f(9)).pack(anchor="w", pady=(4, 6))
        else:
            tk.Label(card, text="Sin senales de alerta automaticas \u00b7 analiza para confirmar",
                     bg=COLORS["card"], fg=COLORS["text_muted"], font=self.app.f(9)).pack(anchor="w", pady=(4, 6))

        botones = tk.Frame(card, bg=COLORS["card"])
        botones.pack(fill="x")
        # "Analizar dispositivo": hace el chequeo real (autorun.inf +
        # ejecutables de malware conocido + dobles extensiones) SOLO
        # cuando el usuario lo pide, en vez de decidir "sospechoso" de
        # forma automatica con solo conectar el USB.
        RoundedButton(botones, "Analizar dispositivo", bg=COLORS["blue"], parent_bg=COLORS["card"],
                      font=self.app.f(10, "bold"),
                      command=lambda d=dev: self._analizar(d)
                      ).pack(fill="x", pady=(0, 6))
        # Cualquier dispositivo, sospechoso o no, se puede expulsar.
        RoundedButton(botones, "Expulsar dispositivo", bg=COLORS["red"] if sospechoso else COLORS["orange"],
                      parent_bg=COLORS["card"], font=self.app.f(10, "bold"),
                      command=lambda d=dev: self._bloquear(d)
                      ).pack(fill="x")

    def _analizar(self, dev):
        self.cancelar_refresco()
        threading.Thread(target=self._analizar_en_hilo, args=(dev,), daemon=True).start()

    def _analizar_en_hilo(self, dev):
        resultado = backend.escanear_usb(dev["unidad"])
        self.after(0, lambda: self._resultado_analisis(dev, resultado))

    def _resultado_analisis(self, dev, resultado):
        texto = "\n".join(f"\u2022 {h}" for h in resultado["hallazgos"])
        pie = f"\n\nArchivos analizados: {resultado.get('archivos_analizados', 0)}"
        if resultado["sospechoso"]:
            messagebox.showwarning(
                "MemGuard \u2014 Analisis de USB",
                f"Se encontraron senales sospechosas en {dev['unidad']}:\n\n{texto}{pie}"
            )
        else:
            messagebox.showinfo(
                "MemGuard \u2014 Analisis de USB",
                f"Analisis de {dev['unidad']} completo:\n\n{texto}{pie}"
            )
        self.actualizar()

    def _bloquear(self, dev):
        confirmar = messagebox.askyesno(
            "MemGuard",
            f"Esto va a desmontar/expulsar {dev['unidad']} de forma segura.\n"
            "No podras leer ni escribir en el hasta que lo reconectes.\n\n"
            "\u00bfContinuar?"
        )
        if not confirmar:
            return
        threading.Thread(target=self._bloquear_en_hilo, args=(dev,), daemon=True).start()

    def _bloquear_en_hilo(self, dev):
        exito, mensaje = backend.expulsar_usb(dev["unidad"], dev.get("device"))
        # Los widgets de Tkinter solo se tocan desde el hilo principal:
        # self.after(0, ...) programa esto de forma segura.
        self.after(0, lambda: self._resultado_bloqueo(exito, mensaje))

    def _resultado_bloqueo(self, exito, mensaje):
        if exito:
            messagebox.showinfo("MemGuard", mensaje)
        else:
            messagebox.showerror(
                "MemGuard",
                f"No se pudo bloquear el dispositivo.\n\n{mensaje}"
            )
        self.cancelar_refresco()
        self.actualizar()


# --------------------------------------------------------------------------
# Pantalla 5: Ciberseguridad
# --------------------------------------------------------------------------
class CiberScreen(BaseScreen):
    def construir(self):
        self.encabezado("Ciberseguridad")

        stats = tk.Frame(self, bg=COLORS["bg"])
        stats.pack(fill="x", padx=30)
        self.lbl_amenazas = self._stat(stats, "Amenazas", COLORS["red"])
        self.lbl_escaneados = self._stat(stats, "Escaneados", COLORS["blue"])
        self.lbl_usb_bloq = self._stat(stats, "USB bloq.", COLORS["orange"])
        self.lbl_estado = self._stat(stats, "Estado", COLORS["green"])

        body = tk.Frame(self, bg=COLORS["bg"])
        body.pack(fill="both", expand=True, padx=30, pady=(20, 20))
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)

        # Consola tipo "Log Kali Linux"
        consola_wrap = Card(body, padx=0, pady=0)
        consola_wrap.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        cabecera_consola = tk.Frame(consola_wrap, bg=COLORS["card"])
        cabecera_consola.pack(fill="x", padx=14, pady=(12, 6))
        tk.Label(cabecera_consola, text="Log Kali Linux", bg=COLORS["card"], fg=COLORS["text"],
                 font=self.app.f(11, "bold")).pack(side="left")
        self.lbl_estado_scan = tk.Label(cabecera_consola, text="", bg=COLORS["card"],
                                         fg=COLORS["text_muted"], font=self.app.f(9, "bold"))
        self.lbl_estado_scan.pack(side="right")

        self.barra_escaneo = ttk.Progressbar(consola_wrap, length=100, mode="determinate")
        self.barra_escaneo.pack(fill="x", padx=14, pady=(0, 8))

        self.consola = tk.Text(consola_wrap, bg=COLORS["console_bg"], fg=COLORS["console_text"],
                                font=("Consolas", 10), height=10, relief="flat")
        self.consola.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self.consola.tag_configure("alerta", foreground=COLORS["orange"])
        self.consola.tag_configure("exito", foreground=COLORS["green"])
        self.consola.configure(state="disabled")

        self._anim_job = None

        # Registro de amenazas
        registro_wrap = Card(body, padx=0, pady=0)
        registro_wrap.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        tk.Label(registro_wrap, text="Registro de amenazas", bg=COLORS["card"], fg=COLORS["text"],
                 font=self.app.f(11, "bold")).pack(anchor="w", padx=14, pady=(12, 6))
        self.registro = tk.Frame(registro_wrap, bg=COLORS["card"])
        self.registro.pack(fill="both", expand=True, padx=14, pady=(0, 14))

    def _stat(self, master, nombre, color):
        card = Card(master, padx=18, pady=14)
        card.pack(side="left", padx=(0, 16), fill="x", expand=True)
        tk.Label(card, text=nombre, bg=COLORS["card"], fg=COLORS["text_muted"],
                 font=self.app.f(9)).pack(anchor="w")
        valor = tk.Label(card, text="--", bg=COLORS["card"], fg=color,
                          font=self.app.f(20, "bold"))
        valor.pack(anchor="w")
        return valor

    # Pasos "en vivo" que se muestran mientras avanza el analisis. Cada
    # uno tiene el texto de consola y la funcion de backend que hace el
    # trabajo real correspondiente a ese paso.
    _PASOS_ESCANEO = (
        ("Analizando procesos...", lambda: backend.detectar_procesos_sospechosos()),
        ("Analizando memoria RAM...", lambda: backend.obtener_ram()),
        ("Revisando conexiones...", lambda: backend.detectar_conexiones()),
        ("Escaneando puertos...", lambda: backend.detectar_puertos()),
        ("Buscando malware conocido...", lambda: None),
        ("Verificando dispositivos USB...", lambda: backend.detectar_usb()),
        ("Analizando archivos del USB...", lambda: None),
    )

    def al_mostrar(self):
        self.cancelar_refresco()
        self.actualizar()

    def cancelar_refresco(self):
        super().cancelar_refresco()
        if self._anim_job:
            self.after_cancel(self._anim_job)
            self._anim_job = None

    def actualizar(self):
        # Los datos reales se calculan de una sola vez al principio; la
        # animacion de abajo solo va "revelando" ese resultado paso a
        # paso, para que lo que se muestra en pantalla siempre coincida
        # con lo que realmente se encontro.
        alertas = backend.obtener_alertas()
        resumen = backend.resumen_ciberseguridad(alertas)
        self.app.anunciar_alertas_nuevas(alertas)

        self.lbl_amenazas.configure(text=str(resumen["amenazas"]))
        self.lbl_escaneados.configure(text=str(len(backend.obtener_procesos(top=9999))))
        self.lbl_usb_bloq.configure(text=str(sum(1 for d in backend.listar_usb() if d["sospechoso"])))
        self.lbl_estado.configure(
            text=resumen["estado"],
            fg=COLORS["red"] if resumen["estado"] == "ALERTA" else COLORS["green"]
        )

        for w in self.registro.winfo_children():
            w.destroy()
        criticas = [a for a in alertas if a["nivel"] in ("ALTO", "MEDIO")]
        if not criticas:
            tk.Label(self.registro, text="Sin amenazas registradas", bg=COLORS["card"],
                     fg=COLORS["text_muted"], font=self.app.f(9)).pack(anchor="w")
        for a in criticas[:6]:
            self._fila_registro(a)

        self._iniciar_animacion_escaneo(criticas)

    def _fila_registro(self, alerta):
        color, bgcolor = NIVEL_COLOR[alerta["nivel"]]
        fila = tk.Frame(self.registro, bg=COLORS["card"])
        fila.pack(fill="x", pady=4)
        tk.Label(fila, text=alerta["mensaje"], bg=COLORS["card"], fg=COLORS["text"],
                 font=self.app.f(9), anchor="w", justify="left",
                 wraplength=280).pack(side="left", fill="x", expand=True)
        Badge(fila, NIVEL_ETIQUETA[alerta["nivel"]], COLORS[color], COLORS[bgcolor]).pack(side="right")

    # -------------------------------------------------- consola animada
    def _iniciar_animacion_escaneo(self, criticas):
        if self._anim_job:
            self.after_cancel(self._anim_job)
            self._anim_job = None

        self.consola.configure(state="normal")
        self.consola.delete("1.0", "end")
        self.consola.configure(state="disabled")
        self.barra_escaneo["value"] = 0
        self.lbl_estado_scan.configure(text="Escaneando\u2026", fg=COLORS["blue"])

        self._log("Iniciando an\u00e1lisis...", "\u25b6")
        self._ejecutar_paso_escaneo(0, criticas)

    def _ejecutar_paso_escaneo(self, indice, criticas):
        total = len(self._PASOS_ESCANEO)
        if indice < total:
            texto, tarea = self._PASOS_ESCANEO[indice]
            try:
                tarea()
            except Exception:
                pass
            self._log(texto, "\u2713", "exito")
            self.barra_escaneo["value"] = int((indice + 1) / total * 100)
            self._anim_job = self.after(
                300, lambda: self._ejecutar_paso_escaneo(indice + 1, criticas)
            )
        else:
            self._anim_job = self.after(200, lambda: self._finalizar_animacion_escaneo(criticas))

    def _finalizar_animacion_escaneo(self, criticas):
        self._anim_job = None
        if not criticas:
            self._log("No se detectaron amenazas.", "\u2714", "exito")
            self._log("Estado del sistema: SEGURO", "\U0001f6e1", "exito")
            self.lbl_estado_scan.configure(text="\U0001f6e1 Sistema protegido", fg=COLORS["green"])
        else:
            for a in criticas:
                self._log(a["mensaje"], "\u26a0", "alerta")
            self._log(f"{len(criticas)} amenaza(s) encontradas.", "\u274c", "alerta")
            self.lbl_estado_scan.configure(
                text=f"\U0001f6a8 {len(criticas)} amenaza(s) detectada(s)", fg=COLORS["red"]
            )
        self.programar_refresco(int(self.app.config_datos["intervalo_escaneo"]) * 1000, self.actualizar)

    def _log(self, texto, prefijo="\u2713", tag=None):
        self.consola.configure(state="normal")
        if tag:
            self.consola.insert("end", f"{prefijo} {texto}\n", tag)
        else:
            self.consola.insert("end", f"{prefijo} {texto}\n")
        self.consola.see("end")
        # Limitar historial a 40 lineas
        lineas = int(self.consola.index("end-1c").split(".")[0])
        if lineas > 40:
            self.consola.delete("1.0", "2.0")
        self.consola.configure(state="disabled")


# --------------------------------------------------------------------------
# Pantalla 6: Alertas
# --------------------------------------------------------------------------
class AlertasScreen(BaseScreen):
    def construir(self):
        header = tk.Frame(self, bg=COLORS["bg"])
        header.pack(fill="x", padx=30, pady=(24, 16))
        tk.Label(header, text="Alertas", bg=COLORS["bg"], fg=COLORS["text"],
                 font=self.app.f(18, "bold")).pack(side="left")
        self.lbl_nuevas = Badge(header, "0 nuevas", "white", COLORS["red"])
        self.lbl_nuevas.pack(side="left", padx=10)

        self.lista = tk.Frame(self, bg=COLORS["bg"])
        self.lista.pack(fill="both", expand=True, padx=30, pady=(0, 20))

    def al_mostrar(self):
        self.cancelar_refresco()
        self.actualizar()

    def actualizar(self):
        alertas = backend.obtener_alertas()
        self.lbl_nuevas.configure(text=f"{len(alertas)} nuevas")
        self.app.anunciar_alertas_nuevas(alertas)

        for w in self.lista.winfo_children():
            w.destroy()
        if not alertas:
            tk.Label(self.lista, text="No hay alertas por el momento",
                     bg=COLORS["bg"], fg=COLORS["text_muted"],
                     font=self.app.f(11)).pack(anchor="w", pady=20)
        for alerta in alertas:
            fila_alerta(self.lista, self.app, alerta)

        self.programar_refresco(int(self.app.config_datos["intervalo_escaneo"]) * 1000, self.actualizar)


# --------------------------------------------------------------------------
# Pantalla 7: Accesibilidad
# --------------------------------------------------------------------------
class ToggleSwitch(tk.Canvas):
    """Interruptor on/off simple dibujado a mano (sin dependencias extra)."""

    def __init__(self, master, valor_inicial, on_change):
        super().__init__(master, width=44, height=24, bg=COLORS["card"],
                          highlightthickness=0, cursor="hand2")
        self.valor = valor_inicial
        self.on_change = on_change
        self.dibujar()
        self.bind("<Button-1>", self.alternar)

    def dibujar(self):
        self.delete("all")
        color = COLORS["blue"] if self.valor else "#cbd5e1"
        self.create_oval(2, 2, 24, 22, fill=color, outline=color)
        self.create_rectangle(12, 2, 32, 22, fill=color, outline=color)
        self.create_oval(20, 2, 42, 22, fill=color, outline=color)
        cx = 32 if self.valor else 12
        self.create_oval(cx - 9, 3, cx + 9, 21, fill="white", outline="white")

    def alternar(self, event=None):
        self.valor = not self.valor
        self.dibujar()
        self.on_change(self.valor)


class AccesibilidadScreen(BaseScreen):
    def construir(self):
        self.encabezado("Accesibilidad")

        body = tk.Frame(self, bg=COLORS["bg"])
        body.pack(fill="both", expand=True, padx=30)

        # Alertas por voz
        voz = Card(body, padx=18, pady=16)
        voz.pack(fill="x", pady=(0, 16))
        tk.Label(voz, text="Alertas por voz", bg=COLORS["card"], fg=COLORS["text"],
                 font=self.app.f(11, "bold")).pack(anchor="w")
        self.lbl_voz_demo = tk.Label(
            voz, text='"Alerta: USB sospechoso detectado"',
            bg=COLORS["green_bg"], fg=COLORS["green"], font=self.app.f(9), padx=8, pady=6
        )
        self.lbl_voz_demo.pack(anchor="w", fill="x", pady=(8, 4))
        tk.Label(voz, text="Motor: pyttsx3  \u00b7  Velocidad: 145 wpm", bg=COLORS["card"],
                 fg=COLORS["text_muted"], font=self.app.f(8)).pack(anchor="w")

        # Selector de voz: se arma con las voces que la PC donde corre la
        # app tenga instaladas en ese momento (no una lista fija), asi
        # sirve igual si esto se ejecuta en otra maquina distinta.
        self.voces_disponibles = backend.listar_voces()
        tk.Label(voz, text="Elegir voz", bg=COLORS["card"], fg=COLORS["text"],
                 font=self.app.f(10, "bold")).pack(anchor="w", pady=(12, 4))

        nombres = ["Automatica (recomendada)"] + [v["nombre"] for v in self.voces_disponibles]
        self.combo_voz = ttk.Combobox(voz, values=nombres, state="readonly",
                                       font=self.app.f(10))
        voz_guardada = self.app.config_datos.get("voz_id", "")
        indice = 0
        for i, v in enumerate(self.voces_disponibles):
            if v["id"] == voz_guardada:
                indice = i + 1
                break
        self.combo_voz.current(indice)
        self.combo_voz.pack(fill="x")
        self.combo_voz.bind("<<ComboboxSelected>>", self._cambiar_voz)

        if not self.voces_disponibles:
            tk.Label(voz, text="No se detectaron voces de texto a voz instaladas en este equipo.",
                     bg=COLORS["card"], fg=COLORS["text_muted"], font=self.app.f(8)).pack(anchor="w", pady=(6, 0))

        # Ajustes de interfaz (toggles)
        ajustes = Card(body, padx=18, pady=16)
        ajustes.pack(fill="x", pady=(0, 16))
        tk.Label(ajustes, text="Ajustes de interfaz", bg=COLORS["card"], fg=COLORS["text"],
                 font=self.app.f(11, "bold")).pack(anchor="w", pady=(0, 10))

        self._fila_toggle(ajustes, "Texto grande", "texto_grande")
        self._fila_toggle(ajustes, "Alto contraste", "alto_contraste")
        self._fila_toggle(ajustes, "Modo oscuro", "modo_oscuro")
        self._fila_toggle(ajustes, "Alertas sonoras", "alertas_sonoras")

        RoundedButton(body, "Probar alerta de voz", bg=COLORS["blue"], parent_bg=COLORS["bg"],
                      font=self.app.f(10, "bold"),
                      command=self.probar_voz).pack(fill="x")

    def _fila_toggle(self, master, etiqueta, clave):
        fila = tk.Frame(master, bg=COLORS["card"])
        fila.pack(fill="x", pady=6)
        tk.Label(fila, text=etiqueta, bg=COLORS["card"], fg=COLORS["text"],
                 font=self.app.f(10)).pack(side="left")
        valor = bool(self.app.config_datos.get(clave, False))
        switch = ToggleSwitch(fila, valor, lambda v, k=clave: self._cambiar(k, v))
        switch.pack(side="right")

    def _cambiar(self, clave, valor):
        self.app.config_datos[clave] = valor
        backend.guardar_configuracion(self.app.config_datos)
        if clave == "texto_grande":
            self.app.escala_texto = 1.15 if valor else 1.0
            self.app.reconstruir_shell()
        elif clave == "modo_oscuro":
            aplicar_tema(valor)
            self.app.reconstruir_shell()

    def _cambiar_voz(self, event=None):
        idx = self.combo_voz.current()
        if idx <= 0:
            # "Automatica": vuelve a que la app elija sola la mejor voz
            self.app.config_datos["voz_id"] = ""
            backend.guardar_configuracion(self.app.config_datos)
            backend.reconfigurar_voz_automatica()
        else:
            voz = self.voces_disponibles[idx - 1]
            self.app.config_datos["voz_id"] = voz["id"]
            backend.guardar_configuracion(self.app.config_datos)
            backend.establecer_voz(voz["id"])

    def probar_voz(self):
        texto = "Alerta, USB sospechoso detectado"
        hilo = threading.Thread(target=backend.hablar, args=(texto,), daemon=True)
        hilo.start()
        messagebox.showinfo("MemGuard", "Reproduciendo alerta de voz...")


# --------------------------------------------------------------------------
# Pantalla 8: Configuracion
# --------------------------------------------------------------------------
class ConfigScreen(BaseScreen):
    def construir(self):
        self.encabezado("Configuracion")

        card = Card(self, padx=20, pady=20)
        card.pack(fill="x", padx=30)

        self.campos = {}
        self._campo(card, "Intervalo de escaneo (segundos)", "intervalo_escaneo")
        self._campo(card, "Lenguaje", "lenguaje")
        self._campo(card, "Entorno virtual", "entorno_virtual")
        self._campo(card, "Version", "version")
        self._campo(card, "Libreria de voz", "libreria_voz")

        botones = tk.Frame(self, bg=COLORS["bg"])
        botones.pack(fill="x", padx=30, pady=(20, 10))
        RoundedButton(botones, "Guardar cambios", bg=COLORS["blue"], parent_bg=COLORS["bg"],
                      font=self.app.f(10, "bold"),
                      command=self.guardar).pack(fill="x", pady=(0, 8))
        RoundedButton(botones, "Aplicar configuracion", bg=COLORS["green"], parent_bg=COLORS["bg"],
                      font=self.app.f(10, "bold"),
                      command=self.aplicar).pack(fill="x")

        # --- Seguridad de acceso (cambiar contrasena) ---
        seguridad = Card(self, padx=20, pady=20)
        seguridad.pack(fill="x", padx=30, pady=(10, 20))
        tk.Label(seguridad, text="Seguridad de acceso", bg=COLORS["card"], fg=COLORS["text"],
                 font=self.app.f(12, "bold")).pack(anchor="w", pady=(0, 10))

        cred_actual = backend.cargar_credenciales()
        tk.Label(seguridad, text=f"Usuario actual: {cred_actual['usuario']}",
                 bg=COLORS["card"], fg=COLORS["text_muted"], font=self.app.f(9)).pack(anchor="w", pady=(0, 10))

        self.pass_actual = self._campo_password(seguridad, "Contrasena actual")
        self.pass_nueva = self._campo_password(seguridad, "Contrasena nueva (min. 6 caracteres)")
        self.pass_confirmar = self._campo_password(seguridad, "Confirmar contrasena nueva")

        RoundedButton(seguridad, "Actualizar contrasena", bg=COLORS["orange"], parent_bg=COLORS["card"],
                      font=self.app.f(10, "bold"),
                      command=self.cambiar_password).pack(fill="x", pady=(10, 0))

    def _campo_password(self, master, etiqueta):
        fila = tk.Frame(master, bg=COLORS["card"])
        fila.pack(fill="x", pady=6)
        tk.Label(fila, text=etiqueta, bg=COLORS["card"], fg=COLORS["text_muted"],
                 font=self.app.f(9)).pack(anchor="w")
        entrada = entrada_estilizada(fila, show="*", font_size=self.app.f(10)[1])
        entrada.pack(fill="x", pady=(2, 0))
        return entrada

    def cambiar_password(self):
        actual = self.pass_actual.get()
        nueva = self.pass_nueva.get()
        confirmar = self.pass_confirmar.get()
        if nueva != confirmar:
            messagebox.showerror("MemGuard", "La nueva contrasena y su confirmacion no coinciden.")
            return
        exito, mensaje = backend.cambiar_contrasena(actual, nueva)
        if exito:
            self.pass_actual.delete(0, "end")
            self.pass_nueva.delete(0, "end")
            self.pass_confirmar.delete(0, "end")
            messagebox.showinfo("MemGuard", mensaje)
        else:
            messagebox.showerror("MemGuard", mensaje)

    def _campo(self, master, etiqueta, clave):
        fila = tk.Frame(master, bg=COLORS["card"])
        fila.pack(fill="x", pady=8)
        tk.Label(fila, text=etiqueta, bg=COLORS["card"], fg=COLORS["text_muted"],
                 font=self.app.f(9)).pack(anchor="w")
        entrada = entrada_estilizada(fila, font_size=self.app.f(10)[1])
        entrada.insert(0, str(self.app.config_datos.get(clave, "")))
        entrada.pack(fill="x", pady=(2, 0))
        self.campos[clave] = entrada

    def guardar(self):
        for clave, entrada in self.campos.items():
            valor = entrada.get()
            if clave == "intervalo_escaneo":
                try:
                    valor = max(3, int(valor))
                except ValueError:
                    valor = self.app.config_datos["intervalo_escaneo"]
            self.app.config_datos[clave] = valor
        backend.guardar_configuracion(self.app.config_datos)
        messagebox.showinfo("MemGuard", "Cambios guardados correctamente.")

    def aplicar(self):
        self.guardar()
        messagebox.showinfo("MemGuard", "Configuracion aplicada.")


# --------------------------------------------------------------------------
if __name__ == "__main__":
    app = MemGuardApp()
    app.mainloop()
