# /backend/apps/rag/management/commands/process_documents.py

"""
Django management command to process documents for RAG
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.documents.models import Document
from apps.rag.pipeline import rag_pipeline


class Command(BaseCommand):
    help = "Process documents for RAG: extract text, create chunks, generate embeddings"

    def add_arguments(self, parser):
        parser.add_argument(
            "--document-id",
            type=str,
            help="Process specific document by ID",
        )
        parser.add_argument(
            "--reprocess",
            action="store_true",
            help="Reprocess already processed documents",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=10,
            help="Number of documents to process in one batch",
        )

    def handle(self, *args, **options):
        document_id = options["document_id"]
        reprocess = options["reprocess"]
        batch_size = options["batch_size"]

        try:
            if document_id:
                # Process specific document
                try:
                    document = Document.objects.get(id=document_id)
                    self.process_single_document(document, reprocess)
                except Document.DoesNotExist:
                    raise CommandError(
                        f"Document with ID {document_id} does not exist."
                    )
            else:
                # Process multiple documents
                self.process_multiple_documents(reprocess, batch_size)

        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("\nOperation cancelled by user"))
        except Exception as e:
            raise CommandError(f"Error processing documents: {e}")

    def process_single_document(self, document, reprocess=False):
        """Process a single document"""
        if document.processed and not reprocess:
            self.stdout.write(
                self.style.WARNING(
                    f'Document "{document.title}" already processed. Use --reprocess to reprocess.'
                )
            )
            return

        self.stdout.write(f"Processing document: {document.title}")

        try:
            with transaction.atomic():
                # Delete existing chunks if reprocessing
                if reprocess:
                    deleted_count = document.chunks.count()
                    document.chunks.all().delete()
                    document.processed = False
                    document.save(update_fields=["processed"])
                    self.stdout.write(f"  Deleted {deleted_count} existing chunks")

                # Process document
                success = rag_pipeline.process_document(document)

                if success:
                    chunk_count = document.chunks.count()
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  ✓ Successfully processed. Created {chunk_count} chunks."
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(
                            f"  ✗ Failed to process document: {document.title}"
                        )
                    )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"  ✗ Error processing {document.title}: {e}")
            )

    def process_multiple_documents(self, reprocess, batch_size):
        """Process multiple documents"""
        # Get documents to process
        queryset = Document.objects.all()

        if not reprocess:
            queryset = queryset.filter(processed=False)

        total_count = queryset.count()

        if total_count == 0:
            self.stdout.write("No documents to process.")
            return

        self.stdout.write(f"Found {total_count} documents to process.")

        # Process in batches
        processed_count = 0
        failed_count = 0

        for i in range(0, total_count, batch_size):
            batch = queryset[i : i + batch_size]

            for document in batch:
                try:
                    self.process_single_document(document, reprocess)
                    processed_count += 1
                except Exception as e:
                    failed_count += 1
                    self.stdout.write(
                        self.style.ERROR(f"Failed to process {document.title}: {e}")
                    )

            # Show progress
            current_batch_end = min(i + batch_size, total_count)
            self.stdout.write(
                f"Progress: {current_batch_end}/{total_count} documents processed"
            )

        # Summary
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(f"Processing complete!")
        self.stdout.write(f"Successfully processed: {processed_count}")
        self.stdout.write(f"Failed: {failed_count}")

        # Show statistics
        stats = rag_pipeline.get_document_stats()
        self.stdout.write(f"\nCurrent statistics:")
        self.stdout.write(f'Total documents: {stats["total_documents"]}')
        self.stdout.write(f'Processed documents: {stats["processed_documents"]}')
        self.stdout.write(f'Total chunks: {stats["total_chunks"]}')
        self.stdout.write(f'Chunks with embeddings: {stats["chunks_with_embeddings"]}')
