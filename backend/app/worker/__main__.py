"""Worker de IONDU: procesos periódicos (lectura IMAP, reintentos SRI, alertas).

Por ahora solo mantiene el latido (heartbeat) que usa el healthcheck de Docker.
Maneja SIGTERM/SIGINT para terminar el ciclo en curso antes de salir.
"""

import logging
import signal
import threading
from pathlib import Path

from app.core.config import get_settings

logger = logging.getLogger("iondu.worker")
stop = threading.Event()


def run_cycle() -> None:
    """Un ciclo de trabajo. Se completará en los sprints 2 y 3."""


def main() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stop.set())

    heartbeat = Path(settings.worker_heartbeat_file)
    logger.info("worker iniciado")
    while not stop.is_set():
        try:
            run_cycle()
        except Exception:
            logger.exception("error en el ciclo del worker")
        heartbeat.touch()
        stop.wait(settings.worker_tick_seconds)
    logger.info("worker detenido")


if __name__ == "__main__":
    main()
