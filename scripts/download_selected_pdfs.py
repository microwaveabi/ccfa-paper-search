from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import log_event, print_json
from download_pdfs import download_open_access_pdfs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args()

    run_dir = Path(args.run_dir).expanduser().resolve()
    final_papers_path = run_dir / ".internal" / "final_papers.json"
    pdf_dir = run_dir / "pdf"

    if not final_papers_path.exists():
        raise FileNotFoundError(f"Missing final paper selection: {final_papers_path}")

    records = json.loads(final_papers_path.read_text(encoding="utf-8"))
    log_event(f"Final PDF download start; selected_papers={len(records)}")
    manifest = download_open_access_pdfs(records, pdf_dir)
    downloaded = sum(1 for item in manifest if item.get("status") == "downloaded")
    manifest_path = run_dir / ".internal" / "download_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    log_event(f"Final PDF download complete; downloaded={downloaded} total={len(manifest)}")

    print_json(
        {
            "ok": True,
            "run_dir": str(run_dir),
            "selected_paper_count": len(records),
            "downloaded_pdf_count": downloaded,
            "manifest_path": str(manifest_path),
            "pdf_dir": str(pdf_dir),
        }
    )


if __name__ == "__main__":
    main()
