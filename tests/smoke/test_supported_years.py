from pathlib import Path
import sys
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from common import conference_match, load_snapshot, task_dir_for_topic
from download_pdfs import derive_pdf_url
from fetch_dblp import DblpIndexParser, DblpTocParser, filter_enumerated_records, title_matches_terms
from write_outputs import write_writer_context, writer_context_path


def test_supported_snapshots_exist() -> None:
    for year in (2023, 2024, 2025, 2026):
        snapshot = load_snapshot(year)
        assert snapshot


def test_conference_match_avoids_false_positive_substrings() -> None:
    snapshots = load_snapshot(2025)
    assert conference_match("NAACL", snapshots) is None
    assert conference_match("ISCAS", snapshots) is None
    assert conference_match("SVR", snapshots) is None


def test_acl_anthology_pdf_derivation() -> None:
    url = derive_pdf_url({"landing_url": "https://aclanthology.org/2025.acl-long.1191/"})
    assert url == "https://aclanthology.org/2025.acl-long.1191.pdf"


def test_title_matches_terms_supports_phrase_and_token_matching() -> None:
    matches = title_matches_terms(
        "Asynchronous Credit Assignment for Multi-Agent Reinforcement Learning.",
        ["credit assignment", "multi agent reinforcement learning", "bellman equation"],
    )
    assert "credit assignment" in matches
    assert "multi agent reinforcement learning" in matches
    assert "bellman equation" not in matches


def test_dblp_index_parser_extracts_year_specific_toc_urls() -> None:
    parser = DblpIndexParser(2025)
    parser.feed(
        """
        <a href="https://dblp.org/db/conf/acl/acl2025-1.html">ACL 2025</a>
        <a href="https://dblp.org/db/conf/acl/acl2024-1.html">ACL 2024</a>
        <a href="https://dblp.org/rec/conf/acl/2025-1.html">details</a>
        """
    )
    assert parser.toc_urls == ["https://dblp.org/db/conf/acl/acl2025-1.html"]


def test_dblp_toc_parser_extracts_entry_metadata() -> None:
    parser = DblpTocParser()
    parser.feed(
        """
        <li class="entry inproceedings" id="conf/acl/Test25">
          <nav class="publ">
            <ul>
              <li class="drop-down"><div class="body">
                <ul>
                  <li class="ee"><a href="https://aclanthology.org/2025.acl-long.999/">open</a></li>
                  <li class="details"><a href="https://dblp.org/rec/conf/acl/Test25.html">details</a></li>
                </ul>
              </div></li>
            </ul>
          </nav>
          <cite>
            <span itemprop="author"><span itemprop="name">Alice Example</span></span>
            <span itemprop="author"><span itemprop="name">Bob Example</span></span>
            <span class="title" itemprop="name">Provable Zero-Shot Generalization in Offline Reinforcement Learning.</span>
          </cite>
        </li>
        """
    )
    assert len(parser.entries) == 1
    entry = parser.entries[0]
    assert entry["title"] == "Provable Zero-Shot Generalization in Offline Reinforcement Learning."
    assert entry["authors"] == ["Alice Example", "Bob Example"]
    assert entry["landing_url"] == "https://aclanthology.org/2025.acl-long.999/"
    assert entry["dblp_url"] == "https://dblp.org/rec/conf/acl/Test25.html"


def test_filter_enumerated_records_matches_rl_title() -> None:
    records = [
        {
            "title": "Representation-driven Option Discovery in Reinforcement Learning.",
            "year": 2025,
            "conference_abbr": "AAAI",
            "conference_name": "AAAI Conference on Artificial Intelligence",
            "field": "AI",
            "authors": ["A"],
            "landing_url": "https://example.org/paper",
            "dblp_url": "https://dblp.org/rec/conf/aaai/Test25.html",
            "source": "dblp-toc",
        }
    ]
    filtered = filter_enumerated_records(records, ["option discovery", "credit assignment"])
    assert len(filtered) == 1
    assert filtered[0]["search_term"] == "option discovery"


def test_task_dir_uses_pdf_folder_name() -> None:
    with TemporaryDirectory() as temp_dir:
        run_dir = task_dir_for_topic("unit test topic", output_root=Path(temp_dir))
        assert run_dir.parent == Path(temp_dir)
        assert run_dir.name.startswith("ccf-paper-search-")
        assert (run_dir / "pdf").exists()
        assert not (run_dir / "pdfs").exists()


def test_writer_context_is_written() -> None:
    with TemporaryDirectory() as temp_dir:
        run_dir = Path(temp_dir)
        path = write_writer_context(
            run_dir,
            plan={
                "request": "test request",
                "topic": "reinforcement learning",
                "years": [2025],
                "seed_terms": ["reinforcement learning"],
                "terms": ["reinforcement learning"],
                "exclusions": [],
                "mode": "broad-recall",
                "download_open_pdfs": True,
            },
            records=[
                {
                    "title": "Representation-driven Option Discovery in Reinforcement Learning.",
                    "year": 2025,
                    "conference_abbr": "AAAI",
                    "conference_name": "AAAI Conference on Artificial Intelligence",
                    "field": "AI",
                    "authors": ["Alice Example"],
                    "doi": "https://doi.org/10.1/test",
                    "landing_url": "https://example.org/paper",
                    "pdf_url": "https://example.org/paper.pdf",
                    "sources": ["dblp-toc"],
                    "search_terms": ["option discovery"],
                }
            ],
            manifest=[
                {
                    "title": "Representation-driven Option Discovery in Reinforcement Learning.",
                    "status": "downloaded",
                    "pdf_path": "C:/tmp/a.pdf",
                }
            ],
            source_failures=["openalex:test"],
        )
        assert path == writer_context_path(run_dir)
        assert path.exists()
