import sys
from PySide6.QtWidgets import QGraphicsItem, QMenu, QFileDialog, QInputDialog, QLineEdit
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QPen, QBrush, QPainterPath, QFontMetrics, QFont, QPixmap

class GraphNode(QGraphicsItem):
    def __init__(self, node_id, node_type="Data", label="Unknown"):
        super().__init__()
        self.node_id = node_id
        self.node_type = node_type
        self.label = label
        
        self.width = 160
        self.height = 40
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        
        self.edges = []
        self.image_path = None
        self.pixmap = None
        
        self.base_color = QColor("#2d2d2d")
        self.border_color = QColor("#555555")

    def set_image(self, path):
        self.image_path = path
        px = QPixmap(path)
        if not px.isNull():
            self.pixmap = px.scaled(self.width, self.height, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            self.update()

    def boundingRect(self):
        return QRectF(-self.width/2 - 10, -self.height/2 - 10, self.width + 20, self.height + 20)

    def paint(self, painter, option, widget):
        path = QPainterPath()
        rect = QRectF(-self.width/2, -self.height/2, self.width, self.height)
        path.addRoundedRect(rect, 8, 8)
        
        painter.save()
        painter.setClipPath(path)
        
        if self.pixmap:
            painter.drawPixmap(-self.width/2, -self.height/2, self.width, self.height, self.pixmap)
            # Add darken overlay
            painter.setBrush(QBrush(QColor(0, 0, 0, 150)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(rect)
        else:
            painter.setBrush(QBrush(self.base_color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(rect)
            
        painter.restore()
        
        if self.isSelected():
            painter.setPen(QPen(QColor("#ffffff"), 2))
        else:
            painter.setPen(QPen(self.border_color, 1))
            
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)
        
        # Label
        painter.setPen(QPen(QColor("#ffffff")))
        font = QFont("Arial", 10)
        painter.setFont(font)
        fm = QFontMetrics(font)
        elided_label = fm.elidedText(self.label, Qt.TextElideMode.ElideRight, int(self.width - 20))
        painter.drawText(QRectF(-self.width/2 + 10, -self.height/2, self.width - 20, self.height), Qt.AlignmentFlag.AlignCenter, elided_label)

        # Draw connection ports
        painter.setPen(QPen(QColor("#777777"), 1))
        painter.setBrush(QBrush(QColor("#2d2d2d")))
        painter.drawEllipse(QRectF(-self.width/2 - 4, -4, 8, 8))
        painter.drawEllipse(QRectF(self.width/2 - 4, -4, 8, 8))
        painter.drawEllipse(QRectF(-4, -self.height/2 - 4, 8, 8))
        painter.drawEllipse(QRectF(-4, self.height/2 - 4, 8, 8))

    def left_port_rect(self):
        return QRectF(-self.width/2 - 6, -6, 12, 12)

    def right_port_rect(self):
        return QRectF(self.width/2 - 6, -6, 12, 12)

    def top_port_rect(self):
        return QRectF(-6, -self.height/2 - 6, 12, 12)

    def bottom_port_rect(self):
        return QRectF(-6, self.height/2 - 6, 12, 12)

    def mousePressEvent(self, event):
        pos = event.pos()
        if self.left_port_rect().contains(pos):
             self.start_edge_creation('left', pos)
             event.accept()
        elif self.right_port_rect().contains(pos):
             self.start_edge_creation('right', pos)
             event.accept()
        elif self.top_port_rect().contains(pos):
             self.start_edge_creation('top', pos)
             event.accept()
        elif self.bottom_port_rect().contains(pos):
             self.start_edge_creation('bottom', pos)
             event.accept()
        else:
            self.is_connecting = False
            super().mousePressEvent(event)

    def start_edge_creation(self, port, pos):
        self.is_connecting = True
        view = self.scene().views()[0]
        if port == 'left': center = self.left_port_rect().center()
        elif port == 'right': center = self.right_port_rect().center()
        elif port == 'top': center = self.top_port_rect().center()
        else: center = self.bottom_port_rect().center()
        view.start_temp_edge(self.mapToScene(center), port)

    def mouseMoveEvent(self, event):
        if hasattr(self, 'is_connecting') and self.is_connecting:
            view = self.scene().views()[0]
            view.update_temp_edge(self.mapToScene(event.pos()))
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if hasattr(self, 'is_connecting') and self.is_connecting:
            self.is_connecting = False
            view = self.scene().views()[0]
            view.finish_temp_edge(self.mapToScene(event.pos()), self)
            event.accept()
        else:
            if event.button() == Qt.MouseButton.RightButton:
                pass # Event handles right click differently
            super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu()
        edit_action = menu.addAction("Edit Text")
        img_action = menu.addAction("Set Image")
        comment_action = menu.addAction("Leave Comment")
        del_action = menu.addAction("Delete Node")
        
        action = menu.exec(event.screenPos())
        view = self.scene().views()[0]
        
        if action == edit_action:
            new_label, ok = QInputDialog.getText(view, "Edit Node", "Enter new text:", QLineEdit.EchoMode.Normal, self.label)
            if ok and new_label:
                self.label = new_label
                view.nx_graph.nodes[self.node_id]['label'] = new_label
                self.update()
                view.save_history()
        elif action == img_action:
            path, _ = QFileDialog.getOpenFileName(view, "Select Image", "", "Images (*.png *.jpg *.jpeg *.bmp)")
            if path:
                self.set_image(path)
                view.nx_graph.nodes[self.node_id]['image'] = path
                view.save_history()
        elif action == comment_action:
            if hasattr(view.main_window, 'notes_panel'):
                view.main_window.notes_panel.focus_comment(self.node_id)
        elif action == del_action:
            view.remove_node(self)

    def mouseDoubleClickEvent(self, event):
        view = self.scene().views()[0]
        new_label, ok = QInputDialog.getText(view, "Edit Node", "Enter new text:", QLineEdit.EchoMode.Normal, self.label)
        if ok and new_label:
            self.label = new_label
            view.nx_graph.nodes[self.node_id]['label'] = new_label
            self.update()
            if hasattr(view.main_window, 'notes_panel') and view.main_window.notes_panel.current_node_id == self.node_id:
                view.main_window.notes_panel.node_info_label.setText(f"Notes for: {self.label}")
            view.save_history()
        super().mouseDoubleClickEvent(event)

    def add_edge(self, edge):
        self.edges.append(edge)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for edge in self.edges:
                edge.update_position()
        return super().itemChange(change, value)

