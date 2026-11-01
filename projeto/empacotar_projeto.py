from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

PROJETO = Path.cwd()

ARQUIVO_SAIDA = "GeradorSalasABC_Entrega.zip"

PASTAS_INCLUIDAS = [
    "frontend",
    "backend",
    "etl",
    "dist",
    "modelagem",
]

ARQUIVOS_INCLUIDOS = [
    "app.py",
    "requirements.txt",
    "README.md",
]

with ZipFile(ARQUIVO_SAIDA, "w", ZIP_DEFLATED) as zipf:

    for arquivo in ARQUIVOS_INCLUIDOS:
        caminho = PROJETO / arquivo

        if caminho.exists():
            zipf.write(
                caminho,
                caminho.relative_to(PROJETO)
            )

    for pasta in PASTAS_INCLUIDAS:
        raiz = PROJETO / pasta

        if not raiz.exists():
            continue

        for item in raiz.rglob("*"):

            if item.is_file():

                # Ignora cache
                if "__pycache__" in str(item):
                    continue

                # Ignora arquivos temporários
                if item.suffix in (
                    ".pyc",
                    ".pyo",
                    ".log",
                ):
                    continue

                zipf.write(
                    item,
                    item.relative_to(PROJETO)
                )

print(f"ZIP gerado: {ARQUIVO_SAIDA}")