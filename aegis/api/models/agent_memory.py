from langgraph.store.postgres import PostgresStore
from langchain.embeddings import init_embeddings
from langchain_postgres import PGVectorStore, PGEngine
from django.db import models
from pgvector.django import VectorField, HnswIndex


class Doc(models.Model):
    # PGVectorStore defaults
    langchain_id = models.TextField(primary_key=True)        # default id_column
    content = models.TextField()                              # default content_column
    embedding = VectorField(dimensions=1536)                  # default embedding_column
    langchain_metadata = models.JSONField(default=dict, blank=True)  # default metadata_json_column

    # optional convenience fields for your app logic
    title = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        # create it in the RAG schema, with the exact table name PGVectorStore uses

        db_table = 'rag"."docs'
        indexes = [
            HnswIndex(
                name="docs_emb_l2_hnsw",
                fields=["embedding"],
                opclasses=["vector_l2_ops"],  # Euclidean / L2
                m=16,
                ef_construction=64,
            ),
        ]