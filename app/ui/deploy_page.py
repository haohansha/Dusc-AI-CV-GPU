from pathlib import Path
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QComboBox, QLabel, QTextEdit, QSpinBox, QMessageBox,
    QFileDialog, QFormLayout)
from PyQt5.QtCore import Qt
from modules.export_engine import ExportConfig


class DeployPage(QWidget):
    def __init__(self, project_root: Path, export_engine, model_manager):
        super().__init__()
        self._project_root = Path(project_root)
        self._export_engine = export_engine
        self._model_manager = model_manager
        self._setup_ui()
        self._refresh_models()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        layout.addWidget(self._create_model_selection())
        layout.addWidget(self._create_export_options())
        layout.addWidget(self._create_deploy_package())
        layout.addWidget(self._create_deploy_instructions())
        layout.addWidget(self._create_verify())
        layout.addStretch()

    def _create_model_selection(self):
        box = QGroupBox("选择模型")
        box_layout = QVBoxLayout(box)

        self._model_combo = QComboBox()
        box_layout.addWidget(self._model_combo)
        return box

    def _create_export_options(self):
        box = QGroupBox("导出选项")
        box_layout = QVBoxLayout(box)

        btn_row = QHBoxLayout()

        self._export_trt_btn = QPushButton("导出 TensorRT")
        self._export_trt_btn.clicked.connect(self._on_export_tensorrt)
        btn_row.addWidget(self._export_trt_btn)

        self._export_onnx_btn = QPushButton("导出 ONNX")
        self._export_onnx_btn.clicked.connect(self._on_export_onnx)
        btn_row.addWidget(self._export_onnx_btn)

        btn_row.addStretch()
        box_layout.addLayout(btn_row)

        self._advanced_toggle = QPushButton("高级选项 ▼")
        self._advanced_toggle.setCheckable(True)
        self._advanced_toggle.clicked.connect(self._on_toggle_advanced)
        box_layout.addWidget(self._advanced_toggle)

        self._advanced_panel = QWidget()
        self._advanced_panel.setVisible(False)
        adv_layout = QFormLayout(self._advanced_panel)
        adv_layout.setContentsMargins(10, 5, 10, 5)

        self._imgsz_spin = QSpinBox()
        self._imgsz_spin.setRange(320, 1280)
        self._imgsz_spin.setSingleStep(32)
        self._imgsz_spin.setValue(640)
        adv_layout.addRow("输入分辨率：", self._imgsz_spin)

        self._precision_combo = QComboBox()
        self._precision_combo.addItems(["FP16", "INT8"])
        adv_layout.addRow("精度：", self._precision_combo)

        self._workspace_spin = QSpinBox()
        self._workspace_spin.setRange(1, 16)
        self._workspace_spin.setValue(4)
        adv_layout.addRow("Workspace (GB)：", self._workspace_spin)

        box_layout.addWidget(self._advanced_panel)
        return box

    def _create_deploy_package(self):
        box = QGroupBox("生成部署包")
        box_layout = QVBoxLayout(box)

        btn_row = QHBoxLayout()
        self._deploy_btn = QPushButton("生成部署包")
        self._deploy_btn.clicked.connect(self._on_generate_deploy_package)
        btn_row.addWidget(self._deploy_btn)
        btn_row.addStretch()
        box_layout.addLayout(btn_row)

        self._deploy_status_label = QLabel("")
        self._deploy_status_label.setWordWrap(True)
        box_layout.addWidget(self._deploy_status_label)
        return box

    def _create_deploy_instructions(self):
        box = QGroupBox("部署说明")
        box_layout = QVBoxLayout(box)

        self._instructions_edit = QTextEdit()
        self._instructions_edit.setReadOnly(True)
        self._instructions_edit.setMaximumHeight(260)
        self._instructions_edit.setPlainText(
            "=== Jetson Nano/Orin 部署步骤 ===\n"
            "1. 将生成的 deploy_package_xxx.zip 解压到 Jetson 设备\n"
            "2. 运行环境配置: bash setup_jetson.sh\n"
            "3. 测试推理: python3 smoke_detect.py --model models/xxx.engine --video test.mp4\n"
            "4. 生产部署: python3 smoke_detect.py --model models/xxx.engine --rtsp rtsp://摄像头地址\n"
            "\n"
            "=== 支持的模型格式 ===\n"
            "- TensorRT (.engine): 推理速度最快, Jetson 推荐\n"
            "- ONNX (.onnx): 跨平台兼容\n"
            "- PyTorch (.pt): 直接推理, 速度较慢\n"
            "\n"
            "=== 性能参考 (Jetson Orin Nano 8GB) ===\n"
            "- TensorRT FP16: ~60-80 FPS\n"
            "- ONNX Runtime: ~25-40 FPS\n"
            "- PyTorch: ~15-25 FPS"
        )
        box_layout.addWidget(self._instructions_edit)
        return box

    def _create_verify(self):
        box = QGroupBox("验证导出")
        box_layout = QVBoxLayout(box)

        btn_row = QHBoxLayout()
        self._verify_btn = QPushButton("验证导出")
        self._verify_btn.clicked.connect(self._on_verify_export)
        btn_row.addWidget(self._verify_btn)
        btn_row.addStretch()
        box_layout.addLayout(btn_row)

        self._verify_result_label = QLabel("")
        self._verify_result_label.setWordWrap(True)
        box_layout.addWidget(self._verify_result_label)
        return box

    def _get_selected_model_path(self):
        model_name = self._model_combo.currentText()
        if not model_name:
            return None
        for info in self._model_manager.list_models():
            if info.name == model_name:
                return info.path
        return None

    def _refresh_models(self):
        self._model_combo.clear()
        models = self._model_manager.list_models()
        for info in models:
            self._model_combo.addItem(info.name)

    def _build_export_config(self):
        precision = self._precision_combo.currentText()
        return ExportConfig(
            imgsz=self._imgsz_spin.value(),
            half=True,
            int8=(precision == "INT8"),
            workspace=self._workspace_spin.value(),
        )

    def _on_toggle_advanced(self):
        if self._advanced_toggle.isChecked():
            self._advanced_panel.setVisible(True)
            self._advanced_toggle.setText("高级选项 ▲")
        else:
            self._advanced_panel.setVisible(False)
            self._advanced_toggle.setText("高级选项 ▼")

    def _on_export_tensorrt(self):
        model_path = self._get_selected_model_path()
        if not model_path:
            QMessageBox.warning(self, "提示", "请先选择一个模型")
            return

        config = self._build_export_config()
        QMessageBox.information(self, "导出中", "正在导出 TensorRT，请稍候...")

        try:
            result = self._export_engine.export_tensorrt(model_path, config=config)
            if result and result.exists():
                QMessageBox.information(
                    self, "导出成功",
                    f"TensorRT 导出成功:\n{result}"
                )
            else:
                QMessageBox.critical(
                    self, "导出失败",
                    "TensorRT 导出失败，请确认 GPU 支持 TensorRT。"
                )
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出过程发生错误:\n{e}")

    def _on_export_onnx(self):
        model_path = self._get_selected_model_path()
        if not model_path:
            QMessageBox.warning(self, "提示", "请先选择一个模型")
            return

        config = self._build_export_config()
        QMessageBox.information(self, "导出中", "正在导出 ONNX，请稍候...")

        try:
            result = self._export_engine.export_onnx(model_path, config=config)
            if result and result.exists():
                QMessageBox.information(
                    self, "导出成功",
                    f"ONNX 导出成功:\n{result}"
                )
            else:
                QMessageBox.critical(
                    self, "导出失败",
                    "ONNX 导出失败，请检查模型文件是否有效。"
                )
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出过程发生错误:\n{e}")

    def _on_generate_deploy_package(self):
        model_path = self._get_selected_model_path()
        if not model_path:
            QMessageBox.warning(self, "提示", "请先选择一个模型")
            return

        output_dir = str(self._project_root / "deploy")
        QMessageBox.information(self, "生成中", "正在生成部署包，此过程可能需要几分钟，请稍候...")

        try:
            result = self._export_engine.generate_deploy_package(model_path, output_dir)
            if result:
                zip_path, zip_size = result
                size_mb = zip_size / 1024 / 1024
                self._deploy_status_label.setText(
                    f"部署包已生成: {zip_path}\n文件大小: {size_mb:.1f} MB"
                )
                QMessageBox.information(
                    self, "生成成功",
                    f"部署包已生成:\n{zip_path}\n文件大小: {size_mb:.1f} MB"
                )
            else:
                self._deploy_status_label.setText("生成失败")
                QMessageBox.critical(
                    self, "生成失败",
                    "部署包生成失败，请先导出模型。"
                )
        except Exception as e:
            self._deploy_status_label.setText(f"错误: {e}")
            QMessageBox.critical(self, "错误", f"生成部署包时发生错误:\n{e}")

    def _on_verify_export(self):
        model_path = self._get_selected_model_path()
        if not model_path:
            QMessageBox.warning(self, "提示", "请先选择一个模型")
            return

        model_stem = Path(model_path).stem
        models_dir = self._project_root / "models"
        engine_path = models_dir / f"{model_stem}.engine"
        onnx_path = models_dir / f"{model_stem}.onnx"

        results = []
        engine_ok = self._export_engine.verify_export(str(engine_path))
        results.append(f"TensorRT (.engine): {'✓ 有效' if engine_ok else '✗ 不存在或无效'}")

        onnx_ok = self._export_engine.verify_export(str(onnx_path))
        results.append(f"ONNX (.onnx): {'✓ 有效' if onnx_ok else '✗ 不存在或无效'}")

        result_text = "\n".join(results)
        self._verify_result_label.setText(result_text)

        all_ok = engine_ok and onnx_ok
        if all_ok:
            QMessageBox.information(self, "验证结果", f"所有导出文件验证通过:\n{result_text}")
        else:
            QMessageBox.warning(self, "验证结果", f"部分导出文件验证未通过:\n{result_text}")
