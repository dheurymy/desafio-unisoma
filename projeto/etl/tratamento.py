"""Validação determinística dos dados de entrada do ensalamento."""

from __future__ import annotations

import argparse
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pandas as pd


# Define os estados possíveis do resultado do tratamento.
Status = Literal["OK", "ERRO"]

# Define as colunas, recursos e valores aceitos nas planilhas.
COLUNAS_ALUNOS = {"Nome", "Sexo", "Disponibilidade"}
COLUNAS_TURMAS = {"Recursos", "Quantidade"}
RECURSOS_OBRIGATORIOS = {
    "turmas_manha",
    "turmas_tarde",
    "vagas_manha",
    "vagas_tarde",
}
SEXOS_VALIDOS = {"m", "f"}
DISPONIBILIDADES_VALIDAS = {"manha", "tarde"}

# Controla a gravação temporária dos DataFrames para conferência manual.
SALVAR_DATAFRAMES_DEBUG = True


# Armazena os dados tratados, mensagens e inconsistências encontradas.
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
    inconsistencias: pd.DataFrame | None = None


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


# Converte um valor para texto e remove espaços nas extremidades.
def _texto(valor: object) -> str:
    """Converte um valor para texto sem considerar espaços nas extremidades."""
    return str(valor).strip()


# Normaliza texto para comparações sem diferença de maiúsculas ou acentos.
def _chave_texto(valor: object) -> str:
    """Gera uma chave para comparar maiúsculas e acentos de forma segura."""
    texto = unicodedata.normalize("NFKD", _texto(valor))
    sem_acento = "".join(caractere for caractere in texto if not unicodedata.combining(caractere))
    return sem_acento.casefold()


# Corrige os nomes das três primeiras colunas conforme suas posições esperadas.
def revisar_colunas(
    alunos: pd.DataFrame,
) -> tuple[pd.DataFrame, list[dict[str, object]]]:
    """Corrige títulos usando a posição fixa das três colunas de alunos."""
    nomes_esperados = ["Nome", "Sexo", "Disponibilidade"]
    if len(alunos.columns) < len(nomes_esperados):
        return alunos, []

    alunos_corrigidos = alunos.copy()
    colunas = list(alunos_corrigidos.columns)
    correcoes: list[dict[str, object]] = []

    for posicao, nome_esperado in enumerate(nomes_esperados):
        nome_atual = _texto(colunas[posicao])
        if nome_atual != nome_esperado:
            correcoes.append(
                {
                    "Linha": "-",
                    "Coluna": nome_esperado,
                    "Tipo de erro": "Cabeçalho corrigido automaticamente",
                    "Detalhes": (
                        f"'{nome_atual}' -> '{nome_esperado}'"
                    ),
                }
            )
            colunas[posicao] = nome_esperado

    alunos_corrigidos.columns = colunas
    return alunos_corrigidos, correcoes


# Corrige automaticamente valores textuais conhecidos em sexo e disponibilidade.
def revisar_textos(
    alunos: pd.DataFrame,
) -> tuple[pd.DataFrame, list[dict[str, object]]]:
    """Corrige somente equivalências textuais conhecidas nas colunas permitidas."""
    alunos_corrigidos = alunos.copy()
    correcoes: list[dict[str, object]] = []

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
                {
                    "Linha": posicao + 2,
                    "Coluna": coluna,
                    "Tipo de erro": "Valor corrigido automaticamente",
                    "Detalhes": f"'{original}' -> '{corrigido}'",
                }
            )

    return alunos_corrigidos, correcoes


