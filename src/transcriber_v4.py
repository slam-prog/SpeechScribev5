"""
Speech Transcriber V5 - Enhanced Accuracy.

Authors: NAJIB MOHAMMED AL-AMIR & WALID HASSAN MOHAMMAD AL-MOTAWAKEL
AI Assistant: Perplexity AI
"""

import json
import csv
import numpy as np
from pathlib import Path

from audio_processor import AudioProcessor
from clusterer_v4 import ClustererV5


class SpeechTranscriberV5:
    """Main transcription class V5."""
    
    def __init__(self, audio_path=None, segment_ms=25.0, threshold=0.85, max_clusters=200):
        self.audio_path = audio_path
        self.segment_ms = segment_ms
        self.threshold = threshold
        self.max_clusters = max_clusters
        
        self.audio_processor = AudioProcessor()
        self.clusterer = ClustererV5()
        
        self.audio = None
        self.sample_rate = None
        self.clusters = []
        self.labels = {}
        self.text_result = []
    
    def load_audio(self):
        """Load audio file."""
        if not self.audio_path:
            raise ValueError("No audio path specified")
        
        self.sample_rate, self.audio = self.audio_processor.load(self.audio_path)
        print(f"Loaded {len(self.audio)/self.sample_rate:.2f}s audio")
    
    def transcribe(self):
        """Run full transcription pipeline V5."""
        if self.audio is None:
            self.load_audio()
        
        print("\n" + "="*60)
        print("=== Enhanced Transcription V5 ===")
        print("="*60)
        print(f"  Segment length: {self.segment_ms}ms")
        print(f"  Threshold: {self.threshold}")
        print(f"  Max clusters: {self.max_clusters}")
        print("="*60)
        
        self.clusters = self.clusterer.transcribe(
            self.audio,
            self.sample_rate,
            self.segment_ms,
            self.threshold,
            self.max_clusters,
        )
        
        print("\n" + "="*60)
        print("Transcription Complete!")
        print(f"  Total time: {len(self.audio)/self.sample_rate:.2f}s")
        print(f"  Total clusters: {len(self.clusters)}")
        print("="*60)
    
    def save_clusters_for_review(self, output_path='clusters.json'):
        """Save clusters to JSON."""
        clusters_lite = []
        
        sorted_clusters = sorted(
            self.clusters,
            key=lambda c: c['segments'][0]['start_seconds'] if c['segments'] else 0
        )
        
        for cluster in sorted_clusters:
            cluster_lite = {
                'id': cluster['id'],
                'count': len(cluster['segments']),
                'representative': {
                    'start_seconds': cluster['representative_start'] / self.sample_rate,
                    'end_seconds': cluster['representative_end'] / self.sample_rate,
                },
                'segments': [
                    {
                        'start_seconds': seg['start_seconds'],
                        'end_seconds': seg['end_seconds'],
                        'start': seg['start'],
                        'end': seg['end'],
                    }
                    for seg in cluster['segments'][:10]
                ]
            }
            clusters_lite.append(cluster_lite)
        
        with open(output_path, 'w', encoding='utf-8-sig') as f:
            json.dump(clusters_lite, f, indent=2, ensure_ascii=False)
        
        print(f"Saved clusters to {output_path}")
    
    def create_labels_template(self, output_path='manual_labels.csv'):
        """Create CSV template for manual labeling."""
        with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow([
                'cluster_id', 'character', 'count',
                'first_occurrence_seconds', 'notes'
            ])
            
            sorted_clusters = sorted(
                self.clusters,
                key=lambda c: c['segments'][0]['start_seconds'] if c['segments'] else 0
            )
            
            for cluster in sorted_clusters:
                cluster_id = cluster['id']
                count = len(cluster['segments'])
                first_occ = cluster['segments'][0]['start_seconds'] if cluster['segments'] else 0
                
                writer.writerow([
                    cluster_id,
                    '',
                    count,
                    f'{first_occ:.2f}',
                    ''
                ])
        
        print(f"Created labels template: {output_path}")
    
    def save_segments_info(self, output_csv='segments_info.csv'):
        """Save segment information to CSV."""
        with open(output_csv, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow([
                'cluster_id', 'segment_id',
                'start_sample', 'end_sample',
                'start_seconds', 'end_seconds'
            ])
            
            for cluster in self.clusters:
                cluster_id = cluster['id']
                
                for seg_id, seg in enumerate(cluster['segments']):
                    writer.writerow([
                        cluster_id,
                        seg_id,
                        seg['start'],
                        seg['end'],
                        f"{seg['start_seconds']:.6f}",
                        f"{seg['end_seconds']:.6f}",
                    ])
        
        print(f"Saved segments info to {output_csv}")
    
    def compress_audio(self, output_path='compressed_audio.wav'):
        """Create compressed audio."""
        if not self.clusters:
            return
        
        used_regions = []
        
        for cluster in self.clusters:
            for seg in cluster['segments']:
                used_regions.append((seg['start'], seg['end']))
        
        used_regions.sort()
        
        merged_regions = []
        if used_regions:
            current_start, current_end = used_regions[0]
            
            for start, end in used_regions[1:]:
                if start <= current_end + 100:
                    current_end = max(current_end, end)
                else:
                    merged_regions.append((current_start, current_end))
                    current_start, current_end = start, end
            
            merged_regions.append((current_start, current_end))
        
        compressed_audio = []
        
        for start, end in merged_regions:
            segment = self.audio[start:end]
            compressed_audio.extend(segment)
        
        compressed_audio = np.array(compressed_audio)
        
        from scipy.io import wavfile
        wavfile.write(output_path, self.sample_rate, (compressed_audio * 32767).astype(np.int16))
        
        original_size = len(self.audio) * 2
        compressed_size = len(compressed_audio) * 2
        ratio = (1 - compressed_size / original_size) * 100
        
        print(f"Compressed audio: {output_path}")
        print(f"  Original: {original_size / 1024 / 1024:.2f} MB")
        print(f"  Compressed: {compressed_size / 1024 / 1024:.2f} MB")
        print(f"  Reduction: {ratio:.1f}%")
    
    def load_manual_labels(self, labels_path='manual_labels.csv'):
        """Load manual labels from CSV."""
        self.labels = {}
        
        with open(labels_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                cluster_id = int(row['cluster_id'])
                character = row['character'].strip()
                if character:
                    self.labels[cluster_id] = character
        
        print(f"Loaded {len(self.labels)} labels")
    
    def generate_text(self):
        """Generate text from labels."""
        if not self.clusters:
            raise ValueError("No clusters available")
        
        if not self.labels:
            raise ValueError("No labels loaded")
        
        cluster_to_char = {}
        for cluster in self.clusters:
            cluster_id = cluster['id']
            if cluster_id in self.labels:
                character = self.labels[cluster_id]
                for seg in cluster['segments']:
                    cluster_to_char[seg['start']] = character
        
        self.text_result = []
        
        all_segments = []
        for cluster in self.clusters:
            if cluster['id'] in self.labels:
                character = self.labels[cluster['id']]
                for seg in cluster['segments']:
                    all_segments.append({
                        'character': character,
                        'start': seg['start'],
                        'end': seg['end'],
                        'start_seconds': seg['start_seconds'],
                        'end_seconds': seg['end_seconds'],
                    })
        
        all_segments.sort(key=lambda x: x['start'])
        
        for seg in all_segments:
            self.text_result.append(seg)
        
        print(f"Generated {len(self.text_result)} text segments")
    
    def save_text(self, output_txt='output_text.txt', output_csv='output_text_details.csv', output_srt='output_subtitles.srt'):
        """Save generated text to files."""
        if not self.text_result:
            raise ValueError("No text generated")
        
        with open(output_txt, 'w', encoding='utf-8-sig') as f:
            for seg in self.text_result:
                f.write(seg['character'])
        
        with open(output_csv, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(['character', 'start', 'end', 'start_seconds', 'end_seconds'])
            for seg in self.text_result:
                writer.writerow([
                    seg['character'],
                    seg['start'],
                    seg['end'],
                    f"{seg['start_seconds']:.3f}",
                    f"{seg['end_seconds']:.3f}",
                ])
        
        with open(output_srt, 'w', encoding='utf-8-sig') as f:
            for i, seg in enumerate(self.text_result, 1):
                start_ms = int(seg['start_seconds'] * 1000)
                end_ms = int(seg['end_seconds'] * 1000)
                
                start_h = start_ms // 3600000
                start_m = (start_ms % 3600000) // 60000
                start_s = (start_ms % 60000) // 1000
                start_ms_rem = start_ms % 1000
                
                end_h = end_ms // 3600000
                end_m = (end_ms % 3600000) // 60000
                end_s = (end_ms % 60000) // 1000
                end_ms_rem = end_ms % 1000
                
                f.write(f"{i}\n")
                f.write(f"{start_h:02d}:{start_m:02d}:{start_s:02d},{start_ms_rem:03d} --> ")
                f.write(f"{end_h:02d}:{end_m:02d}:{end_s:02d},{end_ms_rem:03d}\n")
                f.write(f"{seg['character']}\n\n")
        
        print(f"Saved text to {output_txt}, {output_csv}, {output_srt}")
