from pathlib import Path
import subprocess
import sys

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QFormLayout, QRadioButton, QButtonGroup, QPushButton, QComboBox,
    QSpinBox, QDoubleSpinBox, QProgressBar, QLabel, QListWidget,
    QAbstractItemView, QCheckBox, QMessageBox, QFileDialog)
from PyQt5.QtCore import Qt

from app.widgets.log_panel import LogPanel
from modules.train_engine import TrainingConfig, TrainEngine


class TrainPage(QWidget):
    def __init__(self, project_root: Path, train_engine, model_manager, dataset_manager):
        super().__init__()
        self._project_root = project_root
        self._train_engine_module = train_engine
        self._model_manager = model_manager
        self._dataset_manager = dataset_manager

        self._train_engine = None
        self._param_widgets = {}
        self._prepared_dataset_path = None

        self._setup_ui()
        self._refresh_models()
        self._refresh_default_dataset_summary()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        layout.addWidget(self._create_data_source_section())
        layout.addWidget(self._create_model_section())
        layout.addWidget(self._create_training_params_section())
        layout.addWidget(self._create_training_control_section())
        layout.addStretch()

    def _create_data_source_section(self):
        group = QGroupBox("数据源")
        vbox = QVBoxLayout(group)

        self._data_source_group = QButtonGroup(self)
        self._radio_default = QRadioButton("使用默认数据集")
        self._radio_imported = QRadioButton("使用导入素材")
        self._radio_default.setChecked(True)
        self._data_source_group.addButton(self._radio_default, 0)
        self._data_source_group.addButton(self._radio_imported, 1)
        self._data_source_group.buttonClicked.connect(self._on_data_source_changed)

        radio_layout = QHBoxLayout()
        radio_layout.addWidget(self._radio_default)
        radio_layout.addWidget(self._radio_imported)
        radio_layout.addStretch()
        vbox.addLayout(radio_layout)

        self._default_dataset_widget = QWidget()
        default_layout = QFormLayout(self._default_dataset_widget)
        default_layout.setContentsMargins(0, 4, 0, 4)
        self._label_total_images = QLabel("--")
        self._label_train_count = QLabel("--")
        self._label_val_count = QLabel("--")
        self._label_classes = QLabel("--")
        default_layout.addRow("图片总数:", self._label_total_images)
        default_layout.addRow("训练集:", self._label_train_count)
        default_layout.addRow("验证集:", self._label_val_count)
        default_layout.addRow("类别:", self._label_classes)
        vbox.addWidget(self._default_dataset_widget)

        self._imported_dataset_widget = QWidget()
        imported_layout = QVBoxLayout(self._imported_dataset_widget)
        imported_layout.setContentsMargins(0, 4, 0, 4)

        self._media_list = QListWidget()
        self._media_list.setSelectionMode(QAbstractItemView.MultiSelection)
        imported_layout.addWidget(self._media_list)

        self._btn_prepare_data = QPushButton("准备数据")
        self._btn_prepare_data.clicked.connect(self._on_prepare_data)
        imported_layout.addWidget(self._btn_prepare_data)

        vbox.addWidget(self._imported_dataset_widget)
        self._imported_dataset_widget.setVisible(False)

        return group

    def _create_model_section(self):
        group = QGroupBox("基础模型")
        vbox = QVBoxLayout(group)

        self._model_combo = QComboBox()
        vbox.addWidget(self._model_combo)

        self._model_info_label = QLabel()
        vbox.addWidget(self._model_info_label)

        return group

    def _create_training_params_section(self):
        group = QGroupBox("训练参数")
        vbox = QVBoxLayout(group)

        basic_form = QFormLayout()

        self._param_widgets["epochs"] = QSpinBox()
        self._param_widgets["epochs"].setRange(1, 500)
        self._param_widgets["epochs"].setValue(50)
        basic_form.addRow("训练轮数:", self._param_widgets["epochs"])

        self._param_widgets["batch"] = QSpinBox()
        self._param_widgets["batch"].setRange(1, 128)
        self._param_widgets["batch"].setValue(8)
        basic_form.addRow("批次大小:", self._param_widgets["batch"])

        self._param_widgets["lr0"] = QDoubleSpinBox()
        self._param_widgets["lr0"].setRange(0.00001, 0.1)
        self._param_widgets["lr0"].setDecimals(5)
        self._param_widgets["lr0"].setSingleStep(0.00001)
        self._param_widgets["lr0"].setValue(0.0001)
        basic_form.addRow("学习率:", self._param_widgets["lr0"])

        self._param_widgets["imgsz"] = QSpinBox()
        self._param_widgets["imgsz"].setRange(320, 1280)
        self._param_widgets["imgsz"].setSingleStep(32)
        self._param_widgets["imgsz"].setValue(640)
        basic_form.addRow("图像尺寸:", self._param_widgets["imgsz"])

        vbox.addLayout(basic_form)

        self._btn_toggle_advanced = QPushButton("高级选项 ▼")
        self._btn_toggle_advanced.clicked.connect(self._on_toggle_advanced)
        vbox.addWidget(self._btn_toggle_advanced)

        self._advanced_panel = QWidget()
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
        vbox.addWidget(self._advanced_panel)

        self._btn_reset_defaults = QPushButton("重置为默认")
        self._btn_reset_defaults.clicked.connect(self._on_reset_defaults)
        vbox.addWidget(self._btn_reset_defaults)

        return group

    def _create_training_control_section(self):
        group = QGroupBox("训练控制")
        vbox = QVBoxLayout(group)

        btn_layout = QHBoxLayout()

        self._btn_start_train = QPushButton("开始训练")
        self._btn_start_train.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; font-weight: bold; "
            "padding: 6px 20px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #45a049; }"
            "QPushButton:disabled { background-color: #cccccc; }"
        )
        self._btn_start_train.clicked.connect(self._on_start_training)
        btn_layout.addWidget(self._btn_start_train)

        self._btn_stop_train = QPushButton("停止训练")
        self._btn_stop_train.setStyleSheet(
            "QPushButton { background-color: #f44336; color: white; font-weight: bold; "
            "padding: 6px 20px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #d32f2f; }"
            "QPushButton:disabled { background-color: #cccccc; }"
        )
        self._btn_stop_train.setEnabled(False)
        self._btn_stop_train.clicked.connect(self._on_stop_training)
        btn_layout.addWidget(self._btn_stop_train)
        btn_layout.addStretch()

        vbox.addLayout(btn_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("就绪")
        vbox.addWidget(self.progress_bar)

        plots_layout = QHBoxLayout()

        self._loss_plot_placeholder = QLabel("训练曲线将在此显示")
        self._loss_plot_placeholder.setAlignment(Qt.AlignCenter)
        self._loss_plot_placeholder.setMinimumHeight(200)
        self._loss_plot_placeholder.setStyleSheet(
            "QLabel { border: 1px solid #cccccc; background-color: #fafafa; }"
        )
        plots_layout.addWidget(self._loss_plot_placeholder)

        self._metrics_plot_placeholder = QLabel("训练曲线将在此显示")
        self._metrics_plot_placeholder.setAlignment(Qt.AlignCenter)
        self._metrics_plot_placeholder.setMinimumHeight(200)
        self._metrics_plot_placeholder.setStyleSheet(
            "QLabel { border: 1px solid #cccccc; background-color: #fafafa; }"
        )
        plots_layout.addWidget(self._metrics_plot_placeholder)

        vbox.addLayout(plots_layout)

        self.log_panel = LogPanel()
        vbox.addWidget(self.log_panel)

        return group

    def _refresh_models(self):
        self._model_combo.clear()
        models = self._model_manager.list_models()
        for model_info in models:
            display_text = f"{model_info.name} ({model_info.model_type})"
            self._model_combo.addItem(display_text, model_info)

    def _refresh_default_dataset_summary(self):
        try:
            summary = self._dataset_manager.get_dataset_summary()
            self._label_total_images.setText(str(summary.get("total_images", 0)))
            self._label_train_count.setText(str(summary.get("train_count", 0)))
            self._label_val_count.setText(str(summary.get("val_count", 0)))
            classes = summary.get("classes", [])
            self._label_classes.setText(", ".join(classes) if classes else "无")
        except Exception:
            self._label_total_images.setText("--")
            self._label_train_count.setText("--")
            self._label_val_count.setText("--")
            self._label_classes.setText("加载失败")

    def _refresh_media_list(self):
        self._media_list.clear()
        media_items = self._dataset_manager.list_media()
        for media_info in media_items:
            label_text = f"{media_info.name}  [{media_info.media_type}]"
            if media_info.media_type == "video":
                label_text += f"  {media_info.resolution}  {media_info.duration:.1f}s"
            self._media_list.addItem(label_text)

    def _on_data_source_changed(self, button):
        is_default = (self._data_source_group.id(button) == 0)
        self._default_dataset_widget.setVisible(is_default)
        self._imported_dataset_widget.setVisible(not is_default)

        if is_default:
            self._refresh_default_dataset_summary()
        else:
            self._refresh_media_list()

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

    def _on_reset_defaults(self):
        defaults = self._get_default_values()
        self._param_widgets["epochs"].setValue(defaults["epochs"])
        self._param_widgets["batch"].setValue(defaults["batch"])
        self._param_widgets["lr0"].setValue(defaults["lr0"])
        self._param_widgets["imgsz"].setValue(defaults["imgsz"])
        self._param_widgets["optimizer"].setCurrentText(defaults["optimizer"])
        self._param_widgets["warmup_epochs"].setValue(defaults["warmup_epochs"])
        self._param_widgets["patience"].setValue(defaults["patience"])
        self._param_widgets["weight_decay"].setValue(defaults["weight_decay"])
        self._param_widgets["cos_lr"].setChecked(defaults["cos_lr"])
        self.log_panel.append_log("训练参数已重置为默认值。", "INFO")

    def _get_default_values(self):
        return {
            "epochs": 50,
            "batch": 8,
            "lr0": 0.0001,
            "imgsz": 640,
            "optimizer": "AdamW",
            "warmup_epochs": 2,
            "patience": 15,
            "weight_decay": 0.0005,
            "cos_lr": True,
        }

    def _collect_config(self):
        config = TrainingConfig()

        is_default = self._radio_default.isChecked()
        if is_default:
            smoke_data_yaml = self._project_root / "data" / "smoke_dataset" / "data.yaml"
            config.data = str(smoke_data_yaml)
        else:
            if self._prepared_dataset_path:
                config.data = self._prepared_dataset_path
            else:
                config.data = str(self._project_root / "data" / "factory_dataset" / "data.yaml")

        model_info = self._model_combo.currentData()
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
        if self._radio_imported.isChecked() and self._prepared_dataset_path is None:
            reply = QMessageBox.question(
                self, "数据集未准备",
                "您选择了\u201c使用导入素材\u201d但尚未准备数据集。\n"
                "是否使用已存在的工厂数据集？\n\n"
                "选\u201c否\u201d将返回，请您先点击\u201c准备数据\u201d按钮。",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        if self._model_combo.currentData() is None:
            QMessageBox.warning(self, "提示", "请先选择一个基础模型。")
            return

        config = self._collect_config()
        if not config.data or not Path(config.data).exists():
            QMessageBox.warning(self, "提示", f"数据集文件不存在:\n{config.data}")
            return
        if not config.model or not Path(config.model).exists():
            QMessageBox.warning(self, "提示", f"模型文件不存在:\n{config.model}")
            return

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
                    f"最佳模型已保存到 models/ 目录。\n"
                    "请在\u201c模型管理\u201d页面查看新模型。"
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
