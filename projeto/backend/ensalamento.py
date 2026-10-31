"""Integração: tratamento.py -> modelagem -> abas do Excel -> resposta do front.

Não altera tratamento.py nem os arquivos da modelagem; só os orquestra.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font

#from ..etl.tratamento. import processar_excel
#from ..modelagem.otimizacao import otimizar_ensalamento  # ajuste se a pasta tiver outro nome

from etl.tratamento import processar_excel
from modelagem import otimizar_ensalamento

ABA_ENSALAMENTO = "Ensalamento"
ABA_INCONSISTENCIAS = "Inconsistências"
# Confira estes cabeçalhos com o template dos cenários de teste.
COLUNAS_ENSALAMENTO = ["Nome", "Sexo", "Disponibilidade", "Turma"]
COLUNAS_INCONSISTENCIAS = ["Tipo", "Descrição"]
# O solver (CBC) roda em duas etapas; cada uma para neste limite e devolve a
# melhor solução encontrada até ali, para a tela nunca ficar travada.
TEMPO_LIMITE_POR_ETAPA = 30  # segundos


# ---------------------------------------------------------------- entrada

def _montar_alunos(df: pd.DataFrame) -> list[dict]:
    """DataFrame já tratado -> lista de dicts que o modelo espera."""
    alunos = []
    for indice, linha in df.iterrows():
        turno = str(linha["Disponibilidade"]).strip().casefold()
        alunos.append({
            "id": int(indice),
            "nome": str(linha["Nome"]).strip(),
            "sexo": str(linha["Sexo"]).strip().upper(),
            "turno": "Manhã" if turno == "manhã" else "Tarde",
        })
    return alunos


def _montar_turmas(df: pd.DataFrame) -> list[dict]:
    """Aba Turmas -> turmas nomeadas em sequência contínua (manhã primeiro)."""
    valores = df.set_index("Recursos")["Quantidade"]
    total = int(valores["turmas_manha"]) + int(valores["turmas_tarde"])
    if total > 26:
        raise ValueError(f"São {total} turmas; o padrão de letras vai só até Z.")

    turmas, letra = [], 0
    for turno, sufixo in (("Manhã", "manha"), ("Tarde", "tarde")):
        for _ in range(int(valores[f"turmas_{sufixo}"])):
            turmas.append({
                "turma": f"{turno.upper()} - {chr(65 + letra)}",
                "turno": turno,
                "vagas": int(valores[f"vagas_{sufixo}"]),
            })
            letra += 1
    return turmas


# ----------------------------------------------------------- inconsistências

def _duplicidades(df: pd.DataFrame | None) -> list[str]:
    """tratamento.py não detecta nomes repetidos; isso entra como alerta."""
    if df is None or "Nome" not in df.columns:
        return []
    nomes = df["Nome"].dropna().astype(str).str.strip()
    nomes = nomes[nomes != ""]
    avisos = []
    for nome, qtd in nomes.value_counts().items():
        if qtd > 1:
            linhas = ", ".join(str(i + 2) for i in nomes.index[nomes == nome])
            avisos.append(
                f"Nome repetido '{nome}' (linhas {linhas}): "
                "mantidos como alunos distintos, confira se não é erro de cadastro"
            )
    return avisos


def _linhas_inconsistencias(res, duplicidades: list[str]) -> list[tuple[str, str]]:
    linhas = [("Tratada", c) for c in (res.correcoes or [])]
    linhas += [("Pendente", e) for e in res.erros]
    linhas += [("Alerta", d) for d in duplicidades]
    return linhas


# ------------------------------------------------------------------ saída

def _escrever_aba(wb, nome: str, cabecalho: list[str], linhas: list) -> None:
    if nome in wb.sheetnames:
        del wb[nome]
    ws = wb.create_sheet(nome)
    ws.append(cabecalho)
    for linha in linhas:
        ws.append(list(linha))
    for celula in ws[1]:
        celula.font = Font(bold=True)
    for coluna in ws.columns:
        maior = max(len(str(c.value or "")) for c in coluna)
        ws.column_dimensions[coluna[0].column_letter].width = min(maior + 3, 90)


def _gravar(caminho: str, ensalamento: list, inconsistencias: list) -> None:
    """Grava as duas abas no próprio Excel de entrada (substitui as antigas)."""
    wb = load_workbook(caminho)
    # Sem resultado, a aba fica só com o cabeçalho (como no template do cenário)
    # e não sobra ensalamento antigo de outra execução.
    _escrever_aba(wb, ABA_ENSALAMENTO, COLUNAS_ENSALAMENTO, ensalamento)
    _escrever_aba(wb, ABA_INCONSISTENCIAS, COLUNAS_INCONSISTENCIAS, inconsistencias)
    wb.save(caminho)


def _tentar_gravar(caminho, ensalamento, inconsistencias) -> tuple[bool, str | None]:
    try:
        _gravar(caminho, ensalamento, inconsistencias)
        return True, None
    except PermissionError:
        return False, "Não foi possível salvar: feche a planilha no Excel e tente de novo."
    except Exception as exc:  # arquivo corrompido, etc.
        return False, f"Não foi possível salvar o resultado: {exc}"


# ------------------------------------------------------------------ front

def _resposta(ok, mensagem, inconsistencias=(), turmas=(), arquivo_gerado=False):
    return {
        "ok": ok,
        "mensagem": mensagem,
        "inconsistencias": [f"{tipo}: {texto}" for tipo, texto in inconsistencias],
        "turmas": list(turmas),
        "arquivo_gerado": arquivo_gerado,
    }


def executar_ensalamento(caminho: str | None) -> dict:
    """Fluxo completo. Devolve o dict que o scripts.js espera."""
    if not caminho or not Path(caminho).is_file():
        return _resposta(False, "Nenhuma planilha válida selecionada.")

    res = processar_excel(caminho)
    inconsistencias = _linhas_inconsistencias(res, _duplicidades(res.alunos))

    # 1) Dados com problema que não dá para corrigir: não roda o modelo.
    if res.status != "OK":
        gravou, erro = _tentar_gravar(caminho, [], inconsistencias)
        n = len(res.erros)
        msg = res.erros[0] if n == 1 else f"{n} problemas impedem o ensalamento"
        return _resposta(False, erro or msg, inconsistencias, arquivo_gerado=gravou)

    # 2) Otimização.
    try:
        saida = otimizar_ensalamento(
            _montar_alunos(res.alunos), _montar_turmas(res.turmas),
            time_limit=TEMPO_LIMITE_POR_ETAPA,
        )
    except Exception as exc:
        inconsistencias.append(("Pendente", f"Falha no modelo: {exc}"))
        gravou, erro = _tentar_gravar(caminho, [], inconsistencias)
        return _resposta(False, erro or f"Falha no modelo: {exc}",
                         inconsistencias, arquivo_gerado=gravou)

    # 3) Grava as abas e responde.
    linhas = [
        [r["Nome do aluno"], r["Sexo"], r["Disponibilidade"], r["Turma"]]
        for r in saida["alocacao"]
    ]
    gravou, erro = _tentar_gravar(caminho, linhas, inconsistencias)
    if not gravou:
        return _resposta(False, erro, inconsistencias)

    m = saida["metricas"]
    turmas = [
        {"turma": r["Turma"], "total": r["Alunos"],
         "m": r["Masculino"], "f": r["Feminino"]}
        for r in saida["resumo"]
    ]
    return _resposta(
        True,
        f"{m['total_alocados']} alunos alocados em {m['total_turmas']} turmas",
        inconsistencias, turmas, arquivo_gerado=True,
    )