from PySide6.QtWidgets import QGraphicsItem
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QPainterPath, QFontMetrics, QFont

class GraphEdge(QGraphicsItem):
    def __init__(self, source_node, target_node, label="", source_port='right', target_port='left'):
        super().__init__()
        self.source_node = source_node
        self.target_node = target_node
        self.label = label
        self.source_port = source_port
        self.target_port = target_port
        
        self.source_node.add_edge(self)
        self.target_node.add_edge(self)
        
        self.setZValue(-1) # Send to back
        
    def update_position(self):
        self.prepareGeometryChange()
        
    def boundingRect(self):
        if not self.source_node or not self.target_node: return QRectF()
        
        def get_port_offset(node, port):
            if port == 'left': return QPointF(-node.width/2 - 4, 0)
            elif port == 'right': return QPointF(node.width/2 + 4, 0)
            elif port == 'top': return QPointF(0, -node.height/2 - 4)
            else: return QPointF(0, node.height/2 + 4)

        offset1 = get_port_offset(self.source_node, self.source_port)
        offset2 = get_port_offset(self.target_node, self.target_port)

        intersect1 = self.mapFromItem(self.source_node, offset1)
        intersect2 = self.mapFromItem(self.target_node, offset2)

        return QRectF(intersect1, intersect2).normalized().adjusted(-80, -80, 80, 80)
        
    def paint(self, painter, option, widget):
        if not self.source_node or not self.target_node: return
            
        def get_port_offset(node, port):
            if port == 'left': return QPointF(-node.width/2 - 4, 0)
            elif port == 'right': return QPointF(node.width/2 + 4, 0)
            elif port == 'top': return QPointF(0, -node.height/2 - 4)
            else: return QPointF(0, node.height/2 + 4)

        offset1 = get_port_offset(self.source_node, self.source_port)
        offset2 = get_port_offset(self.target_node, self.target_port)

        p1_local = self.source_node.scenePos() + offset1
        p2_local = self.target_node.scenePos() + offset2
        
        # We need it in the coordinate system of the edge (which is parented to the scene)
        intersect1 = self.mapFromItem(self.source_node, offset1)
        intersect2 = self.mapFromItem(self.target_node, offset2)

        # Bezier curve
        path = QPainterPath(intersect1)
        
        # Calculate control points for logic-like routing
        if self.source_port in ('left', 'right'):
            control1_offset = QPointF(30 if self.source_port == 'right' else -30, 0)
        else:
            control1_offset = QPointF(0, 30 if self.source_port == 'bottom' else -30)
            
        if self.target_port in ('left', 'right'):
            control2_offset = QPointF(30 if self.target_port == 'right' else -30, 0)
        else:
            control2_offset = QPointF(0, 30 if self.target_port == 'bottom' else -30)
            
        path.cubicTo(intersect1 + control1_offset, intersect2 + control2_offset, intersect2)

        
        painter.setPen(QPen(QColor("#555555"), 2, Qt.PenStyle.SolidLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)
        
        # Label
        if self.label:
            mid_point = path.pointAtPercent(0.5)
            font = QFont("Arial", 8)
            painter.setFont(font)
            fm = QFontMetrics(font)
            w = fm.horizontalAdvance(self.label)
            h = fm.height()
            
            bg_rect = QRectF(mid_point.x() - w/2 - 4, mid_point.y() - h/2 - 2, w + 8, h + 4)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#1e1e1e"))
            painter.drawRoundedRect(bg_rect, 4, 4)
            
            painter.setPen(QColor("#aaaaaa"))
            painter.drawText(bg_rect, Qt.AlignmentFlag.AlignCenter, self.label)
