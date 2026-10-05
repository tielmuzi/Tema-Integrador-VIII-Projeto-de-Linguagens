# Plano de implementação — Escudo d'Água

## Escopo aprovado
Compilador modular em Python para uma DSL de monitoramento de chuvas e prevenção de alagamentos, com Scanner, Parser descendente recursivo, Interpretador, integração com respostas de Google Forms, exemplos T01–T06, documentação de terminal e versão web responsiva para inspeção do pipeline.

## Decisões de implementação
- A DSL usa `INICIO`/`FIM` como delimitadores, identificadores iniciados por maiúscula, números inteiros e os símbolos `(`, `)`, `;`, `,`, `=`.
- O scanner usa exclusivamente `re` para reconhecer palavras reservadas, IDs, números e símbolos, reportando posição e trecho do erro.
- O parser é descendente recursivo e expõe uma árvore JSON serializável.
- O interpretador mantém áreas, sensores, níveis e alarmes em memória e produz mensagens legíveis.
- A API web chama o mesmo pipeline Python; não existe uma segunda implementação da linguagem no frontend.

## Estrutura
- `src/scanner.py`: tokens, regras léxicas e erros.
- `src/parser.py`: AST, gramática e erros sintáticos.
- `src/interpretador.py`: execução e simulação.
- `src/main.py`: CLI e função de pipeline.
- `scripts/integracao_forms.py`: CSV → programa `.min`.
- `exemplos/`: matriz T01–T06 e arquivos de entrada.
- `web/`: editor, visualização de tokens/árvore/execução e testes.
- `server.py`: servidor HTTP e endpoint `/api/compile`.

## Dados incorporados
`dados/respostas_google_forms.csv` guarda a planilha fornecida em UTF-8; `scripts/analisar_respostas.py` gera `dados/resumo_respostas.json` com 13 respostas, distribuição estimada de risco, canais, conteúdos de alerta, apoio a sensores e evidências. A integração usa esse resumo para gerar níveis numéricos na DSL quando a planilha não possui uma coluna de risco explícita. A bancada web expõe esses indicadores em “Pesquisa de campo”.

## Direção visual
A interface segue uma estética de centro de operações climático: azul-petróleo profundo para confiança, amarelo-chuva como assinatura de alerta e superfícies claras para leitura rápida. O layout usa uma coluna de contexto lateral e um painel de trabalho amplo, com cartões de telemetria, bordas suaves e microanimações discretas. A voz é técnica, humana e preventiva: “Leia o sinal antes da enchente” e “Cada token deixa o risco mais visível”.

## Marca
Posicionamento: uma bancada didática que transforma dados de chuva em decisões compreensíveis. Personalidade: atenta, didática, responsável. A marca usa o escudo com ondas fornecido em `web/image/` e o nome Escudo d'Água junto ao símbolo.
