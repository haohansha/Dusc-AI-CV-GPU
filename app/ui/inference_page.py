from pathlib import Path

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QComboBox, QLabel, QSlider, QRadioButton, QButtonGroup,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter, QSpinBox,
    QFileDialog, QMessageBox, QAbstractItemView, QApplication)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap
import cv2

from modules.inference_engine import InferenceConfig


class InferencePage(QWidget):
    def __init__(self, project_root, inference_engine, model_manager, dataset_manager):
        super().__init__()
        self._project_root = Path(project_root)
        self._inference_engine = inference_engine
        self._model_manager = model_manager
        self._dataset_manager = dataset_manager
        self._stop_requested = False
        self._setup_ui()
        self._refresh_models()
        self._populate_media()

    def _setup_ui(self):
        splitter = QSplitter(Qt.Horizontal)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        model_group = QGroupBox("模型选择")
        model_layout = QVBoxLayout(model_group)
        self._model_combo = QComboBox()
        model_layout.addWidget(self._model_combo)
        left_layout.addWidget(model_group)

        source_group = QGroupBox("输入源")
        source_layout = QVBoxLayout(source_group)

        self._source_group = QButtonGroup(self)
        self._radio_image = QRadioButton("图片")
        self._radio_video = QRadioButton("视频")
        self._radio_camera = QRadioButton("摄像头")
        self._radio_image.setChecked(True)
        self._source_group.addButton(self._radio_image, 0)
        self._source_group.addButton(self._radio_video, 1)
        self._source_group.addButton(self._radio_camera, 2)

        rb_layout = QHBoxLayout()
        rb_layout.addWidget(self._radio_image)
        rb_layout.addWidget(self._radio_video)
        rb_layout.addWidget(self._radio_camera)
        source_layout.addLayout(rb_layout)

        self._media_combo = QComboBox()
        source_layout.addWidget(self._media_combo)

        browse_row = QHBoxLayout()
        self._browse_btn = QPushButton("浏览文件")
        self._browse_btn.clicked.connect(self._on_browse)
        browse_row.addWidget(self._browse_btn)
        self._camera_spin = QSpinBox()
        self._camera_spin.setRange(0, 99)
        self._camera_spin.setValue(0)
        self._camera_spin.setVisible(False)
        browse_row.addWidget(self._camera_spin)
        browse_row.addStretch()
        source_layout.addLayout(browse_row)

        self._source_group.buttonClicked.connect(self._on_source_changed)
        left_layout.addWidget(source_group)

        param_group = QGroupBox("参数")
        param_layout = QVBoxLayout(param_group)
        conf_row = QHBoxLayout()
        conf_row.addWidget(QLabel("置信度阈值"))
        self._conf_slider = QSlider(Qt.Horizontal)
        self._conf_slider.setRange(0, 100)
        self._conf_slider.setValue(25)
        conf_row.addWidget(self._conf_slider)
        self._conf_label = QLabel("0.25")
        conf_row.addWidget(self._conf_label)
        self._conf_slider.valueChanged.connect(self._on_conf_changed)
        param_layout.addLayout(conf_row)
        left_layout.addWidget(param_group)

        ctrl_group = QGroupBox("控制")
        ctrl_layout = QHBoxLayout(ctrl_group)
        self._start_btn = QPushButton("开始检测")
        self._start_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 6px 16px; }"
        )
        self._start_btn.clicked.connect(self._on_start)
        ctrl_layout.addWidget(self._start_btn)
        self._stop_btn = QPushButton("停止检测")
        self._stop_btn.setEnabled(False)
        self._stop_btn.setStyleSheet(
            "QPushButton { background-color: #F44336; color: white; font-weight: bold; padding: 6px 16px; }"
        )
        self._stop_btn.clicked.connect(self._on_stop)
        ctrl_layout.addWidget(self._stop_btn)
        left_layout.addWidget(ctrl_group)

        left_layout.addStretch()
        splitter.addWidget(left_panel)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        preview_group = QGroupBox("检测画面")
        preview_layout = QVBoxLayout(preview_group)
        self._preview_label = QLabel()
        self._preview_label.setMinimumSize(640, 480)
        self._preview_label.setAlignment(Qt.AlignCenter)
        self._preview_label.setStyleSheet(
            "QLabel { border: 1px solid #cccccc; background-color: #f5f5f5; }"
        )
        self._preview_label.setText("请选择模型和输入源，点击开始检测")
        preview_layout.addWidget(self._preview_label)
        right_layout.addWidget(preview_group, stretch=3)

        results_group = QGroupBox("检测结果")
        results_layout = QVBoxLayout(results_group)
        self._results_table = QTableWidget()
        self._results_table.setColumnCount(4)
        self._results_table.setHorizontalHeaderLabels(
            ["类别", "置信度", "位置(x1,y1,x2,y2)", "面积占比"]
        )
        self._results_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._results_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        header = self._results_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        results_layout.addWidget(self._results_table)
        self._stats_label = QLabel("总帧数: 0 | 平均FPS: 0 | 总检测数: 0")
        results_layout.addWidget(self._stats_label)
        right_layout.addWidget(results_group, stretch=2)

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 7)
        splitter.setSizes([300, 800])

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(splitter)

    def _refresh_models(self):
        self._model_combo.clear()
        models = self._model_manager.list_models()
        for m in models:
            self._model_combo.addItem(m.name, m.path)

    def _on_source_changed(self, button):
        source_id = self._source_group.id(button)
        if source_id == 2:
            self._media_combo.setEnabled(False)
            self._browse_btn.setEnabled(False)
            self._camera_spin.setVisible(True)
        else:
            self._media_combo.setEnabled(True)
            self._browse_btn.setEnabled(True)
            self._camera_spin.setVisible(False)
            self._populate_media()

    def _populate_media(self):
        self._media_combo.clear()
        source_id = self._source_group.checkedId()
        if source_id == 0:
            media_type = "image"
        elif source_id == 1:
            media_type = "video"
        else:
            return
        media_list = self._dataset_manager.list_media()
        for media in media_list:
            if media.media_type == media_type:
                self._media_combo.addItem(media.name, media.path)

    def _on_conf_changed(self, value):
        self._conf_label.setText(f"{value / 100:.2f}")

    def _resolve_media_path(self, media_path):
        if not media_path:
            return None
        p = Path(media_path)
        if p.is_absolute():
            return str(p)
        return str(self._project_root / p)

    def _on_browse(self):
        source_id = self._source_group.checkedId()
        if source_id == 0:
            title = "选择图片"
            filter_str = "图片文件 (*.jpg *.jpeg *.png *.bmp);;所有文件 (*.*)"
        else:
            title = "选择视频"
            filter_str = "视频文件 (*.mp4 *.avi *.mov *.mkv);;所有文件 (*.*)"

        file_path, _ = QFileDialog.getOpenFileName(self, title, "", filter_str)
        if not file_path:
            return
        self._media_combo.addItem(Path(file_path).name, file_path)
        self._media_combo.setCurrentIndex(self._media_combo.count() - 1)

    def _get_conf(self):
        return self._conf_slider.value() / 100.0

    def _on_start(self):
        model_path = self._model_combo.currentData()
        if not model_path:
            QMessageBox.warning(self, "提示", "请先选择一个模型")
            return

        source_id = self._source_group.checkedId()
        conf = self._get_conf()

        self._stop_requested = False
        self._start_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)

        try:
            if source_id == 0:
                self._run_image(model_path, conf)
            elif source_id == 1:
                self._run_video(model_path, conf)
            else:
                self._run_camera(model_path, conf)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"检测失败: {str(e)}")
        finally:
            self._start_btn.setEnabled(True)
            self._stop_btn.setEnabled(False)

    def _run_image(self, model_path, conf):
        media_path = self._media_combo.currentData()
        if not media_path:
            QMessageBox.warning(self, "提示", "请选择一张图片")
            return

        full_path = self._resolve_media_path(media_path)
        if full_path is None or not Path(full_path).exists():
            QMessageBox.warning(self, "错误", f"文件不存在: {full_path}")
            return

        frame = cv2.imread(full_path)
        if frame is None:
            QMessageBox.warning(self, "错误", f"无法读取图片: {full_path}")
            return

        model = self._inference_engine._load_model(model_path)
        annotated_frame, detections, inference_ms = self._inference_engine.process_frame(frame, model, conf)

        self._display_frame(annotated_frame)
        self._update_results_table(detections)
        fps = 1000 / inference_ms if inference_ms > 0 else 0
        self._stats_label.setText(f"总帧数: 1 | 平均FPS: {fps:.1f} | 总检测数: {len(detections)}")

    def _run_video(self, model_path, conf):
        media_path = self._media_combo.currentData()
        if not media_path:
            QMessageBox.warning(self, "提示", "请选择一个视频")
            return

        full_path = self._resolve_media_path(media_path)
        if full_path is None or not Path(full_path).exists():
            QMessageBox.warning(self, "错误", f"文件不存在: {full_path}")
            return

        last_frame = [None]
        last_detections = [[]]

        def progress_cb(frame_count, total_frames, annotated_frame, detections, inference_ms):
            last_frame[0] = annotated_frame
            last_detections[0] = detections

        stats = self._inference_engine.detect_video(
            full_path, model_path, conf, save=True,
            progress_callback=progress_cb
        )

        if stats is None:
            QMessageBox.warning(self, "错误", f"无法打开视频: {full_path}")
            return

        if last_frame[0] is not None:
            self._display_frame(last_frame[0])
        if last_detections[0]:
            self._update_results_table(last_detections[0])

        self._stats_label.setText(
            f"总帧数: {stats['total_frames']} | "
            f"平均FPS: {stats['avg_fps']:.1f} | "
            f"总检测数: {stats['total_detections']}"
        )

    def _run_camera(self, model_path, conf):
        camera_id = self._camera_spin.value()

        def frame_cb(annotated_frame, detections, avg_fps, inference_ms):
            if self._stop_requested:
                return False
            self._display_frame(annotated_frame)
            self._update_results_table(detections)
            self._stats_label.setText(
                f"摄像头实时 | 平均FPS: {avg_fps:.1f} | 总检测数: {len(detections)}"
            )
            QApplication.processEvents()
            return True

        self._inference_engine.detect_camera(camera_id, model_path, conf, frame_cb)

    def _on_stop(self):
        self._stop_requested = True

    def _display_frame(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_per_line = ch * w
        qt_img = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_img)
        self._preview_label.setPixmap(pixmap.scaled(
            self._preview_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _update_results_table(self, detections):
        self._results_table.setRowCount(0)
        self._results_table.setRowCount(len(detections))
        for row, det in enumerate(detections):
            self._results_table.setItem(row, 0, QTableWidgetItem(det.class_name))
            self._results_table.setItem(row, 1, QTableWidgetItem(f"{det.confidence * 100:.1f}%"))
            x1, y1, x2, y2 = det.bbox
            self._results_table.setItem(row, 2, QTableWidgetItem(f"({int(x1)}, {int(y1)}, {int(x2)}, {int(y2)})"))
            self._results_table.setItem(row, 3, QTableWidgetItem(f"{det.area_pct:.2f}%"))
