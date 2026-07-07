from pathlib import Path
import subprocess
import sys

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFileDialog, QMessageBox, QFormLayout,
    QSplitter, QComboBox, QSpinBox, QDoubleSpinBox, QProgressBar, QCheckBox,
    QListWidget, QAbstractItemView, QFrame)
from PyQt5.QtCore import Qt

from app.widgets.model_list import ModelListWidget
from app.widgets.log_panel import LogPanel
from app.models.app_config import AppConfig


def _fmt_size(size_bytes):
    if size_bytes is None or size_bytes == 0:
        return "-"
    size_bytes = float(size_bytes)
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / 1024:.1f} KB"


class ModelPage(QWidget):
    """模型管理页：上半区模型列表 + 下半区微调训练（v2 设计稿合并布局）"""

    def __init__(self, project_root: Path, model_manager, dataset_manager, train_engine=None):
        super().__init__()
        self._project_root = Path(project_root)
        self._model_manager = model_manager
        self._dataset_manager = dataset_manager
        self._train_engine_module = train_engine
        self._app_config = AppConfig(project_root)

        # 训练相关状态
        self._train_engine = None
        self._param_widgets = {}
        self._prepared_dataset_path = None
        self._selected_model_info = None

        self._setup_ui()
        self._connect_signals()
        self._refresh_models()
        self._refresh_media_list()

    # ---------- UI 搭建 ----------

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # 顶部工具栏
        toolbar = self._create_toolbar()
        layout.addLayout(toolbar)

        # 上下分栏 splitter
        splitter = QSplitter(Qt.Vertical)
        splitter.setChildrenCollapsible(False)

        # 上半区：模型列表卡片
        upper_card = self._create_model_list_card()
        splitter.addWidget(upper_card)

        # 下半区：微调训练卡片
        lower_card = self._create_training_card()
        splitter.addWidget(lower_card)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([480, 280])

        layout.addWidget(splitter, 1)

    def _create_toolbar(self):
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(8)

        self._import_btn = QPushButton("导入模型")
        self._import_btn.setStyleSheet(
            "QPushButton { background-color: #1B5E3B; color: white; "
            "padding: 6px 16px; border: 1px solid #1B5E3B; border-radius: 2px; "
            "font-weight: 500; }"
            "QPushButton:hover { background-color: #15713A; }"
        )
        self._import_btn.clicked.connect(self._on_import)
        toolbar_layout.addWidget(self._import_btn)

        self._refresh_btn = QPushButton("刷新")
        self._refresh_btn.setStyleSheet(
            "QPushButton { background-color: #FFFFFF; color: #5F6368; "
            "padding: 6px 16px; border: 1px solid #D5D8DC; border-radius: 2px; }"
            "QPushButton:hover { background-color: #F0F2F5; }"
        )
        self._refresh_btn.clicked.connect(self._on_refresh)
        toolbar_layout.addWidget(self._refresh_btn)

        self._compare_btn = QPushButton("模型对比")
        self._compare_btn.setStyleSheet(
            "QPushButton { background-color: #FFFFFF; color: #5F6368; "
            "padding: 6px 16px; border: 1px solid #D5D8DC; border-radius: 2px; }"
            "QPushButton:hover { background-color: #F0F2F5; }"
        )
        self._compare_btn.clicked.connect(self._on_compare)
        toolbar_layout.addWidget(self._compare_btn)

        toolbar_layout.addStretch()
        return toolbar_layout

    def _create_model_list_card(self):
        card = QFrame()
        card.setStyleSheet(
            "QFrame { background-color: #FFFFFF; border: 1px solid #D5D8DC; "
            "border-radius: 8px; }"
        )
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 10, 14, 12)
        card_layout.setSpacing(8)

        # 卡片标题
        title = QLabel("模型列表")
        title.setStyleSheet(
            "font-size: 15px; font-weight: 600; color: #1A1D21; background: transparent; border: none;"
        )
        card_layout.addWidget(title)

        # 模型列表表格（隐藏内置工具栏）
        self._model_list_widget = ModelListWidget(show_toolbar=False)
        self._model_list_widget.setMinimumHeight(180)
        card_layout.addWidget(self._model_list_widget, 1)

        # 详情栏（灰色背景，单行横向排列）
        self._detail_bar = QLabel("路径: -  |  架构: -  |  类别: -")
        self._detail_bar.setStyleSheet(
            "QLabel { background-color: #EDF0F3; color: #5F6368; "
            "padding: 8px 12px; border-radius: 4px; font-size: 12px; border: none; }"
        )
        self._detail_bar.setWordWrap(False)
        self._detail_bar.setMinimumHeight(28)
        card_layout.addWidget(self._detail_bar)

        return card

    def _create_training_card(self):
        card = QFrame()
        card.setStyleSheet(
            "QFrame { background-color: #FFFFFF; border: 1px solid #D5D8DC; "
            "border-radius: 8px; }"
        )
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 10, 14, 14)
        card_layout.setSpacing(10)

        # 卡片标题
        title = QLabel("微调训练")
        title.setStyleSheet(
            "font-size: 15px; font-weight: 600; color: #1A1D21; background: transparent; border: none;"
        )
        card_layout.addWidget(title)

        # 两列布局：左数据源 40% / 右训练参数 60%
        cols = QHBoxLayout()
        cols.setSpacing(16)

        cols.addWidget(self._create_data_source_column(), 40)
        cols.addWidget(self._create_training_params_column(), 60)
        card_layout.addLayout(cols, 1)

        # 训练控制条
        card_layout.addLayout(self._create_training_controls())

        # 日志面板
        self.log_panel = LogPanel()
        self.log_panel.setMaximumHeight(140)
        card_layout.addWidget(self.log_panel)

        return card

    def _create_data_source_column(self):
        col = QFrame()
        col.setStyleSheet("QFrame { background: transparent; border: none; }")
        col_layout = QVBoxLayout(col)
        col_layout.setContentsMargins(0, 0, 0, 0)
        col_layout.setSpacing(6)

        title = QLabel("数据源")
        title.setStyleSheet("font-size: 13px; font-weight: 600; color: #1A1D21; background: transparent; border: none;")
        col_layout.addWidget(title)

        # 分类筛选下拉框
        cat_row = QHBoxLayout()
        cat_label = QLabel("分类筛选:")
        cat_label.setStyleSheet("font-size: 12px; color: #5F6368; background: transparent; border: none;")
        cat_row.addWidget(cat_label)
        self._category_combo = QComboBox()
        self._category_combo.addItem("全部分类")
        self._category_combo.currentIndexChanged.connect(self._on_category_filter_changed)
        cat_row.addWidget(self._category_combo, 1)
        col_layout.addLayout(cat_row)

        # 导入素材列表
        self._media_list = QListWidget()
        self._media_list.setSelectionMode(QAbstractItemView.MultiSelection)
        col_layout.addWidget(self._media_list, 1)

        self._btn_prepare_data = QPushButton("准备数据")
        self._btn_prepare_data.clicked.connect(self._on_prepare_data)
        col_layout.addWidget(self._btn_prepare_data)

        col_layout.addStretch()
        return col

    def _create_training_params_column(self):
        col = QFrame()
        col.setStyleSheet("QFrame { background: transparent; border: none; }")
        col_layout = QVBoxLayout(col)
        col_layout.setContentsMargins(0, 0, 0, 0)
        col_layout.setSpacing(6)

        title = QLabel("训练参数")
        title.setStyleSheet("font-size: 13px; font-weight: 600; color: #1A1D21; background: transparent; border: none;")
        col_layout.addWidget(title)

        # 2×2 网格
        grid = QHBoxLayout()
        left_col = QFormLayout()
        right_col = QFormLayout()

        self._param_widgets["epochs"] = QSpinBox()
        self._param_widgets["epochs"].setRange(1, 500)
        self._param_widgets["epochs"].setValue(50)
        left_col.addRow("训练轮数:", self._param_widgets["epochs"])

        self._param_widgets["batch"] = QSpinBox()
        self._param_widgets["batch"].setRange(1, 128)
        self._param_widgets["batch"].setValue(8)
        right_col.addRow("批次:", self._param_widgets["batch"])

        self._param_widgets["lr0"] = QDoubleSpinBox()
        self._param_widgets["lr0"].setRange(0.00001, 0.1)
        self._param_widgets["lr0"].setDecimals(5)
        self._param_widgets["lr0"].setSingleStep(0.00001)
        self._param_widgets["lr0"].setValue(0.0001)
        left_col.addRow("学习率:", self._param_widgets["lr0"])

        self._param_widgets["imgsz"] = QSpinBox()
        self._param_widgets["imgsz"].setRange(320, 1280)
        self._param_widgets["imgsz"].setSingleStep(32)
        self._param_widgets["imgsz"].setValue(640)
        right_col.addRow("尺寸:", self._param_widgets["imgsz"])

        grid.addLayout(left_col)
        grid.addLayout(right_col)
        col_layout.addLayout(grid)

        # 高级选项
        self._btn_toggle_advanced = QPushButton("高级选项 ▼")
        self._btn_toggle_advanced.setStyleSheet(
            "QPushButton { color: #1B5E3B; border: none; text-align: left; "
            "background: transparent; font-size: 12px; }"
        )
        self._btn_toggle_advanced.clicked.connect(self._on_toggle_advanced)
        col_layout.addWidget(self._btn_toggle_advanced)

        self._advanced_panel = QFrame()
        self._advanced_panel.setStyleSheet("QFrame { background: transparent; border: none; }")
        advanced_form = QFormLayout(self._advanced_panel)

        self._param_widgets["optimizer"] = QComboBox()
        self._param_widgets["optimizer"].addItems(["AdamW", "SGD", "Adam"])
        advanced_form.addRow("优化器:", self._param_widgets["optimizer"])

        self._param_widgets["warmup_epochs"] = QSpinBox()
        self._param_widgets["warmup_epochs"].setRange(0, 10)
        self._param_widgets["warmup_epochs"].setValue(2)
        advanced_form.addRow("预热轮数:", self._param_widgets["warmup_epochs"])

        self._param_widgets["patience"] = QSpinBox()
        self._param_widgets["patience"].setRange(1, 50)
        self._param_widgets["patience"].setValue(15)
        advanced_form.addRow("早停耐心:", self._param_widgets["patience"])

        self._param_widgets["weight_decay"] = QDoubleSpinBox()
        self._param_widgets["weight_decay"].setRange(0.0, 1.0)
        self._param_widgets["weight_decay"].setDecimals(5)
        self._param_widgets["weight_decay"].setSingleStep(0.0001)
        self._param_widgets["weight_decay"].setValue(0.0005)
        advanced_form.addRow("权重衰减:", self._param_widgets["weight_decay"])

        self._param_widgets["cos_lr"] = QCheckBox("余弦学习率")
        self._param_widgets["cos_lr"].setChecked(True)
        advanced_form.addRow("", self._param_widgets["cos_lr"])

        self._advanced_panel.setVisible(False)
        col_layout.addWidget(self._advanced_panel)

        col_layout.addStretch()
        return col

    def _create_training_controls(self):
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(8)

        self._btn_start_train = QPushButton("开始训练")
        self._btn_start_train.setStyleSheet(
            "QPushButton { background-color: #1B5E3B; color: white; "
            "padding: 6px 16px; border: 1px solid #1B5E3B; border-radius: 2px; "
            "font-weight: 500; }"
            "QPushButton:hover { background-color: #15713A; }"
            "QPushButton:disabled { background-color: #cccccc; border-color: #cccccc; }"
        )
        self._btn_start_train.clicked.connect(self._on_start_training)
        controls_layout.addWidget(self._btn_start_train)

        self._btn_stop_train = QPushButton("停止训练")
        self._btn_stop_train.setStyleSheet(
            "QPushButton { background-color: #FFFFFF; color: #5F6368; "
            "padding: 6px 16px; border: 1px solid #D5D8DC; border-radius: 2px; }"
            "QPushButton:hover { background-color: #F0F2F5; }"
            "QPushButton:disabled { color: #cccccc; }"
        )
        self._btn_stop_train.setEnabled(False)
        self._btn_stop_train.clicked.connect(self._on_stop_training)
        controls_layout.addWidget(self._btn_stop_train)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("就绪")
        self.progress_bar.setMinimumWidth(200)
        controls_layout.addWidget(self.progress_bar, 1)

        return controls_layout

    # ---------- 信号连接 ----------

    def _connect_signals(self):
        self._model_list_widget.model_selected.connect(self._on_model_selected)
        self._model_list_widget.model_double_clicked.connect(self._on_model_double_clicked)
        self._model_list_widget.import_clicked.connect(self._on_import)
        self._model_list_widget.refresh_clicked.connect(self._on_refresh)
        self._model_list_widget.compare_clicked.connect(self._on_compare_selected)
        self._model_list_widget.delete_requested.connect(self._on_delete)
        self._model_list_widget.set_default_requested.connect(self._on_set_default)

    # ---------- 模型列表相关 ----------

    def _refresh_models(self):
        try:
            models = self._model_manager.list_models()
            models_data = []
            for m in models:
                models_data.append({
                    "name": m.name,
                    "path": m.path,
                    "model_type": m.model_type,
                    "num_classes": m.num_classes,
                    "class_names": m.class_names,
                    "file_size": m.file_size,
                    "created_at": m.created_at,
                    "status": m.status,
                    "metrics": m.metrics,
                })
            self._model_list_widget.load_models(models_data)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"刷新模型列表失败: {e}")

    def _on_model_selected(self, info):
        # 记录当前选中模型，供训练使用
        self._selected_model_info = info

        # 更新详情栏
        path = info.get("path", "-")
        arch = info.get("model_type", "-")
        class_names = info.get("class_names", [])
        if class_names:
            classes_text = ", ".join(str(c) for c in class_names)
        else:
            num_classes = info.get("num_classes", 0)
            classes_text = f"{num_classes} 个类别"
        self._detail_bar.setText(
            f"路径: <span style='color:#1A1D21;'>{path}</span>  |  "
            f"架构: <span style='color:#1A1D21;'>{arch}</span>  |  "
            f"类别: <span style='color:#1A1D21;'>{classes_text}</span>"
        )
        self._detail_bar.setTextFormat(Qt.RichText)
        self._detail_bar.setToolTip(path)

    def _on_model_double_clicked(self, info):
        detail_text = (
            f"名称: {info.get('name', '-')}\n"
            f"路径: {info.get('path', '-')}\n"
            f"类型: {info.get('model_type', '-')}\n"
            f"大小: {_fmt_size(info.get('file_size'))}\n"
            f"类别数: {info.get('num_classes', '-')}\n"
            f"创建时间: {info.get('created_at', '-')}\n"
            f"状态: {info.get('status', '-')}\n"
            f"mAP: {info.get('metrics', {}).get('mAP', '-')}"
        )
        QMessageBox.information(self, "模型详情", detail_text)

    def _on_import(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入模型",
            str(self._model_manager.project_root),
            "PyTorch 模型文件 (*.pt)"
        )
        if not file_path:
            return
        try:
            result = self._model_manager.import_model(Path(file_path))
            if result is None:
                QMessageBox.warning(self, "导入失败", f"无法导入模型文件: {file_path}")
                return
            QMessageBox.information(self, "导入成功", f"模型已导入: {result.name}")
            self._refresh_models()
        except Exception as e:
            QMessageBox.warning(self, "导入失败", f"导入模型时发生错误: {e}")

    def _on_refresh(self):
        try:
            self._model_manager.scan_models_dir()
            self._refresh_models()
        except Exception as e:
            QMessageBox.warning(self, "刷新失败", f"刷新模型列表时发生错误: {e}")

    def _on_compare(self):
        selected = self._model_list_widget.get_selected_models()
        if len(selected) < 2:
            QMessageBox.information(self, "提示", "请先在列表中选择两个模型（按住 Ctrl 多选）")
            return
        QMessageBox.information(
            self, "模型对比",
            f"准备对比以下模型:\n"
            f"模型 A: {selected[0].get('name', '-')} ({selected[0].get('model_type', '-')})\n"
            f"模型 B: {selected[1].get('name', '-')} ({selected[1].get('model_type', '-')})\n\n"
            "模型对比功能需要指定测试图片或视频文件。\n该功能将在后续版本中完善。"
        )

    def _on_compare_selected(self, model_a, model_b):
        QMessageBox.information(
            self, "模型对比",
            f"准备对比以下模型:\n"
            f"模型 A: {model_a.get('name', '-')} ({model_a.get('model_type', '-')})\n"
            f"模型 B: {model_b.get('name', '-')} ({model_b.get('model_type', '-')})\n\n"
            "模型对比功能需要指定测试图片或视频文件。\n该功能将在后续版本中完善。"
        )

    def _on_delete(self, model_name):
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除模型 \"{model_name}\" 吗？\n此操作将删除模型文件，不可恢复。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        try:
            success = self._model_manager.remove_model(model_name)
            if success:
                QMessageBox.information(self, "删除成功", f"模型 \"{model_name}\" 已删除")
            else:
                QMessageBox.warning(self, "删除失败", f"无法删除模型 \"{model_name}\"")
            self._refresh_models()
        except Exception as e:
            QMessageBox.warning(self, "删除失败", f"删除模型时发生错误: {e}")

    def _on_set_default(self, model_name):
        try:
            self._app_config.set("last_model", model_name)
            QMessageBox.information(
                self, "设置成功",
                f"已将 \"{model_name}\" 设为默认模型"
            )
        except Exception as e:
            QMessageBox.warning(self, "设置失败", f"保存默认模型时发生错误: {e}")

    # ---------- 数据源 / 训练相关（从 TrainPage 移植） ----------

    def _refresh_category_combo(self):
        """刷新分类筛选下拉框，保留当前选中项"""
        current_text = self._category_combo.currentText() if hasattr(self, "_category_combo") else ""
        self._category_combo.blockSignals(True)
        self._category_combo.clear()
        self._category_combo.addItem("全部分类")
        for cat in self._dataset_manager.list_categories():
            self._category_combo.addItem(cat)
        # 恢复选中项
        idx = self._category_combo.findText(current_text)
        if idx >= 0:
            self._category_combo.setCurrentIndex(idx)
        else:
            self._category_combo.setCurrentIndex(0)
        self._category_combo.blockSignals(False)

    def _refresh_media_list(self):
        self._refresh_category_combo()
        self._media_list.clear()

        category = self._category_combo.currentText()
        if category and category != "全部分类":
            media_items = self._dataset_manager.list_media_by_category(category)
        else:
            media_items = self._dataset_manager.list_media()

        for media_info in media_items:
            label_text = f"{media_info.name}  [{media_info.media_type}]"
            if media_info.media_type == "video":
                label_text += f"  {media_info.resolution}  {media_info.duration:.1f}s"
            self._media_list.addItem(label_text)

    def _on_category_filter_changed(self):
        self._media_list.clear()

        category = self._category_combo.currentText()
        if category and category != "全部分类":
            media_items = self._dataset_manager.list_media_by_category(category)
        else:
            media_items = self._dataset_manager.list_media()

        for media_info in media_items:
            label_text = f"{media_info.name}  [{media_info.media_type}]"
            if media_info.media_type == "video":
                label_text += f"  {media_info.resolution}  {media_info.duration:.1f}s"
            self._media_list.addItem(label_text)

    def _on_prepare_data(self):
        selected_items = self._media_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "提示", "请在素材列表中至少选择一个视频或图片。")
            return

        self.log_panel.clear()
        self.log_panel.append_log("开始准备训练数据...", "INFO")

        frames_dir = self._project_root / "data" / "factory_frames"
        frames_dir.mkdir(parents=True, exist_ok=True)

        media_items = self._dataset_manager.list_media()
        selected_names = {item.text().split("  [")[0] for item in selected_items}
        selected_media = [m for m in media_items if m.name in selected_names]

        total_extracted = 0

        for media_info in selected_media:
            media_path = self._project_root / media_info.path
            if media_info.media_type == "video":
                self.log_panel.append_log(f"正在从视频抽帧: {media_info.name}", "INFO")
                try:
                    extracted = self._dataset_manager.extract_frames(
                        str(media_path),
                        interval=15,
                        output_dir=str(frames_dir),
                    )
                    total_extracted += extracted
                    self.log_panel.append_log(f"  已抽取 {extracted} 帧", "SUCCESS")
                except Exception as e:
                    self.log_panel.append_log(f"  抽帧失败: {e}", "ERROR")
            elif media_info.media_type == "image":
                self.log_panel.append_log(f"复制图片: {media_info.name}", "INFO")
                try:
                    import shutil
                    dest_path = frames_dir / media_path.name
                    shutil.copy2(str(media_path), str(dest_path))
                    total_extracted += 1
                    self.log_panel.append_log(f"  已复制", "SUCCESS")
                except Exception as e:
                    self.log_panel.append_log(f"  复制失败: {e}", "ERROR")

        if total_extracted == 0:
            self.log_panel.append_log("未提取到任何有效数据。", "ERROR")
            return

        self.log_panel.append_log(f"共提取 {total_extracted} 个文件到 {frames_dir}", "SUCCESS")

        predefined_path = self._project_root / "configs" / "predefined_classes.txt"
        msg = (
            "数据抽取完成！\n\n"
            f"帧已保存到:\n{frames_dir}\n\n"
            "下一步：请使用 LabelImg 进行标注。\n"
            "是否现在启动 LabelImg？\n\n"
            "提示：标注完成后，请将所有标注文件保存在同一文件夹中，然后返回此处继续。"
        )
        reply = QMessageBox.question(
            self, "启动 LabelImg", msg,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
        )

        if reply == QMessageBox.Yes:
            try:
                subprocess.Popen(
                    [sys.executable, "-c",
                     f"from labelImg.labelImg import main; import sys; "
                     f"sys.argv = ['labelImg', r'{frames_dir}', "
                     f"r'{predefined_path}', r'{frames_dir}']; main()"],
                    cwd=str(self._project_root),
                )
                self.log_panel.append_log("已启动 LabelImg，请完成标注后返回。", "INFO")
            except Exception as e:
                self.log_panel.append_log(f"启动 LabelImg 失败: {e}", "ERROR")
                QMessageBox.warning(
                    self, "启动失败",
                    f"无法启动 LabelImg: {e}\n\n"
                    f"请手动运行 labelimg.bat 进行标注。\n"
                    f"标注目录: {frames_dir}"
                )

        prep_reply = QMessageBox.question(
            self, "准备数据集",
            "标注完成后，是否立即构建训练数据集？\n\n"
            "这将会将标注数据与默认数据集合并，生成可用于训练的数据集。",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
        )

        if prep_reply == QMessageBox.Yes:
            self._run_prepare_dataset(frames_dir)

    def _run_prepare_dataset(self, frames_dir):
        try:
            original_dataset_dir = self._project_root / "data" / "smoke_dataset"
            output_dir = self._project_root / "data" / "factory_dataset"

            result = self._dataset_manager.prepare_dataset(
                str(frames_dir),
                str(original_dataset_dir),
                str(output_dir),
                val_split=0.2,
            )

            if result is None:
                self.log_panel.append_log(
                    "未找到成对的图片和标注文件，请先使用 LabelImg 完成标注。", "ERROR"
                )
                QMessageBox.warning(
                    self, "数据集准备失败",
                    "未找到标注文件（*.txt）。\n\n"
                    "请确保:\n"
                    "1. 已在 LabelImg 中对所有图片完成标注\n"
                    "2. 标注文件（.txt）与图片保存在同一目录"
                )
                return

            self._prepared_dataset_path = str(output_dir / "data.yaml")
            self.log_panel.append_log("数据集准备完成！", "SUCCESS")
            self.log_panel.append_log(f"  标注帧数: {result['total_paired']}", "INFO")
            self.log_panel.append_log(f"  训练集: {result['train_images']} 图片", "INFO")
            self.log_panel.append_log(f"  验证集: {result['val_images']} 图片", "INFO")
            self.log_panel.append_log(f"  输出目录: {result['output_dir']}", "INFO")

            QMessageBox.information(
                self, "数据集准备完成",
                f"训练数据集已构建完成！\n\n"
                f"标注帧数: {result['total_paired']}\n"
                f"训练集: {result['train_images']} 图片, {result['train_labels']} 标注\n"
                f"验证集: {result['val_images']} 图片, {result['val_labels']} 标注\n\n"
                f"数据集路径: {result['output_dir']}"
            )
        except Exception as e:
            self.log_panel.append_log(f"数据集准备失败: {e}", "ERROR")
            QMessageBox.critical(self, "错误", f"数据集准备过程中发生错误:\n{e}")

    def _on_toggle_advanced(self):
        is_visible = self._advanced_panel.isVisible()
        self._advanced_panel.setVisible(not is_visible)
        self._btn_toggle_advanced.setText("高级选项 ▲" if not is_visible else "高级选项 ▼")

    def _collect_config(self):
        from modules.train_engine import TrainingConfig
        config = TrainingConfig()

        if self._prepared_dataset_path:
            config.data = self._prepared_dataset_path
        else:
            config.data = str(self._project_root / "data" / "factory_dataset" / "data.yaml")

        model_info = self._selected_model_info
        if model_info:
            config.model = model_info.path
        else:
            config.model = ""

        config.epochs = self._param_widgets["epochs"].value()
        config.batch = self._param_widgets["batch"].value()
        config.lr0 = self._param_widgets["lr0"].value()
        config.imgsz = self._param_widgets["imgsz"].value()
        config.optimizer = self._param_widgets["optimizer"].currentText()
        config.warmup_epochs = self._param_widgets["warmup_epochs"].value()
        config.patience = self._param_widgets["patience"].value()
        config.weight_decay = self._param_widgets["weight_decay"].value()
        config.cos_lr = self._param_widgets["cos_lr"].isChecked()

        config.project = str(self._project_root / "runs" / "train")
        config.name = "factory_finetune"
        config.exist_ok = True

        return config

    def _on_start_training(self):
        if self._prepared_dataset_path is None:
            reply = QMessageBox.question(
                self, "数据集未准备",
                "尚未准备训练数据集。\n"
                "是否使用已存在的工厂数据集？\n\n"
                "选“否”将返回，请您先点击“准备数据”按钮。",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        if self._selected_model_info is None:
            QMessageBox.warning(self, "提示", "请先在模型列表中选择一个模型。")
            return

        config = self._collect_config()
        if not config.data or not Path(config.data).exists():
            QMessageBox.warning(self, "提示", f"数据集文件不存在:\n{config.data}")
            return
        if not config.model or not Path(config.model).exists():
            QMessageBox.warning(self, "提示", f"模型文件不存在:\n{config.model}")
            return

        from modules.train_engine import TrainEngine
        self._train_engine = TrainEngine(self._project_root)

        self._btn_start_train.setEnabled(False)
        self._btn_stop_train.setEnabled(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("训练中...")
        self.log_panel.clear()
        self.log_panel.append_log("开始训练...", "INFO")
        self.log_panel.append_log(f"数据集: {config.data}", "INFO")
        self.log_panel.append_log(f"模型: {config.model}", "INFO")
        self.log_panel.append_log(f"训练轮数: {config.epochs}", "INFO")
        self.log_panel.append_log(f"批次大小: {config.batch}", "INFO")
        self.log_panel.append_log(f"学习率: {config.lr0}", "INFO")
        self.log_panel.append_log(f"图像尺寸: {config.imgsz}", "INFO")
        self.log_panel.append_log("提示: 训练过程会阻塞UI，请耐心等待。", "WARNING")

        try:
            def progress_callback(current_epoch, total_epochs, metrics):
                if total_epochs > 0:
                    pct = int(current_epoch / total_epochs * 100)
                    self.progress_bar.setValue(pct)
                    self.progress_bar.setFormat(f"训练中... {current_epoch}/{total_epochs} ({pct}%)")
                self.log_panel.append_log(f"Epoch {current_epoch}/{total_epochs} 完成", "INFO")

            self._train_engine.train(config, progress_callback=progress_callback)

            self.progress_bar.setValue(100)
            self.progress_bar.setFormat("训练完成")

            status = self._train_engine.get_status()
            if status.get("status") == "stopped":
                self.log_panel.append_log("训练已被用户停止。", "WARNING")
                QMessageBox.information(self, "训练已停止", "训练已手动停止。")
            else:
                self.log_panel.append_log("训练完成！", "SUCCESS")
                self._model_manager.scan_models_dir()
                self._refresh_models()
                QMessageBox.information(
                    self, "训练完成",
                    "模型微调训练已完成！\n\n"
                    f"最佳模型已保存到 models/ 目录。"
                )
        except Exception as e:
            self.log_panel.append_log(f"训练失败: {e}", "ERROR")
            self.progress_bar.setFormat("训练失败")
            QMessageBox.critical(self, "训练失败", f"训练过程中发生错误:\n{e}")
        finally:
            self._btn_start_train.setEnabled(True)
            self._btn_stop_train.setEnabled(False)
            self._train_engine = None

    def _on_stop_training(self):
        if self._train_engine is not None:
            self.log_panel.append_log("正在停止训练...", "WARNING")
            self._train_engine.stop()
            self._btn_stop_train.setEnabled(False)
