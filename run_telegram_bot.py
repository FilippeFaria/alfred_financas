from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import sys
import os
import threading


ROOT = Path(__file__).resolve().parent
VENV_SITE_PACKAGES = ROOT / ".venv" / "Lib" / "site-packages"


def preparar_path() -> None:
    # Reaproveita os pacotes puros da .venv e preserva pandas/numpy do runtime atual.
    if str(ROOT) not in sys.path:
        sys.path.append(str(ROOT))
    if VENV_SITE_PACKAGES.exists() and str(VENV_SITE_PACKAGES) not in sys.path:
        sys.path.append(str(VENV_SITE_PACKAGES))


class _HealthHandler(BaseHTTPRequestHandler):
    @staticmethod
    def _is_health_path(path: str) -> bool:
        return path in {"/", "/health"}

    def _send_health_response(self, include_body: bool) -> None:
        body = b'{"status":"online"}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if include_body:
            self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - assinatura exigida pelo BaseHTTPRequestHandler
        if self._is_health_path(self.path):
            self._send_health_response(include_body=True)
            return

        self.send_response(404)
        self.end_headers()

    def do_HEAD(self) -> None:  # noqa: N802 - assinatura exigida pelo BaseHTTPRequestHandler
        if self._is_health_path(self.path):
            self._send_health_response(include_body=False)
            return

        self.send_response(404)
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return


def iniciar_servidor_healthcheck() -> None:
    porta = int(os.getenv("PORT", "10000"))
    servidor = ThreadingHTTPServer(("0.0.0.0", porta), _HealthHandler)
    thread = threading.Thread(target=servidor.serve_forever, daemon=True)
    thread.start()
    print(f"[healthcheck] Servidor HTTP ativo em 0.0.0.0:{porta} (rotas: / e /health)")


if __name__ == "__main__":
    preparar_path()
    iniciar_servidor_healthcheck()
    from src.telegram_bot.bot import main

    main()
