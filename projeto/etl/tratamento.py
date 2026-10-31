"""Validação determinística dos dados de entrada do ensalamento."""

from __future__ import annotations

import argparse
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pandas as pd


Status = Literal["OK", "ERRO"]

COLUNAS_ALUNOS = {"Nome", "Sexo", "Disponibilidade"}
COLUNAS_TURMAS = {"Recursos", "Quantidade"}
RECURSOS_OBRIGATORIOS = {
    "turmas_manha",
    "turmas_tarde",
    "vagas_manha",
    "vagas_tarde",
}
SEXOS_VALIDOS = {"m", "f"}
DISPONIBILIDADES_VALIDAS = {"manhã", "tarde"}


@dataclass
class ResultadoTratamento:
    """Resultado da leitura e validação de uma instância."""

    status: Status
    mensagem: str
    erros: list[str]
    alunos: pd.DataFrame | None = None
    turmas: pd.DataFrame | None = None
    erros_iniciais: list[str] | None = None
    correcoes: list[str] | None = None


CORRECOES_SEXO = {
    "f": "F",
    "feminino": "F",
    "Feminino": "F",
    "fem": "F",
    "FEM": "F",
    "mulher": "F",
    "m": "M",
    "masculino": "M",
    "homem": "M",
    "Masculino": "M",
    "masc": "M",
    "MASC": "M",
}
CORRECOES_DISPONIBILIDADE = {
    "manha": "Manhã",
    "manhã": "Manhã",
    "matutino": "Manhã",
    "matutina": "Manhã",
    "tarde": "Tarde",
    "vespertino": "Tarde",
    "vespertina": "Tarde",
}


def _texto(valor: object) -> str:
    """Converte um valor para texto sem considerar espaços nas extremidades."""
    return str(valor).strip()


def _chave_texto(valor: object) -> str:
    """Gera uma chave para comparar maiúsculas e acentos de forma segura."""
    texto = unicodedata.normalize("NFKD", _texto(valor))
    sem_acento = "".join(caractere for caractere in texto if not unicodedata.combining(caractere))
    return sem_acento.casefold()


