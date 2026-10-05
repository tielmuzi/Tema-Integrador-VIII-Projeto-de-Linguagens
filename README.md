# Escudo d'Água — compilador de monitoramento de chuvas

O Escudo d'Água implementa, em Python puro, um compilador didático para uma DSL de monitoramento de chuvas e prevenção de alagamentos. O pipeline é explícito: **Scanner → Parser → Interpretador**. A pasta `web/` expõe o mesmo pipeline em uma bancada visual no navegador.

## Alinhamento aos Objetivos de Desenvolvimento Sustentável

O projeto tem como referência principal o **ODS 10 — Redução das Desigualdades**, especialmente a meta **10.2**, de promover a inclusão social de pessoas em situação de vulnerabilidade, e a meta **10.3**, de garantir igualdade de oportunidades e reduzir desigualdades de resultados. No contexto do Escudo d'Água, isso significa orientar o desenvolvimento para tornar informações sobre riscos climáticos mais compreensíveis e reduzir barreiras comunicacionais.

O projeto também se co-alinha ao **ODS 4 — Educação de Qualidade**, em particular às metas **4.5**, sobre eliminar disparidades no acesso e na participação, e **4.a**, sobre ambientes de aprendizagem inclusivos e acessíveis. A proposta é fortalecer práticas pedagógicas inclusivas com tecnologia assistiva.

Na versão atual, a pesquisa comunitária reúne evidências sobre impactos e preferências de comunicação, enquanto o monitoramento e os alertas da interface são simulações demonstrativas. O projeto é um protótipo educacional: não opera ainda como serviço de alerta nem comprova, por si só, a remoção de barreiras de acesso.

## Tecnologias utilizadas

- **Python 3.10+** e biblioteca padrão para o compilador (Scanner, Parser e Interpretador), a CLI, os scripts de dados e o servidor HTTP local. Não há dependências externas de Python para executar o projeto.
- **HTML5, CSS3 e JavaScript puro** para a interface web responsiva, sem framework ou pacote de frontend.
- **HTTP e JSON** na API local que conecta a interface ao servidor Python.
- **CSV e JSON** para importar respostas do formulário e armazenar dados e resumos.
- **Google Fonts** (Manrope e DM Mono) para a tipografia da interface.
- **Pyright** como ferramenta opcional de análise estática de tipos, configurada em `pyrightconfig.json`.

## Requisitos e inicialização

Use Python 3.10 ou superior. A biblioteca padrão é suficiente; não há dependências obrigatórias externas.

```bash
cd Projeto Escudo d'Água
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Executar o compilador

A entrada é um arquivo `.min`. O comando abaixo imprime tokens, árvore sintática, status e a saída da simulação em JSON:

```bash
python -m src.main exemplos/T01_valido_simples.min --json
```

Para inspecionar apenas etapas específicas:

```bash
python -m src.main exemplos/T02_valido_varias_instrucoes.min --tokens
python -m src.main exemplos/T02_valido_varias_instrucoes.min --ast
python -m src.main exemplos/T02_valido_varias_instrucoes.min --sem-execucao
```

A linguagem aceita `INICIO` e `FIM`, declarações de área com uma lista de parâmetros, sensores, comandos `MONITORE`, `ALARME` e atribuições de nível. Exemplos:

```text
INICIO
AREA Centro (SENSOR, NIVEL);
NIVEL Centro = 85;
MONITORE Centro;
ALARME;
FIM
```

Os identificadores seguem `[A-Z][a-zA-Z0-9_]*`; números são inteiros `[0-9]+`. Comentários iniciados por `#` são ignorados.
Erros léxicos e sintáticos informam linha e coluna e incluem o trecho de código com um marcador na posição do problema.

## Google Forms

Exporte o formulário para CSV com colunas equivalentes a `bairro`/`área` e `nível de risco`/`risco`. Em seguida:

```bash
python scripts/integracao_forms.py dados/respostas_google_forms.csv programa_valido.min
python -m src.main programa_valido.min --json
```

A integração converte níveis textuais `baixo`, `médio` e `alto` para 25, 60 e 90, respectivamente. Números informados são limitados ao intervalo de 0 a 100.

A planilha fornecida pelo formulário não possui uma coluna numérica de risco. O projeto calcula uma estimativa por resposta cruzando suscetibilidade declarada, frequência de alagamentos e quantidade de impactos relatados. O resumo reproduzível fica em `dados/resumo_respostas.json` e pode ser regenerado com:

```bash
python scripts/analisar_respostas.py dados/respostas_google_forms.csv dados/resumo_respostas.json
```

Na amostra analisada, são 13 respostas: 8 perfis (62%) foram classificados como risco alto; 11 pessoas usariam o sistema digital; 13 consideram sensores importantes ou muito importantes; WhatsApp aparece em 9 respostas e SMS em 5. Localização do risco é a informação mais solicitada (11 respostas), seguida de orientações de segurança (9). Esses sinais agora aparecem na seção “Pesquisa de campo” da versão web e orientam a geração automática dos níveis da DSL.

## Casos de validação

| Caso | Arquivo | Resultado esperado |
|---|---|---|
| T01 | `exemplos/T01_valido_simples.min` | Aceito |
| T02 | `exemplos/T02_valido_varias_instrucoes.min` | Aceito |
| T03 | `exemplos/T03_comando_desconhecido.min` | Erro léxico |
| T04 | `exemplos/T04_sem_ponto_virgula.min` | Erro sintático |
| T05 | `exemplos/T05_parenteses_incorretos.min` | Erro sintático |
| T06 | `exemplos/T06_id_invalido.min` | Erro léxico |

Para executar a matriz:

```bash
for arquivo in exemplos/T*.min; do
  echo "==== $arquivo ===="
  python -m src.main "$arquivo" --json || true
done
```

## Versão web

A interface web possui visão geral, pesquisa comunitária, monitoramento, classificação de risco, compilador DSL e relatórios. A pesquisa usa os indicadores agregados do CSV real; pontos, medições e alertas são demonstrativos, aparecem identificados como simulados e ficam persistidos em `dados/monitoramento.json`.

O monitoramento permite cadastrar e excluir pontos, registrar medições, simular uma enchente e consultar o histórico. As faixas de risco são editáveis e o simulador recalcula o resultado durante a edição. O compilador oferece validação sem execução, interpretação, tokens, AST e erros com trecho e marcador de coluna. Relatórios exportam dados consolidados em CSV e podem ser impressos ou salvos como PDF pelo navegador.

```bash
python server.py
```

Abra `http://localhost:3000`. Além do endpoint `POST /api/compile`, a API local oferece `/api/dashboard`, `/api/monitoring`, `/api/points`, `/api/measurements`, `/api/simulate` e `/api/rules` para a interface operacional. O arquivo de telemetria inicial é criado automaticamente quando o servidor inicia pela primeira vez.

## Estrutura modular

`src/scanner.py` concentra tokens e erros léxicos; `src/parser.py` contém a gramática e a AST; `src/interpretador.py` simula o domínio; `src/main.py` orquestra CLI e API; `scripts/integracao_forms.py` faz a conversão de dados; `exemplos/` guarda a matriz; `web/` é a camada de visualização.

## Licença acadêmica

Projeto desenvolvido para fins educacionais no contexto do Escudo d'Água. Desenvolvedor: Salatiel Muzi Martins. Direitos reservados © 2026.
