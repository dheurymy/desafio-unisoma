import pulp


def criar_variaveis_alocacao(alunos, turmas):
    x = {}
    for aluno in alunos:
        for turma in turmas:
            if aluno["turno"] == turma["turno"]:
                chave = (aluno["id"], turma["turma"])
                nome_turma = "".join(
                    c if c.isalnum() else "_" for c in turma["turma"]
                )
                x[chave] = pulp.LpVariable(
                    f"x_{aluno['id']}_{nome_turma}",
                    cat=pulp.LpBinary,
                )
    return x


def adicionar_alocacao_unica(modelo, alunos, turmas, x):
    turmas_por_turno = {
        turno: [t for t in turmas if t["turno"] == turno]
        for turno in ("Manhã", "Tarde")
    }

    for aluno in alunos:
        candidatas = turmas_por_turno[aluno["turno"]]
        modelo += (
            pulp.lpSum(x[(aluno["id"], t["turma"])] for t in candidatas) == 1,
            f"alocacao_unica_{aluno['id']}",
        )


def adicionar_capacidade(modelo, alunos, turmas, x):
    """A quantidade alocada em cada turma não pode superar suas vagas."""
    alunos_por_turno = {
        turno: [a for a in alunos if a["turno"] == turno]
        for turno in ("Manhã", "Tarde")
    }

    for indice, turma in enumerate(turmas):
        grupo = alunos_por_turno[turma["turno"]]
        quantidade = pulp.lpSum(
            x[(a["id"], turma["turma"])] for a in grupo
        )
        modelo += (
            quantidade <= turma["vagas"],
            f"capacidade_{indice}",
        )


def criar_limites_de_quantidade(modelo, alunos, turmas, x):
    menores = {}
    maiores = {}
    quantidades = {}

    for turno in ("Manhã", "Tarde"):
        grupo_alunos = [a for a in alunos if a["turno"] == turno]
        grupo_turmas = [t for t in turmas if t["turno"] == turno]

        if not grupo_alunos or not grupo_turmas:
            continue

        menores[turno] = pulp.LpVariable(
            f"menor_{'manha' if turno == 'Manhã' else 'tarde'}",
            lowBound=0,
            cat=pulp.LpInteger,
        )
        maiores[turno] = pulp.LpVariable(
            f"maior_{'manha' if turno == 'Manhã' else 'tarde'}",
            lowBound=0,
            cat=pulp.LpInteger,
        )

        for indice, turma in enumerate(grupo_turmas):
            quantidade = pulp.lpSum(
                x[(a["id"], turma["turma"])] for a in grupo_alunos
            )
            quantidades[(turno, turma["turma"])] = quantidade

            modelo += (
                quantidade >= menores[turno],
                f"limite_inferior_{turno}_{indice}",
            )
            modelo += (
                quantidade <= maiores[turno],
                f"limite_superior_{turno}_{indice}",
            )

    return menores, maiores, quantidades


def preservar_equilibrio_de_quantidade(
    modelo, menores, maiores, melhor_amplitude
):
    for turno, amplitude in melhor_amplitude.items():
        modelo += (
            maiores[turno] - menores[turno] <= amplitude,
            f"preservar_amplitude_{turno}",
        )
