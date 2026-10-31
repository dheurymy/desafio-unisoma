
"""Orquestração do modelo MILP de ensalamento."""

# Importa defaultdict, uma estrutura de dicionário que cria automaticamente
# uma lista vazia quando uma chave ainda não existe.
# Será utilizado para agrupar os alunos por turma.
from collections import defaultdict

# Importa a biblioteca PuLP, utilizada para criar e resolver
# problemas de programação linear inteira mista (MILP).
import pulp


# Importa do arquivo restricoes.py as funções responsáveis
# por criar as variáveis de decisão e adicionar as restrições.
from .restricoes import (
    # Cria as variáveis binárias que indicam se um aluno será alocado
    # em determinada turma.
    criar_variaveis_alocacao,

    # Garante que cada aluno seja alocado em no máximo uma turma.
    adicionar_alocacao_unica,

    # Impede que uma turma receba mais alunos do que suas vagas.
    adicionar_capacidade,

    # Cria variáveis auxiliares que representam a menor e a maior
    # quantidade de alunos entre as turmas de cada turno.
    criar_limites_de_quantidade,

    # Preserva a melhor diferença encontrada entre a maior e a menor
    # turma durante as etapas posteriores da otimização.
    preservar_equilibrio_de_quantidade,
)


# Importa do arquivo objetivo.py as funções que representam
# os objetivos matemáticos que o modelo deseja minimizar.
from .objetivo import (
    # Calcula a soma das diferenças entre a maior e a menor turma
    # de cada turno.
    objetivo_equilibrio_quantidade,

    # Cria variáveis que medem o desvio da proporção de gênero
    # entre os alunos originalmente cadastrados e os selecionados.
    criar_desvios_selecao_genero,

    # Monta a função objetivo que minimiza os desvios de gênero
    # dos alunos selecionados em cada turno.
    objetivo_equilibrio_selecao_genero,

    # Cria variáveis que medem o desvio da proporção de gênero
    # dentro de cada turma.
    criar_desvios_de_genero,

    # Monta a função objetivo que minimiza os desvios de gênero
    # entre as turmas e a proporção original do respectivo turno.
    objetivo_equilibrio_genero,
)


# Define os únicos turnos permitidos no modelo.
# O uso de conjunto (set) facilita a verificação de pertencimento.
TURNOS_VALIDOS = {"Manhã", "Tarde"}

# Define os únicos valores permitidos para representar o sexo dos alunos.
SEXOS_VALIDOS = {"M", "F"}


