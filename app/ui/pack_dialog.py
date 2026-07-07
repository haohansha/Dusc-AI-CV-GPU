"""素材打包对话框：管理已标注图片素材的分类归属"""

from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QSplitter, QGroupBox,
    QListWidget, QListWidgetItem, QLabel, QPushButton,
    QMessageBox, QInputDialog
)


class PackDialog(QDialog):
    """双栏分类管理器：左栏已标注图片素材，右栏分类列表（带勾选）"""

    def __init__(self, project_root, dataset_manager, parent=None):
        super().__init__(parent)
        self.project_root = Path(project_root)
        self.dataset_manager = dataset_manager
        self._image_map = {}  # name -> MediaInfo
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        self.setWindowTitle("素材打包")
        self.setMinimumSize(1000, 640)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # 顶部说明
        hint = QLabel("将已标注的图片素材归入分类，便于后续训练按分类选择。同一素材可属于多个分类。")
        hint.setWordWrap(True)
        hint.setStyleSheet("QLabel { color: #666666; font-size: 12px; }")
        layout.addWidget(hint)

        # 双栏 splitter
        splitter = QSplitter(Qt.Horizontal)

        # === 左栏：已标注图片素材列表 ===
        left_group = QGroupBox("已标注图片素材")
        left_layout = QVBoxLayout(left_group)
        self.image_list = QListWidget()
        self.image_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.image_list.currentItemChanged.connect(self._on_image_selected)
        left_layout.addWidget(self.image_list, 1)
        # 显示当前选中素材的分类归属
        self.current_cats_label = QLabel("未选择素材")
        self.current_cats_label.setWordWrap(True)
        self.current_cats_label.setStyleSheet("QLabel { color: #333333; font-size: 12px; padding: 4px; }")
        left_layout.addWidget(self.current_cats_label)
        splitter.addWidget(left_group)

        # === 右栏：分类管理 ===
        right_group = QGroupBox("分类管理")
        right_layout = QVBoxLayout(right_group)

        # 分类操作按钮
        cat_btn_row = QHBoxLayout()
        self.btn_new_cat = QPushButton("新建分类")
        self.btn_new_cat.clicked.connect(self._on_new_category)
        self.btn_rename_cat = QPushButton("重命名")
        self.btn_rename_cat.clicked.connect(self._on_rename_category)
        self.btn_del_cat = QPushButton("删除分类")
        self.btn_del_cat.clicked.connect(self._on_delete_category)
        cat_btn_row.addWidget(self.btn_new_cat)
        cat_btn_row.addWidget(self.btn_rename_cat)
        cat_btn_row.addWidget(self.btn_del_cat)
        cat_btn_row.addStretch()
        right_layout.addLayout(cat_btn_row)

        right_layout.addWidget(QLabel("勾选分类可将当前选中的素材归入该分类："))

        # 分类列表（带勾选框）
        self.cat_list = QListWidget()
        self.cat_list.itemChanged.connect(self._on_cat_check_changed)
        right_layout.addWidget(self.cat_list, 1)

        # 统计信息
        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet("QLabel { color: #666666; font-size: 12px; padding: 4px; }")
        self.stats_label.setWordWrap(True)
        right_layout.addWidget(self.stats_label)

        splitter.addWidget(right_group)
        splitter.setSizes([600, 400])
        layout.addWidget(splitter, 1)

        # 底部关闭按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_close = QPushButton("关闭")
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

    def _load_data(self):
        """加载已标注图片素材和分类列表"""
        # 1. 加载已标注图片
        all_media = self.dataset_manager.list_media()
        labeled_images = [m for m in all_media
                          if m.media_type == "image"
                          and self.dataset_manager.has_label_for(m.name)]
        self._image_map = {}
        self.image_list.clear()
        for i, m in enumerate(labeled_images, 1):
            # 显示分类归属在列表项中
            cats_str = f"  [{', '.join(m.categories)}]" if m.categories else ""
            item = QListWidgetItem(f"{i:03d}. {m.name}{cats_str}")
            item.setData(Qt.UserRole, m.name)
            self.image_list.addItem(item)
            self._image_map[m.name] = m

        # 2. 加载分类列表
        self._refresh_cat_list()
        self._update_stats()

    def _refresh_cat_list(self, checked_names=None):
        """刷新分类列表，保留勾选状态"""
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

    def _on_image_selected(self, current, previous):
        """选中素材时，刷新分类勾选状态以反映该素材的归属"""
        if current is None:
            self.current_cats_label.setText("未选择素材")
            self._refresh_cat_list(set())
            return
        name = current.data(Qt.UserRole)
        m = self._image_map.get(name)
        if not m:
            return
        cats = m.categories or []
        self.current_cats_label.setText(
            f"当前: {name}\n分类: {', '.join(cats) if cats else '无'}"
        )
        self._refresh_cat_list(set(cats))

    def _on_cat_check_changed(self, item):
        """勾选/取消勾选分类时，立即保存到当前选中的素材"""
        current = self.image_list.currentItem()
        if current is None:
            return
        name = current.data(Qt.UserRole)
        # 收集当前所有勾选的分类
        checked = []
        for i in range(self.cat_list.count()):
            it = self.cat_list.item(i)
            if it.checkState() == Qt.Checked:
                checked.append(it.text())
        self.dataset_manager.set_media_categories(name, checked)
        # 更新本地缓存
        self._image_map[name].categories = checked
        # 更新列表项显示
        cats_str = f"  [{', '.join(checked)}]" if checked else ""
        current.setText(f"{self.image_list.currentRow() + 1:03d}. {name}{cats_str}")
        # 更新当前素材信息
        self.current_cats_label.setText(
            f"当前: {name}\n分类: {', '.join(checked) if checked else '无'}"
        )
        self._update_stats()

    def _on_new_category(self):
        name, ok = QInputDialog.getText(self, "新建分类", "分类名称:")
        if ok and name.strip():
            name = name.strip()
            self.dataset_manager.add_category(name)
            # 保留当前选中素材的勾选状态
            current = self.image_list.currentItem()
            checked = set()
            if current:
                m = self._image_map.get(current.data(Qt.UserRole))
                if m:
                    checked = set(m.categories or [])
            self._refresh_cat_list(checked)
            self._update_stats()

    def _on_rename_category(self):
        current = self.cat_list.currentItem()
        if not current:
            QMessageBox.information(self, "提示", "请先选择要重命名的分类")
            return
        old_name = current.text()
        new_name, ok = QInputDialog.getText(self, "重命名分类", "新名称:", text=old_name)
        if ok and new_name.strip() and new_name.strip() != old_name:
            self.dataset_manager.rename_category(old_name, new_name.strip())
            self._load_data()

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
            self._load_data()

    def _update_stats(self):
        cats = self.dataset_manager.list_categories()
        total = self.image_list.count()
        lines = [f"已标注图片: {total} 张 | 分类数: {len(cats)}"]
        for cat in cats:
            count = len(self.dataset_manager.list_media_by_category(cat))
            lines.append(f"  · {cat}: {count} 张")
        self.stats_label.setText("\n".join(lines))
