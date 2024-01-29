#!/usr/bin/env python3
"""
Explore embeddings database.
"""

import pandas as pd
import typer
from renumics import spotlight
from typing_extensions import Annotated

from assistant import get_chromadb, get_embeddings_model, parse_model_name
from assistant.const import EMBEDDINGS_MODEL_NAME_HELP
from assistant.settings import settings

app = typer.Typer()


@app.command()
def explore(
    embeddings_model_name: Annotated[
        str, typer.Option("--embeddings", help=EMBEDDINGS_MODEL_NAME_HELP)
    ] = settings.full_embeddings_model_name,
) -> None:
    """
    Load sources and chat history from a Polytec Assistant settings file, export
    and optionally visalize them.
    """

    embeddings_model = get_embeddings_model(*parse_model_name(embeddings_model_name))
    docs_vectorstore = get_chromadb(
        settings.docs_db_directory, embeddings_model, settings.docs_db_collection
    )

    response = docs_vectorstore.get(include=["metadatas", "documents", "embeddings"])
    docs_df = pd.DataFrame(
        {
            "id": response["ids"],
            "source": [metadata.get("source") for metadata in response["metadatas"]],
            "page": [metadata.get("page", -1) for metadata in response["metadatas"]],
            "document": response["documents"],
            "embedding": response["embeddings"],
        }
    )

    questions_vectorstore = get_chromadb(
        settings.questions_db_directory,
        embeddings_model,
        settings.questions_db_collection,
    )
    response = questions_vectorstore.get(
        include=["metadatas", "documents", "embeddings"]
    )
    questions_df = pd.DataFrame(
        {
            "id": response["ids"],
            "question": response["documents"],
            "embedding": response["embeddings"],
            "answer": [metadata.get("answer") for metadata in response["metadatas"]],
            "sources": [
                metadata.get("sources").split(",") for metadata in response["metadatas"]
            ],
        }
    )

    docs_df["used_by_n_questions"] = docs_df["id"].apply(
        lambda id: questions_df["sources"].apply(lambda sources: id in sources).sum()
    )
    docs_df["used_by"] = [
        q["id"] if src_id in q["sources"] else None
        for _, q in questions_df.iterrows()
        for src_id in docs_df["id"]
    ]
    questions_df["used_by"] = questions_df["id"]

    df = pd.concat([docs_df, questions_df], ignore_index=True)
    print(df)
    spotlight.show(df, embed=False, analyze=False)


if __name__ == "__main__":
    app()
