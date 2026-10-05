# Dados da pesquisa

`respostas_google_forms.csv` é a exportação fornecida para o Projeto Escudo d'Água, convertida para UTF-8 e mantida no repositório para permitir reprodução da análise. `resumo_respostas.json` é gerado por `scripts/analisar_respostas.py`.

A pesquisa não possui uma coluna explícita de nível numérico. Por isso, o script estima o risco por resposta cruzando suscetibilidade declarada, frequência de alagamentos e quantidade de impactos relatados. O resultado alimenta `scripts/integracao_forms.py` e a seção de evidências da versão web.