# Função privada responsável por validar os dados recebidos pelo modelo.
# O underline no início do nome indica que ela é uma função interna do módulo.
def _validar_entrada(alunos, turmas):

    # Verifica se alunos e turmas foram recebidos como listas.
    # Se algum dos parâmetros tiver outro tipo, interrompe a execução.
    if not isinstance(alunos, list) or not isinstance(turmas, list):
        raise TypeError("alunos e turmas devem ser listas de dicionários.")

    # Verifica se a lista de alunos está vazia.
    # O modelo não consegue realizar o ensalamento sem alunos.
    if not alunos:
        raise ValueError("A lista de alunos está vazia.")

    # Verifica se a lista de turmas está vazia.
    # O modelo precisa de turmas para realizar as alocações.
    if not turmas:
        raise ValueError("A lista de turmas está vazia.")

    # Percorre a lista de alunos e extrai o identificador de cada um.
    ids = [a.get("id") for a in alunos]

    # Verifica se algum aluno não possui identificador.
    # O ID é necessário para identificar as variáveis de alocação.
    if any(i is None for i in ids):
        raise ValueError("Todo aluno precisa ter um campo 'id'.")

    # Verifica se existem identificadores repetidos.
    # Cada aluno precisa ter um ID único.
    if len(ids) != len(set(ids)):
        raise ValueError("Os IDs dos alunos devem ser únicos.")

    # Extrai o nome de cada turma.
    nomes_turmas = [t.get("turma") for t in turmas]

    # Verifica se alguma turma está sem nome ou identificador.
    if any(not nome for nome in nomes_turmas):
        raise ValueError("Toda turma precisa ter um nome.")

    # Verifica se existem nomes de turmas repetidos.
    # O modelo utiliza o nome da turma para identificar as variáveis.
    if len(nomes_turmas) != len(set(nomes_turmas)):
        raise ValueError("Os nomes das turmas devem ser únicos.")

    # Inicia a validação individual de cada aluno.
    for aluno in alunos:

        # Define os campos obrigatórios que cada aluno precisa possuir.
        campos = ("nome", "sexo", "turno")

        # Cria uma lista contendo os campos que estão faltando.
        faltantes = [c for c in campos if c not in aluno]

        # Se houver algum campo obrigatório ausente, interrompe a execução.
        if faltantes:
            raise ValueError(
                f"Aluno ID {aluno['id']} sem campos: {', '.join(faltantes)}."
            )

        # Verifica se o sexo informado está entre os valores permitidos.
        if aluno["sexo"] not in SEXOS_VALIDOS:
            raise ValueError(
                f"Sexo inválido para o aluno ID {aluno['id']}: "
                f"{aluno['sexo']!r}. Use M ou F."
            )

        # Verifica se o turno informado está entre os turnos permitidos.
        if aluno["turno"] not in TURNOS_VALIDOS:
            raise ValueError(
                f"Turno inválido para o aluno ID {aluno['id']}: "
                f"{aluno['turno']!r}. Use Manhã ou Tarde."
            )

    # Inicia a validação individual de cada turma.
    for turma in turmas:

        # Verifica se a turma possui um turno válido.
        if "turno" not in turma or turma["turno"] not in TURNOS_VALIDOS:
            raise ValueError(
                f"Turno inválido na turma {turma.get('turma')!r}."
            )

        # Obtém a quantidade de vagas disponíveis na turma.
        vagas = turma.get("vagas")

        # Verifica se a quantidade de vagas é um número inteiro positivo.
        # Também impede que valores booleanos sejam aceitos como números,
        # pois em Python bool é uma subclasse de int.
        if (
            isinstance(vagas, bool)
            or not isinstance(vagas, int)
            or vagas <= 0
        ):
            raise ValueError(
                f"As vagas da turma {turma['turma']!r} "
                "devem ser um inteiro positivo."
            )

    # Verifica se existe capacidade disponível para cada turno.
    for turno in TURNOS_VALIDOS:

        # Conta quantos alunos pertencem ao turno atual.
        qtd_alunos = sum(a["turno"] == turno for a in alunos)

        # Soma as vagas de todas as turmas pertencentes ao turno atual.
        capacidade = sum(
            t["vagas"] for t in turmas if t["turno"] == turno
        )

        # Se existem alunos no turno, mas nenhuma vaga disponível,
        # interrompe a execução porque não existe turma para recebê-los.
        if qtd_alunos > 0 and capacidade == 0:
            raise ValueError(f"Não existem turmas para o turno {turno}.")


# Função responsável por executar o solver e verificar o resultado.
def _resolver(modelo, solver, etapa):

    # Executa o solver sobre o modelo matemático.
    # O solver procura uma solução que respeite as restrições
    # e minimize a função objetivo atualmente definida.
    status_codigo = modelo.solve(solver)

    # Converte o código numérico retornado pelo PuLP
    # em uma descrição textual, como Optimal, Infeasible ou Unbounded.
    status = pulp.LpStatus[status_codigo]

    # Verifica se o solver encontrou uma solução ótima.
    # Se não encontrou, interrompe a execução e informa em qual etapa ocorreu.
    if status != "Optimal":
        raise RuntimeError(
            f"A etapa '{etapa}' não encontrou solução ótima. "
            f"Status retornado pelo solver: {status}."
        )


