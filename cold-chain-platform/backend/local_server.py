import os
from pathlib import Path

import uvicorn

from app.core.db import Base, engine
from app.main import app
from app.seed import main as seed_main
from app.models import *  # noqa: F403


def bootstrap() -> None:
    Base.metadata.create_all(bind=engine)
    seed_main([])


if __name__ == "__main__":
    data_dir = Path(os.environ.get("COLD_CHAIN_DATA_DIR", ".")).resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    os.chdir(data_dir)
    bootstrap()
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
