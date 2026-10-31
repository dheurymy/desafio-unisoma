import os
import subprocess
import sys
from tkinter import filedialog
import tkinter as tk

from .ensalamento import executar_ensalamento


class Api:

    def __init__(self):
        self.caminho = None

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

        return arquivo

    def executar(self):
        # tratamento -> modelagem -> grava abas no Excel -> resposta p/ o front
        return executar_ensalamento(self.caminho)

    def abrir_resultado(self):
        if not self.caminho or not os.path.isfile(self.caminho):
            raise FileNotFoundError("Planilha de resultado não encontrada.")

        if hasattr(os, "startfile"):  # Windows
            os.startfile(self.caminho)
        else:  # só para testes fora do Windows
            subprocess.Popen(
                ["open" if sys.platform == "darwin" else "xdg-open", self.caminho]
            )