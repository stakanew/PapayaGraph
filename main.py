import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QStatusBar, QLabel, QMessageBox, QStackedWidget,
    QLineEdit, QPushButton
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction

from graph_canvas import GraphCanvas
from graph_3d_canvas import Graph3DCanvas
from notes_panel import CommentsPanel
from chat_panel import ChatPanel
from import_export import ImportExport
from styles import apply_dark_theme

class PapayaGraphWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Papaya Graph")
        self.resize(1200, 800)
        
        self._graph_canvas_2d = None
        self.graph_canvas_3d = None
        self.stack = None
        
        self.notes_panel = None
        self.chat_panel = None
        
        self.import_export = ImportExport(self)
        
        self.init_ui()
        apply_dark_theme(QApplication.instance())
        
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.update_counters)
        self.refresh_timer.start(1000)
        
        self.autosave_timer = QTimer()
        self.autosave_timer.timeout.connect(self.import_export.save_project_auto)
        self.autosave_timer.start(3000)
        
        QTimer.singleShot(500, self.import_export.load_project_auto)

    @property
    def graph_canvas(self):
        return self._graph_canvas_2d

    def init_ui(self):
        self.setup_menu()
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Search panel
        search_widget = QWidget()
        search_layout = QHBoxLayout(search_widget)
        search_layout.setContentsMargins(10, 5, 10, 5)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter phone, email, nickname, domain, IP...")
        self.search_input.returnPressed.connect(self.perform_search)
        search_layout.addWidget(self.search_input)
        
        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(self.perform_search)
        search_layout.addWidget(self.search_btn)
        
        layout.addWidget(search_widget)
        
        # Main content
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        layout.addWidget(content_widget, 1) # stretch 1
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        self.stack = QStackedWidget()
        self._graph_canvas_2d = GraphCanvas(self)
        self.graph_canvas_3d = Graph3DCanvas(self)
        
        self.stack.addWidget(self._graph_canvas_2d)
        self.stack.addWidget(self.graph_canvas_3d)
        
        self.chat_panel = ChatPanel(self)
        self.notes_panel = CommentsPanel(self)
        
        splitter.addWidget(self.chat_panel)
        splitter.addWidget(self.stack)
        splitter.addWidget(self.notes_panel)
            
        splitter.setSizes([250, 650, 300])
        content_layout.addWidget(splitter)
        
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.update_counters()

    def perform_search(self):
        text = self.search_input.text().strip()
        if text:
            self.graph_canvas.handle_paste(text) # handles identification and node creation
            
            # Auto-run transforms corresponding to the search string to do a deep search
            # Need to get the newly created node
            node = list(self.graph_canvas.nodes_dict.values())[-1]
            
            if node.node_type == "Phone":
                self.graph_canvas.run_transform(node, "Find Phone Entities")
            elif node.node_type == "Email":
                self.graph_canvas.run_transform(node, "Check Breaches")
            elif node.node_type == "Social" or node.node_type == "Data": # nickname
                self.graph_canvas.run_transform(node, "Check Nickname")
            elif node.node_type == "Domain":
                self.graph_canvas.run_transform(node, "WHOIS")
            elif node.node_type == "IP":
                self.graph_canvas.run_transform(node, "Geolocation")
            elif node.node_type == "Crypto":
                self.graph_canvas.run_transform(node, "Check Balance")
            elif node.node_type == "Person":
                self.graph_canvas.run_transform(node, "Find Person Profiles")
            elif node.node_type == "Car":
                self.graph_canvas.run_transform(node, "Check Auto Drom/Avito")
            
            self.search_input.clear()

    def update_counters(self):
        if self.graph_canvas:
            nodes = len(self.graph_canvas.nodes_dict)
            edges = len(self.graph_canvas.nx_graph.edges)
            mode = "2D" if self.stack.currentIndex() == 0 else "3D"
            self.status_bar.showMessage(f"Ready | View: {mode} | Nodes: {nodes} | Edges: {edges}")

    def setup_menu(self):
        menubar = self.menuBar()
        
        # File Menu
        file_menu = menubar.addMenu("File")
        file_menu.addAction(QAction("New Project", self, triggered=self.new_project))
        file_menu.addAction(QAction("Open Project...", self, triggered=self.import_export.open_project))
        file_menu.addAction(QAction("Save Project", self, triggered=self.import_export.save_project))
        file_menu.addSeparator()
        
        export_menu = file_menu.addMenu("Export Graph")
        export_menu.addAction(QAction("Export as PNG...", self, triggered=self.import_export.export_png))
        export_menu.addAction(QAction("Export as GEXF...", self, triggered=self.import_export.export_gexf))
        
        file_menu.addSeparator()
        file_menu.addAction(QAction("Exit", self, triggered=self.close))
        
        # View Menu
        view_menu = menubar.addMenu("View")
        view_menu.addAction(QAction("Toggle 3D / 2D View", self, triggered=self.toggle_3d_view))
        view_menu.addSeparator()
        
        layout_menu = view_menu.addMenu("Graph Layout (2D)")
        layout_menu.addAction(QAction("Hierarchical (Top-Down)", self, triggered=lambda: self.graph_canvas.apply_layout("hierarchical")))
        layout_menu.addAction(QAction("Force-directed (Organic)", self, triggered=lambda: self.graph_canvas.apply_layout("force")))
        layout_menu.addAction(QAction("Spider Web (Kamada Kawai)", self, triggered=lambda: self.graph_canvas.apply_layout("spider_web")))
        layout_menu.addAction(QAction("Circular", self, triggered=lambda: self.graph_canvas.apply_layout("circular")))
        
    def toggle_3d_view(self):
        if self.stack.currentIndex() == 0:
            self.stack.setCurrentIndex(1)
            self.graph_canvas_3d.sync_from_main()
        else:
            self.stack.setCurrentIndex(0)
            
    def new_project(self):
        answer = QMessageBox.question(self, "New Project", "Clear current project?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if answer == QMessageBox.StandardButton.Yes:
            for node in list(self.graph_canvas.nodes_dict.values()):
                self.graph_canvas.remove_node(node)
            self.notes_panel.current_node_id = None
            self.notes_panel.input_field.setEnabled(False)
            self.notes_panel.node_info_label.setText("Select a node to edit notes.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PapayaGraphWindow()
    window.show()
    sys.exit(app.exec())
