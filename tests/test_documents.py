"""Tests for the document ingestion and analysis system."""

from graphsim.documents.reader import (
    DocumentContent,
    read_document,
    read_txt,
)
from graphsim.documents.analyzer import DocumentAnalysis, StakeholderInfo


# ============================================================================
# Reader tests
# ============================================================================

def test_read_txt_from_bytes():
    text = "Detta är ett testdokument.\n\nDet handlar om en reform."
    doc = read_txt(file_bytes=text.encode("utf-8"), filename="test.txt")

    assert doc.filename == "test.txt"
    assert doc.file_type == "txt"
    assert "testdokument" in doc.text
    assert doc.word_count > 0


def test_read_document_txt():
    text = "Reformbeslut om skolverksamhet."
    doc = read_document(file_bytes=text.encode("utf-8"), filename="reform.txt")

    assert doc.file_type == "txt"
    assert "Reformbeslut" in doc.text


def test_document_preview():
    text = "A" * 600
    doc = DocumentContent(filename="test.txt", file_type="txt", text=text)

    assert len(doc.preview) <= 503  # 500 + "..."
    assert doc.preview.endswith("...")


def test_document_word_count():
    doc = DocumentContent(
        filename="test.txt", file_type="txt",
        text="Hej alla glada medarbetare",
    )
    assert doc.word_count == 4


def test_read_document_unsupported():
    import pytest
    with pytest.raises(ValueError, match="Unsupported"):
        read_document(file_bytes=b"data", filename="test.xyz")


# ============================================================================
# Document analysis model tests
# ============================================================================

def test_document_analysis_model():
    analysis = DocumentAnalysis(
        title="Budgetneddragning 2025",
        document_type="decision",
        summary="Kommunen beslutar om 15% nedskärning",
        key_points=["Spara 20 MSEK", "Drabbar socialtjänsten"],
        decisions_made=["Personalneddragning"],
        affected_groups=["Socialsekreterare", "Klienter"],
        stakeholders=[
            StakeholderInfo(
                role="Enhetschef",
                perspective="Orolig för personalens arbetsmiljö",
                likely_stance="negative",
                key_concerns=["Personalbrist", "Kvalitet"],
            ),
        ],
        risks_identified=["Ökad arbetsbelastning"],
        simulation_hooks=["Konflikt mellan besparingsmål och kvalitetskrav"],
    )

    assert analysis.title == "Budgetneddragning 2025"
    assert len(analysis.stakeholders) == 1
    assert analysis.stakeholders[0].likely_stance == "negative"


def test_stakeholder_info_defaults():
    s = StakeholderInfo(
        role="Test", perspective="Neutral", likely_stance="neutral"
    )
    assert s.information_access == "medium"
    assert s.key_concerns == []
