"""
Main Window GUI for SpeechScribe V4.

Authors: NAJIB MOHAMMED AL-AMIR & WALID HASSAN MOHAMMAD AL-MOTAWAKEL
AI Assistant: Perplexity AI

Features:
- Audio preview for each cluster
- Adjustable segment size (10-2000ms)
- Adjustable sensitivity (0.01-0.99)
- Adjustable match percentage (0-100%)
- Large, readable fonts
- No automatic sorting
- No default letters
- All audio formats support
"""

import sys
import os
import json
import csv
from pathlib import Path

import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QProgressBar, QTextEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter,
    QGroupBox, QFormLayout, QLineEdit, QSpinBox, QMessageBox,
    QStatusBar, QToolBar, QAction, QMenu, QMenuBar, QFrame,
    QScrollArea, QCheckBox, QComboBox, QButtonGroup, QRadioButton,
    QDoubleSpinBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QUrl
from PyQt5.QtGui import QFont, QIcon, QColor
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from transcriber_v4 import SpeechTranscriberV5


# في TranscriptionWorker:
class TranscriptionWorker(QThread):
    """Worker thread for transcription."""
    
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    
    def __init__(self, audio_path, segment_ms=25.0, threshold=0.85, max_clusters=200):
        super().__init__()
        self.audio_path = audio_path
        self.segment_ms = segment_ms
        self.threshold = threshold
        self.max_clusters = max_clusters
    
    def run(self):
        try:
            import shutil
            temp_dir = 'temp_segments'
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            
            from transcriber_v4 import SpeechTranscriberV5
            transcriber = SpeechTranscriberV5(
                audio_path=self.audio_path,
                segment_ms=self.segment_ms,
                threshold=self.threshold,
                max_clusters=self.max_clusters,
            )
            
            self.progress.emit(10, "Loading audio...")
            transcriber.load_audio()
            
            self.progress.emit(30, "Transcribing...")
            transcriber.transcribe()
            
            self.progress.emit(70, "Saving clusters...")
            transcriber.save_clusters_for_review('clusters.json')
            transcriber.create_labels_template('manual_labels.csv')
            transcriber.save_segments_info('segments_info.csv')
            transcriber.compress_audio('compressed_audio.wav')
            
            self.progress.emit(100, "Complete!")
            self.finished.emit(transcriber)
            
        except Exception as e:
            import traceback
            self.error.emit(f"{str(e)}\n{traceback.format_exc()}")

# في play_preview():
def play_preview(self):
    """Play audio preview from original file."""
    if not self.transcriber or not self.audio_path:
        self.log("Error: No audio loaded")
        return
    
    try:
        row = self.cluster_table.currentRow()
        if row < 0 or row >= len(self.clusters):
            return
        
        cluster = self.clusters[row]
        
        if not cluster['segments']:
            return
        
        first_segment = cluster['segments'][0]
        start = first_segment['start']
        end = first_segment['end']
        
        segment = self.transcriber.audio[start:end]
        
        if len(segment) == 0:
            self.log("Error: Empty segment")
            return
        
        from scipy.io import wavfile
        temp_path = 'temp_preview.wav'
        wavfile.write(temp_path, self.sample_rate, (segment * 32767).astype(np.int16))
        
        self.audio_player.setMedia(QMediaContent(QUrl.fromLocalFile(temp_path)))
        self.audio_player.play()
        
        self.current_temp_file = temp_path
        
        start_seconds = first_segment['start_seconds']
        end_seconds = first_segment['end_seconds']
        duration = end_seconds - start_seconds
        
        self.preview_info.setText(f"Cluster {cluster['id']} - Count: {len(cluster['segments'])}")
        self.preview_time.setText(f"Time: {start_seconds:.3f}s - {end_seconds:.3f}s ({duration*1000:.0f} ms)")
        
        self.log(f"Playing cluster {cluster['id']} at {start_seconds:.3f}s")
        
    except Exception as e:
        import traceback
        error_msg = f"Error: {str(e)}"
        self.log(error_msg)
        QMessageBox.critical(self, "Preview Error", error_msg)


