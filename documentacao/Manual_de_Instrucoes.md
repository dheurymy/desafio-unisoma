# Manual de Instruções de Uso

## 1. Apresentação

O sistema realiza a distribuição de alunos em turmas de acordo com as informações fornecidas em uma planilha Excel.

Para utilizar o sistema, não é necessário clonar o projeto ou instalar programas de desenvolvimento. Basta ter acesso ao arquivo executável fornecido pela equipe.

## 2. Antes de começar

Prepare uma planilha Excel no formato `.xlsx` contendo os dados dos alunos e das turmas.

A planilha deve conter, preferencialmente, as abas `Alunos` e `Turmas`. As abas `Ensalamento` e `Inconsistências` podem estar presentes em arquivos já utilizados pelo sistema, mas não são necessárias para o primeiro carregamento.

## 3. Formato da aba Alunos

A aba `Alunos` deve conter uma linha para cada aluno. As três primeiras colunas devem seguir esta ordem:

| Ordem | Coluna | Preenchimento esperado |
|---|---|---|
| 1 | Nome | Nome completo do aluno |
| 2 | Sexo | `M` ou `F` |
| 3 | Disponibilidade | `Manhã` ou `Tarde` |

Exemplo:

| Nome | Sexo | Disponibilidade |
|---|---|---|
| Ana Souza | F | Manhã |
| João Lima | M | Tarde |

Evite deixar o nome do aluno vazio. Também confira se o sexo e a disponibilidade foram informados corretamente.

## 4. Formato da aba Turmas

A aba `Turmas` deve informar os recursos disponíveis para o ensalamento, como a quantidade de turmas e a quantidade de vagas para cada turno.

Utilize como referência as planilhas de exemplo fornecidas pela equipe. Não altere os nomes dos recursos nem a estrutura dessa aba sem orientação do responsável pelo sistema.

## 5. Como abrir o sistema

1. Localize o arquivo executável recebido da equipe.
2. Clique duas vezes no arquivo `EnsalamentoABC.exe`.
3. Aguarde a abertura da tela principal.
4. Se o Windows exibir uma mensagem de segurança, confirme a abertura somente se o arquivo tiver sido recebido de uma fonte confiável.

O programa não exige que o usuário abra o código-fonte ou utilize o terminal.

## 6. Como carregar uma planilha

1. Na tela inicial, escolha a opção para carregar ou selecionar uma planilha.
2. Localize o arquivo `.xlsx` no computador.
3. Selecione o arquivo e confirme a escolha.
4. Aguarde o sistema realizar a leitura e a verificação dos dados.

O arquivo original não deve ser alterado pelo sistema durante o tratamento. Mesmo assim, recomenda-se manter uma cópia de segurança da planilha antes de iniciar o processo.

## 7. Verificação dos dados

Após o carregamento, o sistema verifica os dados da planilha antes de executar a distribuição. São verificados, entre outros casos:

- ausência de nome;
- ausência de sexo;
- ausência de disponibilidade;
- valores inválidos em `Sexo`;
- valores inválidos em `Disponibilidade`;
- nomes incorretos das colunas principais;
- alunos duplicados no mesmo turno.

## 8. Correções automáticas

Alguns erros simples de escrita podem ser corrigidos automaticamente:

- `feminino` pode ser convertido para `F`;
- `masculino` pode ser convertido para `M`;
- `manha` pode ser convertido para `Manhã`;
- `matutino` pode ser convertido para `Manhã`;
- `vespertino` pode ser convertido para `Tarde`.

As correções realizadas são informadas ao usuário e ficam registradas nas inconsistências para conferência.

Valores como `I`, `Integral` ou `integral` não são convertidos automaticamente para um turno. Como não é possível escolher o turno correto apenas com essa informação, o registro é informado como inconsistente e não segue para a distribuição.

## 9. Alunos duplicados

Se dois alunos possuem o mesmo nome e a mesma disponibilidade, o sistema informa a duplicidade.

Essa situação não significa automaticamente que os registros serão excluídos. A ocorrência é registrada para que possa ser avaliada pela equipe responsável pelo ensalamento.

