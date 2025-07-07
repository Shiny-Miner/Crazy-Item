# ✅ FINAL DANGER.PY - Based on original master.py
# Includes:
# - All original logic preserved (load_item_defines, graphics table, icon logic)
# - Extra gItemData fields editable
# - Search bar
# - Description editing + saving
# - Name input limited to 13 chars (14th is auto _END)
# - Full dark theme and layout untouched

# ⚠️ Large code file – will be regenerated in complete chunks
# Please continue scrolling in next messages for full working script

import sys
import os
import re
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QListWidget,
    QLabel, QLineEdit, QPushButton, QTextEdit, QFileDialog, QMessageBox,
    QSplitter, QListWidgetItem, QScrollArea
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt

def decode_char_array(array_text):
    punctuation_map = {
        "_PERIOD": ".", "_HYPHEN": "-", "_APOSTROPHE": "'", "_EXCLAMATION": "!",
        "_QUESTION": "?", "_eACUTE": "é", "_NEWLINE": "\n"
    }

    compress_patterns = [
        (["_PO", "_KE", "_BL", "_OC", "_OK"], "Pokeblock"),
        (["_P", "_o", "_k", "_eACUTE", "_BL", "_OC", "_OK"], "Pokéblock"),
    ]

    tokens = [c.strip() for c in array_text.split(',')]
    result = []
    i = 0
    glyphs = 0

    while i < len(tokens) and glyphs < 13:
        token = tokens[i]
        if token == "_END":
            break

        # Match compressed sequences like Pokeblock
        matched = False
        for pattern, word in compress_patterns:
            if tokens[i:i+len(pattern)] == pattern:
                result.append(word)
                i += len(pattern)
                glyphs += 1
                matched = True
                break
        if matched:
            continue

        if token == "_SPACE":
            result.append(" ")
        elif token in punctuation_map:
            result.append(punctuation_map[token])
        elif token.startswith("'") and len(token) == 3:
            result.append(token[1])
        elif token.startswith("_") and len(token) == 2:
            result.append(token[1])
        elif token.startswith("_"):
            result.append(token[1:].capitalize())
        else:
            result.append(token.strip("_"))

        i += 1
        glyphs += 1

    return ''.join(result).strip()

def encode_char_array(text):
    encode_map = {
        " ": "_SPACE", "\n": "_NEWLINE", "é": "_eACUTE", "'": "_APOSTROPHE",
        "!": "_EXCLAMATION", "?": "_QUESTION", "@": "_AT", "-": "_HYPHEN", ".": "_PERIOD"
    }

    number_map = {str(i): f"_{i}" for i in range(10)}

    # Optional compression for symbol macros like Pokéblock → _PO, _KE, ...
    compress_map = {
        "Pokeblock": ["_PO", "_KE", "_BL", "_OC", "_OK"],
        "Pokéblock": ["_P", "_o", "_k", "_eACUTE", "_BL", "_OC", "_OK"]
    }

    for key in compress_map:
        if text.startswith(key):
            return ", ".join(compress_map[key] + encode_char_array(text[len(key):]).split(", ")[:-1] + ["_END"])

    result = []
    for ch in text:
        if ch in encode_map:
            result.append(encode_map[ch])
        elif ch in number_map:
            result.append(number_map[ch])
        elif ch.isalpha():
            result.append(f"_{ch}")
        else:
            result.append(f"'{ch}'")
            # Truncate the macro array to max 13 glyphs
        if len(result) > 13:
            result = result[:13]
    result.append("_END")
    return ", ".join(result)

