# backend/apps/documents/views.py
"""
Document API views
"""
import logging

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import Document, DocumentChunk
from .serializers import DocumentChunkSerializer, DocumentSerializer

logger = logging.getLogger(__name__)


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def document_list(request):
    """List documents or upload a new document"""
    if request.method == "GET":
        documents = Document.objects.all()[:20]  # Limit to 20 most recent
        serializer = DocumentSerializer(documents, many=True)
        return Response(serializer.data)

    elif request.method == "POST":
        serializer = DocumentSerializer(data=request.data)
        if serializer.is_valid():
            document = serializer.save()

            # TODO: Process document asynchronously
            # process_document_async.delay(document.id)

            return Response(
                DocumentSerializer(document).data, status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([AllowAny])
def document_detail(request, document_id):
    """Get document details"""
    document = get_object_or_404(Document, id=document_id)
    serializer = DocumentSerializer(document)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([AllowAny])
def document_chunks(request, document_id):
    """Get chunks for a document"""
    document = get_object_or_404(Document, id=document_id)
    chunks = document.chunks.all()[:50]  # Limit to 50 chunks
    serializer = DocumentChunkSerializer(chunks, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([AllowAny])
def search_chunks(request):
    """Search document chunks (simplified)"""
    query = request.GET.get("q", "").strip()

    if not query:
        return Response(
            {"error": 'Query parameter "q" is required'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Simple text search - in production, use vector similarity
    chunks = DocumentChunk.objects.filter(content__icontains=query)[:10]

    serializer = DocumentChunkSerializer(chunks, many=True)
    return Response({"query": query, "results": serializer.data})
