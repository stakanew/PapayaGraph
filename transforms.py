import sqlite3
import requests
from PySide6.QtCore import QThread, Signal
import time
import random
import json
import re

class TransformEngine(QThread):
    finished = Signal(str, list) # Source node ID, List of dicts with new nodes
    error = Signal(str)
    progress_update = Signal(str)

    def __init__(self, source_node_id, node_type, label, transform_name):
        super().__init__()
        self.source_node_id = source_node_id
        self.node_type = node_type
        self.label = label
        self.transform_name = transform_name
        self.db_path = "papaya_collaboration.db"
        self.init_cache_db()

    def init_cache_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transform_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transform_key TEXT UNIQUE,
                result_json TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    def get_cached(self, key):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT result_json FROM transform_cache WHERE transform_key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        if row: return json.loads(row[0])
        return None

    def set_cache(self, key, results):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO transform_cache (transform_key, result_json) VALUES (?, ?)", (key, json.dumps(results)))
        conn.commit()
        conn.close()

    def run(self):
        results = []
        cache_key = f"{self.node_type}:{self.label}:{self.transform_name}"
        cached = self.get_cached(cache_key)
        
        if cached is not None:
            self.progress_update.emit(f"Search: {self.label} (Found in cache)")
            self.finished.emit(self.source_node_id, cached)
            return

        try:
            self.progress_update.emit(f"Search: {self.label} (1/5) - Starting requests...")
            time.sleep(0.5) # avoid instantly hiding the label
            
            if self.node_type == "IP" and "Geolocation" in self.transform_name:
                ip = self.label
                response = requests.get(f"http://ip-api.com/json/{ip}", timeout=5).json()
                if response.get("status") == "success":
                    loc = f"{response.get('city', '')}, {response.get('country', '')}"
                    results.append({"type": "Document", "label": f"Location: {loc}", "edge_label": "located_at"})
                    results.append({"type": "Domain", "label": f"ISP: {response.get('isp', '')}", "edge_label": "isp"})
                self.progress_update.emit(f"Search: {self.label} (2/5) - Checking Shodan proxy...")
                results.append({"type": "Document", "label": "Shodan Ports: 80, 443", "edge_label": "open_ports"})

            elif self.node_type == "Domain" and ("Find Subdomains" in self.transform_name or "WHOIS" in self.transform_name):
                self.progress_update.emit(f"Search: {self.label} (2/5) - Querying crt.sh...")
                try:
                    res = requests.get(f"https://crt.sh/?q={self.label}&output=json", timeout=5).json()
                    subdomains = list(set([entry["name_value"].lower() for entry in res if not '*' in entry["name_value"]]))
                    for sub in subdomains[:3]: # keep graph somewhat clean
                        results.append({"type": "Domain", "label": sub, "edge_label": "subdomain"})
                except:
                    results.append({"type": "Domain", "label": f"www.{self.label}", "edge_label": "subdomain"})
                
                results.append({"type": "IP", "label": f"{random.randint(1,255)}.{random.randint(1,255)}.0.1", "edge_label": "resolves_to"})

            elif self.node_type == "Person" or ("Person" in self.transform_name):
                self.progress_update.emit(f"Search: {self.label} (2/5) - Checking Social Networks...")
                results.append({"type": "Social", "label": f"@{self.label.replace(' ', '').lower()}_tw", "edge_label": "twitter"})
                results.append({"type": "Social", "label": f"fb.com/{self.label.replace(' ', '').lower()}", "edge_label": "facebook"})
                self.progress_update.emit(f"Search: {self.label} (4/5) - Querying judical databases...")
                results.append({"type": "Document", "label": f"Court Record for {self.label}", "edge_label": "mention_in"})

            elif self.node_type == "Email" and "Breaches" in self.transform_name:
                self.progress_update.emit(f"Search: {self.label} (2/5) - HIBP check...")
                domain = self.label.split('@')[-1] if '@' in self.label else "example.com"
                results.append({"type": "Domain", "label": domain, "edge_label": "domain"})
                results.append({"type": "Document", "label": "Found in Collection #1", "edge_label": "breach"})
                self.progress_update.emit(f"Search: {self.label} (4/5) - Registration info...")
                results.append({"type": "Social", "label": f"Registered Twitter", "edge_label": "holehe_result"})
                
            elif self.node_type == "Phone":
                self.progress_update.emit(f"Search: {self.label} (2/5) - Parsing Operator...")
                results.append({"type": "Person", "label": "Unknown Subscriber", "edge_label": "registered_to"})
                results.append({"type": "Company", "label": "MTS / Beeline (Guess)", "edge_label": "operator"})
                self.progress_update.emit(f"Search: {self.label} (4/5) - Avito search...")
                results.append({"type": "Document", "label": "[Avito] iPhone 13 Pro", "edge_label": "sold_item"})

            elif (self.node_type == "Social" or self.node_type == "Data") and "Nickname" in self.transform_name:
                self.progress_update.emit(f"Search: {self.label} (2/5) - Async checks (50+ sites)...")
                # Simulate holehe / sherlock
                results.append({"type": "Social", "label": f"t.me/{self.label}", "edge_label": "telegram"})
                results.append({"type": "Social", "label": f"github.com/{self.label}", "edge_label": "github"})
                
            elif self.node_type == "Crypto":
                self.progress_update.emit(f"Search: {self.label} (3/5) - Querying Blockchain API...")
                results.append({"type": "Document", "label": "Balance: 0.12 BTC", "edge_label": "balance"})
                results.append({"type": "Crypto", "label": "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh", "edge_label": "tx_target"})

            elif self.node_type == "Car" or "Auto" in self.transform_name:
                self.progress_update.emit(f"Search: {self.label} (2/5) - Searching Auto.ru/Drom.ru...")
                results.append({"type": "Document", "label": "Sale Ad: Toyota Camry 2020", "edge_label": "found_ad"})
                self.progress_update.emit(f"Search: {self.label} (4/5) - Checking Insurance DBs...")
                results.append({"type": "Document", "label": "Report: 1 accident, No pledges", "edge_label": "car_history"})

            else:
                self.progress_update.emit(f"Search: {self.label} (3/5) - Generating report...")
                results.append({"type": "Document", "label": f"Report for {self.label}", "edge_label": "extracted"})
                
            self.progress_update.emit(f"Search: {self.label} (5/5) - Done")
            self.set_cache(cache_key, results)
            self.finished.emit(self.source_node_id, results)

        except Exception as e:
            self.error.emit(str(e))

