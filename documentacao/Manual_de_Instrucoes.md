# Manual de Instruções

## 1. Sobre o sistema

O sistema realiza o ensalamento de alunos em turmas a partir de uma planilha Excel.

O fluxo geral da aplicação é:

```text
Carregamento da planilha
        ↓
Tratamento e validação dos dados
        ↓
Separação dos dados válidos e das inconsistências
        ↓
Execução do modelo matemático
        ↓
Exibição do resultado do ensalamento
```

O tratamento dos dados é realizado pelo arquivo `projeto/etl/tratamento.py`. A modelagem está concentrada na pasta `projeto/modelagem` e a aplicação é iniciada pelo arquivo `projeto/app.py`.

## 2. Requisitos

Para executar o projeto pelo código-fonte, é necessário ter:

- Python instalado;
- acesso ao terminal;
- as bibliotecas listadas em `projeto/requirements.txt`;
- uma planilha Excel no formato `.xlsx`.

Instale as dependências a partir da pasta do projeto:

```bash
pip install -r projeto/requirements.txt
```

## 3. Como iniciar a aplicação

Na raiz do projeto, execute:

```bash
python projeto/app.py
```

Também existe uma versão compilada em `projeto/dist/EnsalamentoABC.exe`, quando essa versão estiver disponível para distribuição.

## 4. Formato da planilha de entrada

A planilha deve ser um arquivo Excel (`.xlsx`) com as abas utilizadas pelo sistema.

### 4.1 Aba `Alunos`

A aba deve conter os dados dos alunos. As três primeiras colunas devem representar:

| Posição | Coluna esperada | Descrição |
|---|---|---|
| 1 | `Nome` | Nome completo do aluno |
| 2 | `Sexo` | Sexo do aluno, normalmente `M` ou `F` |
| 3 | `Disponibilidade` | Turno disponível, normalmente `Manhã` ou `Tarde` |

O tratamento considera a posição das três primeiras colunas para identificar casos em que o cabeçalho foi preenchido com um nome incorreto. Por exemplo, se a primeira coluna estiver nomeada de forma diferente, ela poderá ser reconhecida como a coluna `Nome` e a correção será registrada.

### 4.2 Aba `Turmas`

A aba `Turmas` contém os recursos disponíveis para o ensalamento, como a quantidade de turmas e de vagas por turno.

Os nomes e a organização dos recursos devem seguir o padrão das instâncias de teste fornecidas em `documentacao/instancias`.

### 4.3 Outras abas

As instâncias de teste também podem conter abas como `Ensalamento` e `Inconsistências`. O tratamento atual lê as planilhas disponíveis no arquivo, mas não altera o Excel original.

## 5. Tratamento dos dados

O arquivo `projeto/etl/tratamento.py` executa as seguintes etapas:

1. lê o arquivo Excel;
2. localiza as abas de alunos e turmas;
3. verifica as colunas necessárias;
4. corrige alguns erros de escrita conhecidos;
5. identifica valores ausentes ou inválidos;
6. separa os alunos válidos dos registros inconsistentes;
7. identifica alunos duplicados no mesmo turno;
8. devolve os dados preparados para a modelagem.

O tratamento não realiza a distribuição dos alunos nas turmas. Essa decisão pertence ao modelo matemático.

## 6. Correções automáticas

Alguns erros de escrita podem ser corrigidos automaticamente.

### Sexo

Exemplos de valores reconhecidos e padronizados:

| Valor informado | Valor tratado |
|---|---|
| `feminino` | `F` |
| `mulher` | `F` |
| `masculino` | `M` |
| `homem` | `M` |

### Disponibilidade

Exemplos de valores reconhecidos e padronizados:

| Valor informado | Valor tratado |
|---|---|
| `manha` | `Manhã` |
| `manhã` | `Manhã` |
| `matutino` | `Manhã` |
| `tarde` | `Tarde` |
| `vespertino` | `Tarde` |

Valores como `I`, `Integral` ou `integral` não são convertidos automaticamente para um turno. Eles permanecem como inconsistências e o registro é descartado do dataframe enviado à modelagem, pois escolher um turno nesse momento seria uma decisão da modelagem, não do tratamento.

Todas as correções automáticas são registradas no dataframe de inconsistências.

## 7. Inconsistências

Quando um registro não pode ser corrigido com segurança, ele não é enviado à modelagem. A ocorrência é registrada no dataframe de inconsistências.

Os casos verificados incluem:

- nome ausente;
- sexo ausente;
- disponibilidade ausente;
- sexo inválido;
- disponibilidade inválida;
- cabeçalho identificado ou corrigido pela posição;
- alunos duplicados no mesmo turno.

