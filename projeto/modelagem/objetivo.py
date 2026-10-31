import pulp


def objetivo_equilibrio_quantidade(menores, maiores):
    return pulp.lpSum(
        maiores[turno] - menores[turno]
        for turno in menores
    )


def criar_desvios_de_genero(modelo, alunos, turmas, x):
    desvios = []
    for turno in ("Manhã", "Tarde"):
        grupo_alunos = [a for a in alunos if a["turno"] == turno]
        grupo_turmas = [t for t in turmas if t["turno"] == turno]

        if not grupo_alunos:
            continue

        total_alunos = len(grupo_alunos)
        total_masculino = sum(
            1 for a in grupo_alunos if a["sexo"] == "M"
        )

        for indice, turma in enumerate(grupo_turmas):
            quantidade = pulp.lpSum(
                x[(a["id"], turma["turma"])] for a in grupo_alunos
            )
            masculino = pulp.lpSum(
                x[(a["id"], turma["turma"])]
                for a in grupo_alunos
                if a["sexo"] == "M"
            )

            expressao = (
                total_alunos * masculino
                - total_masculino * quantidade
            )

            desvio = pulp.LpVariable(
                f"desvio_genero_{'manha' if turno == 'Manhã' else 'tarde'}_{indice}",
                lowBound=0,
            )

            modelo += desvio >= expressao
            modelo += desvio >= -expressao
            desvios.append(desvio)

    return desvios


def objetivo_equilibrio_genero(desvios):
    return pulp.lpSum(desvios)
