# backend/apps/core/management/commands/seed_database.py
"""
Django management command to seed database with test data
"""
import random
import time

import numpy as np
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.documents.models import Document, DocumentChunk


class Command(BaseCommand):
    help = "Seed database with test data for development and staging environments"

    def add_arguments(self, parser):
        parser.add_argument(
            "--environment",
            type=str,
            choices=["development", "staging"],
            default="development",
            help="Target environment (development or staging only)",
        )
        parser.add_argument(
            "--size",
            type=str,
            choices=["small", "medium", "large"],
            default="small",
            help="Amount of data to seed (small=5 docs, medium=20 docs, large=50 docs)",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing seed data before creating new",
        )

    def handle(self, *args, **options):
        environment = options["environment"]
        size = options["size"]
        clear_existing = options["clear"]

        # Prevent seeding production
        if settings.ENVIRONMENT == "production":
            raise CommandError(
                "Cannot seed database in production environment. "
                "Current ENVIRONMENT=production"
            )

        # Size mapping: (num_docs, chunks_per_doc)
        size_mapping = {
            "small": (5, 50),
            "medium": (20, 100),
            "large": (50, 200),
        }
        num_docs, chunks_per_doc = size_mapping[size]
        total_chunks = num_docs * chunks_per_doc

        self.stdout.write(f"Seeding {environment} environment with {size} dataset")
        self.stdout.write(
            f"Will create {num_docs} documents with {total_chunks} total chunks"
        )

        start_time = time.time()

        # Clear existing seed data if requested
        if clear_existing:
            self.clear_seed_data()

        # Seed the database
        with transaction.atomic():
            self.seed_documents(num_docs, chunks_per_doc)

        elapsed = time.time() - start_time
        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully created {num_docs} documents with {total_chunks} chunks "
                f"in {elapsed:.2f} seconds"
            )
        )

    def clear_seed_data(self):
        """Clear existing seed data"""
        seed_docs = Document.objects.filter(description__startswith="[SEED]")
        doc_count = seed_docs.count()
        chunk_count = DocumentChunk.objects.filter(
            document__description__startswith="[SEED]"
        ).count()

        if doc_count > 0:
            self.stdout.write(
                f"Clearing {doc_count} seed documents and {chunk_count} chunks..."
            )
            seed_docs.delete()
            self.stdout.write(self.style.WARNING("Cleared existing seed data"))

    def seed_documents(self, num_docs: int, chunks_per_doc: int):
        """Create documents and chunks with embeddings"""
        # Document templates for variety
        doc_templates = [
            {
                "title": "DMX Splitter {model} User Manual",
                "type": "manual",
                "product_line": "DMX Splitter",
            },
            {
                "title": "XPD-{model} Technical Specifications",
                "type": "datasheet",
                "product_line": "Ethernet DMX Node",
            },
            {
                "title": "Installation Guide - Model {model}",
                "type": "quick_start",
                "product_line": "DIN Rail",
            },
            {
                "title": "Firmware Release Notes v{version}",
                "type": "firmware_notes",
                "product_line": "DMX Equipment",
            },
            {
                "title": "Troubleshooting Guide {model}",
                "type": "manual",
                "product_line": "Hybrid DMX",
            },
        ]

        # Content templates for chunks
        content_templates = [
            "The device supports DMX512-A protocol with full RDM compatibility. "
            "Maximum cable length is 300 meters with proper termination. "
            "Operating temperature range: -20°C to +50°C.",
            "Connection procedure: 1) Power off all devices. 2) Connect DMX cables. "
            "3) Verify termination at end of line. 4) Power on controller first. "
            "5) Check status LEDs for proper operation.",
            "Technical specifications include: Input voltage 12-48V DC, "
            "power consumption max 5W, 4 isolated DMX outputs, "
            "LED indicators for signal and power status.",
            "The optical isolation protects against ground loops and interference. "
            "Each output can drive up to 32 DMX devices. "
            "Built-in surge protection on all ports.",
            "RDM (Remote Device Management) allows bidirectional communication. "
            "Discovery process automatically detects all connected devices. "
            "Parameters can be set remotely without physical access.",
            "Mounting options include DIN rail clip, surface mount bracket, "
            "or rack mount using optional accessories. "
            "Ensure adequate ventilation around device.",
            "LED indicators: Green = power OK, Red = fault detected, "
            "Yellow flashing = data activity, All off = no power. "
            "Refer to troubleshooting section for error codes.",
            "Firmware updates can be performed via USB connection. "
            "Download latest firmware from manufacturer website. "
            "Follow update procedure carefully to avoid bricking device.",
        ]

        documents = []

        self.stdout.write("Creating documents and chunks...")

        for i in range(num_docs):
            # Select random template
            template = random.choice(doc_templates)
            model_num = f"{random.randint(10, 99)}"
            version = f"{random.randint(1, 5)}.{random.randint(0, 9)}"

            # Create document (removed metadata field)
            doc = Document(
                title=template["title"].format(model=model_num, version=version),
                document_type=template["type"],
                language="en",
                product_line=template["product_line"],
                version=version if "firmware" in template["title"].lower() else "",
                description=f"[SEED] Test data - {template['product_line']} - Batch {int(time.time())}",
                file_size=random.randint(100000, 5000000),
                page_count=random.randint(5, 50),
                processed=True,
            )
            documents.append(doc)

        # Bulk create documents
        Document.objects.bulk_create(documents, batch_size=100)
        self.stdout.write(f"  Created {len(documents)} documents")

        # Now create chunks with embeddings
        self.stdout.write(f"  Generating {chunks_per_doc} chunks per document...")

        for doc_idx, doc in enumerate(
            Document.objects.filter(description__startswith="[SEED]").order_by(
                "-created_at"
            )[:num_docs]
        ):
            doc_chunks = []

            for chunk_idx in range(chunks_per_doc):
                # Generate realistic content
                content = random.choice(content_templates)
                content = f"[Page {chunk_idx // 5 + 1}] {content}"

                # Generate random 384-dimension embedding
                embedding = self._generate_random_embedding()

                chunk = DocumentChunk(
                    document=doc,
                    content=content,
                    page_number=(chunk_idx // 5) + 1,
                    section_title=(
                        f"Section {chunk_idx // 10 + 1}" if chunk_idx % 10 == 0 else ""
                    ),
                    chunk_index=chunk_idx,
                    embedding=embedding,
                    metadata={
                        "seeded": True,
                        "word_count": len(content.split()),
                        "char_count": len(content),
                        "embedding_model": "seed-random",
                    },
                )
                doc_chunks.append(chunk)

            # Bulk create chunks for this document
            DocumentChunk.objects.bulk_create(doc_chunks, batch_size=500)

            # Progress indicator
            if (doc_idx + 1) % 5 == 0 or doc_idx == num_docs - 1:
                total_chunks_created = (doc_idx + 1) * chunks_per_doc
                self.stdout.write(
                    f"  Progress: {doc_idx + 1}/{num_docs} documents, {total_chunks_created} chunks"
                )

    def _generate_random_embedding(self, dimension: int = 384) -> list:
        """Generate random normalized embedding vector"""
        # Generate random vector
        vector = np.random.randn(dimension).astype(np.float32)

        # Normalize to unit length (L2 normalization)
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm

        return vector.tolist()
