from collections import defaultdict
import pulp

from .restricoes import (
    criar_variaveis_alocacao,
    adicionar_alocacao_unica,
    adicionar_capacidade,
    criar_limites_de_quantidade,
    preservar_equilibrio_de_quantidade,
)
from .objetivo import (
    objetivo_equilibrio_quantidade,
    criar_desvios_de_genero,
    objetivo_equilibrio_genero,
)


TURNOS_VALIDOS = {"Manhã", "Tarde"}
SEXOS_VALIDOS = {"M", "F"}


def _validar_entrada(alunos, turmas):
    if not isinstance(alunos, list) or not isinstance(turmas, list):
        raise TypeError("alunos e turmas devem ser listas de dicionários.")

    if not alunos:
        raise ValueError("A lista de alunos está vazia.")
    if not turmas:
        raise ValueError("A lista de turmas está vazia.")

    ids = [a.get("id") for a in alunos]
    if any(i is None for i in ids):
        raise ValueError("Todo aluno precisa ter um campo 'id'.")
    if len(ids) != len(set(ids)):
        raise ValueError("Os IDs dos alunos devem ser únicos.")

    nomes_turmas = [t.get("turma") for t in turmas]
    if any(not nome for nome in nomes_turmas):
        raise ValueError("Toda turma precisa ter um nome.")
    if len(nomes_turmas) != len(set(nomes_turmas)):
        raise ValueError("Os nomes das turmas devem ser únicos.")

    for aluno in alunos:
        campos = ("nome", "sexo", "turno")
        faltantes = [c for c in campos if c not in aluno]
        if faltantes:
            raise ValueError(
                f"Aluno ID {aluno['id']} sem campos: {', '.join(faltantes)}."
            )
        if aluno["sexo"] not in SEXOS_VALIDOS:
            raise ValueError(
                f"Sexo inválido para o aluno ID {aluno['id']}: "
                f"{aluno['sexo']!r}. Use M ou F."
            )
        if aluno["turno"] not in TURNOS_VALIDOS:
            raise ValueError(
                f"Turno inválido para o aluno ID {aluno['id']}: "
                f"{aluno['turno']!r}. Use Manhã ou Tarde."
            )

    for turma in turmas:
        if "turno" not in turma or turma["turno"] not in TURNOS_VALIDOS:
            raise ValueError(
                f"Turno inválido na turma {turma.get('turma')!r}."
            )
        vagas = turma.get("vagas")
        if isinstance(vagas, bool) or not isinstance(vagas, int) or vagas <= 0:
            raise ValueError(
                f"As vagas da turma {turma['turma']!r} "
                "devem ser um inteiro positivo."
            )

    for turno in TURNOS_VALIDOS:
        qtd_alunos = sum(a["turno"] == turno for a in alunos)
        capacidade = sum(
            t["vagas"] for t in turmas if t["turno"] == turno
        )
        if qtd_alunos > capacidade:
            raise ValueError(
                f"Capacidade insuficiente no turno {turno}: "
                f"{qtd_alunos} alunos para {capacidade} vagas."
            )
        if qtd_alunos > 0 and capacidade == 0:
            raise ValueError(f"Não existem turmas para o turno {turno}.")


def _resolver(modelo, solver, etapa):
    status_codigo = modelo.solve(solver)
    status = pulp.LpStatus[status_codigo]
    if status != "Optimal":
        raise RuntimeError(
            f"A etapa '{etapa}' não encontrou solução ótima. "
            f"Status retornado pelo solver: {status}."
        )


def otimizar_ensalamento(alunos, turmas, msg_solver=False, time_limit=None):
  
    _validar_entrada(alunos, turmas)

    modelo = pulp.LpProblem("Ensalamento_ONG", pulp.LpMinimize)
    x = criar_variaveis_alocacao(alunos, turmas)

    adicionar_alocacao_unica(modelo, alunos, turmas, x)
    adicionar_capacidade(modelo, alunos, turmas, x)

    menores, maiores, quantidades = criar_limites_de_quantidade(
        modelo, alunos, turmas, x
    )

    solver_kwargs = {"msg": msg_solver}
    if time_limit is not None:
        solver_kwargs["timeLimit"] = time_limit
    solver = pulp.PULP_CBC_CMD(**solver_kwargs)

    # ETAPA 1: otimizar equilíbrio de quantidade.
    modelo.setObjective(
        objetivo_equilibrio_quantidade(menores, maiores)
    )
    _resolver(modelo, solver, "equilíbrio de quantidade")

    melhor_amplitude = {}
    for turno in menores:
        valor = pulp.value(maiores[turno] - menores[turno])
        melhor_amplitude[turno] = int(round(valor))

    # ETAPA 2: preservar o melhor equilíbrio de quantidade e
    # otimizar a proporção de gênero.
    preservar_equilibrio_de_quantidade(
        modelo, menores, maiores, melhor_amplitude
    )
    desvios = criar_desvios_de_genero(modelo, alunos, turmas, x)
    modelo.setObjective(objetivo_equilibrio_genero(desvios))
    _resolver(modelo, solver, "equilíbrio de gênero")

    alocacao = []
    por_turma = defaultdict(list)

    for aluno in alunos:
        turma_escolhida = None
        for turma in turmas:
            chave = (aluno["id"], turma["turma"])
            if chave in x and pulp.value(x[chave]) > 0.5:
                turma_escolhida = turma
                break

        if turma_escolhida is None:
            raise RuntimeError(
                f"O aluno ID {aluno['id']} não foi encontrado na solução."
            )

        registro = {
            "id": aluno["id"],
            "Nome do aluno": aluno["nome"],
            "Sexo": aluno["sexo"],
            "Disponibilidade": aluno["turno"],
            "Turma": turma_escolhida["turma"],
        }
        alocacao.append(registro)
        por_turma[turma_escolhida["turma"]].append(aluno)

    resumo = []
    for turma in turmas:
        grupo = por_turma[turma["turma"]]
        masculino = sum(a["sexo"] == "M" for a in grupo)
        feminino = sum(a["sexo"] == "F" for a in grupo)
        total = len(grupo)

        resumo.append({
            "Turma": turma["turma"],
            "Turno": turma["turno"],
            "Vagas": turma["vagas"],
            "Alunos": total,
            "Vagas restantes": turma["vagas"] - total,
            "Masculino": masculino,
            "Feminino": feminino,
            "Diferença M-F": abs(masculino - feminino),
            "Percentual masculino": (
                round(100 * masculino / total, 2) if total else 0.0
            ),
            "Percentual feminino": (
                round(100 * feminino / total, 2) if total else 0.0
            ),
        })

    total_alocados = len(alocacao)
    metricas = {
        "total_alunos": len(alunos),
        "total_alocados": total_alocados,
        "total_turmas": len(turmas),
        "amplitude_por_turno": melhor_amplitude,
        "desvio_genero_modelo": float(pulp.value(
            objetivo_equilibrio_genero(desvios)
        ) or 0),
    }

    return {
        "status": "Optimal",
        "alocacao": alocacao,
        "resumo": resumo,
        "metricas": metricas,
    }
