from __future__ import annotations

import json
import pathlib
from typing import List, Optional

import typer
from langchain_text_splitters import RecursiveCharacterTextSplitter

from athena_server.config import Settings, make_embeddings
from athena_server.memory.vectorstore import get_vectorstore

app = typer.Typer(help="Athena ingestion CLI: embed documents into PGVector")


@app.command("files")
def ingest_files(
    paths: List[str] = typer.Argument(..., help="Files or directories to ingest"),
    glob: str = typer.Option("**/*", help="Glob applied to directories"),
    chunk_size: int = typer.Option(1200, help="Text splitter chunk size"),
    chunk_overlap: int = typer.Option(150, help="Text splitter overlap"),
    collection: Optional[str] = typer.Option(None, help="Override collection name"),
    dry_run: bool = typer.Option(False, help="Parse and split only; do not write"),
):
    settings = Settings()
    embeddings = make_embeddings(settings)
    vectorstore = get_vectorstore(settings, embeddings, collection_name=collection)

    files: List[pathlib.Path] = []
    for p in paths:
        path = pathlib.Path(p)
        if path.is_dir():
            files.extend([f for f in path.glob(glob) if f.is_file()])
        elif path.is_file():
            files.append(path)
        else:
            typer.echo(f"Skipping missing path: {p}")

    docs = []
    for f in files:
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:  # noqa: BLE001
            typer.echo(f"Failed to read {f}: {e}")
            continue
        splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        for i, chunk in enumerate(splitter.split_text(text)):
            docs.append(
                {
                    "page_content": chunk,
                    "metadata": {"source": str(f), "chunk": i},
                }
            )

    typer.echo(f"Prepared {len(docs)} chunks from {len(files)} file(s)")

    if dry_run:
        sample = json.dumps(docs[:2], ensure_ascii=False) if docs else "[]"
        typer.echo(f"Dry run; first docs: {sample}")
        raise typer.Exit(code=0)

    if docs:
        vectorstore.add_documents(docs)  # type: ignore[arg-type]
        typer.echo("Ingestion completed.")
    else:
        typer.echo("No documents to ingest.")


if __name__ == "__main__":
    app()
