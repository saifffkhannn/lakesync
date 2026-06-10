from convert_folder import _read_source_text


def test_read_source_text_accepts_windows_encoded_abap(tmp_path):
    source_path = tmp_path / "ABAP_RSSCD100.txt"
    source_path.write_bytes("REPORT zr.\nDATA text TYPE string VALUE 'Änderung'.\n".encode("cp1252"))

    assert "Änderung" in _read_source_text(source_path)
