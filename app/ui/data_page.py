from pathlib import Path
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QFileDialog, QMessageBox, QInputDialog, QListWidget, QListWidgetItem,
    QSplitter, QGroupBox, QLabel, QAbstractItemView, QMenu, QAction,
    QProgressBar, QDialog, QFormLayout, QSpinBox, QDialogButtonBox,
    QRadioButton, QButtonGroup, QFrame, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QImage
import cv2

from app.ui.label_editor_dialog import LabelEditorDialog


class DataPage(QWidget):
    """数据管理页：对接 DatasetManager 后端，支持视频/图片分栏、预览、抽帧、删除"""

    # 信号：当数据集发生变化时通知其他页面
    media_changed = pyqtSignal()

    def __init__(self, project_root: Path, dataset_manager):
        super().__init__()
        self.project_root = Path(project_root)
        self.dataset_manager = dataset_manager
        # 当前选中的媒体信息（dict 形式，含 name/media_type/path）
        self._current_media = None
        self._current_label = None
        self._setup_ui()
        self._refresh_media()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # 顶部按钮栏
        btn_row = QHBoxLayout()
        self.btn_import_video = QPushButton("导入视频")
        self.btn_import_video.clicked.connect(self._on_import_video)
        btn_row.addWidget(self.btn_import_video)

        self.btn_import_image = QPushButton("导入图片")
        self.btn_import_image.clicked.connect(self._on_import_image)
        btn_row.addWidget(self.btn_import_image)

        self.btn_import_label = QPushButton("导入标签")
        self.btn_import_label.clicked.connect(self._on_import_label)
        btn_row.addWidget(self.btn_import_label)

        self.btn_scan = QPushButton("扫描文件夹")
        self.btn_scan.clicked.connect(self._on_scan_dir)
        btn_row.addWidget(self.btn_scan)

        self.btn_delete = QPushButton("批量删除")
        self.btn_delete.clicked.connect(self._on_delete)
        btn_row.addWidget(self.btn_delete)

        self.btn_extract = QPushButton("视频抽帧")
        self.btn_extract.clicked.connect(self._on_extract_frames)
        btn_row.addWidget(self.btn_extract)

        self.btn_annotate = QPushButton("添加标签")
        self.btn_annotate.clicked.connect(self._on_annotate)
        btn_row.addWidget(self.btn_annotate)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        # 三栏：左栏（视频+图片分栏）| 中栏（预览）| 右栏（媒体信息）
        splitter = QSplitter(Qt.Horizontal)

        # === 左栏：素材列表（上下分栏）===
        left_group = QGroupBox("素材列表")
        left_layout = QVBoxLayout(left_group)

        # 视频素材区
        left_layout.addWidget(QLabel("视频素材"))
        self.video_list = QListWidget()
        self.video_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.video_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.video_list.currentRowChanged.connect(self._on_video_selected)
        self.video_list.customContextMenuRequested.connect(self._on_video_context_menu)
        left_layout.addWidget(self.video_list, 1)

        # 已标注图片区
        left_layout.addWidget(QLabel("已标注图片"))
        self.image_labeled_list = QListWidget()
        self.image_labeled_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.image_labeled_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.image_labeled_list.currentRowChanged.connect(self._on_image_selected)
        self.image_labeled_list.customContextMenuRequested.connect(self._on_image_context_menu)
        left_layout.addWidget(self.image_labeled_list, 1)

        # 未标注图片区
        left_layout.addWidget(QLabel("未标注图片"))
        self.image_unlabeled_list = QListWidget()
        self.image_unlabeled_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.image_unlabeled_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.image_unlabeled_list.currentRowChanged.connect(self._on_image_selected)
        self.image_unlabeled_list.customContextMenuRequested.connect(self._on_image_context_menu)
        left_layout.addWidget(self.image_unlabeled_list, 1)

        # 标签管理区
        left_layout.addWidget(QLabel("标签管理"))
        self.label_list = QListWidget()
        self.label_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.label_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.label_list.currentRowChanged.connect(self._on_label_selected)
        self.label_list.customContextMenuRequested.connect(self._on_label_context_menu)
        left_layout.addWidget(self.label_list, 1)

        splitter.addWidget(left_group)

        # === 中栏：预览区 ===
        mid_group = QGroupBox("预览区")
        mid_layout = QVBoxLayout(mid_group)
        self.preview_label = QLabel("请选择左侧素材进行预览")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(480, 468)
        self.preview_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.preview_label.setStyleSheet(
            "QLabel { border: 1px solid #cccccc; background-color: #fafafa; color: #888888; }"
        )
        mid_layout.addWidget(self.preview_label)
        splitter.addWidget(mid_group)

        # === 右栏：媒体信息 ===
        right_group = QGroupBox("媒体信息")
        right_layout = QVBoxLayout(right_group)
        self.info_label = QLabel("未选择素材")
        self.info_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet(
            "QLabel { padding: 8px; background: #f5f5f5; border-radius: 4px; }"
        )
        right_layout.addWidget(self.info_label)

        # 分类管理 GroupBox
        cat_group = QGroupBox("分类管理")
        cat_layout = QVBoxLayout(cat_group)
        cat_btn_row = QHBoxLayout()
        self.btn_new_cat = QPushButton("新建")
        self.btn_new_cat.clicked.connect(self._on_new_category)
        self.btn_rename_cat = QPushButton("重命名")
        self.btn_rename_cat.clicked.connect(self._on_rename_category)
        self.btn_del_cat = QPushButton("删除")
        self.btn_del_cat.clicked.connect(self._on_delete_category)
        cat_btn_row.addWidget(self.btn_new_cat)
        cat_btn_row.addWidget(self.btn_rename_cat)
        cat_btn_row.addWidget(self.btn_del_cat)
        cat_layout.addLayout(cat_btn_row)
        self.cat_list = QListWidget()
        self.cat_list.itemChanged.connect(self._on_cat_check_changed)
        cat_layout.addWidget(self.cat_list, 1)
        self.cat_stats_label = QLabel("")
        self.cat_stats_label.setStyleSheet("QLabel { color: #666; font-size: 11px; }")
        self.cat_stats_label.setWordWrap(True)
        cat_layout.addWidget(self.cat_stats_label)
        right_layout.addWidget(cat_group)

        splitter.addWidget(right_group)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        splitter.setStretchFactor(2, 1)
        splitter.setSizes([300, 700, 300])
        layout.addWidget(splitter)

        # 底部状态栏
        self.status_label = QLabel("共 0 个素材 | 视频: 0 | 图片: 0 | 当前: 无选择")
        self.status_label.setStyleSheet("color: #555555; padding: 4px;")
        layout.addWidget(self.status_label)

    # ---------- 数据刷新 ----------

    def _resolve_media_path(self, path_str):
        """解析媒体路径：绝对路径直接返回，相对路径基于 project_root 拼接"""
        p = Path(path_str)
        return p if p.is_absolute() else self.project_root / p

    def _refresh_media(self):
        """从 DatasetManager 重新加载媒体列表，统一编号（视频在前，图片在后）"""
        self.video_list.clear()
        self.image_labeled_list.clear()
        self.image_unlabeled_list.clear()
        self.label_list.clear()

        media_list = self.dataset_manager.list_media()
        # 视频在前，图片在后，统一编号
        videos = [m for m in media_list if m.media_type == "video"]
        images = [m for m in media_list if m.media_type == "image"]

        idx = 1
        for m in videos:
            item = QListWidgetItem(f"{idx:03d}. {m.name}")
            item.setData(Qt.UserRole, m)
            item.setData(Qt.UserRole + 1, idx)
            self.video_list.addItem(item)
            idx += 1

        # 图片按已标注/未标注拆分到两个列表（统一编号继续递增）
        labeled_count = 0
        unlabeled_count = 0
        for m in images:
            has_lbl = self.dataset_manager.has_label_for(m.name)
            if has_lbl:
                cats_str = f"  [{', '.join(m.categories)}]" if m.categories else ""
                item = QListWidgetItem(f"{idx:03d}. {m.name}{cats_str}")
                item.setData(Qt.UserRole, m)
                item.setData(Qt.UserRole + 1, idx)
                self.image_labeled_list.addItem(item)
                labeled_count += 1
            else:
                item = QListWidgetItem(f"{idx:03d}. {m.name}")
                item.setData(Qt.UserRole, m)
                item.setData(Qt.UserRole + 1, idx)
                self.image_unlabeled_list.addItem(item)
                unlabeled_count += 1
            idx += 1

        # 标签列表（独立编号，与视频/图片编号不连续）
        labels = self.dataset_manager.list_labels()
        label_idx = 1
        for lbl in labels:
            item = QListWidgetItem(f"{label_idx:03d}. {lbl.name}")
            item.setData(Qt.UserRole, lbl)
            item.setData(Qt.UserRole + 1, label_idx)
            self.label_list.addItem(item)
            label_idx += 1

        video_count = len(videos)
        image_count = len(images)
        label_count = len(labels)
        total = video_count + image_count
        self.status_label.setText(
            f"共 {total} 个素材 | 视频: {video_count} | 图片: {image_count} (已标注 {labeled_count}/未标注 {unlabeled_count}) | 标签: {label_count} | 当前: 无选择"
        )
        self._current_media = None
        self._current_label = None
        self.preview_label.clear()
        self.preview_label.setText("请选择左侧素材进行预览")
        self.info_label.setText("未选择素材")
        # 刷新分类列表与统计
        self._refresh_cat_list()
        self.media_changed.emit()

    # ---------- 选择处理 ----------

    def _on_video_selected(self, row):
        if row < 0:
            return
        # 取消另外三个列表的选择
        self.image_labeled_list.setCurrentRow(-1)
        self.image_unlabeled_list.setCurrentRow(-1)
        self.label_list.setCurrentRow(-1)
        item = self.video_list.item(row)
        if not item:
            return
        m = item.data(Qt.UserRole)
        self._current_media = m
        self._show_preview(m)
        self._show_info(m)
        self._clear_cat_checkstate()
        total_img = self.image_labeled_list.count() + self.image_unlabeled_list.count()
        self.status_label.setText(
            f"共 {self.video_list.count() + total_img} 个素材 | "
            f"视频: {self.video_list.count()} | 图片: {total_img} | "
            f"标签: {self.label_list.count()} | 当前: {m.name} (视频)"
        )

    def _on_image_selected(self, row):
        if row < 0:
            return
        # 判断来自哪个 list
        list_widget = self.sender()
        if list_widget is self.image_labeled_list:
            item = self.image_labeled_list.item(row)
        elif list_widget is self.image_unlabeled_list:
            item = self.image_unlabeled_list.item(row)
        else:
            return  # 来自其他列表，忽略
        if not item:
            return
        m = item.data(Qt.UserRole)
        self._current_media = m
        self._show_preview(m)
        self._show_info(m)
        # 取消另外三个列表的选择
        self.video_list.setCurrentRow(-1)
        self.label_list.setCurrentRow(-1)
        if list_widget is self.image_labeled_list:
            self.image_unlabeled_list.setCurrentRow(-1)
            self._refresh_cat_checkstate(m)
            tag = "已标注图片"
        else:
            self.image_labeled_list.setCurrentRow(-1)
            self._clear_cat_checkstate()
            tag = "未标注图片"
        total_img = self.image_labeled_list.count() + self.image_unlabeled_list.count()
        self.status_label.setText(
            f"共 {self.video_list.count() + total_img} 个素材 | "
            f"视频: {self.video_list.count()} | 图片: {total_img} | "
            f"标签: {self.label_list.count()} | 当前: {m.name} ({tag})"
        )

    def _on_label_selected(self, row):
        if row < 0:
            return
        # 取消另外三个列表的选择
        self.video_list.setCurrentRow(-1)
        self.image_labeled_list.setCurrentRow(-1)
        self.image_unlabeled_list.setCurrentRow(-1)
        item = self.label_list.item(row)
        if not item:
            return
        lbl = item.data(Qt.UserRole)
        self._current_media = None
        self._current_label = lbl
        self._show_label_preview(lbl)
        self._show_label_info(lbl)
        self._clear_cat_checkstate()
        total_img = self.image_labeled_list.count() + self.image_unlabeled_list.count()
        self.status_label.setText(
            f"共 {self.video_list.count() + total_img} 个素材 | "
            f"视频: {self.video_list.count()} | 图片: {total_img} | "
            f"标签: {self.label_list.count()} | 当前: {lbl.name} (标签)"
        )

    # ---------- 预览 ----------

    def _show_preview(self, media_info):
        path = self._resolve_media_path(media_info.path)
        if not path.exists():
            self.preview_label.setText(f"文件不存在:\n{path}")
            return

        if media_info.media_type == "image":
            pixmap = QPixmap(str(path))
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    self.preview_label.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
                self.preview_label.setPixmap(scaled)
            else:
                self.preview_label.setText(f"无法加载图片:\n{media_info.name}")
        elif media_info.media_type == "video":
            cap = cv2.VideoCapture(str(path))
            ret, frame = cap.read()
            cap.release()
            if ret:
                h, w, ch = frame.shape
                bytes_per_line = ch * w
                if ch == 3:
                    q_img = QImage(frame.data, w, h, bytes_per_line, QImage.Format_BGR888)
                else:
                    q_img = QImage(frame.data, w, h, bytes_per_line, QImage.Format_Grayscale8)
                pixmap = QPixmap.fromImage(q_img)
                scaled = pixmap.scaled(
                    self.preview_label.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
                self.preview_label.setPixmap(scaled)
            else:
                self.preview_label.setText(f"无法读取视频:\n{media_info.name}")

    def _show_info(self, m):
        size_mb = m.file_size / (1024 * 1024) if m.file_size else 0
        lines = [
            f"文件名: {m.name}",
            f"类型: {'视频' if m.media_type == 'video' else '图片'}",
            f"路径: {m.path}",
            f"大小: {size_mb:.2f} MB",
        ]
        if m.media_type == "video":
            lines.extend([
                f"分辨率: {m.resolution}",
                f"帧率: {m.fps} FPS",
                f"帧数: {m.frame_count}",
                f"时长: {m.duration}s",
            ])
        else:  # 图片才显示已标注（动态查询标签注册表）
            has_lbl = self.dataset_manager.has_label_for(m.name)
            lines.append(f"已标注: {'是' if has_lbl else '否'}")
        # 显示素材分类归属
        cats = getattr(m, 'categories', None) or []
        lines.append(f"分类: {', '.join(cats) if cats else '无'}")
        lines.append(f"导入时间: {m.imported_at}")
        self.info_label.setText("\n".join(lines))

    def _show_label_preview(self, lbl):
        """标签预览：显示 txt 文本内容"""
        path = self._resolve_media_path(lbl.path)
        if not path.exists():
            self.preview_label.setText(f"文件不存在:\n{path}")
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            if len(content) > 2000:
                content = content[:2000] + "\n... (内容过长，已截断)"
            self.preview_label.setText(content)
        except Exception as e:
            self.preview_label.setText(f"无法读取标签:\n{str(e)}")

    def _show_label_info(self, lbl):
        size_kb = lbl.file_size / 1024 if lbl.file_size else 0
        lines = [
            f"文件名: {lbl.name}",
            f"类型: 标签",
            f"路径: {lbl.path}",
            f"大小: {size_kb:.2f} KB",
            f"标注数: {lbl.line_count}",
            f"导入时间: {lbl.imported_at}",
        ]
        self.info_label.setText("\n".join(lines))

    # ---------- 右键菜单 ----------

    def _on_video_context_menu(self, pos):
        item = self.video_list.itemAt(pos)
        if not item:
            return
        menu = QMenu(self)
        extract_action = QAction("视频抽帧", self)
        extract_action.triggered.connect(self._on_extract_frames)
        menu.addAction(extract_action)
        delete_action = QAction("批量删除", self)
        delete_action.triggered.connect(self._on_delete)
        menu.addAction(delete_action)
        menu.exec_(self.video_list.viewport().mapToGlobal(pos))

    def _on_image_context_menu(self, pos):
        list_widget = self.sender()
        item = list_widget.itemAt(pos)
        if not item:
            return
        menu = QMenu(self)
        delete_action = QAction("批量删除", self)
        delete_action.triggered.connect(self._on_delete)
        menu.addAction(delete_action)
        menu.exec_(list_widget.viewport().mapToGlobal(pos))

    def _on_label_context_menu(self, pos):
        item = self.label_list.itemAt(pos)
        if not item:
            return
        menu = QMenu(self)
        delete_action = QAction("删除", self)
        delete_action.triggered.connect(self._on_delete_label)
        menu.addAction(delete_action)
        menu.exec_(self.label_list.viewport().mapToGlobal(pos))

    # ---------- 按钮事件 ----------

    def _on_import_video(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择视频文件", "", "视频文件 (*.mp4 *.avi *.mov *.mkv *.webm *.flv)"
        )
        if not path:
            return
        try:
            info = self.dataset_manager.import_video(path)
            self._refresh_media()
            QMessageBox.information(self, "导入成功", f"视频已导入:\n{info.name}")
        except Exception as e:
            QMessageBox.critical(self, "导入失败", f"导入视频失败:\n{str(e)}")

    def _on_import_image(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "选择图片文件", "", "图片文件 (*.jpg *.jpeg *.png *.bmp *.tiff *.tif)"
        )
        if not paths:
            return
        try:
            results = self.dataset_manager.import_images(paths)
            self._refresh_media()
            QMessageBox.information(
                self, "导入成功",
                f"已导入 {len(results)} 张图片:\n" + "\n".join(r.name for r in results)
            )
        except Exception as e:
            QMessageBox.critical(self, "导入失败", f"导入图片失败:\n{str(e)}")

    def _on_import_label(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "选择标签文件", "", "标签文件 (*.txt)"
        )
        if not paths:
            return
        try:
            results = self.dataset_manager.import_labels(paths)
            self._refresh_media()
            QMessageBox.information(
                self, "导入成功",
                f"已导入 {len(results)} 个标签:\n" + "\n".join(r.name for r in results)
            )
        except Exception as e:
            QMessageBox.critical(self, "导入失败", f"导入标签失败:\n{str(e)}")

    def _on_delete_label(self):
        row = self.label_list.currentRow()
        if row < 0:
            return
        item = self.label_list.item(row)
        lbl = item.data(Qt.UserRole)
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除标签 \"{lbl.name}\" 吗？\n此操作将同时删除文件和登记记录。",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        try:
            self.dataset_manager.remove_label(lbl.name, delete_file=True)
            self._refresh_media()
        except Exception as e:
            QMessageBox.critical(self, "删除失败", f"删除标签失败:\n{str(e)}")

    def _on_scan_dir(self):
        """扫描用户选择的文件夹，复制并导入所有视频/图片/标签到项目内"""
        dir_path = QFileDialog.getExistingDirectory(
            self, "选择要扫描的文件夹", ""
        )
        if not dir_path:
            return
        try:
            result = self.dataset_manager.scan_media_dir(target_dir=dir_path, copy_files=True)
            self._refresh_media()
            v_n = len(result["videos"])
            i_n = len(result["images"])
            l_n = len(result["labels"])
            total = v_n + i_n + l_n
            if total == 0:
                QMessageBox.information(self, "扫描完成", "未发现新素材（视频/图片/标签）")
            else:
                lines = []
                if v_n:
                    lines.append(f"视频 {v_n} 个:\n" + "\n".join(m.name for m in result["videos"]))
                if i_n:
                    lines.append(f"图片 {i_n} 个:\n" + "\n".join(m.name for m in result["images"]))
                if l_n:
                    lines.append(f"标签 {l_n} 个:\n" + "\n".join(l.name for l in result["labels"]))
                QMessageBox.information(
                    self, "扫描完成",
                    f"已导入 {total} 个新素材:\n\n" + "\n\n".join(lines)
                )
        except Exception as e:
            QMessageBox.critical(self, "扫描失败", f"扫描文件夹失败:\n{str(e)}")

    def _on_delete(self):
        """批量删除：选择类型（视频/图片/标签），指定起止编号，直接删除"""
        video_count = self.video_list.count()
        image_count = self.image_labeled_list.count() + self.image_unlabeled_list.count()
        label_count = self.label_list.count()
        if video_count == 0 and image_count == 0 and label_count == 0:
            QMessageBox.warning(self, "提示", "当前没有素材可删除")
            return

        # 自定义对话框：类型选择 + 起止编号
        dialog = QDialog(self)
        dialog.setWindowTitle("批量删除")
        form = QFormLayout(dialog)

        # 类型选择
        type_layout = QHBoxLayout()
        rb_video = QRadioButton(f"视频 ({video_count})")
        rb_video.setEnabled(video_count > 0)
        rb_image = QRadioButton(f"图片 ({image_count})")
        rb_image.setEnabled(image_count > 0)
        rb_label = QRadioButton(f"标签 ({label_count})")
        rb_label.setEnabled(label_count > 0)
        # 默认选中第一个可用类型
        if video_count > 0:
            rb_video.setChecked(True)
        elif image_count > 0:
            rb_image.setChecked(True)
        else:
            rb_label.setChecked(True)
        type_layout.addWidget(rb_video)
        type_layout.addWidget(rb_image)
        type_layout.addWidget(rb_label)
        type_layout.addStretch()
        form.addRow("删除类型:", type_layout)

        start_spin = QSpinBox(dialog)
        end_spin = QSpinBox(dialog)
        form.addRow("起始编号:", start_spin)
        form.addRow("结束编号:", end_spin)

        # 用 QButtonGroup 管理互斥，buttonClicked 只在用户切换时触发一次
        type_group = QButtonGroup(dialog)
        type_group.setExclusive(True)
        type_group.addButton(rb_video, 0)
        type_group.addButton(rb_image, 1)
        type_group.addButton(rb_label, 2)

        def update_range(btn_id=None):
            # btn_id 来自 buttonClicked 信号；None 时为初始调用
            if btn_id is None:
                btn_id = type_group.checkedId()
            if btn_id == 0:
                n = video_count
            elif btn_id == 1:
                n = image_count
            else:
                n = label_count
            n = max(n, 1)
            start_spin.setRange(1, n)
            end_spin.setRange(1, n)
            start_spin.setValue(1)
            end_spin.setValue(n)

        type_group.buttonClicked.connect(update_range)
        update_range()  # 初始化范围

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=dialog)
        btns.accepted.connect(dialog.accept)
        btns.rejected.connect(dialog.reject)
        form.addRow(btns)
        if dialog.exec_() != QDialog.Accepted:
            return

        # 根据类型收集目标
        if rb_video.isChecked():
            target_lists = [self.video_list]
            is_label = False
        elif rb_image.isChecked():
            target_lists = [self.image_labeled_list, self.image_unlabeled_list]
            is_label = False
        else:
            target_lists = [self.label_list]
            is_label = True

        start = start_spin.value()
        end = end_spin.value()
        if start > end:
            start, end = end, start

        targets = []
        for target_list in target_lists:
            for i in range(target_list.count()):
                item = target_list.item(i)
                idx = item.data(Qt.UserRole + 1)
                if start <= idx <= end:
                    obj = item.data(Qt.UserRole)
                    targets.append((idx, obj.name))

        if not targets:
            QMessageBox.information(self, "提示", "指定编号范围内没有素材")
            return

        deleted = 0
        errors = []
        for idx, name in targets:
            try:
                if is_label:
                    self.dataset_manager.remove_label(name, delete_file=True)
                else:
                    self.dataset_manager.remove_media(name, delete_file=True)
                deleted += 1
            except Exception as e:
                errors.append(f"{idx:03d}. {name}: {str(e)}")

        self._refresh_media()

        if errors:
            QMessageBox.warning(
                self, "部分删除失败",
                f"成功删除 {deleted} 个，失败 {len(errors)} 个:\n" + "\n".join(errors)
            )
        else:
            QMessageBox.information(self, "删除完成", f"已删除 {deleted} 个")

    def _on_extract_frames(self):
        if not self._current_media:
            QMessageBox.warning(self, "提示", "请先选择一个视频素材")
            return
        if self._current_media.media_type != "video":
            QMessageBox.warning(self, "提示", "只能对视频素材进行抽帧")
            return
        interval, ok = QInputDialog.getInt(
            self, "抽帧间隔", "请输入抽帧间隔（每 N 帧抽取 1 帧）:", 15, 1, 300
        )
        if not ok:
            return
        try:
            media_path = self._resolve_media_path(self._current_media.path)
            count = self.dataset_manager.extract_frames(str(media_path), interval)
            self._refresh_media()
            QMessageBox.information(self, "抽帧完成", f"成功抽取 {count} 帧，已自动加入图片素材。")
        except Exception as e:
            QMessageBox.critical(self, "抽帧失败", f"抽帧失败:\n{str(e)}")

    def _on_annotate(self):
        """打开标签标注窗口"""
        images = [m for m in self.dataset_manager.list_media() if m.media_type == "image"]
        if not images:
            QMessageBox.warning(self, "提示", "当前没有图片素材可标注，请先导入图片或抽帧")
            return
        dialog = LabelEditorDialog(self.project_root, self.dataset_manager, self)
        dialog.showMaximized()
        if dialog.exec_() == QDialog.Accepted:
            self._refresh_media()

    # ---------- 分类管理 ----------

    def _refresh_cat_list(self, checked_names=None, enabled=True):
        """刷新分类列表，保留勾选状态，并可控制列表是否可用"""
        if checked_names is None:
            checked_names = set()
        self.cat_list.blockSignals(True)
        self.cat_list.clear()
        for cat in self.dataset_manager.list_categories():
            item = QListWidgetItem(cat)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if cat in checked_names else Qt.Unchecked)
            self.cat_list.addItem(item)
        self.cat_list.blockSignals(False)
        self.cat_list.setEnabled(enabled)
        self._update_cat_stats()

    def _refresh_cat_checkstate(self, m):
        """选中已标注图片时，刷新分类勾选状态，启用列表"""
        cats = m.categories or []
        self._refresh_cat_list(set(cats), enabled=True)

    def _clear_cat_checkstate(self):
        """未标注图片/视频/标签时，清空勾选，禁用列表"""
        self._refresh_cat_list(set(), enabled=False)

    def _on_cat_check_changed(self, item):
        """勾选/取消勾选分类时，立即保存到所有选中的已标注图片（支持 Shift 多选批量打勾）"""
        # 收集所有选中的已标注图片
        selected_items = self.image_labeled_list.selectedItems()
        if not selected_items:
            return
        # 收集当前所有勾选的分类
        checked = []
        for i in range(self.cat_list.count()):
            it = self.cat_list.item(i)
            if it.checkState() == Qt.Checked:
                checked.append(it.text())
        # 批量保存到每张选中的已标注图片
        for sel_item in selected_items:
            m = sel_item.data(Qt.UserRole)
            if not self.dataset_manager.has_label_for(m.name):
                continue  # 未标注图片不参与分类
            self.dataset_manager.set_media_categories(m.name, checked)
            m.categories = list(checked)
            # 更新列表项显示
            self._refresh_image_labeled_item_text(m.name, checked)
        # 更新媒体信息区（显示当前 currentItem）
        if self._current_media:
            self._show_info(self._current_media)
        self._update_cat_stats()

    def _update_cat_stats(self):
        cats = self.dataset_manager.list_categories()
        labeled_count = self.image_labeled_list.count()
        lines = [f"已标注图片: {labeled_count} 张 | 分类数: {len(cats)}"]
        for cat in cats:
            count = len(self.dataset_manager.list_media_by_category(cat))
            lines.append(f"  · {cat}: {count} 张")
        self.cat_stats_label.setText("\n".join(lines))

    def _refresh_image_labeled_item_text(self, name, categories):
        """更新已标注图片列表中指定项的文本（追加分类后缀）"""
        for i in range(self.image_labeled_list.count()):
            item = self.image_labeled_list.item(i)
            m = item.data(Qt.UserRole)
            if m.name == name:
                cats_str = f"  [{', '.join(categories)}]" if categories else ""
                item.setText(f"{i+1:03d}. {name}{cats_str}")
                break

    def _on_new_category(self):
        name, ok = QInputDialog.getText(self, "新建分类", "分类名称:")
        if ok and name.strip():
            name = name.strip()
            self.dataset_manager.add_category(name)
            # 保留当前选中素材的勾选状态
            checked = set()
            if self._current_media and self._current_media.media_type == "image":
                checked = set(self._current_media.categories or [])
            self._refresh_cat_list(checked)

    def _on_rename_category(self):
        current = self.cat_list.currentItem()
        if not current:
            QMessageBox.information(self, "提示", "请先选择要重命名的分类")
            return
        old_name = current.text()
        new_name, ok = QInputDialog.getText(self, "重命名分类", "新名称:", text=old_name)
        if ok and new_name.strip() and new_name.strip() != old_name:
            self.dataset_manager.rename_category(old_name, new_name.strip())
            self._refresh_media()
            if self._current_media:
                self._refresh_cat_checkstate(self._current_media)

    def _on_delete_category(self):
        current = self.cat_list.currentItem()
        if not current:
            QMessageBox.information(self, "提示", "请先选择要删除的分类")
            return
        name = current.text()
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定删除分类 '{name}' 吗？\n素材本身不会被删除，仅移除分类归属。"
        )
        if reply == QMessageBox.Yes:
            self.dataset_manager.delete_category(name)
            self._refresh_media()
            if self._current_media:
                self._refresh_cat_checkstate(self._current_media)

    # ---------- 外部接口 ----------

    def get_selected_media(self):
        """获取当前选中的媒体信息，供其他页面调用"""
        return self._current_media

    def resizeEvent(self, event):
        """窗口大小变化时，重新缩放预览图"""
        if self._current_media:
            self._show_preview(self._current_media)
        super().resizeEvent(event)
