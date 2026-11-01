"""Integração: tratamento -> modelagem -> abas do Excel -> resposta do front.

Não altera o tratamento nem os arquivos da modelagem; só os orquestra.
"""

from __future__ import annotations

import unicodedata
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font

# ---- AJUSTE ESTES DOIS IMPORTS conforme as suas pastas -------------------
from etl.tratamento import processar_excel
from modelagem import otimizar_ensalamento
# --------------------------------------------------------------------------
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import (
    getSampleStyleSheet,
    ParagraphStyle,
)
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    PageBreak,
)

from datetime import datetime
from collections import defaultdict

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import (
    getSampleStyleSheet,
    ParagraphStyle,
)
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
)



ABA_ENSALAMENTO = "Ensalamento"
ABA_INCONSISTENCIAS = "Inconsistências"
COLUNAS_ENSALAMENTO = ["Nome", "Sexo", "Disponibilidade", "Turma"]
# Mesmas colunas do DataFrame de inconsistências do tratamento.
COLUNAS_INCONSISTENCIAS = ["Linha", "Coluna", "Tipo de erro", "Detalhes"]
# O solver (CBC) roda em duas etapas; cada uma para neste limite e devolve a
# melhor solução encontrada até ali, para a tela nunca ficar travada.
TEMPO_LIMITE_POR_ETAPA = 30  # segundos

ERRO_GERAL = "Erro geral da instância"      # texto usado pelo tratamento
LINHA_DESCARTADA = "Registro descartado"    # começo do texto usado pelo tratamento
# Erros gerais do tratamento que listam vários itens separados por vírgula.
CODIGOS_COM_LISTA = {
    "ABAS_AUSENTES",
    "COLUNAS_ALUNOS_AUSENTES",
    "COLUNAS_TURMAS_AUSENTES",
    "RECURSOS_TURMAS_AUSENTES",
    "RECURSOS_TURMAS_REPETIDOS",
}


# ------------------------------------------------------------ normalização

def _vazio(v) -> bool:
    return pd.isna(v) or str(v).strip() == ""


def _texto(v) -> str:
    return "" if _vazio(v) else str(v).strip()


def _sem_acento(t: str) -> str:
    t = unicodedata.normalize("NFKD", t)
    return "".join(c for c in t if not unicodedata.combining(c)).casefold()


def _sexo(v) -> str | None:
    t = _texto(v).upper()
    return t if t in ("M", "F") else None


def _turno(v) -> str | None:
    return {"manha": "Manhã", "tarde": "Tarde"}.get(_sem_acento(_texto(v)))


# ---------------------------------------------------------------- entrada

def _montar_alunos(df: pd.DataFrame) -> list[dict]:
    """DataFrame de alunos válidos -> lista de dicts que o modelo espera."""
    return [
        {
            "id": int(indice),
            "nome": _texto(linha["Nome"]),
            "sexo": _sexo(linha["Sexo"]),
            "turno": _turno(linha["Disponibilidade"]),
        }
        for indice, linha in df.iterrows()
    ]


def _turmas_configuradas(df: pd.DataFrame) -> int:
    valores = df.set_index("Recursos")["Quantidade"]
    return int(valores["turmas_manha"]) + int(valores["turmas_tarde"])


