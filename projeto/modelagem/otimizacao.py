
"""Orquestração do modelo MILP de ensalamento."""

# Importa defaultdict, uma estrutura de dicionário que cria automaticamente
# uma lista vazia quando uma chave ainda não existe.
from collections import defaultdict

# Importa a biblioteca PuLP, utilizada para criar e resolver
# problemas de programação linear e programação linear inteira.
import pulp

# Importa as funções responsáveis pelas restrições matemáticas do modelo.
from .restricoes import (
    criar_variaveis_alocacao,       # Cria as variáveis que representam a alocação dos alunos nas turmas.
    adicionar_alocacao_unica,       # Garante que cada aluno seja alocado em exatamente uma turma.
    adicionar_capacidade,           # Impede que uma turma receba mais alunos do que suas vagas.
    criar_limites_de_quantidade,    # Cria variáveis que representam os limites de alunos por turno.
    preservar_equilibrio_de_quantidade,  # Mantém o melhor equilíbrio de quantidade encontrado na primeira etapa.
)

# Importa as funções responsáveis pela otimização do equilíbrio de gênero.
from .objetivo import (
    objetivo_equilibrio_quantidade, # Cria a função objetivo para equilibrar a quantidade de alunos.
    criar_desvios_de_genero,        # Cria variáveis que representam os desvios de proporção de gênero.
    objetivo_equilibrio_genero,     # Cria a função objetivo para minimizar os desvios de gênero.
)


# Define os únicos turnos permitidos para os alunos e para as turmas.
TURNOS_VALIDOS = {"Manhã", "Tarde"}

# Define os valores permitidos para representar o sexo dos alunos.
SEXOS_VALIDOS = {"M", "F"}


