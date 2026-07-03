# 修复"扫描目录"功能 — 改为用户选择文件夹

## 一、Summary

将数据管理页的"扫描目录"功能从硬编码扫描 `project_root/data` 改为弹出目录选择对话框，由用户自行选择要扫描的文件夹。扫描到的媒体文件**仅登记路径引用**（不复制），文件保留在用户选择的原始位置。需同步处理外部目录（项目外）的绝对路径存储与解析，确保预览、打开文件夹、抽帧、删除等功能对绝对路径同样有效。

## 二、Current State Analysis

### 当前实现（基于 Phase 1 探索）

| 位置 | 行号 | 现状 | 问题 |
|------|------|------|------|
| [data_page.py](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/data_page.py#L42-L44) | 42-44 | 按钮文案"扫描目录"，连接 `_on_scan_dir` | 文案需改为"扫描文件夹" |
| [data_page.py](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/data_page.py#L315-L329) | 315-329 | `_on_scan_dir` 直接调用 `scan_media_dir()` 无参数 | 缺少 `QFileDialog.getExistingDirectory` 目录选择 |
| [dataset_manager.py](file:///e:/project/Dusc%20AI%20CV%20GPU/modules/dataset_manager.py#L45-L99) | 45-99 | `scan_media_dir(self)` 硬编码 `data_dir = self.project_root / "data"` | 不接受外部目录参数 |
| [dataset_manager.py](file:///e:/project/Dusc%20AI%20CV%20GPU/modules/dataset_manager.py#L62) | 62 | `file_path.relative_to(self.project_root)` | 外部目录会抛 `ValueError` |
| [dataset_manager.py](file:///e:/project/Dusc%20AI%20CV%20GPU/modules/dataset_manager.py#L357) | 357 | `file_path = self.project_root / entry["path"]` | 绝对路径拼接会出错 |
| [data_page.py](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/data_page.py#L197) | 197 | `path = self.project_root / media_info.path` | 绝对路径拼接会出错 |
| [data_page.py](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/data_page.py#L363) | 363 | `media_path = self.project_root / self._current_media.path` | 绝对路径拼接会出错 |
| [data_page.py](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/data_page.py#L373) | 373 | `path = self.project_root / self._current_media.path` | 绝对路径拼接会出错 |

### Python Path 拼接行为关键点

```python
# 字符串拼接：绝对路径字符串会被当作相对路径处理（错误！）
Path("e:/proj") / "e:/external/file.mp4"
# Windows 结果: WindowsPath('e:/proj/e:/external/file.mp4')  ← 错误

# Path 对象拼接：右操作数为绝对路径时，直接返回右操作数（正确）
Path("e:/proj") / Path("e:/external/file.mp4")
# Windows 结果: WindowsPath('e:/external/file.mp4')  ← 正确
```

因此需要统一用 `Path` 对象 + `is_absolute()` 判断来解析路径，不能依赖字符串拼接。

## 三、Proposed Changes

### 修改 1：`dataset_manager.py` — `scan_media_dir` 接受目录参数 + 路径存储兼容绝对路径

**文件**：`e:\project\Dusc AI CV GPU\modules\dataset_manager.py`
**行号**：45-99

**改动**：
1. 方法签名：`def scan_media_dir(self):` → `def scan_media_dir(self, target_dir=None):`
2. 第 46 行目录解析：
   ```python
   if target_dir is not None:
       data_dir = Path(target_dir)
   else:
       data_dir = self.project_root / "data"
   ```
3. 第 62 行路径存储（区分项目内/外）：
   ```python
   try:
       stored_path = str(file_path.relative_to(self.project_root)).replace("\\", "/")
   except ValueError:
       # 文件在项目外，存绝对路径
       stored_path = str(file_path).replace("\\", "/")
   relative_path = stored_path  # 变量名保持以减少下游改动
   ```
4. 其余逻辑（视频元信息读取、registry 登记）保持不变。

### 修改 2：`dataset_manager.py` — `remove_media` 路径解析兼容绝对路径

**文件**：`e:\project\Dusc AI CV GPU\modules\dataset_manager.py`
**行号**：357

**改动**：
```python
# 原代码
file_path = self.project_root / entry["path"]

# 改为
raw_path = entry["path"]
p = Path(raw_path)
file_path = p if p.is_absolute() else self.project_root / p
```

### 修改 3：`data_page.py` — 按钮文案 + `_on_scan_dir` 加目录选择对话框

**文件**：`e:\project\Dusc AI CV GPU\app\ui\data_page.py`

**3a. 按钮文案**（第 42 行）：
```python
# 原
self.btn_scan = QPushButton("扫描目录")
# 改
self.btn_scan = QPushButton("扫描文件夹")
```

**3b. `_on_scan_dir` 方法**（第 315-329 行）：
```python
def _on_scan_dir(self):
    """扫描用户选择的文件夹，自动注册未登记的媒体文件（仅登记路径，不复制）"""
    dir_path = QFileDialog.getExistingDirectory(
        self, "选择要扫描的文件夹", ""
    )
    if not dir_path:
        return
    try:
        new_entries = self.dataset_manager.scan_media_dir(target_dir=dir_path)
        self._refresh_media()
        if new_entries:
            names = "\n".join(e.name for e in new_entries)
            QMessageBox.information(
                self, "扫描完成",
                f"在所选文件夹发现 {len(new_entries)} 个新素材:\n{names}"
            )
        else:
            QMessageBox.information(self, "扫描完成", "未发现新素材")
    except Exception as e:
        QMessageBox.critical(self, "扫描失败", f"扫描文件夹失败:\n{str(e)}")
```

方法名 `_on_scan_dir` 保持不变（内部实现细节，最小改动）。

### 修改 4：`data_page.py` — 新增路径解析辅助方法 + 3 处调用点替换

**文件**：`e:\project\Dusc AI CV GPU\app\ui\data_page.py`

**4a. 新增辅助方法**（放在 `_refresh_media` 之前，第 124 行附近）：
```python
def _resolve_media_path(self, path_str):
    """解析媒体路径：绝对路径直接返回，相对路径基于 project_root 拼接"""
    p = Path(path_str)
    return p if p.is_absolute() else self.project_root / p
```

**4b. `_show_preview`**（第 197 行）：
```python
# 原
path = self.project_root / media_info.path
# 改
path = self._resolve_media_path(media_info.path)
```

**4c. `_on_extract_frames`**（第 363 行）：
```python
# 原
media_path = self.project_root / self._current_media.path
# 改
media_path = self._resolve_media_path(self._current_media.path)
```

**4d. `_on_open_folder`**（第 373 行）：
```python
# 原
path = self.project_root / self._current_media.path
# 改
path = self._resolve_media_path(self._current_media.path)
```

## 四、Assumptions & Decisions

1. **仅登记不复制**：用户确认扫描到的文件仅登记路径引用，不复制到 `data/media`。文件保留在用户选择的原始位置。
2. **递归扫描**：保持原 `rglob("*")` 递归扫描行为，会扫描所选文件夹的所有子目录。
3. **去重逻辑不变**：registry 以文件名为 key，同名文件只登记第一个。此为原代码行为，本次不修改。若用户在不同目录扫描到同名文件，第二次会跳过。
4. **向后兼容**：`scan_media_dir(target_dir=None)` 不传参数时仍扫描默认 `data` 目录，保持原有调用路径可用。
5. **路径存储策略**：项目内文件存相对路径（兼容现有逻辑），项目外文件存绝对路径（正斜杠标准化）。
6. **方法名保持**：`_on_scan_dir` 方法名不改（内部实现），仅改按钮文案为"扫描文件夹"。

## 五、Verification Steps

### 5.1 静态验证
1. 启动应用，确认数据管理页按钮显示"扫描文件夹"（非"扫描目录"）。
2. 点击"扫描文件夹"，确认弹出目录选择对话框（非直接扫描）。
3. 对话框取消后无异常、无列表刷新。

### 5.2 功能验证 — 扫描项目内目录
1. 准备测试文件：在 `e:\project\Dusc AI CV GPU\data\` 下放一个测试视频（如 test_scan.mp4）。
2. 点击"扫描文件夹"，选择 `data` 目录。
3. 确认素材列表出现该视频，媒体信息中"路径"显示相对路径（如 `data/test_scan.mp4`）。
4. 选中该素材，确认预览图正常显示、媒体信息正确、点击"打开文件夹"能定位到正确目录。

### 5.3 功能验证 — 扫描项目外目录（关键）
1. 准备外部测试目录：如 `C:\temp\scan_test\`，放入一个测试视频和一个测试图片。
2. 点击"扫描文件夹"，选择 `C:\temp\scan_test`。
3. 确认素材列表出现这两个文件，媒体信息中"路径"显示**绝对路径**（如 `C:/temp/scan_test/xxx.mp4`）。
4. 选中视频素材，确认：
   - 预览图正常显示（验证 `_resolve_media_path` 对绝对路径有效）
   - 媒体信息（分辨率/帧率/时长）正确读取
   - 点击"打开文件夹"能打开 `C:\temp\scan_test`（验证绝对路径解析）
   - 点击"视频抽帧"能正常抽帧（验证绝对路径解析）
5. 选中图片素材，确认预览图正常显示。
6. 删除该外部素材，确认能正确删除登记记录（不删除原文件，验证 `remove_media` 路径解析）。

### 5.4 回归验证
1. "导入视频"功能仍正常（复制到 data/media，相对路径）。
2. "导入图片"功能仍正常。
3. 原有素材（若 registry 中已有）仍能正常预览、打开、删除。
