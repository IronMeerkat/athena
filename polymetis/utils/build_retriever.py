from langchain_core.vectorstores import VectorStoreRetriever
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from langchain_cohere import CohereRerank
from langchain_postgres import PGVectorStore
from athena_logging import get_logger
from athena_settings import settings

logger = get_logger(__name__)



def build_retriever(vectorstore: PGVectorStore) -> VectorStoreRetriever | ContextualCompressionRetriever:
    search_type = settings.RETRIEVAL_SEARCH_TYPE
    k = settings.RETRIEVAL_K
    fetch_k = settings.RETRIEVAL_FETCH_K
    lambda_mult = settings.RETRIEVAL_MMR_LAMBDA

    base_kwargs = {"k": k}
    if search_type == "mmr":
        base_kwargs.update({"fetch_k": fetch_k, "lambda_mult": lambda_mult})

    base: VectorStoreRetriever = vectorstore.as_retriever(search_type=search_type, search_kwargs=base_kwargs)

    if settings.DISABLE_RERANKING == 1:
        return base

    provider = settings.RERANKER_PROVIDER.lower()

    # Cohere path (good for prod)
    if provider == "cohere" and CohereRerank is not None and settings.COHERE_API_KEY:
        try:
            top_n = settings.RERANKER_TOPN
            model = settings.COHERE_RERANK_MODEL
            reranker : CohereRerank = CohereRerank(model=model, top_n=top_n)
            return ContextualCompressionRetriever(
                base_retriever=base,
                base_compressor=reranker,
            )
        except Exception:
            logger.exception("Cohere reranker init failed; falling back to base retriever")
            return base

    # Local HF cross-encoder path (good for RTX 4070 dev)
    if provider == "hf" and HuggingFaceCrossEncoder is not None:
        try:
            model_name = settings.RERANKER_MODEL
            top_n = settings.RERANKER_TOPN
            # Device is auto-selected by underlying libs; no 'device' kw in this wrapper
            # Import torch lazily only to check availability if needed later
            try:
                import torch  # type: ignore
                if not torch.cuda.is_available():
                    raise Exception("CUDA failed")
            except Exception:
                logger.warning("using CPU", exc_info=True)

            ce : HuggingFaceCrossEncoder = HuggingFaceCrossEncoder(model_name=model_name)
            reranker : CrossEncoderReranker = CrossEncoderReranker(model=ce, top_n=top_n)
            return ContextualCompressionRetriever(
                base_retriever=base,
                base_compressor=reranker,
            )
        except Exception:
            logger.exception("HF cross-encoder reranker init failed; falling back to base retriever")
            return base

    return base