# Função privada responsável por validar os dados recebidos pelo modelo.
# O "_" no início do nome indica que ela é uma função de uso interno do módulo.
def _validar_entrada(alunos, turmas):

    # Verifica se os parâmetros recebidos são listas.
    # Se algum deles não for uma lista, interrompe a execução com TypeError.
    if not isinstance(alunos, list) or not isinstance(turmas, list):
        raise TypeError("alunos e turmas devem ser listas de dicionários.")

    # Verifica se a lista de alunos está vazia.
    # Não é possível realizar o ensalamento sem alunos.
    if not alunos:
        raise ValueError("A lista de alunos está vazia.")

    # Verifica se a lista de turmas está vazia.
    # Não é possível distribuir alunos sem turmas disponíveis.
    if not turmas:
        raise ValueError("A lista de turmas está vazia.")

    # Percorre a lista de alunos e extrai o valor do campo "id" de cada aluno.
    # O método get() retorna None caso o campo não exista.
    ids = [a.get("id") for a in alunos]

    # Verifica se algum aluno está sem identificação.
    # O ID é necessário para identificar cada aluno individualmente no modelo.
    if any(i is None for i in ids):
        raise ValueError("Todo aluno precisa ter um campo 'id'.")

    # Compara a quantidade de IDs com a quantidade de IDs únicos.
    # Se os valores forem diferentes, significa que existem IDs duplicados.
    if len(ids) != len(set(ids)):
        raise ValueError("Os IDs dos alunos devem ser únicos.")

    # Percorre a lista de turmas e extrai o nome de cada uma.
    nomes_turmas = [t.get("turma") for t in turmas]

    # Verifica se alguma turma está sem nome ou possui um nome vazio.
    if any(not nome for nome in nomes_turmas):
        raise ValueError("Toda turma precisa ter um nome.")

    # Verifica se existem nomes de turmas repetidos.
    # Cada turma precisa possuir uma identificação única.
    if len(nomes_turmas) != len(set(nomes_turmas)):
        raise ValueError("Os nomes das turmas devem ser únicos.")

    # Inicia a validação individual de cada aluno.
    for aluno in alunos:

        # Define os campos obrigatórios que cada aluno precisa possuir.
        campos = ("nome", "sexo", "turno")

        # Cria uma lista contendo os campos que estão faltando no cadastro.
        # A expressão c not in aluno verifica se a chave existe no dicionário.
        faltantes = [c for c in campos if c not in aluno]

        # Se existir algum campo obrigatório faltando, interrompe a execução.
        if faltantes:

            # Apresenta o ID do aluno e os campos que precisam ser preenchidos.
            raise ValueError(
                f"Aluno ID {aluno['id']} sem campos: {', '.join(faltantes)}."
            )

        # Verifica se o sexo informado pertence aos valores permitidos.
        # Somente M ou F são aceitos nesta versão do modelo.
        if aluno["sexo"] not in SEXOS_VALIDOS:

            # Informa qual aluno possui um valor de sexo inválido.
            raise ValueError(
                f"Sexo inválido para o aluno ID {aluno['id']}: "
                f"{aluno['sexo']!r}. Use M ou F."
            )

        # Verifica se a disponibilidade do aluno corresponde a um turno válido.
        if aluno["turno"] not in TURNOS_VALIDOS:

            # Informa qual aluno possui um turno inválido.
            raise ValueError(
                f"Turno inválido para o aluno ID {aluno['id']}: "
                f"{aluno['turno']!r}. Use Manhã ou Tarde."
            )

    # Inicia a validação individual de cada turma.
    for turma in turmas:

        # Verifica se a turma possui o campo "turno" e se ele é válido.
        # O uso de or garante que as duas condições sejam verificadas.
        if "turno" not in turma or turma["turno"] not in TURNOS_VALIDOS:

            # Informa qual turma possui um turno inválido.
            raise ValueError(
                f"Turno inválido na turma {turma.get('turma')!r}."
            )

        # Obtém a quantidade de vagas disponíveis na turma.
        vagas = turma.get("vagas")

        # Valida a quantidade de vagas.
        # O primeiro teste impede que valores booleanos sejam aceitos,
        # pois em Python bool é uma subclasse de int.
        # O segundo exige que o valor seja um número inteiro.
        # O terceiro impede que a turma tenha zero ou menos vagas.
        if isinstance(vagas, bool) or not isinstance(vagas, int) or vagas <= 0:

            # Interrompe a execução caso a capacidade da turma seja inválida.
            raise ValueError(
                f"As vagas da turma {turma['turma']!r} "
                "devem ser um inteiro positivo."
            )

    # Percorre os turnos permitidos para verificar se existe capacidade suficiente.
    for turno in TURNOS_VALIDOS:

        # Conta quantos alunos possuem disponibilidade para o turno atual.
        # A comparação retorna True ou False para cada aluno.
        # Em Python, True é contabilizado como 1 e False como 0.
        qtd_alunos = sum(a["turno"] == turno for a in alunos)

        # Soma a capacidade de todas as turmas pertencentes ao turno atual.
        capacidade = sum(
            t["vagas"] for t in turmas if t["turno"] == turno
        )

        # Verifica se a quantidade de alunos ultrapassa a capacidade total.
        if qtd_alunos > capacidade:

            # Impede que o modelo seja executado quando não existem vagas suficientes.
            raise ValueError(
                f"Capacidade insuficiente no turno {turno}: "
                f"{qtd_alunos} alunos para {capacidade} vagas."
            )

        # Verifica se existem alunos para o turno, mas nenhuma turma disponível.
        # Essa condição também funciona como uma verificação adicional de segurança.
        if qtd_alunos > 0 and capacidade == 0:
            raise ValueError(f"Não existem turmas para o turno {turno}.")


