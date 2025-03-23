import pytest
from datetime import datetime
from gpx_analyzer import GPXAnalyzer, TrackPoint
import tempfile
import os

@pytest.fixture
def sample_gpx_content():
    return """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="Test GPX"
     xmlns="http://www.topografix.com/GPX/1/1"
     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
     xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd">
    <trk>
        <name>Test Track</name>
        <type>hiking</type>
        <trkseg>
            <trkpt lat="40.7128" lon="-74.0060">
                <ele>10.0</ele>
                <time>2024-01-01T10:00:00Z</time>
            </trkpt>
            <trkpt lat="40.7129" lon="-74.0061">
                <ele>20.0</ele>
                <time>2024-01-01T10:00:01Z</time>
            </trkpt>
            <trkpt lat="40.7130" lon="-74.0062">
                <ele>30.0</ele>
                <time>2024-01-01T10:00:02Z</time>
            </trkpt>
        </trkseg>
        <trkseg>
            <trkpt lat="40.7131" lon="-74.0063">
                <ele>40.0</ele>
                <time>2024-01-01T10:00:03Z</time>
            </trkpt>
        </trkseg>
    </trk>
</gpx>"""

@pytest.fixture
def sample_gpx_file(tmp_path, sample_gpx_content):
    gpx_file = tmp_path / "test.gpx"
    gpx_file.write_text(sample_gpx_content)
    return str(gpx_file)

def test_haversine_distance():
    analyzer = GPXAnalyzer("dummy.gpx")
    distance = analyzer._haversine_distance(40.7128, -74.0060, 40.7129, -74.0061)
    assert distance > 0
    assert distance < 1  # Should be less than 1 km

def test_parse_trackpoint():
    analyzer = GPXAnalyzer("dummy.gpx")
    point = TrackPoint(
        lat=40.7128,
        lon=-74.0060,
        ele=10.0,
        time=datetime(2024, 1, 1, 10, 0, 0)
    )
    assert point.lat == 40.7128
    assert point.lon == -74.0060
    assert point.ele == 10.0
    assert point.time == datetime(2024, 1, 1, 10, 0, 0)

def test_analyze_speed(sample_gpx_file):
    analyzer = GPXAnalyzer(sample_gpx_file)
    issues = analyzer.analyze_speed(max_speed_threshold=1.0)  # Very low threshold for testing
    assert len(issues) > 0
    assert issues[0]['type'] == 'speed'

def test_analyze_elevation(sample_gpx_file):
    analyzer = GPXAnalyzer(sample_gpx_file)
    issues = analyzer.analyze_elevation(max_elevation_change=5.0)  # Low threshold for testing
    assert len(issues) > 0
    assert issues[0]['type'] == 'elevation'

def test_analyze_segment_continuity(sample_gpx_file):
    analyzer = GPXAnalyzer(sample_gpx_file)
    issues = analyzer.analyze_segment_continuity(max_gap=0.1)  # Very low threshold for testing
    assert len(issues) > 0
    assert issues[0]['type'] == 'continuity'

def test_strip_privacy_basic(sample_gpx_file, tmp_path):
    output_file = str(tmp_path / "output.gpx")
    from gpx_analyzer import cli
    cli(['strip-privacy', sample_gpx_file, output_file])
    
    # Verify the output file exists and has content
    assert os.path.exists(output_file)
    with open(output_file, 'r') as f:
        content = f.read()
        assert '<?xml' in content
        assert '<gpx' in content
        assert '<trk>' in content
        assert '<trkpt' in content
        assert '<ele>' in content
        assert '<time>' not in content  # Verify timestamps are removed

def test_strip_privacy_with_trim(sample_gpx_file, tmp_path):
    output_file = str(tmp_path / "output.gpx")
    from gpx_analyzer import cli
    cli(['strip-privacy', sample_gpx_file, output_file, '--trim-distance', '0.25'])
    
    # Verify the output file exists and has content
    assert os.path.exists(output_file)
    with open(output_file, 'r') as f:
        content = f.read()
        assert '<?xml' in content
        assert '<gpx' in content
        assert '<trk>' in content
        assert '<trkpt' in content
        assert '<ele>' in content
        assert '<time>' not in content

def test_strip_privacy_with_start_location(sample_gpx_file, tmp_path):
    output_file = str(tmp_path / "output.gpx")
    from gpx_analyzer import cli
    cli(['strip-privacy', sample_gpx_file, output_file, 
         '--start-lat', '40.7128', '--start-lon', '-74.0060', 
         '--start-radius', '0.25'])
    
    # Verify the output file exists and has content
    assert os.path.exists(output_file)
    with open(output_file, 'r') as f:
        content = f.read()
        assert '<?xml' in content
        assert '<gpx' in content
        assert '<trk>' in content
        assert '<trkpt' in content
        assert '<ele>' in content
        assert '<time>' not in content

def test_strip_privacy_with_all_options(sample_gpx_file, tmp_path):
    output_file = str(tmp_path / "output.gpx")
    from gpx_analyzer import cli
    cli(['strip-privacy', sample_gpx_file, output_file,
         '--trim-distance', '0.5',
         '--start-lat', '40.7128', '--start-lon', '-74.0060',
         '--start-radius', '0.5'])
    
    # Verify the output file exists and has content
    assert os.path.exists(output_file)
    with open(output_file, 'r') as f:
        content = f.read()
        assert '<?xml' in content
        assert '<gpx' in content
        assert '<trk>' in content
        assert '<trkpt' in content
        assert '<ele>' in content
        assert '<time>' not in content 