#!/usr/bin/env python3
import click
from lxml import etree
import math
from typing import List, Tuple, Dict
from dataclasses import dataclass
from datetime import datetime
import sys

@dataclass
class TrackPoint:
    lat: float
    lon: float
    ele: float
    time: datetime
    speed: float = 0.0

class GPXAnalyzer:
    def __init__(self, gpx_file: str):
        self.gpx_file = gpx_file
        self.tree = etree.parse(gpx_file)
        self.root = self.tree.getroot()
        self.namespace = self.root.nsmap[None]

    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate the great circle distance between two points using the haversine formula."""
        R = 6371  # Earth's radius in kilometers

        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        distance = R * c

        return distance

    def _parse_trackpoint(self, trkpt) -> TrackPoint:
        """Parse a trackpoint element into a TrackPoint object."""
        lat = float(trkpt.get('lat'))
        lon = float(trkpt.get('lon'))
        ele = float(trkpt.find(f'.//{{{self.namespace}}}ele').text)
        time_str = trkpt.find(f'.//{{{self.namespace}}}time').text
        time = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        
        return TrackPoint(lat=lat, lon=lon, ele=ele, time=time)

    def analyze_speed(self, max_speed_threshold: float = 100.0) -> List[Dict]:
        """Analyze speed between consecutive points using the haversine formula."""
        issues = []
        
        for trk in self.root.findall(f'.//{{{self.namespace}}}trk'):
            for trkseg in trk.findall(f'.//{{{self.namespace}}}trkseg'):
                points = [self._parse_trackpoint(trkpt) for trkpt in trkseg.findall(f'.//{{{self.namespace}}}trkpt')]
                
                for i in range(len(points) - 1):
                    p1, p2 = points[i], points[i + 1]
                    distance = self._haversine_distance(p1.lat, p1.lon, p2.lat, p2.lon)
                    time_diff = (p2.time - p1.time).total_seconds() / 3600  # Convert to hours
                    
                    if time_diff > 0:
                        speed = distance / time_diff  # km/h
                        if speed > max_speed_threshold:
                            issues.append({
                                "type": "speed",
                                "message": f"High speed detected: {speed:.2f} km/h",
                                "location": f"Track {trk.find(f'.//{{{self.namespace}}}name').text}",
                                "time": p1.time.isoformat()
                            })
        
        return issues

    def analyze_elevation(self, max_elevation_change: float = 100.0) -> List[Dict]:
        """Analyze elevation changes between consecutive points."""
        issues = []
        
        for trk in self.root.findall(f'.//{{{self.namespace}}}trk'):
            for trkseg in trk.findall(f'.//{{{self.namespace}}}trkseg'):
                points = [self._parse_trackpoint(trkpt) for trkpt in trkseg.findall(f'.//{{{self.namespace}}}trkpt')]
                
                for i in range(len(points) - 1):
                    p1, p2 = points[i], points[i + 1]
                    elevation_change = abs(p2.ele - p1.ele)
                    
                    if elevation_change > max_elevation_change:
                        issues.append({
                            "type": "elevation",
                            "message": f"Large elevation change detected: {elevation_change:.2f} meters",
                            "location": f"Track {trk.find(f'.//{{{self.namespace}}}name').text}",
                            "time": p1.time.isoformat()
                        })
        
        return issues

    def analyze_segment_continuity(self, max_gap: float = 300.0) -> List[Dict]:
        """Analyze continuity between track segments."""
        issues = []
        
        for trk in self.root.findall(f'.//{{{self.namespace}}}trk'):
            trksegs = trk.findall(f'.//{{{self.namespace}}}trkseg')
            
            for i in range(len(trksegs) - 1):
                seg1_points = [self._parse_trackpoint(trkpt) for trkpt in trksegs[i].findall(f'.//{{{self.namespace}}}trkpt')]
                seg2_points = [self._parse_trackpoint(trkpt) for trkpt in trksegs[i + 1].findall(f'.//{{{self.namespace}}}trkpt')]
                
                if seg1_points and seg2_points:
                    last_point = seg1_points[-1]
                    first_point = seg2_points[0]
                    time_diff = (first_point.time - last_point.time).total_seconds()
                    
                    if time_diff > max_gap:
                        issues.append({
                            "type": "continuity",
                            "message": f"Large time gap between segments: {time_diff:.2f} seconds",
                            "location": f"Track {trk.find(f'.//{{{self.namespace}}}name').text}",
                            "time": last_point.time.isoformat()
                        })
        
        return issues

@click.group()
def cli():
    """GPX file analyzer and validator."""
    pass

@cli.command()
@click.argument('gpx_file', type=click.Path(exists=True))
@click.option('--max-speed', default=100.0, help='Maximum speed threshold in km/h')
@click.option('--max-elevation-change', default=100.0, help='Maximum elevation change threshold in meters')
@click.option('--max-gap', default=300.0, help='Maximum time gap between segments in seconds')
def analyze(gpx_file, max_speed, max_elevation_change, max_gap):
    """Analyze a GPX file for potential issues."""
    analyzer = GPXAnalyzer(gpx_file)
    
    speed_issues = analyzer.analyze_speed(max_speed)
    elevation_issues = analyzer.analyze_elevation(max_elevation_change)
    continuity_issues = analyzer.analyze_segment_continuity(max_gap)
    
    all_issues = speed_issues + elevation_issues + continuity_issues
    
    if not all_issues:
        click.echo("No issues found in the GPX file.")
        return
    
    click.echo(f"\nFound {len(all_issues)} issues:\n")
    for issue in all_issues:
        click.echo(f"[{issue['type'].upper()}] {issue['message']}")
        click.echo(f"Location: {issue['location']}")
        click.echo(f"Time: {issue['time']}\n")

@cli.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.argument('output_file', type=click.Path())
@click.option('--trim-distance', type=click.Choice(['0.25', '0.5', '1.0']), default='0.25',
              help='Distance in miles to trim from start and end of track')
@click.option('--start-lat', type=float, help='Latitude of start location to remove points near')
@click.option('--start-lon', type=float, help='Longitude of start location to remove points near')
@click.option('--start-radius', type=click.Choice(['0.25', '0.5', '1.0']), default='0.25',
              help='Radius in miles to remove points near start location')
def strip_privacy(input_file: str, output_file: str, trim_distance: str, start_lat: float, 
                 start_lon: float, start_radius: str):
    """Strip privacy-sensitive details from a GPX file."""
    try:
        # Parse the input GPX file
        tree = etree.parse(input_file)
        root = tree.getroot()
        namespace = root.nsmap[None]

        # Create a new GPX element with only essential attributes
        new_root = etree.Element('gpx', 
            version="1.1",
            creator="GPXAnalyzer",
            xmlns="http://www.topografix.com/GPX/1/1",
            nsmap=root.nsmap)

        # Convert miles to kilometers for calculations
        trim_distance_km = float(trim_distance) * 1.60934
        start_radius_km = float(start_radius) * 1.60934

        # Copy tracks
        for trk in root.findall(f'.//{{{namespace}}}trk'):
            new_trk = etree.SubElement(new_root, f'{{{namespace}}}trk')
            
            # Copy track name and type if they exist
            name = trk.find(f'.//{{{namespace}}}name')
            if name is not None:
                etree.SubElement(new_trk, f'{{{namespace}}}name').text = name.text
            
            trk_type = trk.find(f'.//{{{namespace}}}type')
            if trk_type is not None:
                etree.SubElement(new_trk, f'{{{namespace}}}type').text = trk_type.text

            # Process track segments
            for trkseg in trk.findall(f'.//{{{namespace}}}trkseg'):
                new_trkseg = etree.SubElement(new_trk, f'{{{namespace}}}trkseg')
                
                # Get all trackpoints
                trkpts = trkseg.findall(f'.//{{{namespace}}}trkpt')
                if not trkpts:
                    continue

                # Calculate cumulative distances for trimming
                distances = []
                total_distance = 0
                for i in range(len(trkpts) - 1):
                    lat1 = float(trkpts[i].get('lat'))
                    lon1 = float(trkpts[i].get('lon'))
                    lat2 = float(trkpts[i + 1].get('lat'))
                    lon2 = float(trkpts[i + 1].get('lon'))
                    distance = GPXAnalyzer._haversine_distance(lat1, lon1, lat2, lon2)
                    total_distance += distance
                    distances.append(total_distance)

                # Find points to keep based on trim distance
                start_idx = 0
                end_idx = len(trkpts)
                
                # Trim from start
                for i, dist in enumerate(distances):
                    if dist >= trim_distance_km:
                        start_idx = i
                        break

                # Trim from end
                for i in range(len(distances) - 1, -1, -1):
                    if total_distance - distances[i] >= trim_distance_km:
                        end_idx = i + 1
                        break

                # Process trackpoints
                for i, trkpt in enumerate(trkpts):
                    # Skip points outside the trimmed range
                    if i < start_idx or i >= end_idx:
                        continue

                    # Skip points near start location if specified
                    if start_lat is not None and start_lon is not None:
                        lat = float(trkpt.get('lat'))
                        lon = float(trkpt.get('lon'))
                        distance = GPXAnalyzer._haversine_distance(start_lat, start_lon, lat, lon)
                        if distance <= start_radius_km:
                            continue

                    new_trkpt = etree.SubElement(new_trkseg, f'{{{namespace}}}trkpt',
                        lat=trkpt.get('lat'),
                        lon=trkpt.get('lon'))
                    
                    # Copy only elevation data
                    ele = trkpt.find(f'.//{{{namespace}}}ele')
                    if ele is not None:
                        etree.SubElement(new_trkpt, f'{{{namespace}}}ele').text = ele.text

        # Write the modified GPX to the output file
        tree = etree.ElementTree(new_root)
        tree.write(output_file, pretty_print=True, xml_declaration=True, encoding='UTF-8')
        
        click.echo(f"Successfully stripped privacy-sensitive details from {input_file}")
        click.echo(f"Output saved to {output_file}")
        
    except Exception as e:
        click.echo(f"Error processing GPX file: {str(e)}", err=True)
        sys.exit(1)

if __name__ == '__main__':
    cli() 