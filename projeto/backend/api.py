import os
import subprocess
import sys
from tkinter import filedialog
import tkinter as tk

from .ensalamento import executar_ensalamento


class Api:
    def __init__(self):
        self.caminho = None
        self.pdf = None

    def selecionar_planilha(self):
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)

        arquivo = filedialog.askopenfilename(
            title="Selecione a Planilha",
            filetypes=[
                ("Arquivos Excel", "*.xlsx")
            ]
        )

        root.destroy()

        if arquivo:
            self.caminho = arquivo
            self.pdf = None

        return arquivo

    def executar(self, usar_so_necessarias=False):
        resultado = executar_ensalamento(
            self.caminho,
            bool(usar_so_necessarias)
        )

        self.pdf = resultado.get("pdf")

        return resultado

    def abrir_resultado(self):
        if not self.caminho or not os.path.isfile(self.caminho):
            raise FileNotFoundError(
                "Planilha de resultado não encontrada."
            )

        # Abre Excel
        if hasattr(os, "startfile"):
            os.startfile(self.caminho)
        else:
            subprocess.Popen(
                [
                    "open" if sys.platform == "darwin" else "xdg-open",
                    self.caminho,
                ]
            )

        # Abre PDF
        if self.pdf and os.path.isfile(self.pdf):
            if hasattr(os, "startfile"):
                os.startfile(self.pdf)
            else:
                subprocess.Popen(
                    [
                        "open" if sys.platform == "darwin" else "xdg-open",
                        self.pdf,
                    ]
                )