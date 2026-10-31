import time
from tkinter import filedialog
import tkinter as tk


class Api:

    # --- MODO DE TESTE DO FRONT END -------------------------------------
    # Troque para True para simular um ensalamento impossível (mais alunos
    # do que vagas) e ver o estado de erro da tela (passo 2).
    SIMULAR_FALHA_ENSALAMENTO = True
    # ---------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Métodos simulados: só devolvem dados fixos no formato que o front
    # espera. Nenhuma leitura de Excel nem modelo de otimização aqui.
    # ------------------------------------------------------------------

    def executar(self):

        time.sleep(2)  # simula processamento

        inconsistencias = [
            "Linha 5: 'manha' corrigido para 'Manhã'",
            "Linha 6: sexo inválido 'x' (Caio de Andrade da Costa)",
            "Nome duplicado: 'Lara Dias Ferreira Rodrigues' (2 ocorrências)",
        ]

        if self.SIMULAR_FALHA_ENSALAMENTO:
            return {
                "ok": False,
                "mensagem": "Turno Manhã: 80 alunos para 70 vagas",
                "inconsistencias": inconsistencias,
                "turmas": [],
                "arquivo_gerado": True,  # abas Inconsistências gravadas mesmo assim
            }

        return {
            "ok": True,
            "mensagem": "70 alunos alocados em 4 turmas",
            "inconsistencias": inconsistencias,
            "turmas": [
                {"turma": "MANHÃ - A", "total": 18, "m": 9, "f": 9},
                {"turma": "MANHÃ - B", "total": 17, "m": 8, "f": 9},
                {"turma": "TARDE - C", "total": 18, "m": 10, "f": 8},
                {"turma": "TARDE - D", "total": 17, "m": 9, "f": 8},
            ],
        }

    def abrir_resultado(self):

        # Futuramente: os.startfile(caminho_do_xlsx)
        print("abrir_resultado chamado (simulado)")