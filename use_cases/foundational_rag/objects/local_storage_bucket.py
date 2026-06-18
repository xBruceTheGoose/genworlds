import os
import logging
from typing import List

from genworlds.objects.abstracts.object import AbstractObject
from genworlds.events.abstracts.event import AbstractEvent
from genworlds.events.abstracts.action import AbstractAction

logger = logging.getLogger(__name__)

try:
    import PyPDF2
    _PDF_AVAILABLE = True
except ImportError:
    _PDF_AVAILABLE = False

try:
    from docx import Document as DocxDocument
    _DOCX_AVAILABLE = True
except ImportError:
    _DOCX_AVAILABLE = False


class AgentRequestsFolderConversion(AbstractEvent):
    event_type: str = "agent_requests_folder_conversion"
    description: str = "An agent requests conversion of all supported documents in a folder to a single txt file."
    input_folder_path: str
    output_file_path: str
    sender_id: str


class FolderConversionCompleted(AbstractEvent):
    event_type: str = "folder_conversion_completed"
    description: str = "Notifies the agent that the folder has been successfully converted into a txt file."
    output_txt_path: str
    sender_id: str


class ConvertFolderToTxt(AbstractAction):
    trigger_event_class = AgentRequestsFolderConversion
    description = "Converts all supported documents in a folder to a single txt file."

    def __init__(self, host_object: AbstractObject):
        super().__init__(host_object=host_object)

    def __call__(self, event: AgentRequestsFolderConversion):
        all_texts: List[str] = []

        for filename in os.listdir(event.input_folder_path):
            file_path = os.path.join(event.input_folder_path, filename)
            ext = os.path.splitext(filename)[1].lower()

            try:
                if ext == ".md":
                    with open(file_path, "r", encoding="utf-8") as f:
                        all_texts.append(f.read())

                elif ext == ".docx" and _DOCX_AVAILABLE:
                    doc = DocxDocument(file_path)
                    all_texts.append("\n".join(p.text for p in doc.paragraphs))
                elif ext == ".docx":
                    logger.warning("python-docx not installed; skipping %s", filename)

                elif ext == ".pdf" and _PDF_AVAILABLE:
                    with open(file_path, "rb") as f:
                        reader = PyPDF2.PdfReader(f)
                        all_texts.append(
                            "\n".join(
                                page.extract_text() or ""
                                for page in reader.pages
                            )
                        )
                elif ext == ".pdf":
                    logger.warning("PyPDF2 not installed; skipping %s", filename)

            except Exception:
                logger.exception("Failed to process file %s", file_path)

        output_txt_path = os.path.join(
            self.host_object.storage_path, event.output_file_path
        )
        with open(output_txt_path, "w", encoding="utf-8") as f:
            f.write("\n\n---\n\n".join(all_texts))

        logger.info("Converted folder to %s", output_txt_path)

        self.host_object.send_event(
            FolderConversionCompleted(
                sender_id=self.host_object.id,
                target_id=event.sender_id,
                output_txt_path=output_txt_path,
            )
        )


class LocalStorageBucket(AbstractObject):
    def __init__(self, id: str, storage_path: str = "./"):
        self.storage_path = storage_path
        actions = [ConvertFolderToTxt(host_object=self)]
        super().__init__(
            name="LocalStorage Bucket",
            id=id,
            description=(
                "Consolidates various document types (.md, .docx, .pdf) into a single "
                ".txt file and stores it locally."
            ),
            actions=actions,
        )
