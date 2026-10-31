
"""Funções objetivo do modelo de ensalamento."""

# Importa a biblioteca PuLP, utilizada para criar e resolver
# problemas de otimização linear e programação linear inteira.
import pulp


def objetivo_equilibrio_quantidade(menores, maiores):
    """
    Minimiza a soma das amplitudes (maior turma - menor turma)
    de cada turno.

    O objetivo é deixar as turmas com quantidades de alunos
    o mais próximas possível dentro de cada turno.
    """

    # Calcula a diferença entre a maior e a menor turma de cada turno.
    # O pulp.lpSum soma todas essas diferenças.
    # Quanto menor o resultado, mais equilibrada será a quantidade
    # de alunos entre as turmas de cada turno.
    return pulp.lpSum(
        maiores[turno] - menores[turno]
        for turno in menores
    )


def criar_desvios_selecao_genero(modelo, alunos, turmas, x):
    """
    Mede o desvio entre a proporção original de meninos
    de cada turno e a proporção de meninos entre os alunos alocados.
    """

    desvios = []

    for turno in ("Manhã", "Tarde"):

        grupo_alunos = [
            a for a in alunos if a["turno"] == turno
        ]

        if not grupo_alunos:
            continue

        total_alunos = len(grupo_alunos)

        total_masculino = sum(
            1 for a in grupo_alunos if a["sexo"] == "M"
        )

        total_selecionado = pulp.lpSum(
            x[(a["id"], turma["turma"])]
            for a in grupo_alunos
            for turma in turmas
            if turma["turno"] == turno
            and (a["id"], turma["turma"]) in x
        )

        masculino_selecionado = pulp.lpSum(
            x[(a["id"], turma["turma"])]
            for a in grupo_alunos
            if a["sexo"] == "M"
            for turma in turmas
            if turma["turno"] == turno
            and (a["id"], turma["turma"]) in x
        )

        expressao = (
            total_alunos * masculino_selecionado
            - total_masculino * total_selecionado
        )

        nome_turno = "manha" if turno == "Manhã" else "tarde"

        desvio = pulp.LpVariable(
            f"desvio_selecao_genero_{nome_turno}",
            lowBound=0
        )

        modelo += desvio >= expressao
        modelo += desvio >= -expressao

        desvios.append(desvio)

    return desvios



def objetivo_equilibrio_selecao_genero(desvios):
    """
    Minimiza o desvio da proporção de gênero
    entre os alunos selecionados em cada turno.
    """

    return pulp.lpSum(desvios)


def criar_desvios_de_genero(modelo, alunos, turmas, x):
    """
    Mede o desvio da proporção de meninos em cada turma em relação
    à proporção geral de meninos do respectivo turno.

    Para cada turma j:
        desvio_j >= N * M_j - M * n_j
        desvio_j >= -(N * M_j - M * n_j)

    Como N e M são constantes, as expressões são lineares.
    """

    # Cria uma lista vazia para armazenar as variáveis
    # que representam os desvios de gênero de cada turma.
    desvios = []

    # Percorre os dois turnos existentes no modelo.
    for turno in ("Manhã", "Tarde"):

        # Seleciona somente os alunos que pertencem ao turno atual.
        grupo_alunos = [a for a in alunos if a["turno"] == turno]

        # Seleciona somente as turmas que pertencem ao turno atual.
        grupo_turmas = [t for t in turmas if t["turno"] == turno]

        # Verifica se existem alunos nesse turno.
        # Se não houver, pula para o próximo turno.
        if not grupo_alunos:
            continue

        # Calcula a quantidade total de alunos do turno atual.
        total_alunos = len(grupo_alunos)

        # Conta quantos alunos do turno são do sexo masculino.
        # A condição a["sexo"] == "M" identifica os meninos.
        total_masculino = sum(
            1 for a in grupo_alunos if a["sexo"] == "M"
        )

        # Percorre todas as turmas pertencentes ao turno atual.
        # O enumerate também fornece um índice para identificar cada turma.
        for indice, turma in enumerate(grupo_turmas):

            # Calcula a quantidade total de alunos atribuídos à turma.
            # A variável x indica se determinado aluno foi colocado
            # em determinada turma.
            # Se x[(a["id"], turma["turma"])] for 1, o aluno pertence
            # à turma; se for 0, não pertence.
            quantidade = pulp.lpSum(
                x[(a["id"], turma["turma"])]
                for a in grupo_alunos
                if (a["id"], turma["turma"]) in x
            )

            # Calcula quantos meninos foram atribuídos à turma atual.
            # Considera somente os alunos cujo sexo é masculino ("M").
            masculino = pulp.lpSum(
                x[(a["id"], turma["turma"])]
                for a in grupo_alunos
                if a["sexo"] == "M"
                and (a["id"], turma["turma"]) in x
            )

            # Calcula a diferença entre a proporção de meninos
            # da turma e a proporção geral de meninos do turno.
            #
            # total_alunos * masculino:
            # quantidade de alunos do turno multiplicada pela
            # quantidade de meninos na turma.
            #
            # total_masculino * quantidade:
            # quantidade total de meninos do turno multiplicada
            # pela quantidade de alunos na turma.
            #
            # A diferença igual a zero indica que a proporção
            # de meninos na turma é igual à proporção geral do turno.
            expressao = (
                total_alunos * masculino
                - total_masculino * quantidade
            )

            # Cria uma variável de decisão auxiliar que representa
            # o desvio de gênero da turma.
            #
            # O nome da variável muda conforme o turno e o índice
            # da turma, evitando nomes repetidos no modelo.
            #
            # lowBound=0 determina que o desvio não pode ser negativo.
            desvio = pulp.LpVariable(
                f"desvio_genero_{'manha' if turno == 'Manhã' else 'tarde'}_{indice}",
                lowBound=0,
            )

            # Primeira restrição:
            # Obriga o desvio a ser maior ou igual à expressão calculada.
            # Isso impede que o desvio fique abaixo da diferença positiva.
            modelo += desvio >= expressao

            # Segunda restrição:
            # Obriga o desvio a ser maior ou igual ao negativo da expressão.
            # Isso impede que o desvio fique abaixo do valor absoluto
            # da diferença quando a expressão for negativa.
            #
            # Juntas, as duas restrições garantem:
            # desvio >= |expressao|.
            modelo += desvio >= -expressao

            # Adiciona a variável de desvio à lista.
            # Assim, ela poderá ser utilizada posteriormente
            # na função objetivo de equilíbrio de gênero.
            desvios.append(desvio)

    # Retorna a lista com os desvios calculados para todas as turmas.
    return desvios


def objetivo_equilibrio_genero(desvios):
    """
    Minimiza a soma dos desvios proporcionais de gênero.

    O objetivo é aproximar a proporção de meninos em cada turma
    da proporção geral de meninos do respectivo turno.
    """

    # Soma todos os desvios de gênero utilizando pulp.lpSum.
    # Ao minimizar essa soma, o modelo procura distribuir
    # os meninos de maneira proporcional entre as turmas.
    return pulp.lpSum(desvios)