# Função principal responsável por executar todo o processo de otimização.
# Recebe os alunos, as turmas e configurações opcionais do solver.
def otimizar_ensalamento(alunos, turmas, msg_solver=False, time_limit=None):

    """
    Executa a otimização lexicográfica do ensalamento.

    A otimização lexicográfica resolve os objetivos em uma ordem de prioridade.
    Cada etapa procura seu melhor resultado e o preserva nas etapas seguintes.

    Retorno:
        Dicionário contendo o status, as alocações, os alunos não alocados,
        o resumo das turmas e as métricas gerais do modelo.
    """

    # Antes de criar o modelo matemático, verifica se os dados recebidos
    # possuem os campos e valores necessários.
    _validar_entrada(alunos, turmas)

    # Cria o problema de otimização.
    # LpProblem representa o modelo matemático.
    # LpMinimize informa que as funções objetivo serão minimizadas.
    modelo = pulp.LpProblem("Ensalamento_ONG", pulp.LpMinimize)

    # Cria as variáveis de decisão do modelo.
    # Cada variável binária x indica se um aluno foi alocado em uma turma:
    # 1 = aluno alocado naquela turma.
    # 0 = aluno não alocado naquela turma.
    x = criar_variaveis_alocacao(alunos, turmas)

    # Adiciona ao modelo a restrição que impede que um aluno
    # seja alocado em mais de uma turma.
    adicionar_alocacao_unica(modelo, alunos, turmas, x)

    # Adiciona ao modelo as restrições de capacidade.
    # Cada turma só poderá receber alunos até atingir seu limite de vagas.
    adicionar_capacidade(modelo, alunos, turmas, x)

    # Cria as variáveis auxiliares utilizadas para equilibrar
    # a quantidade de alunos entre as turmas de cada turno.
    # menores representa a quantidade da menor turma.
    # maiores representa a quantidade da maior turma.
    # quantidades representa a quantidade de alunos em cada turma.
    menores, maiores, quantidades = criar_limites_de_quantidade(
        modelo, alunos, turmas, x
    )

    # Cria um dicionário com as configurações do solver.
    # msg controla se as mensagens internas do CBC serão exibidas.
    solver_kwargs = {"msg": msg_solver}

    # Verifica se foi informado um limite de tempo para a otimização.
    if time_limit is not None:

        # Adiciona o limite de tempo às configurações do solver.
        solver_kwargs["timeLimit"] = time_limit

    # Cria o solver CBC, responsável por resolver o problema MILP.
    solver = pulp.PULP_CBC_CMD(**solver_kwargs)


    # ============================================================
    # ETAPA 1: MAXIMIZAÇÃO DA QUANTIDADE DE ALUNOS ALOCADOS
    # ============================================================

    # Define a primeira função objetivo.
    # Como o modelo é de minimização, utilizamos o negativo da soma
    # das variáveis de alocação para maximizar a quantidade de alunos.
    #
    # Exemplo:
    # 10 alunos alocados -> objetivo = -10.
    # 20 alunos alocados -> objetivo = -20.
    # Minimizar -20 é melhor do que minimizar -10.
    modelo.setObjective(-pulp.lpSum(x.values()))

    # Executa a primeira etapa da otimização.
    _resolver(modelo, solver, "maximização de alunos alocados")

    # Obtém o maior número de alunos que o modelo conseguiu alocar.
    # pulp.value recupera o valor numérico da expressão após a resolução.
    # round arredonda o resultado e int converte para inteiro.
    melhor_total_alocados = int(
        round(pulp.value(pulp.lpSum(x.values())))
    )

    # Adiciona uma restrição que preserva o total máximo encontrado.
    # Assim, nas próximas etapas o solver não poderá reduzir
    # a quantidade de alunos alocados.
    modelo += (
        pulp.lpSum(x.values()) == melhor_total_alocados,
        "Preservar_maximo_alunos_alocados"
    )


    # ============================================================
    # ETAPA 2: EQUILÍBRIO DA PROPORÇÃO M/F DOS ALUNOS SELECIONADOS
    # ============================================================

    # Cria variáveis auxiliares para medir a diferença entre:
    # a proporção original de meninos em cada turno e
    # a proporção de meninos entre os alunos efetivamente selecionados.
    desvios_selecao = criar_desvios_selecao_genero(
        modelo, alunos, turmas, x
    )

    # Monta a função objetivo que soma os desvios de todos os turnos.
    # O objetivo será minimizar essa soma.
    objetivo_selecao = objetivo_equilibrio_selecao_genero(
        desvios_selecao
    )

    # Define a função objetivo da segunda etapa.
    modelo.setObjective(objetivo_selecao)

    # Executa a segunda etapa da otimização.
    _resolver(modelo, solver, "equilíbrio de gênero dos selecionados")

    # Recupera o menor desvio encontrado na segunda etapa.
    melhor_desvio_selecao = float(
        pulp.value(objetivo_selecao) or 0
    )

    # Preserva o melhor equilíbrio de gênero encontrado.
    # A tolerância 1e-5 evita problemas causados por pequenas
    # diferenças numéricas do solver.
    modelo += (
        objetivo_selecao <= melhor_desvio_selecao + 1e-5,
        "Preservar_equilibrio_genero_selecionados"
    )


    # ============================================================
    # ETAPA 3: EQUILÍBRIO DA QUANTIDADE DE ALUNOS NAS TURMAS
    # ============================================================

    # Define a função objetivo responsável por minimizar
    # a diferença entre a maior e a menor turma de cada turno.
    modelo.setObjective(
        objetivo_equilibrio_quantidade(menores, maiores)
    )

    # Executa a terceira etapa da otimização.
    _resolver(modelo, solver, "equilíbrio de quantidade")

    # Armazena a melhor amplitude encontrada para cada turno.
    # Amplitude é a diferença entre a maior e a menor turma.
    # Exemplo: maior turma = 20 e menor turma = 15.
    # Amplitude = 20 - 15 = 5.
    melhor_amplitude = {
        turno: int(
            round(pulp.value(maiores[turno] - menores[turno]))
        )
        for turno in menores
    }

    # Adiciona restrições para preservar a amplitude encontrada.
    # Dessa forma, a próxima etapa não poderá piorar o equilíbrio
    # da quantidade de alunos entre as turmas.
    preservar_equilibrio_de_quantidade(
        modelo, menores, maiores, melhor_amplitude
    )


    # ============================================================
    # ETAPA 4: EQUILÍBRIO DE GÊNERO DENTRO DAS TURMAS
    # ============================================================

    # Cria variáveis auxiliares que medem a diferença entre
    # a proporção de meninos de cada turma e a proporção original
    # de meninos do respectivo turno.
    desvios = criar_desvios_de_genero(
        modelo, alunos, turmas, x
    )

    # Define a função objetivo que soma os desvios de gênero das turmas.
    # O solver tentará minimizar essa soma.
    modelo.setObjective(
        objetivo_equilibrio_genero(desvios)
    )

    # Executa a última etapa da otimização.
    _resolver(modelo, solver, "equilíbrio de gênero nas turmas")


    # ============================================================
    # EXTRAÇÃO DOS RESULTADOS DA OTIMIZAÇÃO
    # ============================================================

    # Cria uma lista vazia para armazenar os alunos que foram alocados.
    alocacao = []

    # Cria uma lista vazia para armazenar os alunos que não conseguiram
    # ser alocados por falta de vagas disponíveis.
    nao_alocados = []

    # Cria um dicionário que armazenará os alunos agrupados por turma.
    # Cada chave será o nome da turma e cada valor será uma lista de alunos.
    por_turma = defaultdict(list)

    # Percorre todos os alunos recebidos pelo modelo.
    for aluno in alunos:

        # Inicializa a variável que armazenará a turma escolhida.
        # None indica que o aluno ainda não foi encontrado em nenhuma turma.
        turma_escolhida = None

        # Percorre todas as turmas disponíveis.
        for turma in turmas:

            # Cria a chave que identifica a variável de alocação
            # correspondente ao aluno e à turma atual.
            chave = (aluno["id"], turma["turma"])

            # Verifica se a combinação aluno/turma possui uma variável
            # e se o valor encontrado pelo solver é maior que 0.5.
            # Como a variável é binária, isso indica que ela vale 1.
            if chave in x and pulp.value(x[chave]) > 0.5:

                # Guarda a turma em que o aluno foi alocado.
                turma_escolhida = turma

                # Interrompe a busca porque o aluno já foi encontrado.
                break

        # Verifica se nenhuma turma foi escolhida para o aluno.
        if turma_escolhida is None:

            # Adiciona o aluno à lista de não alocados.
            # Também registra o motivo pelo qual ele não foi alocado.
            nao_alocados.append({
                "id": aluno["id"],
                "Nome do aluno": aluno["nome"],
                "Sexo": aluno["sexo"],
                "Disponibilidade": aluno["turno"],
                "Motivo": "Sem vagas disponíveis no turno"
            })

            # Pula para o próximo aluno.
            continue

        # Cria um dicionário com as informações do aluno alocado.
        registro = {
            "id": aluno["id"],
            "Nome do aluno": aluno["nome"],
            "Sexo": aluno["sexo"],
            "Disponibilidade": aluno["turno"],
            "Turma": turma_escolhida["turma"],
        }

        # Adiciona o registro à lista geral de alunos alocados.
        alocacao.append(registro)

        # Adiciona o aluno à lista de sua respectiva turma.
        por_turma[turma_escolhida["turma"]].append(aluno)


    # ============================================================
    # GERAÇÃO DO RESUMO DAS TURMAS
    # ============================================================

    # Cria uma lista vazia para armazenar os indicadores de cada turma.
    resumo = []

    # Percorre todas as turmas cadastradas.
    for turma in turmas:

        # Recupera a lista de alunos que foram alocados na turma atual.
        # Se a turma não tiver alunos, será retornada uma lista vazia.
        grupo = por_turma[turma["turma"]]

        # Conta quantos alunos do grupo são do sexo masculino.
        masculino = sum(a["sexo"] == "M" for a in grupo)

        # Conta quantos alunos do grupo são do sexo feminino.
        feminino = sum(a["sexo"] == "F" for a in grupo)

        # Calcula a quantidade total de alunos da turma.
        total = len(grupo)

        # Adiciona ao resumo as informações e os indicadores da turma.
        resumo.append({

            # Nome ou identificador da turma.
            "Turma": turma["turma"],

            # Turno ao qual a turma pertence.
            "Turno": turma["turno"],

            # Capacidade máxima da turma.
            "Vagas": turma["vagas"],

            # Quantidade de alunos efetivamente alocados.
            "Alunos": total,

            # Quantidade de vagas que ainda estão disponíveis.
            "Vagas restantes": turma["vagas"] - total,

            # Quantidade de alunos masculinos.
            "Masculino": masculino,

            # Quantidade de alunos femininos.
            "Feminino": feminino,

            # Diferença absoluta entre a quantidade de meninos e meninas.
            "Diferença M-F": abs(masculino - feminino),

            # Percentual de alunos masculinos na turma.
            # Se a turma estiver vazia, retorna 0 para evitar divisão por zero.
            "Percentual masculino": (
                round(100 * masculino / total, 2) if total else 0.0
            ),

            # Percentual de alunos femininos na turma.
            # Se a turma estiver vazia, retorna 0 para evitar divisão por zero.
            "Percentual feminino": (
                round(100 * feminino / total, 2) if total else 0.0
            ),
        })


    # ============================================================
    # GERAÇÃO DAS MÉTRICAS GERAIS DO MODELO
    # ============================================================

    # Calcula a quantidade total de alunos efetivamente alocados.
    total_alocados = len(alocacao)

    # Cria um dicionário com os indicadores gerais da otimização.
    metricas = {

        # Quantidade total de alunos recebidos pelo modelo.
        "total_alunos": len(alunos),

        # Quantidade total de alunos que conseguiram uma turma.
        "total_alocados": total_alocados,

        # Quantidade total de alunos que ficaram sem alocação.
        "total_nao_alocados": len(nao_alocados),

        # Quantidade total de turmas disponíveis.
        "total_turmas": len(turmas),

        # Melhor amplitude encontrada entre as turmas de cada turno.
        "amplitude_por_turno": melhor_amplitude,

        # Melhor desvio da proporção de gênero dos alunos selecionados.
        "desvio_genero_selecao": melhor_desvio_selecao,

        # Valor da função objetivo de equilíbrio de gênero dentro das turmas.
        "desvio_genero_modelo": float(
            pulp.value(objetivo_equilibrio_genero(desvios)) or 0
        ),
    }

    # Retorna todos os resultados do modelo em um único dicionário.
    return {

        # Indica que o solver encontrou uma solução ótima.
        "status": "Optimal",

        # Lista com os alunos e suas respectivas turmas.
        "alocacao": alocacao,

        # Lista com os alunos que não foram alocados e seus motivos.
        "nao_alocados": nao_alocados,

        # Resumo estatístico de cada turma.
        "resumo": resumo,

        # Indicadores gerais da otimização.
        "metricas": metricas,
    }