def _montar_turmas(df: pd.DataFrame, alunos: list[dict] | None = None) -> list[dict]:
    """Aba Turmas -> turmas nomeadas em sequência contínua (manhã primeiro).

    Se `alunos` for informado, usa só as turmas necessárias em cada turno:
    alunos / vagas, arredondado para cima (limitado ao que a planilha prevê).
    Os nomes continuam em sequência com as turmas que sobrarem.
    """
    valores = df.set_index("Recursos")["Quantidade"]

    plano = []  # (turno, quantidade de turmas, vagas por turma)
    for turno, sufixo in (("Manhã", "manha"), ("Tarde", "tarde")):
        configuradas = int(valores[f"turmas_{sufixo}"])
        vagas = int(valores[f"vagas_{sufixo}"])
        quantidade = configuradas
        if alunos is not None:
            n = sum(1 for a in alunos if a["turno"] == turno)
            quantidade = min(configuradas, -(-n // vagas))  # teto de n / vagas
        plano.append((turno, quantidade, vagas))

    total = sum(q for _, q, _ in plano)
    if total > 26:
        raise ValueError(f"São {total} turmas; o padrão de letras vai só até Z.")

    turmas, letra = [], 0
    for turno, quantidade, vagas in plano:
        for _ in range(quantidade):
            turmas.append({
                "turma": f"{turno.upper()} - {chr(65 + letra)}",
                "turno": turno,
                "vagas": vagas,
            })
            letra += 1
    return turmas


# ----------------------------------------------------------- inconsistências
# Regra: cada linha da aba Inconsistências é UMA inconsistência.

def _explodir_erro_geral(erro: str) -> list[str]:
    """'RECURSOS_TURMAS_AUSENTES: a, b' -> ['...: a', '...: b']."""
    codigo = erro.split(":", 1)[0].strip()
    if codigo not in CODIGOS_COM_LISTA or ":" not in erro:
        return [erro]
    itens = [i.strip() for i in erro.split(":", 1)[1].split(",") if i.strip()]
    return [f"{codigo}: {item}" for item in itens] or [erro]


def _linhas_inconsistencias(res) -> list[list]:
    """DataFrame de inconsistências do tratamento -> linhas [Linha, Coluna, Tipo, Detalhes].

    Os erros gerais que listavam vários itens são separados, um por linha.
    """
    df = getattr(res, "inconsistencias", None)
    if df is None or df.empty:
        return []

    linhas = []
    for _, r in df.iterrows():
        linha, coluna, tipo, detalhes = (r[c] for c in COLUNAS_INCONSISTENCIAS)
        if detalhes == ERRO_GERAL:
            linhas.extend(["-", "-", erro, ERRO_GERAL] for erro in _explodir_erro_geral(str(tipo)))
        else:
            linhas.append([linha, coluna, tipo, detalhes])
    return linhas


def _texto_da_linha(linha: list) -> str:
    """Texto curto de uma inconsistência para o log da tela."""
    n, coluna, tipo, detalhes = linha
    if detalhes == ERRO_GERAL:
        return str(tipo)
    onde = f"Linha {n}, coluna {coluna}" if str(n) != "-" else f"Coluna {coluna}"
    return f"{onde}: {tipo} — {detalhes}"


def _qtd_alunos_descartados(linhas: list[list]) -> int:
    return len({l[0] for l in linhas if str(l[3]).startswith(LINHA_DESCARTADA)})


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
    """Grava as duas abas no próprio Excel de entrada (substitui as antigas).

    Sem resultado, a aba Ensalamento fica só com o cabeçalho (como no template
    do cenário) e não sobra ensalamento antigo de outra execução.
    """
    wb = load_workbook(caminho)
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
    
    

def gerar_pdf_resumo(
    caminho_pdf: str,
    caminho_planilha: str,
    saida: dict,
    inconsistencias: list[list],
) -> None:

    doc = SimpleDocTemplate(caminho_pdf)

    styles = getSampleStyleSheet()

    titulo_style = ParagraphStyle(
        "TituloCentralizado",
        parent=styles["Title"],
        alignment=TA_CENTER,
    )

    elementos = []

    # ==========================================================
    # CABEÇALHO
    # ==========================================================

    try:
        logo = Path(__file__).parent / "logo_abc.png"

        if logo.exists():
            img = Image(
                str(logo),
                width=150,
                height=75,
            )

            img.hAlign = "CENTER"

            elementos.append(img)
            elementos.append(Spacer(1, 10))

    except Exception as exc:
        print(f"Erro ao carregar logo: {exc}")

    elementos.append(
        Paragraph(
            "ABC APRENDIZ",
            styles["Heading1"],
        )
    )

    elementos.append(
        Paragraph(
            "RELATÓRIO DE ENSALAMENTO",
            titulo_style,
        )
    )

    elementos.append(Spacer(1, 12))

    elementos.append(
        Paragraph(
            f"<b>Data/Hora da execução:</b> "
            f"{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
            styles["Normal"],
        )
    )

    elementos.append(
        Paragraph(
            f"<b>Planilha utilizada:</b> "
            f"{Path(caminho_planilha).name}",
            styles["Normal"],
        )
    )

    elementos.append(Spacer(1, 20))

    # ==========================================================
    # RESUMO EXECUTIVO
    # ==========================================================

    elementos.append(
        Paragraph(
            "Resumo Executivo",
            styles["Heading1"],
        )
    )

    metricas = saida["metricas"]

    total_alocados = metricas["total_alocados"]
    total_turmas = metricas["total_turmas"]
    total_inconsistencias = len(inconsistencias)

    elementos.append(
        Paragraph(
            f"Total de alunos alocados: "
            f"<b>{total_alocados}</b>",
            styles["Normal"],
        )
    )

    elementos.append(
        Paragraph(
            f"Total de turmas utilizadas: "
            f"<b>{total_turmas}</b>",
            styles["Normal"],
        )
    )

    elementos.append(
        Paragraph(
            f"Total de inconsistências encontradas: "
            f"<b>{total_inconsistencias}</b>",
            styles["Normal"],
        )
    )

    elementos.append(Spacer(1, 20))

    # ==========================================================
    # RESUMO DAS TURMAS
    # ==========================================================

    elementos.append(
        Paragraph(
            "Resumo das Turmas",
            styles["Heading1"],
        )
    )

    dados_resumo = [
        ["Turma", "Alunos", "Masculino", "Feminino"]
    ]

    for turma in saida["resumo"]:
        dados_resumo.append([
            turma["Turma"],
            turma["Alunos"],
            turma["Masculino"],
            turma["Feminino"],
        ])

    tabela_resumo = Table(
        dados_resumo,
        colWidths=[200, 80, 80, 80],
    )

    tabela_resumo.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e9b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
    ]))

    elementos.append(tabela_resumo)

    elementos.append(PageBreak())

    # ==========================================================
    # UMA PÁGINA POR TURMA
    # ==========================================================

    turmas_alunos = defaultdict(list)

    for aluno in saida["alocacao"]:
        turmas_alunos[aluno["Turma"]].append(aluno)

    resumo_por_turma = {
        turma["Turma"]: turma
        for turma in saida["resumo"]
    }

    turmas_ordenadas = sorted(turmas_alunos.keys())

    for indice, nome_turma in enumerate(turmas_ordenadas):

        alunos = turmas_alunos[nome_turma]

        elementos.append(
            Paragraph(
                f"Turma {nome_turma}",
                styles["Title"],
            )
        )

        elementos.append(Spacer(1, 8))

        info = resumo_por_turma.get(nome_turma)

        if info:

            elementos.append(
                Paragraph(
                    f"Total de alunos: <b>{info['Alunos']}</b>",
                    styles["Normal"],
                )
            )

            elementos.append(
                Paragraph(
                    f"Masculinos: <b>{info['Masculino']}</b>",
                    styles["Normal"],
                )
            )

            elementos.append(
                Paragraph(
                    f"Femininos: <b>{info['Feminino']}</b>",
                    styles["Normal"],
                )
            )

        elementos.append(Spacer(1, 12))

        dados_alunos = [
            ["#", "Nome", "Sexo", "Turno"]
        ]

        for posicao, aluno in enumerate(
            sorted(
                alunos,
                key=lambda x: x["Nome do aluno"]
            ),
            start=1
        ):
            dados_alunos.append([
                posicao,
                aluno["Nome do aluno"],
                aluno["Sexo"],
                aluno["Disponibilidade"],
            ])

        tabela_alunos = Table(
            dados_alunos,
            colWidths=[30, 320, 50, 90],
        )

        tabela_alunos.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e9b")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))

        elementos.append(tabela_alunos)

        
        elementos.append(PageBreak())

    # ==========================================================
    # INCONSISTÊNCIAS
    # ==========================================================

    elementos.append(
        Paragraph(
            "Inconsistências Encontradas",
            styles["Heading1"],
        )
    )

    elementos.append(Spacer(1, 10))

    if inconsistencias:

        elementos.append(
            Paragraph(
                f"Total de inconsistências: <b>{len(inconsistencias)}</b>",
                styles["Normal"],
            )
        )

        elementos.append(Spacer(1, 8))

        for inconsistencia in inconsistencias:

            elementos.append(
                Paragraph(
                    f"• {_texto_da_linha(inconsistencia)}",
                    styles["Normal"],
                )
            )

    else:

        elementos.append(
            Paragraph(
                "Nenhuma inconsistência encontrada.",
                styles["Normal"],
            )
        )

    elementos.append(PageBreak())

    doc.build(elementos)