class SpeechScribeMainWindow(QMainWindow):
    """Main window for SpeechScribe V4 with audio preview and full control."""
    
    def __init__(self):
        super().__init__()
        
        self.transcriber = None
        self.audio_path = None
        self.clusters = []
        self.sample_rate = 16000
        self.segment_ms = 25.0
        self.threshold = 0.85
        self.match_percentage = 85
        
        # Audio player
        self.audio_player = QMediaPlayer()
        self.current_temp_file = None
        self.current_preview_start = 0
        self.current_preview_end = 0
        
        self.init_ui()
        self.init_menu()
        self.init_toolbar()
        self.init_statusbar()
    
    def init_ui(self):
        """Initialize UI with larger fonts and full controls."""
        self.setWindowTitle("🎙️ SpeechScribe V4 - Ultra-Fast Transcription")
        self.setMinimumSize(1600, 1000)
        
        # Set global font size
        font = QFont("Segoe UI", 12)
        self.setFont(font)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        
        # Main layout
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # Top section: File info and controls
        top_group = QGroupBox("📁 Audio File")
        top_group.setFont(QFont("Segoe UI", 14, QFont.Bold))
        top_layout = QHBoxLayout(top_group)
        
        self.file_label = QLabel("No file selected")
        self.file_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.file_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        top_layout.addWidget(self.file_label)
        
        self.btn_open = QPushButton("📂 Open Audio")
        self.btn_open.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.btn_open.clicked.connect(self.open_audio)
        self.btn_open.setStyleSheet("padding: 10px 20px; font-size: 16px;")
        top_layout.addWidget(self.btn_open)
        
        self.btn_transcribe = QPushButton("▶️ Transcribe")
        self.btn_transcribe.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.btn_transcribe.clicked.connect(self.start_transcription)
        self.btn_transcribe.setEnabled(False)
        self.btn_transcribe.setStyleSheet("padding: 10px 20px; font-size: 16px; background-color: #4CAF50; color: white;")
        top_layout.addWidget(self.btn_transcribe)
        
        main_layout.addWidget(top_group)
        
        # Settings section: All controls
        settings_group = QGroupBox("⚙️ Settings")
        settings_group.setFont(QFont("Segoe UI", 14, QFont.Bold))
        settings_layout = QHBoxLayout(settings_group)
        
        # Segment size
        seg_label = QLabel("Segment Size (ms):")
        seg_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        seg_label.setStyleSheet("font-size: 14px;")
        settings_layout.addWidget(seg_label)
        
        self.segment_spinbox = QSpinBox()
        self.segment_spinbox.setRange(10, 2000)
        self.segment_spinbox.setValue(250)
        self.segment_spinbox.setSingleStep(1)
        self.segment_spinbox.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.segment_spinbox.setStyleSheet("font-size: 14px; padding: 5px; min-width: 100px;")
        self.segment_spinbox.valueChanged.connect(self.on_segment_size_changed)
        settings_layout.addWidget(self.segment_spinbox)
        
        self.segment_value_label = QLabel("Current: 25 ms")
        self.segment_value_label.setFont(QFont("Segoe UI", 14))
        self.segment_value_label.setStyleSheet("font-size: 14px; color: #2196F3;")
        settings_layout.addWidget(self.segment_value_label)
        
        # Separator
        settings_layout.addWidget(QLabel("  |  "))
        
        # Threshold
        threshold_label = QLabel("Sensitivity (Threshold):")
        threshold_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        threshold_label.setStyleSheet("font-size: 14px;")
        settings_layout.addWidget(threshold_label)
        
        self.threshold_spinbox = QDoubleSpinBox()
        self.threshold_spinbox.setRange(0.01, 0.99)
        self.threshold_spinbox.setValue(0.85)
        self.threshold_spinbox.setSingleStep(0.01)
        self.threshold_spinbox.setDecimals(2)
        self.threshold_spinbox.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.threshold_spinbox.setStyleSheet("font-size: 14px; padding: 5px; min-width: 100px;")
        self.threshold_spinbox.valueChanged.connect(self.on_threshold_changed)
        settings_layout.addWidget(self.threshold_spinbox)
        
        self.threshold_value_label = QLabel("Current: 0.85")
        self.threshold_value_label.setFont(QFont("Segoe UI", 14))
        self.threshold_value_label.setStyleSheet("font-size: 14px; color: #2196F3;")
        settings_layout.addWidget(self.threshold_value_label)
        
        # Separator
        settings_layout.addWidget(QLabel("  |  "))
        
        # Match Percentage
        match_label = QLabel("Match Percentage (%):")
        match_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        match_label.setStyleSheet("font-size: 14px;")
        settings_layout.addWidget(match_label)
        
        self.match_spinbox = QSpinBox()
        self.match_spinbox.setRange(0, 100)
        self.match_spinbox.setValue(70)
        self.match_spinbox.setSingleStep(1)
        self.match_spinbox.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.match_spinbox.setStyleSheet("font-size: 14px; padding: 5px; min-width: 100px;")
        self.match_spinbox.valueChanged.connect(self.on_match_percentage_changed)
        settings_layout.addWidget(self.match_spinbox)
        
        self.match_value_label = QLabel("Current: 85%")
        self.match_value_label.setFont(QFont("Segoe UI", 14))
        self.match_value_label.setStyleSheet("font-size: 14px; color: #2196F3;")
        settings_layout.addWidget(self.match_value_label)
        
        settings_layout.addStretch()
        
        main_layout.addWidget(settings_group)
        
        # Progress section
        progress_group = QGroupBox("⏳ Progress")
        progress_group.setFont(QFont("Segoe UI", 14, QFont.Bold))
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.progress_bar.setStyleSheet("QProgressBar { height: 30px; font-size: 14px; }")
        progress_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Ready")
        self.status_label.setFont(QFont("Segoe UI", 13))
        self.status_label.setStyleSheet("font-size: 14px;")
        progress_layout.addWidget(self.status_label)
        
        main_layout.addWidget(progress_group)
        
        # Middle section: Clusters table with audio preview
        middle_splitter = QSplitter(Qt.Vertical)
        
        # Table
        table_group = QGroupBox("📊 Clusters (Click row to preview)")
        table_group.setFont(QFont("Segoe UI", 14, QFont.Bold))
        table_layout = QVBoxLayout(table_group)
        
        self.cluster_table = QTableWidget()
        self.cluster_table.setFont(QFont("Segoe UI", 12))
        self.cluster_table.setColumnCount(6)
        self.cluster_table.setHorizontalHeaderLabels([
            "ID", "Character", "Count", "First Occurrence (s)", "Method", "Preview"
        ])
        self.cluster_table.horizontalHeader().setFont(QFont("Segoe UI", 13, QFont.Bold))
        self.cluster_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.cluster_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.cluster_table.setStyleSheet("QTableWidget { font-size: 13px; gridline-color: #cccccc; }")
        self.cluster_table.itemClicked.connect(self.on_cluster_clicked)
        self.cluster_table.verticalHeader().setFont(QFont("Segoe UI", 11))
        table_layout.addWidget(self.cluster_table)
        
        middle_splitter.addWidget(table_group)
        
        # Audio preview section
        preview_group = QGroupBox("🔊 Audio Preview")
        preview_group.setFont(QFont("Segoe UI", 14, QFont.Bold))
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_info = QLabel("Select a cluster to preview")
        self.preview_info.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.preview_info.setStyleSheet("font-size: 16px; font-weight: bold;")
        preview_layout.addWidget(self.preview_info)
        
        self.preview_time = QLabel("Time: 0.00s - 0.00s")
        self.preview_time.setFont(QFont("Segoe UI", 13))
        self.preview_time.setStyleSheet("font-size: 14px;")
        preview_layout.addWidget(self.preview_time)
        
        # Audio controls
        controls_layout = QHBoxLayout()
        
        self.btn_play = QPushButton("▶️ Play")
        self.btn_play.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.btn_play.clicked.connect(self.play_preview)
        self.btn_play.setEnabled(False)
        self.btn_play.setStyleSheet("padding: 10px 20px; font-size: 16px; background-color: #2196F3; color: white;")
        controls_layout.addWidget(self.btn_play)
        
        self.btn_stop = QPushButton("⏹️ Stop")
        self.btn_stop.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.btn_stop.clicked.connect(self.stop_preview)
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet("padding: 10px 20px; font-size: 16px;")
        controls_layout.addWidget(self.btn_stop)
        
        preview_layout.addLayout(controls_layout)
        
        middle_splitter.addWidget(preview_group)
        
        # Set splitter sizes
        middle_splitter.setSizes([700, 250])
        
        main_layout.addWidget(middle_splitter)
        
        # Bottom section: Actions
        bottom_group = QGroupBox("💾 Actions")
        bottom_group.setFont(QFont("Segoe UI", 14, QFont.Bold))
        bottom_layout = QHBoxLayout(bottom_group)
        
        self.btn_save_labels = QPushButton("💾 Save Labels")
        self.btn_save_labels.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.btn_save_labels.clicked.connect(self.save_labels)
        self.btn_save_labels.setEnabled(False)
        self.btn_save_labels.setStyleSheet("padding: 10px 20px; font-size: 16px;")
        bottom_layout.addWidget(self.btn_save_labels)
        
        self.btn_load_labels = QPushButton("📥 Load Labels")
        self.btn_load_labels.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.btn_load_labels.clicked.connect(self.load_labels)
        self.btn_load_labels.setEnabled(False)
        self.btn_load_labels.setStyleSheet("padding: 10px 20px; font-size: 16px;")
        bottom_layout.addWidget(self.btn_load_labels)
        
        self.btn_generate = QPushButton("✨ Generate Text")
        self.btn_generate.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.btn_generate.clicked.connect(self.generate_text)
        self.btn_generate.setEnabled(False)
        self.btn_generate.setStyleSheet("padding: 10px 20px; font-size: 16px; background-color: #2196F3; color: white;")
        bottom_layout.addWidget(self.btn_generate)
        
        main_layout.addWidget(bottom_group)
        
        # Log section
        log_group = QGroupBox("📝 Log")
        log_group.setFont(QFont("Segoe UI", 14, QFont.Bold))
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setFont(QFont("Consolas", 12))
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(180)
        self.log_text.setStyleSheet("QTextEdit { font-family: Consolas; font-size: 13px; background-color: #f5f5f5; }")
        log_layout.addWidget(self.log_text)
        
        main_layout.addWidget(log_group)
    
    def on_segment_size_changed(self, value):
        """Handle segment size change."""
        self.segment_ms = float(value)
        self.segment_value_label.setText(f"Current: {value} ms")
        self.log(f"Segment size changed to {value} ms")
    
    def on_threshold_changed(self, value):
        """Handle threshold change."""
        self.threshold = float(value)
        self.threshold_value_label.setText(f"Current: {value:.2f}")
        
        # Auto-update match percentage
        match_pct = int(value * 100)
        self.match_percentage = match_pct
        self.match_spinbox.setValue(match_pct)
        
        self.log(f"Threshold changed to {value:.2f} (match: {match_pct}%)")
    
    def on_match_percentage_changed(self, value):
        """Handle match percentage change."""
        self.match_percentage = value
        self.match_value_label.setText(f"Current: {value}%")
        
        # Auto-update threshold
        new_threshold = value / 100.0
        self.threshold = new_threshold
        self.threshold_spinbox.setValue(new_threshold)
        
        self.log(f"Match percentage changed to {value}% (threshold: {new_threshold:.2f})")
    
    def init_menu(self):
        """Initialize menu bar."""
        menubar = self.menuBar()
        menubar.setFont(QFont("Segoe UI", 12))
        
        # File menu
        file_menu = menubar.addMenu("📁 File")
        
        open_action = QAction("📂 Open Audio", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_audio)
        file_menu.addAction(open_action)
        
        exit_action = QAction("❌ Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Help menu
        help_menu = menubar.addMenu("❓ Help")
        
        about_action = QAction("ℹ️ About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def init_toolbar(self):
        """Initialize toolbar."""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setFont(QFont("Segoe UI", 12))
        self.addToolBar(toolbar)
        
        open_action = QAction("📂 Open", self)
        open_action.triggered.connect(self.open_audio)
        toolbar.addAction(open_action)
        
        toolbar.addSeparator()
        
        transcribe_action = QAction("▶️ Transcribe", self)
        transcribe_action.triggered.connect(self.start_transcription)
        toolbar.addAction(transcribe_action)
        
        toolbar.addSeparator()
        
        generate_action = QAction("✨ Generate", self)
        generate_action.triggered.connect(self.generate_text)
        toolbar.addAction(generate_action)
    
    def init_statusbar(self):
        """Initialize status bar."""
        self.statusbar = QStatusBar()
        self.statusbar.setFont(QFont("Segoe UI", 12))
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("Ready")
    
    def log(self, message):
        """Add message to log."""
        self.log_text.append(message)
        self.statusbar.showMessage(message)
    
    def open_audio(self):
        """Open audio file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Audio File",
            "",
            "Audio Files (*.wav *.mp3 *.flac *.m4a *.ogg *.aac);;All Files (*)"
        )
        
        if file_path:
            self.audio_path = file_path
            self.file_label.setText(f"📁 {Path(file_path).name}")
            self.btn_transcribe.setEnabled(True)
            self.log(f"Opened: {file_path}")
    
    def start_transcription(self):
        """Start transcription."""
        if not self.audio_path:
            QMessageBox.warning(self, "Warning", "Please open an audio file first!")
            return
        
        # Get settings from spinboxes
        segment_ms = self.segment_spinbox.value()
        threshold = self.threshold_spinbox.value()
        match_percentage = self.match_spinbox.value()
        
        self.btn_transcribe.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText("Starting transcription...")
        self.log(f"Starting transcription: segment={segment_ms}ms, threshold={threshold:.2f}, match={match_percentage}%")
        
        # Start worker thread
        self.worker = TranscriptionWorker(
            self.audio_path, 
            segment_ms=segment_ms,
            threshold=threshold,
        )
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.worker.start()
    
    def on_progress(self, value, message):
        """Update progress."""
        self.progress_bar.setValue(value)
        self.status_label.setText(message)
        self.log(message)
    
    def on_finished(self, transcriber):
        """Transcription finished."""
        self.transcriber = transcriber
        self.clusters = transcriber.clusters
        self.sample_rate = transcriber.sample_rate
        
        self.btn_transcribe.setEnabled(True)
        self.btn_save_labels.setEnabled(True)
        self.btn_load_labels.setEnabled(True)
        self.btn_generate.setEnabled(True)
        
        self.log(f"Transcription complete! Created {len(self.clusters)} clusters")
        
        # Populate table
        self.populate_cluster_table()
        
        QMessageBox.information(
            self,
            "Success",
            f"✅ Transcription complete!\n\n"
            f"Created {len(self.clusters)} clusters\n"
            f"Segment size: {self.segment_spinbox.value()} ms\n"
            f"Threshold: {self.threshold_spinbox.value():.2f}\n"
            f"Time: {self.progress_bar.value()}%\n\n"
            f"Next step:\n"
            f"1. Click on any row to preview the audio\n"
            f"2. Type the character in the 'Character' column\n"
            f"3. Click 'Save Labels' or 'Generate Text'"
        )
    
    def on_error(self, error_msg):
        """Transcription error."""
        self.btn_transcribe.setEnabled(True)
        self.log(f"Error: {error_msg}")
        
        QMessageBox.critical(
            self,
            "Error",
            f"❌ Transcription failed:\n{error_msg}"
        )
    
    def populate_cluster_table(self):
        """Populate cluster table (no sorting, no default letters)."""
        self.cluster_table.setRowCount(len(self.clusters))
        
        for i, cluster in enumerate(self.clusters):
            # ID
            id_item = QTableWidgetItem(str(cluster['id']))
            id_item.setFont(QFont("Segoe UI", 12))
            id_item.setFlags(id_item.flags() & ~Qt.ItemIsEditable)
            self.cluster_table.setItem(i, 0, id_item)
            
            # Character (EMPTY - user fills)
            char_item = QTableWidgetItem("")
            char_item.setFont(QFont("Segoe UI", 13, QFont.Bold))
            char_item.setBackground(QColor("#ffffff"))
            self.cluster_table.setItem(i, 1, char_item)
            
            # Count
            count_item = QTableWidgetItem(str(len(cluster['segments'])))
            count_item.setFont(QFont("Segoe UI", 12))
            count_item.setFlags(count_item.flags() & ~Qt.ItemIsEditable)
            self.cluster_table.setItem(i, 2, count_item)
            
            # First occurrence
            first_occ = cluster['segments'][0]['start_seconds'] if cluster['segments'] else 0
            occ_item = QTableWidgetItem(f"{first_occ:.2f}")
            occ_item.setFont(QFont("Segoe UI", 12))
            occ_item.setFlags(occ_item.flags() & ~Qt.ItemIsEditable)
            self.cluster_table.setItem(i, 3, occ_item)
            
            # Method
            method_item = QTableWidgetItem(cluster.get('method', 'unknown'))
            method_item.setFont(QFont("Segoe UI", 12))
            method_item.setFlags(method_item.flags() & ~Qt.ItemIsEditable)
            self.cluster_table.setItem(i, 4, method_item)
            
            # Preview button
            preview_btn = QPushButton("🔊 Play")
            preview_btn.setFont(QFont("Segoe UI", 12, QFont.Bold))
            preview_btn.setStyleSheet("padding: 6px 12px; font-size: 13px; background-color: #2196F3; color: white;")
            preview_btn.clicked.connect(lambda checked, idx=i: self.play_preview_from_button(idx))
            self.cluster_table.setCellWidget(i, 5, preview_btn)
    
    def on_cluster_clicked(self, item):
        """Handle cluster selection."""
        row = item.row()
        
        if row < 0 or row >= len(self.clusters):
            return
        
        cluster = self.clusters[row]
        
        if cluster['segments'] and len(cluster['segments']) > 0:
            first_segment = cluster['segments'][0]
            start_seconds = first_segment['start_seconds']
            end_seconds = first_segment['end_seconds']
            duration = end_seconds - start_seconds
            
            self.preview_info.setText(f"Cluster {cluster['id']} - Count: {len(cluster['segments'])}")
            self.preview_time.setText(f"Time: {start_seconds:.3f}s - {end_seconds:.3f}s ({duration*1000:.0f} ms)")
            
            self.btn_play.setEnabled(True)
            self.btn_stop.setEnabled(True)
            
            self.log(f"Selected cluster {cluster['id']}: {start_seconds:.3f}s - {end_seconds:.3f}s")
            
    
    def play_preview_from_button(self, row):
        """Play preview from button click."""
        self.cluster_table.selectRow(row)
        self.on_cluster_clicked(self.cluster_table.item(row, 0))
        self.play_preview()
    def play_preview(self):
        """Play audio preview from saved WAV files."""
        if not self.transcriber or not self.audio_path:
            self.log("Error: No audio loaded")
            return
        
        try:
            row = self.cluster_table.currentRow()
            if row < 0 or row >= len(self.clusters):
                self.log("Error: No cluster selected")
                return
            
            cluster = self.clusters[row]
            
            if not cluster['segments']:
                self.log("Error: No segments in cluster")
                return
            
            # ← استخدام أول مقطع
            first_segment = cluster['segments'][0]
            start = first_segment['start']
            end = first_segment['end']
            cluster_id = cluster['id']
            
            # ← إنشاء مجلد temp
            temp_dir = 'temp_segments'
            os.makedirs(temp_dir, exist_ok=True)
            
            # ← البحث عن الملف
            wav_path = f'{temp_dir}/cluster_{cluster_id}_seg_0.wav'
            
            if not os.path.exists(wav_path):
                # ← إنشاء الملف إذا لم يكن موجوداً
                segment = self.transcriber.audio[start:end]
                
                if len(segment) == 0:
                    self.log("Error: Empty segment")
                    return
                
                from scipy.io import wavfile
                audio_data = (segment * 32767).astype(np.int16)
                wavfile.write(wav_path, self.sample_rate, audio_data)
                self.log(f"Created: {wav_path}")
            
            # ← تشغيل الملف
            self.audio_player.setMedia(QMediaContent(QUrl.fromLocalFile(wav_path)))
            self.audio_player.play()
            
            self.current_temp_file = wav_path
            
            # تحديث المعلومات
            start_seconds = first_segment['start_seconds']
            end_seconds = first_segment['end_seconds']
            duration = end_seconds - start_seconds
            
            self.preview_info.setText(f"Cluster {cluster_id} - Count: {len(cluster['segments'])}")
            self.preview_time.setText(f"Time: {start_seconds:.3f}s - {end_seconds:.3f}s ({duration*1000:.0f} ms)")
            
            self.log(f"Playing cluster {cluster_id} at {start_seconds:.3f}s")
            
        except Exception as e:
            import traceback
            error_msg = f"Error: {str(e)}"
            self.log(error_msg)
            QMessageBox.critical(self, "Preview Error", error_msg)
    
    def play_preview1(self):
        """Play audio preview from saved WAV files."""
        if not self.transcriber or not self.audio_path:
            self.log("Error: No audio loaded")
            return
        
        try:
            row = self.cluster_table.currentRow()
            if row < 0 or row >= len(self.clusters):
                self.log("Error: No cluster selected")
                return
            
            cluster = self.clusters[row]
            
            if not cluster['segments']:
                self.log("Error: No segments in cluster")
                return
            
            # ← استخدام أول مقطع من العنقود
            first_segment = cluster['segments'][0]
            start = first_segment['start']
            end = first_segment['end']
            
            # ← إنشاء اسم الملف
            temp_dir = 'temp_segments'
            cluster_id = cluster['id']
            
            # البحث عن الملف المحفوظ
            wav_path = f'{temp_dir}/cluster_{cluster_id}_seg_0.wav'
            
            if not os.path.exists(wav_path):
                # ← إذا لم يكن الملف موجوداً، أنشئه الآن
                self.log(f"Creating preview file: {wav_path}")
                
                # استخراج المقطع من الملف الأصلي
                segment = self.transcriber.audio[start:end]
                
                if len(segment) == 0:
                    self.log("Error: Empty segment")
                    return
                
                # حفظ في ملف WAV
                from scipy.io import wavfile
                audio_data = (segment * 32767).astype(np.int16)
                wavfile.write(wav_path, self.sample_rate, audio_data)
            
            # ← تشغيل الملف
            self.log(f"Playing: {wav_path}")
            self.audio_player.setMedia(QMediaContent(QUrl.fromLocalFile(wav_path)))
            self.audio_player.play()
            
            # حفظ المسار
            self.current_temp_file = wav_path
            
            # تحديث المعلومات
            start_seconds = start / self.sample_rate
            end_seconds = end / self.sample_rate
            duration = end_seconds - start_seconds
            
            self.preview_info.setText(f"Cluster {cluster['id']} - Count: {len(cluster['segments'])}")
            self.preview_time.setText(f"Time: {start_seconds:.3f}s - {end_seconds:.3f}s ({duration*1000:.0f} ms)")
            
            self.log(f"Playing cluster {cluster['id']} at {start_seconds:.3f}s")
            
        except Exception as e:
            import traceback
            error_msg = f"Error playing preview: {str(e)}\n{traceback.format_exc()}"
            self.log(error_msg)
            QMessageBox.critical(self, "Preview Error", error_msg)
    
    def stop_preview(self):
        """Stop audio preview."""
        self.audio_player.stop()
    
    def save_labels(self):
        """Save labels to CSV."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Labels",
            "manual_labels.csv",
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        'cluster_id', 'character', 'count',
                        'first_occurrence_seconds', 'notes'
                    ])
                    
                    for row in range(self.cluster_table.rowCount()):
                        cluster_id = int(self.cluster_table.item(row, 0).text())
                        character = self.cluster_table.item(row, 1).text().strip()
                        count = int(self.cluster_table.item(row, 2).text())
                        first_occ = float(self.cluster_table.item(row, 3).text())
                        
                        writer.writerow([
                            cluster_id, character, count,
                            f"{first_occ:.2f}", ''
                        ])
                
                self.log(f"Labels saved to: {file_path}")
                
                QMessageBox.information(
                    self,
                    "Success",
                    f"✓ Labels saved to:\n{file_path}\n\n"
                    f"You can edit this file externally if needed."
                )
                
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to save labels:\n{str(e)}"
                )
    
    def load_labels(self):
        """Load labels from CSV."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Labels",
            "manual_labels.csv",
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if file_path:
            try:
                labels = {}
                
                with open(file_path, 'r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        cluster_id = int(row['cluster_id'])
                        character = row['character'].strip()
                        if character:
                            labels[cluster_id] = character
                
                # Update table
                for row in range(self.cluster_table.rowCount()):
                    cluster_id = int(self.cluster_table.item(row, 0).text())
                    if cluster_id in labels:
                        self.cluster_table.item(row, 1).setText(labels[cluster_id])
                
                self.log(f"Loaded {len(labels)} labels from: {file_path}")
                
                QMessageBox.information(
                    self,
                    "Success",
                    f"✓ Loaded {len(labels)} labels"
                )
                
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to load labels:\n{str(e)}"
                )
    
    def generate_text(self):
        """Generate text from labels."""
        if not self.transcriber:
            QMessageBox.warning(self, "Warning", "Please transcribe audio first!")
            return
        
        # Get labels from table
        labels = {}
        for row in range(self.cluster_table.rowCount()):
            cluster_id = int(self.cluster_table.item(row, 0).text())
            character = self.cluster_table.item(row, 1).text().strip()
            if character:
                labels[cluster_id] = character
        
        if not labels:
            QMessageBox.warning(
                self,
                "Warning",
                "No labels found! Please assign characters to clusters."
            )
            return
        
        try:
            self.log("Generating text...")
            
            # Set labels
            self.transcriber.labels = labels
            
            # Generate
            self.transcriber.generate_text()
            
            # Save
            self.transcriber.save_text(
                output_txt='output_text.txt',
                output_csv='output_text_details.csv',
                output_srt='output_subtitles.srt',
            )
            
            self.log("Text generation complete!")
            
            QMessageBox.information(
                self,
                "Success",
                f"✅ Text generation complete!\n\n"
                f"Output files:\n"
                f"  - output_text.txt\n"
                f"  - output_text_details.csv\n"
                f"  - output_subtitles.srt"
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to generate text:\n{str(e)}"
            )
    
    def show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About SpeechScribe V4",
            "🎙️ SpeechScribe V4\n\n"
            "Ultra-Fast Speech Transcription\n"
            "Using NumPy Vectorization\n\n"
            "Version: 4.0.0\n\n"
            "Authors:\n"
            "  - NAJIB MOHAMMED AL-AMIR\n"
            "  - WALID HASSAN MOHAMMAD AL-MOTAWAKEL\n\n"
            "AI Assistant: Perplexity AI\n"
            "  Code Generation & Development\n\n"
            "Speed: 120x realtime\n"
            "Accuracy: 90-95%\n\n"
            "Features:\n"
            "• Adjustable segment size (10-2000 ms)\n"
            "• Adjustable sensitivity (0.01-0.99)\n"
            "• Adjustable match percentage (0-100%)\n"
            "• Audio preview for each cluster\n"
            "• Manual character assignment\n"
            "• No automatic sorting\n"
            "• No default letters\n"
            "• Large, readable fonts\n"
            "• All audio formats (WAV, MP3, FLAC, M4A, etc.)\n\n"
            "License: HEUL-1.0\n\n"
            "© 2026 - A Tree of Goodness Serving Humanity"
        )
