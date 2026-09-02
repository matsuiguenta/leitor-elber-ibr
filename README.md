# 🌡️ Leitor Elber IBR

> Aplicação interativa em **Streamlit** e gerador de relatórios executivos em **PDF** para análise e monitoramento de temperatura a partir de arquivos `.IBR` exportados por controladoras de temperatura **Elber**.

![Versão](https://img.shields.io/badge/versão-v1.1.0-blue?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.9%2B-yellow?style=flat-square&logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.x-red?style=flat-square&logo=streamlit)
![Plataforma](https://img.shields.io/badge/plataforma-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey?style=flat-square)
![Licença](https://img.shields.io/badge/licença-MIT-green?style=flat-square)

---

## 📸 Visão Geral

A aplicação permite importar arquivos `.IBR` das controladoras Elber e:

- **Visualizar** métricas de temperatura (média, mínima, máxima)
- **Filtrar** por qualquer período de data e hora
- **Selecionar** intervalos diretamente no gráfico com recorte interativo (*brush selection*)
- **Detectar** automaticamente anomalias e eventos de temperatura fora da faixa
- **Gerar** relatórios PDF profissionais com gráficos e tabelas de ocorrências

---

## 🚀 Funcionalidades

### 📊 Painel Interativo
- Métricas de resumo atualizadas em tempo real (média, mínima, máxima, contagem)
- **Filtro de Período Global**: filtra métricas, gráfico, registros e PDF simultaneamente
- **Recorte Interativo no Gráfico**: clique e arraste sobre a linha do tempo para selecionar um intervalo e aplicá-lo como filtro global
- Tabela de registros paginada com dados traduzidos
- **Exportação CSV e Excel**: baixe os dados filtrados em `.csv` (compatível com Excel BR) ou `.xlsx`

### 🔍 Detecção de Anomalias
- Limite crítico de temperatura configurável dinamicamente
- Agrupamento de leituras consecutivas em **Eventos** com duração, pico e horário de retorno ao normal
- Detecção de alarmes, porta aberta, falha de rede e compressor ativo

### 📄 Relatório PDF Profissional
- Cabeçalho executivo com metadados da controladora
- **Identificação do local / equipamento**: campos opcionais para Unidade, Setor, Equipamento, Responsável e Cargo
- Gráfico de alta resolução do histórico de temperatura
- Tabela de estatísticas e resumo de eventos operacionais
- Quantidade de registros configurável (20, 30, 50, 100 ou todos)
- Nome de arquivo automático com ID e data de geração
- **Página de assinatura** (opcional): declaração de responsabilidade técnica com linhas para assinatura do responsável e do solicitante

### 🔎 Parser Robusto `.IBR`
- Decodificação de payload HEX com verificação de checksum por linha
- Extração de metadados JSON (ID, nº de série, SetPoint, Histerese)
- Tratamento inteligente de timestamps anômalos sem perda de dados

---

## 📦 Instalador Windows

**[⬇️ Baixar Setup_Leitor_Elber_IBR_v1.1.0.exe](https://github.com/matsuiguenta/leitor-elber-ibr/releases/download/v1.1.0/Setup_Leitor_Elber_IBR_v1.1.0.exe)**

> Todas as versões disponíveis em: [github.com/matsuiguenta/leitor-elber-ibr/releases](https://github.com/matsuiguenta/leitor-elber-ibr/releases)

O instalador inclui:
- Aplicação completa com todas as dependências Python embutidas
- Atalho para a Área de Trabalho (opcional na instalação)
- Desinstalação pelo Painel de Controle do Windows

| Versão | Data | Mudanças |
|--------|------|----------|
| **v1.2.0** | 2026-09-02 | Exportação CSV/Excel; cadastro de local/equipamento no relatório; página de assinatura no PDF |
| v1.1.0 | 2026-09-02 | Recorte interativo no gráfico → filtro global; reordenação da UI; correções de session_state |
| v1.0.0 | 2026-09-01 | Versão inicial: parser IBR, anomalias, PDF |

---

## 🛠️ Execução via Python (sem instalador)

### Pré-requisitos
- Python 3.9 ou superior

```powershell
# Windows (PowerShell)
py -m venv .venv
.venv\Scripts\activate
pip install -r leitor_elber_ibr/requirements.txt
python -m streamlit run leitor_elber_ibr/app.py
```

```bash
# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
pip install -r leitor_elber_ibr/requirements.txt
streamlit run leitor_elber_ibr/app.py
```

Acesse em `http://localhost:8501` após iniciar.

---

## 📄 Formato do Arquivo `.IBR`

```
##C          ← início da seção de configuração
<HEX JSON>   ← metadados codificados em HEX + checksum
$$           ← início dos registros históricos
<idx;ts;T1;T2;Bat;Rede;Porta;Alarme;Comp;status><CS>  ← registros
```

---

## 📂 Estrutura do Repositório

```text
leitor-elber-ibr/
├── leitor_elber_ibr/
│   ├── app.py              # Interface Streamlit
│   ├── parser_ibr.py       # Parser .IBR e detecção de anomalias
│   ├── report.py           # Gerador de relatório PDF
│   ├── launcher.py         # Launcher para executável Windows
│   ├── requirements.txt    # Dependências Python
│   └── README.md           # Documentação técnica detalhada
└── arquivos/
    └── inno-setup/         # Scripts de empacotamento Windows
        ├── leitor_elber_setup.iss
        ├── leitor_elber.spec
        └── Output/
            └── Setup_Leitor_Elber_IBR_v1.1.0.exe
```

---

## 📋 Roadmap

- [x] Parser robusto de arquivos `.IBR` com validação de checksum
- [x] Filtro global de período (data e hora)
- [x] Detecção de anomalias com agrupamento por evento e duração
- [x] Relatório PDF profissional com gráfico e tabelas
- [x] Instalador Windows (PyInstaller + Inno Setup)
- [x] Recorte interativo por seleção no gráfico aplicado ao filtro global
- [ ] Exportação dos dados filtrados para Excel/CSV
- [ ] Cadastro de unidade/local/equipamento no relatório
- [ ] Relatório com campo para assinatura do responsável técnico
- [ ] Leitura em lote de múltiplos arquivos `.IBR`

---

Desenvolvido com ❤ por **Rogério Matsui Guenta** e Inteligência Artificial
