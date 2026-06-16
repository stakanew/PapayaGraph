import json
import networkx as nx
from PySide6.QtWidgets import QFileDialog, QMessageBox
from PySide6.QtCore import QPointF
from PySide6.QtGui import QImage, QPainter

class ImportExport:
    def __init__(self, main_window):
        self.main_window = main_window

    def save_project(self):
        file_name, _ = QFileDialog.getSaveFileName(self.main_window, "Save Project", "", "Papaya Project (*.papaya)")
        if not file_name:
            return
        self._export_to_file(file_name)
        self.main_window.status_bar.showMessage(f"Project saved to {file_name}", 5000)

    def _export_to_file(self, file_name):
        data = {"nodes": [], "edges": []}
        canvas = self.main_window.graph_canvas
        
        for node_id, node in canvas.nodes_dict.items():
            nx_data = canvas.nx_graph.nodes.get(node_id, {})
            node_data = {
                "id": node_id,
                "type": node.node_type,
                "label": node.label,
                "x": node.pos().x(),
                "y": node.pos().y(),
                "image": node.image_path
            }
            if "timestamp" in nx_data:
                node_data["timestamp"] = nx_data["timestamp"].isoformat()
            data["nodes"].append(node_data)
            
        for u, v, k, data_dict in canvas.nx_graph.edges(keys=True, data=True):
            data["edges"].append({
                "source": u,
                "target": v,
                "label": data_dict.get("label", ""),
                "source_port": data_dict.get("source_port", "right"),
                "target_port": data_dict.get("target_port", "left")
            })
            
        with open(file_name, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

    def save_project_auto(self):
        try:
            self._export_to_file("autosave.papaya")
            # Silently save to simulate sync with friends as well
        except Exception:
            pass

    def open_project(self):
        file_name, _ = QFileDialog.getOpenFileName(self.main_window, "Open Project", "", "Papaya Project (*.papaya);;JSON Files (*.json)")
        if not file_name:
            return
        self._import_from_file(file_name)
        self.main_window.status_bar.showMessage(f"Project loaded from {file_name}", 5000)

    def load_project_auto(self):
        import os
        if os.path.exists("autosave.papaya"):
            self._import_from_file("autosave.papaya")

    def _import_from_file(self, file_name):
        with open(file_name, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        canvas = self.main_window.graph_canvas
        # clear graph
        for node in list(canvas.nodes_dict.values()):
            canvas.remove_node(node)
            
        for node_data in data.get("nodes", []):
            pos = QPointF(node_data.get("x", 0), node_data.get("y", 0))
            node = canvas.add_node(node_data["id"], node_data["type"], node_data["label"], pos)
            image = node_data.get("image")
            if image:
                node.set_image(image)
                canvas.nx_graph.nodes[node_data["id"]]['image'] = image
            if "timestamp" in node_data:
                from datetime import datetime
                try:
                    canvas.nx_graph.nodes[node_data["id"]]['timestamp'] = datetime.fromisoformat(node_data["timestamp"])
                except Exception:
                    pass
            
        for edge_data in data.get("edges", []):
            canvas.add_edge(edge_data["source"], edge_data["target"], edge_data.get("label", ""), edge_data.get("source_port", "right"), edge_data.get("target_port", "left"))
            
        self.main_window.update_counters()
        self.main_window.status_bar.showMessage(f"Project loaded from {file_name}", 5000)

    def export_png(self):
        file_name, _ = QFileDialog.getSaveFileName(self.main_window, "Export PNG", "", "PNG Image (*.png)")
        if not file_name:
            return
            
        canvas = self.main_window.graph_canvas
        rect = canvas.scene.itemsBoundingRect()
        if rect.isEmpty():
            return
            
        image = QImage(int(rect.width() + 100), int(rect.height() + 100), QImage.Format.Format_ARGB32)
        image.fill(0x1e1e1e) # dark bg
        
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        canvas.scene.render(painter, target=image.rect(), source=rect.adjusted(-50, -50, 50, 50))
        painter.end()
        
        image.save(file_name)
        self.main_window.status_bar.showMessage(f"Graph exported to {file_name}", 5000)

    def export_gexf(self):
        file_name, _ = QFileDialog.getSaveFileName(self.main_window, "Export GEXF", "", "GEXF Graph (*.gexf)")
        if not file_name:
            return
            
        nx.write_gexf(self.main_window.graph_canvas.nx_graph, file_name)
        self.main_window.status_bar.showMessage(f"Graph exported to {file_name}", 5000)
