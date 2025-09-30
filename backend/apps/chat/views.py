# apps/chat/views.py
"""
Chat API views with dual RAG architecture support
"""
import logging
import uuid

from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

# Old architecture imports
from apps.core.openrouter import openrouter_client
from apps.domain.models import ValidationError as DomainValidationError

# New architecture imports
from apps.infrastructure.container import create_chat_service
from apps.rag.pipeline import rag_pipeline

from .models import Conversation, Message
from .serializers import (
    ChatRequestSerializer,
    ConversationSerializer,
    FeedbackSerializer,
    MessageSerializer,
)

logger = logging.getLogger(__name__)

# Feature flag
USE_NEW_ARCHITECTURE = getattr(settings, "USE_NEW_RAG_ARCHITECTURE", False)


@api_view(["POST"])
@permission_classes([AllowAny])
def chat(request):
    """
    Main chat endpoint with RAG integration - process user message and return AI response

    Supports both old and new architecture via feature flag.
    """
    serializer = ChatRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data

    # Route to appropriate implementation
    if USE_NEW_ARCHITECTURE:
        return _chat_new_architecture(data)
    else:
        return _chat_old_architecture(data)


def _chat_new_architecture(data):
    """Handle chat using new hexagonal architecture"""
    user_message = data["message"]
    conversation_id = data.get("conversation_id")
    language = data.get("language", "en")
    session_id = data.get("session_id")

    # Validate language
    if language not in ["en", "de", "fr", "es"]:
        logger.info(f"Invalid language '{language}', defaulting to English")
        language = "en"

    logger.info(f"Using NEW architecture with language: {language}")

    try:
        # Create chat service
        service = create_chat_service()

        # Get or create conversation
        if conversation_id:
            conversation = get_object_or_404(Conversation, id=conversation_id)
            # Convert to domain conversation if needed
            conv_id = conversation.id
        else:
            # Create new conversation
            conversation = Conversation.objects.create(
                session_id=session_id or str(uuid.uuid4()),
                language=language,
                title=(
                    user_message[:50] + "..."
                    if len(user_message) > 50
                    else user_message
                ),
            )
            conv_id = conversation.id

        # Generate answer using new architecture
        try:
            answer = service.answer_question(
                conversation_id=conv_id, query=user_message, language=language
            )

            # Get the AI message that was saved by the service
            ai_msg = (
                Message.objects.filter(conversation_id=conv_id, role="assistant")
                .order_by("-created_at")
                .first()
            )

            return Response(
                {
                    "success": True,
                    "conversation_id": str(conversation.id),
                    "message": MessageSerializer(ai_msg).data,
                    "rag_metadata": {
                        "architecture": "new_hexagonal",
                        "context_used": answer.context_used,
                        "sources_count": answer.source_count,
                        "citations_count": len(answer.citations),
                        "method": answer.method,
                    },
                }
            )

        except DomainValidationError as e:
            logger.error(f"Domain validation error: {e}")
            return Response(
                {"success": False, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

    except Exception as e:
        logger.error(f"Error in new architecture: {e}", exc_info=True)

        # Fallback to simple response
        fallback_response = get_fallback_response(language)
        ai_msg = Message.objects.create(
            conversation=conversation,
            role="assistant",
            content=fallback_response,
            metadata={"error": True, "architecture": "new_hexagonal", "fallback": True},
        )

        return Response(
            {
                "success": True,
                "conversation_id": str(conversation.id),
                "message": MessageSerializer(ai_msg).data,
                "rag_metadata": {
                    "architecture": "new_hexagonal",
                    "context_used": False,
                    "error": True,
                    "fallback_used": True,
                },
            }
        )


def _chat_old_architecture(data):
    """Handle chat using old RAG architecture (original implementation)"""
    user_message = data["message"]
    conversation_id = data.get("conversation_id")
    language = data.get("language", "en")
    session_id = data.get("session_id")

    if language == "auto":
        detected_language = detect_message_language(user_message)
        logger.info(f"Auto-detected language '{detected_language}'")
        language = detected_language

    if language not in ["en", "de", "fr", "es"]:
        logger.info(f"Invalid language '{language}', defaulting to English")
        language = "en"

    logger.info(f"Using OLD architecture with language: {language}")

    try:
        # Get or create conversation
        if conversation_id:
            conversation = get_object_or_404(Conversation, id=conversation_id)
        else:
            conversation = Conversation.objects.create(
                session_id=session_id or str(uuid.uuid4()),
                language=language,
                title=(
                    user_message[:50] + "..."
                    if len(user_message) > 50
                    else user_message
                ),
            )

        # Save user message
        user_msg = Message.objects.create(
            conversation=conversation, role="user", content=user_message
        )

        # Generate AI response with RAG
        try:
            # Get conversation history
            recent_messages = list(conversation.messages.order_by("-created_at")[:6])
            conversation_history = []
            for msg in reversed(recent_messages):
                conversation_history.append({"role": msg.role, "content": msg.content})

            # Generate RAG-enhanced response
            rag_result = rag_pipeline.generate_rag_response(
                query=user_message,
                conversation_history=conversation_history,
                language=language,
            )

            ai_response = rag_result["response"]
            citations = rag_result["citations"]
            sources = rag_result["sources"]
            context_used = rag_result["context_used"]

            # Save AI response
            ai_msg = Message.objects.create(
                conversation=conversation,
                role="assistant",
                content=ai_response,
                metadata={
                    "model": openrouter_client.llm_model,
                    "citations": citations,
                    "sources": sources,
                    "context_used": context_used,
                    "rag_enhanced": True,
                    "architecture": "old_rag",
                },
            )

            conversation.save(update_fields=["updated_at"])

            return Response(
                {
                    "success": True,
                    "conversation_id": str(conversation.id),
                    "message": MessageSerializer(ai_msg).data,
                    "rag_metadata": {
                        "architecture": "old_rag",
                        "context_used": context_used,
                        "sources_count": len(sources),
                        "citations_count": len(citations),
                    },
                }
            )

        except Exception as e:
            logger.error(f"Error generating RAG response: {e}")

            # Fallback to simple LLM
            try:
                recent_messages = conversation.messages.order_by("-created_at")[:6]
                messages = [{"role": "system", "content": get_system_prompt(language)}]

                for msg in reversed(recent_messages):
                    messages.append({"role": msg.role, "content": msg.content})

                ai_response = openrouter_client.generate_answer(messages)

                ai_msg = Message.objects.create(
                    conversation=conversation,
                    role="assistant",
                    content=ai_response,
                    metadata={
                        "model": openrouter_client.llm_model,
                        "citations": [],
                        "fallback_response": True,
                        "architecture": "old_rag",
                        "rag_error": str(e),
                    },
                )

                conversation.save(update_fields=["updated_at"])

                return Response(
                    {
                        "success": True,
                        "conversation_id": str(conversation.id),
                        "message": MessageSerializer(ai_msg).data,
                        "rag_metadata": {
                            "architecture": "old_rag",
                            "context_used": False,
                            "fallback_used": True,
                        },
                    }
                )

            except Exception as fallback_error:
                logger.error(f"Fallback failed: {fallback_error}")

                fallback_response = get_fallback_response(language)
                ai_msg = Message.objects.create(
                    conversation=conversation,
                    role="assistant",
                    content=fallback_response,
                    metadata={
                        "error": True,
                        "final_fallback": True,
                        "architecture": "old_rag",
                    },
                )

                return Response(
                    {
                        "success": True,
                        "conversation_id": str(conversation.id),
                        "message": MessageSerializer(ai_msg).data,
                        "rag_metadata": {
                            "architecture": "old_rag",
                            "context_used": False,
                            "error": True,
                        },
                    }
                )

    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        return Response(
            {"success": False, "error": "Internal server error"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# Rest of the views remain the same
@api_view(["GET"])
@permission_classes([AllowAny])
def conversation_detail(request, conversation_id):
    """Get conversation details with messages"""
    conversation = get_object_or_404(Conversation, id=conversation_id)
    serializer = ConversationSerializer(conversation)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([AllowAny])
def conversation_list(request):
    """List conversations for a session"""
    session_id = request.GET.get("session_id")
    conversations = Conversation.objects.all()

    if session_id:
        conversations = conversations.filter(session_id=session_id)

    conversations = conversations[:20]
    serializer = ConversationSerializer(conversations, many=True)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([AllowAny])
def feedback(request):
    """Submit feedback on a message"""
    serializer = FeedbackSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    feedback = serializer.save()
    return Response(FeedbackSerializer(feedback).data, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([AllowAny])
def search_documents(request):
    """Search documents using RAG similarity search"""
    query = request.data.get("query", "").strip()

    if not query:
        return Response(
            {"error": "Query is required"}, status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # Use old architecture for now (can be updated later)
        results = rag_pipeline.search_similar_chunks(query, limit=10)

        formatted_results = []
        for result in results:
            formatted_results.append(
                {
                    "document_title": result["document_title"],
                    "document_type": result["document_type"],
                    "page_number": result["page_number"],
                    "section_title": result["section_title"],
                    "content_preview": (
                        result["content"][:200] + "..."
                        if len(result["content"]) > 200
                        else result["content"]
                    ),
                    "similarity_score": result["similarity_score"],
                }
            )

        return Response(
            {
                "query": query,
                "results": formatted_results,
                "total_results": len(formatted_results),
            }
        )

    except Exception as e:
        logger.error(f"Error searching documents: {e}")
        return Response(
            {"error": "Search failed"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def rag_stats(request):
    """Get RAG system statistics"""
    try:
        stats = rag_pipeline.get_document_stats()
        stats["architecture"] = "new_hexagonal" if USE_NEW_ARCHITECTURE else "old_rag"
        return Response(stats)
    except Exception as e:
        logger.error(f"Error getting RAG stats: {e}")
        return Response(
            {"error": "Failed to get stats"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# Helper functions
def get_system_prompt(language="en"):
    """Get system prompt for the AI assistant with RAG context"""
    if language not in ["en", "de", "fr", "es"]:
        language = "en"

    prompts = {
        "en": """You are a helpful AI assistant that answers questions based on documentation using RAG.""",
        "de": """Sie sind ein hilfreicher KI-Assistent.""",
        "fr": """Vous êtes un assistant IA utile.""",
        "es": """Eres un asistente de IA útil.""",
    }

    return prompts.get(language, prompts["en"])


def detect_message_language(message: str) -> str:
    """Detect language from user message"""
    # Simple detection logic
    return "en"


def get_fallback_response(language="en"):
    """Get fallback response when both architectures fail"""
    responses = {
        "en": "I apologize, but I'm experiencing technical difficulties. Please try again.",
        "de": "Entschuldigung, aber ich habe technische Schwierigkeiten.",
        "fr": "Je m'excuse, mais je rencontre des difficultés techniques.",
        "es": "Me disculpo, pero estoy teniendo problemas técnicos.",
    }
    return responses.get(language, responses["en"])
