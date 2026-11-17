import tkinter as tk

TIPOS_TRANSPORTE = {
    "Metro": "MTO", "Tren Ligero": "TLO", "Trolebús": "TLB",
    "Cablebús": "CBS", "Metrobús": "MTB", "Red de Transporte de Pasajeros": "RTP",
}
LETRAS, DIGITOS = 3, 9
CODIGOS = list(TIPOS_TRANSPORTE.values())
LISTA = ", ".join(CODIGOS)

VERDE, ROJO, GRIS = "#2e7d32", "#d32f2f", "#dee2e6"


# ---------------------------------------------------------------------------
# Lógica de validación
# ---------------------------------------------------------------------------
def es_mayuscula(c):
    return "A" <= c <= "Z"


def es_digito(c):
    return "0" <= c <= "9"


def en_alfabeto(c):
    return es_mayuscula(c) or es_digito(c)


def nombre(cod):
    return next((k for k, v in TIPOS_TRANSPORTE.items() if v == cod), None)


def desc_caracter(c):
    if "a" <= c <= "z":
        return f"«{c}» es minúscula: solo se aceptan mayúsculas (A-Z)."
    if c == " ":
        return "Hay un espacio en el código."
    return f"«{c}» no pertenece al alfabeto permitido (A-Z, 0-9)."


def analizar(cad):
    """Autómata interno (no se dibuja): {MTO, TLO, TLB, CBS, MTB, RTP} → [0-9]{9}
    Devuelve dict con: cad, ok (nº de caracteres válidos),
    error ({tipo, pos, len, texto} | None), codigo, folio."""
    n = len(cad)

    def fallo(tipo, pos, ln, texto, ok=None):
        return {"cad": cad, "ok": pos if ok is None else ok,
                "error": {"tipo": tipo, "pos": pos, "len": ln, "texto": texto}}

    if not n:
        return fallo("Inválido", 0, 0, "No se ingresó ningún código.")

    j = 0                                   # letras mayúsculas consecutivas
    while j < n and es_mayuscula(cad[j]):
        j += 1

    if not j:
        c = cad[0]
        if en_alfabeto(c):
            return fallo("Malformado", 0, 1,
                         f"El código debe iniciar con un transporte ({LISTA}); se encontró «{c}».")
        return fallo("Inválido", 0, 1, desc_caracter(c))

    pal = cad[:min(j, LETRAS)]
    if pal not in CODIGOS:
        if j == n and j <= LETRAS and any(t.startswith(pal) for t in CODIGOS):
            return fallo("Incompleto", n, 0, "El código termina antes de completar el transporte.")
        extra = f" y excede {LETRAS} letras" if j > LETRAS else ""
        return fallo("Malformado", 0, j,
                     f"«{cad[:j]}» no está en el diccionario{extra} (válidos: {LISTA}).", 0)

    if j > LETRAS:
        return fallo("Malformado", LETRAS, j - LETRAS,
                     f"El transporte admite máximo {LETRAS} letras; sobran {j - LETRAS}.")

    for i in range(j, n):
        c = cad[i]
        if not es_digito(c):
            if en_alfabeto(c):
                return fallo("Malformado", i, 1,
                             f"Después de «{pal}» solo pueden ir dígitos; se encontró «{c}».")
            return fallo("Inválido", i, 1, desc_caracter(c))
        if i - j >= DIGITOS:
            return fallo("Malformado", i, n - i,
                         f"El folio debe tener exactamente {DIGITOS} dígitos; sobran {n - i}.")

    d = n - j
    if d < DIGITOS:
        if d:
            texto = f"El folio tiene {d} dígito(s); faltan {DIGITOS - d} para completar los {DIGITOS}."
        else:
            texto = f"Faltan los dígitos después de «{pal}» (se requieren {DIGITOS})."
        return fallo("Incompleto", n, 0, texto)

    return {"cad": cad, "ok": n, "error": None, "codigo": pal, "folio": cad[j:]}


