# 🚀 Self-Healing MLOps Platform (End-to-End)

Uma plataforma de Machine Learning Operations de nível corporativo, projetada em arquitetura de microsserviços, 100% conteinerizada (Docker), orientada a Data Contracts (YAML) e blindada por sistemas de Auto-Cura (Self-Healing) contra Data/Concept Drift.

---

## 🛠️ Como Iniciar a Aplicação (Bootstrapping)

A arquitetura foi inteiramente orquestrada via **Docker Compose** nativo em Linux. Para subir o laboratório isolado na sua máquina sem instalar nenhuma dependência sistêmica fora do Docker Engine:

1. Clone o repositório e navegue até o diretório da Pipeline:
```bash
git clone https://github.com/engfelipeviana/machine_Learning_pipeline.git
cd machine_Learning_pipeline
```

2. Inicialize a Nuvem da Infraestrutura e Build workers isolados:
```bash
# Sobe os containers de rede raiz, bancos (PostgreSQL, MinIO), Plataformas (Airflow, MLflow) e APIs (FastAPI)
docker compose up -d

# Builda localmente as Imagens Master para os Workers Analíticos e de Computação do Airflow
docker compose build builder-data-worker
docker compose build builder-mlops-worker
```

3. Acesse os *Endpoints* Essenciais via localhost:
- **Apache Airflow (Orquestrador UI):** [http://localhost:8088](http://localhost:8088) *(admin / admin)*
- **MinIO S3 (Data Lake Console):** [http://localhost:9001](http://localhost:9001) *(minioadmin / minioadmin)*
- **MLflow (Model Registry):** [http://localhost:5000](http://localhost:5000)
- **FastAPI (Inference Swagger UI):** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Trino / JupyterLab:** [http://localhost:8888](http://localhost:8888)

---

## 🏛️ Arquitetura Macro da Solução

O ecossistema divide-se em Ingestão Medallion, Orquestração Docker-in-Docker (DinD), Registro Científico Controlado e Consumo API de Baixa Latência. A Máquina Airflow lidera a auto-manutenção da Inteligência Artificial.

```mermaid
graph TD
    %% Nós Externos e UI
    User([Engenheiro/Analista]) --> Airflow
    Client([Aplicações Web Mobile]) --> FastAPI

    %% Data Lakehouse
    subgraph S3 MinIO Data Lake
        LZ[(Landing Zone)]
        Raw[(Raw Zone)]
        Trusted[(Trusted Iceberg)]
    end

    %% Airflow Orchestration
    subgraph Computação Cron
        DAG1[DAG 01: ELT Medallion]
        DAG2[DAG 02: Model Trainer]
        DAG4[DAG 04: Drift Monitor]
    end
    
    %% Compute Workers (Docker-in-Docker)
    subgraph Docker Workers Socket Isolado
        DW[Data Eng Worker Pandas]
        MW[MLOps Worker Scikit/Evidently]
    end

    %% Model Lifecycle
    MLF[(MLflow Model Registry)]
    
    %% Connections / Eventos de Rotas
    DAG1 --> DW
    DW --> LZ
    DW --> Raw
    DW -->|ingestion_date Append| Trusted
    
    DAG2 --> MW
    MW --> |Baixa Contrato YAML + Trusted Matriz| Trusted
    MW --> |Registra versão Champions| MLF
    
    DAG4 --> MW
    MW --> |Comrpara Timeline via Estatística KS| Trusted
    MW -- Trigger MLOps (XCom TRUE) --> DAG2
    
    MLF -. FastAPI Puxa RAM do S3 .-> FastAPI
```

---

## 🧩 Componentes da Arquitetura em Detalhes

### 1. Data Engineering (Pipeline ELT Medallion)
A ingestão de dados atua sobre o modelo de camadas lógicas (Medallion Architecture) persistindo DataFrames físicos no S3, rastreados matematicamente via Particionamento Temporal.

- **Fluxo Lógico:** O arquivo sujo de eventos chega na `Landing Zone` cru. A Airflow (DAG 01) invoca um container Docker puro (*Data Worker*) que higieniza e converte o dado para Parquet (`Raw Zone`). No último salto, uma coluna sistêmica temporal `ingestion_date` é aplicada e o Delta/Data Append é soldado sobre os arquivos legados da camada central `Trusted Zone`.
- **Norte Estratégico:** Fornecer massas de dados governadas limpas pro time de Dados rodar Feature Engineering e Consultas ANSI SQL Pesadas sem sobrecarregar Bancos Transacionais, entregando aos Cientistas de MLOps blocos padronizados de Inteligência Artificial.

```mermaid
sequenceDiagram
    participant S31 as S3/Landing
    participant AW as Airflow (DockerOperator)
    participant DW as Python Data Worker
    participant S33 as S3/Trusted
    
    AW->>DW: Aciona Sub-rotina DAG 01
    DW->>S31: Lê arquivo cru CSV
    DW->>DW: Higieniza Tipagem + Remove Outliers Dtype
    DW->>DW: Feature Timestamp: ingestion_date = datetime.now()
    DW->>S33: Resgata Cargas Históricas Particionadas
    DW->>DW: pd.Concat(Old_Data + New_Events)
    DW->>S33: Sobrescreve Iceberg Parquet (Append Virtual Formado)
```

### 2. Contract-Driven ML Training (Orquestração DinD)
A pipeline defende e erradica o risco de Código Rígido do Cientista rodando local em laboratório. Todo o Treino é abstraído por Variáveis em um Arquivo passivo Genérico. Todo Treino roda em ambientes sub-virtuais isolados e que sofrem Auto-Destruição assim que finalizados.

- **Fluxo Lógico:** A Airflow (DAG 02) lê por S3fs o arquivo `penguins_contract.yaml`. O processo chama um *Socket do Docker da Máquina Servidora (DinD)* pedindo pra levantar temporariamente a imagem Ubuntu `worker-mlops`. Variáveis do Contrato (Features Categórica, Caminhos) são enjetadas nas ENVs. Ele treina o Modelo Scikit Pipeline robusto local e aciona client nativo do MLflow. O binário `.pkl` sobe criptografado ao repositório unificado.
- **Norte Estratégico:** Viabilizar escalabilidade. Ambientes Orquestradores Limpos. Pra testar Redes Neurais vs XGBoost num modelo novo, muda-se o contrato YAML de `60 linhas` sem ter que refatorar os Pythons base.

```mermaid
graph LR
    YAML[penguins_contract.yaml S3] -->|Airflow Parser| DIND[DockerOperator Socket]
    DIND -->|Spawn Isolate Session| MWO[Ubuntu worker-mlops]
    MWO -->|Fetches Train Slice| Data[(Trusted Delta Sets)]
    MWO -->|Scikit-Learn Model.Fit()| Artifact[(Cerebro Pickle_Binary)]
    Artifact --> MLflow[Logger MLflow Tracking API]
    MLflow --> S3Bucket[(MLflow Artifacts Store)]
```

### 3. Model Serving (FastAPI Real Time)
A fronteira da MLOps não termina onde o Treino acaba, mas como ele é Exposto como Produto Global pro Ecossistema.
- **Fluxo Lógico:** Um Servidor ASGI `FastAPI` inicia atrelando a um evento raiz `Lifespan`. Imediatamente, ele acessa o Banco Log SQL Postgre do MLflow por API para caçar via string Tag "Qual é a versão atual marcada como @Champion do Time?". Após deduzir o Hash Key dele próprio, o Endpoiny baixa o Parquet das lógicas treináveis (Features Scale rules) pra dentro da Memória RAM da máquina App. Os Routes abrem as postas.
- **Norte Estratégico:** Entrega com Latência Baixa HTTP JSON ao Frontend/Mobiles/VueJS e tolerância a quedas via Inversão Computacional de Despacho (O Cérebro S3 preenche o Modelo Local Instantaneamente na inicialização do serviço Cloud).

```mermaid
sequenceDiagram
    participant App as FrontEnd (App Mobile/React)
    participant API as FastAPI Serving App
    participant MLF as MetaStore MLflow
    participant S3 as Object Storage MinIO
    
    Note over API: Docker Pod Initialization
    API->>MLF: GET Request: Filter runs matching tag=@Champion
    MLF-->>API: Active Artifact Run_ID = 2bc01dfb003a
    API->>S3: Downloads raw Weights (SKlearn model.pkl)
    S3-->>API: Modelo Alocado em RAM viva
    
    App->>API: HTTP POST /predict (Pinguin JSON Payload)
    API->>API: Roda Vetor contra Pickler Dinâmico
    API-->>App: Traz Previsão Resposta 200 JSON
```

### 4. Observabilidade Estocástica (Self-Healing MLOps)
O Guardião Definitivo e o propósito Central Operacional de ML Engineers (A Fama da Fase 8): Garantir que Modelos envelheçam ativamente ou morram ao detectar Model Decay de maneira preemptiva. 

- **Fluxo Lógico:** A Airflow (DAG 04 cronjob @weekly) roda silenciosamente pelo evidentemente (`EvidentlyAI`). Recortando magicamente as "Geracoes Passadas Ouro (Ano 2000 Base)" da Janela Recente do Lake "Geração Nova Corrompida (2026)".
As métricas Kolmogorov-Smirnov/Wasserstein cruzam as matrizes e verificam desvios de *P-value>0.05*. Se simétrica ou anomalias explodem à marca de 50%, a Matemática dispara True de Regressão. A DAG 04 lança um Branch Booleano desviando o fluxo do *end_monitor* pra Acionar o Gatilho Direto de Auto-Cura. O Airflow desce a API pra Dag 02 e Roda Retreinando a Placa Neural na Base Modificada automaticamente.
- **Norte Estratégico:** Governança Imutável. Ninguém treina modelos pra testes frívolos. É a Matéria ditando o ritmo Evolutivo do software, tirando carga cerebral cara de Cientistas para ficarem rastreando Desempenho. Custos Caem, Performance é Self-Driving.

```mermaid
graph TD
    A[Cron Semanal: DAG 04] --> B[DockerOperator Python: drift_monitor]
    B -->|Bate nos Registros S3 Trusted| C{Isolamento Ingestion_Date}
    C -->|Legado Baseline| Ref(Amostra Histórica de Referência)
    C -->|Cargas Mutantes/Atuais| Cur(Amostra Fresca Atual S3)
    Ref --> EV[EvidentlyAI Machine: KS Test]
    Cur --> EV
    EV -->|Overlaps Distribution P-Value| D{Dataset Concept Drift Matrix?}
    D -- Sim > Limiar (True) --> X[Python XCom PUSH: DRIFT_DETECTED: TRUE]
    D -- Não (False Saúde Boa) --> Y[Python XCom PUSH: DRIFT_DETECTED: FALSE]
    
    X --> PBO[AI BranchPythonOperator Routing]
    Y --> PBO
    PBO -- Condition Boolean TRUE --> Train[TriggerDagRun Call API: MLOps_DAG_02_Trainer]
    PBO -- Condition Boolean FALSE --> End[EmptyNode Finaliza Esteira em Paz]
```
