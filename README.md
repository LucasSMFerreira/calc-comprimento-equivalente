# Calculadora de Comprimento Equivalente

![CI](https://github.com/LucasSMFerreira/calc-comprimento-equivalente/actions/workflows/ci.yml/badge.svg)

Software aberto que calcula o comprimento equivalente de tubulações hidráulicas.
Trabalho da P2 de Fenômenos de Transporte, Universidade de Vassouras, 2026.2.

**Acesse:** https://calc-hidraulica.discloud.dev

## Como funciona

Cada conexão (joelho, registro, válvula) causa uma perda de carga. O comprimento equivalente
é o tamanho de tubo reto, de mesmo diâmetro, que causaria a mesma perda. A calculadora soma:

L_total = Σ (quantidade × L_eq unitário)

com os valores da planilha `1 Perda de Carga Localizada.xlsx` (35 conexões, PVC e Metal, de 1/4" a 14").

## Como usar

1. Escolha o diâmetro em polegadas ou milímetros.
2. Toque nas fotos das conexões, ou descreva em texto, ou importe uma planilha.
3. Veja o comprimento equivalente total e baixe o memorial em PDF.

## Funcionalidades

- Cálculo com `Decimal`, sem erro de arredondamento
- Material por item (PVC ou Metal) e diâmetro em pol ou mm
- Entrada por planilha modelo e por texto livre, sempre com confirmação
- IA local opcional (Ollama no homelab) para frases soltas; a IA nunca calcula
- Memorial de cálculo em PDF com lista de compras
- Tabela base salva em SQLite, com versões, prévia de mudanças, exportação e senha de admin

## Arquitetura

| Pasta | Responsabilidade |
| --- | --- |
| `app/dominio` | Física pura: tabela, cálculo, diâmetros (não conhece web nem banco) |
| `app/dados` | Importar a planilha e guardar versões em SQLite |
| `app/entrada` | Ler planilha de itens, texto e IA |
| `app/relatorio` | Memorial em PDF |
| `app/static` | Interface (HTML, CSS, JavaScript) |
| `app/main.py` | API FastAPI |
| `servico_ia` | Serviço com token na frente do Ollama (roda no homelab) |

## Rodar localmente

    python3 -m venv .venv && source .venv/bin/activate
    pip install -r requirements-dev.txt
    cp .env.example .env
    python run.py            # http://127.0.0.1:8080
    pytest -v                # 55 testes

## Validação

O Exercício 5 dos slides (3/4") dá 17,80 m, igual ao gabarito. Detalhes em [docs/validacao.md](docs/validacao.md).

## Deploy

Discloud (`discloud.config`). O banco fica no `.discloudignore`, então os deploys não apagam as versões da tabela.

## Licença

MIT. Autor: Lucas Martins Ferreira.