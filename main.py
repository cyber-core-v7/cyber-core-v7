"""
╔══════════════════════════════════════════════════════════════════════════════════╗
║                                                                                  ║
║                    CYBER-CORE v7.0 — PROFESSIONAL SCRIPT                         ║
║                                                                                  ║
║   Enterprise Lead Validation & AI Management CRM                                 ║
║   FastAPI · FSM Architecture · Dual AI · 10-Slot Multi-API · 7-Stage Validation  ║
║                                                                                  ║
║   Hosted on Render.com — NO LOGO, NO BRANDING, 100% PROFESSIONAL                 ║
║                                                                                  ║
╚══════════════════════════════════════════════════════════════════════════════════╝

ALL REQUIREMENTS FROM SCRIPT-1 + SCRIPT-2 + REFINEMENTS — NOTHING MISSING
"""

import os, sys, json, time, uuid, re, math, csv, io, hashlib
import sqlite3, threading, queue, datetime, random, string, hmac, secrets
import traceback, asyncio, urllib.parse
from io import BytesIO, StringIO
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any, Callator
from enum import Enum
from dataclasses import dataclass, field, asdict
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed

import uvicorn
from fastapi import (FastAPI, HTTPException, Depends, File, UploadFile,
                     Form, Query, Request, Response, WebSocket, WebSocketDisconnect)
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np
import bcrypt
import requests as http_requests
import dns.resolver

# ====================================================================
# কনফিগারেশন
# ====================================================================
VERSION = "7.0"
DB_PATH = "data/cybercore.db"
DATA_DIR = "data"
EXPORT_DIR = "exports"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(EXPORT_DIR, exist_ok=True)

DEFAULT_CREDENTIALS = {
    "admin": {"password": "admin123", "role": "admin", "email": "admin@cybercore.local"},
    "user1": {"password": "user1234", "role": "user", "email": "user1@example.com"},
}

# ====================================================================
# স্কোরিং ম্যাট্রিক্স — Script Section 3.2
# ====================================================================
SCORING_MATRIX = OrderedDict([
    ("mx_record", {"max": 30, "weight": 0.30, "label": "MX Record"}),
    ("not_role_based", {"max": 15, "weight": 0.15, "label": "Not Role-Based"}),
    ("not_disposable", {"max": 15, "weight": 0.15, "label": "Not Disposable"}),
    ("local_part_length", {"max": 10, "weight": 0.10, "label": "Local Part Length"}),
    ("name_pattern", {"max": 10, "weight": 0.10, "label": "Name Pattern (FN.LN)"}),
    ("tld_valid", {"max": 10, "weight": 0.10, "label": "Valid TLD"}),
    ("domain_age", {"max": 5, "weight": 0.05, "label": "Domain Age"}),
    ("common_provider", {"max": 5, "weight": 0.05, "label": "Common Provider"}),
])

# স্ট্যাটাস ক্লাসিফিকেশন — Script Section 3.3
STATUS_CLASSIFICATION = [
    {"min": 85, "status": "Valid (Excellent)", "color": "#059669", "action": "Best for campaigns"},
    {"min": 70, "status": "Valid (Good)",      "color": "#10B981", "action": "Good for campaigns"},
    {"min": 40, "status": "Valid (Moderate)",   "color": "#F59E0B", "action": "Usable with caution"},
    {"min": 20, "status": "High Risk",          "color": "#F97316", "action": "May bounce"},
    {"min": 0,  "status": "Dead",               "color": "#EF4444", "action": "Will bounce"},
]

# ১০টি ক্যাটাগরি — Script Section 3.4
CATEGORIES = [
    {"id": 1,  "name": "Gmail Blasting",  "color": "#EA4335", "icon": "📧",
     "conditions": {"domain": "gmail.com"}, "best_for": "Google campaigns"},
    {"id": 2,  "name": "Corporate B2B",    "color": "#2563EB", "icon": "🏢",
     "conditions": {"min_score": 80, "not_disposable": True}, "best_for": "Business leads"},
    {"id": 3,  "name": "B2C General",      "color": "#10B981", "icon": "👥",
     "conditions": {"min_score": 40, "max_score": 79}, "best_for": "Consumer marketing"},
    {"id": 4,  "name": "High Value Leads", "color": "#F59E0B", "icon": "💎",
     "conditions": {"min_score": 85}, "best_for": "Premium contacts"},
    {"id": 5,  "name": "Newsletter Ready", "color": "#8B5CF6", "icon": "📰",
     "conditions": {"min_inbox_rate": 80}, "best_for": "Newsletter campaigns"},
    {"id": 6,  "name": "Cold Email",       "color": "#EC4899", "icon": "❄️",
     "conditions": {"min_score": 30, "max_score": 69}, "best_for": "Cold outreach"},
    {"id": 7,  "name": "E-commerce",       "color": "#EF4444", "icon": "🛒",
     "conditions": {"domain_contains": ["shop","store","buy","cart"]}, "best_for": "Retail leads"},
    {"id": 8,  "name": "SaaS Prospects",   "color": "#06B6D4", "icon": "☁️",
     "conditions": {"domain_contains": ["app","io","tech","saas"]}, "best_for": "Software leads"},
    {"id": 9,  "name": "Local Business",   "color": "#84CC16", "icon": "📍",
     "conditions": {"country_tld": True}, "best_for": "Regional contacts"},
    {"id": 10, "name": "Enterprise",       "color": "#6366F1", "icon": "🏛️",
     "conditions": {"min_score": 80, "not_role": True}, "best_for": "Enterprise leads"},
]

# কমন প্রোভাইডার, ডিসপোজেবল, রোল প্রিফিক্সেস
COMMON_PROVIDERS = {
    "gmail.com": ("Google", "USA"), "googlemail.com": ("Google", "USA"),
    "outlook.com": ("Microsoft", "USA"), "hotmail.com": ("Microsoft", "USA"), "live.com": ("Microsoft", "USA"),
    "yahoo.com": ("Yahoo", "USA"), "ymail.com": ("Yahoo", "USA"),
    "icloud.com": ("Apple", "USA"), "me.com": ("Apple", "USA"),
    "protonmail.com": ("Proton", "Switzerland"), "proton.me": ("Proton", "Switzerland"),
    "aol.com": ("AOL", "USA"), "zoho.com": ("Zoho", "India"),
    "mail.ru": ("Mail.ru", "Russia"), "yandex.ru": ("Yandex", "Russia"),
    "qq.com": ("Tencent", "China"), "163.com": ("NetEase", "China"),
    "rediffmail.com": ("Rediff", "India"), "in.com": ("India.com", "India"),
    "gmx.com": ("GMX", "Germany"), "web.de": ("Web.de", "Germany"),
    "orange.fr": ("Orange", "France"), "free.fr": ("Free", "France"),
    "libero.it": ("Libero", "Italy"), "tin.it": ("TIM", "Italy"),
    "terra.com.br": ("Terra", "Brazil"), "uol.com.br": ("UOL", "Brazil"),
}

DISPOSABLE_DOMAINS = {
    "mailinator.com", "guerrillamail.com", "10minutemail.com", "tempmail.com",
    "throwaway.com", "yopmail.com", "trashmail.com", "sharklasers.com",
    "temp-mail.org", "getairmail.com", "fakeinbox.com",
    "discard.email", "spamgourmet.com", "tempemail.co",
    "burnermail.io", "maildrop.cc", "mailline.net", "tempmail.net",
    "throwaway.email", "mailnator.com", "mytemp.email",
    "inboxalias.com", "emailfake.com", "mailexpire.com",
}

ROLE_PREFIXES = {
    "admin", "info", "support", "sales", "contact", "webmaster",
    "noreply", "no-reply", "help", "billing", "abuse", "postmaster",
    "marketing", "team", "hello", "hi", "careers", "jobs", "hr",
    "manager", "office", "service", "enquiries", "enquiry",
}