# ------------------------------------------------------------------ front

def _resposta(
    ok,
    mensagem,
    inconsistencias=(),
    turmas=(),
    arquivo_gerado=False,
    pdf=None,
):
    return {
        "ok": ok,
        "mensagem": mensagem,
        "inconsistencias": [_texto_da_linha(l) for l in inconsistencias],
        "turmas": list(turmas),
        "arquivo_gerado": arquivo_gerado,
        "pdf": pdf,
    }


def _bloquear(caminho, inconsistencias, mensagem):
    """Não dá para ensalar: grava as abas (Ensalamento vazio) e avisa o front."""
    gravou, erro = _tentar_gravar(caminho, [], inconsistencias)
    return _resposta(False, erro or mensagem, inconsistencias, arquivo_gerado=gravou)


def executar_ensalamento(caminho: str | None, usar_so_necessarias: bool = False) -> dict:
    """Fluxo completo. Devolve o dict que o scripts.js espera.

    usar_so_necessarias=False (padrão): usa todas as turmas da aba Turmas.
    usar_so_necessarias=True: abre só as turmas que os alunos exigem.
    """
    if not caminho or not Path(caminho).is_file():
        return _resposta(False, "Nenhuma planilha válida selecionada.")

    res = processar_excel(caminho)
    inconsistencias = _linhas_inconsistencias(res)

    # 1) Erro que impede o ensalamento (abas, colunas, Turmas, capacidade...):
    #    não roda o modelo; grava só as inconsistências.
    if res.status != "OK":
        gerais = [l for l in inconsistencias if l[3] == ERRO_GERAL]
        if not gerais:  # erro sem registro no DataFrame (ex.: arquivo inválido)
            gerais = [["-", "-", e, ERRO_GERAL] for e in res.erros]
            inconsistencias += gerais
        msg = gerais[0][2] if len(gerais) == 1 else f"{len(gerais)} problemas impedem o ensalamento"
        return _bloquear(caminho, inconsistencias, msg)

    # 2) Otimização com os alunos válidos que o tratamento devolveu.
    try:
        alunos = _montar_alunos(res.alunos)
        turmas_modelo = _montar_turmas(res.turmas, alunos if usar_so_necessarias else None)
        saida = otimizar_ensalamento(
            alunos, turmas_modelo, time_limit=TEMPO_LIMITE_POR_ETAPA,
        )
    except Exception as exc:
        inconsistencias.append(["-", "-", f"Falha no modelo: {exc}", ERRO_GERAL])
        return _bloquear(caminho, inconsistencias, f"Falha no modelo: {exc}")

    # 3) Grava as abas e responde.
    linhas = [
        [r["Nome do aluno"], r["Sexo"], r["Disponibilidade"], r["Turma"]]
        for r in saida["alocacao"]
    ]
    gravou, erro = _tentar_gravar(caminho, linhas, inconsistencias)
    if not gravou:
        return _resposta(False, erro, inconsistencias)
    
    pdf_path = None

    try:
        pdf_path = str(
            Path(caminho).with_name(
                f"{Path(caminho).stem}_resumo.pdf"
            )
        )

        gerar_pdf_resumo(
            pdf_path,
            caminho,
            saida,
            inconsistencias,
        )

    except Exception as exc:
        print(f"Erro ao gerar PDF: {exc}")
        pdf_path = None

    m = saida["metricas"]
    n_alunos, n_turmas = m["total_alocados"], m["total_turmas"]
    mensagem = (
        f"{n_alunos} {'aluno alocado' if n_alunos == 1 else 'alunos alocados'} "
        f"em {n_turmas} {'turma' if n_turmas == 1 else 'turmas'}"
    )
    disponiveis = _turmas_configuradas(res.turmas)
    if usar_so_necessarias and m["total_turmas"] < disponiveis:
        mensagem += f" (de {disponiveis} disponíveis)"
    sem_turma = _qtd_alunos_descartados(inconsistencias)
    if sem_turma:
        mensagem += f" · {sem_turma} sem turma (dados inválidos)"
    turmas = [
        {"turma": r["Turma"], "total": r["Alunos"],
         "m": r["Masculino"], "f": r["Feminino"]}
        for r in saida["resumo"]
    ]
    return _resposta(
    True,
    mensagem,
    inconsistencias,
    turmas,
    arquivo_gerado=True,
    pdf=pdf_path,
    )