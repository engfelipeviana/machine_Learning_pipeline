# Self-Healing MLOps Platform (End-to-End)

Uma plataforma de Machine Learning Operations de nível corporativo, projetada em arquitetura de microsserviços, 100% conteinerizada (Docker), orientada a Data Contracts (YAML) e blindada por sistemas de Auto-Cura (Self-Healing) contra Data/Concept Drift.

---

## Como Iniciar a Aplicacao (Bootstrapping)

A arquitetura foi inteiramente orquestrada via Docker Compose nativo em Linux. Para subir o laboratório isolado na sua máquina sem instalar nenhuma dependência sistêmica fora do Docker Engine:

1. Clone o repositório e navegue até o diretório da Pipeline:
```bash
git clone https://github.com/engfelipeviana/machine_Learning_pipeline.git
cd machine_Learning_pipeline
```

2. Inicialize a Nuvem da Infraestrutura e Build workers isolados:
```bash
# Sobe os containers de rede raiz, bancos, Plataformas Airflow/MLflow e APIs
docker compose up -d

# Builda localmente as Imagens Master para os Workers Analíticos e de Computacao do Airflow
docker compose build builder-data-worker
docker compose build builder-mlops-worker
```

3. Acesse os Endpoints Essenciais via localhost:
- Apache Airflow (Orquestrador UI): http://localhost:8088 (admin / admin)
- MinIO S3 (Data Lake Console): http://localhost:9001 (minioadmin / minioadmin)
- MLflow (Model Registry): http://localhost:5000
- FastAPI (Inference Swagger UI): http://localhost:8000/docs
- Trino / JupyterLab: http://localhost:8888

---

## Arquitetura Macro da Solucao

O ecossistema divide-se em Ingestão Medallion, Orquestracao Docker-in-Docker (DinD), Registro Científico Controlado e Consumo API de Baixa Latência. A Máquina Airflow lidera a auto-manutenção da Inteligência Artificial.

```mermaid
graph TD
    User([Engenheiro/Analista]) --> Airflow
    Client([Aplicacoes Web Mobile]) --> FastAPI

    subgraph S3 MinIO Data Lake
        LZ[(Landing Zone)]
        Raw[(Raw Zone)]
        Trusted[(Trusted Iceberg)]
    end

    subgraph Computacao Cron
        DAG1[DAG 01: ELT Medallion]
        DAG2[DAG 02: Model Trainer]
        DAG4[DAG 04: Drift Monitor]
    end
    
    subgraph Docker Workers Socket Isolado
        DW[Data Eng Worker Pandas]
        MW[MLOps Worker Scikit/Evidently]
    end

    MLF[(MLflow Model Registry)]
    
    DAG1 --> DW
    DW --> LZ
    DW --> Raw
    DW -->|ingestion_date Append| Trusted
    
    DAG2 --> MW
    MW --> |Baixa Contrato YAML e Trusted Matriz| Trusted
    MW --> |Registra versao Champions| MLF
    
    DAG4 --> MW
    MW --> |Compara Timeline via Estatistica KS| Trusted
    MW -- Trigger MLOps XCom TRUE --> DAG2
    
    MLF -. FastAPI Puxa RAM do S3 .-> FastAPI
```

---

## Componentes da Arquitetura em Detalhes

### 1. Data Engineering (Pipeline ELT Medallion)
A ingestão de dados atua sobre o modelo de camadas lógicas (Medallion Architecture) persistindo DataFrames físicos no S3, rastreados matematicamente via Particionamento Temporal.

- Fluxo Lógico: O arquivo cru chega na Landing Zone. A DAG 01 Airflow invoca um container Docker puro que higieniza e converte o dado para Parquet (Raw Zone). No ultimo salto, uma coluna sistêmica temporal ingestion_date e aplicada e o Delta/Append e soldado sobre a camada central Trusted Zone.
- Norte Estratégico: Fornecer massas de dados governadas limpas pro time de Dados rodar Feature Engineering e Consultas ANSI SQL Pesadas, entregando aos Cientistas blocos padronizados de Inteligência Artificial.

```mermaid
sequenceDiagram
    participant S31 as S3/Landing
    participant AW as Airflow DockerOperator
    participant DW as Python Data Worker
    participant S33 as S3/Trusted
    
    AW->>DW: Aciona Sub-rotina DAG 01
    DW->>S31: Le arquivo cru CSV
    DW->>DW: Higieniza Tipagem e Remove Outliers
    DW->>DW: Add Feature ingestion_date
    DW->>S33: Resgata Cargas Historicas Particionadas
    DW->>DW: pd.Concat entre Dados Velhos e Novos
    DW->>S33: Sobrescreve Iceberg Parquet Append
```

### 2. Contract-Driven ML Training (Orquestracao DinD)
A pipeline defende e erradica o risco de Código Rígido do Cientista rodando local em laboratório. Todo o Treino é abstraído por Variáveis em um Arquivo passivo Genérico. Todo Treino roda em ambientes sub-virtuais isolados e que sofrem Auto-Destruicao assim que finalizados.

