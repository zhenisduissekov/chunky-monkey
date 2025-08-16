import tempfile
import json
from pathlib import Path
from src.main import compute_hash
import os

def test_compute_hash_known_value():
    # Test that compute_hash returns correct SHA256 for known content
    with tempfile.NamedTemporaryFile("w+b", delete=True) as f:
        f.write(b"hello world")
        f.flush()
        expected = "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
        assert compute_hash(Path(f.name)) == expected

def test_compute_hash_empty_file():
    # Test that compute_hash returns correct SHA256 for empty file
    with tempfile.NamedTemporaryFile("w+b", delete=True) as f:
        expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        assert compute_hash(Path(f.name)) == expected

def test_compute_hash_different_files():
    # Test that different files produce different hashes
    with tempfile.NamedTemporaryFile("w+b", delete=True) as f1, \
         tempfile.NamedTemporaryFile("w+b", delete=True) as f2:
        f1.write(b"foo")
        f1.flush()
        f2.write(b"bar")
        f2.flush()
        assert compute_hash(Path(f1.name)) != compute_hash(Path(f2.name))

def test_detect_article_deltas(tmp_path):
    # Simulate delta detection logic from main.py
    def detect_article_deltas(articles_dir, hash_record_path):
        prev_hashes = {}
        if os.path.exists(hash_record_path):
            with open(hash_record_path) as f:
                prev_hashes = json.load(f)
        changed = []
        new_hashes = prev_hashes.copy()
        for md_file in Path(articles_dir).glob("*.md"):
            h = compute_hash(md_file)
            if md_file.name not in prev_hashes or prev_hashes[md_file.name] != h:
                changed.append(md_file)
            new_hashes[md_file.name] = h
        return changed, new_hashes

    # Setup: create two markdown files
    file1 = tmp_path / "a.md"
    file2 = tmp_path / "b.md"
    file1.write_text("foo")
    file2.write_text("bar")
    hash_record = tmp_path / "hashes.json"
    # First run: both are new
    changed, new_hashes = detect_article_deltas(tmp_path, hash_record)
    assert set(f.name for f in changed) == {"a.md", "b.md"}
    # Save hashes
    hash_record.write_text(json.dumps({f.name: compute_hash(f) for f in [file1, file2]}))
    # Second run: no changes
    changed, _ = detect_article_deltas(tmp_path, hash_record)
    assert changed == []
    # Modify one file
    file1.write_text("baz")
    changed, _ = detect_article_deltas(tmp_path, hash_record)
    assert [f.name for f in changed] == ["a.md"]
