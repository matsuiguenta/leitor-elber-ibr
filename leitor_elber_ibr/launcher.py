import os
import socket
import sys
import webbrowser
import streamlit.web.cli as stcli


def get_free_port(start_port=8501):
    """Encontra a primeira porta livre a partir de start_port."""
    for port in range(start_port, start_port + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            res = sock.connect_ex(("127.0.0.1", port))
            if res != 0:
                return port
    return start_port


def main():
    if getattr(sys, "frozen", False):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    app_path = os.path.join(base_dir, "app.py")
    port = get_free_port(8501)

    # Configuração de execução do Streamlit
    sys.argv = [
        "streamlit",
        "run",
        app_path,
        "--global.developmentMode=false",
        "--server.headless=true",
        f"--server.port={port}",
    ]

    # Abre o navegador padrão na porta livre encontrada
    webbrowser.open(f"http://localhost:{port}")

    # Executa o Streamlit
    sys.exit(stcli.main())


if __name__ == "__main__":
    main()
