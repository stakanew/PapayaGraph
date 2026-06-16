import math
import random
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath, QFont, QFontMetrics
from PySide6.QtCore import Qt, QTimer, QPointF

class Graph3DCanvas(QWidget):
    def __init__(self, main_window=None):
        super().__init__(main_window)
        self.main_window = main_window
        
        self.setStyleSheet("background-color: #000000; border: none;")
        self.setMouseTracking(True)
        
        self.nodes = {}
        self.edges = []
        
        # Camera
        self.rot_x = 0.0
        self.rot_y = 0.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.zoom = 1.0
        self.camera_z = 1000.0
        
        self.last_pos = None
        self.mouse_btn = None
        
        self.hovered_node = None
        self.selected_node = None
        self.dragged_node = None
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.physics_step)
        self.timer.start(16)  # ~60 fps
        
    def fly_to_node(self, node_id):
        if node_id in self.nodes:
            self.selected_node = node_id
            n = self.nodes[node_id]
            # Center the camera on this node
            # We want sx, sy without pan to be at center
            # Project logic uses: sx = width/2 + pan_x + x1*scale
            # So to make sx = width/2, we need pan_x = -x1*scale
            
            x1 = n['x'] * math.cos(self.rot_y) - n['z'] * math.sin(self.rot_y)
            z1 = n['x'] * math.sin(self.rot_y) + n['z'] * math.cos(self.rot_y)
            y1 = n['y'] * math.cos(self.rot_x) - z1 * math.sin(self.rot_x)
            z2 = n['y'] * math.sin(self.rot_x) + z1 * math.cos(self.rot_x)
            
            z_dist = self.camera_z + z2
            if z_dist < 1: z_dist = 1
            f = 800.0
            
            self.target_zoom = 1.5
            scale = (f / z_dist) * self.target_zoom
            
            self.target_pan_x = -x1 * scale
            self.target_pan_y = -y1 * scale

    def apply_time_filter(self, current_ts):
        self.current_ts = current_ts

    def sync_from_main(self):
        if not self.main_window or not hasattr(self.main_window, 'graph_canvas'):
            return
            
        nx_graph = self.main_window.graph_canvas.nx_graph
        
        current_ids = set(self.nodes.keys())
        nx_ids = set(nx_graph.nodes.keys())
        
        from datetime import datetime
        
        for n in nx_ids - current_ids:
            ts = nx_graph.nodes[n].get('timestamp')
            if isinstance(ts, str):
                try: ts = datetime.fromisoformat(ts).timestamp()
                except: ts = 0
            elif ts: ts = ts.timestamp()
            else: ts = 0
                
            self.nodes[n] = {
                'id': n,
                'label': nx_graph.nodes[n].get('label', n),
                'x': random.uniform(-100, 100),
                'y': random.uniform(-100, 100),
                'z': random.uniform(-100, 100),
                'vx': 0, 'vy': 0, 'vz': 0,
                'ts': ts
            }
            
        for n in current_ids - nx_ids:
            del self.nodes[n]
            if self.hovered_node == n: self.hovered_node = None
            if self.selected_node == n: self.selected_node = None
            if self.dragged_node == n: self.dragged_node = None
            
        for n in nx_ids:
            if n in self.nodes:
                self.nodes[n]['label'] = nx_graph.nodes[n].get('label', n)
                ts = nx_graph.nodes[n].get('timestamp')
                if isinstance(ts, str):
                    try: ts = datetime.fromisoformat(ts).timestamp()
                    except: ts = 0
                elif ts: ts = ts.timestamp()
                else: ts = 0
                self.nodes[n]['ts'] = ts
                
        # Handle MultiDiGraph edges
        self.edges = []
        for u, v, k in nx_graph.edges(keys=True):
            self.edges.append((u, v, k))

    def project(self, x, y, z):
        # Rotate Y
        x1 = x * math.cos(self.rot_y) - z * math.sin(self.rot_y)
        z1 = x * math.sin(self.rot_y) + z * math.cos(self.rot_y)
        # Rotate X
        y1 = y * math.cos(self.rot_x) - z1 * math.sin(self.rot_x)
        z2 = y * math.sin(self.rot_x) + z1 * math.cos(self.rot_x)
        
        z_dist = self.camera_z + z2
        if z_dist < 1: z_dist = 1
        
        f = 800.0
        scale = (f / z_dist) * self.zoom
        
        sx = self.width() / 2 + self.pan_x + x1 * scale
        sy = self.height() / 2 + self.pan_y + y1 * scale
        
        return sx, sy, z2, scale

    def screen_to_world_delta(self, sdx, sdy, z2):
        z_dist = self.camera_z + z2
        if z_dist < 1: z_dist = 1
        scale = (800.0 / z_dist) * self.zoom
        
        cx = sdx / scale
        cy = sdy / scale
        cz = 0
        
        cy1 = cy * math.cos(-self.rot_x) - cz * math.sin(-self.rot_x)
        cz1 = cy * math.sin(-self.rot_x) + cz * math.cos(-self.rot_x)
        
        world_dx = cx * math.cos(-self.rot_y) - cz1 * math.sin(-self.rot_y)
        world_dz = cx * math.sin(-self.rot_y) + cz1 * math.cos(-self.rot_y)
        world_dy = cy1
        
        return world_dx, world_dy, world_dz

    def physics_step(self):
        if hasattr(self, 'target_pan_x'):
            # Interpolate towards target
            self.pan_x += (self.target_pan_x - self.pan_x) * 0.1
            self.pan_y += (self.target_pan_y - self.pan_y) * 0.1
            self.zoom += (self.target_zoom - self.zoom) * 0.1
            if abs(self.target_pan_x - self.pan_x) < 1.0 and abs(self.target_pan_y - self.pan_y) < 1.0:
                del self.target_pan_x
                del self.target_pan_y
                del self.target_zoom

        if not self.isVisible(): 
            return
            
        self.sync_from_main()
        
        nodes = list(self.nodes.values())
        node_by_id = self.nodes
        
        k_repel = 3000.0
        k_spring = 0.05
        ideal_length = 60.0
        k_gravity = 0.0005
        damping = 0.85
        
        forces = {n['id']: [0,0,0] for n in nodes}
        
        for i in range(len(nodes)):
            n1 = nodes[i]
            for j in range(i+1, len(nodes)):
                n2 = nodes[j]
                dx = n1['x'] - n2['x']
                dy = n1['y'] - n2['y']
                dz = n1['z'] - n2['z']
                dist_sq = dx*dx + dy*dy + dz*dz
                if dist_sq < 0.1:
                    dx += random.uniform(-0.1, 0.1)
                    dist_sq = 0.1
                
                if dist_sq < 100000:
                    dist = math.sqrt(dist_sq)
                    f = k_repel / dist_sq
                    fx = (dx / dist) * f
                    fy = (dy / dist) * f
                    fz = (dz / dist) * f
                    forces[n1['id']][0] += fx
                    forces[n1['id']][1] += fy
                    forces[n1['id']][2] += fz
                    forces[n2['id']][0] -= fx
                    forces[n2['id']][1] -= fy
                    forces[n2['id']][2] -= fz

        for u, v, _ in self.edges:
            if u in forces and v in forces:
                n1 = node_by_id[u]
                n2 = node_by_id[v]
                dx = n1['x'] - n2['x']
                dy = n1['y'] - n2['y']
                dz = n1['z'] - n2['z']
                dist = math.sqrt(dx*dx + dy*dy + dz*dz)
                if dist < 0.1: dist = 0.1
                
                diff = dist - ideal_length
                f = diff * k_spring
                fx = (dx / dist) * f
                fy = (dy / dist) * f
                fz = (dz / dist) * f
                
                forces[n1['id']][0] -= fx
                forces[n1['id']][1] -= fy
                forces[n1['id']][2] -= fz
                forces[n2['id']][0] += fx
                forces[n2['id']][1] += fy
                forces[n2['id']][2] += fz

        for n in nodes:
            fid = n['id']
            forces[fid][0] -= n['x'] * k_gravity
            forces[fid][1] -= n['y'] * k_gravity
            forces[fid][2] -= n['z'] * k_gravity
            
            forces[fid][0] += random.uniform(-0.2, 0.2)
            forces[fid][1] += random.uniform(-0.2, 0.2)
            forces[fid][2] += random.uniform(-0.2, 0.2)
            
            if self.dragged_node == fid:
                n['vx'] = 0
                n['vy'] = 0
                n['vz'] = 0
            else:
                n['vx'] = (n['vx'] + forces[fid][0]) * damping
                n['vy'] = (n['vy'] + forces[fid][1]) * damping
                n['vz'] = (n['vz'] + forces[fid][2]) * damping
                n['x'] += n['vx']
                n['y'] += n['vy']
                n['z'] += n['vz']
                
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#000000"))
        
        screen_data = {}
        for n in self.nodes.values():
            if hasattr(self, 'current_ts') and self.current_ts is not None:
                if n.get('ts', 0) > self.current_ts:
                    continue
            sx, sy, sz, scale = self.project(n['x'], n['y'], n['z'])
            screen_data[n['id']] = {'sx': sx, 'sy': sy, 'sz': sz, 'scale': scale, 'node': n}
            
        selected_edges = set()
        selected_nodes = set()
        if self.selected_node:
            selected_nodes.add(self.selected_node)
            for u, v, _ in self.edges:
                if u == self.selected_node:
                    selected_nodes.add(v)
                    selected_edges.add((u, v))
                elif v == self.selected_node:
                    selected_nodes.add(u)
                    selected_edges.add((u, v))
                    
        # Draw edges
        for u, v, _ in self.edges:
            if u in screen_data and v in screen_data:
                s1 = screen_data[u]
                s2 = screen_data[v]
                if self.selected_node:
                    if (u, v) in selected_edges or (v, u) in selected_edges:
                        painter.setPen(QPen(QColor(255, 255, 255, 200), 1.5))
                    else:
                        painter.setPen(QPen(QColor(100, 100, 100, 20), 0.5))
                else:
                    painter.setPen(QPen(QColor(200, 200, 200, 80), 0.8))
                painter.drawLine(s1['sx'], s1['sy'], s2['sx'], s2['sy'])
                
        # Sort nodes by depth
        ordered_nodes = sorted(screen_data.values(), key=lambda x: x['sz'], reverse=True)
        
        for sd in ordered_nodes:
            n = sd['node']
            scale = sd['scale']
            base_r = 4 * scale
            if base_r < 1.5: base_r = 1.5
            
            is_sel = (n['id'] == self.selected_node)
            is_hov = (n['id'] == self.hovered_node)
            in_sel_group = (n['id'] in selected_nodes)
            
            if self.selected_node:
                if is_sel:
                    painter.setBrush(QBrush(QColor(255, 255, 255, 255)))
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawEllipse(QPointF(sd['sx'], sd['sy']), base_r * 1.5, base_r * 1.5)
                elif in_sel_group:
                    painter.setBrush(QBrush(QColor(240, 240, 240, 200)))
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawEllipse(QPointF(sd['sx'], sd['sy']), base_r * 1.2, base_r * 1.2)
                else:
                    painter.setBrush(QBrush(QColor(100, 100, 100, 30)))
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawEllipse(QPointF(sd['sx'], sd['sy']), base_r * 0.8, base_r * 0.8)
            else:
                alpha = 255 if is_hov else 160
                painter.setBrush(QBrush(QColor(230, 230, 230, alpha)))
                painter.setPen(Qt.PenStyle.NoPen)
                br = base_r * 1.3 if is_hov else base_r
                painter.drawEllipse(QPointF(sd['sx'], sd['sy']), br, br)
                
            # Draw label for all nodes if scale is not too small
            if scale > 0.3:
                painter.setPen(QPen(QColor(200, 200, 200, 200)))
                font = QFont("Arial", max(6, int(8 * scale)))
                painter.setFont(font)
                painter.drawText(QPointF(sd['sx'] + base_r * 1.5, sd['sy'] + base_r * 1.5), n['label'])
                
        if self.hovered_node and self.hovered_node in screen_data:
            sd = screen_data[self.hovered_node]
            painter.setPen(QColor(255, 255, 255, 255))
            font = QFont("Arial", 10)
            painter.setFont(font)
            fm = QFontMetrics(font)
            text = sd['node']['label']
            w = fm.horizontalAdvance(text)
            painter.drawText(sd['sx'] - w/2, sd['sy'] - 12 - sd['scale']*4, text)

    def mousePressEvent(self, event):
        self.last_pos = event.pos()
        self.mouse_btn = event.button()
        
        if self.mouse_btn == Qt.MouseButton.LeftButton:
            if self.hovered_node:
                if self.selected_node == self.hovered_node:
                    self.selected_node = None
                else:
                    self.selected_node = self.hovered_node
                    if self.main_window and hasattr(self.main_window, 'notes_panel'):
                        self.main_window.notes_panel.load_node_notes(self.selected_node, self.nodes[self.selected_node]['label'])
                        
                self.dragged_node = self.hovered_node
            else:
                self.selected_node = None
                
    def mouseMoveEvent(self, event):
        min_dist = float('inf')
        h_node = None
        for n in self.nodes.values():
            sx, sy, sz, scale = self.project(n['x'], n['y'], n['z'])
            dx = sx - event.position().x()
            dy = sy - event.position().y()
            dist_sq = dx*dx + dy*dy
            r = max(4 * scale, 6)
            if dist_sq < r*r*4 and sz < min_dist:
                min_dist = sz
                h_node = n['id']
                
        self.hovered_node = h_node
        
        if not self.last_pos:
            self.last_pos = event.pos()
            return
            
        if self.mouse_btn == Qt.MouseButton.LeftButton and self.dragged_node:
            dx = event.pos().x() - self.last_pos.x()
            dy = event.pos().y() - self.last_pos.y()
            n = self.nodes[self.dragged_node]
            _, _, sz, _ = self.project(n['x'], n['y'], n['z'])
            wdx, wdy, wdz = self.screen_to_world_delta(dx, dy, sz)
            n['x'] += wdx
            n['y'] += wdy
            n['z'] += wdz
        elif self.mouse_btn == Qt.MouseButton.LeftButton:
            dx = event.pos().x() - self.last_pos.x()
            dy = event.pos().y() - self.last_pos.y()
            self.rot_y += dx * 0.005
            self.rot_x += dy * 0.005
        elif self.mouse_btn == Qt.MouseButton.RightButton:
            dx = event.pos().x() - self.last_pos.x()
            dy = event.pos().y() - self.last_pos.y()
            self.pan_x += dx
            self.pan_y += dy
            
        self.last_pos = event.pos()

    def mouseReleaseEvent(self, event):
        self.mouse_btn = None
        self.dragged_node = None

    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            self.zoom *= 1.15
        else:
            self.zoom /= 1.15
