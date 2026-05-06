"""Launcher local para a API FastAPI do Alfred Financas."""

import uvicorn


def main() -> None:
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()