def revisar_colunas(alunos: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Corrige títulos usando a posição fixa das três colunas de alunos."""
    nomes_esperados = ["Nome", "Sexo", "Disponibilidade"]
    if len(alunos.columns) < len(nomes_esperados):
        return alunos, []

    alunos_corrigidos = alunos.copy()
    colunas = list(alunos_corrigidos.columns)
    correcoes: list[str] = []

    for posicao, nome_esperado in enumerate(nomes_esperados):
        nome_atual = _texto(colunas[posicao])
        if nome_atual != nome_esperado:
            correcoes.append(
                f"Cabeçalho da coluna {posicao + 1}: "
                f"'{nome_atual}' -> '{nome_esperado}'"
            )
            colunas[posicao] = nome_esperado

    alunos_corrigidos.columns = colunas
    return alunos_corrigidos, correcoes


def revisar_textos(alunos: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Corrige somente equivalências textuais conhecidas nas colunas permitidas."""
    alunos_corrigidos = alunos.copy()
    correcoes: list[str] = []

    for coluna, mapa in (
        ("Sexo", CORRECOES_SEXO),
        ("Disponibilidade", CORRECOES_DISPONIBILIDADE),
    ):
        if coluna not in alunos_corrigidos.columns:
            continue

        for posicao, indice in enumerate(alunos_corrigidos.index):
            valor = alunos_corrigidos.at[indice, coluna]
            if pd.isna(valor):
                continue

            original = _texto(valor)
            corrigido = mapa.get(_chave_texto(original))
            if corrigido is None or original == corrigido:
                continue

            alunos_corrigidos.at[indice, coluna] = corrigido
            correcoes.append(
                f"Alunos, linha {posicao + 2}, coluna {coluna}: "
                f"'{original}' -> '{corrigido}'"
            )

    return alunos_corrigidos, correcoes


def _validar_alunos(alunos: pd.DataFrame) -> list[str]:
    erros: list[str] = []
    colunas_ausentes = COLUNAS_ALUNOS - set(alunos.columns)

    if colunas_ausentes:
        erros.append(
            "COLUNAS_ALUNOS_AUSENTES: "
            + ", ".join(sorted(colunas_ausentes))
        )
        return erros

    if alunos.empty:
        erros.append("DADOS_ALUNOS_AUSENTES: a planilha Alunos está vazia")
        return erros

    nomes_nao_texto = [
        str(indice + 2)
        for indice, valor in alunos["Nome"].items()
        if not pd.isna(valor) and not isinstance(valor, str)
    ]
    if nomes_nao_texto:
        erros.append(
            "TIPO_NOME_INVALIDO: valores não textuais nas linhas "
            + ", ".join(nomes_nao_texto)
        )

    obrigatorias = alunos[["Nome", "Sexo", "Disponibilidade"]]
    linhas_com_vazio = obrigatorias.isna().any(axis=1)
    linhas_com_texto_vazio = obrigatorias.astype(str).apply(
        lambda coluna: coluna.str.strip().eq("")
    ).any(axis=1)
    linhas_invalidas = linhas_com_vazio | linhas_com_texto_vazio

    if linhas_invalidas.any():
        linhas = [str(indice + 2) for indice in alunos.index[linhas_invalidas]]
        erros.append(
            "DADOS_ALUNOS_AUSENTES: campos obrigatórios vazios nas linhas "
            + ", ".join(linhas)
        )

    sexos = alunos["Sexo"].dropna().map(_texto).str.casefold()
    sexos_invalidos = sorted(set(sexos) - SEXOS_VALIDOS)
    if sexos_invalidos:
        erros.append("VALOR_SEXO_INVALIDO: " + ", ".join(sexos_invalidos))

    disponibilidades = (
        alunos["Disponibilidade"].dropna().map(_texto).str.casefold()
    )
    disponibilidades_invalidas = sorted(
        set(disponibilidades) - DISPONIBILIDADES_VALIDAS
    )
    if disponibilidades_invalidas:
        erros.append(
            "VALOR_DISPONIBILIDADE_INVALIDO: "
            + ", ".join(disponibilidades_invalidas)
        )

    return erros


def _validar_turmas(turmas: pd.DataFrame) -> list[str]:
    erros: list[str] = []
    colunas_ausentes = COLUNAS_TURMAS - set(turmas.columns)

    if colunas_ausentes:
        erros.append(
            "COLUNAS_TURMAS_AUSENTES: "
            + ", ".join(sorted(colunas_ausentes))
        )
        return erros

    if turmas.empty:
        return ["DADOS_TURMAS_AUSENTES: a planilha Turmas está vazia"]

    recursos = turmas["Recursos"].dropna().map(_texto)
    recursos_encontrados = set(recursos)
    recursos_ausentes = RECURSOS_OBRIGATORIOS - recursos_encontrados
    if recursos_ausentes:
        erros.append(
            "RECURSOS_TURMAS_AUSENTES: "
            + ", ".join(sorted(recursos_ausentes))
        )

    recursos_repetidos = recursos[recursos.duplicated()].unique()
    if len(recursos_repetidos) > 0:
        erros.append(
            "RECURSOS_TURMAS_REPETIDOS: "
            + ", ".join(sorted(recursos_repetidos))
        )

    valores = turmas.set_index("Recursos")["Quantidade"]
    for recurso in sorted(RECURSOS_OBRIGATORIOS & recursos_encontrados):
        valor = valores[recurso]
        if pd.isna(valor):
            erros.append(f"QUANTIDADE_AUSENTE: {recurso}")
            continue

        try:
            numero = float(valor)
        except (TypeError, ValueError):
            erros.append(f"QUANTIDADE_INVALIDA: {recurso}={valor}")
            continue

        if not numero.is_integer() or numero <= 0:
            erros.append(f"QUANTIDADE_INVALIDA: {recurso}={valor}")

    return erros


def _validar_capacidade(
    alunos: pd.DataFrame, turmas: pd.DataFrame
) -> list[str]:
    """Verifica apenas a capacidade objetiva informada no arquivo."""
    if _validar_alunos(alunos) or _validar_turmas(turmas):
        return []

    erros: list[str] = []
    valores = turmas.set_index("Recursos")["Quantidade"]
    for periodo, nome_periodo in (("manhã", "manha"), ("tarde", "tarde")):
        quantidade_alunos = (
            alunos["Disponibilidade"].map(_texto).str.casefold() == periodo
        ).sum()
        capacidade = int(valores[f"turmas_{nome_periodo}"]) * int(
            valores[f"vagas_{nome_periodo}"]
        )
        if quantidade_alunos > capacidade:
            erros.append(
                "CAPACIDADE_INSUFICIENTE: "
                f"{periodo} possui {quantidade_alunos} alunos e "
                f"capacidade para {capacidade}"
            )

    return erros


def validar_dados(
    alunos: pd.DataFrame, turmas: pd.DataFrame
) -> list[str]:
    """Retorna todos os erros objetivos encontrados nos dados."""
    erros = _validar_alunos(alunos) + _validar_turmas(turmas)
    if not erros:
        erros.extend(_validar_capacidade(alunos, turmas))
    return erros


def processar_excel(caminho_arquivo: str | Path) -> ResultadoTratamento:
    """Lê, valida e informa o resultado de uma instância Excel."""
    caminho = Path(caminho_arquivo)

    if not caminho.is_file():
        mensagem = f"ARQUIVO_NAO_ENCONTRADO: {caminho}"
        print(f"ERRO: {mensagem}")
        return ResultadoTratamento("ERRO", mensagem, [mensagem])

    try:
        planilhas = pd.read_excel(caminho, sheet_name=None)
    except (OSError, ValueError) as exc:
        mensagem = f"ARQUIVO_INVALIDO: {exc}"
        print(f"ERRO: {mensagem}")
        return ResultadoTratamento("ERRO", mensagem, [mensagem])

    erros: list[str] = []
    abas_obrigatorias = {"Alunos", "Turmas"}
    abas_ausentes = abas_obrigatorias - set(planilhas)
    if abas_ausentes:
        erros.append("ABAS_AUSENTES: " + ", ".join(sorted(abas_ausentes)))

    alunos = planilhas.get("Alunos")
    turmas = planilhas.get("Turmas")
    erros_iniciais = list(erros)
    correcoes: list[str] = []
    if alunos is not None and turmas is not None:
        erros_iniciais.extend(validar_dados(alunos, turmas))
        alunos, correcoes_colunas = revisar_colunas(alunos)
        alunos, correcoes_textos = revisar_textos(alunos)
        correcoes = correcoes_colunas + correcoes_textos
        erros = list(erros) + validar_dados(alunos, turmas)

    print("ERROS INICIAIS:")
    if erros_iniciais:
        for erro in erros_iniciais:
            print(f"- {erro}")
    else:
        print("- nenhum")

    print("CORREÇÕES AUTOMÁTICAS:")
    if correcoes:
        for correcao in correcoes:
            print(f"- {correcao}")
    else:
        print("- nenhuma")

    if erros:
        mensagem = "Dados inválidos após a revisão textual."
        print("ERROS FINAIS:")
        for erro in erros:
            print(f"- {erro}")
        return ResultadoTratamento(
            "ERRO",
            mensagem,
            erros,
            alunos,
            turmas,
            erros_iniciais,
            correcoes,
        )

    mensagem = "OK: dados prontos para a modelagem."
    print(mensagem)
    return ResultadoTratamento(
        "OK", mensagem, [], alunos, turmas, erros_iniciais, correcoes
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Valida os dados de uma instância Excel."
    )
    parser.add_argument("arquivo", type=Path, help="Caminho do arquivo .xlsx")
    args = parser.parse_args()
    processar_excel(args.arquivo)


if __name__ == "__main__":
    main()
