# 🏦 BancoDigital — Flask + Docker Compose

Sistema bancário fullstack desenvolvido com **Python/Flask** e **PostgreSQL**, orquestrado com **Docker Compose**.

> Projeto da disciplina **Sistemas para Internet** — Prof. Igo Moura  
> Tópico: Orquestração de Múltiplos Containers com Docker Compose

---

## 📋 Sobre o Projeto

 O BancoDigital simula operações bancárias reais por meio de uma interface web moderna integrada a um backend Flask e banco de dados PostgreSQL.O sistema permite o gerenciamento completo de contas bancárias, incluindo movimentações financeiras, consultas de extrato e validações de segurança para evitar operações inválidas.

O **BancoDigital** simula operações bancárias reais:

* **Abertura de contas** com nome, CPF e saldo inicial
* **Depósito** — adiciona saldo à conta
* **Saque** — remove saldo com validação de saldo suficiente
* **Transferência** — movimenta valor entre duas contas (transação atômica com rollback)
* **Extrato** — histórico de transações por conta ou geral
* **Dashboard** — visão geral de todas as contas e saldo total

### Melhorias Implementadas na Versão Atual

* **Validação de CPF** com obrigatoriedade de 11 dígitos no cadastro de contas
* **Máscara automática de CPF** durante a digitação
* **Bloqueio de CPFs duplicados** no sistema
* **Confirmação de transferência** antes da execução da operação
* **Exclusão de contas** diretamente pela interface
* **Proteção contra exclusão de contas** que possuam transações registradas
* **Melhoria das mensagens de validação e feedback** para o usuário


---

## 🛠️ Tecnologias

| Camada | Tecnologia |
|--------|-----------|
| Backend | Python 3.11 + Flask 3.0 |
| Banco de Dados | PostgreSQL 15 |
| Orquestração | Docker Compose |
| Frontend | HTML + CSS + JavaScript (vanilla) |

---

## 📁 Estrutura do Projeto

```
banco-flask/
├── templates/
│   └── index.html        # Interface completa (HTML + CSS + JS)
├── app.py                # Backend Flask com todas as rotas
├── requirements.txt      # Dependências Python
├── Dockerfile
├── docker-compose.yml
├── .env
└── README.md
```

---

## 🗄️ Modelo de Dados

### Tabela `contas`
| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | SERIAL PK | Identificador único |
| titular | VARCHAR(100) | Nome do titular |
| cpf | VARCHAR(11) | CPF único |
| saldo | NUMERIC(10,2) | Saldo atual |
| criado_em | TIMESTAMP | Data de abertura |

### Tabela `transacoes`
| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | SERIAL PK | Identificador único |
| conta_id | FK → contas | Conta relacionada |
| tipo | VARCHAR(30) | deposito / saque / transferencia_saida / transferencia_entrada |
| valor | NUMERIC(10,2) | Valor da operação |
| descricao | TEXT | Descrição opcional |
| realizado_em | TIMESTAMP | Data/hora da operação |

---

## 🚀 Como Rodar

### Pré-requisitos
- [Docker](https://docs.docker.com/get-docker/) instalado e rodando

### Passo a passo

```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/banco-flask.git
cd banco-flask

# 2. Crie o arquivo .env
cp .env.example .env

# 3. Suba o ambiente
docker compose up -d

# 4. Acesse no navegador
# http://localhost:3000
```

---

## ✅ Comandos Úteis

| Comando | Descrição |
|---------|-----------|
| `docker compose up -d` | Sobe todos os containers |
| `docker compose logs -f` | Acompanha os logs |
| `docker compose down` | Para os containers (dados persistem) |
| `docker compose down -v` | Para e apaga os dados |
| `docker compose up -d --build` | Reconstrói após alterar código |

---

## 🔥 Prova de Fogo — Persistência de Dados

```bash
# 1. Sobe o ambiente
docker compose up -d

# 2. Crie contas e faça operações em http://localhost:3000

# 3. Derruba TUDO
docker compose down

# 4. Sobe novamente
docker compose up -d

# 5. Acesse http://localhost:3000 — dados ainda estão lá! ✅
```

Isso funciona porque o volume `dados_banco` persiste no host.  
Apenas `docker compose down -v` apagaria os dados.

---

## 🌐 Arquitetura Docker

```
[Navegador] → localhost:3000 → [banco-web: Flask] → db:5432 → [banco-postgres: PostgreSQL]
                                      ↑                                    ↑
                                  rede-banco                          dados_banco (volume)
```

O Docker Compose cria a rede interna `rede-banco`. O Flask se conecta ao PostgreSQL usando o hostname `db`, que é resolvido automaticamente pelo DNS interno do Docker.
