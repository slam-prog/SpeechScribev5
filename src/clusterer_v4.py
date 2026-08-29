"""
Ultra-Fast Clusterer V5 - Enhanced Accuracy & Memory Safe.

Authors: NAJIB MOHAMMED AL-AMIR & WALID HASSAN MOHAMMAD AL-MOTAWAKEL
AI Assistant: Perplexity AI
"""

import numpy as np
from scipy.io import wavfile
import os


class ClustererV5:
    """Enhanced clustering - memory safe."""
    
    def __init__(self):
        self.segment_length = 1102
        self.original_audio = None
        self.sample_rate = None
    
    def find_matches_enhanced(self, segment, audio, threshold_ratio=0.85):
        """Find matches - Memory Safe Version."""
        L = len(segment)
        N = len(audio)
        
        if L == 0 or N == 0 or L > N:
            return []
        
        # تطبيع المقطع
        segment_norm = segment / (np.linalg.norm(segment) + 1e-10)
        
        matches = []
        
        # معالجة على مراحل
        chunk_size = 10000
        
        for start in range(0, N - L + 1, chunk_size):
            end = min(start + chunk_size + L - 1, N)
            chunk = audio[start:end]
            
            if len(chunk) < L:
                continue
            
            num_windows = len(chunk) - L + 1
            
            if num_windows <= 0:
                continue
            
            # حلقة سريعة
            for i in range(num_windows):
                window = chunk[i:i+L]
                window_norm = window / (np.linalg.norm(window) + 1e-10)
                similarity = np.dot(window_norm, segment_norm)
                
                if similarity >= threshold_ratio:
                    match_pos = start + i
                    matches.append(match_pos)
        
        # إزالة التكرار
        if len(matches) > 0:
            final_matches = [matches[0]]
            for pos in matches[1:]:
                if pos - final_matches[-1] >= L // 2:
                    final_matches.append(pos)
            return final_matches
        else:
            return []
    
    def transcribe(self, audio, sample_rate, segment_ms=25.0, threshold=0.85, max_clusters=200):
        """Full transcription - memory safe."""
        self.original_audio = audio.copy()
        self.sample_rate = sample_rate
        
        L = int(sample_rate * segment_ms / 1000)
        self.segment_length = L
        
        N = len(audio)
        audio_work = audio.copy()
        used_mask = np.zeros(N, dtype=bool)
        
        clusters = []
        cluster_id = 0
        iteration = 0
        
        temp_dir = 'temp_segments'
        os.makedirs(temp_dir, exist_ok=True)
        
        while True:
            iteration += 1
            
            start_pos = 0
            while start_pos < N and used_mask[start_pos]:
                start_pos += 1
            
            if start_pos + L > N:
                break
            
            segment = audio_work[start_pos:start_pos+L]
            
            if np.max(np.abs(segment)) < 0.01:
                used_mask[start_pos:start_pos+L] = True
                continue
            
            matches = self.find_matches_enhanced(segment, audio_work, threshold_ratio=threshold)
            
            if not matches:
                used_mask[start_pos:start_pos+L] = True
                continue
            
            cluster = {
                'id': cluster_id,
                'representative_start': start_pos,
                'representative_end': start_pos + L,
                'segments': [],
                'matches': matches,
                'method': 'enhanced_v5',
            }
            
            for idx, match_pos in enumerate(matches):
                used_mask[match_pos:match_pos+L] = True
                
                cluster['segments'].append({
                    'start': match_pos,
                    'end': match_pos + L,
                    'start_seconds': match_pos / sample_rate,
                    'end_seconds': (match_pos + L) / sample_rate,
                })
                
                # حفظ WAV (يمكن حذفه لاحقاً)
                segment_audio = self.original_audio[match_pos:match_pos+L]
                wav_path = f'{temp_dir}/cluster_{cluster_id}_seg_{idx}.wav'
                wavfile.write(wav_path, sample_rate, (segment_audio * 32767).astype(np.int16))
            
            if cluster['segments']:
                clusters.append(cluster)
                cluster_id += 1
                
                for match_pos in matches:
                    audio_work[match_pos:match_pos+L] = 0
                
                if len(clusters) >= max_clusters:
                    break
            
            if iteration % 100 == 0:
                used_percent = (np.sum(used_mask) / N) * 100
                print(f"  Iteration {iteration}: {len(clusters)} clusters | Used: {used_percent:.1f}%")
        
        print(f"\nTotal clusters: {len(clusters)}")
        print(f"Total iterations: {iteration}")
        
        return clusters
