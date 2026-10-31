
"""Restrições matemáticas do modelo de ensalamento."""

# Importa a biblioteca PuLP.
# Ela permite criar variáveis matemáticas, restrições e problemas de otimização.
import pulp


# 1. CRIAÇÃO DAS VARIÁVEIS DE ALOCAÇÃO

# Define uma função que cria as variáveis responsáveis por representar
# a alocação dos alunos nas turmas.
def criar_variaveis_alocacao(alunos, turmas):

    """
    Cria variáveis binárias x[(id_aluno, nome_turma)].

    Cada variável representa uma possível alocação:
        1 = aluno alocado na turma.
        0 = aluno não alocado na turma.

    Só cria variáveis para combinações de mesmo turno.
    """

    # Cria um dicionário vazio que armazenará todas as variáveis de decisão.
    # As chaves serão combinações de ID do aluno e nome da turma.
    x = {}

    # Percorre todos os alunos recebidos.
    for aluno in alunos:

        # Para cada aluno, percorre todas as turmas disponíveis.
        for turma in turmas:

            # Verifica se o turno de disponibilidade do aluno
            # é igual ao turno de funcionamento da turma.
            # Isso impede que um aluno da manhã seja alocado à tarde, por exemplo.
            if aluno["turno"] == turma["turno"]:

                # Cria uma chave que identifica exclusivamente
                # a combinação entre o aluno e a turma.
                # Exemplo: (1, "MANHÃ - A").
                chave = (aluno["id"], turma["turma"])

                # Prepara o nome da turma para ser utilizado
                # na identificação da variável matemática.
                # O método join() une todos os caracteres em uma única string.
                nome_turma = "".join(

                    # Percorre cada caractere do nome da turma.
                    # Se for letra ou número, mantém o caractere.
                    # Caso contrário, substitui por "_" para evitar
                    # caracteres especiais no nome da variável.
                    c if c.isalnum() else "_" for c in turma["turma"]
                )

                # Cria a variável matemática e armazena no dicionário x.
                x[chave] = pulp.LpVariable(

                    # Define o nome da variável.
                    # Exemplo: x_1_MANHÃ___A.
                    # O ID do aluno e o nome da turma ajudam a identificar
                    # qual combinação aquela variável representa.
                    f"x_{aluno['id']}_{nome_turma}",

                    # Define o tipo da variável como binária.
                    # Isso significa que ela só pode assumir os valores 0 ou 1.
                    cat=pulp.LpBinary,
                )

    # Retorna o dicionário com todas as variáveis de alocação criadas.
    return x


# 2. RESTRIÇÃO DE ALOCAÇÃO ÚNICA

# Define uma função que adiciona ao modelo a restrição
# responsável por garantir que cada aluno esteja em exatamente uma turma.
def adicionar_alocacao_unica(modelo, alunos, turmas, x):

    # Documentação da função:
    # Cada aluno deve ser alocado em exatamente uma turma do seu turno.

    # Cria um dicionário que separa as turmas por turno.
    # A chave será o nome do turno e o valor será a lista de turmas daquele turno.
    turmas_por_turno = {

        # Para cada turno válido, cria uma lista contendo
        # somente as turmas que pertencem a ele.
        turno: [t for t in turmas if t["turno"] == turno]

        # Percorre os dois turnos utilizados pelo modelo.
        for turno in ("Manhã", "Tarde")
    }

    # Percorre todos os alunos para adicionar uma restrição individual para cada um.
    for aluno in alunos:

        # Recupera somente as turmas compatíveis com o turno do aluno.
        # Um aluno da manhã só poderá ser alocado nas turmas da manhã.
        candidatas = turmas_por_turno[aluno["turno"]]

        # Adiciona uma restrição matemática ao modelo.
        modelo += (

            # Soma as variáveis de alocação do aluno em todas as turmas candidatas.
            # Como cada variável pode valer 0 ou 1, a soma precisa ser exatamente 1.
            #
            # Exemplo:
            # x[(1, "MANHÃ - A")] +
            # x[(1, "MANHÃ - B")] +
            # x[(1, "MANHÃ - C")] = 1
            #
            # Isso garante que o aluno seja alocado em uma única turma.
            pulp.lpSum(
                x[(aluno["id"], t["turma"])] for t in candidatas
            ) == 1,

            # Define um nome exclusivo para identificar essa restrição.
            # O ID do aluno é utilizado para diferenciar cada restrição.
            f"alocacao_unica_{aluno['id']}",
        )


