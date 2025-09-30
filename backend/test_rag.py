# test_rag.py - Create this file in your backend directory

import os

import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from apps.core.openrouter import openrouter_client
from apps.documents.models import DocumentChunk
from apps.rag.pipeline import rag_pipeline


def test_embeddings():
    """Test embedding generation"""
    print("=== Testing Embedding Generation ===")
    try:
        test_embeddings = openrouter_client.generate_embeddings(["test query"])
        if test_embeddings:
            print(f"✓ Embedding generated: {len(test_embeddings)} vectors")
            print(f"✓ Dimension: {len(test_embeddings[0])}")
            print(f"✓ Current model: {openrouter_client.get_current_embedding_model()}")
        else:
            print("✗ No embeddings generated")
    except Exception as e:
        print(f"✗ Error: {e}")


def test_chunk_data():
    """Test chunk data"""
    print("\n=== Testing Chunk Data ===")
    total_chunks = DocumentChunk.objects.count()
    chunks_with_embeddings = DocumentChunk.objects.exclude(
        embedding__isnull=True
    ).count()

    print(f"Total chunks: {total_chunks}")
    print(f"Chunks with embeddings: {chunks_with_embeddings}")

    if chunks_with_embeddings > 0:
        sample_chunk = DocumentChunk.objects.exclude(embedding__isnull=True).first()
        print(
            f"Sample embedding dimension: {len(sample_chunk.embedding) if sample_chunk.embedding else 0}"
        )
        if sample_chunk.metadata:
            print(
                f"Sample embedding model: {sample_chunk.metadata.get('embedding_model', 'unknown')}"
            )


def test_similarity_search():
    """Test similarity search"""
    print("\n=== Testing Similarity Search ===")
    test_queries = ["DMX splitter", "installation", "connection", "power"]

    for query in test_queries:
        try:
            results = rag_pipeline.search_similar_chunks(query, limit=3)
            print(f"\nQuery: '{query}'")
            print(f"Found {len(results)} similar chunks")

            for i, result in enumerate(results):
                score = result["similarity_score"]
                content = result["content"][:80].replace("\n", " ")
                doc_title = result["document_title"]
                page = result["page_number"]
                print(
                    f"  {i + 1}. Score: {score:.3f} - {doc_title} (p.{page}) - {content}..."
                )

        except Exception as e:
            print(f"✗ Error searching for '{query}': {e}")


def test_full_rag_response():
    """Test complete RAG response"""
    print("\n=== Testing Full RAG Response ===")
    test_query = "How do I connect a DMX splitter?"

    try:
        response = rag_pipeline.generate_rag_response(test_query)
        print(f"Query: {test_query}")
        print(f"Context used: {response['context_used']}")
        print(f"Sources found: {len(response['sources'])}")
        print(f"Embedding model: {response.get('embedding_model_used', 'unknown')}")

        if response["sources"]:
            print("\nSources:")
            for i, source in enumerate(response["sources"]):
                print(
                    f"  {i + 1}. {source['document']} (p.{source['page']}) - Score: {source['similarity']:.3f}"
                )

        print(f"\nResponse: {response['response'][:300]}...")

    except Exception as e:
        print(f"✗ Error generating RAG response: {e}")


def get_system_stats():
    """Get system statistics"""
    print("\n=== System Statistics ===")
    try:
        stats = rag_pipeline.get_document_stats()
        for key, value in stats.items():
            print(f"{key}: {value}")
    except Exception as e:
        print(f"✗ Error getting stats: {e}")


if __name__ == "__main__":
    print("Testing RAG System...")
    print("=" * 50)

    test_embeddings()
    test_chunk_data()
    test_similarity_search()
    test_full_rag_response()
    get_system_stats()

    print("\n" + "=" * 50)
    print("Testing complete!")
