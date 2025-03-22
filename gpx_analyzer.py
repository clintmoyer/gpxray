#!/usr/bin/env python3
import click
from lxml import etree
import math
from typing import List, Tuple, Dict
from dataclasses import dataclass
from datetime import datetime

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
                                'type': 'speed',
                                'message': f'High speed detected: {speed:.2f} km/h',
                                'location': f'Track {trk.find(f'.//{{{self.namespace}}}name').text}',
                                'time': p1.time.isoformat()
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
                            'type': 'elevation',
                            'message': f'Large elevation change detected: {elevation_change:.2f} meters',
                            'location': f'Track {trk.find(f'.//{{{self.namespace}}}name').text}',
                            'time': p1.time.isoformat()
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
                            'type': 'continuity',
                            'message': f'Large time gap between segments: {time_diff:.2f} seconds',
                            'location': f'Track {trk.find(f'.//{{{self.namespace}}}name').text}',
                            'time': last_point.time.isoformat()
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

if __name__ == '__main__':
    cli() 