- Fluxo Lógico: A DAG 02 do Airflow lê o arquivo penguins_contract.yaml. O processo chama o Socket do Docker da Máquina Servidora (DinD) pedindo pra levantar temporariamente a imagem worker-mlops. Variáveis do Contrato sao injetadas. Ele treina o Modelo Scikit Pipeline robusto local e aciona client nativo do MLflow. O binário Pickle sobe criptografado ao repositório unificado.
- Norte Estratégico: Viabilizar escalabilidade. Ambientes Orquestradores Limpos. Pra testar Redes Neurais vs XGBoost num modelo novo, muda-se o contrato YAML sem ter que refatorar os Pythons base.

```mermaid
graph LR
    YAML[penguins_contract.yaml S3] -->|Airflow Parser| DIND[DockerOperator Socket]
    DIND -->|Spawn Isolate Session| MWO[Ubuntu worker-mlops]
    MWO -->|Fetches Train Slice| Data[(Trusted Delta Sets)]
    MWO -->|Scikit-Learn Model Fit| Artifact[(Pickle Binary)]
    Artifact --> MLflow[Logger MLflow Tracking API]
    MLflow --> S3Bucket[(MLflow Artifacts Store)]
```

### 3. Model Serving (FastAPI Real Time)
A fronteira da MLOps não termina onde o Treino acaba, mas sim como ele é Exposto como Produto Global pro Ecossistema.

- Fluxo Lógico: Um Servidor FastAPI inicia atrelando a um evento raiz Lifespan. Imediatamente, ele acessa o Banco Log SQL Postgre do MLflow por API para cacar via string Tag Qual a versao atual marcada como Champion. Após deduzir o Hash Key, o endpoint baixa o Parquet de lógicas treináveis pra dentro da Memória RAM. As Rotas abrem as portas de Inference.
- Norte Estratégico: Entrega com Latência Baixa HTTP JSON ao Frontend e tolerância a quedas via Inversão Computacional de Despacho (O Cérebro S3 preenche o Modelo Local Instantaneamente na inicialização do serviço Cloud).

```mermaid
sequenceDiagram
    participant App as FrontEnd App/React
    participant API as FastAPI Serving App
    participant MLF as MetaStore MLflow
    participant S3 as Object Storage MinIO
    
    Note over API: Docker Pod Initialization
    API->>MLF: GET Request Filter runs tag Champion
    MLF-->>API: Active Artifact Run_ID 2bc01dfb003a
    API->>S3: Downloads raw Weights model.pkl
    S3-->>API: Modelo Alocado em RAM viva
    
    App->>API: HTTP POST /predict JSON Payload
    API->>API: Roda Vetor contra Pickler Dinamico
    API-->>App: Traz Previsao Resposta 200 JSON
```

### 4. Observabilidade Estocástica (Self-Healing MLOps)
O Guardiao Definitivo e o propósito Central Operacional de ML Engineers (Fase 8): Garantir que Modelos envelhecam ativamente ou morram ao detectar Model Decay de maneira preemptiva. 

- Fluxo Lógico: A DAG 04 cronjob weekly roda silenciosamente pelo EvidentlyAI. Recorta as Geracoes Passadas Ouro (Ano 2000 Base) da Janela Recente do Lake Geracao Nova Corrompida (2026). As métricas Kolmogorov-Smirnov cruzam as matrizes e verificam desvios de P-value superior a 0.05. Se anomalias explodem na marca de 50 porcento, a Matemática dispara True de Regressão. A DAG 04 lanca um Branch Booleano e desvia o fluxo pra Acionar o Gatilho Direto de Auto-Cura. O Airflow Roda Retreinando a Placa Neural na Base Modificada automaticamente.
- Norte Estratégico: Governanca Imutável. A Matéria dita o ritmo Evolutivo do software, tirando carga cerebral cara de Cientistas para ficarem rastreando Desempenho. Custos Caem, Performance é Self-Driving.

```mermaid
graph TD
    A[Cron Semanal: DAG 04] --> B[DockerOperator Python: drift_monitor]
    B -->|Bate nos Registros S3 Trusted| C{Isolamento Ingestion_Date}
    C -->|Legado Baseline| Ref(Amostra Historica de Referencia)
    C -->|Cargas Mutantes Atuais| Cur(Amostra Fresca Atual S3)
    Ref --> EV[EvidentlyAI Machine: KS Test]
    Cur --> EV
    EV -->|Overlaps Distribution P-Value| D{Dataset Concept Drift Matrix}
    D -- Sim Limiar True --> X[Python XCom PUSH: DRIFT_DETECTED TRUE]
    D -- Nao Limiar False --> Y[Python XCom PUSH: DRIFT_DETECTED FALSE]
    
    X --> PBO[AI BranchPythonOperator Routing]
    Y --> PBO
    PBO -- Condition Boolean TRUE --> Train[TriggerDagRun Call API: DAG 02 Model_Trainer]
    PBO -- Condition Boolean FALSE --> End[EmptyNode Finaliza Esteira em Paz]
```
