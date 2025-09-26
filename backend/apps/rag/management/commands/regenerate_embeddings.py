# apps/rag/management/commands/regenerate_embeddings.py

"""
Django management command to regenerate embeddings with consistent model
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.documents.models import DocumentChunk
from apps.core.openrouter import openrouter_client
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Regenerate embeddings for all chunks using consistent embedding model'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=50,
            help='Number of chunks to process in one batch',
        )
        parser.add_argument(
            '--force-model',
            type=str,
            help='Force use of specific embedding model',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without actually updating',
        )

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        force_model = options['force_model']
        dry_run = options['dry_run']

        # Get all chunks
        total_chunks = DocumentChunk.objects.count()
        chunks_with_embeddings = DocumentChunk.objects.exclude(embedding__isnull=True).count()
        chunks_without_embeddings = total_chunks - chunks_with_embeddings

        self.stdout.write(f'Total chunks: {total_chunks}')
        self.stdout.write(f'Chunks with embeddings: {chunks_with_embeddings}')
        self.stdout.write(f'Chunks without embeddings: {chunks_without_embeddings}')

        if total_chunks == 0:
            self.stdout.write(self.style.WARNING('No chunks found to process'))
            return

        # Get current embedding model
        if force_model:
            current_model = force_model
            self.stdout.write(f'Forcing use of model: {current_model}')
        else:
            current_model = openrouter_client.get_current_embedding_model()
            self.stdout.write(f'Current embedding model: {current_model}')

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes will be made'))
            self.stdout.write(f'Would regenerate embeddings for {total_chunks} chunks using model: {current_model}')
            return

        # Confirm before proceeding
        if not self._confirm_regeneration(total_chunks, current_model):
            self.stdout.write('Cancelled by user')
            return

        # Process chunks in batches
        processed_count = 0
        failed_count = 0

        chunks_queryset = DocumentChunk.objects.all().order_by('id')

        for i in range(0, total_chunks, batch_size):
            batch = chunks_queryset[i:i + batch_size]

            try:
                self.stdout.write(
                    f'Processing batch {i // batch_size + 1} ({i + 1}-{min(i + batch_size, total_chunks)})...')

                # Extract texts for batch
                chunk_texts = [chunk.content for chunk in batch]
                chunk_ids = [chunk.id for chunk in batch]

                # Generate embeddings
                embeddings = openrouter_client.generate_embeddings(chunk_texts, model=force_model)

                if len(embeddings) != len(chunk_texts):
                    self.stdout.write(
                        self.style.ERROR(
                            f'Embedding count mismatch: expected {len(chunk_texts)}, got {len(embeddings)}')
                    )
                    failed_count += len(batch)
                    continue

                # Update chunks with new embeddings
                with transaction.atomic():
                    for chunk, embedding in zip(batch, embeddings):
                        chunk.embedding = embedding
                        # Add metadata about regeneration
                        if not chunk.metadata:
                            chunk.metadata = {}
                        chunk.metadata['embedding_model'] = openrouter_client.get_current_embedding_model()
                        chunk.metadata['embedding_regenerated'] = True
                        chunk.save(update_fields=['embedding', 'metadata'])

                processed_count += len(batch)
                self.stdout.write(f'  ✓ Updated {len(batch)} chunks')

            except Exception as e:
                failed_count += len(batch)
                self.stdout.write(
                    self.style.ERROR(f'Failed to process batch {i // batch_size + 1}: {e}')
                )

        # Summary
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write('Embedding regeneration complete!')
        self.stdout.write(f'Successfully processed: {processed_count}')
        self.stdout.write(f'Failed: {failed_count}')

        if processed_count > 0:
            self.stdout.write('\nNext steps:')
            self.stdout.write('1. Test the RAG system to ensure embeddings work correctly')
            self.stdout.write(
                '2. Run: python manage.py shell -c "from apps.rag.pipeline import rag_pipeline; print(rag_pipeline.search_similar_chunks(\'test query\'))"')

    def _confirm_regeneration(self, total_chunks, model):
        """Ask for user confirmation before regenerating embeddings"""
        self.stdout.write('\n' + '⚠️  WARNING: This will regenerate ALL embeddings!')
        self.stdout.write(f'   - {total_chunks} chunks will be processed')
        self.stdout.write(f'   - Using model: {model}')
        self.stdout.write('   - This may take several minutes and cost API credits')
        self.stdout.write('   - Existing embeddings will be overwritten')

        response = input('\nContinue? (yes/no): ').lower().strip()
        return response in ['yes', 'y']
