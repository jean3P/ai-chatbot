# backend/apps/chat/views.py

"""
Chat API views with RAG integration
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
import logging
import uuid

from .models import Conversation, Message
from .serializers import (
    ConversationSerializer,
    MessageSerializer,
    ChatRequestSerializer,
    FeedbackSerializer
)
from apps.core.openrouter import openrouter_client
from apps.rag.pipeline import rag_pipeline

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([AllowAny])
def chat(request):
    """
    Main chat endpoint with RAG integration - process user message and return AI response
    """
    serializer = ChatRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    user_message = data['message']
    conversation_id = data.get('conversation_id')
    language = data.get('language', 'en')
    # IMPORTANT: Only use auto-detection if explicitly requested
    # Remove the automatic 'auto' detection to prevent unwanted language switching
    if language == 'auto':
        detected_language = detect_message_language(user_message)
        logger.info(f"DEBUG: Auto-detected language '{detected_language}' for message: '{user_message[:50]}...'")
        language = detected_language

    # Ensure we have a valid language code
    if language not in ['en', 'de', 'fr', 'es']:
        logger.info(f"DEBUG: Invalid language '{language}', defaulting to English")
        language = 'en'
    session_id = data.get('session_id')
    logger.info(f"DEBUG: Using language: {language}")

    try:
        # Get or create conversation
        if conversation_id:
            conversation = get_object_or_404(Conversation, id=conversation_id)
        else:
            conversation = Conversation.objects.create(
                session_id=session_id or str(uuid.uuid4()),
                language=language,
                title=user_message[:50] + "..." if len(user_message) > 50 else user_message
            )

        # Save user message
        user_msg = Message.objects.create(
            conversation=conversation,
            role='user',
            content=user_message
        )

        # Generate AI response with RAG
        try:
            # Get conversation history for context
            recent_messages = list(conversation.messages.order_by('-created_at')[:6])
            conversation_history = []

            for msg in reversed(recent_messages):
                conversation_history.append({
                    'role': msg.role,
                    'content': msg.content
                })

            # Generate RAG-enhanced response
            rag_result = rag_pipeline.generate_rag_response(
                query=user_message,
                conversation_history=conversation_history,
                language=language
            )

            ai_response = rag_result['response']
            citations = rag_result['citations']
            sources = rag_result['sources']
            context_used = rag_result['context_used']

            # Save AI response with RAG metadata
            ai_msg = Message.objects.create(
                conversation=conversation,
                role='assistant',
                content=ai_response,
                metadata={
                    'model': openrouter_client.llm_model,
                    'citations': citations,
                    'sources': sources,
                    'context_used': context_used,
                    'rag_enhanced': True
                }
            )

            # Update conversation timestamp
            conversation.save(update_fields=['updated_at'])

            return Response({
                'success': True,
                'conversation_id': str(conversation.id),
                'message': MessageSerializer(ai_msg).data,
                'rag_metadata': {
                    'context_used': context_used,
                    'sources_count': len(sources),
                    'citations_count': len(citations)
                }
            })

        except Exception as e:
            logger.error(f"Error generating RAG response: {e}")

            # Fallback to simple LLM response
            try:
                # Build simple conversation context
                recent_messages = conversation.messages.order_by('-created_at')[:6]
                messages = []

                # System prompt
                system_prompt = get_system_prompt(language)
                messages.append({"role": "system", "content": system_prompt})

                # Add conversation history
                for msg in reversed(recent_messages):
                    messages.append({
                        "role": msg.role,
                        "content": msg.content
                    })

                # Generate simple response
                ai_response = openrouter_client.generate_answer(messages)

                # Save AI response
                ai_msg = Message.objects.create(
                    conversation=conversation,
                    role='assistant',
                    content=ai_response,
                    metadata={
                        'model': openrouter_client.llm_model,
                        'citations': [],
                        'fallback_response': True,
                        'rag_error': str(e)
                    }
                )

                # Update conversation timestamp
                conversation.save(update_fields=['updated_at'])

                return Response({
                    'success': True,
                    'conversation_id': str(conversation.id),
                    'message': MessageSerializer(ai_msg).data,
                    'rag_metadata': {
                        'context_used': False,
                        'sources_count': 0,
                        'citations_count': 0,
                        'fallback_used': True
                    }
                })

            except Exception as fallback_error:
                logger.error(f"Fallback response generation failed: {fallback_error}")

                # Final fallback response
                fallback_response = get_fallback_response(language)
                ai_msg = Message.objects.create(
                    conversation=conversation,
                    role='assistant',
                    content=fallback_response,
                    metadata={'error': True, 'final_fallback': True}
                )

                return Response({
                    'success': True,
                    'conversation_id': str(conversation.id),
                    'message': MessageSerializer(ai_msg).data,
                    'rag_metadata': {
                        'context_used': False,
                        'sources_count': 0,
                        'citations_count': 0,
                        'error': True
                    }
                })

    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        return Response({
            'success': False,
            'error': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def conversation_detail(request, conversation_id):
    """Get conversation details with messages"""
    conversation = get_object_or_404(Conversation, id=conversation_id)
    serializer = ConversationSerializer(conversation)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def conversation_list(request):
    """List conversations for a session"""
    session_id = request.GET.get('session_id')

    conversations = Conversation.objects.all()

    if session_id:
        conversations = conversations.filter(session_id=session_id)

    conversations = conversations[:20]  # Limit to 20 most recent

    serializer = ConversationSerializer(conversations, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([AllowAny])
def feedback(request):
    """Submit feedback on a message"""
    serializer = FeedbackSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    feedback = serializer.save()
    return Response(FeedbackSerializer(feedback).data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
def search_documents(request):
    """Search documents using RAG similarity search"""
    query = request.data.get('query', '').strip()

    if not query:
        return Response({
            'error': 'Query is required'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Search similar chunks
        results = rag_pipeline.search_similar_chunks(query, limit=10)

        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append({
                'document_title': result['document_title'],
                'document_type': result['document_type'],
                'page_number': result['page_number'],
                'section_title': result['section_title'],
                'content_preview': result['content'][:200] + "..." if len(result['content']) > 200 else result['content'],
                'similarity_score': result['similarity_score']
            })

        return Response({
            'query': query,
            'results': formatted_results,
            'total_results': len(formatted_results)
        })

    except Exception as e:
        logger.error(f"Error searching documents: {e}")
        return Response({
            'error': 'Search failed',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def rag_stats(request):
    """Get RAG system statistics"""
    try:
        stats = rag_pipeline.get_document_stats()
        return Response(stats)
    except Exception as e:
        logger.error(f"Error getting RAG stats: {e}")
        return Response({
            'error': 'Failed to get stats'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def get_system_prompt(language='en'):
    """Get system prompt for the AI assistant with RAG context"""

    # Validate language
    if language not in ['en', 'de', 'fr', 'es']:
        print(f"DEBUG: Invalid language '{language}' in system prompt, defaulting to English")
        language = 'en'

    prompts = {
        'en': """You are a helpful AI assistant that answers questions based on documentation using RAG (Retrieval-Augmented Generation). 

        When provided with relevant document context, use it to give accurate, specific answers with citations.
        When no relevant context is available, clearly state that and provide general helpful guidance.

        Guidelines:
        - Always mention specific page numbers and document titles when citing information
        - If the context doesn't fully answer the question, say so clearly
        - Provide step-by-step instructions when appropriate
        - Keep responses clear, concise, and helpful
        - If asked about something not in the documentation, explain that you need to search the available documents""",

        'de': """Sie sind ein hilfreicher KI-Assistent, der Fragen basierend auf der Dokumentation mit RAG (Retrieval-Augmented Generation) beantwortet.

        Verwenden Sie bei relevantem Dokumentenkontext diesen für genaue, spezifische Antworten mit Zitaten.
        Wenn kein relevanter Kontext verfügbar ist, sagen Sie dies klar und bieten allgemeine hilfreiche Anleitung.

        Richtlinien:
        - Erwähnen Sie immer spezifische Seitenzahlen und Dokumenttitel beim Zitieren
        - Falls der Kontext die Frage nicht vollständig beantwortet, sagen Sie dies klar
        - Geben Sie schrittweise Anweisungen wenn angemessen""",

        'fr': """Vous êtes un assistant IA utile qui répond aux questions basées sur la documentation en utilisant RAG (Génération Augmentée par Récupération).

        Lorsqu'un contexte de document pertinent est fourni, utilisez-le pour donner des réponses précises et spécifiques avec des citations.
        Lorsqu'aucun contexte pertinent n'est disponible, dites-le clairement et fournissez des conseils généraux utiles.""",

        'es': """Eres un asistente de IA útil que responde preguntas basadas en documentación usando RAG (Generación Aumentada por Recuperación).

        Cuando se proporciona contexto de documento relevante, úsalo para dar respuestas precisas y específicas con citas.
        Cuando no hay contexto relevante disponible, dilo claramente y proporciona orientación general útil."""
    }

    selected_prompt = prompts.get(language, prompts['en'])
    print(f"DEBUG: Selected system prompt for language: {language}")
    return selected_prompt


def detect_message_language(message: str) -> str:
    """Detect language from user message with improved accuracy"""
    message_lower = message.lower().strip()

    # More specific German detection
    german_words = ['wie', 'der', 'die', 'das', 'ich', 'ist', 'und', 'mit', 'auf', 'einem', 'einer', 'können',
                    'möchten']
    german_patterns = ['ü', 'ä', 'ö', 'ß']  # German-specific characters

    # More specific French detection
    french_words = ['comment', 'le', 'la', 'je', 'est', 'avec', 'pour', 'dans', 'cette', 'vous', 'nous', 'ils']
    french_patterns = ['ç', 'é', 'è', 'à', 'ù']  # French-specific characters

    # More specific Spanish detection - use complete words only and avoid common English false positives
    spanish_words = ['como', 'yo', 'para', 'que', 'este', 'esta', 'donde', 'cuando', 'porque', 'si', 'no', 'muy']
    spanish_patterns = ['ñ', 'í', 'á', 'é', 'ó', 'ú']  # Spanish-specific characters

    # Split message into words for whole-word matching
    words = message_lower.split()

    # Check for language-specific characters first (most reliable)
    if any(char in message_lower for char in german_patterns):
        return 'de'
    if any(char in message_lower for char in french_patterns):
        return 'fr'
    if any(char in message_lower for char in spanish_patterns):
        return 'es'

    # Count matches for each language (whole words only)
    german_score = sum(1 for word in words if word in german_words)
    french_score = sum(1 for word in words if word in french_words)
    spanish_score = sum(1 for word in words if word in spanish_words)

    # Require at least 2 matches to avoid false positives
    min_matches = 2
    max_score = max(german_score, french_score, spanish_score)

    if max_score >= min_matches:
        if german_score == max_score:
            return 'de'
        elif french_score == max_score:
            return 'fr'
        elif spanish_score == max_score:
            return 'es'

    # Default to English if no strong indicators found
    return 'en'


def get_fallback_response(language='en'):
    """Get fallback response when RAG and LLM fail"""
    responses = {
        'en': "I apologize, but I'm experiencing technical difficulties accessing both the documentation and my language model. Please try again in a moment, or contact support if the problem persists.",
        'de': "Entschuldigung, aber ich habe technische Schwierigkeiten beim Zugriff auf die Dokumentation und mein Sprachmodell. Bitte versuchen Sie es in einem Moment noch einmal.",
        'fr': "Je m'excuse, mais je rencontre des difficultés techniques pour accéder à la documentation et à mon modèle de langage. Veuillez réessayer dans un moment."
    }

    return responses.get(language, responses['en'])