# 3. RESTRIÇÃO DE CAPACIDADE DAS TURMAS

# Define uma função responsável por impedir que as turmas
# recebam uma quantidade de alunos superior ao número de vagas.
def adicionar_capacidade(modelo, alunos, turmas, x):

    # Documentação da função:
    # A quantidade alocada em cada turma não pode superar suas vagas.

    # Cria um dicionário que separa os alunos por turno.
    alunos_por_turno = {

        # Para cada turno, seleciona somente os alunos
        # que possuem disponibilidade correspondente.
        turno: [a for a in alunos if a["turno"] == turno]

        # Percorre os turnos da manhã e da tarde.
        for turno in ("Manhã", "Tarde")
    }

    # Percorre todas as turmas.
    # enumerate() fornece dois valores:
    # indice = posição da turma na lista.
    # turma = dicionário com os dados da turma.
    for indice, turma in enumerate(turmas):

        # Recupera somente os alunos que podem estudar no turno da turma atual.
        grupo = alunos_por_turno[turma["turno"]]

        # Calcula matematicamente quantos alunos serão alocados naquela turma.
        quantidade = pulp.lpSum(

            # Soma as variáveis binárias de todos os alunos compatíveis
            # com a turma atual.
            x[(a["id"], turma["turma"])] for a in grupo
        )

        # Adiciona a restrição de capacidade ao modelo.
        modelo += (

            # Determina que a quantidade de alunos alocados
            # deve ser menor ou igual ao número de vagas disponíveis.
            #
            # Exemplo:
            # Se a turma possui 30 vagas:
            # quantidade <= 30
            quantidade <= turma["vagas"],

            # Cria um nome exclusivo para identificar a restrição.
            # O índice diferencia as restrições de capacidade das turmas.
            f"capacidade_{indice}",
        )


# 4. CRIAÇÃO DOS LIMITES DE QUANTIDADE DE ALUNOS

