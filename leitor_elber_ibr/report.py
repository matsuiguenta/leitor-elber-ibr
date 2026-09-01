
from __future__ import annotations

from io import BytesIO
from pathlib import Path
import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, KeepTogether
)

from parser_ibr import temperature_stats, event_count, detect_anomalies


def _fmt(v, decimals=1):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "-"
    return f"{v:.{decimals}f}"


def _make_chart(df: pd.DataFrame) -> BytesIO:
    plot_df = df.dropna(subset=["data_hora"]).copy()
    fig, ax = plt.subplots(figsize=(10.8, 4.0))
    ax.plot(plot_df["data_hora"], plot_df["T1"], label="Sensor 1")
    ax.plot(plot_df["data_hora"], plot_df["T2"], label="Sensor 2")
    ax.set_title("Histórico de temperatura")
    ax.set_xlabel("Data/hora")
    ax.set_ylabel("Temperatura (°C)")
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.autofmt_xdate()
    fig.tight_layout()

    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=160, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


def build_pdf(ibr, filename="Relatorio_Elber.pdf", df_filtered=None, max_records=30, high_temp_limit=6.0) -> bytes:
    df = df_filtered if df_filtered is not None else ibr.data
    meta = ibr.metadata

    out = BytesIO()
    doc = SimpleDocTemplate(
        out, pagesize=A4,
        rightMargin=14*mm, leftMargin=14*mm,
        topMargin=14*mm, bottomMargin=14*mm,
        title="Relatório de Temperatura - Elber",
        author="Leitor Elber IBR",
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="TitleCenter", parent=styles["Title"], alignment=TA_CENTER,
        fontSize=18, leading=22, spaceAfter=8
    ))
    styles.add(ParagraphStyle(
        name="Small", parent=styles["Normal"], fontSize=8, leading=10
    ))
    styles.add(ParagraphStyle(
        name="Section", parent=styles["Heading2"], fontSize=12,
        leading=15, spaceBefore=8, spaceAfter=6
    ))

    story = []
    story.append(Paragraph("RELATÓRIO DE MONITORAMENTO DE TEMPERATURA", styles["TitleCenter"]))
    story.append(Paragraph("Controladora Elber — arquivo de histórico .IBR", styles["Normal"]))
    story.append(Spacer(1, 5*mm))

    serial = meta.get("serial", "-")
    device_id = meta.get("id", "-")
    configs = {c.get("name"): c.get("value") for c in meta.get("configs", [])}

    valid_dates = df["data_hora"].dropna()
    start_str = valid_dates.min().strftime("%d/%m/%Y %H:%M:%S") if not valid_dates.empty else "-"
    end_str = valid_dates.max().strftime("%d/%m/%Y %H:%M:%S") if not valid_dates.empty else "-"

    info = [
        ["Arquivo", Path(filename).name],
        ["ID da controladora", str(device_id)],
        ["Número de série", str(serial)],
        ["Período inicial", start_str],
        ["Período final", end_str],
        ["Total de registros", f"{len(df):,}".replace(",", ".")],
        ["Setpoint", f"{configs.get('SetPoint', '-')} °C"],
        ["Histerese", f"{configs.get('Histerese', '-')} °C"],
    ]
    t = Table(info, colWidths=[45*mm, 135*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (0,-1), colors.lightgrey),
        ("GRID", (0,0), (-1,-1), 0.4, colors.grey),
        ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 8.5),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 5),
        ("RIGHTPADDING", (0,0), (-1,-1), 5),
    ]))
    story.append(t)

    story.append(Paragraph("Resumo das temperaturas", styles["Section"]))
    s1 = temperature_stats(df, "T1")
    s2 = temperature_stats(df, "T2")
    summary = [
        ["Indicador", "Sensor 1 (°C)", "Sensor 2 (°C)"],
        ["Mínima", _fmt(s1["mínima"]), _fmt(s2["mínima"])],
        ["Máxima", _fmt(s1["máxima"]), _fmt(s2["máxima"])],
        ["Média", _fmt(s1["média"]), _fmt(s2["média"])],
        ["Leituras", str(s1["leituras"]), str(s2["leituras"])],
    ]
    t = Table(summary, colWidths=[55*mm, 62*mm, 62*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#e6e6e6")),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("GRID", (0,0), (-1,-1), 0.4, colors.grey),
        ("ALIGN", (1,1), (-1,-1), "CENTER"),
        ("FONTSIZE", (0,0), (-1,-1), 8.5),
    ]))
    story.append(t)

    story.append(Paragraph("Eventos e estados", styles["Section"]))
    events = [
        ["Evento", "Quantidade de registros", "Interpretação"],
        ["Alarme ativo", str(event_count(df, "Alarme")), "Registros em que o alarme = ON"],
        ["Porta aberta", str(event_count(df, "Porta")), "Registros em que a porta = aberta"],
        ["Rede elétrica OFF", str(int((df["Rede"] == 0).sum())), "Registros sem rede elétrica"],
        ["Compressor ligado", str(event_count(df, "Compressor")), "Registros com compressor = ON"],
    ]
    t = Table(events, colWidths=[48*mm, 42*mm, 89*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#e6e6e6")),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("GRID", (0,0), (-1,-1), 0.4, colors.grey),
        ("FONTSIZE", (0,0), (-1,-1), 8.2),
    ]))
    story.append(t)

    # Bloco de Alerta / Detecção de Outliers e Anomalias
    anomalies = detect_anomalies(df, meta, high_temp_limit=high_temp_limit)
    story.append(Paragraph("Detecção de Outliers e Anomalias", styles["Section"]))

    if not anomalies:
        ok_style = ParagraphStyle(
            name="OkBox", parent=styles["Normal"],
            fontSize=8.5, leading=11, textColor=colors.HexColor("#065f46"),
            backColor=colors.HexColor("#d1fae5"), borderColor=colors.HexColor("#10b981"),
            borderWidth=1, borderPadding=6, spaceAfter=6
        )
        story.append(Paragraph(f"✅ Nenhuma anomalia de temperatura (> {high_temp_limit:.1f} °C) ou alarme foi detectada no período analisado.", ok_style))
    else:
        alert_summary_style = ParagraphStyle(
            name="AlertSummary", parent=styles["Normal"],
            fontSize=8.5, leading=11, textColor=colors.HexColor("#991b1b"),
            backColor=colors.HexColor("#fee2e2"), borderColor=colors.HexColor("#ef4444"),
            borderWidth=1, borderPadding=6, spaceAfter=6
        )
        story.append(Paragraph(
            f"<b>⚠️ ALERTA:</b> Foram identificadas {len(anomalies)} ocorrência(s) de anomalia / outlier no período "
            f"(considerando temperatura > {high_temp_limit:.1f} °C ou Alarme Ativo). "
            "Abaixo estão detalhados os horários em que a anomalia iniciou, quando retornou ao normal e a duração do evento:",
            alert_summary_style
        ))

        display_anomalies = anomalies[:20]
        anom_rows = [["Início da Anomalia", "Retorno ao Normal", "Duração", "Detalhes / Tipo", "Status"]]
        for a in display_anomalies:
            ini_str = a["inicio"].strftime("%d/%m/%Y %H:%M:%S")
            norm_str = a["retorno_normal"].strftime("%d/%m/%Y %H:%M:%S") if a["retorno_normal"] is not None else "Em aberto"
            anom_rows.append([
                ini_str,
                norm_str,
                a["duracao_str"],
                a["tipo"],
                "ANOMALIA"
            ])

        t_anom = Table(anom_rows, repeatRows=1, colWidths=[35*mm, 35*mm, 20*mm, 70*mm, 20*mm])
        t_anom.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#991b1b")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("GRID", (0,0), (-1,-1), 0.4, colors.HexColor("#fca5a5")),
            ("FONTSIZE", (0,0), (-1,-1), 7.5),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("ALIGN", (0,0), (2,-1), "CENTER"),
            ("ALIGN", (4,0), (4,-1), "CENTER"),
            ("TEXTCOLOR", (4,1), (4,-1), colors.HexColor("#991b1b")),
            ("FONTNAME", (4,1), (4,-1), "Helvetica-Bold"),
            ("BACKGROUND", (0,1), (-1,-1), colors.HexColor("#fff5f5")),
        ]))
        story.append(t_anom)

        if len(anomalies) > 20:
            story.append(Spacer(1, 2*mm))
            story.append(Paragraph(
                f"<i>Exibindo os primeiros 20 de {len(anomalies)} eventos anômalos identificados no período.</i>",
                styles["Small"]
            ))

    story.append(PageBreak())
    story.append(Paragraph("Gráfico do histórico", styles["Section"]))
    story.append(Image(_make_chart(df), width=180*mm, height=67*mm))

    valid_df = df.dropna(subset=["data_hora"]).copy()
    if max_records is None or str(max_records).lower() in ("todos", "all", "0", "-1"):
        table_df = valid_df
        subtitle = f"Tabela de leituras do período ({len(table_df)} registros)"
    else:
        try:
            limit = int(max_records)
            table_df = valid_df.tail(limit)
            if len(valid_df) > limit:
                subtitle = f"Leituras do período (últimos {len(table_df)} de {len(valid_df)} registros)"
            else:
                subtitle = f"Tabela de leituras do período ({len(table_df)} registros)"
        except (ValueError, TypeError):
            table_df = valid_df
            subtitle = f"Tabela de leituras do período ({len(table_df)} registros)"

    story.append(Paragraph(subtitle, styles["Section"]))
    rows = [["Data/hora", "T1 °C", "T2 °C", "Bateria", "Rede", "Porta", "Alarme", "Compressor"]]
    for _, r in table_df.iterrows():
        rows.append([
            r["data_hora"].strftime("%d/%m/%Y %H:%M:%S"),
            _fmt(r["T1"]), _fmt(r["T2"]), _fmt(r["Bateria"]),
            r["Rede_texto"], r["Porta_texto"], r["Alarme_texto"], r["Compressor_texto"]
        ])
    t = Table(rows, repeatRows=1, colWidths=[33*mm, 15*mm, 15*mm, 17*mm, 19*mm, 19*mm, 20*mm, 25*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#e6e6e6")),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("GRID", (0,0), (-1,-1), 0.3, colors.grey),
        ("FONTSIZE", (0,0), (-1,-1), 6.2),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("ALIGN", (1,1), (-1,-1), "CENTER"),
    ]))
    story.append(t)

    anomalous = int(df.get("data_hora_anomala", pd.Series(dtype=bool)).sum())
    if anomalous:
        story.append(Spacer(1, 3*mm))
        story.append(Paragraph(
            f"Atenção: {anomalous} registro(s) possuem data/hora anômala e foram mantidos nos dados, "
            "mas excluídos do cálculo do período e do gráfico.",
            styles["Small"]
        ))

    story.append(Spacer(1, 5*mm))
    story.append(Paragraph(
        "Observação: este relatório interpreta o formato do arquivo .IBR fornecido. "
        "Os estados Rede, Porta, Alarme e Compressor são apresentados conforme a definição "
        "da própria configuração gravada no arquivo.",
        styles["Small"]
    ))

    def _draw_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#666666"))
        canvas.setStrokeColor(colors.HexColor("#cccccc"))
        canvas.setLineWidth(0.5)
        canvas.line(14 * mm, 10 * mm, (210 - 14) * mm, 10 * mm)
        footer_text = "Desenvolvido com ❤ por Rogério Matsui Guenta e Inteligência Artificial"
        canvas.drawCentredString((210 * mm) / 2, 6 * mm, footer_text)
        canvas.restoreState()

    doc.build(story, onFirstPage=_draw_footer, onLaterPages=_draw_footer)
    return out.getvalue()