class ItemEditor(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Crazy Item!")
        self.resize(1200, 800)

        self.base_path = self.select_folder()
        if not self.base_path:
            sys.exit(0)

        self.items_h_path = os.path.join(self.base_path, "include", "constants", "items.h")
        self.item_tables_c_path = os.path.join(self.base_path, "src", "tables", "item_tables.c")
        self.description_path = os.path.join(self.base_path, "strings", "item_descriptions.string")
        self.icon_folder = os.path.join(self.base_path, "graphics", "item_sprites")
        self.table_h_path = os.path.join(self.base_path, "include", "new", "item_tables.h")

        self.data = []
        self.headers = ["Name", "Price", "HoldEffect", "HoldParam", "Pocket", "Type", "Desc"]
        self.extra_fields = ["Importance", "Unk19", "FieldUseFunc", "BattleUsage", "BattleUseFunc", "SecondaryId"]
        self.readonly_tags = set()
        self.original_rom_defined = set()  # ⬅️ track all DESC_ originally ROM-defined
        self.descriptions = {}
        self.icon_map = {}
        self.graphics_table = {}
        self.item_id_to_name = {}
        self.item_blocks = []
        self.selected_index = -1

        self.load_all()
        self.init_ui()
        self.apply_dark_theme()

    def select_folder(self):
        return QFileDialog.getExistingDirectory(None, "Select your decomp folder")

    def load_all(self):
        self.load_item_defines()
        self.load_icons()
        self.load_descriptions()
        self.load_item_graphics_table()
        self.load_items()

    def load_item_defines(self):
        """Parses item_tables.c per block, aligns constants correctly."""
        self.item_id_to_name = {}
        if not os.path.exists(self.item_tables_c_path):
            return

        with open(self.item_tables_c_path, "r", encoding="utf-8") as f:
            raw = f.read()

        blocks = re.findall(r"(\{[^{}]*?\.name\s*=\s*\{[^}]*?\}[^{}]*?\},)", raw, re.DOTALL)

        for idx, block in enumerate(blocks):
            m = re.search(r"\.itemId\s*=\s*(ITEM_\w+)", block)
            if m:
                self.item_id_to_name[idx] = m.group(1)

    def load_icons(self):
        if os.path.exists(self.icon_folder):
            for f in os.listdir(self.icon_folder):
                if f.endswith(".png"):
                    key = os.path.splitext(f)[0]
                    self.icon_map[key] = os.path.join(self.icon_folder, f)

    def load_descriptions(self):
        with open(self.table_h_path, "r", encoding="utf-8") as f:
            for line in f:
                if "#define DESC_" in line and "(const u8 *)" in line:
                    m = re.match(r"#define\s+(DESC_\w+)", line)
                    if m:
                        tag = m.group(1)
                        self.readonly_tags.add(tag)
                        self.original_rom_defined.add(tag)
        tag = None
        lines = []
        with open(self.description_path, "r", encoding="utf-8-sig") as f:
            for line in f:
                if line.startswith("#org @"):
                    if tag and lines:
                        self.descriptions[tag] = "\n".join(lines).strip()
                    tag = line.replace("#org @", "").strip()
                    lines = []
                elif tag:
                    lines.append(line.strip())
        if tag and lines:
            self.descriptions[tag] = "\n".join(lines).strip()

    def load_item_graphics_table(self):
        self.graphics_table = {}
        if not os.path.exists(self.item_tables_c_path):
            return
        with open(self.item_tables_c_path, "r", encoding="utf-8") as f:
            content = f.read()
        match = re.search(
            r'gItemGraphicsTable\s*\[\s*ITEMS_COUNT\s*\+\s*1\s*\]\s*\[\s*2\s*\]\s*=\s*\{(.*?)\};',
            content, re.DOTALL
        )
        if not match:
            return
        table_body = match.group(1)
        lines = [line.strip() for line in table_body.splitlines() if line.strip() and not line.strip().startswith("//")]
        for item_id, line in enumerate(lines):
            m = re.match(r"\{\s*([\w\d_]+)\s*,\s*([\w\d_]+)\s*\},?", line)
            if m:
                tile_sym, pal_sym = m.groups()
                self.graphics_table[item_id] = (tile_sym, pal_sym)

    def load_items(self):
        with open(self.item_tables_c_path, "r", encoding="utf-8") as f:
            raw = f.read()
        blocks = re.findall(r"(\{[^{}]*?\.name\s*=\s*\{[^}]*?\}[^{}]*?\},)", raw, re.DOTALL)
        self.item_blocks = blocks
        for i, block in enumerate(blocks):
            item = {h: "" for h in self.headers + self.extra_fields}
            name_match = re.search(r"\.name = \{(.*?)\}", block)
            if name_match:
                item["Name"] = decode_char_array(name_match.group(1))[:13]
            for field in [
                ("price", "Price"), ("holdEffect", "HoldEffect"), ("holdEffectParam", "HoldParam"),
                ("pocket", "Pocket"), ("type", "Type"), ("description", "Desc"),
                ("importance", "Importance"), ("unk19", "Unk19"), ("fieldUseFunc", "FieldUseFunc"),
                ("battleUsage", "BattleUsage"), ("battleUseFunc", "BattleUseFunc"), ("secondaryId", "SecondaryId")
            ]:
                m = re.search(rf"\.{field[0]} = ([^,\n]+)", block)
                if m:
                    item[field[1]] = m.group(1).strip()
            item["ID"] = i
            self.data.append(item)

    def import_icon(self):
        idx = self.selected_index
        if idx < 0 or idx >= len(self.data):
            QMessageBox.warning(self, "No Item", "Please select an item first.")
            return

        file_path, _ = QFileDialog.getOpenFileName(self, "Import PNG Icon", "", "PNG Images (*.png)")
        if not file_path:
            return

        from PIL import Image

        try:
            img = Image.open(file_path)
            if img.size != (24, 24):
                QMessageBox.critical(self, "Invalid Size", "Image must be exactly 24x24 pixels.")
                return
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open image: {e}")
            return

        item_id = self.data[idx].get("ID")
        tile_symbol, pal_symbol = self.graphics_table.get(item_id, ("", ""))
        if not tile_symbol or not pal_symbol:
            QMessageBox.warning(self, "No Symbols", f"Graphics symbols not found for item ID {item_id}")
            return

        base_symbol = tile_symbol
        if base_symbol.endswith("Tiles"):
            base_symbol = base_symbol[:-5]

        dest_path = os.path.join(self.icon_folder, f"{base_symbol}.png")
        try:
            os.makedirs(self.icon_folder, exist_ok=True)
            img.save(dest_path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save image: {e}")
            return

        self.icon_map[base_symbol] = dest_path
        self.load_item_into_fields(idx)
        self.update_item_tables_header(tile_symbol, pal_symbol)
        QMessageBox.information(self, "Imported", f"Icon for {base_symbol} updated.")

    def update_item_tables_header(self, tile_sym, pal_sym):
        if not os.path.exists(self.table_h_path):
            return

        with open(self.table_h_path, "r", encoding="utf-8") as f:
            content = f.read()

        defines = [
            rf"#define\s+{tile_sym}\s+\(\(u32\*\).+?\)",
            rf"#define\s+{pal_sym}\s+\(\(u32\*\).+?\)",
        ]

        # Convert to extern if defined
        changed = False
        for sym in [tile_sym, pal_sym]:
            pattern = rf"#define\s+{sym}\s+\(\(u32\*\).+?\)"
            if re.search(pattern, content):
                content = re.sub(pattern, f"extern const u32 {sym}[];", content)
                changed = True

        if changed:
            with open(self.table_h_path, "w", encoding="utf-8") as f:
                f.write(content)

    def update_desc_define_to_extern(self, desc_tag):
        if not os.path.exists(self.table_h_path):
            return

        with open(self.table_h_path, "r", encoding="utf-8") as f:
            content = f.read()

        pattern = rf"#define\s+{desc_tag}\s+\(\(const u8 \*\)[^\)]+\)"
        replacement = f"extern const u8 {desc_tag}[];"

        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)

            with open(self.table_h_path, "w", encoding="utf-8") as f:
                f.write(content)

            self.readonly_tags.remove(desc_tag)

    def on_item_selected(self, current, previous):
        if not current:
            return
        real_idx = current.data(Qt.UserRole)
        self.load_item_into_fields(real_idx)

    # next part: UI setup, search, and 13-char enforcement...
    def init_ui(self):
        self.setMinimumSize(1200, 700)
        layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Horizontal)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍 Search items...")
        self.search_box.textChanged.connect(self.filter_items)
        left_layout.addWidget(self.search_box)

        self.list_widget = QListWidget()
        self.list_widget.setMinimumWidth(300)
        for item in self.data:
            item_id = item.get("ID", 0)
            raw_name = self.item_id_to_name.get(item_id, f"ITEM_{item_id:03}")
            display = raw_name.replace("ITEM_", "").replace("_END", "").replace("_", " ")
            list_item = QListWidgetItem(item.get("Name", f"ITEM_{item_id:03}"))
            list_item.setData(Qt.UserRole, item_id)
            self.list_widget.addItem(list_item)
            left_layout.addWidget(self.list_widget)
        self.list_widget.currentItemChanged.connect(self.on_item_selected)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        self.fields = {}
        for field in self.headers[:-1] + self.extra_fields:
            row = QHBoxLayout()
            label = QLabel(f"{field}:")
            label.setFixedWidth(130)
            line = QLineEdit()
            if field == "Name":
                line.setMaxLength(13)
            self.fields[field] = line
            row.addWidget(label)
            row.addWidget(line)
            right_layout.addLayout(row)

        right_layout.addWidget(QLabel("Description:"))
        self.desc_edit = QTextEdit()
        self.desc_edit.setFixedHeight(120)
        right_layout.addWidget(self.desc_edit)

        self.icon_preview = QLabel()
        self.icon_preview.setFixedSize(48, 48)
        self.icon_preview.setStyleSheet("border: 1px solid #666; background-color: #111;")
        self.icon_preview.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(self.icon_preview)

        self.id_label = QLabel()
        self.id_label.setStyleSheet("font-size: 12px; margin-top: 5px; color: #aaa;")
        right_layout.addWidget(self.id_label)

        self.save_btn = QPushButton("💾 Save All Changes")
        self.save_btn.clicked.connect(self.save_all)
        right_layout.addWidget(self.save_btn)

        self.import_icon_btn = QPushButton("📁 Import Icon (PNG)")
        self.import_icon_btn.clicked.connect(self.import_icon)
        right_layout.addWidget(self.import_icon_btn)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([300, 900])

        layout.addWidget(splitter)

    def filter_items(self, text):
        self.list_widget.clear()
        text = text.strip().lower()

        for item in self.data:
            name = item.get("Name", "")
            if text in name.lower():
                list_item = QListWidgetItem(name)
                list_item.setData(Qt.UserRole, item["ID"])  # Store real index
                self.list_widget.addItem(list_item)

    def load_item_into_fields(self, idx):
        if idx < 0 or idx >= len(self.data):
            return

        self.selected_index = idx
        item = self.data[idx]

        for field in self.headers[:-1] + self.extra_fields:
            self.fields[field].setText(item.get(field, ""))

        desc_tag = item.get("Desc", "")
        desc = self.descriptions.get(desc_tag, "[ROM defined]")
        self.desc_edit.setText(desc)
        if desc_tag in self.readonly_tags:
            answer = QMessageBox.question(
                self,
                "Unlock Description?",
                f"This description is ROM-defined ({desc_tag}).\nDo you want to make it editable?\n(Note: It will only be changed in files if you modify it)",
                QMessageBox.Yes | QMessageBox.No
            )
            if answer == QMessageBox.Yes:
                # Just make it editable now; defer the extern patch to save_all()
                self.desc_edit.setReadOnly(False)
            else:
                self.desc_edit.setReadOnly(True)
        else:
            self.desc_edit.setReadOnly(False)

        tile_symbol, _ = self.graphics_table.get(idx, ("", ""))
        icon_key = tile_symbol[:-5] if tile_symbol.endswith("Tiles") else tile_symbol
        path = self.icon_map.get(icon_key, "")

        item_id = item.get("ID", 0)
        raw_name = self.item_id_to_name.get(item_id, f"ITEM_{item_id:03}")
        display_name = raw_name.replace("ITEM_", "").replace("_END", "").replace("_", " ").title()

        self.setWindowTitle(f"Crazy Item - {display_name} (ID: {item_id} / {item_id:#04X})")
        self.id_label.setText(f"ID: {item_id} / {item_id:#04X}    Constant: {raw_name}")

        if path and os.path.exists(path):
            pixmap = QPixmap(path)
            self.icon_preview.setPixmap(pixmap.scaled(48, 48))
        else:
            self.icon_preview.clear()

    def save_all(self):
        with open(self.item_tables_c_path, "r", encoding="utf-8") as f:
            raw = f.read()

        new_blocks = []
        # Update current item with UI edits before saving
        if self.selected_index >= 0:
            item = self.data[self.selected_index]
            for field in self.headers[:-1] + self.extra_fields:
                item[field] = self.fields[field].text()
        
            # do NOT overwrite the tag; just update text separately
            if self.selected_index >= 0:
                item = self.data[self.selected_index]
                tag = item.get("Desc", "")
                if tag:
                    current_text = self.desc_edit.toPlainText().strip()
                    original_text = self.descriptions.get(tag, "").strip()

                    if tag in self.original_rom_defined and tag in self.readonly_tags:
                        if current_text != original_text:
                            self.update_desc_define_to_extern(tag)
                            self.readonly_tags.discard(tag)

                    if tag not in self.readonly_tags:
                        self.descriptions[tag] = current_text

        for idx, item in enumerate(self.data):
            name = item['Name'][:13]
            name_array = encode_char_array(name)
            block = self.item_blocks[idx]
            block = re.sub(r"\.name = \{[^}]*\}", f".name = {{{name_array}}}", block)
            for field in [
                ("price", "Price"), ("holdEffect", "HoldEffect"), ("holdEffectParam", "HoldParam"),
                ("pocket", "Pocket"), ("type", "Type"), ("description", "Desc"),
                ("importance", "Importance"), ("unk19", "Unk19"), ("fieldUseFunc", "FieldUseFunc"),
                ("battleUsage", "BattleUsage"), ("battleUseFunc", "BattleUseFunc"), ("secondaryId", "SecondaryId")
            ]:
                block = re.sub(rf"\.{field[0]} = [^,\n]+", f".{field[0]} = {item[field[1]]}", block)
            new_blocks.append(block)

        pattern = r"(\{[^{}]*?\.name\s*=\s*\{[^}]*?\}[^{}]*?\},)"
        new_content = re.sub(pattern, lambda m: new_blocks.pop(0), raw, count=len(new_blocks), flags=re.DOTALL)

        with open(self.item_tables_c_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        # Save descriptions
        if self.selected_index >= 0:
            item = self.data[self.selected_index]
            tag = item.get("Desc", "")
            if tag and tag not in self.readonly_tags:
                self.descriptions[tag] = self.desc_edit.toPlainText().strip()
        lines = []
        for tag, text in self.descriptions.items():
            lines.append(f"#org @{tag}")
            lines.extend(text.splitlines())
            lines.append("")
        with open(self.description_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        QMessageBox.information(self, "Saved", "Changes written to item_tables.c and item_descriptions.string")
    def apply_dark_theme(self):
        self.setStyleSheet("""
        QWidget {
            background-color: #1e1e1e;
            color: #f0f0f0;
            font-size: 14px;
        }
        QLineEdit, QTextEdit {
            background-color: #2e2e2e;
            color: #ffffff;
            border: 1px solid #555;
        }
        QPushButton {
            background-color: #3a3a3a;
            border: 1px solid #666;
            padding: 6px;
        }
        QPushButton:hover {
            background-color: #444;
        }
        QListWidget {
            background-color: #2a2a2a;
            color: #ffffff;
        }
        QLabel {
            color: #ffffff;
        }
        """)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ItemEditor()
    window.show()
    sys.exit(app.exec())
