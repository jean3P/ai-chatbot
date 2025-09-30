# /backend/apps/rag/management/commands/batch_upload_documents.py

"""
Django management command to batch upload documents from directory structure
"""
import os
import re
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.documents.models import Document
from apps.rag.pipeline import rag_pipeline
from apps.rag.processors import get_processor_for_file


class Command(BaseCommand):
    help = (
        "Batch upload documents from directory structure with automatic categorization"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "root_directory",
            type=str,
            help="Root directory containing document folders",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be processed without actually uploading",
        )
        parser.add_argument(
            "--process",
            action="store_true",
            help="Process documents immediately after upload",
        )
        parser.add_argument(
            "--language",
            type=str,
            default="de",  # German default based on your directory names
            help="Document language (default: de for German)",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Overwrite existing documents with same name",
        )

    def handle(self, *args, **options):
        root_dir = Path(options["root_directory"])
        dry_run = options["dry_run"]
        process_after_upload = options["process"]
        language = options["language"]
        overwrite = options["overwrite"]

        if not root_dir.exists():
            raise CommandError(f"Directory does not exist: {root_dir}")

        # Find all PDF files in subdirectories
        pdf_files = self.find_pdf_files(root_dir)

        if not pdf_files:
            self.stdout.write(
                self.style.WARNING("No PDF files found in the directory structure")
            )
            return

        self.stdout.write(f"Found {len(pdf_files)} PDF files to process")

        if dry_run:
            self.show_dry_run_results(pdf_files, language)
            return

        # Process files
        uploaded_count = 0
        failed_count = 0
        skipped_count = 0

        for file_info in pdf_files:
            try:
                result = self.upload_document(
                    file_info, language, overwrite, process_after_upload
                )

                if result == "uploaded":
                    uploaded_count += 1
                elif result == "skipped":
                    skipped_count += 1

            except Exception as e:
                failed_count += 1
                self.stdout.write(
                    self.style.ERROR(f'Failed to upload {file_info["file_path"]}: {e}')
                )

        # Summary
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(f"Batch upload complete!")
        self.stdout.write(f"Uploaded: {uploaded_count}")
        self.stdout.write(f"Skipped: {skipped_count}")
        self.stdout.write(f"Failed: {failed_count}")

    def find_pdf_files(self, root_dir):
        """Find all PDF files and extract metadata from directory structure"""
        pdf_files = []

        for root, dirs, files in os.walk(root_dir):
            root_path = Path(root)

            # Extract product info from directory name
            relative_path = root_path.relative_to(root_dir)
            product_info = self.extract_product_info(str(relative_path))

            for file in files:
                if file.lower().endswith(".pdf"):
                    file_path = root_path / file

                    # Extract document info
                    doc_info = self.extract_document_info(file, product_info)

                    pdf_files.append(
                        {
                            "file_path": file_path,
                            "filename": file,
                            "product_line": product_info["product_line"],
                            "product_model": product_info["product_model"],
                            "title": doc_info["title"],
                            "document_type": doc_info["document_type"],
                            "description": doc_info["description"],
                        }
                    )

        return pdf_files

    def extract_product_info(self, directory_path):
        """Extract product information from directory structure"""
        # Handle your specific directory structure
        if directory_path == ".":
            return {"product_line": "General", "product_model": ""}

        # Parse directory names like "28 AB-Splitter - XPD-28"
        parts = directory_path.split(" - ")

        if len(parts) >= 2:
            product_model = parts[-1]  # Last part (e.g., "XPD-28")
            product_description = " - ".join(parts[:-1])  # Everything before model
        else:
            product_model = ""
            product_description = directory_path

        # Determine product line from description
        product_line = self.categorize_product_line(product_description)

        return {
            "product_line": product_line,
            "product_model": product_model,
            "product_description": product_description,
        }

    def categorize_product_line(self, description):
        """Categorize products based on description"""
        description_lower = description.lower()

        if "splitter" in description_lower:
            return "DMX Splitter"
        elif "node" in description_lower or "ethernet" in description_lower:
            return "Ethernet DMX Node"
        elif "hutschienen" in description_lower:
            return "DIN Rail"
        elif "hybrid" in description_lower:
            return "Hybrid DMX"
        elif "booster" in description_lower:
            return "DMX Booster"
        else:
            return "DMX Equipment"

    def extract_document_info(self, filename, product_info):
        """Extract document information from filename"""
        filename_lower = filename.lower()
        filename_clean = (
            filename.replace(".pdf", "").replace("_", " ").replace("-", " ")
        )

        # Determine document type
        document_type = "other"
        if any(
            word in filename_lower
            for word in ["manual", "bedienungsanleitung", "handbuch"]
        ):
            document_type = "manual"
        elif any(
            word in filename_lower for word in ["datasheet", "datenblatt", "spec"]
        ):
            document_type = "datasheet"
        elif any(word in filename_lower for word in ["quick", "start", "installation"]):
            document_type = "quick_start"
        elif any(word in filename_lower for word in ["firmware", "software"]):
            document_type = "firmware_notes"

        # Create title
        title = (
            f"{product_info['product_model']} - {filename_clean}"
            if product_info["product_model"]
            else filename_clean
        )

        # Create description
        description = f"Documentation for {product_info['product_line']}"
        if product_info["product_model"]:
            description += f" {product_info['product_model']}"

        # Detect language from filename
        filename_lower = filename.lower()
        if any(lang in filename_lower for lang in ["_de", "_deu", "_german", "d0"]):
            document_language = "de"
        elif any(lang in filename_lower for lang in ["_fr", "_fre", "_french"]):
            document_language = "fr"
        elif any(lang in filename_lower for lang in ["_es", "_esp", "_spanish"]):
            document_language = "es"
        else:
            document_language = "en"  # Default

        return {
            "title": title,
            "document_type": document_type,
            "description": description,
            "language": document_language,
        }

    def upload_document(self, file_info, language, overwrite, process_after_upload):
        """Upload a single document"""
        file_path = file_info["file_path"]

        # Check if document already exists
        existing_doc = Document.objects.filter(title=file_info["title"]).first()

        if existing_doc and not overwrite:
            self.stdout.write(f'⏭️  Skipped (exists): {file_info["title"]}')
            return "skipped"

        # Validate file
        try:
            processor = get_processor_for_file(str(file_path))
        except ValueError as e:
            raise CommandError(f"Unsupported file type: {e}")

        self.stdout.write(f'📄 Uploading: {file_info["title"]}')

        with transaction.atomic():
            # Delete existing document if overwriting
            if existing_doc and overwrite:
                existing_doc.delete()

            # Create document record
            with open(file_path, "rb") as f:
                django_file = File(f, name=file_path.name)

                document = Document.objects.create(
                    title=file_info["title"],
                    file_path=django_file,
                    document_type=file_info["document_type"],
                    language=language,
                    product_line=file_info["product_line"],
                    description=file_info["description"],
                    file_size=file_path.stat().st_size,
                )

            # Process immediately if requested
            if process_after_upload:
                success = rag_pipeline.process_document(document)
                if success:
                    chunk_count = document.chunks.count()
                    self.stdout.write(f"  ✅ Processed: {chunk_count} chunks created")
                else:
                    self.stdout.write(f"  ⚠️  Upload successful but processing failed")
            else:
                self.stdout.write(f"  ✅ Uploaded: {document.id}")

        return "uploaded"

    def show_dry_run_results(self, pdf_files, language):
        """Show what would be processed in dry run mode"""
        self.stdout.write("\n📋 DRY RUN - Files that would be processed:")
        self.stdout.write("=" * 60)

        by_product_line = {}

        for file_info in pdf_files:
            product_line = file_info["product_line"]
            if product_line not in by_product_line:
                by_product_line[product_line] = []
            by_product_line[product_line].append(file_info)

        for product_line, files in by_product_line.items():
            self.stdout.write(f"\n📦 {product_line} ({len(files)} files):")

            for file_info in files:
                self.stdout.write(f'  📄 {file_info["title"]}')
                self.stdout.write(f'     File: {file_info["filename"]}')
                self.stdout.write(f'     Type: {file_info["document_type"]}')
                self.stdout.write(f'     Model: {file_info["product_model"]}')
                self.stdout.write(f"     Language: {language}")
                self.stdout.write("")

        self.stdout.write(f"Total files to process: {len(pdf_files)}")
        self.stdout.write("\nTo proceed with upload, run without --dry-run flag")
