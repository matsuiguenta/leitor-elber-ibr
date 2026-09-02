# 🌡️ Leitor Elber IBR

Aplicação interativa em **Streamlit** e gerador de relatórios executivos em **PDF** para análise e monitoramento de temperatura a partir de arquivos `.IBR` exportados por controladoras de temperatura **Elber**.

---

## 🚀 Funcionalidades Principais

- **Parser Robusto de Arquivos `.IBR`**:
  - Decodificação de payload HEX e verificação de checksum por linha.
  - Extração automática de metadados em JSON (ID da controladora, número de série, SetPoint, Histerese, sensores, etc.).
  - Tratamento inteligente de *timestamps* anômalos (registros com anos espúrios são isolados sem perda de integridade nos demais dados).
  - Interpretação de leituras dos sensores (T1 e T2), tensão da bateria e estados operacionais (Rede Elétrica, Porta, Alarme e Compressor).

- **Painel Interativo Streamlit**:
  - Visualização de métricas de resumo (médias, mínimas, máximas e contagens).
  - **Filtro de Período**: Seleção flexível de intervalo de data e hora — filtra métricas, gráfico, registros e relatório PDF simultaneamente.
  - **Gráfico Interativo com Recorte por Seleção**: Clique e arraste sobre o gráfico para marcar um intervalo de tempo; um botão aplica o recorte ao filtro global de período.
  - **Exportação CSV e Excel**: Baixe os dados filtrados diretamente da interface em `.csv` (encoding UTF-8 BOM para Excel BR) ou `.xlsx`.
  - **Tabela de Registros**: Exibição clara e paginada dos dados brutos e traduzidos.

- **Detecção Avançada de Outliers e Anomalias**:
  - Configuração dinâmica de limite crítico de temperatura superior (ex.: $> 6,0\text{ °C}$) e inferior.
  - Agrupamento de leituras anômalas consecutivas em **Eventos de Anomalia**.
  - Cálculo automático de início da ocorrência, horário de retorno ao normal, duração formatada (ex.: `2h 15min`), pico de temperatura e total de leituras afetadas.

- **Relatório Profissional em PDF (ReportLab + Matplotlib)**:
  - Cabeçalho executivo com identificação da controladora e metadados do arquivo.
  - **Identificação opcional do local / equipamento**: campos para Unidade, Local/Setor, Equipamento, Responsável Técnico e Cargo.
  - Tabela resumo de estatísticas de temperatura (Mínima, Máxima, Média e Contagem de leituras).
  - Resumo de eventos (Alarme ativo, Porta aberta, Rede elétrica desligada, Compressor ligado).
  - Bloco visual de alerta com tabela detalhada de anomalias detectadas.
  - Gráfico de alta resolução do histórico de temperatura.
  - Opção de customização da quantidade de registros na tabela final do PDF (20, 30, 50, 100 ou todos os registros do período).
  - **Nome do arquivo personalizado**: Inclui o ID da controladora e timestamp de geração (ex: `Relatorio_12345_20260902_174352.pdf`).
  - **Página de assinatura** (opcional): declaração de responsabilidade técnica com linhas para assinatura do responsável e do solicitante.

---

## 📄 Formato do Arquivo `.IBR`

O formato de arquivo `.IBR` utilizado pelas controladoras Elber possui a seguinte estrutura interna:

1. **`##C`**: Marcador de início da seção de configuração.
2. **Bloco de Configuração**: JSON codificado em HEX com checksum de 2 caracteres ao final de cada linha.
3. **`$$`**: Marcador de início dos registros históricos de medição.
4. **Linhas de Registros**: Dados em HEX divididos por `;` no formato:
   `índice;data/hora;T1;T2;Bateria;Rede;Porta;Alarme;Compressor;status` + 2 caracteres de checksum.

---

## 🛠️ Instalação e Execução

### Pré-requisitos
- Python 3.9+ instalado.

### Passos para execução

**No Windows (PowerShell):**
```powershell
# Criar ambiente virtual
py -m venv .venv

# Ativar ambiente virtual
.venv\Scripts\activate

# Instalar dependências
pip install -r requirements.txt

# Executar a aplicação Streamlit
streamlit run app.py
```

**No Linux / macOS:**
```bash
# Criar ambiente virtual
python3 -m venv .venv

# Ativar ambiente virtual
source .venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Executar a aplicação Streamlit
streamlit run app.py
```

Após executar o comando, o navegador abrirá automaticamente no endereço `http://localhost:8501`.

---

## 📦 Instalador Windows

**Versão atual: v1.1.0** — [⬇️ Baixar instalador](https://github.com/matsuiguenta/leitor-elber-ibr/releases/download/v1.1.0/Setup_Leitor_Elber_IBR_v1.1.0.exe) | [Todas as versões](https://github.com/matsuiguenta/leitor-elber-ibr/releases)

Um instalador Windows está disponível que inclui:
- Aplicação Python empacotada com todas as dependências
- Atalho para a área de trabalho (opcional durante instalação)
- Registro de desinstalação pelo Painel de Controle do Windows

### Histórico de versões
| Versão | Data | Mudanças |
|--------|------|----------|
| v1.2.0 | 2026-09-02 | Exportação CSV/Excel; cadastro de local/equipamento no relatório; página de assinatura no PDF |
| v1.1.0 | 2026-09-02 | Recorte interativo no gráfico aplica filtro global; reordenação das seções da UI; seleção de brush sem panning |
| v1.0.0 | 2026-09-01 | Versão inicial com parser IBR, detecção de anomalias e gerador de PDF |

---

## 📂 Estrutura do Projeto

```text
leitor_elber_ibr/
├── app.py              # Interface web Streamlit e controles do dashboard
├── parser_ibr.py       # Parser de arquivos .IBR e motor de detecção de anomalias
├── report.py           # Gerador de relatórios em PDF com ReportLab e gráficos Matplotlib
├── exemplo_T.IBR       # Arquivo de exemplo para testes
├── requirements.txt    # Dependências do projeto (streamlit, pandas, matplotlib, reportlab)
└── README.md           # Documentação do projeto

arquivos/
├── inno-setup/         # Scripts e configuração do instalador Windows
│   ├── leitor_elber_setup.iss    # Script Inno Setup
│   ├── leitor_elber.spec         # Configuração PyInstaller
│   └── Output/
│       └── Setup_Leitor_Elber_IBR_v1.1.0.exe  # Instalador Windows
└── exemplo_T.IBR       # Arquivo de exemplo adicional
```

---

## 📋 Próximas Melhorias Planejadas

- [x] Seleção e filtragem por período do relatório.
- [x] Detecção de eventos com duração (anomalias de temperatura e alarmes).
- [x] Identificação de temperaturas fora da faixa por evento/duração.
- [x] Filtros interativos para dashboard e gráfico.
- [x] Personalização de registros na tabela do PDF.
- [x] Nome do arquivo do relatório com ID da controladora e data de geração.
- [x] Recorte interativo por seleção direta no gráfico (brush selection) aplicado ao filtro global.
- [x] Exportação dos dados filtrados para Excel/CSV.
- [x] Cadastro de unidade/local/equipamento no relatório PDF.
- [x] Relatório com página de assinatura do responsável técnico.
- [ ] Leitura e agregação em lote de múltiplos arquivos `.IBR`.


---

Desenvolvido com ❤ por Rogério Matsui Guenta e Inteligência Artificial