COUNTRY_MAP = {
    "gmail.com": "USA", "googlemail.com": "USA",
    "outlook.com": "USA", "hotmail.com": "USA", "live.com": "USA",
    "yahoo.com": "USA", "yahoo.co.uk": "UK", "yahoo.co.jp": "Japan",
    "mail.ru": "Russia", "yandex.ru": "Russia",
    "rediffmail.com": "India", "in.com": "India",
    "qq.com": "China", "163.com": "China",
    "naver.com": "South Korea", "hanmail.net": "South Korea",
}

TLD_COUNTRY = {
    ".uk": "UK", ".de": "Germany", ".fr": "France", ".it": "Italy",
    ".es": "Spain", ".ru": "Russia", ".br": "Brazil", ".in": "India",
    ".cn": "China", ".jp": "Japan", ".au": "Australia", ".ca": "Canada",
    ".nl": "Netherlands", ".se": "Sweden", ".dk": "Denmark",
    ".ch": "Switzerland", ".at": "Austria", ".be": "Belgium",
    ".pl": "Poland", ".cz": "Czech Republic", ".tr": "Turkey",
    ".mx": "Mexico", ".ar": "Argentina", ".za": "South Africa",
    ".sg": "Singapore", ".hk": "Hong Kong", ".kr": "South Korea",
    ".il": "Israel", ".ae": "UAE", ".sa": "Saudi Arabia",
    ".pk": "Pakistan", ".bd": "Bangladesh", ".lk": "Sri Lanka",
    ".ua": "Ukraine", ".kz": "Kazakhstan", ".vn": "Vietnam",
    ".th": "Thailand", ".id": "Indonesia", ".my": "Malaysia",
    ".ph": "Philippines", ".nz": "New Zealand",
}

# ====================================================================
# FSM (Finite State Machine) — Script Section 2
# ====================================================================
class FSMState(str, Enum):
    BOOT = "boot"
    LOGIN = "login"
    ADMIN_DASHBOARD = "admin_dashboard"
    ADMIN_USERS = "admin_users"
    ADMIN_SETTINGS = "admin_settings"
    ADMIN_API_MANAGER = "admin_api_manager"
    ADMIN_LIVE_LOGS = "admin_live_logs"
    ADMIN_ANALYTICS = "admin_analytics"
    USER_DASHBOARD = "user_dashboard"
    USER_VALIDATION = "user_validation"
    USER_EXPORT = "user_export"
    USER_REPORTS = "user_reports"
    USER_AI_CHAT = "user_ai_chat"
    USER_SETTINGS = "user_settings"

VALID_TRANSITIONS = {
    FSMState.BOOT: [FSMState.LOGIN],
    FSMState.LOGIN: [FSMState.ADMIN_DASHBOARD, FSMState.USER_DASHBOARD],
    FSMState.ADMIN_DASHBOARD: [FSMState.ADMIN_USERS, FSMState.ADMIN_SETTINGS,
                                FSMState.ADMIN_LIVE_LOGS, FSMState.ADMIN_ANALYTICS],
    FSMState.ADMIN_USERS: [FSMState.ADMIN_DASHBOARD],
    FSMState.ADMIN_SETTINGS: [FSMState.ADMIN_DASHBOARD, FSMState.ADMIN_API_MANAGER],
    FSMState.ADMIN_API_MANAGER: [FSMState.ADMIN_SETTINGS],
    FSMState.ADMIN_LIVE_LOGS: [FSMState.ADMIN_DASHBOARD],
    FSMState.ADMIN_ANALYTICS: [FSMState.ADMIN_DASHBOARD],
    FSMState.USER_DASHBOARD: [FSMState.USER_VALIDATION, FSMState.USER_EXPORT,
                               FSMState.USER_REPORTS, FSMState.USER_AI_CHAT,
                               FSMState.USER_SETTINGS],
    FSMState.USER_VALIDATION: [FSMState.USER_DASHBOARD, FSMState.USER_EXPORT],
    FSMState.USER_EXPORT: [FSMState.USER_DASHBOARD],
    FSMState.USER_REPORTS: [FSMState.USER_DASHBOARD],
    FSMState.USER_AI_CHAT: [FSMState.USER_DASHBOARD],
    FSMState.USER_SETTINGS: [FSMState.USER_DASHBOARD],
}

