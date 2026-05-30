import os
import random
import shutil
from pathlib import Path


def prepare_dataset(frames_dir, original_dataset_dir, output_dir, val_split=0.2):
    frames_dir = Path(frames_dir)
    original_dataset_dir = Path(original_dataset_dir)
    output_dir = Path(output_dir)

    ann_files = sorted(frames_dir.glob("*.txt"))
    paired = []
    for ann_file in ann_files:
        img_file_jpg = frames_dir / (ann_file.stem + ".jpg")
        img_file_jpeg = frames_dir / (ann_file.stem + ".jpeg")
        img_file_png = frames_dir / (ann_file.stem + ".png")
        if img_file_jpg.exists():
            paired.append((img_file_jpg, ann_file))
        elif img_file_jpeg.exists():
            paired.append((img_file_jpeg, ann_file))
        elif img_file_png.exists():
            paired.append((img_file_png, ann_file))

    if not paired:
        print("Error: No paired (image + label) files found in", frames_dir)
        return

    random.seed(42)
    random.shuffle(paired)
    n_val = max(1, int(len(paired) * val_split))
    train_pairs = paired[n_val:]
    val_pairs = paired[:n_val]

    train_img_dir = output_dir / "train" / "images"
    train_lbl_dir = output_dir / "train" / "labels"
    val_img_dir = output_dir / "val" / "images"
    val_lbl_dir = output_dir / "val" / "labels"

    for d in [train_img_dir, train_lbl_dir, val_img_dir, val_lbl_dir]:
        d.mkdir(parents=True, exist_ok=True)

    for img, lbl in train_pairs:
        shutil.copy2(img, train_img_dir / img.name)
        shutil.copy2(lbl, train_lbl_dir / lbl.name)
    for img, lbl in val_pairs:
        shutil.copy2(img, val_img_dir / img.name)
        shutil.copy2(lbl, val_lbl_dir / lbl.name)

    print(f"Factory annotation frames:")
    print(f"  Total paired: {len(paired)}")
    print(f"  Train: {len(train_pairs)}")
    print(f"  Val:   {len(val_pairs)}")

    orig_train_img = original_dataset_dir / "train" / "images"
    orig_train_lbl = original_dataset_dir / "train" / "labels"
    orig_count = 0

    if orig_train_img.exists() and orig_train_lbl.exists():
        orig_imgs = sorted(orig_train_img.glob("*.jpg"))
        for img in orig_imgs:
            lbl = orig_train_lbl / (img.stem + ".txt")
            if lbl.exists():
                with open(lbl) as f:
                    new_lines = []
                    for line in f:
                        parts = line.strip().split()
                        if not parts:
                            continue
                        cls_id = int(parts[0])
                        if cls_id == 2:  # smoke -> 0
                            new_lines.append(f"0 {' '.join(parts[1:])}\n")
                    if new_lines:
                        shutil.copy2(img, train_img_dir / img.name)
                        with open(train_lbl_dir / lbl.name, "w") as fw:
                            fw.writelines(new_lines)
                        with open(lbl) as fr:
                            orig_lines = [line for line in fr if line.strip()]
                            orig_smoke = sum(1 for l in orig_lines if int(l.split()[0]) == 2)
                        print(f"  [smoke] {img.name}: {orig_smoke} smoke boxes")
                        orig_count += 1

    print(f"\nOriginal dataset smoke images added to train: {orig_count}")
    total_train_img = len(list(train_img_dir.glob("*")))
    total_train_lbl = len(list(train_lbl_dir.glob("*")))
    total_val_img = len(list(val_img_dir.glob("*")))
    total_val_lbl = len(list(val_lbl_dir.glob("*")))

    print(f"\nFinal dataset:")
    print(f"  Train: {total_train_img} images, {total_train_lbl} labels")
    print(f"  Val:   {total_val_img} images, {total_val_lbl} labels")

    data_yaml = output_dir / "data.yaml"
    data_yaml.write_text(
        f"path: {output_dir.as_posix()}\n"
        "train: train/images\n"
        "val: val/images\n\n"
        "nc: 1\n"
        "names:\n"
        "  0: smoke\n"
    )
    print(f"\nConfig written to: {data_yaml}")


def main():
    project_root = Path(__file__).parent.parent
    frames_dir = project_root / "data" / "factory_frames"
    original_dataset_dir = project_root / "data" / "smoke_dataset"
    output_dir = project_root / "data" / "factory_dataset"

    output_dir.mkdir(parents=True, exist_ok=True)

    for existing in output_dir.glob("*"):
        if existing.is_dir():
            shutil.rmtree(existing)
        else:
            existing.unlink()

    prepare_dataset(frames_dir, original_dataset_dir, output_dir, val_split=0.2)


if __name__ == "__main__":
    main()
