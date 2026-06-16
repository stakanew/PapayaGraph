import networkx as nx
import random
import re
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QMenu, QMessageBox, QInputDialog, QGraphicsPathItem
from PySide6.QtGui import QPainter, QAction, QMouseEvent, QGuiApplication, QKeySequence, QPen, QColor, QPainterPath
from PySide6.QtCore import Qt, QPointF, QTimer
from graph_node import GraphNode
from graph_edge import GraphEdge
from transforms import TransformEngine

class GraphCanvas(QGraphicsView):
    def __init__(self, main_window=None):
        super().__init__(main_window)
        self.main_window = main_window
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing | 
            QPainter.RenderHint.TextAntialiasing | 
            QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        
        self.setStyleSheet("background-color: #1e1e1e; border: none;")
        self.scene.setSceneRect(-5000, -5000, 10000, 10000)
        self.scene.selectionChanged.connect(self.on_selection_changed)
        
        self.nx_graph = nx.MultiDiGraph()
        self.nodes_dict = {}
        
        self._zoom = 1.0
        self.active_transforms = []
        
        self.history = []
        self.history_index = -1
        self.is_restoring = False
        
        # Initial nodes for demo
        self.add_node("n1", "Data", "Ivan Ivanov")
        self.add_node("n2", "Email", "ivan@example.com")
        self.add_edge("n1", "n2", "owns")
        self.save_history()
        
        # 3D Sim / force layout timer
        self.sim_timer = QTimer()
        self.sim_timer.timeout.connect(self.tick_simulation)
        self.layout_target_pos = {}
        self.is_simulating = False

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.StandardKey.Paste):
            text = QGuiApplication.clipboard().text()
            if text:
                self.handle_paste(text)
        elif event.matches(QKeySequence.StandardKey.Undo):
            if self.history_index > 0:
                self.history_index -= 1
                self.restore_history(self.history_index)
        elif event.matches(QKeySequence.StandardKey.Redo):
            if self.history_index < len(self.history) - 1:
                self.history_index += 1
                self.restore_history(self.history_index)
        elif event.matches(QKeySequence.StandardKey.Delete):
            deleted = False
            for item in self.scene.selectedItems():
                if isinstance(item, GraphNode):
                    self.remove_node(item)
                    deleted = True
            if deleted:
                self.save_history()
        else:
            super().keyPressEvent(event)

    def handle_paste(self, text):
        text = text.strip()
        if not text: return
        node_type = "Data"
        if re.match(r'^\+?\d{10,15}$', text):
            node_type = "Phone"
        elif re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', text):
            node_type = "Email"
        elif re.match(r'^(1|3)[a-km-zA-HJ-NP-Z1-9]{25,34}$', text) or text.startswith('bc1'):
            node_type = "Crypto"
        elif re.match(r'^0x[a-fA-F0-9]{40}$', text):
            node_type = "Crypto"
        elif re.match(r'^@[\w\d_]+$', text) or text.startswith("t.me/"):
            node_type = "Social"
        elif re.match(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', text):
            node_type = "Domain"
        elif re.match(r'^[A-ZА-Я]{1}\d{3}[A-ZА-Я]{2}\d{2,3}$', text, re.IGNORECASE) or re.match(r'^[A-HJ-NPR-Z0-9]{17}$', text, re.IGNORECASE):
            node_type = "Car"
        elif len(text.split()) == 3 and all(len(w) > 2 for w in text.split()):
            node_type = "Person"
            
        pos = self.mapToScene(self.viewport().rect().center())
        pos.setX(pos.x() + random.randint(-50, 50))
        pos.setY(pos.y() + random.randint(-50, 50))
        
        node_id = f"node_{random.randint(1000, 99999)}"
        self.add_node(node_id, node_type, text, pos)
        self.save_history()

    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            zoom_factor = 1.15
            self._zoom *= zoom_factor
        else:
            zoom_factor = 1 / 1.15
            self._zoom *= zoom_factor
            
        self.scale(zoom_factor, zoom_factor)
        
    def on_selection_changed(self):
        if self.main_window and self.main_window.notes_panel:
            selected = self.scene.selectedItems()
            if selected and isinstance(selected[0], GraphNode):
                node = selected[0]
                self.main_window.notes_panel.load_node_notes(node.node_id, node.label)
        
    def contextMenuEvent(self, event):
        item = self.itemAt(event.pos())
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #2d2d2d; color: #ffffff; border: 1px solid #444; }
            QMenu::item:selected { background-color: #ff8c00; }
        """)
        
        if isinstance(item, GraphNode):
            node = item
            
            action_transform = menu.addMenu("Run Transform...")
            transforms = []
            if node.node_type == "Person":
                transforms = ["Find Social Media", "Find Email", "Find Phone", "Find Person Profiles"]
            elif node.node_type == "Email":
                transforms = ["Check Breaches", "Find Registrations"]
            elif node.node_type == "Domain":
                transforms = ["WHOIS", "Find Subdomains"]
            elif node.node_type == "Phone":
                transforms = ["Find Operator", "Find Phone Entities"]
            elif node.node_type == "IP":
                transforms = ["Geolocation"]
            elif node.node_type == "Car":
                transforms = ["Check Auto Drom/Avito"]
            elif node.node_type == "Crypto":
                transforms = ["Check Balance"]
            else:
                transforms = ["Extract Entities", "Search Web", "Check Nickname"]
                
            trans_actions = {}
            for t in transforms:
                trans_actions[t] = action_transform.addAction(t)
                
            menu.addSeparator()
            action_delete = QAction("Delete Node", self)
            menu.addAction(action_delete)
            
            action = menu.exec(event.globalPos())
            
            if action == action_delete:
                self.remove_node(node)
            else:
                for t, act in trans_actions.items():
                    if action == act:
                        self.run_transform(node, t)
        else:
            action_add = QAction("Add Custom Node", self)
            menu.addAction(action_add)
            
            action = menu.exec(event.globalPos())
            if action == action_add:
                new_label, ok = QInputDialog.getText(self, "Add Node", "Enter node text:")
                if ok and new_label:
                    scene_pos = self.mapToScene(event.pos())
                    node_id = f"node_{random.randint(1000, 99999)}"
                    self.add_node(node_id, "Document", new_label, scene_pos)

    def run_transform(self, node, transform_name):
        engine = TransformEngine(node.node_id, node.node_type, node.label, transform_name)
        engine.finished.connect(self.on_transform_finished)
        engine.error.connect(self.on_transform_error)
        engine.progress_update.connect(lambda msg: self.main_window.status_bar.showMessage(msg, 5000) if self.main_window else None)
        self.active_transforms.append(engine)
        engine.start()
        
        if self.main_window:
            self.main_window.status_bar.showMessage(f"Running transform '{transform_name}' on {node.label}...", 5000)

    def on_transform_error(self, err_msg):
        if self.main_window:
            QMessageBox.warning(self.main_window, "Transform Error", f"An error occurred: {err_msg}")

    def on_transform_finished(self, source_node_id, new_nodes_data):
        if source_node_id not in self.nodes_dict: return
        source_node = self.nodes_dict[source_node_id]
        
        center_x = source_node.pos().x()
        center_y = source_node.pos().y()
        radius = 120
        
        import math
        angle_step = (2 * math.pi) / len(new_nodes_data) if new_nodes_data else 0
        
        for i, data in enumerate(new_nodes_data):
            angle = i * angle_step
            nx_pos = center_x + radius * math.cos(angle)
            ny_pos = center_y + radius * math.sin(angle)
            
            # Check for duplicates by value (label + type)
            existing_id = None
            for nid, node_obj in self.nodes_dict.items():
                if node_obj.label == data["label"] and node_obj.node_type == data["type"]:
                    existing_id = nid
                    break
            
            if existing_id:
                if not self.nx_graph.has_edge(source_node_id, existing_id) and not self.nx_graph.has_edge(existing_id, source_node_id):
                     self.add_edge(source_node_id, existing_id, data["edge_label"])
            else:
                new_id = f"node_{random.randint(1000, 99999)}"
                self.add_node(new_id, data["type"], data["label"], QPointF(nx_pos, ny_pos))
                self.add_edge(source_node_id, new_id, data["edge_label"])
            
        self.save_history()

    def add_node(self, node_id, node_type, label, position=None):
        if node_id in self.nodes_dict: return self.nodes_dict[node_id]
        
        from datetime import datetime
        self.nx_graph.add_node(node_id, type=node_type, label=label, timestamp=datetime.now())
        node = GraphNode(node_id, node_type, label)
        
        if position:
            node.setPos(position)
        else:
            node.setPos(random.randint(-150, 150), random.randint(-150, 150))
            
        self.scene.addItem(node)
        self.nodes_dict[node_id] = node
        return node
        
    def start_temp_edge(self, start_pos, source_port):
        self.temp_edge = QGraphicsPathItem()
        self.temp_edge.setPen(QPen(QColor("#ff8c00"), 2, Qt.PenStyle.DashLine))
        self.temp_edge.setZValue(100)
        self.scene.addItem(self.temp_edge)
        self.temp_edge_start = start_pos
        self.temp_edge_source_port = source_port

    def update_temp_edge(self, end_pos):
        if hasattr(self, 'temp_edge') and self.temp_edge:
            path = QPainterPath(self.temp_edge_start)
            sp = getattr(self, 'temp_edge_source_port', 'right')
            if sp in ('left', 'right'):
                control1_offset = QPointF(30 if sp == 'right' else -30, 0)
            else:
                control1_offset = QPointF(0, 30 if sp == 'bottom' else -30)
            path.cubicTo(self.temp_edge_start + control1_offset, end_pos, end_pos)
            self.temp_edge.setPath(path)

    def finish_temp_edge(self, end_pos, source_node):
        source_port = getattr(self, 'temp_edge_source_port', 'right')
        if hasattr(self, 'temp_edge') and self.temp_edge:
            self.scene.removeItem(self.temp_edge)
            self.temp_edge = None
            
        item = self.scene.itemAt(end_pos, self.transform())
        # We need to find if we hit a specific port or just the node
        target_port = 'left'
        
        while item and not isinstance(item, GraphNode):
            item = item.parentItem()
            
        if item and item != source_node and isinstance(item, GraphNode):
            # Calculate which port is closest to end_pos
            local_pos = item.mapFromScene(end_pos)
            d_left = (local_pos.x() - item.left_port_rect().center().x())**2 + (local_pos.y() - item.left_port_rect().center().y())**2
            d_right = (local_pos.x() - item.right_port_rect().center().x())**2 + (local_pos.y() - item.right_port_rect().center().y())**2
            d_top = (local_pos.x() - item.top_port_rect().center().x())**2 + (local_pos.y() - item.top_port_rect().center().y())**2
            d_bottom = (local_pos.x() - item.bottom_port_rect().center().x())**2 + (local_pos.y() - item.bottom_port_rect().center().y())**2
            
            min_d = min(d_left, d_right, d_top, d_bottom)
            if min_d == d_left: target_port = 'left'
            elif min_d == d_right: target_port = 'right'
            elif min_d == d_top: target_port = 'top'
            else: target_port = 'bottom'

            if self.nx_graph.has_edge(source_node.node_id, item.node_id) or self.nx_graph.has_edge(item.node_id, source_node.node_id):
                self.remove_edge(source_node.node_id, item.node_id)
            else:
                self.add_edge(source_node.node_id, item.node_id, "", source_port, target_port)
            self.save_history()

    def remove_edge(self, source_id, target_id):
        edges_to_remove = []
        if source_id in self.nodes_dict and target_id in self.nodes_dict:
            source = self.nodes_dict[source_id]
            target = self.nodes_dict[target_id]
            for edge in source.edges:
                if (edge.source_node == source and edge.target_node == target) or \
                   (edge.source_node == target and edge.target_node == source):
                    edges_to_remove.append(edge)
            
            for edge in edges_to_remove:
                if edge.scene() == self.scene:
                    self.scene.removeItem(edge)
                if edge in edge.source_node.edges: edge.source_node.edges.remove(edge)
                if edge in edge.target_node.edges: edge.target_node.edges.remove(edge)

        while self.nx_graph.has_edge(source_id, target_id):
            self.nx_graph.remove_edge(source_id, target_id)
        while self.nx_graph.has_edge(target_id, source_id):
            self.nx_graph.remove_edge(target_id, source_id)

    def add_edge(self, source_id, target_id, label="", source_port='right', target_port='left'):
        if source_id not in self.nodes_dict or target_id not in self.nodes_dict: return
        self.nx_graph.add_edge(source_id, target_id, label=label, source_port=source_port, target_port=target_port)
        
        edge = GraphEdge(self.nodes_dict[source_id], self.nodes_dict[target_id], label, source_port, target_port)
        self.scene.addItem(edge)
        return edge

    def remove_node(self, node):
        for edge in list(node.edges):
            if edge.scene() == self.scene:
                self.scene.removeItem(edge)
            if edge in edge.source_node.edges:
                edge.source_node.edges.remove(edge)
            if edge in edge.target_node.edges:
                edge.target_node.edges.remove(edge)
        
        if node.node_id in self.nx_graph:
            self.nx_graph.remove_node(node.node_id)
        if node.node_id in self.nodes_dict:
            del self.nodes_dict[node.node_id]
            
        if node.scene() == self.scene:
            self.scene.removeItem(node)
        
    def save_history(self):
        if self.is_restoring: return
        state = {
            'nodes': {nid: {'label': d.get('label', ''), 'type': d.get('type', ''), 'image': d.get('image', ''), 'x': self.nodes_dict[nid].x(), 'y': self.nodes_dict[nid].y()} for nid, d in self.nx_graph.nodes(data=True)},
            'edges': [(u, v, d.get('label', ''), d.get('source_port', 'right'), d.get('target_port', 'left')) for u, v, k, d in self.nx_graph.edges(keys=True, data=True)]
        }
        self.history = self.history[:self.history_index+1]
        self.history.append(state)
        # Check size to prevent memory leaks if many actions
        if len(self.history) > 50:
            self.history.pop(0)
        else:
            self.history_index = len(self.history) - 1
            
    def restore_history(self, index):
        if index < 0 or index >= len(self.history): return
        self.is_restoring = True
        state = self.history[index]
        
        for node in list(self.nodes_dict.values()):
            self.remove_node(node)
            
        self.nx_graph.clear()
        self.nodes_dict.clear()
        
        for nid, d in state['nodes'].items():
            node = self.add_node(nid, d['type'], d['label'], QPointF(d['x'], d['y']))
            if d.get('image'):
                node.set_image(d['image'])
                self.nx_graph.nodes[nid]['image'] = d['image']
                
        for edge_data in state['edges']:
            u = edge_data[0]
            v = edge_data[1]
            l = edge_data[2]
            sp = edge_data[3] if len(edge_data) > 3 else 'right'
            tp = edge_data[4] if len(edge_data) > 4 else 'left'
            self.add_edge(u, v, l, sp, tp)
            
        self.scene.update()
        if self.main_window and hasattr(self.main_window, 'graph_canvas_3d'):
             self.main_window.graph_canvas_3d.sync_from_main()
             
        self.is_restoring = False
        
    def apply_layout(self, layout_type="force"):
        if not self.nodes_dict: return
        
        self.is_simulating = False
        self.sim_timer.stop()
        
        if layout_type == "force":
            pos = nx.spring_layout(self.nx_graph, scale=400, k=2)
        elif layout_type == "spider_web":
            # Kamada Kawai creates excellent Spider Web 2D topologies
            try:
                pos = nx.kamada_kawai_layout(self.nx_graph, scale=500)
            except:
                pos = nx.spring_layout(self.nx_graph, scale=500, k=1.5)
        elif layout_type == "circular":
            pos = nx.circular_layout(self.nx_graph, scale=400)
        elif layout_type == "hierarchical":
            try:
                pos = nx.multipartite_layout(self.nx_graph, scale=500)
            except:
                pos = nx.shell_layout(self.nx_graph, scale=500)
        else:
            pos = nx.spring_layout(self.nx_graph, scale=400)
            
        self.layout_target_pos = pos
        self.is_simulating = True
        self.sim_timer.start(30) # animate transition
        
    def tick_simulation(self):
        moved = False
        for node_id, target in self.layout_target_pos.items():
            if node_id in self.nodes_dict:
                node = self.nodes_dict[node_id]
                cx, cy = node.pos().x(), node.pos().y()
                tx, ty = target[0], target[1]
                
                dx = tx - cx
                dy = ty - cy
                
                if abs(dx) > 1 or abs(dy) > 1:
                    node.setPos(cx + dx * 0.1, cy + dy * 0.1)
                    moved = True
                    
        if not moved:
            self.is_simulating = False
            self.sim_timer.stop()
