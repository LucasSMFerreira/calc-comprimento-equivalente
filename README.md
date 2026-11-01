Calculadora de Comprimento Equivalente
Software aberto para calcular o comprimento equivalente de tubulações hidráulicas.
Trabalho da P2 de Fenômenos de Transporte, Universidade de Vassouras.

Em construção. Acompanhe pelas issues.

![CI](https://github.com/LucasSMFerreira/calc-comprimento-equivalente/actions/workflows/ci.yml/badge.svg)

## Deploy (Discloud)

1. `cp .env.example .env` e defina um `ADMIN_TOKEN` forte.
2. Primeiro deploy: `discloud app up` na raiz do projeto.
3. Atualizações: `discloud app commit <ID do app>`.

O banco `data/calculadora.db` está no `.discloudignore`, então os deploys nunca apagam as versões da tabela salvas no site.