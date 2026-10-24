"""Interface do Backup: escolhe origem e destino e mostra o andamento."""

import os
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import backup

ROTULOS = {
    backup.COPIAR: "COPIADO",
    backup.SUBSTITUIR: "SUBSTITUIDO",
    backup.IGNORAR: "IGNORADO",
    "erro": "ERRO",
}


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Backup")
        self.geometry("760x520")
        self.minsize(560, 380)

        self.origem = tk.StringVar()
        self.destino = tk.StringVar()
        self.simular = tk.BooleanVar(value=False)
        self.mostrar_ignorados = tk.BooleanVar(value=False)
        self.fila = queue.Queue()
        self.cancelar = threading.Event()
        self.thread = None

        self._montar()

    def _montar(self):
        quadro = ttk.Frame(self, padding=12)
        quadro.pack(fill="both", expand=True)
        quadro.columnconfigure(1, weight=1)

        for linha, (texto, var) in enumerate((("Origem:", self.origem), ("Destino:", self.destino))):
            ttk.Label(quadro, text=texto).grid(row=linha, column=0, sticky="w", pady=3)
            ttk.Entry(quadro, textvariable=var).grid(row=linha, column=1, sticky="ew", padx=6)
            ttk.Button(quadro, text="Escolher...", command=lambda v=var: self._escolher(v)).grid(
                row=linha, column=2)

        opcoes = ttk.Frame(quadro)
        opcoes.grid(row=2, column=0, columnspan=3, sticky="w", pady=(6, 0))
        ttk.Checkbutton(opcoes, text="Simular (so mostra, nao copia)", variable=self.simular).pack(
            side="left")
        ttk.Checkbutton(opcoes, text="Listar arquivos ignorados", variable=self.mostrar_ignorados).pack(
            side="left", padx=12)

        botoes = ttk.Frame(quadro)
        botoes.grid(row=3, column=0, columnspan=3, sticky="ew", pady=8)
        self.btn_iniciar = ttk.Button(botoes, text="Iniciar backup", command=self._iniciar)
        self.btn_iniciar.pack(side="left")
        self.btn_cancelar = ttk.Button(botoes, text="Cancelar", command=self.cancelar.set,
                                       state="disabled")
        self.btn_cancelar.pack(side="left", padx=6)
        self.status = ttk.Label(botoes, text="")
        self.status.pack(side="left", padx=12)

        self.barra = ttk.Progressbar(quadro, mode="indeterminate")
        self.barra.grid(row=4, column=0, columnspan=3, sticky="ew")

        caixa = ttk.Frame(quadro)
        caixa.grid(row=5, column=0, columnspan=3, sticky="nsew", pady=(8, 0))
        quadro.rowconfigure(5, weight=1)
        self.log = tk.Text(caixa, wrap="none", font=("Consolas", 9), state="disabled")
        rolagem = ttk.Scrollbar(caixa, command=self.log.yview)
        self.log.configure(yscrollcommand=rolagem.set)
        rolagem.pack(side="right", fill="y")
        self.log.pack(side="left", fill="both", expand=True)
        self.log.tag_configure("copiar", foreground="#1a7f37")
        self.log.tag_configure("substituir", foreground="#0550ae")
        self.log.tag_configure("ignorar", foreground="#6e7781")
        self.log.tag_configure("erro", foreground="#cf222e")

    def _escolher(self, var):
        pasta = filedialog.askdirectory(initialdir=var.get() or None)
        if pasta:
            var.set(os.path.normpath(pasta))

    def _escrever(self, texto, tag=None):
        self.log.configure(state="normal")
        self.log.insert("end", texto + "\n", tag)
        self.log.see("end")
        self.log.configure(state="disabled")

    def _iniciar(self):
        origem, destino = self.origem.get().strip(), self.destino.get().strip()
        if not origem or not destino:
            messagebox.showwarning("Backup", "Escolha a pasta de origem e a de destino.")
            return

        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        self.cancelar.clear()
        self.btn_iniciar.configure(state="disabled")
        self.btn_cancelar.configure(state="normal")
        self.barra.configure(mode="indeterminate", value=0)
        self.barra.start(12)
        self.status.configure(text="Copiando..." if not self.simular.get() else "Simulando...")

        def trabalho():
            try:
                res = backup.executar(
                    origem, destino, simular=self.simular.get(),
                    aviso=lambda *a: self.fila.put(("item",) + a),
                    parar=self.cancelar.is_set)
                self.fila.put(("fim", res))
            except Exception as erro:
                self.fila.put(("falha", str(erro)))

        self.thread = threading.Thread(target=trabalho, daemon=True)
        self.thread.start()
        self.after(50, self._consumir)

    def _consumir(self):
        try:
            while True:
                msg = self.fila.get_nowait()
                if msg[0] == "item":
                    _, acao, relativo, motivo = msg
                    if acao == backup.IGNORAR and not self.mostrar_ignorados.get():
                        continue
                    self._escrever(f"{ROTULOS[acao]:<12} {relativo}  ({motivo})", acao)
                else:
                    self._terminar(msg)
                    return
        except queue.Empty:
            pass
        self.after(50, self._consumir)

    def _terminar(self, msg):
        self.barra.stop()
        # parado em modo indeterminado, sobra um bloco solto na barra
        self.barra.configure(mode="determinate", value=100)
        self.btn_iniciar.configure(state="normal")
        self.btn_cancelar.configure(state="disabled")
        if msg[0] == "falha":
            self.status.configure(text="Falhou")
            messagebox.showerror("Backup", msg[1])
            return
        res = msg[1]
        prefixo = "Cancelado. " if self.cancelar.is_set() else ""
        if self.simular.get():
            prefixo += "Simulacao: "
        resumo = (f"{prefixo}{res.copiados} copiados, {res.substituidos} substituidos, "
                  f"{res.ignorados} ignorados, {len(res.erros)} erros")
        self.status.configure(text=resumo)
        self._escrever("\n" + resumo)


if __name__ == "__main__":
    App().mainloop()
