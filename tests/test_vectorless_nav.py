import pytest

from llm import Generation
from vectorless import answer as answer_mod
from vectorless import navigation as nav_mod
from vectorless.answer import answer
from vectorless.models import DocumentNode
from vectorless.navigation import navigate


pytestmark = pytest.mark.django_db


def _tree():
    root = DocumentNode.objects.create(source="d.md", parent=None, title="d.md", level=0, path="d.md", position=0)
    a = DocumentNode.objects.create(source="d.md", parent=root, title="Breaches", level=2,
                                    content="Report within 72 hours.", path="d.md › Breaches", position=1)
    b = DocumentNode.objects.create(source="d.md", parent=root, title="Encryption", level=2,
                                    content="Encrypt at rest.", path="d.md › Encryption", position=2)
    return root, a, b


def test_navigate_selects_by_returned_indices(monkeypatch):
    _root, a, b = _tree()
    # TOC (level>0) is ordered by position: [Breaches(0), Encryption(1)]. LLM picks index 0.
    monkeypatch.setattr(nav_mod, "_generate_json", lambda prompt: "[0]")

    selected = navigate("how fast to report a breach?")
    assert [n.title for n in selected] == ["Breaches"]


def test_navigate_ignores_out_of_range_indices(monkeypatch):
    _tree()
    monkeypatch.setattr(nav_mod, "_generate_json", lambda prompt: "[0, 99]")
    selected = navigate("q")
    assert len(selected) == 1  # 99 is dropped


def test_answer_reads_selected_sections_and_traces_path(monkeypatch):
    _tree()
    monkeypatch.setattr(nav_mod, "_generate_json", lambda prompt: "[0]")
    monkeypatch.setattr(
        answer_mod, "run_generation",
        lambda parts, **kw: Generation(text="Within 72 hours [1].",
                                       input_tokens=30, output_tokens=6, total_tokens=36),
    )

    result = answer("how fast?")
    assert result["answer"] == "Within 72 hours [1]."
    assert result["trace"][0]["path"] == "d.md › Breaches"
    assert result["metrics"]["sections_opened"] == 1
