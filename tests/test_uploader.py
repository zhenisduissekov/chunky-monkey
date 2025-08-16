import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.uploader import upload_file

@patch("src.uploader.requests.post")
def test_upload_file_success(mock_post):
    # Setup mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": "file-123"}
    mock_post.return_value = mock_response

    # Create a temporary markdown file
    with tempfile.NamedTemporaryFile("w+", suffix=".md", delete=True) as f:
        f.write("# Test Article\nContent here.")
        f.flush()
        file_id = upload_file(Path(f.name), "sk-test")
        assert file_id == "file-123"
        # Ensure the correct endpoint was called
        args, kwargs = mock_post.call_args
        assert "/files" in args[0]
        assert kwargs["headers"]["Authorization"].startswith("Bearer ")
        assert "file" in kwargs["files"]
