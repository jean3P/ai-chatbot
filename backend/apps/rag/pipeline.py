# apps/rag/pipeline.py

"""
RAG Pipeline for document processing and retrieval with improved embedding consistency
"""
import logging
from typing import Any, Dict, List, Optional

import numpy as np
from django.conf import settings
from sklearn.metrics.pairwise import cosine_similarity

from apps.core.openrouter import openrouter_client
from apps.core.utils import chunk_text, clean_text, extract_citations
from apps.documents.models import Document, DocumentChunk

from .processors import PDFProcessor

logger = logging.getLogger(__name__)


class RAGPipeline:
    """Main RAG pipeline for document processing and retrieval"""

    def __init__(self):
        self.pdf_processor = PDFProcessor()
        self.max_chunk_size = getattr(settings, "MAX_CHUNK_SIZE", 1200)
        self.chunk_overlap = getattr(settings, "CHUNK_OVERLAP", 200)
        self.max_retrieval_chunks = getattr(settings, "MAX_RETRIEVAL_CHUNKS", 10)
        # Lower similarity threshold for better matches
        self.similarity_threshold = getattr(settings, "SIMILARITY_THRESHOLD", 0.3)

    def process_document(self, document: Document) -> bool:
        """
        Process a document: extract text, create chunks, generate embeddings

        Args:
            document: Document instance to process

        Returns:
            bool: Success status
        """
        try:
            logger.info(f"Processing document: {document.title}")

            # Extract text from PDF
            if not document.file_path:
                raise ValueError("Document has no file path")

            extracted_data = self.pdf_processor.extract_text(document.file_path.path)

            # Update document metadata
            document.page_count = extracted_data["page_count"]
            document.file_size = document.file_path.size

            # Create text chunks
            chunks_data = self._create_chunks(extracted_data["pages"])

            # Generate embeddings for chunks
            chunk_texts = [chunk["content"] for chunk in chunks_data]
            embeddings = openrouter_client.generate_embeddings(chunk_texts)

            if len(embeddings) != len(chunk_texts):
                logger.error(
                    f"Embedding count mismatch: expected {len(chunk_texts)}, got {len(embeddings)}"
                )
                return False

            # Get current embedding model for metadata
            current_model = openrouter_client.get_current_embedding_model()

            # Save chunks to database
            chunk_objects = []
            for i, (chunk_data, embedding) in enumerate(zip(chunks_data, embeddings)):
                # Add embedding model to metadata
                chunk_data["metadata"]["embedding_model"] = current_model
                chunk_data["metadata"]["embedding_dimension"] = (
                    len(embedding) if embedding else 0
                )

                chunk = DocumentChunk(
                    document=document,
                    content=chunk_data["content"],
                    page_number=chunk_data["page_number"],
                    section_title=chunk_data["section_title"],
                    chunk_index=i,
                    embedding=embedding,
                    metadata=chunk_data["metadata"],
                )
                chunk_objects.append(chunk)

            # Bulk create chunks
            DocumentChunk.objects.bulk_create(chunk_objects, batch_size=100)

            # Mark document as processed
            document.processed = True
            document.save(update_fields=["processed", "page_count", "file_size"])

            logger.info(
                f"Successfully processed document: {document.title} ({len(chunk_objects)} chunks)"
            )
            return True

        except Exception as e:
            logger.error(f"Error processing document {document.title}: {e}")
            return False

    def _create_chunks(self, pages: List[Dict]) -> List[Dict]:
        """Create text chunks from extracted pages"""
        chunks_data = []

        for page in pages:
            page_number = page["page_number"]
            sections = page.get("sections", [{"title": "", "content": page["content"]}])

            for section in sections:
                section_title = section.get("title", "").strip()
                section_content = clean_text(section.get("content", ""))

                if not section_content:
                    continue

                # Split section content into chunks
                text_chunks = chunk_text(
                    section_content,
                    max_size=self.max_chunk_size,
                    overlap=self.chunk_overlap,
                )

                for chunk_content in text_chunks:
                    chunk_data = {
                        "content": chunk_content,
                        "page_number": page_number,
                        "section_title": section_title,
                        "metadata": {
                            "word_count": len(chunk_content.split()),
                            "char_count": len(chunk_content),
                            "has_section_title": bool(section_title),
                        },
                    }
                    chunks_data.append(chunk_data)

        return chunks_data

    def search_similar_chunks(
        self, query: str, document_ids: Optional[List[str]] = None, limit: int = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar chunks using embedding similarity

        Args:
            query: Search query
            document_ids: Optional list of document IDs to search within
            limit: Maximum number of results

        Returns:
            List of similar chunks with similarity scores
        """
        try:
            limit = limit or self.max_retrieval_chunks

            # Generate query embedding
            query_embeddings = openrouter_client.generate_embeddings([query])
            if not query_embeddings:
                logger.error("Failed to generate query embedding")
                return []

            query_embedding = query_embeddings[0]
            current_model = openrouter_client.get_current_embedding_model()

            logger.info(
                f"Searching with model: {current_model}, embedding dimension: {len(query_embedding)}"
            )

            # Get chunks to search - prioritize chunks with same embedding model
            chunks_query = DocumentChunk.objects.select_related("document").exclude(
                embedding__isnull=True
            )

            if document_ids:
                chunks_query = chunks_query.filter(document_id__in=document_ids)

            # Get all chunks and separate by embedding model
            all_chunks = list(chunks_query)

            if not all_chunks:
                logger.warning("No chunks with embeddings found")
                return []

            # Separate chunks by embedding model
            same_model_chunks = []
            different_model_chunks = []

            for chunk in all_chunks:
                chunk_model = (
                    chunk.metadata.get("embedding_model") if chunk.metadata else None
                )
                if chunk_model == current_model:
                    same_model_chunks.append(chunk)
                else:
                    different_model_chunks.append(chunk)

            logger.info(
                f"Found {len(same_model_chunks)} chunks with same model, {len(different_model_chunks)} with different models"
            )

            # Try same model chunks first
            results = []
            if same_model_chunks:
                results = self._calculate_similarities(
                    query_embedding, same_model_chunks, current_model
                )

            # If not enough results and we have different model chunks, try those too (with lower threshold)
            if len(results) < limit and different_model_chunks:
                logger.info(
                    "Not enough same-model results, trying cross-model search with lower threshold"
                )
                cross_model_results = self._calculate_similarities(
                    query_embedding,
                    different_model_chunks,
                    current_model,
                    similarity_threshold=0.1,  # Very low threshold for cross-model
                )
                results.extend(cross_model_results)

            # Sort by similarity score and limit results
            results.sort(key=lambda x: x["similarity_score"], reverse=True)
            final_results = results[:limit]

            logger.info(
                f"Found {len(final_results)} similar chunks (threshold: {self.similarity_threshold})"
            )

            # Log top results for debugging
            for i, result in enumerate(final_results[:3]):
                logger.info(
                    f"Result {i + 1}: {result['similarity_score']:.3f} - {result['content'][:100]}..."
                )

            return final_results

        except Exception as e:
            logger.error(f"Error searching similar chunks: {e}")
            return []

    def _calculate_similarities(
        self,
        query_embedding: List[float],
        chunks: List[DocumentChunk],
        query_model: str,
        similarity_threshold: float = None,
    ) -> List[Dict[str, Any]]:
        """Calculate similarities between query and chunks"""
        if similarity_threshold is None:
            similarity_threshold = self.similarity_threshold

        results = []
        chunk_embeddings = []
        valid_chunks = []

        # Collect valid embeddings
        for chunk in chunks:
            if chunk.embedding and len(chunk.embedding) == len(query_embedding):
                chunk_embeddings.append(chunk.embedding)
                valid_chunks.append(chunk)

        if not chunk_embeddings:
            logger.warning("No valid chunk embeddings found")
            return results

        # Calculate similarities
        try:
            query_embedding_array = np.array([query_embedding])
            chunk_embeddings_array = np.array(chunk_embeddings)

            similarity_scores = cosine_similarity(
                query_embedding_array, chunk_embeddings_array
            )[0]

            # Create results
            for chunk, score in zip(valid_chunks, similarity_scores):
                if score >= similarity_threshold:
                    results.append(
                        {
                            "chunk": chunk,
                            "similarity_score": float(score),
                            "document_title": chunk.document.title,
                            "document_type": chunk.document.document_type,
                            "page_number": chunk.page_number,
                            "section_title": chunk.section_title,
                            "content": chunk.content,
                            "embedding_model": (
                                chunk.metadata.get("embedding_model", "unknown")
                                if chunk.metadata
                                else "unknown"
                            ),
                        }
                    )

        except Exception as e:
            logger.error(f"Error calculating similarities: {e}")

        return results

    def generate_rag_response(
        self, query: str, conversation_history: List[Dict] = None, language: str = "en"
    ) -> Dict[str, Any]:
        """
        Generate RAG-enhanced response with prominent document titles

        Args:
            query: User query
            conversation_history: Previous conversation messages
            language: Response language

        Returns:
            Dict containing response and metadata
        """
        # Validate and normalize language
        if language not in ["en", "de", "fr", "es"]:
            logger.info(
                f"DEBUG: Invalid language '{language}' in RAG pipeline, defaulting to English"
            )
            language = "en"

        logger.info(f"DEBUG: RAG pipeline using language: {language}")
        try:
            # Search for relevant chunks
            similar_chunks = self.search_similar_chunks(query)

            # Build context from retrieved chunks
            context = self._build_context(similar_chunks)

            # Create system prompt with context
            system_prompt = self._create_rag_system_prompt(context, language)

            logger.info(f"RAG context built with {len(similar_chunks)} chunks")
            logger.info(
                f"Documents referenced: {', '.join(set(chunk['document_title'] for chunk in similar_chunks))}"
            )

            # Build messages for LLM
            messages = [{"role": "system", "content": system_prompt}]

            # Add conversation history
            if conversation_history:
                for msg in conversation_history[-6:]:  # Last 6 messages
                    messages.append(
                        {
                            "role": msg.get("role", "user"),
                            "content": msg.get("content", ""),
                        }
                    )

            # Add current query
            messages.append({"role": "user", "content": query})

            # Generate response
            response = openrouter_client.generate_answer(messages, max_tokens=800)

            # Extract citations with document titles
            citations = self._extract_enhanced_citations(response, similar_chunks)

            return {
                "response": response,
                "citations": citations,
                "sources": [
                    {
                        "document": chunk["document_title"],
                        "page": chunk["page_number"],
                        "section": chunk["section_title"],
                        "similarity": chunk["similarity_score"],
                        "embedding_model": chunk.get("embedding_model", "unknown"),
                        "content_preview": (
                            chunk["content"][:150] + "..."
                            if len(chunk["content"]) > 150
                            else chunk["content"]
                        ),
                    }
                    for chunk in similar_chunks[:5]  # Top 5 sources
                ],
                "context_used": len(similar_chunks) > 0,
                "embedding_model_used": openrouter_client.get_current_embedding_model(),
                "documents_referenced": list(
                    set(chunk["document_title"] for chunk in similar_chunks)
                ),
            }

        except Exception as e:
            logger.error(f"Error generating RAG response: {e}")
            return {
                "response": self._get_fallback_response(language),
                "citations": [],
                "sources": [],
                "context_used": False,
                "error": str(e),
            }

    def _get_fallback_response(self, language: str) -> str:
        """Get fallback response when RAG fails - now supports all 4 languages"""
        responses = {
            "en": "I apologize, but I'm having trouble accessing the documentation right now. Please try rephrasing your question or try again in a moment.",
            "de": "Entschuldigung, aber ich habe derzeit Probleme beim Zugriff auf die Dokumentation. Bitte formulieren Sie Ihre Frage neu oder versuchen Sie es in einem Moment noch einmal.",
            "fr": "Je m'excuse, mais j'ai des difficultés à accéder à la documentation en ce moment. Veuillez reformuler votre question ou réessayer dans un moment.",
            "es": "Me disculpo, pero estoy teniendo problemas para acceder a la documentación en este momento. Por favor, reformule su pregunta o inténtelo de nuevo en un momento.",
        }
        return responses.get(language, responses["en"])  # Default to English

    def _extract_enhanced_citations(
        self, response: str, similar_chunks: List[Dict], language: str = "en"
    ) -> List[Dict]:
        """Extract citations with document titles for multiple languages"""
        citations = []

        # Language-specific keywords for detecting citations
        page_keywords = {
            "en": ["page", "p.", "pg."],
            "de": ["seite", "s.", "page"],
            "fr": ["page", "p.", "pg."],
            "es": ["página", "pág.", "p.", "page"],
        }

        keywords = page_keywords.get(language, page_keywords["en"])

        for i, chunk in enumerate(similar_chunks):
            # Check if the response references this document
            doc_title = chunk["document_title"]
            page_num = chunk["page_number"]

            # Look for various citation patterns
            citation_found = False
            response_lower = response.lower()

            # Check for document title mentions
            if doc_title.lower()[:20] in response_lower:
                citation_found = True

            # Check for page number mentions with different language keywords
            for keyword in keywords:
                if (
                    f"{keyword} {page_num}" in response_lower
                    or f"{keyword}{page_num}" in response_lower
                ):
                    citation_found = True
                    break

            if citation_found:
                citations.append(
                    {
                        "id": f"citation_{i}",
                        "document": doc_title,
                        "page": page_num,
                        "section": chunk.get("section_title", ""),
                        "text": chunk["content"][:200] + "...",
                        "similarity_score": chunk["similarity_score"],
                    }
                )

        return citations

    def _build_context(self, similar_chunks: List[Dict]) -> str:
        """Build context string from similar chunks with prominent document titles"""
        if not similar_chunks:
            return ""

        context_parts = []
        for i, chunk in enumerate(similar_chunks[:5], 1):  # Top 5 chunks
            similarity_info = f"[Similarity: {chunk['similarity_score']:.2f}]"

            # Make document title more prominent
            document_title = chunk["document_title"]
            page_number = chunk["page_number"]
            section_title = chunk.get("section_title", "")

            # Create a clear header for each source
            header = f"=== DOCUMENT {i}: {document_title} ===\n"
            header += f"Page: {page_number}"
            if section_title:
                header += f" | Section: {section_title}"
            header += f" | {similarity_info}\n"

            context_parts.append(f"{header}\n{chunk['content']}\n")

        return "\n".join(context_parts)

    def _create_rag_system_prompt(self, context: str, language: str) -> str:
        """Create system prompt with RAG context emphasizing document titles for multiple languages"""
        base_prompts = {
            "en": """You are a helpful AI assistant that answers questions based on the provided documentation context.

    CONTEXT:
    {context}

    INSTRUCTIONS:
    - Use the provided context to answer questions accurately and specifically
    - ALWAYS mention the specific document name when referencing information
    - Format citations as: "According to [Document Name, Page X]..." or "As stated in [Document Name, Page X]..."
    - If the context contains relevant information, reference it with both document name and page numbers
    - If the context doesn't contain sufficient information, say so clearly
    - Provide specific document and page references when citing information
    - Keep responses clear, helpful, and well-structured
    - If asked about something not in the context, explain that you need to search the documentation

    Example citation format:
    - "According to the XPD-28 Manual, Page 15, the DMX splitter should be..."
    - "As mentioned in the Installation Guide, Page 3, you need to..."
    - "The Technical Specifications document, Page 7, indicates that..."
    """,
            "de": """Sie sind ein hilfreicher KI-Assistent, der Fragen basierend auf dem bereitgestellten Dokumentationskontext beantwortet.

    KONTEXT:
    {context}

    ANWEISUNGEN:
    - Verwenden Sie den bereitgestellten Kontext, um Fragen genau und spezifisch zu beantworten
    - Erwähnen Sie IMMER den spezifischen Dokumentnamen bei der Referenzierung von Informationen
    - Formatieren Sie Zitate als: "Laut [Dokumentname, Seite X]..." oder "Wie in [Dokumentname, Seite X] angegeben..."
    - Wenn der Kontext relevante Informationen enthält, verweisen Sie darauf mit Dokumentnamen und Seitenzahlen
    - Wenn der Kontext keine ausreichenden Informationen enthält, sagen Sie dies klar
    - Geben Sie spezifische Dokument- und Seitenangaben an, wenn Sie Informationen zitieren
    - Halten Sie Antworten klar, hilfreich und gut strukturiert
    - Wenn nach etwas gefragt wird, das nicht im Kontext steht, erklären Sie, dass Sie die Dokumentation durchsuchen müssen

    Beispiel Zitat-Format:
    - "Laut XPD-28 Handbuch, Seite 15, sollte der DMX Splitter..."
    - "Wie im Installationshandbuch, Seite 3, erwähnt, müssen Sie..."
    - "Das Technische Spezifikationsdokument, Seite 7, zeigt an, dass..."
    """,
            "fr": """Vous êtes un assistant IA utile qui répond aux questions basées sur le contexte de documentation fourni.

    CONTEXTE:
    {context}

    INSTRUCTIONS:
    - Utilisez le contexte fourni pour répondre aux questions de manière précise et spécifique
    - Mentionnez TOUJOURS le nom spécifique du document lors du référencement d'informations
    - Formatez les citations comme: "Selon [Nom du Document, Page X]..." ou "Comme indiqué dans [Nom du Document, Page X]..."
    - Si le contexte contient des informations pertinentes, référencez-les avec le nom du document et les numéros de page
    - Si le contexte ne contient pas d'informations suffisantes, dites-le clairement
    - Fournissez des références spécifiques de document et de page lors de la citation d'informations
    - Gardez les réponses claires, utiles et bien structurées
    - Si on vous demande quelque chose qui n'est pas dans le contexte, expliquez que vous devez rechercher dans la documentation

    Exemple de format de citation:
    - "Selon le Manuel XPD-28, Page 15, le splitter DMX devrait être..."
    - "Comme mentionné dans le Guide d'Installation, Page 3, vous devez..."
    - "Le document Spécifications Techniques, Page 7, indique que..."
    """,
            "es": """Eres un asistente de IA útil que responde preguntas basándose en el contexto de documentación proporcionado.

    CONTEXTO:
    {context}

    INSTRUCCIONES:
    - Usa el contexto proporcionado para responder preguntas de manera precisa y específica
    - SIEMPRE menciona el nombre específico del documento al referenciar información
    - Formatea las citas como: "Según [Nombre del Documento, Página X]..." o "Como se indica en [Nombre del Documento, Página X]..."
    - Si el contexto contiene información relevante, referénciala con el nombre del documento y números de página
    - Si el contexto no contiene información suficiente, dilo claramente
    - Proporciona referencias específicas de documento y página al citar información
    - Mantén las respuestas claras, útiles y bien estructuradas
    - Si se pregunta sobre algo que no está en el contexto, explica que necesitas buscar en la documentación

    Ejemplo de formato de cita:
    - "Según el Manual XPD-28, Página 15, el splitter DMX debería ser..."
    - "Como se menciona en la Guía de Instalación, Página 3, necesitas..."
    - "El documento de Especificaciones Técnicas, Página 7, indica que..."
    """,
        }

        template = base_prompts.get(
            language, base_prompts["en"]
        )  # Default to English if language not found
        return template.format(
            context=(
                context
                if context
                else "No relevant documentation found in the knowledge base."
            )
        )

    def get_document_stats(self) -> Dict[str, Any]:
        """Get statistics about processed documents"""
        current_model = openrouter_client.get_current_embedding_model()

        # Get chunks by embedding model
        chunks_with_embeddings = DocumentChunk.objects.exclude(embedding__isnull=True)
        same_model_chunks = (
            chunks_with_embeddings.filter(
                metadata__embedding_model=current_model
            ).count()
            if current_model
            else 0
        )

        return {
            "total_documents": Document.objects.count(),
            "processed_documents": Document.objects.filter(processed=True).count(),
            "total_chunks": DocumentChunk.objects.count(),
            "chunks_with_embeddings": chunks_with_embeddings.count(),
            "chunks_with_current_model": same_model_chunks,
            "current_embedding_model": current_model,
        }


# Global pipeline instance
rag_pipeline = RAGPipeline()
