
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import binascii
import json
import pandas as pd


@dataclass
class ElberIBR:
    metadata: dict
    data: pd.DataFrame


def _decode_payload(line: str) -> str:
    """Remove o checksum de 2 caracteres no final e converte HEX -> texto."""
    line = line.strip()
    if not line:
        return ""
    # O formato observado usa 2 caracteres ASCII após o payload HEX.
    payload = line[:-2] if len(line) >= 2 else line
    try:
        return bytes.fromhex(payload).decode("latin-1")
    except (ValueError, UnicodeDecodeError):
        return ""


def read_ibr(source) -> ElberIBR:
    """
    Lê arquivo .IBR da controladora Elber.

    Estrutura observada:
      ##C
      <configuração em HEX + checksum de 2 chars>
      ...
      $$
      <registro em HEX + checksum de 2 chars>
      ...
    """
    if hasattr(source, "read"):
        raw = source.read()
        if isinstance(raw, str):
            raw = raw.encode("latin-1")
    else:
        raw = Path(source).read_bytes()

    text = raw.decode("latin-1", errors="replace")
    lines = [x.strip() for x in text.splitlines()]

    try:
        start = lines.index("##C")
    except ValueError:
        raise ValueError("Arquivo inválido: marcador ##C não encontrado.")

    try:
        sep = lines.index("$$")
    except ValueError:
        raise ValueError("Arquivo inválido: marcador $$ não encontrado.")

    config_text = "".join(_decode_payload(x) for x in lines[start + 1:sep])
    if not config_text:
        raise ValueError("Não foi possível decodificar a configuração do arquivo.")

    # JSON pode ser quebrado em vários blocos; o conteúdo observado forma um único objeto.
    try:
        metadata = json.loads(config_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Configuração JSON inválida: {exc}") from exc

    sensor_map = {s["id"]: s for s in metadata.get("sensors", [])}

    rows = []
    for line_no, line in enumerate(lines[sep + 1:], start=sep + 2):
        decoded = _decode_payload(line)
        if not decoded:
            continue
        fields = decoded.split(";")
        if len(fields) < 10:
            continue

        # Formato observado:
        # índice;data/hora;T1;T2;BAT;RD;P;AL;CP;status
        try:
            row = {
                "registro": int(fields[0]),
                "data_hora": pd.to_datetime(fields[1], errors="coerce"),
                "T1": float(fields[2]),
                "T2": float(fields[3]),
                "Bateria": float(fields[4]),
                "Rede": int(fields[5]),
                "Porta": int(fields[6]),
                "Alarme": int(fields[7]),
                "Compressor": int(fields[8]),
                "status": fields[9],
                "_linha": line_no,
            }
            rows.append(row)
        except (ValueError, TypeError):
            continue

    df = pd.DataFrame(rows)
    if df.empty:
        raise ValueError("Nenhum registro de medição foi encontrado no arquivo.")

    df["data_hora"] = pd.to_datetime(df["data_hora"], errors="coerce")

    # Algumas exportações da controladora podem conter timestamps espúrios
    # (no arquivo de exemplo há cinco registros em 2037 no meio de um histórico de 2026).
    # Mantemos esses registros, mas não os usamos na ordenação/período do relatório.
    valid_years = df["data_hora"].dropna().dt.year
    if not valid_years.empty:
        reference_year = int(valid_years.mode().iloc[0])
        df["data_hora_original"] = df["data_hora"]
        df["data_hora_anomala"] = df["data_hora"].notna() & (df["data_hora"].dt.year != reference_year)
        df.loc[df["data_hora_anomala"], "data_hora"] = pd.NaT
    else:
        df["data_hora_original"] = df["data_hora"]
        df["data_hora_anomala"] = False

    df = df.sort_values(["data_hora", "registro"], na_position="last").reset_index(drop=True)

    # Traduções amigáveis
    df["Rede_texto"] = df["Rede"].map({0: "Desligada", 1: "Ligada"}).fillna("Desconhecida")
    df["Porta_texto"] = df["Porta"].map({0: "Fechada", 1: "Aberta"}).fillna("Desconhecida")
    df["Alarme_texto"] = df["Alarme"].map({0: "Normal", 1: "Ativo"}).fillna("Desconhecido")
    df["Compressor_texto"] = df["Compressor"].map({0: "Desligado", 1: "Ligado"}).fillna("Desconhecido")

    return ElberIBR(metadata=metadata, data=df)


def temperature_stats(df: pd.DataFrame, column: str) -> dict:
    s = pd.to_numeric(df[column], errors="coerce").dropna()
    return {
        "mínima": float(s.min()) if len(s) else None,
        "máxima": float(s.max()) if len(s) else None,
        "média": float(s.mean()) if len(s) else None,
        "leituras": int(s.count()),
    }


def event_count(df: pd.DataFrame, column: str) -> int:
    return int((df[column] == 1).sum())


def detect_anomalies(df: pd.DataFrame, metadata: dict, high_temp_limit: float = 6.0, low_temp_limit: float = None) -> list[dict]:
    """
    Detecta e agrupa eventos anômalos significativos (ex. temperatura acima de 6.0 °C ou Alarme ativo).
    Retorna uma lista de dicionários contendo os detalhes de cada evento:
      - tipo: Descrição da anomalia (ex. Temp Alta, Alarme Ativo)
      - inicio: Timestamp de início
      - fim: Timestamp da última leitura anômala
      - retorno_normal: Timestamp da primeira leitura normal após a anomalia (se houver)
      - duracao_str: Duração formatada
      - temp_max: Temperatura máxima no evento
      - temp_min: Temperatura mínima no evento
      - leituras: Quantidade de registros no evento
    """
    valid_df = df.dropna(subset=["data_hora"]).sort_values("data_hora").copy()
    if valid_df.empty:
        return []

    configs = {c.get("name"): c.get("value") for c in metadata.get("configs", [])}
    try:
        setpoint = float(configs.get("SetPoint"))
        histerese = float(configs.get("Histerese", 0))
        calculated_upper = setpoint + histerese
        calculated_lower = setpoint - histerese
    except (TypeError, ValueError):
        calculated_upper = 5.0
        calculated_lower = 2.0

    upper_limit = high_temp_limit if high_temp_limit is not None else max(calculated_upper + 1.0, 6.0)
    lower_limit = low_temp_limit if low_temp_limit is not None else min(calculated_lower, 1.0)

    def is_row_anomalous(row):
        t1 = row["T1"]
        alarm = row["Alarme"] == 1
        high = upper_limit is not None and t1 > upper_limit
        low = lower_limit is not None and t1 < lower_limit
        return high or low or alarm

    anomalies = []
    current_block = []

    for idx, row in valid_df.iterrows():
        if is_row_anomalous(row):
            current_block.append(row)
        else:
            if current_block:
                _add_anomaly_event(anomalies, current_block, row["data_hora"], lower_limit, upper_limit)
                current_block = []

    if current_block:
        _add_anomaly_event(anomalies, current_block, None, lower_limit, upper_limit)

    return anomalies


def _add_anomaly_event(anomalies_list, block, normal_time, lower_limit, upper_limit):
    block_df = pd.DataFrame(block)
    inicio = block_df["data_hora"].min()
    fim = block_df["data_hora"].max()

    fin_calc = normal_time if normal_time is not None else fim
    dur = fin_calc - inicio

    tot_sec = int(dur.total_seconds())
    if tot_sec <= 0:
        dur_str = "1 leitura"
    else:
        hours, remainder = divmod(tot_sec, 3600)
        minutes, seconds = divmod(remainder, 60)
        parts = []
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}min")
        if not parts:
            parts.append(f"{seconds}s")
        dur_str = " ".join(parts)

    t1_max = block_df["T1"].max()
    t1_min = block_df["T1"].min()
    alarm_active = (block_df["Alarme"] == 1).any()

    tipos = []
    if upper_limit is not None and t1_max > upper_limit:
        tipos.append(f"Temperatura Alta ({t1_max:.1f} °C)")
    if lower_limit is not None and t1_min < lower_limit:
        tipos.append(f"Temperatura Baixa ({t1_min:.1f} °C)")
    if alarm_active:
        tipos.append("Alarme Ativo")

    tipo_str = " | ".join(tipos) if tipos else "Anomalia de Temperatura"

    anomalies_list.append({
        "tipo": tipo_str,
        "inicio": inicio,
        "fim": fim,
        "retorno_normal": normal_time,
        "duracao_str": dur_str,
        "temp_max": t1_max,
        "temp_min": t1_min,
        "leituras": len(block_df),
        "alarm_active": alarm_active,
    })