Um aluno duplicado no mesmo turno é informado como inconsistência, mas os registros não são automaticamente descartados. Essa decisão pode depender das regras do problema e deve ser avaliada pela equipe responsável pela modelagem.

As inconsistências possuem informações como:

| Campo | Descrição |
|---|---|
| `Linha` | Número da linha correspondente à planilha original |
| `Coluna` | Coluna relacionada ao problema |
| `Tipo de erro` | Categoria da inconsistência |
| `Detalhes` | Descrição do valor encontrado ou da correção realizada |

O número da linha preserva a posição original na planilha, inclusive quando outras linhas anteriores foram descartadas.

## 8. Retorno do tratamento

O processamento retorna um objeto com as informações do resultado, incluindo:

- status do processamento;
- mensagem geral;
- lista de erros iniciais;
- lista de correções automáticas;
- dataframe de alunos válidos;
- dataframe de turmas;
- dataframe de inconsistências.

O dataframe de alunos válidos deve ser encaminhado para a modelagem. O dataframe de inconsistências pode ser exibido ao usuário para conferência ou disponibilizado para download.

O arquivo Excel original não é sobrescrito nem modificado durante o tratamento.

## 9. Capacidade das turmas

O tratamento não bloqueia a execução quando a quantidade de alunos é maior que a quantidade de vagas disponíveis.

Essa situação deve ser tratada pelo modelo matemático, que pode identificar a inviabilidade, aplicar as regras definidas pelo problema ou informar que não existe solução dentro das restrições fornecidas.

Da mesma forma, o tratamento não decide que uma turma deve ser utilizada antes de outra. Regras como minimizar a quantidade de turmas utilizadas devem ser representadas na função objetivo ou nas restrições do modelo.

## 10. Arquivos de debug

Para facilitar a conferência durante o desenvolvimento, o tratamento possui uma opção de salvamento dos dataframes em CSV.

Quando o salvamento de debug está habilitado, os arquivos são gerados em:

```text
projeto/dados/debug/alunos_tratados.csv
projeto/dados/debug/inconsistencias.csv
```

Esses arquivos são auxiliares para conferência e não substituem o arquivo Excel original.

Quando não for mais necessário gerar esses arquivos, a opção de debug pode ser desabilitada no arquivo `projeto/etl/tratamento.py`.

## 11. Mensagens exibidas no terminal

Durante a execução, o sistema pode exibir mensagens como:

```text
DataFrame de alunos válidos: 120 linha(s)
DataFrame de inconsistências: 7 linha(s)
```

Também podem ser exibidos:

- erros encontrados na leitura ou validação;
- correções automáticas realizadas;
- alunos duplicados no mesmo turno;
- confirmação de que os dados estão prontos para a modelagem.

Uma mensagem de sucesso significa que o tratamento foi concluído. Ela não significa necessariamente que o problema de ensalamento possui solução, pois essa verificação pertence à etapa de modelagem.

## 12. Organização do projeto

As principais pastas e arquivos são:

```text
projeto/
├── app.py                    # Ponto de entrada da aplicação
├── backend/                  # Comunicação e serviços do backend
├── etl/
│   └── tratamento.py         # Leitura, validação e preparação dos dados
├── modelagem/                # Restrições, objetivo e otimização
├── frontend/                 # Interface visual da aplicação
├── dados/                    # Instâncias e arquivos auxiliares
├── requirements.txt          # Dependências Python
└── dist/                     # Versão compilada, quando gerada
```

## 13. Fluxo recomendado para o usuário

1. Prepare a planilha de acordo com o formato descrito neste manual.
2. Abra a aplicação.
3. Carregue o arquivo `.xlsx`.
4. Aguarde a validação dos dados.
5. Confira as mensagens e as inconsistências identificadas.
6. Corrija a planilha original se necessário e carregue-a novamente.
7. Prossiga com os registros válidos para a etapa de modelagem.
8. Analise o resultado do ensalamento.

## 14. Observações para desenvolvedores

O tratamento deve permanecer responsável pela qualidade e pela padronização dos dados. A modelagem deve permanecer responsável pelas decisões de alocação e otimização.

Essa separação evita que regras de distribuição sejam implementadas como decisões fixas no tratamento. Assim, alterações nas regras do ensalamento podem ser feitas no modelo matemático sem modificar a etapa de preparação dos dados.

Antes da entrega final, recomenda-se testar as quatro instâncias disponíveis em `documentacao/instancias` e verificar:

- a quantidade de alunos válidos;
- a quantidade de inconsistências;
- as correções automáticas realizadas;
- as linhas originais indicadas nos erros;
- o comportamento da modelagem quando a capacidade é insuficiente.
