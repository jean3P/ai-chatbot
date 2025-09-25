# backend/apps/chat/views.py
"""
Chat API views
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

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([AllowAny])
def chat(request):
    """
    Main chat endpoint - process user message and return AI response
    """
    serializer = ChatRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    user_message = data['message']
    conversation_id = data.get('conversation_id')
    language = data.get('language', 'en')
    session_id = data.get('session_id')

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

        # Generate AI response (simplified for now)
        try:
            # Build conversation context
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

            # Generate response
            ai_response = openrouter_client.generate_answer(messages)

            # Save AI response
            ai_msg = Message.objects.create(
                conversation=conversation,
                role='assistant',
                content=ai_response,
                metadata={
                    'model': openrouter_client.llm_model,
                    'citations': []  # TODO: Add RAG citations
                }
            )

            # Update conversation timestamp
            conversation.save(update_fields=['updated_at'])

            return Response({
                'success': True,
                'conversation_id': str(conversation.id),
                'message': MessageSerializer(ai_msg).data
            })

        except Exception as e:
            logger.error(f"Error generating AI response: {e}")

            # Fallback response
            fallback_response = get_fallback_response(language)
            ai_msg = Message.objects.create(
                conversation=conversation,
                role='assistant',
                content=fallback_response,
                metadata={'error': True}
            )

            return Response({
                'success': True,
                'conversation_id': str(conversation.id),
                'message': MessageSerializer(ai_msg).data
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


def get_system_prompt(language='en'):
    """Get system prompt for the AI assistant"""
    prompts = {
        'en': """You are a helpful AI assistant that answers questions based on documentation. 
        Provide clear, step-by-step instructions when possible. 
        Keep responses concise and helpful.""",

        'de': """Sie sind ein hilfreicher KI-Assistent, der Fragen basierend auf der Dokumentation beantwortet. 
        Geben Sie wenn möglich klare, schrittweise Anweisungen. 
        Halten Sie die Antworten prägnant und hilfreich.""",

        'fr': """Vous êtes un assistant IA utile qui répond aux questions basées sur la documentation. 
        Fournissez des instructions claires et étape par étape lorsque possible. 
        Gardez les réponses concises et utiles.""",

        'es': """Eres un asistente de IA útil que responde preguntas basadas en documentación. 
        Proporciona instrucciones claras y paso a paso cuando sea posible. 
        Mantén las respuestas concisas y útiles."""
    }

    return prompts.get(language, prompts['en'])


def get_fallback_response(language='en'):
    """Get fallback response when AI fails"""
    responses = {
        'en': "I apologize, but I'm experiencing technical difficulties. Please try again in a moment.",
        'de': "Entschuldigung, aber ich habe technische Schwierigkeiten. Bitte versuchen Sie es in einem Moment noch einmal.",
        'fr': "Je m'excuse, mais je rencontre des difficultés techniques. Veuillez réessayer dans un moment.",
        'es': "Me disculpo, pero estoy experimentando dificultades técnicas. Por favor, inténtalo de nuevo en un momento."
    }

    return responses.get(language, responses['en'])
