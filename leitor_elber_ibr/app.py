
import importlib
import streamlit as st
import pandas as pd

import parser_ibr
import report

importlib.reload(parser_ibr)
importlib.reload(report)

from parser_ibr import read_ibr, detect_anomalies
from report import build_pdf

st.set_page_config(page_title="Leitor Elber IBR", page_icon="🌡️", layout="wide")

st.title("🌡️ Leitor de arquivos Elber (.IBR)")
st.caption("Importe o arquivo de histórico da controladora e gere um relatório em PDF.")

uploaded = st.file_uploader("Selecione o arquivo .IBR", type=["ibr", "IBR"])

if uploaded:
    try:
        ibr = read_ibr(uploaded)
        df_full = ibr.data
        meta = ibr.metadata

        st.success(f"Arquivo lido com sucesso: {len(df_full):,} registros no total.".replace(",", "."))
        anom = int(df_full.get("data_hora_anomala", pd.Series(dtype=bool)).sum())
        if anom:
            st.warning(
                f"{anom} registro(s) possuem data/hora anômala e foram excluídos apenas do período/gráfico; "
                "os demais dados continuam disponíveis."
            )

        valid_dates = df_full["data_hora"].dropna()
        if not valid_dates.empty:
            min_dt = valid_dates.min()
            max_dt = valid_dates.max()

            with st.expander("📅 **Filtrar por Período / Intervalo de Data e Hora**", expanded=True):
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    start_date = st.date_input("Data inicial", value=min_dt.date(), min_value=min_dt.date(), max_value=max_dt.date())
                    start_time = st.time_input("Hora inicial", value=min_dt.time())
                with col_f2:
                    end_date = st.date_input("Data final", value=max_dt.date(), min_value=min_dt.date(), max_value=max_dt.date())
                    end_time = st.time_input("Hora final", value=max_dt.time())

                start_datetime = pd.Timestamp.combine(start_date, start_time)
                end_datetime = pd.Timestamp.combine(end_date, end_time)

                if start_datetime > end_datetime:
                    st.error("⚠️ A data/hora inicial não pode ser posterior à data/hora final.")
                    df = df_full.copy()
                else:
                    mask = (df_full["data_hora"] >= start_datetime) & (df_full["data_hora"] <= end_datetime)
                    df = df_full[mask].copy()
        else:
            df = df_full.copy()

        if df.empty:
            st.warning("⚠️ Nenhum registro encontrado para o período selecionado. Por favor, escolha um intervalo válido.")
        else:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Registros Exibidos", f"{len(df):,} / {len(df_full):,}".replace(",", "."))
            c2.metric("T1 média", f"{df['T1'].mean():.1f} °C" if not df['T1'].isnull().all() else "-")
            c3.metric("T1 mínima", f"{df['T1'].min():.1f} °C" if not df['T1'].isnull().all() else "-")
            c4.metric("T1 máxima", f"{df['T1'].max():.1f} °C" if not df['T1'].isnull().all() else "-")

            st.subheader("Informações da controladora")
            info = pd.DataFrame({
                "Campo": ["ID", "Número de série", "SetPoint", "Histerese", "Início (Filtrado)", "Fim (Filtrado)"],
                "Valor": [
                    meta.get("id", "-"),
                    meta.get("serial", "-"),
                    next((x["value"] + " " + x["unit"] for x in meta.get("configs", []) if x["name"] == "SetPoint"), "-"),
                    next((x["value"] + " " + x["unit"] for x in meta.get("configs", []) if x["name"] == "Histerese"), "-"),
                    df["data_hora"].min().strftime("%d/%m/%Y %H:%M:%S") if not df["data_hora"].dropna().empty else "-",
                    df["data_hora"].max().strftime("%d/%m/%Y %H:%M:%S") if not df["data_hora"].dropna().empty else "-",
                ]
            })
            st.dataframe(info, hide_index=True, use_container_width=True)

            # Bloco de Anomalias / Outliers
            st.subheader("⚠️ Detecção de Outliers e Anomalias")
            high_limit = st.number_input(
                "🌡️ Considerar anomalia se a temperatura do Sensor 1 for superior a (°C):",
                value=6.0,
                step=0.5,
                help="Valores como 5.1 °C são tratados como oscilação normal. Defina 6.0 °C ou superior para detectar discrepâncias graves."
            )

            anomalies = detect_anomalies(df, meta, high_temp_limit=high_limit)
            if not anomalies:
                st.success(f"✅ Nenhuma anomalia de temperatura (> {high_limit:.1f} °C) ou alarme foi detectada no período selecionado.")
            else:
                st.error(f"🚨 **Atenção:** Foram encontradas **{len(anomalies)}** ocorrência(s) de anomalia / outlier no período (> {high_limit:.1f} °C ou Alarme ativo)!")
                anom_data = []
                for a in anomalies:
                    ini_str = a["inicio"].strftime("%d/%m/%Y %H:%M:%S")
                    norm_str = a["retorno_normal"].strftime("%d/%m/%Y %H:%M:%S") if a["retorno_normal"] is not None else "Em aberto"
                    anom_data.append({
                        "Início da Anomalia": ini_str,
                        "Retorno ao Normal": norm_str,
                        "Duração": a["duracao_str"],
                        "Leituras": a["leituras"],
                        "Pico / Detalhes": a["tipo"],
                        "Status": "⚠️ ALERTA"
                    })
                st.dataframe(pd.DataFrame(anom_data), hide_index=True, use_container_width=True)

            st.subheader("📊 Gráfico de Temperaturas")
            with st.expander("📅 **Filtrar período exclusivo para o gráfico**", expanded=True):
                cg1, cg2 = st.columns(2)
                valid_df_dates = df["data_hora"].dropna()
                min_c_dt = valid_df_dates.min() if not valid_df_dates.empty else pd.Timestamp.now()
                max_c_dt = valid_df_dates.max() if not valid_df_dates.empty else pd.Timestamp.now()

                with cg1:
                    c_s_date = st.date_input("Data inicial do gráfico", value=min_c_dt.date(), min_value=min_c_dt.date(), max_value=max_c_dt.date(), key="chart_start_date")
                    c_s_time = st.time_input("Hora inicial do gráfico", value=min_c_dt.time(), key="chart_start_time")
                with cg2:
                    c_e_date = st.date_input("Data final do gráfico", value=max_c_dt.date(), min_value=min_c_dt.date(), max_value=max_c_dt.date(), key="chart_end_date")
                    c_e_time = st.time_input("Hora final do gráfico", value=max_c_dt.time(), key="chart_end_time")

                chart_start_dt = pd.Timestamp.combine(c_s_date, c_s_time)
                chart_end_dt = pd.Timestamp.combine(c_e_date, c_e_time)

                if chart_start_dt > chart_end_dt:
                    st.error("⚠️ Data/Hora inicial do gráfico não pode ser maior que a final.")
                    chart_df = df
                else:
                    chart_mask = (df["data_hora"] >= chart_start_dt) & (df["data_hora"] <= chart_end_dt)
                    chart_df = df[chart_mask].copy()

            if chart_df.empty:
                st.warning("⚠️ Nenhum registro encontrado para o período do gráfico selecionado.")
            else:
                chart = chart_df.set_index("data_hora")[["T1", "T2"]].rename(columns={
                    "T1": "Sensor 1 (°C)", "T2": "Sensor 2 (°C)"
                })
                st.line_chart(chart)

            st.subheader("Registros")
            display_cols = [
                "registro", "data_hora", "T1", "T2", "Bateria",
                "Rede_texto", "Porta_texto", "Alarme_texto", "Compressor_texto"
            ]
            st.dataframe(
                df[display_cols].rename(columns={
                    "registro": "Registro", "data_hora": "Data/Hora",
                    "T1": "T1 °C", "T2": "T2 °C", "Bateria": "Bateria V",
                    "Rede_texto": "Rede", "Porta_texto": "Porta",
                    "Alarme_texto": "Alarme", "Compressor_texto": "Compressor"
                }),
                hide_index=True, use_container_width=True, height=450
            )

            st.divider()
            col_pdf1, col_pdf2 = st.columns([1, 1])
            with col_pdf1:
                pdf_records_opt = st.selectbox(
                    "📋 Quantidade de registros na tabela do PDF:",
                    options=["30 registros (Padrão)", "20 registros", "50 registros", "100 registros", "Todos os registros do período"],
                    index=0
                )

                if pdf_records_opt.startswith("20"):
                    max_rec = 20
                elif pdf_records_opt.startswith("30"):
                    max_rec = 30
                elif pdf_records_opt.startswith("50"):
                    max_rec = 50
                elif pdf_records_opt.startswith("100"):
                    max_rec = 100
                else:
                    max_rec = None

            with col_pdf2:
                st.write("")
                st.write("")
                pdf = build_pdf(ibr, uploaded.name, df_filtered=df, max_records=max_rec, high_temp_limit=high_limit)
                st.download_button(
                    "📄 Gerar / baixar relatório PDF",
                    data=pdf,
                    file_name=f"Relatorio_{uploaded.name.rsplit('.', 1)[0]}.pdf",
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True
                )

    except Exception as exc:
        st.error(f"Não foi possível ler o arquivo: {exc}")
        st.exception(exc)
else:
    st.info("Envie um arquivo .IBR para começar.")

st.divider()
st.caption("Desenvolvido com ❤ por Rogério Matsui Guenta e Inteligência Artificial")