# Separa linhas inválidas e registra os motivos para removê-las.
def separar_inconsistencias(
    alunos: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Remove linhas inválidas e registra cada inconsistência encontrada."""
    registros: list[dict[str, object]] = []
    indices_validos: list[object] = []

    for indice in alunos.index:
        linha = alunos.loc[indice]
        erros_linha: list[tuple[str, str]] = []

        nome = linha.get("Nome")
        if pd.isna(nome) or _texto(nome) == "":
            erros_linha.append(("Nome", "Valor Ausente na Coluna Nome"))
        elif not isinstance(nome, str):
            erros_linha.append(("Nome", "Tipo Inválido na Coluna Nome"))

        sexo = linha.get("Sexo")
        if pd.isna(sexo) or _texto(sexo) == "":
            erros_linha.append(("Sexo", "Valor Ausente na Coluna Sexo"))
        elif _chave_texto(sexo) not in SEXOS_VALIDOS:
            erros_linha.append(("Sexo", "Valor Inválido na Coluna Sexo"))

        disponibilidade = linha.get("Disponibilidade")
        if pd.isna(disponibilidade) or _texto(disponibilidade) == "":
            erros_linha.append(
                (
                    "Disponibilidade",
                    "Valor Ausente na Coluna Disponibilidade",
                )
            )
        elif _chave_texto(disponibilidade) not in DISPONIBILIDADES_VALIDAS:
            erros_linha.append(
                (
                    "Disponibilidade",
                    "Valor Inválido na Coluna Disponibilidade",
                )
            )

        if erros_linha:
            for coluna, tipo in erros_linha:
                registros.append(
                    {
                        "Linha": int(indice) + 2,
                        "Coluna": coluna,
                        "Tipo de erro": tipo,
                        "Detalhes": "Registro descartado do DataFrame de alunos",
                    }
                )
        else:
            indices_validos.append(indice)

    alunos_validos = alunos.loc[indices_validos]
    inconsistencias = pd.DataFrame(
        registros,
        columns=["Linha", "Coluna", "Tipo de erro", "Detalhes"],
    )
    return alunos_validos, inconsistencias


# Identifica nomes repetidos no mesmo turno sem remover os alunos.
def identificar_duplicidades(alunos: pd.DataFrame) -> pd.DataFrame:
    """Registra nomes repetidos quando a disponibilidade também é igual."""
    registros: list[dict[str, object]] = []
    chaves = pd.DataFrame(
        {
            "nome": alunos["Nome"].map(_chave_texto),
            "disponibilidade": alunos["Disponibilidade"].map(_chave_texto),
        },
        index=alunos.index,
    )
    quantidade_por_grupo = chaves.groupby(
        ["nome", "disponibilidade"]
    )["nome"].transform("size")

    for indice in alunos.index:
        if quantidade_por_grupo.loc[indice] <= 1:
            continue

        nome = _texto(alunos.at[indice, "Nome"])
        disponibilidade = _texto(alunos.at[indice, "Disponibilidade"])
        registros.append(
            {
                "Linha": int(indice) + 2,
                "Coluna": "Nome",
                "Tipo de erro": "Aluno duplicado no mesmo turno",
                "Detalhes": (
                    f"'{nome}' aparece mais de uma vez no turno "
                    f"'{disponibilidade}'"
                ),
            }
        )

    return pd.DataFrame(
        registros,
        columns=["Linha", "Coluna", "Tipo de erro", "Detalhes"],
    )


# Salva cópias CSV dos DataFrames para inspeção durante o desenvolvimento.
def salvar_dataframes_debug(
    alunos: pd.DataFrame,
    inconsistencias: pd.DataFrame,
) -> None:
    """Salva cópias CSV dos DataFrames para conferência manual."""
    pasta_debug = Path(__file__).resolve().parents[1] / "dados" / "debug"
    pasta_debug.mkdir(parents=True, exist_ok=True)
    alunos.to_csv(
        pasta_debug / "alunos_tratados.csv",
        index=False,
        encoding="utf-8-sig",
    )
    inconsistencias.to_csv(
        pasta_debug / "inconsistencias.csv",
        index=False,
        encoding="utf-8-sig",
    )
    print(f"DataFrames de debug salvos em: {pasta_debug}")


# Valida colunas, preenchimento e valores da planilha de alunos.
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

    disponibilidades = alunos["Disponibilidade"].dropna().map(_chave_texto)
    disponibilidades_invalidas = sorted(
        set(disponibilidades) - DISPONIBILIDADES_VALIDAS
    )
    if disponibilidades_invalidas:
        erros.append(
            "VALOR_DISPONIBILIDADE_INVALIDO: "
            + ", ".join(disponibilidades_invalidas)
        )

    return erros


# Valida recursos, quantidades e configurações das turmas.
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


# Verifica se há vagas suficientes para os alunos de cada turno.
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
            alunos["Disponibilidade"].map(_chave_texto)
            == _chave_texto(periodo)
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


# Reúne todas as validações aplicáveis à instância carregada.
def validar_dados(
    alunos: pd.DataFrame, turmas: pd.DataFrame
) -> list[str]:
    """Retorna todos os erros objetivos encontrados nos dados."""
    return _validar_alunos(alunos) + _validar_turmas(turmas)


# Coordena leitura, correções, filtragem, validação e retorno dos DataFrames.
def processar_excel(caminho_arquivo: str | Path) -> ResultadoTratamento:
    """Lê, valida e informa o resultado de uma instância Excel."""
    caminho = Path(caminho_arquivo)

    if not caminho.is_file():
        mensagem = f"ARQUIVO_NAO_ENCONTRADO: {caminho}"
        print(f"ERRO: {mensagem}")
        return ResultadoTratamento("ERRO", mensagem, [mensagem])

    # Carrega todas as abas do arquivo Excel.
    try:
        planilhas = pd.read_excel(caminho, sheet_name=None)
    except (OSError, ValueError) as exc:
        mensagem = f"ARQUIVO_INVALIDO: {exc}"
        print(f"ERRO: {mensagem}")
        return ResultadoTratamento("ERRO", mensagem, [mensagem])

    # Confere se as abas essenciais existem.
    erros: list[str] = []
    abas_obrigatorias = {"Alunos", "Turmas"}
    abas_ausentes = abas_obrigatorias - set(planilhas)
    if abas_ausentes:
        erros.append("ABAS_AUSENTES: " + ", ".join(sorted(abas_ausentes)))

    alunos = planilhas.get("Alunos")
    turmas = planilhas.get("Turmas")
    erros_iniciais = list(erros)
    correcoes: list[str] = []
    inconsistencias = pd.DataFrame(
        columns=["Linha", "Coluna", "Tipo de erro", "Detalhes"]
    )
    if alunos is not None and turmas is not None:
        # Registra os problemas encontrados antes de qualquer correção.
        erros_iniciais.extend(validar_dados(alunos, turmas))

        # Corrige cabeçalhos e valores textuais previamente conhecidos.
        alunos, correcoes_colunas = revisar_colunas(alunos)
        alunos, correcoes_textos = revisar_textos(alunos)
        correcoes_registros = correcoes_colunas + correcoes_textos
        correcoes = [
            f"Linha {registro['Linha']}, coluna {registro['Coluna']}: "
            f"{registro['Detalhes']}"
            for registro in correcoes_registros
        ]
        if correcoes_registros:
            inconsistencias = pd.DataFrame(
                correcoes_registros,
                columns=["Linha", "Coluna", "Tipo de erro", "Detalhes"],
            )

        # Remove linhas inválidas e reúne as inconsistências informativas.
        if COLUNAS_ALUNOS.issubset(alunos.columns):
            alunos, inconsistencias_alunos = separar_inconsistencias(alunos)
            duplicidades = identificar_duplicidades(alunos)
            inconsistencias = pd.concat(
                [inconsistencias, inconsistencias_alunos, duplicidades],
                ignore_index=True,
            )
            if not duplicidades.empty:
                quantidade_duplicidades = len(duplicidades)
                erros_iniciais.append(
                    f"{quantidade_duplicidades} aluno(s) duplicado(s) "
                    "encontrado(s) no mesmo turno;"
                )

        # DEBUG: remover este bloco quando não precisar mais conferir os DataFrames.
        if SALVAR_DATAFRAMES_DEBUG:
            salvar_dataframes_debug(alunos, inconsistencias)

        # Valida novamente os dados depois das correções e remoções.
        erros = list(erros) + validar_dados(alunos, turmas)
        print(f"DataFrame de alunos válidos: {len(alunos)} linha(s)")
        print(
            "DataFrame de inconsistências: "
            f"{len(inconsistencias)} linha(s)"
        )

        if erros:
            registros_globais = pd.DataFrame(
                [
                    {
                        "Linha": "-",
                        "Coluna": "-",
                        "Tipo de erro": erro,
                        "Detalhes": "Erro geral da instância",
                    }
                    for erro in erros
                ],
                columns=["Linha", "Coluna", "Tipo de erro", "Detalhes"],
            )
            inconsistencias = pd.concat(
                [inconsistencias, registros_globais], ignore_index=True
            )

    # Exibe o diagnóstico inicial e as correções realizadas.
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

    # Interrompe o fluxo se ainda houver erros bloqueantes.
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
            inconsistencias,
        )

    # Retorna os DataFrames quando os dados estão prontos para a modelagem.
    mensagem = (
        "OK: dados prontos para a modelagem. "
        f"{len(inconsistencias)} inconsistência(s) registrada(s)."
    )
    print(mensagem)
    return ResultadoTratamento(
        "OK",
        mensagem,
        [],
        alunos,
        turmas,
        erros_iniciais,
        correcoes,
        inconsistencias,
    )


# Permite executar o tratamento diretamente pelo terminal.
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Valida os dados de uma instância Excel."
    )
    parser.add_argument("arquivo", type=Path, help="Caminho do arquivo .xlsx")
    args = parser.parse_args()
    processar_excel(args.arquivo)


if __name__ == "__main__":
    main()
