from pathlib import Path
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QPushButton, QComboBox, QLabel, QTextEdit, QSpinBox, QMessageBox,
    QFileDialog, QFormLayout, QScrollArea)
from PyQt5.QtCore import Qt

# === 设计系统令牌（与 ai-detection-ui-design/colors_and_type.css 一致）===
COLOR_PRIMARY = "#1B5E3B"
COLOR_PRIMARY_HOVER = "#15713A"
COLOR_PRIMARY_ACTIVE = "#0F5A2E"
COLOR_PRIMARY_LIGHT = "#E8F5EE"
COLOR_BG_BASE = "#F5F6F8"
COLOR_BG_SURFACE = "#FFFFFF"
COLOR_BG_SUNKEN = "#EDF0F3"
COLOR_TEXT_PRIMARY = "#1A1D21"
COLOR_TEXT_SECONDARY = "#5F6368"
COLOR_TEXT_TERTIARY = "#8C9197"
COLOR_BORDER_DEFAULT = "#D5D8DC"
COLOR_STATE_SUCCESS = "#1B7A3D"
COLOR_STATE_SUCCESS_BG = "#E8F5EE"

# 通用样式表
CARD_STYLE = f"""
QFrame#card {{
    background: {COLOR_BG_SURFACE};
    border: 1px solid {COLOR_BORDER_DEFAULT};
    border-radius: 8px;
}}
"""
CARD_TITLE_STYLE = f"""
QLabel#cardTitle {{
    font-size: 38px;
    font-weight: 600;
    color: {COLOR_TEXT_PRIMARY};
    background: transparent;
    border: none;
}}
"""
PRIMARY_BTN_STYLE = f"""
QPushButton {{
    background: {COLOR_PRIMARY};
    color: #FFFFFF;
    border: none;
    border-radius: 2px;
    padding: 0 40px;
    height: 90px;
    font-size: 32px;
    font-weight: 500;
}}
QPushButton:hover {{ background: {COLOR_PRIMARY_HOVER}; }}
QPushButton:pressed {{ background: {COLOR_PRIMARY_ACTIVE}; }}
QPushButton:disabled {{ background: #B0B5BB; }}
"""
OUTLINE_BTN_STYLE = f"""
QPushButton {{
    background: {COLOR_BG_SURFACE};
    color: {COLOR_PRIMARY};
    border: 1px solid {COLOR_PRIMARY};
    border-radius: 2px;
    padding: 0 35px;
    height: 80px;
    font-size: 32px;
    font-weight: 500;
}}
QPushButton:hover {{ background: {COLOR_PRIMARY_LIGHT}; }}
QPushButton:pressed {{ background: {COLOR_PRIMARY_LIGHT}; }}
"""
COMBO_STYLE = f"""
QComboBox {{
    background: {COLOR_BG_SURFACE};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER_DEFAULT};
    border-radius: 2px;
    padding: 0 25px;
    height: 80px;
    font-size: 32px;
}}
QComboBox::drop-down {{ border: none; width: 50px; }}
QComboBox QAbstractItemView {{
    background: {COLOR_BG_SURFACE};
    color: {COLOR_TEXT_PRIMARY};
    selection-background-color: {COLOR_PRIMARY_LIGHT};
    selection-color: {COLOR_PRIMARY};
    border: 1px solid {COLOR_BORDER_DEFAULT};
    font-size: 32px;
}}
"""
SPIN_STYLE = f"""
QSpinBox {{
    background: {COLOR_BG_SURFACE};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER_DEFAULT};
    border-radius: 2px;
    padding: 0 25px;
    height: 80px;
    font-size: 32px;
}}
"""
LABEL_FIELD_STYLE = f"""
QLabel#fieldLabel {{
    font-size: 30px;
    font-weight: 600;
    color: {COLOR_TEXT_SECONDARY};
    background: transparent;
    border: none;
}}
"""
TEXTAREA_STYLE = f"""
QTextEdit {{
    background: {COLOR_BG_SUNKEN};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER_DEFAULT};
    border-radius: 6px;
    padding: 30px;
    font-family: 'JetBrains Mono','Consolas',monospace;
    font-size: 30px;
    line-height: 160%;
}}
"""
ENV_LABEL_STYLE = f"""
QLabel#envInfo {{
    color: {COLOR_PRIMARY};
    font-weight: 600;
    font-size: 32px;
    background: {COLOR_PRIMARY_LIGHT};
    border: 1px solid {COLOR_PRIMARY_LIGHT};
    border-radius: 6px;
    padding: 20px 30px;
}}
"""
SUCCESS_ROW_STYLE = f"""
QFrame#successRow {{
    background: transparent;
    border: none;
    border-bottom: 1px solid #EDF0F3;
}}
"""


