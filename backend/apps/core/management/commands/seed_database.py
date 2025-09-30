# backend/apps/core/management/commands/seed_database.py
"""
Django management command to seed database with test data
"""
import random
import time

import numpy as np
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.chat.models import Conversation, Message
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
            help="Amount of data to seed (small/medium/large)",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing seed data before creating new",
        )
        parser.add_argument(
            "--documents-only",
            action="store_true",
            help="Only seed documents, skip conversations",
        )
        parser.add_argument(
            "--conversations-only",
            action="store_true",
            help="Only seed conversations, skip documents",
        )

    def handle(self, *args, **options):
        environment = options["environment"]
        size = options["size"]
        clear_existing = options["clear"]
        docs_only = options["documents_only"]
        convs_only = options["conversations_only"]

        # Prevent seeding production
        if settings.ENVIRONMENT == "production":
            raise CommandError(
                "Cannot seed database in production environment. "
                "Current ENVIRONMENT=production"
            )

        # Size mapping: (num_docs, chunks_per_doc, num_conversations, msgs_per_conv)
        size_mapping = {
            "small": (5, 50, 20, (5, 10)),
            "medium": (20, 100, 100, (5, 12)),
            "large": (50, 200, 500, (5, 15)),
        }
        num_docs, chunks_per_doc, num_convs, msg_range = size_mapping[size]
        total_chunks = num_docs * chunks_per_doc

        self.stdout.write(self.style.SUCCESS(f"\n{'='*70}"))
        self.stdout.write(
            self.style.SUCCESS(f"Seeding {environment} environment with {size} dataset")
        )
        self.stdout.write(self.style.SUCCESS(f"{'='*70}\n"))

        start_time = time.time()

        # Clear existing seed data if requested
        if clear_existing:
            self.clear_seed_data(docs_only, convs_only)

        # Get or create test user for conversations
        test_user, _ = User.objects.get_or_create(
            username="seed_user",
            defaults={
                "email": "seed@example.com",
                "first_name": "Seed",
                "last_name": "User",
            },
        )

        # Seed the database
        with transaction.atomic():
            if not convs_only:
                self.stdout.write("\n SEEDING DOCUMENTS")
                self.stdout.write("-" * 70)
                self.seed_documents(num_docs, chunks_per_doc)

            if not docs_only:
                self.stdout.write("\n SEEDING CONVERSATIONS")
                self.stdout.write("-" * 70)
                self.seed_conversations(num_convs, msg_range, test_user)

        elapsed = time.time() - start_time
        self.stdout.write(self.style.SUCCESS(f"\n{'='*70}"))
        self.stdout.write(
            self.style.SUCCESS(f"✓ Seeding completed in {elapsed:.2f} seconds")
        )
        self.stdout.write(self.style.SUCCESS(f"{'='*70}\n"))

    def clear_seed_data(self, docs_only=False, convs_only=False):
        """Clear existing seed data"""
        if not convs_only:
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

        if not docs_only:
            seed_convs = Conversation.objects.filter(title__startswith="[SEED]")
            conv_count = seed_convs.count()
            msg_count = Message.objects.filter(
                conversation__title__startswith="[SEED]"
            ).count()

            if conv_count > 0:
                self.stdout.write(
                    f"Clearing {conv_count} seed conversations and {msg_count} messages..."
                )
                seed_convs.delete()

        if doc_count > 0 or conv_count > 0:
            self.stdout.write(self.style.WARNING("Cleared existing seed data\n"))

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

        for i in range(num_docs):
            # Select random template
            template = random.choice(doc_templates)
            model_num = f"{random.randint(10, 99)}"
            version = f"{random.randint(1, 5)}.{random.randint(0, 9)}"

            # Create document
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
        self.stdout.write(f"  ✓ Created {len(documents)} documents")

        # Now create chunks with embeddings
        total_chunks_created = 0
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
            total_chunks_created += len(doc_chunks)

        self.stdout.write(f"  ✓ Created {total_chunks_created} chunks")

    def seed_conversations(self, num_conversations: int, msg_range: tuple, user: User):
        """Create conversations with messages and citations"""
        # Conversation title templates
        title_templates = [
            "How to configure DMX {model}?",
            "Installation help for XPD-{model}",
            "Troubleshooting error code {error}",
            "Firmware update procedure",
            "RDM setup questions",
            "Cable length limitations",
            "Power supply requirements",
            "LED indicator meanings",
            "DIN rail mounting options",
            "Comparing models {m1} vs {m2}",
            "Best practices for {topic}",
            "Understanding {feature} feature",
        ]

        # User message templates
        user_templates = [
            "How do I {action} on the {model}?",
            "What is the maximum {spec} for this device?",
            "I'm getting error code {error}, what does it mean?",
            "Can you explain how {feature} works?",
            "What are the differences between {m1} and {m2}?",
            "Is it possible to {action}?",
            "I need help with {topic}.",
            "Where can I find information about {spec}?",
        ]

        # Assistant response templates
        assistant_templates = [
            "Based on the documentation, {explanation}. The recommended procedure is to {steps}.",
            "According to the technical specifications, {spec_detail}. You should {recommendation}.",
            "The error code {error} indicates {meaning}. To resolve this, {solution}.",
            "The {feature} feature allows you to {functionality}. Here's how to use it: {steps}.",
            "When comparing {m1} and {m2}, the key differences are {comparison}. I recommend {recommendation}.",
        ]

        conversations = []
        all_messages = []
        total_messages = 0

        self.stdout.write(f"  Creating {num_conversations} conversations...")

        # Get some document chunks for citations
        available_chunks = list(
            DocumentChunk.objects.filter(
                document__description__startswith="[SEED]"
            ).values_list("id", flat=True)[:100]
        )

        for i in range(num_conversations):
            # Generate conversation title
            template = random.choice(title_templates)
            model = f"XPD-{random.randint(10, 99)}"
            error = f"E{random.randint(100, 999)}"
            topic = random.choice(
                ["DMX setup", "RDM configuration", "network settings", "firmware"]
            )
            feature = random.choice(
                ["auto-discovery", "backup mode", "failover", "monitoring"]
            )

            title = template.format(
                model=model,
                m1=f"XPD-{random.randint(10, 99)}",
                m2=f"XPD-{random.randint(10, 99)}",
                error=error,
                topic=topic,
                feature=feature,
            )

            # Create conversation
            conv = Conversation(
                user=user,
                title=f"[SEED] {title}",
            )
            conversations.append(conv)

        # Bulk create conversations
        Conversation.objects.bulk_create(conversations, batch_size=100)
        self.stdout.write(f"  ✓ Created {len(conversations)} conversations")

        # Create messages for each conversation
        self.stdout.write("  Creating messages with citations...")

        for conv_idx, conv in enumerate(
            Conversation.objects.filter(title__startswith="[SEED]").order_by(
                "-created_at"
            )[:num_conversations]
        ):
            num_messages = random.randint(msg_range[0], msg_range[1])
            # Ensure even number for user/assistant pairs
            if num_messages % 2 != 0:
                num_messages += 1

            conv_messages = []

            for msg_idx in range(num_messages):
                is_user = msg_idx % 2 == 0

                if is_user:
                    # User message
                    template = random.choice(user_templates)
                    content = template.format(
                        action=random.choice(
                            ["configure", "install", "update", "reset"]
                        ),
                        model=f"XPD-{random.randint(10, 99)}",
                        spec=random.choice(
                            ["cable length", "power consumption", "data rate"]
                        ),
                        error=f"E{random.randint(100, 999)}",
                        feature=random.choice(
                            ["RDM", "failover", "auto-discovery", "monitoring"]
                        ),
                        m1=f"XPD-{random.randint(10, 99)}",
                        m2=f"XPD-{random.randint(10, 99)}",
                        topic=random.choice(
                            ["installation", "configuration", "troubleshooting"]
                        ),
                    )

                    msg = Message(
                        conversation=conv,
                        role="user",
                        content=content,
                        metadata={"seeded": True},
                    )
                else:
                    # Assistant message with citations
                    template = random.choice(assistant_templates)
                    content = template.format(
                        explanation=random.choice(
                            [
                                "the device supports full RDM functionality",
                                "you need to configure the network settings first",
                                "this requires firmware version 2.0 or higher",
                            ]
                        ),
                        steps=random.choice(
                            [
                                "power off, connect cables, then power on",
                                "use the configuration software to set parameters",
                                "follow the quick start guide section 3",
                            ]
                        ),
                        spec_detail=random.choice(
                            [
                                "the maximum cable length is 300 meters",
                                "power consumption is 5W maximum",
                                "the device supports 4 isolated outputs",
                            ]
                        ),
                        recommendation=random.choice(
                            [
                                "use Cat5e or better cable",
                                "ensure proper termination",
                                "consult the troubleshooting guide",
                            ]
                        ),
                        error=f"E{random.randint(100, 999)}",
                        meaning=random.choice(
                            [
                                "a connection timeout",
                                "invalid configuration",
                                "firmware mismatch",
                            ]
                        ),
                        solution=random.choice(
                            [
                                "check cable connections",
                                "reset to factory defaults",
                                "update firmware",
                            ]
                        ),
                        feature=random.choice(
                            ["RDM", "auto-discovery", "failover", "monitoring"]
                        ),
                        functionality=random.choice(
                            [
                                "automatically detect devices",
                                "switch to backup mode",
                                "monitor network status",
                            ]
                        ),
                        m1=f"XPD-{random.randint(10, 99)}",
                        m2=f"XPD-{random.randint(10, 99)}",
                        comparison=random.choice(
                            [
                                "port count and power rating",
                                "RDM support and firmware",
                                "mounting options and price",
                            ]
                        ),
                    )

                    # Add citations if we have chunks available
                    citations = []
                    if available_chunks:
                        num_citations = random.randint(1, 3)
                        cited_chunks = random.sample(
                            available_chunks, min(num_citations, len(available_chunks))
                        )
                        citations = [
                            {
                                "chunk_id": str(chunk_id),
                                "relevance": random.uniform(0.7, 0.95),
                            }
                            for chunk_id in cited_chunks
                        ]

                    msg = Message(
                        conversation=conv,
                        role="assistant",
                        content=content,
                        metadata={"seeded": True, "citations": citations},
                    )

                conv_messages.append(msg)

            # Bulk create messages for this conversation
            Message.objects.bulk_create(conv_messages, batch_size=100)
            total_messages += len(conv_messages)

            # Progress indicator
            if (conv_idx + 1) % 20 == 0 or conv_idx == num_conversations - 1:
                self.stdout.write(
                    f"  Progress: {conv_idx + 1}/{num_conversations} conversations, {total_messages} messages"
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"  ✓ Created {num_conversations} conversations with {total_messages} messages"
            )
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