## 10. Resultado da validação

Ao final da verificação, o sistema informa:

- a quantidade de alunos válidos;
- a quantidade de inconsistências encontradas;
- as correções automáticas realizadas;
- os erros que não puderam ser corrigidos;
- se os dados estão prontos para a etapa de distribuição.

Quando houver inconsistências que impeçam o aproveitamento de um registro, esse registro não será enviado para a modelagem. Os demais alunos válidos poderão continuar no processo, conforme as regras da aplicação.

## 11. Como agir quando houver erros

Quando o sistema informar erros:

1. Leia a mensagem exibida.
2. Confira a linha e a coluna indicadas.
3. Abra uma cópia da planilha original.
4. Corrija os dados apontados.
5. Salve a planilha.
6. Carregue o arquivo corrigido novamente no sistema.

Exemplos de correções comuns:

- preencher um nome que esteja vazio;
- trocar um valor diferente de `M` ou `F` por um valor válido;
- trocar uma disponibilidade inválida por `Manhã` ou `Tarde`;
- verificar se o cabeçalho da coluna foi colocado na posição correta.

## 12. Execução do ensalamento

Quando a validação for concluída e os dados estiverem prontos, avance para a etapa de distribuição dos alunos.

O sistema utilizará os alunos válidos e as informações das turmas para executar o ensalamento conforme as regras do modelo matemático.

O tratamento dos dados não escolhe manualmente uma turma para cada aluno. Ele apenas prepara as informações e informa os problemas encontrados. A decisão final de distribuição é realizada pela etapa de modelagem.

## 13. Capacidade das turmas

Se houver mais alunos do que vagas disponíveis, o tratamento não interrompe automaticamente o processo por esse motivo.

Essa situação deve ser analisada pelo modelo de distribuição. O resultado poderá indicar que existe uma solução, que é necessário utilizar mais turmas ou que não há solução dentro das regras informadas.

## 14. Inconsistências e conferência

As inconsistências podem incluir informações como:

| Informação | Exemplo |
|---|---|
| Linha | Linha 12 da planilha original |
| Coluna | `Nome` |
| Tipo de erro | Valor ausente |
| Detalhes | Nome não informado |

As linhas indicadas correspondem à posição original na planilha, mesmo quando outras linhas também foram descartadas.

## 15. Mensagens de sucesso

A mensagem de que os dados estão prontos para a modelagem significa que a etapa de tratamento foi concluída.

Isso não garante que o ensalamento terá uma solução. A existência de uma solução depende das regras, das restrições e das vagas disponíveis analisadas pelo modelo matemático.

## 16. Problemas comuns

### O arquivo não abre

Verifique se:

- o arquivo é realmente um `.xlsx`;
- a planilha não está corrompida;
- o arquivo não está aberto em outro programa;
- foi utilizado o executável correto fornecido pela equipe.

### A aba de alunos não foi encontrada

Confira se a planilha contém uma aba chamada `Alunos`.

### A aba de turmas não foi encontrada

Confira se a planilha contém uma aba chamada `Turmas`.

### Muitos registros foram considerados inconsistentes

Confira os nomes das colunas, os valores de sexo e os turnos informados. Utilize `M`, `F`, `Manhã` e `Tarde` sempre que possível.

### O resultado não possui todos os alunos

Verifique a lista de inconsistências. Alunos com dados ausentes ou inválidos podem ter sido removidos do conjunto enviado para a modelagem.

## 17. Recomendações

- Mantenha uma cópia original da planilha.
- Não altere a estrutura das abas sem orientação.
- Confira as inconsistências antes de prosseguir.
- Corrija os dados na planilha e carregue-a novamente quando necessário.
- Não feche o programa enquanto o resultado estiver sendo processado.
- Guarde o arquivo de resultado gerado pelo sistema.

## 18. Suporte

Em caso de erro que não esteja descrito neste manual, envie à equipe responsável:

- a planilha utilizada;
- a mensagem exibida pelo sistema;
- a etapa em que o erro ocorreu;
- uma captura de tela, se possível.

Não envie senhas ou informações que não sejam necessárias para a análise do problema.
