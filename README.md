# MLOps Pipeline - Local Infrastructure Base

Este repositório contém a infraestrutura base para um Pipeline de MLOps moderno, 100% conteinerizado usando Docker e `docker-compose`. Ele simula um ambiente de nuvem (como a AWS) localmente para garantir reprodutibilidade total nos projetos de engenharia de dados e ciência de dados.

## 🏗 Arquitetura Fase 1

Nesta primeira fase, configuramos a base de dados em formato Data Lake house (desacoplando armazenamento de processamento legal) e o ambiente de desenvolvimento.

Os principais componentes são:

1. **MinIO (`minio` e `minio-init`)**
   - **Papel:** Servidor de armazenamento de objetos compatível com a API do AWS S3. É o nosso "Data Lake" bruto.
   - **Buckets Padrão:** `mlops-data` (arquivos crus) e `warehouse` (onde o Trino salvará os dados tabelados).
   - **Portas:** `9000` (API) e `9001` (Console Web).

2. **PostgreSQL (`postgres-metastore`)**
   - **Papel:** Servidor de banco de dados relacional usado exclusivamente como o *Metastore* (Catálogo de Metadados) para os formatos de tabela Iceberg. Diferencia os metadados dos arquivos físicos do MinIO.
   - **Porta:** `5432`.

3. **Trino (`trino`)**
   - **Papel:** Motor de query SQL massivamente paralelo (MPP) que atua como nosso Data Warehouse e consulta remotamente o S3. Simula componentes parecidos com o AWS Athena / Redshift.
   - **Porta:** `8081` (Console Web UI e conexão via API).

4. **JupyterLab (`jupyterlab`)**
   - **Papel:** Ambiente de experimentação e ciência de dados seguro em Python.
   - **Bibliotecas inclusas:** `pandas`, `boto3`, `s3fs`, `trino` e `sqlalchemy-trino`.
   - **Porta:** `8888`.

---

## 🚀 Como Executar

### 1. Pré-requisitos
Certifique-se de que sua máquina possui instalados:
- **Docker**
- **Docker Compose**

### 2. Subindo o Ambiente
Pelo terminal, navegue até a pasta do projeto (onde está o `docker-compose.yml`) e execute o comando abaixo para construir a imagem customizada do Jupyter e subir todos os serviços e suas redes parelhas no background:

```bash
docker compose up -d --build
```

> 💡 *Na primeira vez, o Docker pode demorar um pouco para baixar as imagens oficiais do MinIO, Trino, Postgres e Jupyter.*

### 3. Acessando os Serviços

Com os serviços rodando (`docker compose ps`), você poderá acessá-los através do seu navegador:

- **JupyterLab:** Para acessar o Jupyter, você precisa do Token de segurança que é gerado toda vez na inicialização. Para pegá-lo, veja os logs com o comando:
  ```bash
  docker compose logs jupyterlab | grep "token="
  ```
  Procure pelo link gerado `http://127.0.0.1:8888/lab?token=SEU_TOKEN_AQUI` e cole no navegador.

- **Painel Web Trino:** Acesse [http://localhost:8081](http://localhost:8081).
  *(Faça login utilizando o usuário genérico `admin`, sem necessidade de senha)*.

- **Painel Console MinIO:** Acesse [http://localhost:9001](http://localhost:9001).
  *(Faça login com User `minioadmin` e Password `minioadmin`)*.

---

## 🧪 Exemplos de Uso

Dentro do seu JupyterLab, na aba de arquivos (lado esquerdo), repare na pasta conectada contendo exemplos práticos:

- `example_s3.py`: Como autenticar via `boto3`, conectar no nosso MinIO falso e criar/enviar um arquivo Parquet usando DataFrame do Pandas.
- `example_trino.py`: Como conectar usando SQL Alchemy/trino DBAPI direto no container do Trino porta 8080 para testar conexões, listar schemas no `Iceberg` e consultar tabelas remotas sem precisar mover arquivos.

### Persistência dos Notebooks
Qualquer notebook ou arquivo `.ipynb` criado e salvo pelo JupyterLab fica persistido **na sua máquina local** e mapeado na pasta `./jupyter/notebooks` usando os Volumes do Docker. 
Isso significa que **seu ambiente de estudos está a salvo mesmo se você matar os containers.**

---

## 🛑 Como Desligar o Ambiente

Para parar o processamento local (sem deletar recursos ou dados):

```bash
docker compose stop
```

Se quiser desligar o ambiente completo e destruir os contêineres e na parte de rede (preservando o volume físico dos dados):

```bash
docker compose down
```

---

*Fase 2 de Ingestões Orquestradas usando Airflow vindo em breve...*