# ---------------------------------------------------------------------------
# Interfaz
# ---------------------------------------------------------------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Torniquete")
        self.timer = None
        self._ajustando = False

        # Panel de estado
        self.status_panel = tk.Frame(self, highlightthickness=4,
                                     highlightbackground=GRIS, padx=20, pady=20)
        self.status_panel.grid(row=0, column=0, padx=20, pady=20)
        self.turnstile_icon = tk.Label(self.status_panel, text="🔒", font=("Arial", 40))
        self.turnstile_icon.pack()
        self.status_message = tk.Label(self.status_panel, text="TORNIQUETE BLOQUEADO",
                                       font=("Arial", 14, "bold"))
        self.status_message.pack()
        self.feedback_message = tk.Label(self.status_panel, wraplength=400)

        # Visor (verde = válido, rojo = error)
        self.visor = tk.Text(self, height=1, width=40, font=("Courier", 16),
                             state="disabled")
        self.visor.tag_config("ok", foreground="#1b5e20", background="#c8e6c9")
        self.visor.tag_config("err", foreground="#b71c1c", background="#ffcdd2", underline=True)
        self.visor.tag_config("ign", foreground="#aaaaaa", overstrike=True)
        self.visor.grid(row=1, column=0, padx=20)
        self.visor.grid_remove()

        # Entrada con mayúsculas automáticas
        self.var_unico = tk.StringVar()
        self.var_unico.trace_add("write", self._a_mayusculas)
        self.input_unico = tk.Entry(self, textvariable=self.var_unico,
                                    font=("Courier", 16), width=40)
        self.input_unico.grid(row=2, column=0, padx=20, pady=10)
        self.input_unico.bind("<Return>", self._on_enter)
        self.input_unico.focus()

        # Botones
        self.btn_validate = tk.Button(self, text="VALIDAR", command=self.validar_acceso)
        self.btn_validate.grid(row=3, column=0, pady=10)
        self.btn_pass = tk.Button(self, text="PASAR", command=self.reiniciar_sistema)
        self.btn_pass.grid(row=3, column=0, pady=10)
        self.btn_pass.grid_remove()

    # ---------- Visor ----------
    def pintar_visor(self, r):
        cad, ok, e = r["cad"], r["ok"], r["error"]

        self.visor.config(state="normal")
        self.visor.delete("1.0", tk.END)

        for k, c in enumerate(cad):
            es_err = bool(e) and e["pos"] <= k < e["pos"] + e["len"]
            cls = "ok" if k < ok else "err" if es_err else "ign"
            self.visor.insert(tk.END, "␣" if c == " " else c, cls)

        if e and e["pos"] >= len(cad):          # falta algo al final
            self.visor.insert(tk.END, "?", "err")

        self.visor.config(state="disabled")
        if cad or e:
            self.visor.grid()
        else:
            self.visor.grid_remove()

    # ---------- Validación ----------
    def validar_acceso(self):
        r = analizar(self.var_unico.get().strip())
        e = r["error"]
        self.pintar_visor(r)

        if e:
            pos = f" (posición {e['pos'] + 1})" if e["len"] else ""
            return self.estado(ROJO, "🔒", "TORNIQUETE BLOQUEADO",
                               f"✖ Error {e['tipo']}{pos}: {e['texto']}", "error")

        self.estado(VERDE, "🔓", "ACCESO PERMITIDO - TORNIQUETE ABIERTO",
                    f"✔ Validación Exitosa. Sistema: {nombre(r['codigo'])} ({r['codigo']}). "
                    f"Folio: {r['folio']}", "success")
        self.btn_validate.grid_remove()
        self.btn_pass.grid()
        if self.timer:
            self.after_cancel(self.timer)
        self.timer = self.after(6000, self.reiniciar_sistema)   # regreso automático a los 6 s

    def reiniciar_sistema(self):
        if self.timer:
            self.after_cancel(self.timer)
            self.timer = None
        self.var_unico.set("")
        self.input_unico.focus()
        self.visor.grid_remove()
        self.btn_validate.grid()
        self.btn_pass.grid_remove()
        self.estado(GRIS, "🔒", "TORNIQUETE BLOQUEADO")

    def estado(self, borde, icono, mensaje, feedback="", tipo=""):
        self.status_panel.config(highlightbackground=borde)
        self.turnstile_icon.config(text=icono)
        self.status_message.config(text=mensaje)
        if feedback:
            color = ROJO if tipo == "error" else VERDE if tipo == "success" else "black"
            self.feedback_message.config(text=feedback, fg=color)
            self.feedback_message.pack()
        else:
            self.feedback_message.config(text="")
            self.feedback_message.pack_forget()

    # ---------- Eventos ----------
    def _a_mayusculas(self, *_):                # mayúsculas automáticas
        if self._ajustando:
            return
        self._ajustando = True
        p = self.input_unico.index(tk.INSERT)
        self.var_unico.set(self.var_unico.get().upper())
        self.input_unico.icursor(p)
        self._ajustando = False

    def _on_enter(self, _event):
        if self.btn_validate.winfo_ismapped():
            self.validar_acceso()


if __name__ == "__main__":
    App().mainloop()
