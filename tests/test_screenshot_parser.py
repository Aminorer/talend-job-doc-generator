import base64
from pathlib import Path

from parser.screenshot_parser import ScreenshotParser


FIXTURES = Path(__file__).parent / "fixtures"


def test_screenshot_parser_extracts_png(tmp_path):
    source = FIXTURES / "sample_job.screenshot"
    target = tmp_path / source.name
    target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    output_dir = tmp_path / "screens"
    parser = ScreenshotParser(str(target), output_dir=str(output_dir))
    extracted = parser.parse()

    assert extracted is not None
    assert extracted.exists()
    assert extracted.suffix == ".png"

    xml_content = source.read_text(encoding="utf-8")
    encoded = xml_content.split('value="')[1].split('"')[0]
    assert extracted.read_bytes() == base64.b64decode(encoded)
