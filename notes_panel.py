import sqlite3
import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTextEdit, QPushButton, QLabel, QHBoxLayout, 
    QListWidget, QListWidgetItem, QLineEdit, QScrollArea
)
from PySide6.QtCore import Qt

class CommentsPanel(QWidget):
    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window
        self.current_node_id = None
        self.db_path = "papaya_collaboration.db"
        self.init_db()
        self.init_ui()
        
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id TEXT,
                author TEXT,
                content TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        self.title_label = QLabel("Node Comments")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 16px; color: #ff8c00;")
        layout.addWidget(self.title_label)
        
        self.node_info_label = QLabel("Select a node to view comments.")
        self.node_info_label.setStyleSheet("color: #aaaaaa;")
        layout.addWidget(self.node_info_label)
        
        self.comments_list = QListWidget()
        self.comments_list.setStyleSheet("background-color: #1e1e1e; border: 1px solid #333;")
        layout.addWidget(self.comments_list)
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Write a comment...")
        self.input_field.setEnabled(False)
        self.input_field.returnPressed.connect(self.add_comment)
        layout.addWidget(self.input_field)
        
        self.send_btn = QPushButton("Send")
        self.send_btn.setEnabled(False)
        self.send_btn.clicked.connect(self.add_comment)
        layout.addWidget(self.send_btn)

    def load_node_notes(self, node_id, node_label):
        self.current_node_id = node_id
        self.node_info_label.setText(f"Comments for: {node_label}")
        self.input_field.setEnabled(True)
        self.send_btn.setEnabled(True)
        self.refresh_comments()
        
    def focus_comment(self, node_id):
        # We assume self.main_window selected it already
        self.input_field.setFocus()
        
    def refresh_comments(self):
        self.comments_list.clear()
        if not self.current_node_id: return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT author, content, timestamp FROM comments WHERE node_id = ? ORDER BY timestamp ASC', (self.current_node_id,))
        for row in cursor.fetchall():
            author, content, ts = row
            item = QListWidgetItem(f"[{ts[:16]}] {author}:\n{content}")
            if author == "Me":
                item.setForeground(Qt.GlobalColor.cyan)
            else:
                item.setForeground(Qt.GlobalColor.lightGray)
            self.comments_list.addItem(item)
        conn.close()
        self.comments_list.scrollToBottom()

    def add_comment(self):
        if not self.current_node_id: return
        text = self.input_field.text().strip()
        if not text: return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO comments (node_id, author, content)
            VALUES (?, ?, ?)
        ''', (self.current_node_id, "Me", text))
        conn.commit()
        conn.close()
        
        self.input_field.clear()
        self.refresh_comments()
