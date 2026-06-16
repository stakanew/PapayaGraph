import sqlite3
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem, QLineEdit, 
    QPushButton, QHBoxLayout, QMessageBox, QTabWidget
)
from PySide6.QtCore import Qt, QTimer

class ChatPanel(QWidget):
    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window
        self.my_id = "USER_" + str(hash(self) % 10000)
        self.db_path = "papaya_collaboration.db"
        self.init_db()
        self.init_ui()
        
        # Fake online sync
        self.sync_timer = QTimer(self)
        self.sync_timer.timeout.connect(self.refresh_chat)
        self.sync_timer.start(2000)

    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS global_chat (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                author TEXT,
                content TEXT,
                node_link TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS friends (
                friend_id TEXT PRIMARY KEY,
                role TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Chat Tab
        chat_tab = QWidget()
        chat_layout = QVBoxLayout(chat_tab)
        chat_layout.setContentsMargins(0, 5, 0, 0)
        
        self.chat_list = QListWidget()
        self.chat_list.setStyleSheet("background-color: #1e1e1e; border: 1px solid #333;")
        self.chat_list.itemDoubleClicked.connect(self.on_chat_double_click)
        chat_layout.addWidget(self.chat_list)
        
        input_layout = QHBoxLayout()
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Message project...")
        self.chat_input.returnPressed.connect(self.send_chat)
        input_layout.addWidget(self.chat_input)
        
        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self.send_chat)
        input_layout.addWidget(self.send_btn)
        chat_layout.addLayout(input_layout)
        
        # Friends Tab
        friends_tab = QWidget()
        friends_layout = QVBoxLayout(friends_tab)
        friends_layout.setContentsMargins(0, 5, 0, 0)
        
        self.my_id_label = QLabel(f"My ID: {self.my_id}")
        self.my_id_label.setStyleSheet("color: #ff8c00; font-weight: bold;")
        friends_layout.addWidget(self.my_id_label)
        
        self.friends_list = QListWidget()
        friends_layout.addWidget(self.friends_list)
        
        add_friend_layout = QHBoxLayout()
        self.friend_id_input = QLineEdit()
        self.friend_id_input.setPlaceholderText("Friend ID...")
        add_friend_layout.addWidget(self.friend_id_input)
        
        self.add_friend_btn = QPushButton("Add")
        self.add_friend_btn.clicked.connect(self.add_friend)
        add_friend_layout.addWidget(self.add_friend_btn)
        friends_layout.addLayout(add_friend_layout)
        
        self.tabs.addTab(chat_tab, "Project Chat")
        self.tabs.addTab(friends_tab, "Friends")
        
        self.refresh_chat()
        self.refresh_friends()

    def refresh_chat(self):
        prev_count = self.chat_list.count()
        self.chat_list.clear()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT author, content, node_link, timestamp FROM global_chat ORDER BY timestamp ASC')
        for row in cursor.fetchall():
            author, content, node_link, ts = row
            text = f"[{ts[:16]}] {author}:\n{content}"
            if node_link: text += f"\n(Link: {node_link})"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, node_link)
            if author == "Me":
                item.setForeground(Qt.GlobalColor.cyan)
            else:
                item.setForeground(Qt.GlobalColor.white)
            self.chat_list.addItem(item)
        conn.close()
        
        if self.chat_list.count() > prev_count:
            self.chat_list.scrollToBottom()

    def send_chat(self):
        text = self.chat_input.text().strip()
        if not text: return
        
        node_link = None
        if self.main_window.graph_canvas.scene.selectedItems():
            selected = self.main_window.graph_canvas.scene.selectedItems()
            from graph_node import GraphNode
            if isinstance(selected[0], GraphNode):
                node_link = selected[0].node_id
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO global_chat (author, content, node_link)
            VALUES (?, ?, ?)
        ''', ("Me", text, node_link))
        conn.commit()
        conn.close()
        
        self.chat_input.clear()
        self.refresh_chat()

    def on_chat_double_click(self, item):
        node_link = item.data(Qt.ItemDataRole.UserRole)
        if node_link and self.main_window:
            canvas2d = self.main_window.graph_canvas
            if node_link in canvas2d.nodes_dict:
                node = canvas2d.nodes_dict[node_link]
                canvas2d.scene.clearSelection()
                node.setSelected(True)
                canvas2d.centerOn(node)
                
            canvas3d = self.main_window.graph_canvas_3d
            if node_link in canvas3d.nodes:
                canvas3d.selected_node = node_link
                # Focus camera on node (pan)
                n = canvas3d.nodes[node_link]
                canvas3d.pan_x = -n['x']
                canvas3d.pan_y = -n['y']
                self.main_window.stack.setCurrentIndex(1) # Switch to 3D maybe? Or stay in 2D

    def add_friend(self):
        fid = self.friend_id_input.text().strip()
        if not fid: return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO friends (friend_id, role) VALUES (?, ?)', (fid, "Editor"))
        conn.commit()
        conn.close()
        
        self.friend_id_input.clear()
        self.refresh_friends()

    def refresh_friends(self):
        self.friends_list.clear()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT friend_id, role FROM friends')
        for row in cursor.fetchall():
            fid, role = row
            item = QListWidgetItem(f"🟢 {fid} ({role})")
            self.friends_list.addItem(item)
        conn.close()