def make_card(title: str) -> tuple:
    """创建一个卡片容器，返回 (frame, content_layout)"""
    card = QFrame()
    card.setObjectName("card")
    card.setStyleSheet(CARD_STYLE)
    card_layout = QVBoxLayout(card)
    card_layout.setContentsMargins(40, 40, 40, 40)
    card_layout.setSpacing(30)

    title_label = QLabel(title)
    title_label.setObjectName("cardTitle")
    title_label.setStyleSheet(CARD_TITLE_STYLE)
    card_layout.addWidget(title_label)

    return card, card_layout


class DeployPage(QWidget):
    def __init__(self, project_root: Path, export_engine, model_manager, app_config=None):
        super().__init__()
        self._project_root = Path(project_root)
        self._export_engine = export_engine
        self._model_manager = model_manager
        self._app_config = app_config
        # 从 AppConfig.jetson 读取 Nano 环境参数作为控件初始值
        jetson = (app_config.get("jetson") if app_config else None) or {}
        self._jetson_imgsz = jetson.get("imgsz", 640)
        self._jetson_precision = jetson.get("precision", "FP16")
        self._jetson_workspace = jetson.get("workspace", 4)
        self._jetson_half = jetson.get("half", True)
        self._jetson_info = (
            f"目标 Nano 环境：TensorRT {jetson.get('tensorrt_version', '未知')} / "
            f"Ultralytics {jetson.get('ultralytics_version', '未知')} / "
            f"OpenCV {jetson.get('opencv_version', '未知')}"
        ) if jetson else "目标 Nano 环境：未配置（使用默认值）"
        self._setup_ui()
        self._refresh_models()

    def _setup_ui(self):
        # 外层用滚动区域包裹，背景设为浅灰
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ background: {COLOR_BG_BASE}; border: none; }}")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        content.setStyleSheet(f"background: {COLOR_BG_BASE};")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(30)

        # 顶部 Nano 环境信息条
        env_label = QLabel(self._jetson_info)
        env_label.setObjectName("envInfo")
        env_label.setStyleSheet(ENV_LABEL_STYLE)
        layout.addWidget(env_label)

        # 顶部操作工具栏（导出 TensorRT / 导出 ONNX / 生成部署包）
        toolbar = QHBoxLayout()
        toolbar.setSpacing(20)
        self._export_trt_btn = QPushButton("导出 TensorRT")
        self._export_trt_btn.setStyleSheet(PRIMARY_BTN_STYLE)
        self._export_trt_btn.setCursor(Qt.PointingHandCursor)
        self._export_trt_btn.clicked.connect(self._on_export_tensorrt)
        toolbar.addWidget(self._export_trt_btn)

        self._export_onnx_btn = QPushButton("导出 ONNX")
        self._export_onnx_btn.setStyleSheet(PRIMARY_BTN_STYLE)
        self._export_onnx_btn.setCursor(Qt.PointingHandCursor)
        self._export_onnx_btn.clicked.connect(self._on_export_onnx)
        toolbar.addWidget(self._export_onnx_btn)

        self._deploy_btn = QPushButton("生成部署包")
        self._deploy_btn.setStyleSheet(PRIMARY_BTN_STYLE)
        self._deploy_btn.setCursor(Qt.PointingHandCursor)
        self._deploy_btn.clicked.connect(self._on_generate_deploy_package)
        toolbar.addWidget(self._deploy_btn)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # Card 1: 选择模型
        card1, c1_layout = make_card("选择模型")
        self._model_combo = QComboBox()
        self._model_combo.setStyleSheet(COMBO_STYLE)
        self._model_combo.setCursor(Qt.PointingHandCursor)
        c1_layout.addWidget(self._model_combo)
        layout.addWidget(card1)

        # Card 2: 高级选项（可折叠）
        card2, c2_layout = make_card("高级选项")
        # 折叠按钮
        self._advanced_toggle = QPushButton("▼")
        self._advanced_toggle.setFixedSize(60, 60)
        self._advanced_toggle.setStyleSheet(f"""
            QPushButton {{ background: transparent; border: none; color: {COLOR_TEXT_SECONDARY}; font-size: 35px; }}
            QPushButton:hover {{ color: {COLOR_PRIMARY}; }}
        """)
        self._advanced_toggle.setCheckable(True)
        self._advanced_toggle.clicked.connect(self._on_toggle_advanced)
        # 把折叠按钮放到标题行右侧
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.addStretch()
        title_row.addWidget(self._advanced_toggle)
        c2_layout.addLayout(title_row)

        # 三列：输入分辨率 / 精度 / Workspace
        adv_row = QHBoxLayout()
        adv_row.setSpacing(40)

        # 输入分辨率
        col1 = QVBoxLayout()
        col1.setSpacing(15)
        lbl1 = QLabel("输入分辨率")
        lbl1.setObjectName("fieldLabel")
        lbl1.setStyleSheet(LABEL_FIELD_STYLE)
        col1.addWidget(lbl1)
        self._imgsz_spin = QSpinBox()
        self._imgsz_spin.setRange(320, 1280)
        self._imgsz_spin.setSingleStep(32)
        self._imgsz_spin.setValue(self._jetson_imgsz)
        self._imgsz_spin.setStyleSheet(SPIN_STYLE)
        col1.addWidget(self._imgsz_spin)
        adv_row.addLayout(col1)

        # 精度
        col2 = QVBoxLayout()
        col2.setSpacing(15)
        lbl2 = QLabel("精度")
        lbl2.setObjectName("fieldLabel")
        lbl2.setStyleSheet(LABEL_FIELD_STYLE)
        col2.addWidget(lbl2)
        self._precision_combo = QComboBox()
        self._precision_combo.addItems(["FP16", "FP32", "INT8"])
        idx = self._precision_combo.findText(self._jetson_precision)
        if idx >= 0:
            self._precision_combo.setCurrentIndex(idx)
        self._precision_combo.setStyleSheet(COMBO_STYLE)
        self._precision_combo.setCursor(Qt.PointingHandCursor)
        col2.addWidget(self._precision_combo)
        adv_row.addLayout(col2)

        # Workspace
        col3 = QVBoxLayout()
        col3.setSpacing(15)
        lbl3 = QLabel("Workspace")
        lbl3.setObjectName("fieldLabel")
        lbl3.setStyleSheet(LABEL_FIELD_STYLE)
        col3.addWidget(lbl3)
        self._workspace_combo = QComboBox()
        self._workspace_combo.addItems(["4 GB", "2 GB", "8 GB"])
        ws_idx = self._workspace_combo.findText(f"{self._jetson_workspace} GB")
        if ws_idx >= 0:
            self._workspace_combo.setCurrentIndex(ws_idx)
        self._workspace_combo.setStyleSheet(COMBO_STYLE)
        self._workspace_combo.setCursor(Qt.PointingHandCursor)
        col3.addWidget(self._workspace_combo)
        adv_row.addLayout(col3)

        self._advanced_panel = QWidget()
        self._advanced_panel.setStyleSheet("background: transparent;")
        self._advanced_panel.setLayout(adv_row)
        self._advanced_panel.setVisible(False)
        c2_layout.addWidget(self._advanced_panel)
        layout.addWidget(card2)

        # Card 3: 部署说明
        card3, c3_layout = make_card("部署说明")
        self._instructions_edit = QTextEdit()
        self._instructions_edit.setReadOnly(True)
        self._instructions_edit.setMinimumHeight(350)
        self._instructions_edit.setStyleSheet(TEXTAREA_STYLE)
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
        c3_layout.addWidget(self._instructions_edit)
        layout.addWidget(card3)

        # Card 4: 验证导出
        card4, c4_layout = make_card("验证导出")
        # 标题行右侧的"验证导出"按钮
        verify_title_row = QHBoxLayout()
        verify_title_row.addStretch()
        self._verify_btn = QPushButton("验证导出")
        self._verify_btn.setStyleSheet(OUTLINE_BTN_STYLE)
        self._verify_btn.setCursor(Qt.PointingHandCursor)
        self._verify_btn.clicked.connect(self._on_verify_export)
        verify_title_row.addWidget(self._verify_btn)
        c4_layout.addLayout(verify_title_row)

        # 验证结果容器（动态添加行）
        self._verify_container = QVBoxLayout()
        self._verify_container.setSpacing(0)
        c4_layout.addLayout(self._verify_container)

        # 初始占位
        self._verify_rows = []
        layout.addWidget(card4)

        layout.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll)

    def _add_verify_row(self, label_text: str, ok: bool):
        """添加一行验证结果（绿色对勾 + 文字）"""
        row = QFrame()
        row.setObjectName("successRow")
        row.setStyleSheet(SUCCESS_ROW_STYLE)
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 20, 0, 20)
        row_layout.setSpacing(25)

        # 圆形对勾图标
        icon = QLabel("✓")
        icon.setFixedSize(50, 50)
        icon.setAlignment(Qt.AlignCenter)
        if ok:
            icon.setStyleSheet(
                f"background: {COLOR_STATE_SUCCESS_BG}; color: {COLOR_STATE_SUCCESS}; "
                f"border-radius: 25px; font-weight: bold; font-size: 30px;"
            )
        else:
            icon.setStyleSheet(
                f"background: #FEF0F0; color: #C53030; "
                f"border-radius: 25px; font-weight: bold; font-size: 30px;"
            )
        row_layout.addWidget(icon)

        text = QLabel(label_text)
        color = COLOR_STATE_SUCCESS if ok else "#C53030"
        text.setStyleSheet(
            f"color: {color}; font-size: 32px; background: transparent; border: none;"
        )
        row_layout.addWidget(text)
        row_layout.addStretch()

        self._verify_container.addWidget(row)
        self._verify_rows.append(row)

    def _clear_verify_rows(self):
        for row in self._verify_rows:
            row.deleteLater()
        self._verify_rows.clear()

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
        from modules.export_engine import ExportConfig  # 延迟导入，避免 Demo 模式触发 torch
        precision = self._precision_combo.currentText()
        # 从 combo 解析 workspace 数值
        ws_text = self._workspace_combo.currentText().replace(" GB", "")
        try:
            workspace = int(ws_text)
        except ValueError:
            workspace = self._jetson_workspace
        return ExportConfig(
            imgsz=self._imgsz_spin.value(),
            half=self._jetson_half if precision == "FP16" else False,
            int8=(precision == "INT8"),
            workspace=workspace,
            device=self._app_config.get("jetson", {}).get("device", 0) if self._app_config else 0,
        )

    def _on_toggle_advanced(self):
        if self._advanced_toggle.isChecked():
            self._advanced_panel.setVisible(True)
            self._advanced_toggle.setText("▲")
        else:
            self._advanced_panel.setVisible(False)
            self._advanced_toggle.setText("▼")

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
                QMessageBox.information(
                    self, "生成成功",
                    f"部署包已生成:\n{zip_path}\n文件大小: {size_mb:.1f} MB"
                )
            else:
                QMessageBox.critical(
                    self, "生成失败",
                    "部署包生成失败，请先导出模型。"
                )
        except Exception as e:
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

        # 清除旧行
        self._clear_verify_rows()

        engine_ok = self._export_engine.verify_export(str(engine_path))
        self._add_verify_row(f"TensorRT (.engine): {'有效' if engine_ok else '不存在或无效'}", engine_ok)

        onnx_ok = self._export_engine.verify_export(str(onnx_path))
        self._add_verify_row(f"ONNX (.onnx): {'有效' if onnx_ok else '不存在或无效'}", onnx_ok)

        all_ok = engine_ok and onnx_ok
        if all_ok:
            QMessageBox.information(self, "验证结果", "所有导出文件验证通过")
        else:
            QMessageBox.warning(self, "验证结果", "部分导出文件验证未通过")