# Define uma função que cria as variáveis utilizadas para controlar
# o menor e o maior número de alunos em cada turno.
def criar_limites_de_quantidade(modelo, alunos, turmas, x):

    """
    Cria L_turno e U_turno e força:

        L_turno <= quantidade de cada turma <= U_turno

    Minimizar U-L equivale a minimizar a amplitude
    de tamanhos das turmas.
    """

    # Cria um dicionário para armazenar a variável que representa
    # a menor quantidade de alunos encontrada em cada turno.
    menores = {}

    # Cria um dicionário para armazenar a variável que representa
    # a maior quantidade de alunos encontrada em cada turno.
    maiores = {}

    # Cria um dicionário para armazenar a expressão matemática
    # que representa a quantidade de alunos em cada turma.
    quantidades = {}

    # Percorre os turnos da manhã e da tarde.
    for turno in ("Manhã", "Tarde"):

        # Seleciona todos os alunos que pertencem ao turno atual.
        grupo_alunos = [a for a in alunos if a["turno"] == turno]

        # Seleciona todas as turmas que pertencem ao turno atual.
        grupo_turmas = [t for t in turmas if t["turno"] == turno]

        # Verifica se existem alunos e turmas para o turno atual.
        # Se algum dos grupos estiver vazio, não há necessidade
        # de criar variáveis de equilíbrio para esse turno.
        if not grupo_alunos or not grupo_turmas:

            # Interrompe apenas a iteração atual e passa para o próximo turno.
            continue

        # Cria uma variável matemática que representa
        # a menor quantidade de alunos entre as turmas do turno.
        menores[turno] = pulp.LpVariable(

            # Define o nome da variável de acordo com o turno.
            # Para manhã, será "menor_manha".
            # Para tarde, será "menor_tarde".
            f"menor_{'manha' if turno == 'Manhã' else 'tarde'}",

            # Define que a variável não pode assumir valores negativos.
            # Uma turma não pode possuir uma quantidade negativa de alunos.
            lowBound=0,

            # Define a variável como inteira.
            # A quantidade de alunos deve ser um número inteiro.
            cat=pulp.LpInteger,
        )

        # Cria uma variável matemática que representa
        # a maior quantidade de alunos entre as turmas do turno.
        maiores[turno] = pulp.LpVariable(

            # Define o nome da variável conforme o turno.
            f"maior_{'manha' if turno == 'Manhã' else 'tarde'}",

            # Impede que a variável assuma valores negativos.
            lowBound=0,

            # Define que a variável deve assumir somente valores inteiros.
            cat=pulp.LpInteger,
        )

        # Percorre todas as turmas do turno atual.
        # enumerate() também fornece o índice de cada turma.
        for indice, turma in enumerate(grupo_turmas):

            # Calcula a quantidade de alunos que serão alocados
            # especificamente na turma atual.
            quantidade = pulp.lpSum(

                # Soma as variáveis de alocação dos alunos
                # que pertencem ao turno atual.
                x[(a["id"], turma["turma"])] for a in grupo_alunos
            )

            # Armazena a expressão matemática no dicionário quantidades.
            # A chave é formada pelo turno e pelo nome da turma.
            # Exemplo: ("Manhã", "MANHÃ - A").
            quantidades[(turno, turma["turma"])] = quantidade

            # Adiciona a primeira restrição de equilíbrio.
            modelo += (

                # Determina que a quantidade de alunos da turma
                # deve ser maior ou igual ao menor limite do turno.
                #
                # Exemplo:
                # quantidade >= menor_manha
                quantidade >= menores[turno],

                # Define um nome exclusivo para essa restrição.
                f"limite_inferior_{turno}_{indice}",
            )

            # Adiciona a segunda restrição de equilíbrio.
            modelo += (

                # Determina que a quantidade de alunos da turma
                # deve ser menor ou igual ao maior limite do turno.
                #
                # Exemplo:
                # quantidade <= maior_manha
                quantidade <= maiores[turno],

                # Define um nome exclusivo para essa restrição.
                f"limite_superior_{turno}_{indice}",
            )

    # Retorna os três dicionários para que outras funções possam utilizá-los.
    # menores: menor limite de alunos por turno.
    # maiores: maior limite de alunos por turno.
    # quantidades: expressão de quantidade de alunos por turma.
    return menores, maiores, quantidades


# 5. PRESERVAÇÃO DO EQUILÍBRIO DE QUANTIDADE

# Define uma função que será utilizada na segunda etapa da otimização.
# Sua finalidade é impedir que o equilíbrio de quantidade
# encontrado na primeira etapa seja prejudicado.
def preservar_equilibrio_de_quantidade(
    modelo, menores, maiores, melhor_amplitude
):

    # Documentação:
    # Na segunda etapa, impede piorar a amplitude ótima de cada turno.

    # Percorre o dicionário que contém a melhor amplitude encontrada
    # para cada turno na primeira etapa da otimização.
    # turno representa o nome do turno.
    # amplitude representa a diferença ótima entre maior e menor quantidade.
    for turno, amplitude in melhor_amplitude.items():

        # Adiciona uma nova restrição ao modelo.
        modelo += (

            # Determina que a diferença entre o maior e o menor limite
            # não pode ultrapassar a amplitude encontrada anteriormente.
            #
            # Exemplo:
            # Se a melhor amplitude encontrada foi 2:
            # maior_manha - menor_manha <= 2
            #
            # Isso preserva o equilíbrio de quantidade durante
            # a otimização do equilíbrio de gênero.
            maiores[turno] - menores[turno] <= amplitude,

            # Define um nome exclusivo para a restrição de preservação.
            f"preservar_amplitude_{turno}",
        )
