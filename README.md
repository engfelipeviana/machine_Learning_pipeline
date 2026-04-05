# MLOps Pipeline - Local Infrastructure Base

Este repositório contém a infraestrutura base para um Pipeline de MLOps moderno, 100% conteinerizado usando Docker e `docker-compose`. Ele simula um ambiente de nuvem (como a AWS) localmente para garantir reprodutibilidade total nos projetos de engenharia de dados e ciência de dados.

## Arquitetura Fase 1

Nesta primeira fase, configuramos a base de dados em formato Data Lake house (desacoplando armazenamento de processamento legal) e o ambiente de desenvolvimento.

Os principais componentes são:

1. **MinIO (`minio` e `minio-init`)**
   - **Papel:** Servidor de armazenamento de objetos compatível com a API do AWS S3. É a fundação do Data Lakehouse.
   - **Buckets Padrão:** `landing-zone`, `mlops-data`, `warehouse`, `mlflow-artifacts` e `airflow-logs`.
   - **Portas:** `9000` (API) e `9001` (Console Web).

2. **PostgreSQL (`postgres-metastore`)**
   - **Papel:** Servidor de banco de dados relacional usado exclusivamente como o *Metastore* (Catálogo de Metadados) para os formatos de tabela Iceberg. Diferencia os metadados dos arquivos físicos do MinIO.
   - **Porta:** `5432`.

3. **Trino (`trino`)**
   - **Papel:** Motor de query SQL massivamente paralelo (MPP) que atua como nosso Data Warehouse e consulta remotamente o S3. Simula componentes parecidos com o AWS Athena / Redshift.
   - **Porta:** `8081` (Console Web UI e conexão via API).

4. **JupyterLab (`jupyterlab`)**
   - **Papel:** Ambiente de experimentação e ciência de dados local.
   - **Bibliotecas e Extensões:** Já vem com `pandas`, `boto3`, `s3fs`, conectores do Trino e a extensão gráfica `jupyterlab-s3-browser` para navegar no S3 diretamente na IDE.
   - **Acesso Descomplicado:** Autenticação via token desativada para desenvolvimento local.
   - **Porta:** `8888`.

---

## Como Executar

### 1. Pré-requisitos
Certifique-se de que sua máquina possui instalados:
- **Docker**
- **Docker Compose**

### 2. Subindo o Ambiente
Pelo terminal, navegue até a pasta do projeto (onde está o `docker-compose.yml`) e execute o comando abaixo para construir a imagem customizada do Jupyter e subir todos os serviços e suas redes parelhas no background:

```bash
docker compose up -d --build
```

> *Na primeira vez, o Docker pode demorar um pouco para baixar as imagens oficiais do MinIO, Trino, Postgres e Jupyter.*

### 3. Acessando os Serviços

Com os serviços rodando (`docker compose ps`), você poderá acessá-los através do seu navegador:

- **JupyterLab:** Acesse diretamente [http://127.0.0.1:8888](http://127.0.0.1:8888) (ou `localhost:8888`). Não é necessário procurar por tokens, a IDE abrirá automaticamente conectada.
  - **Navegador S3 Integrado:** No menu lateral esquerdo do JupyterLab, há um ícone de "Nuvem/Bucket" (`jupyterlab-s3-browser`). Clique nele e insira:
    - *Endpoint*: `http://minio:9000`
    - *Access Key*: `minioadmin`
    - *Secret Key*: `minioadmin`
    Isso permitirá navegar visualmente em todos os buckets do MinIO sem sair do Jupyter!

- **Painel Web Trino:** Acesse [http://localhost:8081](http://localhost:8081).
  *(Faça login utilizando o usuário genérico `admin`, sem necessidade de senha)*.

- **Painel Console MinIO:** Acesse [http://localhost:9001](http://localhost:9001).
  *(Faça login com User `minioadmin` e Password `minioadmin`)*.

---

## Exemplos de Uso

Dentro do seu JupyterLab, na aba de arquivos (lado esquerdo), você encontrará acesso à pasta de notebooks montada (`./jupyter/notebooks`), com exemplos consolidados:

- **Integração S3:** `upload_to_landing_zone.py` e `example_s3.py` para entender autenticação com `boto3` e o envio arquivos para MinIO.
- **Consultas Iceberg:** `example_trino.py` para consultar tabelas SQL fisicamente distantes sem mover o arquivo.
- **Machine Learning Integrado S3:** `ML_CLASSIFICAO_PENGUINS_MINIO.ipynb` apresenta um Pipeline completo: O Pandas lê dados do MinIO `landing-zone`, treina uma Árvore de Decisão e realiza cache serializado de volta no repositório `warehouse/models`.

### Persistência dos Notebooks
Qualquer notebook ou arquivo `.ipynb` criado e salvo pelo JupyterLab fica persistido **na sua máquina local** e mapeado na pasta `./jupyter/notebooks` usando os Volumes do Docker. 
Isso significa que **seu ambiente de estudos está a salvo mesmo se você matar os containers.**

---

## Como Desligar o Ambiente

Para parar o processamento local (sem deletar recursos ou dados):

```bash
docker compose stop
```

Se quiser desligar o ambiente completo e destruir os contêineres e na parte de rede (preservando o volume físico dos dados):

```bash
docker compose down
```

---

*A Fase 2 (Orquestração MLOps com Airflow e MLFlow) já teve seus buckets preparados e integrados. Brevemente os serviços estarão acoplados aqui.*
