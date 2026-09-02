import importlib
import io
import streamlit as st
import pandas as pd
import altair as alt

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

            def_start_date = st.session_state.get("sel_start_date", min_dt.date())
            def_start_time = st.session_state.get("sel_start_time", min_dt.time())
            def_end_date   = st.session_state.get("sel_end_date",   max_dt.date())
            def_end_time   = st.session_state.get("sel_end_time",   max_dt.time())

            def_start_date = max(min(def_start_date, max_dt.date()), min_dt.date())
            def_end_date   = max(min(def_end_date,   max_dt.date()), min_dt.date())

            mask = (df_full["data_hora"] >= pd.Timestamp.combine(def_start_date, def_start_time)) & \
                   (df_full["data_hora"] <= pd.Timestamp.combine(def_end_date, def_end_time))
            df = df_full[mask].copy()
        else:
            df = df_full.copy()

        if df.empty:
            st.warning("⚠️ Nenhum registro encontrado para o período selecionado. Por favor, escolha um intervalo válido.")
        else:
            # ── 1. Métricas ────────────────────────────────────────────────────
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Registros Exibidos", f"{len(df):,} / {len(df_full):,}".replace(",", "."))
            c2.metric("T1 média",  f"{df['T1'].mean():.1f} °C" if not df['T1'].isnull().all() else "-")
            c3.metric("T1 mínima", f"{df['T1'].min():.1f} °C"  if not df['T1'].isnull().all() else "-")
            c4.metric("T1 máxima", f"{df['T1'].max():.1f} °C"  if not df['T1'].isnull().all() else "-")

            # ── 2. Filtro de Período ───────────────────────────────────────────
            with st.expander("📅 **Filtrar por Período / Intervalo de Data e Hora**", expanded=True):
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    start_date = st.date_input("Data inicial", value=def_start_date, min_value=min_dt.date(), max_value=max_dt.date(), key="w_start_date")
                    start_time = st.time_input("Hora inicial", value=def_start_time, key="w_start_time")
                with col_f2:
                    end_date = st.date_input("Data final", value=def_end_date, min_value=min_dt.date(), max_value=max_dt.date(), key="w_end_date")
                    end_time = st.time_input("Hora final", value=def_end_time, key="w_end_time")

                start_datetime = pd.Timestamp.combine(start_date, start_time)
                end_datetime   = pd.Timestamp.combine(end_date, end_time)

                if start_datetime > end_datetime:
                    st.error("⚠️ A data/hora inicial não pode ser posterior à data/hora final.")
                    df = df_full.copy()
                else:
                    mask = (df_full["data_hora"] >= start_datetime) & (df_full["data_hora"] <= end_datetime)
                    df = df_full[mask].copy()

            # ── 3. Gráfico de Temperaturas ─────────────────────────────────────
            st.subheader("📊 Gráfico de Temperaturas")
            st.caption("💡 **Recorte interativo:** Clique e arraste sobre o gráfico para marcar um intervalo e clique em **Aplicar recorte** para filtrar todos os dados.")

            chart_prep = df.dropna(subset=["data_hora"]).copy()
            df_chart_long = chart_prep.melt(
                id_vars=["data_hora"],
                value_vars=["T1", "T2"],
                var_name="Sensor_Code",
                value_name="Temperatura"
            )
            df_chart_long["Sensor"] = df_chart_long["Sensor_Code"].map({"T1": "Sensor 1 (°C)", "T2": "Sensor 2 (°C)"})

            brush = alt.selection_interval(encodings=["x"], name="brush_select")
            chart_obj = (
                alt.Chart(df_chart_long)
                .mark_line(size=2)
                .encode(
                    x=alt.X("data_hora:T", title="Data / Hora"),
                    y=alt.Y("Temperatura:Q", title="Temperatura (°C)", scale=alt.Scale(zero=False)),
                    color=alt.Color("Sensor:N", title="Sensor", scale=alt.Scale(range=["#1f77b4", "#ff7f0e"])),
                    tooltip=[
                        alt.Tooltip("data_hora:T", title="Data/Hora", format="%d/%m/%Y %H:%M:%S"),
                        alt.Tooltip("Sensor:N", title="Sensor"),
                        alt.Tooltip("Temperatura:Q", title="Temperatura (°C)", format=".1f")
                    ]
                )
                .add_params(brush)
                .properties(height=380)
            )
            chart_event = st.altair_chart(chart_obj, use_container_width=True, on_select="rerun")

            if chart_event and hasattr(chart_event, "selection") and "brush_select" in chart_event.selection:
                selected_bounds = chart_event.selection["brush_select"]
                if "data_hora" in selected_bounds and len(selected_bounds["data_hora"]) == 2:
                    raw_start, raw_end = selected_bounds["data_hora"]
                    if isinstance(raw_start, (int, float)):
                        sel_start_dt = pd.to_datetime(raw_start, unit="ms")
                        sel_end_dt   = pd.to_datetime(raw_end,   unit="ms")
                    else:
                        sel_start_dt = pd.to_datetime(raw_start)
                        sel_end_dt   = pd.to_datetime(raw_end)

                    st.info(
                        f"📍 **Recorte selecionado:** De **{sel_start_dt.strftime('%d/%m/%Y %H:%M:%S')}** "
                        f"até **{sel_end_dt.strftime('%d/%m/%Y %H:%M:%S')}**  —  "
                        f"Clique em **Aplicar recorte** para filtrar registros, métricas e relatório."
                    )
                    col_b1, col_b2 = st.columns([1, 1])
                    with col_b1:
                        if st.button("🎯 Aplicar recorte ao período global", type="primary", use_container_width=True):
                            st.session_state["sel_start_date"] = sel_start_dt.date()
                            st.session_state["sel_start_time"] = sel_start_dt.time()
                            st.session_state["sel_end_date"]   = sel_end_dt.date()
                            st.session_state["sel_end_time"]   = sel_end_dt.time()
                            for _k in ["w_start_date", "w_start_time", "w_end_date", "w_end_time"]:
                                st.session_state.pop(_k, None)
                            st.rerun()
                    with col_b2:
                        if st.button("🔄 Resetar para o período completo", use_container_width=True):
                            for _k in ["sel_start_date", "sel_start_time", "sel_end_date", "sel_end_time",
                                       "w_start_date", "w_start_time", "w_end_date", "w_end_time"]:
                                st.session_state.pop(_k, None)
                            st.rerun()

            # ── 4. Informações da Controladora ────────────────────────────────
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

            # ── 5. Detecção de Anomalias ───────────────────────────────────────
            st.subheader("⚠️ Detecção de Outliers e Anomalias")
            high_limit = st.number_input(
                "🌡️ Considerar anomalia se a temperatura do Sensor 1 for superior a (°C):",
                value=6.0, step=0.5,
                help="Valores como 5.1 °C são tratados como oscilação normal. Defina 6.0 °C ou superior para detectar discrepâncias graves."
            )
            anomalies = detect_anomalies(df, meta, high_temp_limit=high_limit)
            if not anomalies:
                st.success(f"✅ Nenhuma anomalia de temperatura (> {high_limit:.1f} °C) ou alarme foi detectada no período selecionado.")
            else:
                st.error(f"🚨 **Atenção:** Foram encontradas **{len(anomalies)}** ocorrência(s) de anomalia / outlier no período (> {high_limit:.1f} °C ou Alarme ativo)!")
                anom_data = []
                for a in anomalies:
                    ini_str  = a["inicio"].strftime("%d/%m/%Y %H:%M:%S")
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

            # ── 6. Tabela de Registros + Exportação ───────────────────────────
            st.subheader("Registros")
            display_cols = [
                "registro", "data_hora", "T1", "T2", "Bateria",
                "Rede_texto", "Porta_texto", "Alarme_texto", "Compressor_texto"
            ]
            rename_map = {
                "registro": "Registro", "data_hora": "Data/Hora",
                "T1": "T1 °C", "T2": "T2 °C", "Bateria": "Bateria V",
                "Rede_texto": "Rede", "Porta_texto": "Porta",
                "Alarme_texto": "Alarme", "Compressor_texto": "Compressor"
            }
            df_display = df[display_cols].rename(columns=rename_map)
            st.dataframe(df_display, hide_index=True, use_container_width=True, height=450)

            # Exportação CSV / Excel
            st.markdown("**⬇️ Exportar dados filtrados:**")
            exp_col1, exp_col2 = st.columns([1, 1])

            with exp_col1:
                csv_bytes = df_display.to_csv(index=False, sep=";", encoding="utf-8-sig").encode("utf-8-sig")
                controller_id = meta.get("id", "sem_id").replace("/", "-").replace("\\", "-")
                gen_ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
                st.download_button(
                    "📊 Baixar CSV",
                    data=csv_bytes,
                    file_name=f"Registros_{controller_id}_{gen_ts}.csv",
                    mime="text/csv",
                    use_container_width=True
                )

            with exp_col2:
                xlsx_buf = io.BytesIO()
                with pd.ExcelWriter(xlsx_buf, engine="openpyxl") as writer:
                    df_display.to_excel(writer, index=False, sheet_name="Registros")
                xlsx_buf.seek(0)
                st.download_button(
                    "📗 Baixar Excel (.xlsx)",
                    data=xlsx_buf.getvalue(),
                    file_name=f"Registros_{controller_id}_{gen_ts}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

            # ── 7. Identificação do Local / Equipamento ────────────────────────
            st.divider()
            st.subheader("📄 Gerar Relatório PDF")

            with st.expander("🏢 **Identificação do local e equipamento (opcional)**", expanded=False):
                ri_col1, ri_col2 = st.columns(2)
                with ri_col1:
                    ri_unidade    = st.text_input("Unidade / Empresa",    value=st.session_state.get("ri_unidade", ""),    key="ri_unidade",    placeholder="Ex.: Frigorífico Norte Ltda")
                    ri_local      = st.text_input("Local / Setor",        value=st.session_state.get("ri_local", ""),      key="ri_local",      placeholder="Ex.: Câmara Fria 02")
                    ri_equip      = st.text_input("Equipamento",          value=st.session_state.get("ri_equip", ""),      key="ri_equip",      placeholder="Ex.: Controladora Elber #12")
                with ri_col2:
                    ri_resp       = st.text_input("Responsável Técnico",  value=st.session_state.get("ri_resp", ""),       key="ri_resp",       placeholder="Ex.: João da Silva")
                    ri_cargo      = st.text_input("Cargo / Registro",     value=st.session_state.get("ri_cargo", ""),      key="ri_cargo",      placeholder="Ex.: Técnico em Refrigeração")
                    ri_assinatura = st.checkbox(
                        "📝 Incluir página de assinatura no relatório",
                        value=st.session_state.get("ri_assinatura", False),
                        key="ri_assinatura",
                        help="Adiciona uma página ao final do PDF com campos para assinatura do responsável técnico e do solicitante."
                    )

            report_info = {
                "unidade":           ri_unidade,
                "local":             ri_local,
                "equipamento":       ri_equip,
                "responsavel":       ri_resp,
                "cargo":             ri_cargo,
                "incluir_assinatura": ri_assinatura,
            }

            # ── 8. Configurações e download do PDF ─────────────────────────────
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
                pdf = build_pdf(
                    ibr, uploaded.name,
                    df_filtered=df,
                    max_records=max_rec,
                    high_temp_limit=high_limit,
                    report_info=report_info
                )
                pdf_controller_id = meta.get("id", "sem_id").replace("/", "-").replace("\\", "-")
                pdf_gen_date = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
                st.download_button(
                    "📄 Gerar / baixar relatório PDF",
                    data=pdf,
                    file_name=f"Relatorio_{pdf_controller_id}_{pdf_gen_date}.pdf",
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