# Função responsável por executar o solver e verificar o resultado da otimização.
def _resolver(modelo, solver, etapa):

    # Executa o solver sobre o modelo matemático recebido.
    # O solver procura uma solução que satisfaça as restrições e a função objetivo.
    # O resultado retornado é um código numérico que representa o status da solução.
    status_codigo = modelo.solve(solver)

    # Converte o código numérico em uma descrição textual.
    # Exemplos: Optimal, Infeasible, Unbounded e Not Solved.
    status = pulp.LpStatus[status_codigo]

    # Verifica se o solver encontrou uma solução ótima.
    if status != "Optimal":

        # Se não encontrou uma solução ótima, interrompe a execução.
        # A mensagem informa em qual etapa ocorreu o problema.
        raise RuntimeError(
            f"A etapa '{etapa}' não encontrou solução ótima. "
            f"Status retornado pelo solver: {status}."
        )


# Função principal que executa todo o processo de otimização do ensalamento.
# Recebe a lista de alunos, a lista de turmas e configurações opcionais do solver.
def otimizar_ensalamento(alunos, turmas, msg_solver=False, time_limit=None):

    """
    Executa a otimização lexicográfica em duas etapas.

    Entrada:
        alunos = [
            {"id": 1, "nome": "João", "sexo": "M", "turno": "Manhã"}
        ]

        turmas = [
            {"turma": "MANHÃ - A", "turno": "Manhã", "vagas": 30}
        ]

    Retorno:
        {
            "status": "Optimal",
            "alocacao": [...],
            "resumo": [...],
            "metricas": {...}
        }
    """

    # Primeiramente, valida todos os dados recebidos.
    # Se existir algum problema nos cadastros, o processo é interrompido.
    _validar_entrada(alunos, turmas)

    # Cria o problema de otimização utilizando a biblioteca PuLP.
    # "Ensalamento_ONG" é o nome do problema.
    # LpMinimize informa que o objetivo será minimizar uma função matemática.
    modelo = pulp.LpProblem("Ensalamento_ONG", pulp.LpMinimize)

    # Cria as variáveis de decisão do modelo.
    # Essas variáveis representam se determinado aluno será colocado em determinada turma.
    # Normalmente são variáveis binárias: 1 para alocado e 0 para não alocado.
    x = criar_variaveis_alocacao(alunos, turmas)

    # Adiciona ao modelo a restrição que garante que cada aluno seja alocado uma única vez.
    adicionar_alocacao_unica(modelo, alunos, turmas, x)

    # Adiciona ao modelo a restrição que impede que uma turma ultrapasse sua capacidade.
    adicionar_capacidade(modelo, alunos, turmas, x)

    # Cria as variáveis e os limites utilizados para equilibrar a quantidade de alunos.
    # menores: representa o limite inferior de alunos por turma dentro de cada turno.
    # maiores: representa o limite superior de alunos por turma dentro de cada turno.
    # quantidades: representa as quantidades de alunos associadas às turmas.
    menores, maiores, quantidades = criar_limites_de_quantidade(
        modelo, alunos, turmas, x
    )

    # Cria um dicionário com as configurações que serão enviadas ao solver.
    # msg controla a exibição das mensagens de execução do CBC no terminal.
    # False significa que as mensagens do solver ficarão ocultas.
    solver_kwargs = {"msg": msg_solver}

    # Verifica se foi informado um limite de tempo para a otimização.
    if time_limit is not None:

        # Adiciona o limite de tempo às configurações do solver.
        # O valor é informado em segundos.
        solver_kwargs["timeLimit"] = time_limit

    # Cria o solver CBC, utilizado pelo PuLP para resolver o problema matemático.
    # O operador ** desempacota o dicionário, enviando suas chaves como argumentos.
    solver = pulp.PULP_CBC_CMD(**solver_kwargs)

    # ETAPA 1: OTIMIZAÇÃO DO EQUILÍBRIO DE QUANTIDADE

    # Define a primeira função objetivo do problema.
    # O objetivo é minimizar a diferença entre a turma mais cheia
    # e a turma menos cheia de cada turno.
    modelo.setObjective(
        objetivo_equilibrio_quantidade(menores, maiores)
    )

    # Executa a primeira etapa da otimização.
    # O solver procura a melhor distribuição possível em relação à quantidade de alunos.
    _resolver(modelo, solver, "equilíbrio de quantidade")

    # Cria um dicionário para armazenar a melhor amplitude encontrada em cada turno.
    melhor_amplitude = {}

    # Percorre os turnos representados pelas variáveis menores.
    for turno in menores:

        # Obtém a diferença entre a quantidade máxima e mínima de alunos do turno.
        # pulp.value() extrai o valor numérico encontrado pelo solver.
        valor = pulp.value(maiores[turno] - menores[turno])

        # Arredonda o resultado e converte para inteiro.
        # Isso é feito porque a quantidade de alunos deve ser um número inteiro.
        # O resultado é armazenado para ser preservado na segunda etapa.
        melhor_amplitude[turno] = int(round(valor))

    # ETAPA 2: OTIMIZAÇÃO DO EQUILÍBRIO DE GÊNERO

    # Adiciona restrições para preservar o melhor equilíbrio de quantidade
    # encontrado na primeira etapa.
    # Isso impede que a segunda etapa prejudique o resultado anterior.
    preservar_equilibrio_de_quantidade(
        modelo, menores, maiores, melhor_amplitude
    )

    # Cria as variáveis matemáticas que representam os desvios
    # entre as proporções de alunos masculinos e femininos nas turmas.
    desvios = criar_desvios_de_genero(modelo, alunos, turmas, x)

    # Define a segunda função objetivo.
    # Agora o modelo procura minimizar os desvios de proporção de gênero.
    modelo.setObjective(objetivo_equilibrio_genero(desvios))

    # Executa a segunda etapa da otimização.
    # A solução precisa respeitar as restrições originais e o equilíbrio
    # de quantidade preservado na etapa anterior.
    _resolver(modelo, solver, "equilíbrio de gênero")

    # EXTRAÇÃO DOS RESULTADOS DA OTIMIZAÇÃO

    # Cria uma lista vazia para armazenar a alocação final de cada aluno.
    alocacao = []

    # Cria um dicionário em que cada turma terá uma lista de alunos.
    # defaultdict(list) cria automaticamente uma lista quando uma turma é adicionada.
    por_turma = defaultdict(list)

    # Percorre todos os alunos para descobrir em qual turma cada um foi alocado.
    for aluno in alunos:

        # Inicializa a variável que armazenará a turma escolhida.
        # None significa que nenhuma turma foi encontrada até o momento.
        turma_escolhida = None

        # Percorre todas as turmas disponíveis para verificar a alocação do aluno.
        for turma in turmas:

            # Cria uma chave que identifica a combinação entre aluno e turma.
            # Essa chave é utilizada para acessar a variável de decisão correspondente.
            chave = (aluno["id"], turma["turma"])

            # Verifica se a combinação existe no conjunto de variáveis do modelo.
            # Também verifica se o valor encontrado pelo solver é maior que 0.5.
            # Como a variável é binária, isso significa que o aluno foi alocado naquela turma.
            if chave in x and pulp.value(x[chave]) > 0.5:

                # Armazena a turma em que o aluno foi encontrado.
                turma_escolhida = turma

                # Interrompe a procura porque o aluno já possui uma turma identificada.
                break

        # Verifica se o aluno foi encontrado em alguma turma.
        if turma_escolhida is None:

            # Caso não exista alocação, interrompe a execução e informa o ID do aluno.
            raise RuntimeError(
                f"O aluno ID {aluno['id']} não foi encontrado na solução."
            )

        # Cria um dicionário contendo os dados do aluno e sua turma de destino.
        registro = {
            "id": aluno["id"],                       # Armazena o identificador do aluno.
            "Nome do aluno": aluno["nome"],          # Armazena o nome do aluno.
            "Sexo": aluno["sexo"],                   # Armazena o sexo informado no cadastro.
            "Disponibilidade": aluno["turno"],       # Armazena o turno disponível do aluno.
            "Turma": turma_escolhida["turma"],       # Armazena o nome da turma selecionada.
        }

        # Adiciona o registro do aluno à lista de alocações finais.
        alocacao.append(registro)

        # Adiciona o aluno à lista correspondente à turma em que foi alocado.
        por_turma[turma_escolhida["turma"]].append(aluno)

    # GERAÇÃO DO RESUMO DAS TURMAS

    # Cria uma lista vazia para armazenar as estatísticas de cada turma.
    resumo = []

    # Percorre todas as turmas para calcular suas informações finais.
    for turma in turmas:

        # Recupera a lista de alunos que foram alocados na turma atual.
        # Se não houver alunos, o defaultdict retorna uma lista vazia.
        grupo = por_turma[turma["turma"]]

        # Conta quantos alunos do grupo possuem sexo masculino.
        masculino = sum(a["sexo"] == "M" for a in grupo)

        # Conta quantos alunos do grupo possuem sexo feminino.
        feminino = sum(a["sexo"] == "F" for a in grupo)

        # Calcula a quantidade total de alunos da turma.
        total = len(grupo)

        # Adiciona um dicionário com as informações e estatísticas da turma.
        resumo.append({

            # Nome da turma.
            "Turma": turma["turma"],

            # Turno em que a turma funciona.
            "Turno": turma["turno"],

            # Capacidade máxima de alunos da turma.
            "Vagas": turma["vagas"],

            # Quantidade de alunos efetivamente alocados.
            "Alunos": total,

            # Calcula quantas vagas ainda estão disponíveis.
            "Vagas restantes": turma["vagas"] - total,

            # Quantidade de alunos do sexo masculino.
            "Masculino": masculino,

            # Quantidade de alunos do sexo feminino.
            "Feminino": feminino,

            # Calcula a diferença absoluta entre a quantidade de homens e mulheres.
            # abs() garante que o resultado seja sempre positivo ou zero.
            "Diferença M-F": abs(masculino - feminino),

            # Calcula o percentual de alunos masculinos na turma.
            # Se a turma estiver vazia, retorna 0.0 para evitar divisão por zero.
            # round(..., 2) limita o resultado a duas casas decimais.
            "Percentual masculino": (
                round(100 * masculino / total, 2) if total else 0.0
            ),

            # Calcula o percentual de alunos femininos na turma.
            # Também evita divisão por zero quando não existem alunos na turma.
            "Percentual feminino": (
                round(100 * feminino / total, 2) if total else 0.0
            ),
        })

    # GERAÇÃO DAS MÉTRICAS GERAIS DO MODELO

    # Calcula a quantidade total de alunos presentes na lista de alocações.
    total_alocados = len(alocacao)

    # Cria um dicionário com os indicadores gerais da execução.
    metricas = {

        # Quantidade total de alunos recebidos como entrada.
        "total_alunos": len(alunos),

        # Quantidade de alunos que foram efetivamente alocados.
        "total_alocados": total_alocados,

        # Quantidade total de turmas disponíveis.
        "total_turmas": len(turmas),

        # Armazena a melhor diferença entre as quantidades de alunos
        # encontrada em cada turno na primeira etapa da otimização.
        "amplitude_por_turno": melhor_amplitude,

        # Recupera o valor numérico da função objetivo de equilíbrio de gênero.
        # float() converte o resultado para número decimal.
        # O operador or 0 garante que seja retornado zero caso o valor seja None
        # ou outro valor considerado falso.
        "desvio_genero_modelo": float(pulp.value(
            objetivo_equilibrio_genero(desvios)
        ) or 0),
    }

    # Retorna um dicionário contendo todos os resultados da otimização.
    return {

        # Informa que o solver encontrou uma solução ótima nas duas etapas.
        "status": "Optimal",

        # Retorna a relação de alunos e suas respectivas turmas.
        "alocacao": alocacao,

        # Retorna as estatísticas individuais de cada turma.
        "resumo": resumo,

        # Retorna as métricas gerais do modelo matemático.
        "metricas": metricas,
    }