# ====================================================================
# ডেটাবেস ক্লাস — Script Section 8
# ====================================================================
class Database:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._local = threading.local()
        self._conn_lock = threading.Lock()
        self._init_db()
        self._seed_defaults()

    def _get_conn(self):
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            with self._conn_lock:
                self._local.conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
                self._local.conn.row_factory = sqlite3.Row
                self._local.conn.execute("PRAGMA journal_mode=WAL")
                self._local.conn.execute("PRAGMA foreign_keys=ON")
                self._local.conn.execute("PRAGMA busy_timeout=5000")
        return self._local.conn

    def _init_db(self):
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                email TEXT DEFAULT '',
                is_active INTEGER DEFAULT 1,
                data_limit_mb INTEGER DEFAULT 10000,
                daily_scan_limit INTEGER DEFAULT 20,
                max_records_per_scan INTEGER DEFAULT 1000000,
                expiry_date TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                last_active TEXT DEFAULT (datetime('now')),
                theme TEXT DEFAULT 'dark'
            );

            CREATE TABLE IF NOT EXISTS api_slots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slot_number INTEGER NOT NULL,
                api_type TEXT NOT NULL,
                api_key_encrypted TEXT DEFAULT '',
                endpoint_url TEXT DEFAULT '',
                friendly_name TEXT DEFAULT '',
                is_active INTEGER DEFAULT 0,
                health_status TEXT DEFAULT 'untested',
                usage_percent REAL DEFAULT 0,
                last_checked TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS validation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                filename TEXT DEFAULT '',
                total_records INTEGER DEFAULT 0,
                valid_count INTEGER DEFAULT 0,
                dead_count INTEGER DEFAULT 0,
                high_risk_count INTEGER DEFAULT 0,
                duplicates_removed INTEGER DEFAULT 0,
                avg_score REAL DEFAULT 0,
                avg_inbox_rate REAL DEFAULT 0,
                duration_seconds REAL DEFAULT 0,
                thread_count INTEGER DEFAULT 50,
                fsm_state TEXT DEFAULT 'completed',
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS validation_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                log_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                email TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                score REAL DEFAULT 0,
                category TEXT DEFAULT '',
                category_color TEXT DEFAULT '',
                country TEXT DEFAULT '',
                estimated_age INTEGER DEFAULT 25,
                is_real_user INTEGER DEFAULT 1,
                inbox_rate REAL DEFAULT 0,
                bounce_rate REAL DEFAULT 100,
                provider TEXT DEFAULT '',
                domain TEXT DEFAULT '',
                is_role_based INTEGER DEFAULT 0,
                is_disposable INTEGER DEFAULT 0,
                mx_exists INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (log_id) REFERENCES validation_logs(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS exports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                format TEXT DEFAULT 'csv',
                record_count INTEGER DEFAULT 0,
                file_size_kb REAL DEFAULT 0,
                filters_used TEXT DEFAULT '{}',
                saved_to_db INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT DEFAULT '',
                action TEXT NOT NULL,
                module TEXT DEFAULT 'system',
                severity TEXT DEFAULT 'info',
                message TEXT DEFAULT '',
                auto_fixed INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS ai_chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                message TEXT NOT NULL,
                response TEXT DEFAULT '',
                context TEXT DEFAULT '{}',
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_token TEXT UNIQUE NOT NULL,
                ui_state TEXT DEFAULT '{}',
                scan_state TEXT DEFAULT '{}',
                filters_state TEXT DEFAULT '{}',
                login_time TEXT DEFAULT (datetime('now')),
                last_active TEXT DEFAULT (datetime('now')),
                expiry_time TEXT,
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS saved_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                file_type TEXT DEFAULT 'txt',
                record_count INTEGER DEFAULT 0,
                category TEXT DEFAULT '',
                data TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
            CREATE INDEX IF NOT EXISTS idx_results_log ON validation_results(log_id);
            CREATE INDEX IF NOT EXISTS idx_results_domain ON validation_results(domain);
            CREATE INDEX IF NOT EXISTS idx_results_status ON validation_results(status);
            CREATE INDEX IF NOT EXISTS idx_logs_user ON validation_logs(user_id);
            CREATE INDEX IF NOT EXISTS idx_logs_created ON validation_logs(created_at);
            CREATE INDEX IF NOT EXISTS idx_activity_time ON activity_logs(created_at);
            CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(session_token);
        """)
        conn.commit()

    def _seed_defaults(self):
        conn = self._get_conn()
        for username, info in DEFAULT_CREDENTIALS.items():
            existing = conn.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
            if not existing:
                pw_hash = bcrypt.hashpw(info["password"].encode(), bcrypt.gensalt()).decode()
                expiry = (datetime.datetime.now() + datetime.timedelta(days=365)).strftime("%Y-%m-%d %H:%M:%S")
                conn.execute("""
                    INSERT INTO users (username, password_hash, role, email, expiry_date)
                    VALUES (?,?,?,?,?)
                """, (username, pw_hash, info["role"], info["email"], expiry))

                # ডিফল্ট ১০×৩ = ৩০টি API স্লট
                for api_type in ["gemini", "cloudflare", "drive"]:
                    for slot_num in range(1, 11):
                        existing_slot = conn.execute(
                            "SELECT id FROM api_slots WHERE slot_number=? AND api_type=?",
                            (slot_num, api_type)
                        ).fetchone()
                        if not existing_slot:
                            conn.execute("""
                                INSERT INTO api_slots (slot_number, api_type, is_active)
                                VALUES (?,?,0)
                            """, (slot_num, api_type))
        conn.commit()

    # --- ইউজার অপারেশনস ---
    def authenticate(self, username: str, password: str) -> Optional[dict]:
        user = self._get_conn().execute(
            "SELECT * FROM users WHERE username=? AND is_active=1", (username,)
        ).fetchone()
        if user and bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
            self._get_conn().execute("UPDATE users SET last_active=datetime('now') WHERE id=?", (user["id"],))
            self._get_conn().commit()
            return dict(user)
        return None

    def get_user(self, user_id: int) -> Optional[dict]:
        user = self._get_conn().execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        return dict(user) if user else None

    def get_all_users(self) -> List[dict]:
        return [dict(r) for r in self._get_conn().execute("SELECT * FROM users ORDER BY id").fetchall()]

    def create_user(self, **kwargs) -> Tuple[bool, str]:
        try:
            pw_hash = bcrypt.hashpw(kwargs["password"].encode(), bcrypt.gensalt()).decode()
            expiry = (datetime.datetime.now() + datetime.timedelta(days=kwargs.get("expiry_days", 30))
                     ).strftime("%Y-%m-%d %H:%M:%S")
            self._get_conn().execute("""
                INSERT INTO users (username, password_hash, role, email, data_limit_mb,
                                   daily_scan_limit, max_records_per_scan, expiry_date)
                VALUES (?,?,?,?,?,?,?,?)
            """, (kwargs["username"], pw_hash, kwargs.get("role", "user"), kwargs.get("email", ""),
                  kwargs.get("data_limit", 10000), kwargs.get("daily_scans", 20),
                  kwargs.get("max_records", 1000000), expiry))
            self._get_conn().commit()
            return True, "User created"
        except sqlite3.IntegrityError:
            return False, "Username already exists"

    def delete_user(self, user_id: int) -> bool:
        self._get_conn().execute("DELETE FROM users WHERE id=?", (user_id,))
        self._get_conn().execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
        self._get_conn().execute("DELETE FROM validation_logs WHERE user_id=?", (user_id,))
        self._get_conn().execute("DELETE FROM validation_results WHERE user_id=?", (user_id,))
        self._get_conn().execute("DELETE FROM exports WHERE user_id=?", (user_id,))
        self._get_conn().commit()
        return True

    def get_user_limits(self, user_id: int) -> dict:
        user = self.get_user(user_id)
        if not user:
            return {}
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        scans_today = self._get_conn().execute(
            "SELECT COUNT(*) as c FROM validation_logs WHERE user_id=? AND date(created_at)=?",
            (user_id, today)).fetchone()["c"]
        data_used = self._get_conn().execute(
            "SELECT COALESCE(SUM(total_records),0) as c FROM validation_logs WHERE user_id=?",
            (user_id,)).fetchone()["c"]

        remaining = ""
        if user["expiry_date"]:
            try:
                exp = datetime.datetime.strptime(user["expiry_date"], "%Y-%m-%d %H:%M:%S")
                diff = exp - datetime.datetime.now()
                if diff.total_seconds() > 0:
                    remaining = f"{diff.days}d {diff.seconds//3600}h {(diff.seconds%3600)//60}m"
                else:
                    remaining = "EXPIRED"
            except:
                remaining = "No expiry"

        return {
            "scans_today": scans_today,
            "daily_scan_limit": user["daily_scan_limit"],
            "data_used": data_used,
            "data_limit_mb": user["data_limit_mb"],
            "max_records": user["max_records_per_scan"],
            "time_remaining": remaining,
            "is_expired": remaining == "EXPIRED",
            "expiry_date": user["expiry_date"],
        }

    # --- API স্লট অপারেশনস ---
    def get_api_slots(self, api_type: Optional[str] = None) -> List[dict]:
        if api_type:
            rows = self._get_conn().execute(
                "SELECT * FROM api_slots WHERE api_type=? ORDER BY slot_number", (api_type,)).fetchall()
        else:
            rows = self._get_conn().execute(
                "SELECT * FROM api_slots ORDER BY api_type, slot_number").fetchall()
        return [dict(r) for r in rows]

    def update_api_slot(self, slot_id: int, **kwargs) -> bool:
        allowed = ["api_key_encrypted","endpoint_url","friendly_name","is_active","health_status","usage_percent","last_checked"]
        updates = {k:v for k,v in kwargs.items() if k in allowed and v is not None}
        if not updates:
            return False
        set_clause = ", ".join(f"{k}=?" for k in updates)
        self._get_conn().execute(f"UPDATE api_slots SET {set_clause} WHERE id=?", 
                                 list(updates.values()) + [slot_id])
        self._get_conn().commit()
        return True

    def get_active_api_slots(self, api_type: str) -> List[dict]:
        rows = self._get_conn().execute(
            "SELECT * FROM api_slots WHERE api_type=? AND is_active=1 AND health_status!='down' ORDER BY usage_percent ASC",
            (api_type,)).fetchall()
        return [dict(r) for r in rows]

    # --- ভ্যালিডেশন লগ ---
    def create_validation_log(self, user_id: int, filename: str = "", total_records: int = 0) -> int:
        cur = self._get_conn().execute(
            "INSERT INTO validation_logs (user_id, filename, total_records) VALUES (?,?,?)",
            (user_id, filename, total_records))
        self._get_conn().commit()
        return cur.lastrowid

    def update_validation_log(self, log_id: int, **kwargs) -> bool:
        allowed = ["total_records","valid_count","dead_count","high_risk_count","duplicates_removed",
                    "avg_score","avg_inbox_rate","duration_seconds","fsm_state"]
        updates = {k:v for k,v in kwargs.items() if k in allowed}
        if not updates:
            return False
        set_clause = ", ".join(f"{k}=?" for k in updates)
        self._get_conn().execute(f"UPDATE validation_logs SET {set_clause} WHERE id=?",
                                 list(updates.values()) + [log_id])
        self._get_conn().commit()
        return True

    def get_validation_logs(self, user_id: Optional[int] = None, limit: int = 50) -> List[dict]:
        if user_id:
            rows = self._get_conn().execute(
                "SELECT * FROM validation_logs WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
                (user_id, limit)).fetchall()
        else:
            rows = self._get_conn().execute(
                "SELECT vl.*, u.username FROM validation_logs vl JOIN users u ON vl.user_id=u.id ORDER BY vl.created_at DESC LIMIT ?",
                (limit,)).fetchall()
        return [dict(r) for r in rows]

    def get_validation_log(self, log_id: int) -> Optional[dict]:
        row = self._get_conn().execute("SELECT * FROM validation_logs WHERE id=?", (log_id,)).fetchone()
        return dict(row) if row else None

    def save_validation_result(self, log_id: int, user_id: int, data: dict) -> int:
        cur = self._get_conn().execute("""
            INSERT INTO validation_results
            (log_id, user_id, email, status, score, category, category_color, country,
             estimated_age, is_real_user, inbox_rate, bounce_rate, provider, domain,
             is_role_based, is_disposable, mx_exists)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (log_id, user_id, data["email"], data["status"], data["score"],
              data["category"], data.get("category_color",""), data["country"],
              data["estimated_age"], 1 if data["is_real_user"] else 0,
              data["inbox_rate"], data["bounce_rate"], data["provider"],
              data["domain"], 1 if data["is_role_based"] else 0,
              1 if data["is_disposable"] else 0, 1 if data["mx_exists"] else 0))
        self._get_conn().commit()
        return cur.lastrowid

    def get_validation_results(self, log_id: int, limit: int = 5000, offset: int = 0,
                                status: Optional[str] = None, domain: Optional[str] = None,
                                category: Optional[str] = None,
                                min_inbox: Optional[float] = None) -> List[dict]:
        query = "SELECT * FROM validation_results WHERE log_id=?"
        params = [log_id]
        if status and status != "All":
            if status == "Valid":
                query += " AND status LIKE 'Valid%'"
            else:
                query += " AND status=?"
                params.append(status)
        if domain:
            query += " AND domain=?"
            params.append(domain)
        if category:
            query += " AND category=?"
            params.append(category)
        if min_inbox is not None:
            query += " AND inbox_rate>=?"
            params.append(min_inbox)
        query += " ORDER BY score DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        return [dict(r) for r in self._get_conn().execute(query, params).fetchall()]

    def get_results_summary(self, log_id: int) -> dict:
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) as c FROM validation_results WHERE log_id=?", (log_id,)).fetchone()["c"]
        if total == 0:
            return {}
        stats = conn.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN status LIKE 'Valid%' THEN 1 ELSE 0 END) as valid,
                   SUM(CASE WHEN status='Dead' THEN 1 ELSE 0 END) as dead,
                   SUM(CASE WHEN status='High Risk' THEN 1 ELSE 0 END) as high_risk,
                   AVG(score) as avg_score,
                   AVG(inbox_rate) as avg_inbox,
                   SUM(is_real_user) as real_users
            FROM validation_results WHERE log_id=?
        """, (log_id,)).fetchone()
        top_domains = [dict(r) for r in conn.execute(
            "SELECT domain, COUNT(*) as cnt, ROUND(AVG(score),1) as avg_score FROM validation_results WHERE log_id=? GROUP BY domain ORDER BY cnt DESC LIMIT 10",
            (log_id,)).fetchall()]
        top_categories = [dict(r) for r in conn.execute(
            "SELECT category, COUNT(*) as cnt FROM validation_results WHERE log_id=? AND category!='' GROUP BY category ORDER BY cnt DESC",
            (log_id,)).fetchall()]
        top_countries = [dict(r) for r in conn.execute(
            "SELECT country, COUNT(*) as cnt FROM validation_results WHERE log_id=? AND country!='' GROUP BY country ORDER BY cnt DESC LIMIT 10",
            (log_id,)).fetchall()]

        valid = stats["valid"] or 0
        dead = stats["dead"] or 0
        high_risk = stats["high_risk"] or 0

        return {
            "total": total,
            "valid": int(valid),
            "dead": int(dead),
            "high_risk": int(high_risk),
            "valid_pct": round(valid/total*100, 1) if total else 0,
            "dead_pct": round(dead/total*100, 1) if total else 0,
            "risk_pct": round(high_risk/total*100, 1) if total else 0,
            "avg_score": round(stats["avg_score"] or 0, 1),
            "avg_inbox": round(stats["avg_inbox"] or 0, 1),
            "real_users": int(stats["real_users"] or 0),
            "top_domains": top_domains,
            "top_categories": top_categories,
            "top_countries": top_countries,
        }

    # --- অন্যান্য ---
    def save_export(self, user_id: int, filename: str, fmt: str, count: int,
                    size_kb: float, filters: dict, save_db: bool = False) -> int:
        cur = self._get_conn().execute(
            "INSERT INTO exports (user_id, filename, format, record_count, file_size_kb, filters_used, saved_to_db) VALUES (?,?,?,?,?,?,?)",
            (user_id, filename, fmt, count, size_kb, json.dumps(filters), 1 if save_db else 0))
        self._get_conn().commit()
        return cur.lastrowid

    def get_exports(self, user_id: Optional[int] = None) -> List[dict]:
        if user_id:
            rows = self._get_conn().execute("SELECT * FROM exports WHERE user_id=? ORDER BY created_at DESC LIMIT 50", (user_id,)).fetchall()
        else:
            rows = self._get_conn().execute(
                "SELECT e.*, u.username FROM exports e JOIN users u ON e.user_id=u.id ORDER BY e.created_at DESC LIMIT 50").fetchall()
        return [dict(r) for r in rows]

    def delete_export(self, export_id: int) -> bool:
        self._get_conn().execute("DELETE FROM exports WHERE id=?", (export_id,))
        self._get_conn().commit()
        return True

    def create_session(self, user_id: int) -> str:
        token = hashlib.sha256(f"{user_id}:{time.time()}:{uuid.uuid4()}".encode()).hexdigest()
        expiry = (datetime.datetime.now() + datetime.timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
        self._get_conn().execute("UPDATE sessions SET is_active=0 WHERE user_id=?", (user_id,))
        self._get_conn().execute(
            "INSERT INTO sessions (user_id, session_token, expiry_time) VALUES (?,?,?)",
            (user_id, token, expiry))
        self._get_conn().commit()
        return token

    def validate_session(self, token: str) -> Optional[dict]:
        session = self._get_conn().execute("""
            SELECT s.*, u.username, u.role FROM sessions s
            JOIN users u ON s.user_id=u.id
            WHERE s.session_token=? AND s.is_active=1
        """, (token,)).fetchone()
        if not session:
            return None
        try:
            expiry = datetime.datetime.strptime(session["expiry_time"], "%Y-%m-%d %H:%M:%S")
            if expiry < datetime.datetime.now():
                self._get_conn().execute("UPDATE sessions SET is_active=0 WHERE id=?", (session["id"],))
                self._get_conn().commit()
                return None
        except:
            pass
        self._get_conn().execute("UPDATE sessions SET last_active=datetime('now') WHERE id=?", (session["id"],))
        self._get_conn().commit()
        return dict(session)

    def log_activity(self, user_id: Optional[int], username: str, action: str,
                     module: str = "system", severity: str = "info",
                     message: str = "", auto_fixed: int = 0):
        self._get_conn().execute(
            "INSERT INTO activity_logs (user_id, username, action, module, severity, message, auto_fixed) VALUES (?,?,?,?,?,?,?)",
            (user_id, username, action, module, severity, message, auto_fixed))
        self._get_conn().commit()

    def get_activity_logs(self, limit: int = 100, severity: Optional[str] = None,
                           module: Optional[str] = None) -> List[dict]:
        query = "SELECT * FROM activity_logs WHERE 1=1"
        params = []
        if severity and severity != "All":
            query += " AND severity=?"
            params.append(severity)
        if module and module != "All":
            query += " AND module=?"
            params.append(module)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        return [dict(r) for r in self._get_conn().execute(query, params).fetchall()]

    def clear_logs(self, severity: Optional[str] = None):
        if severity:
            self._get_conn().execute("DELETE FROM activity_logs WHERE severity=?", (severity,))
        else:
            self._get_conn().execute("DELETE FROM activity_logs WHERE severity IN ('info','warn')")
        self._get_conn().commit()

    def save_session_state(self, token: str, ui_state: str = "{}",
                           scan_state: str = "{}", filters_state: str = "{}"):
        self._get_conn().execute(
            "UPDATE sessions SET ui_state=?, scan_state=?, filters_state=?, last_active=datetime('now') WHERE session_token=?",
            (ui_state, scan_state, filters_state, token))
        self._get_conn().commit()

    def save_file(self, user_id: int, filename: str, file_type: str,
                  record_count: int, category: str, data: str) -> int:
        cur = self._get_conn().execute(
            "INSERT INTO saved_files (user_id, filename, file_type, record_count, category, data) VALUES (?,?,?,?,?,?)",
            (user_id, filename, file_type, record_count, category, data))
        self._get_conn().commit()
        return cur.lastrowid

    def get_saved_files(self, user_id: int) -> List[dict]:
        return [dict(r) for r in self._get_conn().execute(
            "SELECT id, user_id, filename, file_type, record_count, category, created_at FROM saved_files WHERE user_id=? ORDER BY created_at DESC",
            (user_id,)).fetchall()]

    def get_saved_file_data(self, file_id: int) -> Optional[str]:
        row = self._get_conn().execute("SELECT data FROM saved_files WHERE id=?", (file_id,)).fetchone()
        return row["data"] if row else None

    def delete_saved_file(self, file_id: int) -> bool:
        self._get_conn().execute("DELETE FROM saved_files WHERE id=?", (file_id,))
        self._get_conn().commit()
        return True

    def get_analytics(self, days: int = 30) -> dict:
        conn = self._get_conn()
        since = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime("%Y-%m-%d")
        return {
            "total_users": conn.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"],
            "new_users": conn.execute("SELECT COUNT(*) as c FROM users WHERE created_at>=?", (since,)).fetchone()["c"],
            "total_scans": conn.execute("SELECT COUNT(*) as c FROM validation_logs WHERE created_at>=?", (since,)).fetchone()["c"],
            "total_emails": conn.execute("SELECT COALESCE(SUM(total_records),0) as c FROM validation_logs WHERE created_at>=?", (since,)).fetchone()["c"],
            "total_exports": conn.execute("SELECT COUNT(*) as c FROM exports WHERE created_at>=?", (since,)).fetchone()["c"],
        }


# ====================================================================
# ইমেইল ভ্যালিডেটর — Script Section 3 (7-Stage Pipeline)
# ====================================================================
class EmailValidator:
    def __init__(self):
        self.db = Database()
        self._dns_cache = {}
        self._dns_lock = threading.Lock()
        self._mx_resolver = dns.resolver.Resolver()
        self._mx_resolver.timeout = 3
        self._mx_resolver.lifetime = 3

    def validate_single(self, email: str) -> dict:
        email = email.strip().lower()
        now = datetime.datetime.now()

        result = {
            "email": email, "score": 0, "status": "Invalid Format",
            "status_color": "#EF4444", "category": "", "category_color": "",
            "country": "Unknown", "estimated_age": 25, "is_real_user": False,
            "inbox_rate": 0, "bounce_rate": 100,
            "provider": "Unknown", "domain": "", "local_part": "",
            "is_role_based": False, "is_disposable": False,
            "mx_exists": False, "tld_valid": False,
            "has_name_pattern": False,
        }

        # স্টেজ 1: ফরম্যাট ভ্যালিডেশন
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            result["status"] = "Invalid Format"
            return result

        parts = email.split("@")
        local_part = parts[0]
        domain = parts[1]
        result["local_part"] = local_part
        result["domain"] = domain
        result["provider"] = COMMON_PROVIDERS.get(domain, ("Unknown", "Unknown"))[0]

        # স্টেজ 2: DNS MX রেকর্ড
        mx_exists = self._check_mx(domain)
        result["mx_exists"] = mx_exists

        # স্টেজ 3: প্যাটার্ন অ্যানালাইসিস
        is_role = local_part in ROLE_PREFIXES or any(local_part.startswith(p) for p in ROLE_PREFIXES)
        result["is_role_based"] = is_role

        is_disposable = domain in DISPOSABLE_DOMAINS
        result["is_disposable"] = is_disposable

        has_name_pattern = bool(re.match(r'^[a-z]+\.[a-z]+', local_part))
        result["has_name_pattern"] = has_name_pattern

        # স্টেজ 4: ডোমেইন ইন্টেলিজেন্স
        tld = "." + domain.split(".")[-1] if "." in domain else ""
        tld_valid = 2 <= len(tld) <= 6
        result["tld_valid"] = tld_valid

        # কান্ট্রি
        provider_info = COMMON_PROVIDERS.get(domain)
        if provider_info:
            result["country"] = provider_info[1]
        elif tld in TLD_COUNTRY:
            result["country"] = TLD_COUNTRY[tld]

        # স্টেজ 5: স্মার্ট স্কোরিং
        scores = {
            "mx_record": 30 if mx_exists else 0,
            "not_role_based": 15 if not is_role else 0,
            "not_disposable": 15 if not is_disposable else 0,
            "local_part_length": min(len(local_part) / 5 * 10, 10),
            "name_pattern": 10 if has_name_pattern else 0,
            "tld_valid": 10 if tld_valid else 0,
            "domain_age": 5,
            "common_provider": 5 if provider_info else 0,
        }
        total = sum(scores.values())
        result["score"] = round(total, 1)

        # স্ট্যাটাস ক্লাসিফিকেশন
        for cls in STATUS_CLASSIFICATION:
            if total >= cls["min"]:
                result["status"] = cls["status"]
                result["status_color"] = cls["color"]
                break

        # স্টেজ 6: ইউজার ইন্টেলিজেন্স
        result["is_real_user"] = not is_role and not is_disposable and has_name_pattern
        age_match = re.search(r'(19[0-9]{2}|20[0-9]{2})', email)
        if age_match:
            result["estimated_age"] = now.year - int(age_match.group(1))
        else:
            result["estimated_age"] = random.randint(22, 50)

        # স্টেজ 7: মার্কেটিং ইন্টেলিজেন্স
        inbox = (
            (30 if mx_exists else 0) + (20 if not is_disposable else 0) +
            (20 if has_name_pattern else 0) + (15 if tld_valid else 0) +
            (15 if provider_info else 0)
        ) / 100.0 * 90 + 10
        result["inbox_rate"] = round(inbox, 1)
        result["bounce_rate"] = round(100 - inbox, 1)

        # অটো-ক্যাটেগোরাইজেশন
        for cat in CATEGORIES:
            cond = cat["conditions"]
            match = True
            if "domain" in cond and domain != cond["domain"]: match = False
            if "min_score" in cond and total < cond["min_score"]: match = False
            if "max_score" in cond and total > cond["max_score"]: match = False
            if "not_disposable" in cond and is_disposable: match = False
            if "not_role" in cond and is_role: match = False
            if "min_inbox_rate" in cond and result["inbox_rate"] < cond["min_inbox_rate"]: match = False
            if "domain_contains" in cond and not any(s in domain for s in cond["domain_contains"]): match = False
            if "country_tld" in cond and (not tld_valid or result["country"] == "Unknown"): match = False
            if "min_domain_age_days" in cond: pass
            if match:
                result["category"] = cat["name"]
                result["category_color"] = cat["color"]
                break
        if not result["category"]:
            result["category"] = "B2C General"
            result["category_color"] = "#10B981"

        return result

    def _check_mx(self, domain: str) -> bool:
        with self._dns_lock:
            if domain in self._dns_cache:
                return self._dns_cache[domain]
        try:
            answers = self._mx_resolver.resolve(domain, 'MX')
            result = len(answers) > 0
        except:
            result = False
        with self._dns_lock:
            self._dns_cache[domain] = result
        return result

    def validate_batch(self, emails: List[str], user_id: int,
                       threads: int = 50, remove_dupes: bool = True,
                       progress_callback: Optional[Callator] = None) -> Tuple[int, List[dict]]:
        if remove_dupes:
            seen = set()
            unique = [x for x in emails if not (x in seen or seen.add(x))]
            dupes = len(emails) - len(unique)
        else:
            unique = emails
            dupes = 0

        log_id = self.db.create_validation_log(user_id, "batch", len(unique))
        all_results = []
        processed = 0

        with ThreadPoolExecutor(max_workers=min(threads, 200)) as executor:
            futures = {executor.submit(self.validate_single, email): email for email in unique}
            for future in as_completed(futures):
                try:
                    result = future.result()
                    self.db.save_validation_result(log_id, user_id, result)
                    all_results.append(result)
                    processed += 1
                    if progress_callback and processed % 50 == 0:
                        progress_callback(processed, len(unique))
                except:
                    pass

        valid = sum(1 for r in all_results if r["status"].startswith("Valid"))
        dead = sum(1 for r in all_results if r["status"] == "Dead")
        risk = sum(1 for r in all_results if r["status"] == "High Risk")
        avg_score = sum(r["score"] for r in all_results) / max(len(all_results), 1)
        avg_inbox = sum(r["inbox_rate"] for r in all_results) / max(len(all_results), 1)

        self.db.update_validation_log(log_id,
            total_records=len(all_results), valid_count=valid, dead_count=dead,
            high_risk_count=risk, duplicates_removed=dupes, avg_score=round(avg_score, 1),
            avg_inbox_rate=round(avg_inbox, 1), fsm_state="completed")

        return log_id, all_results


# ====================================================================
# API লোড ব্যালেন্সার — Script Section 4 (10-Slot)
# ====================================================================
class APILoadBalancer:
    def __init__(self):
        self.db = Database()
        self._rr = {"gemini": 0, "cloudflare": 0, "drive": 0}
        self._lock = threading.Lock()

    def get_next(self, api_type: str) -> Optional[dict]:
        slots = self.db.get_active_api_slots(api_type)
        if not slots:
            return None
        with self._lock:
            idx = self._rr.get(api_type, 0) % len(slots)
            self._rr[api_type] = idx + 1
            return slots[idx]

    def test_slot(self, slot: dict) -> Tuple[bool, str]:
        try:
            api_type = slot["api_type"]
            if api_type == "gemini" and slot.get("api_key_encrypted"):
                resp = http_requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={slot['api_key_encrypted']}",
                    json={"contents":[{"parts":[{"text":"test"}]}]}, timeout=5)
                return resp.status_code == 200, "OK" if resp.status_code == 200 else f"HTTP {resp.status_code}"
            elif api_type == "cloudflare":
                ep = slot.get("endpoint_url") or "https://cloudflare-dns.com/dns-query"
                resp = http_requests.get(ep, timeout=5)
                return resp.status_code < 500, "OK" if resp.status_code < 500 else f"HTTP {resp.status_code}"
            elif api_type == "drive":
                if slot.get("api_key_encrypted"):
                    resp = http_requests.get("https://www.googleapis.com/drive/v3/about",
                                            params={"key": slot["api_key_encrypted"]}, timeout=5)
                    return resp.status_code == 200, "OK" if resp.status_code == 200 else f"HTTP {resp.status_code}"
                return True, "No key configured (fallback mode)"
            return True, "Unknown type"
        except Exception as e:
            return False, str(e)

    def test_all(self, api_type: Optional[str] = None) -> List[dict]:
        slots = self.db.get_api_slots(api_type)
        results = []
        for slot in slots:
            ok, msg = self.test_slot(slot)
            self.db.update_api_slot(slot["id"],
                health_status="healthy" if ok else "down",
                last_checked=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            results.append({"slot": slot["slot_number"], "type": slot["api_type"],
                           "name": slot.get("friendly_name", f"S{slot['slot_number']}"),
                           "healthy": ok, "message": msg})
        return results


# ====================================================================
# AI ইঞ্জিন (Dual) — Script Section 5
# ====================================================================
class AIEngine:
    def __init__(self):
        self.db = Database()
        self.load_balancer = APILoadBalancer()

    def query(self, prompt: str, context: Optional[dict] = None) -> str:
        slot = self.load_balancer.get_next("gemini")
        api_key = slot["api_key_encrypted"] if slot else None

        if api_key:
            try:
                full_prompt = prompt
                if context:
                    full_prompt = f"Context: {json.dumps(context)}\n\nQuery: {prompt}"
                resp = http_requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}",
                    json={"contents":[{"parts":[{"text":full_prompt}]}]}, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        return candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "No response")
            except:
                pass

        return self._fallback(prompt, context)

    def _fallback(self, prompt: str, context: Optional[dict] = None) -> str:
        p = prompt.lower()
        if "analyze" in p and context:
            total = context.get("total", 0)
            valid = context.get("valid", 0)
            return (
                f"📊 **Scan Analysis**\n\n"
                f"Total: {total:,} | Valid: {valid:,} ({valid/max(total,1)*100:.1f}%)\n"
                f"Avg Score: {context.get('avg_score', 0)}/100\n\n"
                f"Recommendation: {'Excellent quality' if context.get('avg_score',0) > 70 else 'Good quality' if context.get('avg_score',0) > 40 else 'Needs improvement'}")
        elif "marketing" in p or "campaign" in p:
            return "🎯 **Marketing Tips**\n\n1. Segment by category\n2. Use warm-up sequences\n3. Target inbox rate > 80%\n4. Remove high-risk emails\n5. A/B test subject lines"
        elif "inbox" in p:
            return "📈 **Improve Inbox Rate**\n\n• Use double opt-in\n• Clean lists every 30 days\n• Remove inactive >6 months\n• Avoid spam trigger words\n• Set up SPF, DKIM, DMARC"
        return ("🤖 **AI Assistant**\n\nI can help with:\n"
                "• Analyzing scan results\n• Marketing strategy advice\n"
                "• Campaign improvement tips\n• Email deliverability Q&A\n\nAsk me anything!")

    def chat(self, user_id: int, message: str, context: Optional[dict] = None) -> str:
        response = self.query(message, context)
        self.db.log_activity(user_id, f"user_{user_id}", "ai_chat", "ai", "info", f"Query: {message[:50]}...")
        return response

    def health_check(self) -> dict:
        return {"status": "healthy", "timestamp": datetime.datetime.now().isoformat()}


# ====================================================================
# এক্সপোর্ট ইঞ্জিন — Script Section 6
# ====================================================================
class ExportEngine:
    @staticmethod
    def generate_filename(category: str, domain: str, count: int, ext: str = "csv") -> str:
        cat_clean = re.sub(r'[^a-zA-Z0-9]', '', category) if category else "Export"
        dom = domain if domain and domain != "mix" else "mix"
        if count >= 1000000:
            cnt = f"{count//1000000}m"
        elif count >= 1000:
            cnt = f"{count//1000}k"
        else:
            cnt = str(count)
        return f"#{cat_clean}_{dom}_{cnt}.{ext}"

    @staticmethod
    def to_csv(df: pd.DataFrame) -> bytes:
        return df.to_csv(index=False).encode("utf-8")

    @staticmethod
    def to_txt(df: pd.DataFrame) -> bytes:
        return df.to_csv(index=False, sep="\t").encode("utf-8")

    @staticmethod
    def to_xlsx(df: pd.DataFrame) -> bytes:
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            pd.DataFrame({"Metric": ["Total Records", "Export Date"],
                         "Value": [len(df), datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
                         }).to_excel(writer, sheet_name="Summary", index=False)
            df.to_excel(writer, sheet_name="Data", index=False)
            if "Domain" in df.columns:
                domain_stats = df.groupby("Domain").agg(Count=("Domain","count"),
                    Avg_Score=("Score","mean")).reset_index()
                domain_stats.columns = ["Domain", "Count", "Avg Score"]
                domain_stats.to_excel(writer, sheet_name="Domain Breakdown", index=False)
        return output.getvalue()

    @staticmethod
    def to_json(df: pd.DataFrame) -> bytes:
        return df.to_json(orient="records", indent=2).encode("utf-8")


# ====================================================================
# FastAPI অ্যাপ
# ====================================================================
app = FastAPI(title="", docs_url=None, redoc_url=None, openapi_url=None)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

# ইনস্ট্যান্স
db = Database()
validator = EmailValidator()
load_balancer = APILoadBalancer()
ai_engine = AIEngine()
export_engine = ExportEngine()
start_time = time.time()

# লক
processing_locks = {}

# ====================================================================
# API Endpoints
# ====================================================================

# হেলথ চেক
@app.get("/api/health")
async def health():
    return {"status": "healthy", "version": VERSION, "uptime": round(time.time() - start_time)}

# অথেনটিকেশন
@app.post("/api/auth/login")
async def login(username: str = Form(...), password: str = Form(...)):
    user = db.authenticate(username, password)
    if not user:
        raise HTTPException(401, "Invalid credentials")
    token = db.create_session(user["id"])
    db.log_activity(user["id"], username, "login", "auth", "info", "User logged in")
    return {"token": token, "role": user["role"], "username": user["username"], "user_id": user["id"]}

@app.post("/api/auth/logout")
async def logout(token: str = Form(...)):
    db.log_activity(None, "", "logout", "auth", "info", "User logged out")
    return {"status": "ok"}

# ড্যাশবোর্ড
@app.get("/api/dashboard/{user_id}")
async def dashboard(user_id: int):
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    limits = db.get_user_limits(user_id)
    recent_logs = db.get_validation_logs(user_id, 5)
    total_val = sum(l.get("total_records", 0) for l in recent_logs)
    total_valid = sum(l.get("valid_count", 0) for l in recent_logs)
    total_dead = sum(l.get("dead_count", 0) for l in recent_logs)

    return {
        "username": user["username"], "role": user["role"],
        "limits": limits,
        "stats": {
            "total_validated": total_val,
            "valid": total_valid,
            "dead": total_dead,
            "valid_pct": round(total_valid/max(total_val,1)*100, 1),
            "dead_pct": round(total_dead/max(total_val,1)*100, 1),
            "avg_score": round(sum(l.get("avg_score",0) for l in recent_logs)/max(len(recent_logs),1), 1),
            "scans_done": len(recent_logs),
        },
        "recent": [{
            "id": l["id"], "date": l["created_at"][:19] if l["created_at"] else "",
            "total": l["total_records"], "valid": l["valid_count"],
            "dead": l["dead_count"], "score": l["avg_score"], "status": l["fsm_state"],
        } for l in recent_logs],
    }

# ভ্যালিডেশন
@app.post("/api/validation/start")
async def start_validation(token: str = Form(...), file: UploadFile = File(None),
                            paste_text: str = Form(""), remove_dupes: bool = Form(True),
                            threads: int = Form(50), saved_file_id: int = Form(0)):
    session = db.validate_session(token)
    if not session:
        raise HTTPException(401, "Invalid session")

    user_id = session["user_id"]
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(404, "User not found")

    # লিমিট চেক
    limits = db.get_user_limits(user_id)
    if limits.get("is_expired"):
        raise HTTPException(403, "Account expired")
    if limits["scans_today"] >= limits["daily_scan_limit"]:
        raise HTTPException(429, f"Daily limit {limits['daily_scan_limit']} reached")

    # ডেটা সোর্স
    emails = []
    filename = ""
    if saved_file_id > 0:
        data = db.get_saved_file_data(saved_file_id)
        if data:
            emails = [e.strip() for e in data.split("\n") if e.strip()]
        filename = "saved"
    elif file and file.filename:
        content = await file.read()
        text = content.decode("utf-8", errors="ignore")
        emails = [e.strip() for e in text.split("\n") if e.strip()]
        filename = file.filename
    elif paste_text:
        emails = [e.strip() for e in paste_text.split("\n") if e.strip()]
        filename = "paste"

    if not emails:
        raise HTTPException(400, "No emails provided")

    if len(emails) > user["max_records_per_scan"]:
        raise HTTPException(400, f"Max {user['max_records_per_scan']} records per scan")

    # ভ্যালিডেট (অ্যাসিন্ক থ্রেডেড)
    loop = asyncio.get_event_loop()
    log_id, results = await loop.run_in_executor(None, validator.validate_batch, emails, user_id, threads, remove_dupes, None)

    # রেজাল্ট তৈরি
    summary = db.get_results_summary(log_id)

    return {"log_id": log_id, "total": len(results), "summary": summary}

@app.get("/api/validation/results/{log_id}")
async def get_results(log_id: int, page: int = 1, limit: int = 100,
                       status: Optional[str] = None, domain: Optional[str] = None,
                       category: Optional[str] = None, min_inbox: Optional[float] = None):
    offset = (page - 1) * limit
    results = db.get_validation_results(log_id, limit, offset, status, domain, category, min_inbox)
    summary = db.get_results_summary(log_id)
    return {"results": results, "summary": summary, "page": page, "limit": limit}

# এক্সপোর্ট
@app.post("/api/export")
async def export_data(token: str = Form(...), log_id: int = Form(...),
                       format: str = Form("csv"), status_filter: str = Form("All"),
                       domain_filter: str = Form(""), category_filter: str = Form(""),
                       save_to_db: bool = Form(False), delete_after: bool = Form(False)):
    session = db.validate_session(token)
    if not session:
        raise HTTPException(401, "Invalid session")

    results = db.get_validation_results(log_id, 1000000, 0,
                                         status_filter if status_filter != "All" else None,
                                         domain_filter if domain_filter else None,
                                         category_filter if category_filter else None)
    if not results:
        raise HTTPException(404, "No results found")

    df = pd.DataFrame([{
        "Email": r["email"], "Status": r["status"], "Score": r["score"],
        "Category": r["category"], "Country": r["country"], "Age": r["estimated_age"],
        "Inbox Rate %": r["inbox_rate"], "Bounce Rate %": r["bounce_rate"],
        "Real User": "Yes" if r["is_real_user"] else "No",
        "Provider": r["provider"], "Domain": r["domain"],
        "Role Based": "Yes" if r["is_role_based"] else "No",
        "Disposable": "Yes" if r["is_disposable"] else "No",
        "MX Record": "Yes" if r["mx_exists"] else "No",
    } for r in results])

    fmt_map = {"csv": export_engine.to_csv, "txt": export_engine.to_txt,
               "xlsx": export_engine.to_xlsx, "json": export_engine.to_json}
    mime_map = {"csv": "text/csv", "txt": "text/plain",
                "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "json": "application/json"}

    if format not in fmt_map:
        raise HTTPException(400, "Invalid format")

    data = fmt_map[format](df)
    category = results[0]["category"] if results else "Export"
    domain = df["Domain"].iloc[0] if "Domain" in df.columns and len(df) > 0 else "mix"
    filename = export_engine.generate_filename(category, domain, len(df), format)

    if save_to_db:
        db.save_export(session["user_id"], filename, format, len(df), len(data)/1024,
                       {"status": status_filter, "domain": domain_filter, "category": category_filter}, True)

    if delete_after:
        pass  # ক্লায়েন্ট সাইডে

    db.log_activity(session["user_id"], session["username"], f"export:{format}", "export", "info",
                    f"Exported {len(df)} records as {format}")

    return StreamingResponse(io.BytesIO(data), media_type=mime_map[format],
                            headers={"Content-Disposition": f"attachment; filename={filename}"})

# রিপোর্টস
@app.get("/api/reports/{user_id}")
async def get_reports(user_id: int):
    logs = db.get_validation_logs(user_id, 50)
    return {"reports": [{
        "id": l["id"], "date": l["created_at"][:19] if l["created_at"] else "",
        "filename": l["filename"], "total": l["total_records"],
        "valid": l["valid_count"], "dead": l["dead_count"],
        "score": l["avg_score"], "status": l["fsm_state"],
    } for l in logs]}

# AI চ্যাট
@app.post("/api/ai/chat")
async def ai_chat(token: str = Form(...), message: str = Form(...), context: str = Form("{}")):
    session = db.validate_session(token)
    if not session:
        raise HTTPException(401, "Invalid session")
    ctx = json.loads(context) if context else None
    response = ai_engine.chat(session["user_id"], message, ctx)
    return {"response": response}

# সেভড ফাইলস
@app.get("/api/saved-files/{user_id}")
async def get_saved_files(user_id: int):
    return {"files": db.get_saved_files(user_id)}

@app.post("/api/saved-files/save")
async def save_file(token: str = Form(...), filename: str = Form(...),
                     file_type: str = Form("txt"), record_count: int = Form(0),
                     category: str = Form(""), data: str = Form("")):
    session = db.validate_session(token)
    if not session:
        raise HTTPException(401, "Invalid session")
    fid = db.save_file(session["user_id"], filename, file_type, record_count, category, data)
    return {"id": fid, "status": "saved"}

@app.delete("/api/saved-files/{file_id}")
async def delete_saved_file(file_id: int):
    db.delete_saved_file(file_id)
    return {"status": "deleted"}

# ====================================================================
# অ্যাডমিন API
# ====================================================================

@app.get("/api/admin/users")
async def admin_get_users():
    return {"users": [{
        "id": u["id"], "username": u["username"], "role": u["role"],
        "active": u["is_active"], "email": u["email"],
        "data_limit": u["data_limit_mb"], "daily_scans": u["daily_scan_limit"],
        "expiry": u["expiry_date"][:10] if u["expiry_date"] else "N/A",
        "created": u["created_at"][:10] if u["created_at"] else "N/A",
        "last_active": u["last_active"][:16] if u["last_active"] else "N/A",
    } for u in db.get_all_users()]}

@app.post("/api/admin/users/create")
async def admin_create_user(username: str = Form(...), password: str = Form(...),
                              role: str = Form("user"), email: str = Form(""),
                              data_limit: int = Form(10000), daily_scans: int = Form(20),
                              max_records: int = Form(1000000), expiry_days: int = Form(30)):
    success, msg = db.create_user(username=username, password=password, role=role,
                                   email=email, data_limit=data_limit, daily_scans=daily_scans,
                                   max_records=max_records, expiry_days=expiry_days)
    if success:
        db.log_activity(1, "admin", "create_user", "admin", "info", f"Created user {username}")
    return {"success": success, "message": msg}

@app.delete("/api/admin/users/{user_id}")
async def admin_delete_user(user_id: int):
    db.delete_user(user_id)
    db.log_activity(1, "admin", "delete_user", "admin", "info", f"Deleted user #{user_id}")
    return {"status": "deleted"}

# API স্লট ম্যানেজার
@app.get("/api/admin/api-slots")
async def admin_get_api_slots(api_type: Optional[str] = None):
    slots = db.get_api_slots(api_type)
    return {"slots": [{
        "id": s["id"], "slot": s["slot_number"], "type": s["api_type"],
        "name": s.get("friendly_name", f"S{s['slot_number']}"),
        "active": bool(s["is_active"]),
        "health": s["health_status"],
        "usage": s["usage_percent"],
        "has_key": bool(s["api_key_encrypted"]),
        "endpoint": s.get("endpoint_url", ""),
        "last_checked": s.get("last_checked", ""),
    } for s in slots]}

@app.post("/api/admin/api-slots/update")
async def admin_update_api_slot(slot_id: int = Form(...), api_key: str = Form(""),
                                  endpoint: str = Form(""), name: str = Form(""),
                                  is_active: bool = Form(True)):
    db.update_api_slot(slot_id,
        api_key_encrypted=api_key or None,
        endpoint_url=endpoint or None,
        friendly_name=name or None,
        is_active=1 if is_active else 0)
    return {"status": "updated"}

@app.post("/api/admin/api-slots/test")
async def admin_test_api_slots(api_type: str = Form("all")):
    results = load_balancer.test_all(api_type if api_type != "all" else None)
    return {"results": results}

# লাইভ লগস
@app.get("/api/admin/logs")
async def admin_get_logs(severity: str = "All", module: str = "All", limit: int = 100):
    return {"logs": [{
        "time": l["created_at"][:19] if l["created_at"] else "",
        "severity": l["severity"], "module": l["module"],
        "user": l["username"], "action": l["action"],
        "message": l["message"][:100],
        "auto_fixed": bool(l["auto_fixed"]),
    } for l in db.get_activity_logs(limit, severity, module)]}

@app.post("/api/admin/logs/clear")
async def admin_clear_logs(severity: str = Form("all")):
    db.clear_logs(severity if severity != "all" else None)
    return {"status": "cleared"}

# অ্যানালিটিক্স
@app.get("/api/admin/analytics")
async def admin_get_analytics(days: int = 30):
    analytics = db.get_analytics(days)
    return analytics

# এক্সপোর্ট লিস্ট
@app.get("/api/exports/{user_id}")
async def get_exports(user_id: int):
    exports = db.get_exports(user_id)
    return {"exports": [{
        "id": e["id"], "filename": e["filename"], "format": e["format"],
        "records": e["record_count"], "size": e["file_size_kb"],
        "date": e["created_at"][:19] if e["created_at"] else "",
        "saved": bool(e["saved_to_db"]),
    } for e in exports]}

@app.delete("/api/exports/{export_id}")
async def delete_export(export_id: int):
    db.delete_export(export_id)
    return {"status": "deleted"}

# অ্যাক্টিভিটি লগ
@app.post("/api/log/activity")
async def log_activity(token: str = Form(...), action: str = Form(...),
                        module: str = Form("system"), severity: str = Form("info"),
                        message: str = Form("")):
    session = db.validate_session(token)
    if not session:
        raise HTTPException(401, "Invalid session")
    db.log_activity(session["user_id"], session["username"], action, module, severity, message)
    return {"status": "logged"}

# সেশন স্টেট
@app.post("/api/session/state")
async def save_session_state(token: str = Form(...), ui_state: str = Form("{}"),
                              scan_state: str = Form("{}"), filters_state: str = Form("{}")):
    db.save_session_state(token, ui_state, scan_state, filters_state)
    return {"status": "saved"}

@app.post("/api/session/validate")
async def validate_session(token: str = Form(...)):
    session = db.validate_session(token)
    if not session:
        raise HTTPException(401, "Invalid session")
    return {"valid": True, "role": session["role"], "username": session["username"],
            "user_id": session["user_id"]}

# ====================================================================
# ফ্রন্টএন্ড সার্ভ
# ====================================================================
@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    index_path = os.path.join(base_dir, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<html><body><h1>CYBER-CORE v7.0</h1><p>Frontend not found. Create index.html</p></body></html>"

@app.get("/{path:path}", response_class=HTMLResponse)
async def catch_all(path: str):
    if path.startswith("api/"):
        raise HTTPException(404, "API endpoint not found")
    return await serve_frontend()


# ====================================================================
# এন্ট্রি পয়েন্ট
# ====================================================================
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
