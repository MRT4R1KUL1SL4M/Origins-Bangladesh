"""
Origins Bangladesh - Flask + MySQL (mysql-connector-python)

Goal: Navbar buttons behave realistically:
- Search -> /shop?q=...
- Currency change -> /set-currency/<code> (session)
- Wishlist -> /wishlist (DB-backed)
- Cart -> /cart (DB-backed)
- Login/Register -> /auth/login, /auth/register (DB-backed)
- Category/Subcategory -> /shop?category=...&sub=...
"""

from __future__ import annotations

import os
import re
import datetime
import mimetypes
from pathlib import Path as FSPath
import math
import hashlib
import json
import secrets
import smtplib
import time
from email.message import EmailMessage
from decimal import Decimal, ROUND_HALF_UP
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode, quote

import mysql.connector
from mysql.connector import Error as MySQLError
from markupsafe import Markup
from flask import (
    Flask,
    jsonify,
    Response,
    abort,
    flash,
    redirect,
    render_template,
    render_template_string,
    request,
    session,
    send_file,
    url_for,
)
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from dotenv import load_dotenv

# PDF export (Super Admin report)
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image as RLImage
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics import renderPDF

# Excel export (Super Admin report)
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

load_dotenv()

app = Flask(__name__)
app.config.from_object("config.Config")


# -----------------------
# DB Bootstrap (lightweight, safe)
# -----------------------
# This project ships as a single-file Flask app without a migration runner.
# To keep Super Admin sections truly DB-backed, we create a few small support
# tables if they don't exist yet.
_DB_BOOTSTRAPPED = False




def _admin_asset_url(path: Optional[str]) -> Optional[str]:
    path = (path or '').strip()
    if not path:
        return None
    if path.startswith(('http://', 'https://', '/static/', 'data:')):
        return path
    if path.startswith('static/'):
        return '/' + path
    return path


def _mix_demo_rows(rows, demos, key='id', minimum=3):
    rows = list(rows or [])
    seen = {str((r or {}).get(key)) for r in rows if isinstance(r, dict) and (r or {}).get(key) is not None}
    out = rows[:]
    for demo in demos or []:
        if len(out) >= max(minimum, len(rows)) and len(rows) >= minimum:
            break
        if str(demo.get(key)) not in seen:
            out.append(demo)
            seen.add(str(demo.get(key)))
    return out


def _guess_document_kind(url: Optional[str], label: Optional[str] = None) -> str:
    target = ((url or '') + ' ' + (label or '')).lower()
    ext = os.path.splitext((url or '').split('?')[0])[1].lower()
    if ext in {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.bmp'}:
        return 'image'
    if ext == '.pdf' or 'pdf' in target:
        return 'pdf'
    if ext in {'.txt', '.md', '.json', '.csv', '.log', '.xml', '.html'}:
        return 'text'
    mime, _ = mimetypes.guess_type(url or '')
    if mime and mime.startswith('image/'):
        return 'image'
    if mime == 'application/pdf':
        return 'pdf'
    return 'text' if not url or url == '#' else 'file'


def _read_local_text_preview(url: Optional[str], limit: int = 12000) -> str:
    url = (url or '').strip()
    if not url or url == '#' or url.startswith(('http://', 'https://', 'data:')):
        return ''
    rel = url[1:] if url.startswith('/') else url
    rel = rel.lstrip('./')
    base = FSPath(app.root_path)
    path = (base / rel).resolve()
    try:
        path.relative_to(base)
    except Exception:
        return ''
    if not path.exists() or not path.is_file():
        return ''
    if path.suffix.lower() not in {'.txt', '.md', '.json', '.csv', '.log', '.xml', '.html'}:
        return ''
    try:
        return path.read_text(encoding='utf-8', errors='ignore')[:limit]
    except Exception:
        return ''


def _format_admin_documents(title: str, docs: List[Dict[str, Any]]) -> Dict[str, Any]:
    rows = []
    for idx, d in enumerate(docs or [], start=1):
        label = d.get('label') or f'Document {idx}'
        url = d.get('url') or '#'
        meta = d.get('uploaded_at') or d.get('meta') or ''
        kind = d.get('kind') or _guess_document_kind(url, label)
        text_content = d.get('text_content') or ''
        if kind == 'text' and not text_content:
            text_content = _read_local_text_preview(url) or (meta if (not url or url == '#') else '')
        rows.append({
            'id': idx,
            'label': label,
            'url': url,
            'meta': meta,
            'kind': kind,
            'text_content': text_content,
        })
    return {'title': title, 'documents': rows}


def _admin_no_documents(title: str, message: str = 'No uploaded documents were found for this record yet.') -> Dict[str, Any]:
    return _format_admin_documents(title, [{
        'label': 'No documents available',
        'kind': 'text',
        'text_content': message,
        'uploaded_at': 'Awaiting upload'
    }])


def _get_admin_documents_payload(kind: str, record_id: int) -> Dict[str, Any]:
    kind = (kind or '').strip().lower()
    if kind == 'verification':
        docs = db_fetchall(
            """
            SELECT doc_type, file_path, uploaded_at
            FROM seller_verification_doc
            WHERE seller_id=%s
            ORDER BY uploaded_at DESC, doc_type ASC
            """,
            (record_id,),
        ) or []
        rows = [{
            'label': (d.get('doc_type') or 'Document').replace('_', ' ').title(),
            'url': _admin_asset_url(d.get('file_path')) or '#',
            'uploaded_at': d.get('uploaded_at').strftime('%d %b %Y, %I:%M %p') if d.get('uploaded_at') else '',
        } for d in docs]
        return _format_admin_documents('Verification Documents', rows) if rows else _admin_no_documents('Verification Documents')
    if kind == 'qc':
        row = db_fetchone(
            """
            SELECT q.qc_id, q.product_id, p.title, p.image_path, p.description, COALESCE(sp.shop_name, 'Seller') AS seller
            FROM admin_qc_item q
            JOIN product p ON p.product_id=q.product_id
            LEFT JOIN seller_profile sp ON sp.seller_id=q.seller_id
            WHERE q.qc_id=%s OR q.product_id=%s
            ORDER BY CASE WHEN q.qc_id=%s THEN 0 ELSE 1 END
            LIMIT 1
            """,
            (record_id, record_id, record_id),
        ) or {}
        docs = []
        if row:
            docs.append({'label': f"Product Image • {row.get('title') or 'Artifact'}", 'url': _admin_asset_url(row.get('image_path')) or '#', 'uploaded_at': row.get('seller') or ''})
            docs.append({'label': 'Product Description', 'kind': 'text', 'text_content': str(row.get('description') or 'No description available.'), 'uploaded_at': row.get('seller') or ''})
            docs.append({'label': 'QC Reference', 'kind': 'text', 'text_content': f"QC ID: {row.get('qc_id') or '—'}\nProduct ID: {row.get('product_id') or '—'}", 'uploaded_at': 'System reference'})
        return _format_admin_documents('Quality Control Documents', docs) if docs else _admin_no_documents('Quality Control Documents')
    if kind == 'gi':
        row = db_fetchone(
            """
            SELECT a.app_id, a.product_name, a.certificate_path, a.details,
                   COALESCE(sp.shop_name, 'Seller') AS seller, COALESCE(sp.location, 'Bangladesh') AS district
            FROM seller_gi_application a
            LEFT JOIN seller_profile sp ON sp.seller_id=a.seller_id
            WHERE a.app_id=%s
            """,
            (record_id,),
        ) or {}
        docs = []
        if row:
            docs.append({'label': f"GI Certificate • {row.get('product_name') or 'Artifact'}", 'url': _admin_asset_url(row.get('certificate_path')) or '#', 'uploaded_at': row.get('district') or ''})
            docs.append({'label': 'Seller / Region', 'kind': 'text', 'text_content': f"{row.get('seller') or 'Seller'} • {row.get('district') or 'Bangladesh'}", 'uploaded_at': 'Identity reference'})
            docs.append({'label': 'Application Notes', 'kind': 'text', 'text_content': str(row.get('details') or 'No additional notes provided.'), 'uploaded_at': 'Supporting narrative'})
        return _format_admin_documents('GI Certification Dossier', docs) if docs else _admin_no_documents('GI Certification Dossier')
    return _admin_no_documents('Document Viewer')


def _build_featured_selection_queue():
    rows = db_fetchall(
        """
        SELECT sp.seller_id AS id,
               COALESCE(sp.shop_name, ua.name, CONCAT('Seller #', sp.seller_id)) AS name,
               COALESCE(sp.location, 'Bangladesh') AS district,
               COALESCE(sp.avatar_url, '') AS img,
               ROUND(COALESCE(SUM(oi.quantity * oi.unit_price_bdt), 0), 2) AS yesterday_sales,
               COALESCE(SUM(oi.quantity), 0) AS items_sold,
               ROUND(4.6 + (COALESCE(SUM(oi.quantity),0) / 200), 1) AS rating
        FROM seller_profile sp
        JOIN user_account ua ON ua.user_id = sp.seller_id
        LEFT JOIN product p ON p.seller_id = sp.seller_id
        LEFT JOIN order_item oi ON oi.product_id = p.product_id
        LEFT JOIN `order` o ON o.order_id = oi.order_id
             AND DATE(o.created_at) = DATE_SUB(CURDATE(), INTERVAL 1 DAY)
             AND LOWER(o.status) IN ('paid','shipped','delivered')
        WHERE ua.role = 'seller'
        GROUP BY sp.seller_id, sp.shop_name, ua.name, sp.location, sp.avatar_url
        ORDER BY yesterday_sales DESC, items_sold DESC, sp.seller_id DESC
        LIMIT 5
        """
    ) or []
    normalized = []
    for idx, row in enumerate(rows, 1):
        normalized.append({
            'id': row.get('id'),
            'name': row.get('name') or f'Seller #{row.get("id")}',
            'district': row.get('district') or 'Bangladesh',
            'img': _admin_asset_url(row.get('img')) or '/static/assets/img/placeholder.jpg',
            'rating': f"{float(row.get('rating') or 4.8):.1f}",
            'yesterday_sales': float(row.get('yesterday_sales') or 0),
            'yesterday_sales_fmt': fmt_money(row.get('yesterday_sales') or 0),
            'items_sold': int(row.get('items_sold') or 0),
        })
    demos = [
        {'id': 90001, 'name': 'Demo Jamdani House', 'district': 'Narayanganj', 'img': '/static/assets/img/placeholder.jpg', 'rating': '4.9', 'yesterday_sales': 42000, 'yesterday_sales_fmt': 'BDT 42,000', 'items_sold': 9},
        {'id': 90002, 'name': 'Demo Shital Pati Studio', 'district': 'Sylhet', 'img': '/static/assets/img/placeholder.jpg', 'rating': '4.8', 'yesterday_sales': 31500, 'yesterday_sales_fmt': 'BDT 31,500', 'items_sold': 7},
        {'id': 90003, 'name': 'Demo Terracotta Craft', 'district': 'Comilla', 'img': '/static/assets/img/placeholder.jpg', 'rating': '4.8', 'yesterday_sales': 28500, 'yesterday_sales_fmt': 'BDT 28,500', 'items_sold': 6},
    ]
    return _mix_demo_rows(normalized[:5], demos, minimum=3)[:5]

def _bootstrap_db_once() -> None:
    global _DB_BOOTSTRAPPED
    if _DB_BOOTSTRAPPED:
        return
    _DB_BOOTSTRAPPED = True

    # Best-effort: never crash the app if bootstrap fails.
    conn = None
    try:
        conn = get_db()
        cur = conn.cursor()

        # Stores extra data for admin users (designation shown in Super Admin UI)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_profile (
              admin_id INT PRIMARY KEY,
              designation VARCHAR(120) NULL,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              CONSTRAINT fk_admin_profile_user FOREIGN KEY (admin_id)
                REFERENCES user_account(user_id) ON DELETE CASCADE
            ) ENGINE=InnoDB
            """
        )

        # Backfill modern admin profile fields if table already existed
        for stmt in [
            "ALTER TABLE admin_profile ADD COLUMN avatar_url VARCHAR(500) NULL AFTER designation",
            "ALTER TABLE admin_profile ADD COLUMN updated_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP AFTER created_at",
        ]:
            try:
                cur.execute(stmt)
            except Exception:
                pass

        for stmt in [
            "ALTER TABLE user_account ADD COLUMN public_id VARCHAR(32) NULL UNIQUE AFTER role",
        ]:
            try:
                cur.execute(stmt)
            except Exception:
                pass

        try:
            cur.execute("SELECT user_id, role, public_id FROM user_account WHERE public_id IS NULL OR public_id='' ORDER BY user_id ASC")
            pending_public_ids = cur.fetchall() or []
            for row in pending_public_ids:
                role = str((row[1] if not isinstance(row, dict) else row.get('role')) or 'buyer').lower()
                uid = int((row[0] if not isinstance(row, dict) else row.get('user_id')) or 0)
                current_public = (row[2] if not isinstance(row, dict) else row.get('public_id'))
                if uid > 0:
                    try:
                        public_id = issue_public_id(role, uid, current_public)
                        cur.execute("UPDATE user_account SET public_id=%s WHERE user_id=%s", (public_id, uid))
                    except Exception:
                        pass
            conn.commit()
        except Exception:
            pass

        # Admin-only content/editorial team
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_team_member (
              team_id INT AUTO_INCREMENT PRIMARY KEY,
              name VARCHAR(120) NOT NULL,
              email VARCHAR(180) NOT NULL UNIQUE,
              role VARCHAR(80) NOT NULL DEFAULT 'Editor',
              article_count INT NOT NULL DEFAULT 0,
              is_active TINYINT(1) NOT NULL DEFAULT 1,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
              created_by INT NULL
            ) ENGINE=InnoDB
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_coupon (
              coupon_id INT AUTO_INCREMENT PRIMARY KEY,
              code VARCHAR(64) NOT NULL UNIQUE,
              discount_type ENUM('Percentage','Fixed Amount','Free Delivery') NOT NULL DEFAULT 'Percentage',
              discount_value DECIMAL(12,2) NOT NULL DEFAULT 0,
              usage_limit INT NULL,
              used_count INT NOT NULL DEFAULT 0,
              expires_at DATE NULL,
              is_new_user_only TINYINT(1) NOT NULL DEFAULT 0,
              is_active TINYINT(1) NOT NULL DEFAULT 1,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
              created_by INT NULL,
              INDEX idx_coupon_active (is_active, expires_at)
            ) ENGINE=InnoDB
            """
        )

        # Backfill modern commerce columns for legacy schemas created from older schema.sql files
        for stmt in [
            "ALTER TABLE admin_coupon ADD COLUMN minimum_subtotal_bdt DECIMAL(12,2) NULL AFTER is_new_user_only",
            "ALTER TABLE admin_coupon ADD COLUMN maximum_discount_bdt DECIMAL(12,2) NULL AFTER minimum_subtotal_bdt",
            "ALTER TABLE admin_coupon ADD COLUMN starts_at DATETIME NULL AFTER maximum_discount_bdt",
            "ALTER TABLE admin_coupon ADD COLUMN per_user_limit INT NULL AFTER starts_at",
            "ALTER TABLE admin_coupon ADD COLUMN applicable_scope VARCHAR(20) NOT NULL DEFAULT 'all' AFTER per_user_limit",
            "ALTER TABLE `order` ADD COLUMN subtotal_bdt DECIMAL(12,2) NOT NULL DEFAULT 0 AFTER status",
            "ALTER TABLE `order` ADD COLUMN shipping_bdt DECIMAL(12,2) NOT NULL DEFAULT 0 AFTER subtotal_bdt",
            "ALTER TABLE `order` ADD COLUMN discount_bdt DECIMAL(12,2) NOT NULL DEFAULT 0 AFTER shipping_bdt",
            "ALTER TABLE `order` ADD COLUMN coupon_id INT NULL AFTER discount_bdt",
            "ALTER TABLE `order` ADD COLUMN payment_status VARCHAR(20) NOT NULL DEFAULT 'pending' AFTER total_bdt",
            "ALTER TABLE `order` ADD COLUMN payment_method VARCHAR(40) NULL AFTER payment_status",
            "ALTER TABLE `order` ADD COLUMN shipping_name VARCHAR(120) NULL AFTER payment_method",
            "ALTER TABLE `order` ADD COLUMN shipping_phone VARCHAR(40) NULL AFTER shipping_name",
            "ALTER TABLE `order` ADD COLUMN shipping_email VARCHAR(180) NULL AFTER shipping_phone",
            "ALTER TABLE `order` ADD COLUMN shipping_address_line VARCHAR(255) NULL AFTER shipping_email",
            "ALTER TABLE `order` ADD COLUMN shipping_apartment VARCHAR(255) NULL AFTER shipping_address_line",
            "ALTER TABLE `order` ADD COLUMN shipping_country VARCHAR(120) NULL AFTER shipping_apartment",
            "ALTER TABLE `order` ADD COLUMN shipping_city VARCHAR(120) NULL AFTER shipping_country",
            "ALTER TABLE `order` ADD COLUMN postal_code VARCHAR(30) NULL AFTER shipping_city",
            "ALTER TABLE `order` ADD COLUMN invoice_no VARCHAR(40) NULL AFTER postal_code",
            "ALTER TABLE `order` ADD COLUMN placed_at DATETIME NULL AFTER invoice_no",
            "ALTER TABLE `order` ADD COLUMN delivered_at DATETIME NULL AFTER placed_at",
            "ALTER TABLE `order_item` ADD COLUMN product_title_snapshot VARCHAR(200) NULL AFTER unit_price_bdt",
            "ALTER TABLE `order_item` ADD COLUMN product_image_snapshot VARCHAR(255) NULL AFTER product_title_snapshot",
            "ALTER TABLE `order_item` ADD COLUMN artisan_name_snapshot VARCHAR(120) NULL AFTER product_image_snapshot",
        ]:
            try:
                cur.execute(stmt)
            except Exception:
                pass

        # Commerce / buyer experience support tables
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS coupon_redemption (
              redemption_id BIGINT AUTO_INCREMENT PRIMARY KEY,
              coupon_id INT NOT NULL,
              buyer_id INT NOT NULL,
              order_id INT NULL,
              discount_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
              redeemed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              INDEX idx_coupon_redemption_coupon (coupon_id, redeemed_at),
              INDEX idx_coupon_redemption_buyer (buyer_id, redeemed_at)
            ) ENGINE=InnoDB
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS buyer_point_ledger (
              ledger_id BIGINT AUTO_INCREMENT PRIMARY KEY,
              buyer_id INT NOT NULL,
              order_id INT NULL,
              points_delta INT NOT NULL DEFAULT 0,
              reason VARCHAR(40) NOT NULL DEFAULT 'purchase',
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              INDEX idx_point_buyer (buyer_id, created_at)
            ) ENGINE=InnoDB
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS order_status_history (
              history_id BIGINT AUTO_INCREMENT PRIMARY KEY,
              order_id INT NOT NULL,
              status VARCHAR(40) NOT NULL,
              note VARCHAR(255) NULL,
              actor_type VARCHAR(20) NOT NULL DEFAULT 'system',
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              INDEX idx_order_status_history (order_id, created_at)
            ) ENGINE=InnoDB
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS order_provenance_event (
              event_id BIGINT AUTO_INCREMENT PRIMARY KEY,
              order_item_id INT NOT NULL,
              event_type VARCHAR(50) NOT NULL,
              title VARCHAR(160) NOT NULL,
              description TEXT NULL,
              actor_type VARCHAR(20) NOT NULL DEFAULT 'system',
              actor_id INT NULL,
              metadata_json TEXT NULL,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              INDEX idx_order_provenance_item (order_item_id, created_at)
            ) ENGINE=InnoDB
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS buyer_campaign (
              campaign_id BIGINT AUTO_INCREMENT PRIMARY KEY,
              title VARCHAR(180) NOT NULL,
              subtitle VARCHAR(255) NULL,
              image_url VARCHAR(500) NULL,
              access_rule VARCHAR(40) NOT NULL DEFAULT 'all_buyers',
              min_points INT NOT NULL DEFAULT 0,
              starts_at DATETIME NULL,
              ends_at DATETIME NULL,
              cta_label VARCHAR(80) NULL,
              cta_url VARCHAR(255) NULL,
              is_active TINYINT(1) NOT NULL DEFAULT 1,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS newsletter_subscriber (
              subscriber_id INT AUTO_INCREMENT PRIMARY KEY,
              email VARCHAR(180) NOT NULL UNIQUE,
              is_active TINYINT(1) NOT NULL DEFAULT 1,
              subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_qc_item (
              qc_id INT AUTO_INCREMENT PRIMARY KEY,
              product_id INT NOT NULL,
              seller_id INT NULL,
              status ENUM('Pending','Approved','Rejected','Changes Requested') NOT NULL DEFAULT 'Pending',
              note TEXT NULL,
              reviewed_by INT NULL,
              reviewed_at TIMESTAMP NULL,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              UNIQUE KEY uq_qc_product (product_id),
              INDEX idx_qc_status (status, created_at)
            ) ENGINE=InnoDB
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_dispute (
              dispute_id INT AUTO_INCREMENT PRIMARY KEY,
              order_id INT NULL,
              issue TEXT NOT NULL,
              priority ENUM('Low','Medium','High') NOT NULL DEFAULT 'Medium',
              status ENUM('Open','Refunded','Dismissed') NOT NULL DEFAULT 'Open',
              resolution_note TEXT NULL,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              resolved_at TIMESTAMP NULL,
              resolved_by INT NULL,
              INDEX idx_dispute_status (status, created_at)
            ) ENGINE=InnoDB
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_commission_rule (
              rule_id INT AUTO_INCREMENT PRIMARY KEY,
              title VARCHAR(120) NOT NULL DEFAULT 'Default Platform Commission',
              percentage DECIMAL(5,2) NOT NULL DEFAULT 10.00,
              is_active TINYINT(1) NOT NULL DEFAULT 1,
              updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
              updated_by INT NULL
            ) ENGINE=InnoDB
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_message_thread (
              thread_id INT AUTO_INCREMENT PRIMARY KEY,
              seller_id INT NOT NULL,
              subject VARCHAR(180) NOT NULL,
              last_message TEXT NULL,
              updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              INDEX idx_msg_thread (updated_at)
            ) ENGINE=InnoDB
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_message (
              message_id INT AUTO_INCREMENT PRIMARY KEY,
              thread_id INT NOT NULL,
              sender_role ENUM('admin','seller') NOT NULL,
              body TEXT NOT NULL,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              CONSTRAINT fk_admin_msg_thread FOREIGN KEY (thread_id)
                REFERENCES admin_message_thread(thread_id) ON DELETE CASCADE
            ) ENGINE=InnoDB
            """
        )

        # Simple key/value system settings
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS system_setting (
              setting_key VARCHAR(64) PRIMARY KEY,
              setting_value TEXT NULL,
              updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB
            """
        )

        # Audit log for Super Admin actions
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_log (
              audit_id BIGINT AUTO_INCREMENT PRIMARY KEY,
              actor_user_id INT NOT NULL,
              action VARCHAR(80) NOT NULL,
              target_user_id INT NULL,
              ip VARCHAR(64) NULL,
              user_agent VARCHAR(255) NULL,
              metadata_json TEXT NULL,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              INDEX idx_audit_actor (actor_user_id, created_at),
              INDEX idx_audit_target (target_user_id, created_at),
              CONSTRAINT fk_audit_actor FOREIGN KEY (actor_user_id)
                REFERENCES user_account(user_id) ON DELETE CASCADE,
              CONSTRAINT fk_audit_target FOREIGN KEY (target_user_id)
                REFERENCES user_account(user_id) ON DELETE SET NULL
            ) ENGINE=InnoDB
            """
        )



        # Seller payout requests (Super Admin -> Payout Requests)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS payout_request (
              payout_id BIGINT AUTO_INCREMENT PRIMARY KEY,
              trx_id VARCHAR(40) NOT NULL,
              seller_user_id INT NULL,
              shop_name VARCHAR(160) NULL,
              shop_email VARCHAR(160) NULL,
              amount_bdt DECIMAL(12,2) NOT NULL DEFAULT 0,
              destination_type VARCHAR(60) NULL,
              destination_value VARCHAR(160) NULL,
              status VARCHAR(20) NOT NULL DEFAULT 'Pending',
              notes TEXT NULL,
              requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              processed_at TIMESTAMP NULL,
              processed_by INT NULL,
              INDEX idx_payout_status (status, requested_at),
              INDEX idx_payout_seller (seller_user_id, requested_at)
            ) ENGINE=InnoDB
            """
        )

        # Backup log (Security & DB -> Initiate Backup)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS backup_log (
              backup_id BIGINT AUTO_INCREMENT PRIMARY KEY,
              started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              finished_at TIMESTAMP NULL,
              status VARCHAR(20) NOT NULL DEFAULT 'RUNNING',
              file_path VARCHAR(255) NULL,
              details_json TEXT NULL,
              created_by INT NULL,
              INDEX idx_backup_time (started_at)
            ) ENGINE=InnoDB
            """
        )

        # Access block list (Security & DB -> Ban Authority)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS access_block (
              block_id BIGINT AUTO_INCREMENT PRIMARY KEY,
              block_type VARCHAR(10) NOT NULL, -- 'ip' or 'user'
              block_value VARCHAR(120) NOT NULL,
              reason VARCHAR(255) NULL,
              is_active TINYINT(1) NOT NULL DEFAULT 1,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              created_by INT NULL,
              INDEX idx_block_active (is_active, block_type, block_value)
            ) ENGINE=InnoDB
            """
        )

        # Report export registry (for QR verification / audit)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS report_export (
              report_id BIGINT AUTO_INCREMENT PRIMARY KEY,
              report_code CHAR(32) NOT NULL UNIQUE,
              format VARCHAR(10) NOT NULL, -- 'pdf' or 'xlsx'
              file_path VARCHAR(255) NOT NULL,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              created_by INT NULL,
              meta_json TEXT NULL,
              INDEX idx_report_time (created_at)
            ) ENGINE=InnoDB
            """
        )

        # Email template overrides / branding (optional)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS email_template (
              template_key VARCHAR(64) PRIMARY KEY,
              subject_override VARCHAR(160) NULL,
              html_override MEDIUMTEXT NULL,
              text_override MEDIUMTEXT NULL,
              updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB
            """
        )

        # Approval workflow for destructive admin actions (e.g., permanent delete)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS action_approval (
              approval_id BIGINT AUTO_INCREMENT PRIMARY KEY,
              actor_user_id INT NOT NULL,
              action_key VARCHAR(64) NOT NULL,
              target_user_id INT NULL,
              code_hash CHAR(64) NOT NULL,
              salt CHAR(16) NOT NULL,
              expires_at DATETIME NOT NULL,
              consumed_at DATETIME NULL,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              INDEX idx_approval_lookup (actor_user_id, action_key, target_user_id, expires_at),
              CONSTRAINT fk_approval_actor FOREIGN KEY (actor_user_id)
                REFERENCES user_account(user_id) ON DELETE CASCADE
            ) ENGINE=InnoDB
            """
        )

        # Security events (for alerts)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS security_event (
              event_id BIGINT AUTO_INCREMENT PRIMARY KEY,
              event_type VARCHAR(40) NOT NULL,
              severity VARCHAR(10) NOT NULL DEFAULT 'info',
              actor_email VARCHAR(160) NULL,
              ip VARCHAR(64) NULL,
              user_agent VARCHAR(255) NULL,
              message VARCHAR(255) NULL,
              meta_json TEXT NULL,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              INDEX idx_sec_type_time (event_type, created_at),
              INDEX idx_sec_ip_time (ip, created_at)
            ) ENGINE=InnoDB
            """
        )

        # In-app notifications (Super Admin bell)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS notification (
              notification_id BIGINT AUTO_INCREMENT PRIMARY KEY,
              recipient_user_id INT NOT NULL,
              type VARCHAR(40) NOT NULL,
              severity VARCHAR(10) NOT NULL DEFAULT 'info',
              title VARCHAR(180) NOT NULL,
              body VARCHAR(255) NULL,
              link VARCHAR(255) NULL,
              meta_json TEXT NULL,
              is_read TINYINT(1) NOT NULL DEFAULT 0,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              read_at TIMESTAMP NULL,
              INDEX idx_notif_recipient (recipient_user_id, is_read, created_at),
              CONSTRAINT fk_notif_recipient FOREIGN KEY (recipient_user_id)
                REFERENCES user_account(user_id) ON DELETE CASCADE
            ) ENGINE=InnoDB
            """
        )

        # Role-permission matrix (future-proof; not enforced server-side yet)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_permission (
              admin_id INT NOT NULL,
              module_key VARCHAR(60) NOT NULL,
              can_view TINYINT(1) NOT NULL DEFAULT 1,
              can_edit TINYINT(1) NOT NULL DEFAULT 0,
              updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
              PRIMARY KEY (admin_id, module_key),
              CONSTRAINT fk_perm_admin FOREIGN KEY (admin_id)
                REFERENCES user_account(user_id) ON DELETE CASCADE
            ) ENGINE=InnoDB
            """
        )
        # Defaults
        cur.execute(
            "INSERT IGNORE INTO system_setting (setting_key, setting_value) VALUES (%s, %s)",
            ("maintenance_mode", "0"),
        )
        cur.execute(
            "INSERT IGNORE INTO system_setting (setting_key, setting_value) VALUES (%s, %s)",
            ("debug_mode", "0"),
        )
        cur.execute(
            "INSERT IGNORE INTO system_setting (setting_key, setting_value) VALUES (%s, %s)",
            ("ai_provider", "openai"),
        )
        cur.execute(
            "INSERT IGNORE INTO system_setting (setting_key, setting_value) VALUES (%s, %s)",
            ("db_capacity_mb", "1024"),
        )

        # Email branding defaults
        cur.execute(
            "INSERT IGNORE INTO system_setting (setting_key, setting_value) VALUES (%s,%s)",
            ("email_footer_note", "If you didn’t request this, please contact support."),
        )
        cur.execute(
            "INSERT IGNORE INTO system_setting (setting_key, setting_value) VALUES (%s,%s)",
            ("email_signature_name", "Origins Bangladesh"),
        )
        cur.execute(
            "INSERT IGNORE INTO system_setting (setting_key, setting_value) VALUES (%s,%s)",
            ("email_signature_title", "Security & Operations"),
        )

        # Report branding defaults
        cur.execute(
            "INSERT IGNORE INTO system_setting (setting_key, setting_value) VALUES (%s,%s)",
            ("brand_org_name", "Origins Bangladesh"),
        )
        cur.execute(
            "INSERT IGNORE INTO system_setting (setting_key, setting_value) VALUES (%s,%s)",
            ("brand_watermark_text", "CONFIDENTIAL"),
        )
        cur.execute(
            "INSERT IGNORE INTO system_setting (setting_key, setting_value) VALUES (%s,%s)",
            ("brand_signature_name", "Authorized Signatory"),
        )
        cur.execute(
            "INSERT IGNORE INTO system_setting (setting_key, setting_value) VALUES (%s,%s)",
            ("brand_signature_title", "Super Admin Office"),
        )
        cur.execute(
            "INSERT IGNORE INTO system_setting (setting_key, setting_value) VALUES (%s,%s)",
            ("brand_logo_path", "static/assets/img/brand_logo.png"),
        )
        cur.execute(
            "INSERT IGNORE INTO system_setting (setting_key, setting_value) VALUES (%s,%s)",
            ("artisan_hour_live", "0"),
        )
        cur.execute(
            "INSERT IGNORE INTO system_setting (setting_key, setting_value) VALUES (%s,%s)",
            ("artisan_hour_start", "14:00"),
        )
        cur.execute(
            "INSERT IGNORE INTO system_setting (setting_key, setting_value) VALUES (%s,%s)",
            ("artisan_hour_end", "16:00"),
        )
        cur.execute(
            "INSERT IGNORE INTO system_setting (setting_key, setting_value) VALUES (%s,%s)",
            ("home_hero_headline", "Threads of\nTradition,\nWoven with Soul."),
        )
        cur.execute(
            "INSERT IGNORE INTO system_setting (setting_key, setting_value) VALUES (%s,%s)",
            ("home_hero_subtext", "Discover the authenticity of Bengal. From the legendary Muslin to the royal Jamdani, bring home artifacts that carry a millennium of history."),
        )
        cur.execute(
            "INSERT IGNORE INTO system_setting (setting_key, setting_value) VALUES (%s,%s)",
            ("home_hero_image", "/static/assets/img/hero.png?auto=format&fit=crop&q=80&w=1200"),
        )
        cur.execute(
            "INSERT IGNORE INTO system_setting (setting_key, setting_value) VALUES (%s,%s)",
            ("featured_seller_id", "0"),
        )

        # Approval workflow defaults
        cur.execute(
            "INSERT IGNORE INTO system_setting (setting_key, setting_value) VALUES (%s,%s)",
            ("approval_required_permanent_delete", "1"),
        )
        cur.execute(
            "INSERT IGNORE INTO system_setting (setting_key, setting_value) VALUES (%s,%s)",
            ("approval_code_ttl_minutes", "10"),
        )

        # Alert defaults
        cur.execute(
            "INSERT IGNORE INTO system_setting (setting_key, setting_value) VALUES (%s,%s)",
            ("alerts_enabled", "1"),
        )
        cur.execute(
            "INSERT IGNORE INTO system_setting (setting_key, setting_value) VALUES (%s,%s)",
            ("alert_failed_login_threshold", "5"),
        )
        cur.execute(
            "INSERT IGNORE INTO system_setting (setting_key, setting_value) VALUES (%s,%s)",
            ("alert_failed_login_window_minutes", "15"),
        )
        cur.execute(
            "INSERT IGNORE INTO system_setting (setting_key, setting_value) VALUES (%s,%s)",
            ("alert_payout_spike_multiplier", "3"),
        )
        cur.execute(
            "INSERT IGNORE INTO system_setting (setting_key, setting_value) VALUES (%s,%s)",
            ("alert_payout_spike_min_bdt", "5000"),
        )


        cur.execute(
            "INSERT IGNORE INTO admin_commission_rule (rule_id, title, percentage, is_active) VALUES (1, 'Default Platform Commission', 10.00, 1)"
        )
        cur.execute(
            "INSERT IGNORE INTO admin_team_member (team_id, name, email, role, article_count, is_active) VALUES (1, 'Sarah Kabir', 'sarah@origins.bd', 'Senior Editor', 24, 1), (2, 'Rafiq Ahmed', 'rafiq@origins.bd', 'Contributor', 8, 1)"
        )
        cur.execute(
            "INSERT IGNORE INTO admin_coupon (coupon_id, code, discount_type, discount_value, usage_limit, used_count, expires_at, is_new_user_only, is_active) VALUES (1, 'EID26', 'Percentage', 15, NULL, 145, '2026-06-30', 0, 1), (2, 'WELCOME', 'Free Delivery', 0, 1000, 84, NULL, 1, 1)"
        )
        cur.execute(
            "INSERT IGNORE INTO admin_dispute (dispute_id, order_id, issue, priority, status) VALUES (1, NULL, 'Buyer claims product damaged upon arrival.', 'High', 'Open'), (2, NULL, 'Wrong item delivered.', 'Medium', 'Open')"
        )
        try:
            cur.execute(
                """
                INSERT IGNORE INTO admin_qc_item (product_id, seller_id, status, created_at)
                SELECT p.product_id, p.seller_id, 'Pending', p.created_at
                FROM product p
                WHERE COALESCE(p.is_active,0)=0
                LIMIT 25
                """
            )
        except Exception:
            pass
        try:
            cur.execute(
                """
                INSERT IGNORE INTO admin_message_thread (seller_id, subject, last_message)
                SELECT sp.seller_id, CONCAT('Support for ', sp.shop_name), CONCAT('Welcome ', sp.shop_name, '. Your admin thread is ready.')
                FROM seller_profile sp
                LIMIT 25
                """
            )
        except Exception:
            pass
        try:
            cur.execute(
                """
                INSERT IGNORE INTO admin_message (thread_id, sender_role, body)
                SELECT t.thread_id, 'admin', t.last_message
                FROM admin_message_thread t
                """
            )
        except Exception:
            pass
        conn.commit()
    except Exception as e:
        try:
            print("[DB BOOTSTRAP] skipped:", e)
        except Exception:
            pass
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass


# -----------------------
# Navbar Data (Categories / Districts)
# -----------------------
CATEGORIES: Dict[str, List[str]] = {
    "Textile Heritage": [
        "Jamdani",
        "Tangail Weave",
        "Muslin-Inspired Fine Weave",
        "Rajshahi Silk",
        "Handloom Accessories (Stole/Scarf)",
    ],
    "Craft & Folk": [
        "Nakshi Kantha",
        "Shital Pati",
        "Bamboo & Cane",
        "Terracotta",
        "Metal/Brass Craft",
    ],
    "Taste of Bengal": [
        "Aromatic Rice (Kalijira)",
        "Sweets & Desserts",
        "Mango & Seasonal Fruits",
        "Spices",
        "Tea & Honey",
    ],
    "Jute & Earth": [
        "Jute Bags",
        "Home & Lifestyle",
        "Rugs & Mats",
        "Eco Packaging / Gift Wrap",
    ],
    "Leather Works": [
        "Footwear",
        "Bags",
        "Wallets",
        "Belts & Accessories",
    ],
    "Home & Living": [
        "Decor (Wall/Art)",
        "Kitchen & Dining",
        "Bedding",
        "Baskets & Storage",
    ],
}

DISTRICTS = [
    "Bagerhat",
    "Bandarban",
    "Barguna",
    "Barishal",
    "Bhola",
    "Bogura",
    "Brahmanbaria",
    "Chandpur",
    "Chapainawabganj",
    "Chattogram",
    "Chuadanga",
    "Cox's Bazar",
    "Cumilla",
    "Dhaka",
    "Dinajpur",
    "Faridpur",
    "Feni",
    "Gaibandha",
    "Gazipur",
    "Gopalganj",
    "Habiganj",
    "Jamalpur",
    "Jashore",
    "Jhalokathi",
    "Jhenaidah",
    "Joypurhat",
    "Khagrachhari",
    "Khulna",
    "Kishoreganj",
    "Kurigram",
    "Kushtia",
    "Lakshmipur",
    "Lalmonirhat",
    "Madaripur",
    "Magura",
    "Manikganj",
    "Meherpur",
    "Moulvibazar",
    "Munshiganj",
    "Mymensingh",
    "Naogaon",
    "Narail",
    "Narayanganj",
    "Narsingdi",
    "Natore",
    "Netrokona",
    "Nilphamari",
    "Noakhali",
    "Pabna",
    "Panchagarh",
    "Patuakhali",
    "Pirojpur",
    "Rajbari",
    "Rajshahi",
    "Rangamati",
    "Rangpur",
    "Satkhira",
    "Shariatpur",
    "Sherpur",
    "Sirajganj",
    "Sunamganj",
    "Sylhet",
    "Tangail",
    "Thakurgaon",
]

SUPPORTED_CURRENCIES = ("BDT",)


# -----------------------
# Simple in-process cache
# -----------------------
# Keeps the Heritage Map (Atlas) dataset warm.
# If you run multiple workers/instances, each will keep its own cache.
_ATLAS_CACHE: Dict[str, Any] = {"ts": 0.0, "data": None, "etag": None}
_ATLAS_CACHE_TTL_SECONDS = 300  # 5 minutes


# -----------------------
# DB Helpers (mysql-connector)
# -----------------------
def get_db():
import mysql.connector

host = app.config.get("DB_HOST")
user = app.config.get("DB_USER")
password = app.config.get("DB_PASSWORD")
database = app.config.get("DB_NAME")
port = int(app.config.get("DB_PORT") or 4000)

connect_kwargs = dict(
    host=host,
    user=user,
    password=password,
    database=database,
    port=port,
    autocommit=False,
    connection_timeout=10,

    # ✅ VERY IMPORTANT FOR TiDB
    ssl_disabled=False,
)

return mysql.connector.connect(**connect_kwargs)

def _load_atlas_district_names() -> List[str]:
    data_path = FSPath(app.root_path) / "static" / "assets" / "data" / "districts.json"
    try:
        payload = json.loads(data_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    names = []
    seen = set()
    for item in payload or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("zilla") or item.get("name") or "").strip()
        if name and name.lower() not in seen:
            names.append(name)
            seen.add(name.lower())
    return names


def _ensure_atlas_districts_seeded() -> None:
    names = _load_atlas_district_names()
    if not names:
        return
    conn = None
    cur = None
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.executemany("INSERT IGNORE INTO district (name) VALUES (%s)", [(name,) for name in names])
        conn.commit()
    except Exception:
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        try:
            if conn:
                conn.close()
        except Exception:
            pass



def db_fetchall(sql: str, params: Tuple[Any, ...] = ()) -> List[Dict[str, Any]]:
    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params)
        rows = cur.fetchall()
        return rows or []
    finally:
        try:
            conn.close()
        except Exception:
            pass


def db_fetchone(sql: str, params: Tuple[Any, ...] = ()) -> Optional[Dict[str, Any]]:
    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params)
        row = cur.fetchone()
        return row
    finally:
        try:
            conn.close()
        except Exception:
            pass


def db_execute(sql: str, params: Tuple[Any, ...] = (), *, return_lastrowid: bool = False) -> Optional[int]:
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
        return cur.lastrowid if return_lastrowid else None
    except Exception:
        conn.rollback()
        raise
    finally:
        try:
            conn.close()
        except Exception:
            pass




# -----------------------
# Origins Bangladesh ID generation
# Format: OB-[TYPE]-[YYMM]-[XXXX]
# Buyer uses TYPE=UID
# -----------------------
def _yymm_now() -> str:
    return datetime.datetime.now().strftime("%y%m")


def _next_ob_seq(type_code: str, yymm: str, start_seq: int) -> int:
    """Atomic monthly counter using MySQL LAST_INSERT_ID trick.
    Requires table ob_id_sequence(type_code, yymm, last_seq) with PK(type_code,yymm).
    """
    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """
            INSERT INTO ob_id_sequence (type_code, yymm, last_seq)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE last_seq = LAST_INSERT_ID(last_seq + 1)
            """,
            (type_code, yymm, start_seq),
        )
        cur.execute("SELECT LAST_INSERT_ID() AS seq")
        row = cur.fetchone() or {}
        conn.commit()
        return int(row.get("seq") or start_seq)
    except Exception:
        conn.rollback()
        raise
    finally:
        try:
            conn.close()
        except Exception:
            pass


def format_prefixed_id(prefix: str, value: Any, width: int = 6) -> str:
    raw = str(value or '').strip()
    if not raw:
        return f"{prefix}-{'0'*width}"
    m = re.fullmatch(rf"{re.escape(prefix)}-(\d+)", raw, flags=re.IGNORECASE)
    if m:
        return f"{prefix}-{int(m.group(1)):0{width}d}"
    if raw.isdigit():
        return f"{prefix}-{int(raw):0{width}d}"
    digits = ''.join(ch for ch in raw if ch.isdigit())
    if digits:
        return f"{prefix}-{int(digits):0{width}d}"
    return raw if raw.upper().startswith(prefix + '-') else f"{prefix}-{raw}"


def normalize_guardian_id(value: Any, fallback_numeric: Any = None) -> str:
    raw = str(value or '').strip()
    if not raw:
        return format_prefixed_id('OB', fallback_numeric or 0, 4) if fallback_numeric is not None else ''
    if raw.upper().startswith('GV-'):
        return format_prefixed_id('OB', raw[3:], 4)
    m = re.fullmatch(r'OB-(\d+)', raw, flags=re.IGNORECASE)
    if m:
        return format_prefixed_id('OB', m.group(1), 4)
    return raw


def format_order_id(value: Any) -> str:
    return format_prefixed_id('ORD', value, 6)


def format_trx_id(value: Any) -> str:
    return format_prefixed_id('TRX', value, 6)


def next_global_prefixed_id(prefix: str, type_code: str, start_seq: int = 1) -> str:
    seq = _next_ob_seq(type_code, 'global', start_seq)
    return format_prefixed_id(prefix, seq, 6)


def get_or_create_guardian_id(buyer_id: int) -> str:
    """Returns persistent guardian_id for buyer (OB-UID-YYMM-XXXX)."""
    # If buyer_profile exists and has guardian_id, return it
    try:
        prow = db_fetchone(
            "SELECT guardian_id FROM buyer_profile WHERE buyer_id=%s LIMIT 1",
            (buyer_id,),
        ) or {}
        if prow.get("guardian_id"):
            gid = normalize_guardian_id(prow["guardian_id"], buyer_id)
            if gid != str(prow["guardian_id"]):
                try:
                    db_execute("UPDATE buyer_profile SET guardian_id=%s WHERE buyer_id=%s", (gid, buyer_id))
                except Exception:
                    pass
            return gid
    except Exception:
        # Migration not run yet
        return ""

    yymm = _yymm_now()
    type_code = "UID"
    start_seq = 8901  # first issued becomes 8901 (or 8902 depending on existing row)
    try:
        seq = _next_ob_seq(type_code, yymm, start_seq)
        gid = f"OB-{type_code}-{yymm}-{seq:04d}"

        # Ensure profile row exists
        existing = db_fetchone("SELECT buyer_id FROM buyer_profile WHERE buyer_id=%s LIMIT 1", (buyer_id,))
        if not existing:
            db_execute("INSERT INTO buyer_profile (buyer_id, guardian_id) VALUES (%s, %s)", (buyer_id, gid))
        else:
            db_execute("UPDATE buyer_profile SET guardian_id=%s WHERE buyer_id=%s", (gid, buyer_id))
        return gid
    except Exception:
        return ""

# -----------------------
# Auth Helpers
# -----------------------
def current_user_id() -> Optional[int]:
    uid = session.get("user_id")
    return int(uid) if uid is not None else None


def current_role() -> str:
    return session.get("role", "guest")



def current_user_() -> bool:
    uid = current_user_id()
    if not uid:
        return False
    row = db_fetchone("SELECT  FROM user_account WHERE user_id=%s", (uid,))
    return bool(row and row.get(""))


def require_login():
    if not current_user_id():
        flash("Please login first.", "warning")
        return redirect(url_for("login", next=request.path))
    return None


def require_buyer():
    if not current_user_id():
        flash("Please login first.", "warning")
        return redirect(url_for("login", next=request.path))
    if current_role() != "buyer":
        flash("This page is for buyers.", "warning")
        return redirect(url_for("home"))
    return None




def require_role(*roles: str):
    if not current_user_id():
        flash("Please login first.", "warning")
        return redirect(url_for("login", next=request.path))
    if roles and current_role() not in roles:
        flash("You don't have access to that page.", "warning")
        return redirect(url_for("home"))
    return None


def _sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _create_action_approval(*, actor_id: int, action_key: str, target_id: Optional[int]) -> str:
    """Create an approval code (returned raw) and store its hash."""
    code = f"{secrets.randbelow(1000000):06d}"
    salt = secrets.token_hex(8)
    secret = app.config.get("SECRET_KEY", "")
    code_hash = _sha256_hex(code + salt + secret)
    ttl = int(get_setting("approval_code_ttl_minutes", "10") or 10)
    expires = datetime.datetime.utcnow() + datetime.timedelta(minutes=max(2, min(60, ttl)))
    db_execute(
        "INSERT INTO action_approval(actor_user_id, action_key, target_user_id, code_hash, salt, expires_at) VALUES (%s,%s,%s,%s,%s,%s)",
        (actor_id, action_key, target_id, code_hash, salt, expires),
    )
    return code


def _consume_action_approval(*, actor_id: int, action_key: str, target_id: Optional[int], code: str) -> bool:
    try:
        row = db_fetchone(
            """
            SELECT approval_id, salt
            FROM action_approval
            WHERE actor_user_id=%s AND action_key=%s AND target_user_id %s
              AND consumed_at IS NULL AND expires_at > UTC_TIMESTAMP()
            ORDER BY approval_id DESC
            LIMIT 1
            """ % ("= %s" if target_id is not None else "IS NULL"),
            (actor_id, action_key, *( [target_id] if target_id is not None else [] )),
        )
        if not row:
            return False
        salt = str(row.get("salt") or "")
        secret = app.config.get("SECRET_KEY", "")
        code_hash = _sha256_hex(code + salt + secret)
        ok = db_fetchone(
            "SELECT approval_id FROM action_approval WHERE approval_id=%s AND code_hash=%s AND consumed_at IS NULL",
            (int(row["approval_id"]), code_hash),
        )
        if not ok:
            return False
        db_execute("UPDATE action_approval SET consumed_at=UTC_TIMESTAMP() WHERE approval_id=%s", (int(row["approval_id"]),))
        return True
    except Exception:
        return False


def _base_url() -> str:
    base = (app.config.get("BASE_URL") or "").strip()
    if base:
        return base.rstrip("/") + "/"
    try:
        return request.host_url
    except Exception:
        return "http://localhost:5000/"


def _smtp_value(key: str, fallback: Any) -> Any:
    v = get_setting(key, "")
    return v if v not in ("", None) else fallback


def send_email(to_email: str, subject: str, *, text: str, html: str = "") -> None:
    # Prefer DB settings (system_setting) if set, fallback to env/config.py
    host = _smtp_value("smtp_host", app.config.get("SMTP_HOST"))
    port = int(_smtp_value("smtp_port", app.config.get("SMTP_PORT") or 587) or 587)
    user = _smtp_value("smtp_user", app.config.get("SMTP_USER"))
    pwd = _smtp_value("smtp_pass", app.config.get("SMTP_PASS"))
    from_email = _smtp_value("smtp_from", app.config.get("SMTP_FROM")) or user
    from_name = (app.config.get("SMTP_FROM_NAME") or "").strip()

    if not user or not pwd or not host:
        print("[EMAIL NOT SENT] Configure SMTP in system_setting or .env")
        print("To:", to_email)
        print("Subject:", subject)
        print(text)
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{from_email}>" if from_name else from_email
    msg["To"] = to_email
    msg.set_content(text)
    if html:
        msg.add_alternative(html, subtype="html")

    with smtplib.SMTP(host, port) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.login(user, pwd)
        smtp.send_message(msg)


def render_email(template_name: str, **context: Any) -> str:
    """Render an HTML email template from templates/emails."""
    return render_template(f"emails/{template_name}", **context)


def _email_branding_context() -> Dict[str, str]:
    return {
        "email_footer_note": get_setting("email_footer_note", ""),
        "email_signature_name": get_setting("email_signature_name", ""),
        "email_signature_title": get_setting("email_signature_title", ""),
    }


def render_email_with_overrides(template_key: str, *, fallback_template: str, **context: Any) -> Tuple[str, str]:
    """
    Returns (subject_override, html) where subject_override may be empty.
    If an override exists in email_template table, that HTML will be used.
    """
    ctx = {**context, **_email_branding_context()}
    row = db_fetchone(
        "SELECT subject_override, html_override FROM email_template WHERE template_key=%s",
        (template_key,),
    )
    subj = str((row or {}).get("subject_override") or "")
    html_override = (row or {}).get("html_override")
    if html_override:
        # Allow Jinja rendering inside the override
        try:
            html = render_template_string(str(html_override), **ctx)  # type: ignore
        except Exception:
            html = str(html_override)
        return subj, html
    return subj, render_email(fallback_template, **ctx)




def render_email_bundle(template_key: str, *, fallback_template: str, default_subject: str, default_text: str, **context: Any) -> Tuple[str, str, str]:
    """Return (subject, text, html) allowing DB overrides for subject/html/text."""
    ctx = {**context, **_email_branding_context()}
    row = db_fetchone(
        "SELECT subject_override, html_override, text_override FROM email_template WHERE template_key=%s",
        (template_key,),
    )
    subj = str((row or {}).get("subject_override") or "").strip() or default_subject
    html_override = (row or {}).get("html_override")
    text_override = (row or {}).get("text_override")

    def _render_maybe(s: str) -> str:
        try:
            return render_template_string(s, **ctx)  # type: ignore
        except Exception:
            return s

    if html_override:
        html = _render_maybe(str(html_override))
    else:
        html = render_email(fallback_template, **ctx)

    txt = default_text
    if text_override:
        txt = _render_maybe(str(text_override))

    return subj, txt, html

def _alerts_enabled() -> bool:
    return get_setting("alerts_enabled", "1") == "1"


def get_active_new_user_coupon(*, discount_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
    row = db_fetchone(
        """
        SELECT coupon_id, code, discount_type, discount_value, usage_limit, used_count, expires_at
        FROM admin_coupon
        WHERE is_active=TRUE
          AND is_new_user_only=TRUE
          AND (%s IS NULL OR discount_type=%s)
          AND (expires_at IS NULL OR expires_at >= CURDATE())
          AND (usage_limit IS NULL OR used_count < usage_limit)
        ORDER BY created_at DESC, coupon_id DESC
        LIMIT 1
        """,
        (discount_type, discount_type),
    )
    return row or None


@app.post("/newsletter/subscribe")
def newsletter_subscribe():
    email = (request.form.get("email") or "").strip().lower()
    redir = request.form.get("next") or request.referrer or url_for("home")

    if not email:
        flash("Please enter your email address.", "warning")
        return redirect(redir)

    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        flash("Please enter a valid email address.", "warning")
        return redirect(redir)

    existing = db_fetchone("SELECT subscriber_id, is_active FROM newsletter_subscriber WHERE email=%s", (email,))
    if existing:
        if bool(existing.get("is_active", True)):
            flash("This email is already subscribed.", "info")
            return redirect(redir)
        db_execute("UPDATE newsletter_subscriber SET is_active=TRUE WHERE subscriber_id=%s", (existing["subscriber_id"],))
    else:
        db_execute("INSERT INTO newsletter_subscriber(email, is_active) VALUES (%s, TRUE)", (email,))

    try:
        html = render_email("newsletter_subscribed.html", name=email.split("@")[0].replace(".", " ").title() or "Heritage Friend")
        send_email(email, "Welcome to the Heritage Circle", text="Thanks for subscribing to Origins Bangladesh updates.", html=html)
    except Exception as exc:
        print("Newsletter confirmation email failed:", exc)

    flash("Subscription successful. Please check your email.", "success")
    return redirect(redir)


def _alert_recipient_email() -> str:
    # Prefer explicit setting, else current superadmin's email, else fallback empty
    explicit = (get_setting("alert_recipient_email", "") or "").strip()
    if explicit:
        return explicit
    try:
        me = current_user_id()
        if me:
            row = db_fetchone("SELECT email FROM user_account WHERE user_id=%s", (me,))
            return str((row or {}).get("email") or "")
    except Exception:
        pass
    return ""


def log_security_event(
    event_type: str,
    *,
    severity: str = "info",
    actor_email: str = "",
    message: str = "",
    meta: Optional[Dict[str, Any]] = None,
) -> None:
    try:
        ip = (request.headers.get("X-Forwarded-For") or request.remote_addr or "")[:64]
        ua = (request.headers.get("User-Agent") or "")[:255]
        db_execute(
            """
            INSERT INTO security_event(event_type, severity, actor_email, ip, user_agent, message, meta_json)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            """,
            (event_type, severity, actor_email or None, ip or None, ua or None, message or None, json.dumps(meta or {}, ensure_ascii=False)),
        )
    except Exception:
        return


def maybe_send_failed_login_alert(*, actor_email: str) -> None:
    if not _alerts_enabled():
        return
    try:
        threshold = int(get_setting("alert_failed_login_threshold", "5") or 5)
        window_min = int(get_setting("alert_failed_login_window_minutes", "15") or 15)
        ip = (request.headers.get("X-Forwarded-For") or request.remote_addr or "")[:64]
        row = db_fetchone(
            """
            SELECT COUNT(*) AS c
            FROM security_event
            WHERE event_type='failed_login'
              AND (ip=%s OR actor_email=%s)
              AND created_at >= (UTC_TIMESTAMP() - INTERVAL %s MINUTE)
            """,
            (ip, actor_email, window_min),
        )
        c = int((row or {}).get("c") or 0)
        if c < threshold:
            return

        to_email = _alert_recipient_email()
        if not to_email:
            return

        # Throttle: don't spam - one alert per window per ip
        throttle = db_fetchone(
            """
            SELECT COUNT(*) AS c
            FROM security_event
            WHERE event_type='failed_login_alert_sent'
              AND ip=%s
              AND created_at >= (UTC_TIMESTAMP() - INTERVAL %s MINUTE)
            """,
            (ip, window_min),
        )
        if int((throttle or {}).get("c") or 0) > 0:
            return

        subject = f"Security alert: {c} failed login attempts"
        _, html = render_email_with_overrides(
            "security_alert",
            fallback_template="security_alert.html",
            title="Security Alert",
            preheader="Unusual sign-in activity detected",
            actor_email=actor_email,
            ip=ip,
            count=c,
            window_minutes=window_min,
            when_utc=f"{datetime.datetime.utcnow().isoformat()}Z",
        )
        send_email(to_email, subject, text=f"{c} failed login attempts detected for {actor_email or 'unknown'} (IP: {ip})", html=html)
        log_security_event("failed_login_alert_sent", severity="warn", actor_email=actor_email, message="alert_sent", meta={"count": c, "window_minutes": window_min})
    except Exception:
        return


def ensure_new_user_coupon(*, buyer_id: int, buyer_name: str = '') -> str:
    code = f"WELCOME{int(buyer_id):04d}"
    try:
        exists = db_fetchone("SELECT coupon_id, code FROM admin_coupon WHERE code=%s LIMIT 1", (code,)) or {}
        if not exists:
            db_execute(
                """
                INSERT INTO admin_coupon
                (code, discount_type, discount_value, usage_limit, used_count, expires_at, is_new_user_only, minimum_subtotal_bdt, maximum_discount_bdt, starts_at, per_user_limit, applicable_scope, is_active)
                VALUES (%s,'Percentage',10,1,0,DATE_ADD(CURDATE(), INTERVAL 30 DAY),TRUE,0,500,CURRENT_TIMESTAMP,1,'all',TRUE)
                """,
                (code,),
            )
    except Exception:
        pass
    return code


def send_buyer_welcome_email(*, email: str, name: str, buyer_id: int) -> None:
    member_id = format_member_id('buyer', buyer_id)
    coupon_code = ensure_new_user_coupon(buyer_id=buyer_id, buyer_name=name)
    html = render_email('buyer_welcome.html', name=name or 'Buyer', member_id=member_id, coupon_code=coupon_code)
    text = (
        f"Welcome to Origins Bangladesh!\n"
        f"Your Buyer ID: {member_id}\n"
        f"New user coupon code: {coupon_code}\n"
    )
    send_email(email, 'Welcome to Origins Bangladesh', text=text, html=html)


def send_seller_welcome_email(*, email: str, name: str, seller_id: int) -> None:
    member_id = format_member_id('seller', seller_id)
    html = render_email('seller_onboarding.html', name=name or 'Seller', member_id=member_id)
    text = (
        f"Welcome to Origins Bangladesh!\n"
        f"Your Seller ID: {member_id}\n"
        "Please submit your documents for verification.\n"
    )
    send_email(email, 'Seller onboarding: documents required', text=text, html=html)


def _send_simple_status_email(*, to_email: str, subject: str, headline: str, lines: List[str]) -> None:
    try:
        body_html = ''.join(f'<p style="margin:0 0 12px">{Markup.escape(line)}</p>' for line in lines if line)
        html = render_email('generic_status.html', title=headline, preheader=subject, body_html=Markup(body_html))
        text = "\n".join([headline] + [line for line in lines if line]) + "\n"
        send_email(to_email, subject, text=text, html=html)
    except Exception:
        pass


def send_order_status_email(order_id: int, status: str, note: str = '') -> None:
    try:
        row = db_fetchone(
            "SELECT o.order_id, o.buyer_id, o.shipping_email, u.email, u.name, u.public_id FROM `order` o JOIN user_account u ON u.user_id=o.buyer_id WHERE o.order_id=%s LIMIT 1",
            (order_id,),
        ) or {}
        to_email = str(row.get('shipping_email') or row.get('email') or '').strip()
        if not to_email:
            return
        buyer_public_id = str(row.get('public_id') or format_member_id('buyer', int(row.get('buyer_id') or 0)))
        status_key = str(status or '').strip().lower()
        label_map = {
            'pending': 'Order confirmed',
            'paid': 'Order confirmed',
            'accepted': 'Order accepted',
            'processing': 'Order packed',
            'ready_to_ship': 'Order packed',
            'shipped': 'Order shipped',
            'delivered': 'Order delivered',
            'cancelled': 'Order cancelled',
        }
        headline = label_map.get(status_key, 'Order update')
        subject = f"{headline} — {format_order_id(order_id)}"
        lines = [
            f"Hello {row.get('name') or 'Buyer'},",
            f"Buyer ID: {buyer_public_id}",
            f"Order ID: {format_order_id(order_id)}",
            f"Current status: {headline}",
        ]
        if note:
            lines.append(note)
        _send_simple_status_email(to_email=to_email, subject=subject, headline=headline, lines=lines)
    except Exception:
        pass


def send_user_access_email(user_id: int, is_active: bool, reason: str = '') -> None:
    try:
        row = db_fetchone("SELECT user_id, role, name, email, public_id FROM user_account WHERE user_id=%s LIMIT 1", (user_id,)) or {}
        to_email = str(row.get('email') or '').strip()
        if not to_email:
            return
        role = str(row.get('role') or 'user').lower()
        role_label = 'Buyer' if role == 'buyer' else ('Seller' if role == 'seller' else role.title())
        public_id = str(row.get('public_id') or format_member_id(role, int(row.get('user_id') or 0)))
        state = 're-activated' if is_active else 'suspended'
        subject = f"{role_label} account {state} — Origins Bangladesh"
        headline = f"{role_label} account {state}"
        lines = [
            f"Hello {row.get('name') or role_label},",
            f"{role_label} ID: {public_id}",
            f"Your account has been {state}.",
        ]
        if reason:
            lines.append(f"Reason: {reason}")
        _send_simple_status_email(to_email=to_email, subject=subject, headline=headline, lines=lines)
    except Exception:
        pass


def send_seller_verification_email(seller_id: int, approved: bool, note: str = '') -> None:
    try:
        row = db_fetchone(
            "SELECT u.user_id, u.email, u.name, u.public_id, sp.shop_name FROM user_account u LEFT JOIN seller_profile sp ON sp.seller_id=u.user_id WHERE u.user_id=%s LIMIT 1",
            (seller_id,),
        ) or {}
        to_email = str(row.get('email') or '').strip()
        if not to_email:
            return
        seller_public_id = str(row.get('public_id') or format_member_id('seller', int(row.get('user_id') or seller_id)))
        headline = 'Seller documents approved' if approved else 'Seller verification update'
        subject = f"{headline} — Origins Bangladesh"
        lines = [
            f"Hello {row.get('name') or row.get('shop_name') or 'Seller'},",
            f"Seller ID: {seller_public_id}",
            ('Your seller documents have been approved.' if approved else 'Your seller verification status was updated.'),
        ]
        if note:
            lines.append(note)
        _send_simple_status_email(to_email=to_email, subject=subject, headline=headline, lines=lines)
    except Exception:
        pass


def maybe_send_payout_spike_alert(*, seller_id: int, amount_bdt: Decimal, trx_id: str) -> None:
    if not _alerts_enabled():
        return
    try:
        multiplier = Decimal(str(get_setting("alert_payout_spike_multiplier", "3") or "3"))
        min_bdt = Decimal(str(get_setting("alert_payout_spike_min_bdt", "5000") or "5000"))

        # Baseline: average of last 30 days for the seller
        row = db_fetchone(
            """
            SELECT AVG(amount_bdt) AS avg_amt
            FROM payout_request
            WHERE seller_user_id=%s AND requested_at >= (UTC_TIMESTAMP() - INTERVAL 30 DAY)
            """,
            (seller_id,),
        )
        avg_amt = Decimal(str((row or {}).get("avg_amt") or "0"))
        trigger_amt = max(min_bdt, (avg_amt * multiplier if avg_amt > 0 else min_bdt))
        if amount_bdt < trigger_amt:
            return

        to_email = _alert_recipient_email()
        if not to_email:
            return

        subject = "Finance alert: payout spike detected"
        _, html = render_email_with_overrides(
            "payout_spike_alert",
            fallback_template="payout_spike_alert.html",
            title="Finance Alert",
            preheader="Unusual payout request amount detected",
            seller_id=seller_id,
            trx_id=trx_id,
            amount_bdt=f"{amount_bdt:.2f}",
            avg_bdt=f"{avg_amt:.2f}",
            threshold_bdt=f"{trigger_amt:.2f}",
            when_utc=f"{datetime.datetime.utcnow().isoformat()}Z",
        )
        send_email(to_email, subject, text=f"Payout spike: TRX {trx_id} amount {amount_bdt} (avg {avg_amt})", html=html)
        log_security_event("payout_spike", severity="warn", actor_email="", message="payout_spike", meta={"seller_id": seller_id, "trx_id": trx_id, "amount": str(amount_bdt), "avg": str(avg_amt), "threshold": str(trigger_amt)})
    except Exception:
        return


def get_setting(key: str, default: str = "") -> str:
    row = db_fetchone("SELECT setting_value FROM system_setting WHERE setting_key=%s", (key,))
    if not row:
        return default
    return str(row.get("setting_value") or default)


def set_setting(key: str, value: str) -> None:
    db_execute(
        "INSERT INTO system_setting (setting_key, setting_value) VALUES (%s,%s) "
        "ON DUPLICATE KEY UPDATE setting_value=VALUES(setting_value)",
        (key, value),
    )


def audit_log(action: str, *, target_user_id: Optional[int] = None, metadata: Optional[Dict[str, Any]] = None) -> None:
    try:
        actor = current_user_id()
        if not actor:
            return
        ip = (request.headers.get("X-Forwarded-For") or request.remote_addr or "")[:64]
        ua = (request.headers.get("User-Agent") or "")[:255]
        meta_json = json.dumps(metadata or {}, ensure_ascii=False)
        db_execute(
            """
            INSERT INTO audit_log (actor_user_id, action, target_user_id, ip, user_agent, metadata_json)
            VALUES (%s,%s,%s,%s,%s,%s)
            """,
            (actor, action, target_user_id, ip, ua, meta_json),
        )
    except Exception:
        # never block user flows
        return


def create_notification(
    *,
    recipient_user_id: int,
    type: str,
    title: str,
    body: str = "",
    link: str = "",
    severity: str = "info",
    meta: Optional[Dict[str, Any]] = None,
) -> None:
    """Create an in-app notification (DB-backed). Never blocks request flow."""
    try:
        if not recipient_user_id:
            return
        sev = (severity or "info").lower()
        if sev not in ("info", "warn", "error", "success"):
            sev = "info"
        db_execute(
            """
            INSERT INTO notification (recipient_user_id, type, severity, title, body, link, meta_json)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                int(recipient_user_id),
                (type or "event")[:40],
                sev,
                (title or "")[:180],
                (body or "")[:255],
                (link or "")[:255],
                json.dumps(meta or {}, ensure_ascii=False),
            ),
        )
    except Exception:
        return


def notify_current_superadmin(*, type: str, title: str, body: str = "", link: str = "", severity: str = "info", meta: Optional[Dict[str, Any]] = None) -> None:
    try:
        uid = int(current_user_id() or 0)
        if uid:
            create_notification(recipient_user_id=uid, type=type, title=title, body=body, link=link, severity=severity, meta=meta)
    except Exception:
        return


def _extract_public_seq(public_id: str, width: int = 4) -> str:
    parts = str(public_id or '').strip().split('-')
    if not parts:
        return '0' * width
    raw = parts[-1]
    digits = ''.join(ch for ch in raw if ch.isdigit())
    if not digits:
        return '0' * width
    return digits.zfill(width)


def _public_id_template(role: str) -> Tuple[str, int]:
    role = (role or '').strip().lower()
    if role == 'seller':
        return 'SLR', 4
    if role == 'admin':
        return 'ADMIN', 4
    if role == 'superadmin':
        return 'OWNER', 2
    return 'USR', 4


def _build_public_id(role: str, yymm: str, seq: int) -> str:
    code, width = _public_id_template(role)
    return f"OB-{code}-{yymm}-{seq:0{width}d}"


def issue_public_id(role: str, user_id: Optional[int] = None, existing_value: Any = None) -> str:
    role = (role or '').strip().lower() or 'buyer'
    if existing_value:
        raw = str(existing_value).strip()
        if raw.upper().startswith('OB-'):
            return raw
    yymm = _yymm_now()
    type_code, width = _public_id_template(role)
    seq = _next_ob_seq(type_code, yymm, 1)
    public_id = _build_public_id(role, yymm, seq)
    if user_id:
        try:
            db_execute("UPDATE user_account SET public_id=%s WHERE user_id=%s", (public_id, int(user_id)))
        except Exception:
            pass
    return public_id


def get_public_user_id(user_id: Optional[int], role: str = '', existing_value: Any = None) -> str:
    uid = int(user_id or 0)
    row = None
    if uid > 0 and (not role or not existing_value):
        try:
            row = db_fetchone("SELECT role, public_id FROM user_account WHERE user_id=%s LIMIT 1", (uid,)) or {}
        except Exception:
            row = {}
    resolved_role = (role or ((row or {}).get('role') or '')).lower() or 'buyer'
    public_id = existing_value or ((row or {}).get('public_id') if row else None)
    if public_id:
        return str(public_id)
    return issue_public_id(resolved_role, uid or None, public_id)


def format_member_id(role: str, user_id: int) -> str:
    return get_public_user_id(user_id, role=role)


def send_otp_email(*, email: str, purpose: str, otp: str) -> None:
    # purpose: login, verify, reset, admin_login, superadmin_login
    title_map = {
        "login": "Confirm your sign-in",
        "admin_login": "Confirm your admin sign-in",
        "superadmin_login": "Confirm your super admin sign-in",
        "verify": "Verify your email address",
        "reset": "Reset your password",
    }
    subject_map = {
        "login": "Your Origins Bangladesh login code",
        "admin_login": "Your Origins Bangladesh admin login code",
        "superadmin_login": "Your Origins Bangladesh super admin login code",
        "verify": "Verify your Origins Bangladesh account",
        "reset": "Reset your Origins Bangladesh password",
    }
    html = render_email(
        "otp_verification.html",
        title=title_map.get(purpose, "Your verification code"),
        preheader="Your one-time code",
        otp=otp,
        expires_minutes=10,
    )
    send_email(
        email,
        subject_map.get(purpose, "Your Origins Bangladesh code"),
        text=f"Your one-time code is: {otp}\n\nThis code expires in 10 minutes.\n",
        html=html,
    )


def _client_ip() -> str:
    xff = request.headers.get("X-Forwarded-For", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.remote_addr or ""


def _client_ua() -> str:
    return (request.user_agent.string or "")[:250]


def _get_device_cookie() -> str:
    return (request.cookies.get("ob_device") or "").strip()


def _device_hash(device_token: str) -> str:
    secret = app.config.get("SECRET_KEY", "")
    return _sha256_hex(device_token + secret)


def _create_or_refresh_trusted_device(*, user_id: int, device_token: str, label: str = "") -> str:
    """Create/refresh a trusted device entry. Returns revoke token (raw)."""
    dh = _device_hash(device_token)
    revoke_raw = secrets.token_urlsafe(32)
    revoke_hash = _device_hash(revoke_raw)
    expires = datetime.datetime.utcnow() + datetime.timedelta(days=30)

    existing = db_fetchone(
        "SELECT device_id FROM trusted_device WHERE user_id=%s AND device_hash=%s AND revoked_at IS NULL",
        (user_id, dh),
    )
    if existing:
        db_execute(
            "UPDATE trusted_device SET last_seen_at=UTC_TIMESTAMP(), expires_at=%s, revoke_hash=%s, label=%s, ip=%s, user_agent=%s WHERE device_id=%s",
            (expires, revoke_hash, label or None, _client_ip() or None, _client_ua() or None, int(existing["device_id"])),
        )
    else:
        db_execute(
            """
            INSERT INTO trusted_device(user_id, device_hash, revoke_hash, label, ip, user_agent, expires_at, last_seen_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,UTC_TIMESTAMP())
            """,
            (user_id, dh, revoke_hash, label or None, _client_ip() or None, _client_ua() or None, expires),
        )
    return revoke_raw


def _is_known_device(*, user_id: int, device_token: str) -> bool:
    if not device_token:
        return False
    dh = _device_hash(device_token)
    row = db_fetchone(
        """
        SELECT device_id
        FROM trusted_device
        WHERE user_id=%s AND device_hash=%s AND revoked_at IS NULL AND expires_at > UTC_TIMESTAMP()
        """,
        (user_id, dh),
    )
    if row:
        db_execute("UPDATE trusted_device SET last_seen_at=UTC_TIMESTAMP() WHERE device_id=%s", (int(row["device_id"]),))
        return True
    return False


def create_auth_challenge(*, email: str, purpose: str, user_id: Optional[int]) -> Tuple[str, str]:
    email = email.strip().lower()
    otp = f"{secrets.randbelow(1000000):06d}"
    token = secrets.token_urlsafe(32)
    salt = secrets.token_hex(8)
    secret = app.config.get("SECRET_KEY", "")

    code_hash = _sha256_hex(otp + salt + secret)
    token_hash = _sha256_hex(token + salt + secret)
    expires = datetime.datetime.utcnow() + datetime.timedelta(minutes=10)

    db_execute(
        "INSERT INTO auth_token(email, user_id, purpose, code_hash, token_hash, salt, expires_at) VALUES (%s,%s,%s,%s,%s,%s,%s)",
        (email, user_id, purpose, code_hash, token_hash, salt, expires),
    )
    return otp, token


def consume_auth_challenge(*, email: str, purpose: str, otp: Optional[str] = None, token: Optional[str] = None) -> Optional[Dict[str, Any]]:
    email = (email or "").strip().lower()
    row = db_fetchone(
        """
        SELECT token_id, email, user_id, purpose, code_hash, token_hash, salt, expires_at, consumed_at
        FROM auth_token
        WHERE email=%s AND purpose=%s AND consumed_at IS NULL
        ORDER BY token_id DESC
        LIMIT 1
        """,
        (email, purpose),
    )
    if not row:
        return None

    try:
        if row["expires_at"] and row["expires_at"] < datetime.datetime.utcnow():
            return None
    except Exception:
        pass

    salt = row["salt"]
    secret = app.config.get("SECRET_KEY", "")
    ok = False
    if otp:
        ok = _sha256_hex(otp.strip() + salt + secret) == row["code_hash"]
    if token:
        ok = _sha256_hex(token.strip() + salt + secret) == row["token_hash"]

    if not ok:
        return None

    db_execute("UPDATE auth_token SET consumed_at=UTC_TIMESTAMP() WHERE token_id=%s", (row["token_id"],))
    return row


def verify_secret_code(*, user: Dict[str, Any], provided: str, role: str) -> bool:
    """Verify admin/superadmin secret code.

    Priority:
    1) If user.secret_code_hash exists -> verify hash
    2) Fallback to env defaults (Config.ADMIN_SECRET_CODE / Config.SUPERADMIN_SECRET_CODE)
    """
    provided = (provided or "").strip()
    if not provided:
        return False

    stored = (user.get("secret_code_hash") or "").strip()
    if stored:
        try:
            return check_password_hash(stored, provided)
        except Exception:
            return False

    if role == "superadmin":
        return provided == (app.config.get("SUPERADMIN_SECRET_CODE") or "")
    if role == "admin":
        fallback = (app.config.get("ADMIN_SECRET_CODE") or "").strip()
        return bool(fallback) and provided == fallback
    return False




@app.before_request
def _bootstrap_db():
    _bootstrap_db_once()
    return None




@app.before_request
def _enforce_access_blocks():
    # Block requests by IP or by logged-in user id if present.
    try:
        path = request.path or ""
        if path.startswith("/static"):
            return None
        ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or request.remote_addr or ""
        user_id = session.get("user_id")
        # If there is no DB yet, skip gracefully.
        if ip:
            row = db_fetchone(
                "SELECT block_id FROM access_block WHERE is_active=1 AND block_type='ip' AND block_value=%s LIMIT 1",
                (ip,),
            )
            if row:
                return abort(403)
        if user_id:
            row = db_fetchone(
                "SELECT block_id FROM access_block WHERE is_active=1 AND block_type='user' AND block_value=%s LIMIT 1",
                (str(int(user_id)),),
            )
            if row:
                return abort(403)
    except Exception:
        return None
    return None


# -----------------------
# Finance helpers
# -----------------------
def _finance_settled_bdt() -> Decimal:
    """Settled sales in BDT from paid/shipped/delivered orders."""
    row = db_fetchone(
        """
        SELECT COALESCE(SUM(CASE WHEN status IN ('paid','shipped','delivered') THEN total_bdt ELSE 0 END),0) AS settled_bdt
        FROM `order`
        """
    )
    return Decimal(str(row.get("settled_bdt") or "0"))

@app.before_request
def _protect_dashboards():
    path = request.path or ""
    if path.startswith("/buyer"):
        r = require_role("buyer")
        if r:
            return r
    if path.startswith("/seller"):
        r = require_role("seller")
        if r:
            return r
    if path.startswith("/admin"):
        r = require_role("admin")
        if r:
            return r
    if path.startswith("/super-admin"):
        r = require_role("superadmin")
        if r:
            return r
    return None


# -----------------------
# Currency Helpers
# -----------------------
def get_currency() -> str:
    # Platform-wide currency is fixed to Bangladeshi Taka.
    session["currency"] = "BDT"
    return "BDT"


def money_round(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def get_rate_to_bdt(code: str) -> Decimal:
    """Return how many BDT equals 1 unit of currency code."""
    row = db_fetchone("SELECT rate_to_bdt FROM currency_rate WHERE code=%s", (code,))
    if not row:
        # safe fallback: assume 1 for BDT and 120 for USD
        return Decimal("1.0") if code == "BDT" else Decimal("120.0")
    return Decimal(str(row["rate_to_bdt"]))


def convert_from_bdt(amount_bdt: Decimal, to_code: str) -> Decimal:
    if to_code == "BDT":
        return money_round(amount_bdt)
    rate_to_bdt = get_rate_to_bdt(to_code)  # BDT per 1 unit
    if rate_to_bdt == 0:
        return money_round(amount_bdt)
    # amount in to_code = BDT / (BDT per 1 unit)
    return money_round(amount_bdt / rate_to_bdt)


def fmt_money(amount_bdt: Decimal) -> str:
    code = get_currency()
    symbol = "৳" if code == "BDT" else "$"
    shown = convert_from_bdt(amount_bdt, code)
    return f"{symbol}{shown:,.2f}"


# -----------------------
# Home Page Data (Flash Sale / Discovery Engine)
# -----------------------
def sync_artisan_hour_runtime() -> Dict[str, Any]:
    """Normalize live artisan/flash-sale runtime and auto-expire when duration finishes."""
    live = get_setting("artisan_hour_live", "0") == "1"
    duration_seconds = int(get_setting("artisan_hour_duration_seconds", "0") or 0)
    live_started_at_raw = (get_setting("artisan_hour_live_started_at", "") or "").strip()
    live_started_at = None

    if live_started_at_raw:
        try:
            live_started_at = datetime.datetime.fromisoformat(live_started_at_raw)
        except Exception:
            live_started_at = None

    if live and duration_seconds > 0 and live_started_at is None:
        live_started_at = datetime.datetime.now().replace(microsecond=0)
        live_started_at_raw = live_started_at.isoformat()
        set_setting("artisan_hour_live_started_at", live_started_at_raw)

    remaining_seconds = duration_seconds
    expired = False
    now = datetime.datetime.now()
    if live and duration_seconds > 0 and live_started_at is not None:
        elapsed_seconds = max(0, int((now - live_started_at).total_seconds()))
        remaining_seconds = max(0, duration_seconds - elapsed_seconds)
        if remaining_seconds <= 0:
            expired = True
            live = False
            set_setting("artisan_hour_live", "0")
            set_setting("artisan_hour_live_started_at", "")
            live_started_at_raw = ""
            audit_log("artisan_hour_auto_expired", metadata={"duration_seconds": duration_seconds})

    return {
        "live": live,
        "duration_seconds": duration_seconds,
        "remaining_seconds": max(0, remaining_seconds),
        "live_started_at": live_started_at_raw,
        "expired": expired,
    }

def fetch_flash_products(limit: Optional[int] = 10, include_total: bool = False) -> Any:
    """Return DB-backed flash sale products for Home + Flash Deals pages."""
    runtime = sync_artisan_hour_runtime()
    if not runtime["live"]:
        return {"items": [], "total": 0} if include_total else []

    where_sql = """
        FROM product p
        JOIN category c ON c.category_id=p.category_id
        WHERE p.is_active=TRUE
          AND p.stock > 0
          AND p.is_flash_sale=TRUE
    """
    count_row = db_fetchone(f"SELECT COUNT(*) AS total {where_sql}") or {"total": 0}
    total = int(count_row.get("total") or 0)

    sql = f"""
        SELECT
            p.product_id, p.title, p.price_bdt, p.image_path,
            COALESCE(p.flash_discount, 20) AS flash_discount,
            c.name AS category_name
        {where_sql}
        ORDER BY p.created_at DESC
    """
    rows = db_fetchall(sql + (" LIMIT %s" if limit else ""), (limit,) if limit else ())
    out: List[Dict[str, Any]] = []
    for r in rows:
        price_bdt = Decimal(str(r.get("price_bdt") or "0"))
        disc = int(r.get("flash_discount") or 0)
        disc = max(1, min(95, disc))
        old_bdt = (price_bdt / (Decimal("1") - (Decimal(disc) / Decimal("100")))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        out.append(
            {
                "product_id": int(r["product_id"]),
                "name": r["title"],
                "cat": r.get("category_name") or "",
                "price_fmt": fmt_money(price_bdt),
                "old_price_fmt": fmt_money(old_bdt),
                "off": f"{disc}%",
                "img": r.get("image_path") or "/static/assets/img/placeholder.jpg",
            }
        )
    return {"items": out, "total": total} if include_total else out


def fetch_discovery_products(limit: Optional[int] = 20, buyer_id: Optional[int] = None, include_total: bool = False) -> Any:
    """Return DB-backed products for the 'Discovery Engine' grid on Home.

    If buyer_id is provided, each item will include an `is_wished` boolean.
    """
    where_sql = """
        FROM product p
        JOIN category c ON c.category_id=p.category_id
        WHERE p.is_active=TRUE
          AND p.stock > 0
    """
    count_row = db_fetchone(f"SELECT COUNT(*) AS total {where_sql}") or {"total": 0}
    total = int(count_row.get("total") or 0)

    sql = f"""
        SELECT
            p.product_id, p.title, p.price_bdt, p.image_path,
            c.name AS category_name
        {where_sql}
        ORDER BY p.discovery_score DESC, p.created_at DESC
    """
    rows = db_fetchall(sql + (" LIMIT %s" if limit else ""), (limit,) if limit else ())
    out: List[Dict[str, Any]] = []

    wished: set[int] = set()
    if buyer_id and rows:
        ids = [int(r["product_id"]) for r in rows if r.get("product_id") is not None]
        if ids:
            ph = ",".join(["%s"] * len(ids))
            wrows = db_fetchall(
                f"SELECT product_id FROM wishlist WHERE buyer_id=%s AND product_id IN ({ph})",
                tuple([buyer_id] + ids),
            )
            wished = {int(w["product_id"]) for w in wrows if w.get("product_id") is not None}

    for r in rows:
        pid = int(r["product_id"])
        price_bdt = Decimal(str(r.get("price_bdt") or "0"))
        out.append(
            {
                "product_id": pid,
                "name": r.get("title") or "",
                "cat": r.get("category_name") or "",
                "price_fmt": fmt_money(price_bdt),
                "img": r.get("image_path") or "/static/assets/img/placeholder.jpg",
                "is_wished": (pid in wished) if buyer_id else False,
            }
        )
    return {"items": out, "total": total} if include_total else out


def fetch_home_slider_products() -> List[Dict[str, Any]]:
    """Return all active products with images for the homepage showcase slider."""
    rows = db_fetchall(
        """
        SELECT p.product_id, p.title, p.image_path
        FROM product p
        WHERE p.is_active=TRUE
          AND p.stock > 0
          AND COALESCE(NULLIF(TRIM(p.image_path), ''), '') <> ''
        ORDER BY p.created_at DESC, p.product_id DESC
        """
    ) or []
    return [
        {
            "product_id": int(r["product_id"]),
            "name": r.get("title") or "",
            "img": r.get("image_path") or "/static/assets/img/placeholder.jpg",
        }
        for r in rows
        if r.get("product_id") is not None
    ]


def fetch_active_home_coupons() -> List[Dict[str, Any]]:
    """Return active non-expired coupons for the homepage coupon slider."""
    rows = db_fetchall(
        """
        SELECT coupon_id, code, discount_type, discount_value, usage_limit, used_count, expires_at, is_new_user_only
        FROM admin_coupon
        WHERE is_active=1
          AND (expires_at IS NULL OR expires_at >= CURDATE())
          AND (usage_limit IS NULL OR used_count < usage_limit)
        ORDER BY COALESCE(expires_at, '2099-12-31') ASC, created_at DESC, coupon_id DESC
        """
    ) or []

    out: List[Dict[str, Any]] = []
    for r in rows:
        typ = r.get("discount_type") or "Percentage"
        val = Decimal(str(r.get("discount_value") or 0))
        if typ == "Percentage":
            discount_text = f"{int(val) if val == val.to_integral_value() else val}% OFF"
        elif typ == "Fixed Amount":
            discount_text = f"{fmt_money(val)} OFF"
        else:
            discount_text = "Free Delivery"
        usage_limit = r.get("usage_limit")
        used_count = int(r.get("used_count") or 0)
        remaining = None if usage_limit is None else max(0, int(usage_limit) - used_count)
        expires_at = r.get("expires_at")
        out.append({
            "coupon_id": int(r.get("coupon_id") or 0),
            "code": (r.get("code") or "").upper(),
            "discount_text": discount_text,
            "type": typ,
            "expires_text": expires_at.strftime('%d %b %Y') if hasattr(expires_at, 'strftime') else 'No expiry',
            "is_new_user_only": bool(r.get("is_new_user_only")),
            "remaining_text": (f"{remaining} uses left" if remaining is not None else "Unlimited use"),
        })
    return out


# -----------------------
# GI Tag Verification (Authenticity)
# -----------------------
_GI_CODE_ALLOWED = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-")

def normalize_gi_code(raw: str) -> str:
    code = (raw or "").strip().upper()
    # Normalize common separators/spaces
    code = re.sub(r"\s+", "", code)
    return code

def gi_code_is_valid_format(code: str) -> bool:
    if not code:
        return False
    if len(code) < 8 or len(code) > 40:
        return False
    return all(ch in _GI_CODE_ALLOWED for ch in code)

def _client_ip() -> str:
    # behind proxy you may use X-Forwarded-For; we keep safe fallback
    xff = (request.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
    return xff or (request.remote_addr or "")

def verify_gi_tag(code_raw: str) -> Dict[str, Any]:
    """Verify a GI tag code against registry.

    Returns:
      { ok: bool, status: 'verified'|'not_found'|'revoked'|'invalid_format',
        message: str, data?: {...} }
    """
    code = normalize_gi_code(code_raw)
    ip = _client_ip()
    ua = (request.headers.get("User-Agent") or "")[:255]

    if not gi_code_is_valid_format(code):
        # Log invalid format attempts (no tag_id)
        db_execute(
            """INSERT INTO gi_tag_verification_log(tag_id, attempted_code, result, ip, user_agent)
                VALUES (NULL, %s, 'invalid_format', %s, %s)""",
            (code or (code_raw or "")[:40], ip, ua),
        )
        return {
            "ok": False,
            "status": "invalid_format",
            "message": "That code format doesn't look right. Please check the GI tag and try again.",
        }

    # Look up registry
    tag = db_fetchone(
        """SELECT
                gt.tag_id, gt.tag_code, gt.status, gt.verify_count, gt.first_verified_at,
                gt.last_verified_at,
                p.product_id, p.title AS product_title, p.image_path, p.gi_tag,
                c.name AS category_name,
                sc.name AS subcategory_name,
                d.name AS district_name,
                sp.shop_name, sp.owner_name,
                a.artisan_id, a.name AS artisan_name, a.location_text AS artisan_location
            FROM gi_tag gt
            JOIN product p ON p.product_id = gt.product_id
            JOIN category c ON c.category_id = p.category_id
            LEFT JOIN subcategory sc ON sc.subcategory_id = p.subcategory_id
            LEFT JOIN district d ON d.district_id = p.district_id
            JOIN seller_profile sp ON sp.seller_id = p.seller_id
            LEFT JOIN artisan a ON a.artisan_id = gt.issued_to_artisan_id
            WHERE gt.tag_code=%s
            LIMIT 1""",
        (code,),
    )

    if not tag:
        db_execute(
            """INSERT INTO gi_tag_verification_log(tag_id, attempted_code, result, ip, user_agent)
                VALUES (NULL, %s, 'not_found', %s, %s)""",
            (code, ip, ua),
        )
        return {
            "ok": False,
            "status": "not_found",
            "message": "No match found in our GI registry. Please re-check the code on your tag.",
        }

    tag_id = int(tag["tag_id"])

    if tag.get("status") == "revoked":
        db_execute(
            """INSERT INTO gi_tag_verification_log(tag_id, attempted_code, result, ip, user_agent)
                VALUES (%s, %s, 'revoked', %s, %s)""",
            (tag_id, code, ip, ua),
        )
        return {
            "ok": False,
            "status": "revoked",
            "message": "This GI tag has been revoked. If you believe this is an error, contact support with the code.",
            "data": {
                "tag_code": tag.get("tag_code"),
                "product_title": tag.get("product_title"),
            },
        }

    # Mark verification
    now = datetime.datetime.utcnow()
    first = tag.get("first_verified_at")
    db_execute(
        """UPDATE gi_tag
            SET verify_count = verify_count + 1,
                first_verified_at = COALESCE(first_verified_at, %s),
                last_verified_at = %s,
                last_verified_ip = %s,
                last_verified_user_agent = %s
            WHERE tag_id = %s""",
        (now, now, ip, ua, tag_id),
    )
    db_execute(
        """INSERT INTO gi_tag_verification_log(tag_id, attempted_code, result, ip, user_agent)
            VALUES (%s, %s, 'verified', %s, %s)""",
        (tag_id, code, ip, ua),
    )

    # Refetch counters (optional)
    updated = db_fetchone("SELECT verify_count, first_verified_at, last_verified_at FROM gi_tag WHERE tag_id=%s", (tag_id,))
    verify_count = int((updated or {}).get("verify_count") or tag.get("verify_count") or 0)

    def _dt(v):
        try:
            if isinstance(v, (datetime.datetime,)):
                return v.isoformat(sep=" ", timespec="seconds")
            return str(v) if v else None
        except Exception:
            return None

    data = {
        "tag_code": tag.get("tag_code"),
        "product": {
            "id": int(tag.get("product_id")),
            "title": tag.get("product_title") or "",
            "image": tag.get("image_path") or "/static/assets/img/placeholder.jpg",
            "gi_label": tag.get("gi_tag") or "",
            "category": tag.get("category_name") or "",
            "subcategory": tag.get("subcategory_name") or "",
            "district": tag.get("district_name") or "",
        },
        "maker": {
            "shop_name": tag.get("shop_name") or "",
            "owner_name": tag.get("owner_name") or "",
            "artisan_name": tag.get("artisan_name") or "",
            "artisan_location": tag.get("artisan_location") or "",
        },
        "verification": {
            "verify_count": verify_count,
            "first_verified_at": _dt((updated or {}).get("first_verified_at") or first),
            "last_verified_at": _dt((updated or {}).get("last_verified_at") or now),
        },
    }

    # Suspicion signal (simple heuristic)
    suspicious = verify_count >= 25
    msg = "Authenticity confirmed — this GI tag is valid and active."
    if suspicious:
        msg = "Authenticity confirmed — however this tag has been verified unusually often. If this is unexpected, double-check packaging."

    return {
        "ok": True,
        "status": "verified",
        "message": msg,
        "data": data,
        "suspicious": suspicious,
    }

# -----------------------
# Home Page Data (Heritage Soundscape)
# -----------------------
def fetch_soundscape_tracks(limit: int = 8) -> List[Dict[str, Any]]:
    """Return DB-backed soundscape tracks for the Home page."""
    rows = db_fetchall(
        """
        SELECT
            track_id, title, subtitle, duration_sec, audio_url, cover_image_url,
            craft_tag, is_featured, sort_order
        FROM soundscape_track
        WHERE is_active=TRUE
        ORDER BY is_featured DESC, sort_order ASC, track_id ASC
        LIMIT %s
        """,
        (limit,),
    )

    def fmt_dur(sec: int) -> str:
        try:
            s = max(0, int(sec))
        except Exception:
            s = 0
        m, r = divmod(s, 60)
        return f"{m}:{r:02d}"

    out: List[Dict[str, Any]] = []
    for r in rows:
        dur = int(r.get("duration_sec") or 0)
        out.append(
            {
                "track_id": int(r["track_id"]),
                "title": r.get("title") or "",
                "subtitle": r.get("subtitle") or "",
                "duration_sec": dur,
                "duration_fmt": fmt_dur(dur),
                "audio_url": r.get("audio_url") or "",
                "cover_image_url": r.get("cover_image_url") or "",
                "craft_tag": r.get("craft_tag") or "",
                "is_featured": bool(r.get("is_featured")),
            }
        )
    return out

# -----------------------
# Home Page Data (Featured Artisan Spotlight)
# -----------------------
def _fmt_compact_int(n: int) -> str:
    """Compact human readable numbers: 1200 -> 1.2k."""
    try:
        n_int = int(n)
    except Exception:
        return str(n)
    if n_int >= 1_000_000:
        v = n_int / 1_000_000.0
        s = f"{v:.1f}m".replace(".0m", "m")
        return s
    if n_int >= 1_000:
        v = n_int / 1_000.0
        s = f"{v:.1f}k".replace(".0k", "k")
        return s
    return str(n_int)


def fetch_featured_artisan() -> Optional[Dict[str, Any]]:
    """Return the featured artisan + latest active story (if any)."""
    selected_seller_id = _safe_int(get_setting("featured_seller_id", "0") or 0)
    if selected_seller_id > 0:
        seller_featured = _build_featured_artisan_from_seller(selected_seller_id)
        if seller_featured:
            return seller_featured

    a = db_fetchone(
        """
        SELECT
          artisan_id, name, specialty_title, location_text, badge_text,
          hero_image, tag, quote_text, started_year, years_mastery, pieces_created
        FROM artisan
        WHERE is_active=TRUE AND is_featured=TRUE
        ORDER BY updated_at DESC, created_at DESC
        LIMIT 1
        """
    )
    if not a:
        return None

    story = db_fetchone(
        """
        SELECT video_url
        FROM artisan_story
        WHERE artisan_id=%s AND is_active=TRUE
        ORDER BY published_at DESC
        LIMIT 1
        """,
        (int(a["artisan_id"]),),
    )

    years = a.get("years_mastery")
    # If years_mastery isn't explicitly set, derive it from started_year.
    if years is None and a.get("started_year"):
        try:
            years = max(0, datetime.now().year - int(a["started_year"]))
        except Exception:
            years = None

    pieces = a.get("pieces_created")
    # If pieces_created isn't explicitly set, derive it from total units sold
    # for products mapped to this artisan.
    if pieces is None:
        sold = db_fetchone(
            """
            SELECT COALESCE(SUM(oi.quantity),0) AS qty
            FROM artisan_product ap
            JOIN order_item oi ON oi.product_id = ap.product_id
            JOIN `order` o ON o.order_id = oi.order_id
            WHERE ap.artisan_id=%s
              AND o.status IN ('paid','shipped','delivered')
            """,
            (int(a["artisan_id"]),),
        )
        sold_qty = int((sold or {}).get("qty") or 0)
        pieces = sold_qty if sold_qty > 0 else None

    return {
        "artisan_id": int(a["artisan_id"]),
        "name": a.get("name") or "",
        "specialty_title": a.get("specialty_title") or "",
        "location_text": a.get("location_text") or "",
        "badge_text": a.get("badge_text") or "",
        "hero_image": a.get("hero_image") or "",
        "tag": a.get("tag") or "Artisan Story",
        "quote_text": a.get("quote_text") or "",
        "years_mastery": int(years) if years is not None else None,
        "pieces_created": int(pieces) if pieces is not None else None,
        "years_mastery_display": (f"{int(years)}+" if years is not None else ""),
        "pieces_created_display": (_fmt_compact_int(int(pieces)) if pieces is not None else ""),
        "story_video_url": (story.get("video_url") if story else None),
    }


def fetch_site_experience_settings() -> Dict[str, Any]:
    """Homepage/site-experience settings persisted in system_setting."""
    hero_headline = get_setting("home_hero_headline", "Threads of\nTradition,\nWoven with Soul.")
    hero_subtext = get_setting(
        "home_hero_subtext",
        "Discover the authenticity of Bengal. From the legendary Muslin to the royal Jamdani, bring home artifacts that carry a millennium of history.",
    )
    hero_image = get_setting(
        "home_hero_image",
        "https://images.unsplash.com/photo-1621252179027-94459d278660?auto=format&fit=crop&q=80&w=1200",
    )
    artisan_hour_runtime = sync_artisan_hour_runtime()
    artisan_hour_live = artisan_hour_runtime["live"]
    artisan_hour_start_date = (get_setting("artisan_hour_start_date", "") or "").strip()
    artisan_hour_end_date = (get_setting("artisan_hour_end_date", "") or "").strip()
    artisan_hour_start = get_setting("artisan_hour_start", "14:00") or "14:00"
    artisan_hour_end = get_setting("artisan_hour_end", "16:00") or "16:00"
    artisan_hour_total_hours_display = (get_setting("artisan_hour_total_hours_display", "") or "").strip()
    artisan_hour_start_at = ""
    artisan_hour_end_at = ""
    if artisan_hour_start_date and artisan_hour_start:
        artisan_hour_start_at = f"{artisan_hour_start_date}T{artisan_hour_start}:00"
    if artisan_hour_end_date and artisan_hour_end:
        artisan_hour_end_at = f"{artisan_hour_end_date}T{artisan_hour_end}:00"
    return {
        "hero_headline": hero_headline,
        "hero_subtext": hero_subtext,
        "hero_image": hero_image,
        "artisan_hour_live": artisan_hour_live,
        "artisan_hour_start_date": artisan_hour_start_date,
        "artisan_hour_end_date": artisan_hour_end_date,
        "artisan_hour_start": artisan_hour_start,
        "artisan_hour_end": artisan_hour_end,
        "artisan_hour_start_at": artisan_hour_start_at,
        "artisan_hour_end_at": artisan_hour_end_at,
        "artisan_hour_total_hours_display": artisan_hour_total_hours_display,
        "artisan_hour_duration_seconds": artisan_hour_runtime["duration_seconds"],
        "artisan_hour_remaining_seconds": artisan_hour_runtime["remaining_seconds"],
        "artisan_hour_live_started_at": artisan_hour_runtime["live_started_at"],
    }


def _build_featured_artisan_from_seller(seller_id: int) -> Optional[Dict[str, Any]]:
    row = db_fetchone(
        """
        SELECT sp.seller_id, sp.shop_name, sp.owner_name, sp.location, sp.category, sp.story,
               COALESCE(sp.avatar_url, '') AS avatar_url, sp.created_at
        FROM seller_profile sp
        WHERE sp.seller_id=%s
        LIMIT 1
        """,
        (seller_id,),
    )
    if not row:
        return None

    stats = db_fetchone(
        """
        SELECT
          COALESCE(SUM(oi.quantity),0) AS qty,
          COALESCE(COUNT(DISTINCT p.product_id),0) AS product_count
        FROM product p
        LEFT JOIN order_item oi ON oi.product_id=p.product_id
        WHERE p.seller_id=%s
        """,
        (seller_id,),
    ) or {}

    started_year = None
    created_at = row.get("created_at")
    if created_at:
        try:
            started_year = int(str(created_at)[:4])
        except Exception:
            started_year = None
    years_mastery = None
    if started_year:
        years_mastery = max(1, datetime.datetime.now().year - started_year)

    img = row.get("avatar_url") or "/static/assets/img/placeholder.jpg"
    return {
        "artisan_id": int(row.get("seller_id") or 0),
        "name": row.get("shop_name") or row.get("owner_name") or "Featured Artisan",
        "specialty_title": row.get("category") or "Heritage Craft",
        "location_text": row.get("location") or "Bangladesh",
        "badge_text": "Featured Artisan",
        "hero_image": img,
        "tag": "Artisan Spotlight",
        "quote_text": row.get("story") or "Selected by the Origins Bangladesh editorial team.",
        "years_mastery": years_mastery,
        "pieces_created": int(stats.get("qty") or 0) or int(stats.get("product_count") or 0) or None,
        "years_mastery_display": (f"{years_mastery}+" if years_mastery else ""),
        "pieces_created_display": (_fmt_compact_int(int(stats.get("qty") or 0)) if int(stats.get("qty") or 0) else (_fmt_compact_int(int(stats.get("product_count") or 0)) if int(stats.get("product_count") or 0) else "")),
        "story_video_url": None,
        "started_year": started_year,
    }




# -----------------------
# GI Journal (Premium Editorial)
# -----------------------
def fetch_journal_home() -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """Return (featured, side, quote) articles for the Home page GI Journal section."""
    featured = db_fetchone(
        """
        SELECT article_id, slug, title, subtitle, category, read_minutes, hero_image_url, thumb_image_url,
               teaser, quote_text, quote_author
        FROM gi_journal_article
        WHERE is_featured = TRUE
        ORDER BY published_at DESC, article_id DESC
        LIMIT 1
        """
    )
    if not featured:
        # Fallback to the newest article
        featured = db_fetchone(
            """
            SELECT article_id, slug, title, subtitle, category, read_minutes, hero_image_url, thumb_image_url,
                   teaser, quote_text, quote_author
            FROM gi_journal_article
            ORDER BY published_at DESC, article_id DESC
            LIMIT 1
            """
        )

    side = db_fetchone(
        """
        SELECT article_id, slug, title, subtitle, category, read_minutes, hero_image_url, thumb_image_url,
               teaser, quote_text, quote_author
        FROM gi_journal_article
        WHERE (is_featured = FALSE OR is_featured IS NULL)
        ORDER BY published_at DESC, article_id DESC
        LIMIT 1
        """
    )
    if not side:
        side = featured

    quote = db_fetchone(
        """
        SELECT article_id, slug, quote_text, quote_author
        FROM gi_journal_article
        WHERE quote_text IS NOT NULL AND quote_text <> ''
        ORDER BY published_at DESC, article_id DESC
        LIMIT 1
        """
    )
    if not quote:
        quote = {"quote_text": "Stories preserve what time tries to erase.", "quote_author": "Origins Bangladesh"}

    return featured or {}, side or {}, quote or {}


def fetch_journal_categories() -> List[Dict[str, Any]]:
    """Return categories with counts (for filters)."""
    return db_fetchall(
        """
        SELECT COALESCE(NULLIF(TRIM(category),''), 'Culture') AS category, COUNT(*) AS count
        FROM gi_journal_article
        GROUP BY COALESCE(NULLIF(TRIM(category),''), 'Culture')
        ORDER BY count DESC, category ASC
        """
    )


def fetch_journal_archives() -> List[Dict[str, Any]]:
    """Return monthly archives with counts."""
    return db_fetchall(
        """
        SELECT
            YEAR(published_at) AS y,
            MONTH(published_at) AS m,
            COUNT(*) AS count
        FROM gi_journal_article
        WHERE published_at IS NOT NULL
        GROUP BY YEAR(published_at), MONTH(published_at)
        ORDER BY y DESC, m DESC
        """
    )


def fetch_journal_featured_for_index() -> Optional[Dict[str, Any]]:
    """Featured card for index page. Falls back to latest."""
    featured = db_fetchone(
        """
        SELECT article_id, slug, title, subtitle, category, read_minutes, hero_image_url, thumb_image_url,
               teaser, published_at
        FROM gi_journal_article
        WHERE is_featured = TRUE
        ORDER BY published_at DESC, article_id DESC
        LIMIT 1
        """
    )
    if featured:
        return featured
    return db_fetchone(
        """
        SELECT article_id, slug, title, subtitle, category, read_minutes, hero_image_url, thumb_image_url,
               teaser, published_at
        FROM gi_journal_article
        ORDER BY published_at DESC, article_id DESC
        LIMIT 1
        """
    )


def fetch_journal_index_page(
    page: int = 1,
    per_page: int = 9,
    category: str = "",
    archive: str = "",
    exclude_article_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Paginated list of articles for index page, with optional category/archive filters.

    archive format: 'YYYY-MM' (e.g., '2026-02')
    """
    page = max(int(page or 1), 1)
    per_page = max(min(int(per_page or 9), 24), 1)

    where: List[str] = []
    params: List[Any] = []

    if category:
        where.append("COALESCE(NULLIF(TRIM(category),''), 'Culture')=%s")
        params.append(category)

    if archive:
        # archive like '2026-02'
        try:
            y_s, m_s = archive.split("-", 1)
            y = int(y_s)
            m = int(m_s)
            where.append("YEAR(published_at)=%s AND MONTH(published_at)=%s")
            params.extend([y, m])
        except Exception:
            # ignore bad archive
            archive = ""

    if exclude_article_id:
        where.append("article_id<>%s")
        params.append(int(exclude_article_id))

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    total_row = db_fetchone(f"SELECT COUNT(*) AS c FROM gi_journal_article {where_sql}", tuple(params))
    total = int((total_row or {}).get("c") or 0)
    total_pages = max(1, math.ceil(total / per_page)) if total > 0 else 1
    if page > total_pages:
        page = total_pages

    offset = (page - 1) * per_page
    items = db_fetchall(
        f"""
        SELECT article_id, slug, title, subtitle, category, read_minutes, hero_image_url, thumb_image_url,
               teaser, published_at
        FROM gi_journal_article
        {where_sql}
        ORDER BY published_at DESC, article_id DESC
        LIMIT %s OFFSET %s
        """,
        tuple(params + [per_page, offset]),
    )

    return dict(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        category=category,
        archive=archive,
    )


def fetch_article_by_slug(slug: str) -> Optional[Dict[str, Any]]:
    return db_fetchone(
        """
        SELECT article_id, slug, title, subtitle, category, read_minutes, hero_image_url, thumb_image_url,
               teaser, content_html, published_at
        FROM gi_journal_article
        WHERE slug=%s
        LIMIT 1
        """,
        (slug,),
    )

# -----------------------
# Cart / Wishlist Helpers
# -----------------------
def ensure_cart(buyer_id: int) -> int:
    row = db_fetchone("SELECT cart_id FROM cart WHERE buyer_id=%s", (buyer_id,))
    if row:
        return int(row["cart_id"])
    cart_id = db_execute("INSERT INTO cart(buyer_id) VALUES (%s)", (buyer_id,), return_lastrowid=True)
    return int(cart_id or 0)


def cart_summary(buyer_id: Optional[int]) -> Tuple[int, Decimal]:
    if not buyer_id or current_role() != "buyer":
        return (0, Decimal("0"))
    sql = """
        SELECT
            COALESCE(SUM(ci.quantity),0) AS item_count,
            COALESCE(SUM(ci.quantity * p.price_bdt),0) AS total_bdt
        FROM cart c
        LEFT JOIN cart_item ci ON ci.cart_id=c.cart_id
        LEFT JOIN product p ON p.product_id=ci.product_id
        WHERE c.buyer_id=%s
    """
    row = db_fetchone(sql, (buyer_id,))
    if not row:
        return (0, Decimal("0"))
    return (int(row["item_count"] or 0), Decimal(str(row["total_bdt"] or 0)))


def fetch_cart_items_detailed(buyer_id: int) -> List[Dict[str, Any]]:
    rows = db_fetchall(
        """
        SELECT
            ci.cart_item_id,
            ci.quantity,
            p.product_id,
            p.title,
            p.price_bdt,
            p.stock,
            p.image_path,
            p.category_id,
            p.gi_tag,
            a.artisan_id,
            a.name AS artisan_name,
            cat.name AS category_name
        FROM cart crt
        JOIN cart_item ci ON ci.cart_id=crt.cart_id
        JOIN product p ON p.product_id=ci.product_id
        LEFT JOIN artisan_product ap ON ap.product_id=p.product_id
        LEFT JOIN artisan a ON a.artisan_id=ap.artisan_id
        LEFT JOIN category cat ON cat.category_id=p.category_id
        WHERE crt.buyer_id=%s
        ORDER BY ci.created_at DESC
        """,
        (buyer_id,),
    ) or []
    out = []
    for r in rows:
        qty = int(r.get("quantity") or 0)
        price = Decimal(str(r.get("price_bdt") or 0))
        out.append({
            "cart_item_id": int(r.get("cart_item_id") or 0),
            "product_id": int(r.get("product_id") or 0),
            "name": r.get("title") or "",
            "quantity": qty,
            "price_bdt": price,
            "line_total_bdt": price * qty,
            "image_url": r.get("image_path") or "/static/assets/img/placeholder.jpg",
            "stock": int(r.get("stock") or 0),
            "artisan_id": int(r.get("artisan_id") or 0) if r.get("artisan_id") else None,
            "artisan_name": r.get("artisan_name") or "",
            "category_name": r.get("category_name") or "",
            "gi_tag": (r.get("gi_tag") or "").strip(),
        })
    return out


def get_shipping_rate(country_code: str) -> Decimal:
    code = (country_code or "BD").strip().upper()
    rates = {
        "BD": Decimal("100"),
        "IN": Decimal("1000"),
        "NP": Decimal("1200"),
        "BT": Decimal("1000"),
        "PK": Decimal("1500"),
        "LK": Decimal("1500"),
        "CN": Decimal("2000"),
        "MY": Decimal("1800"),
        "SG": Decimal("1800"),
        "AE": Decimal("2000"),
        "SA": Decimal("2200"),
        "GB": Decimal("2500"),
        "US": Decimal("2600"),
        "CA": Decimal("2600"),
        "AU": Decimal("2800"),
    }
    return rates.get(code, Decimal("2500"))


def _table_exists(table_name: str) -> bool:
    try:
        row = db_fetchone("SELECT 1 AS x FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name=%s LIMIT 1", (table_name,))
        return bool(row)
    except Exception:
        return False


def compute_coupon_discount(coupon: Dict[str, Any], subtotal_bdt: Decimal, shipping_bdt: Decimal) -> Decimal:
    ctype = (coupon.get("discount_type") or "").strip().lower()
    value = Decimal(str(coupon.get("discount_value") or 0))
    discount = Decimal("0")
    if ctype == "percentage":
        discount = (subtotal_bdt * value / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    elif ctype == "fixed amount":
        discount = value
    elif ctype == "free delivery":
        discount = shipping_bdt
    max_discount = coupon.get("maximum_discount_bdt")
    if max_discount is not None:
        try:
            discount = min(discount, Decimal(str(max_discount)))
        except Exception:
            pass
    return max(Decimal("0"), min(discount, subtotal_bdt + shipping_bdt))


def get_coupon_by_code(code: str) -> Optional[Dict[str, Any]]:
    code = (code or "").strip().upper()
    if not code:
        return None
    return db_fetchone(
        """
        SELECT coupon_id, code, discount_type, discount_value, usage_limit, used_count,
               expires_at, is_new_user_only, is_active,
               minimum_subtotal_bdt, maximum_discount_bdt, starts_at, per_user_limit, applicable_scope
        FROM admin_coupon
        WHERE UPPER(code)=%s
        LIMIT 1
        """,
        (code,),
    )


def validate_coupon_for_buyer(buyer_id: int, code: str, subtotal_bdt: Decimal, shipping_bdt: Decimal) -> Tuple[Optional[Dict[str, Any]], Optional[str], Decimal]:
    coupon = get_coupon_by_code(code)
    if not coupon:
        return None, "Coupon not found.", Decimal("0")
    if not int(coupon.get("is_active") or 0):
        return None, "This coupon is inactive.", Decimal("0")
    starts_at = coupon.get("starts_at")
    if starts_at and isinstance(starts_at, datetime.datetime) and starts_at > datetime.datetime.now():
        return None, "This coupon is not active yet.", Decimal("0")
    expires_at = coupon.get("expires_at")
    if expires_at and expires_at < datetime.date.today():
        return None, "This coupon has expired.", Decimal("0")
    usage_limit = coupon.get("usage_limit")
    if usage_limit is not None and int(coupon.get("used_count") or 0) >= int(usage_limit or 0):
        return None, "This coupon has reached its usage limit.", Decimal("0")
    min_subtotal = coupon.get("minimum_subtotal_bdt")
    if min_subtotal is not None and subtotal_bdt < Decimal(str(min_subtotal)):
        return None, f"Minimum order must be {fmt_money(Decimal(str(min_subtotal)))}.", Decimal("0")
    if int(coupon.get("is_new_user_only") or 0):
        row = db_fetchone("SELECT COUNT(*) AS c FROM `order` WHERE buyer_id=%s", (buyer_id,)) or {}
        if int(row.get("c") or 0) > 0:
            return None, "This coupon is only for new buyers.", Decimal("0")
    if _table_exists("coupon_redemption"):
        row = db_fetchone("SELECT COUNT(*) AS c FROM coupon_redemption WHERE buyer_id=%s AND coupon_id=%s", (buyer_id, int(coupon.get("coupon_id") or 0))) or {}
        per_user_limit = coupon.get("per_user_limit")
        if per_user_limit is not None and int(row.get("c") or 0) >= int(per_user_limit or 0):
            return None, "You already used this coupon the maximum number of times.", Decimal("0")
    discount = compute_coupon_discount(coupon, subtotal_bdt, shipping_bdt)
    if discount <= 0:
        return None, "This coupon does not apply to your cart.", Decimal("0")
    return coupon, None, discount


def build_checkout_summary(buyer_id: int, coupon_code: str = "", country: str = "BD", payment_method: str = "sslcommerz") -> Dict[str, Any]:
    items = fetch_cart_items_detailed(buyer_id)
    subtotal_bdt = sum((item["line_total_bdt"] for item in items), Decimal("0"))
    shipping_bdt = Decimal("0") if not items else get_shipping_rate(country)
    cod_fee_bdt = Decimal("50") if (payment_method or "").strip().lower() == "cod" and items else Decimal("0")
    discount_bdt = Decimal("0")
    coupon = None
    coupon_error = None
    coupon_code = (coupon_code or "").strip().upper()
    if coupon_code:
        coupon, coupon_error, discount_bdt = validate_coupon_for_buyer(buyer_id, coupon_code, subtotal_bdt, shipping_bdt)
    total_bdt = max(Decimal("0"), subtotal_bdt + shipping_bdt + cod_fee_bdt - discount_bdt)
    return {
        "items": items,
        "item_count": sum(int(item["quantity"]) for item in items),
        "subtotal_bdt": subtotal_bdt,
        "subtotal_fmt": fmt_money(subtotal_bdt),
        "shipping_bdt": shipping_bdt,
        "shipping_fmt": fmt_money(shipping_bdt),
        "cod_fee_bdt": cod_fee_bdt,
        "cod_fee_fmt": fmt_money(cod_fee_bdt),
        "discount_bdt": discount_bdt,
        "discount_fmt": fmt_money(discount_bdt),
        "total_bdt": total_bdt,
        "total_fmt": fmt_money(total_bdt),
        "country": (country or "BD").strip().upper(),
        "payment_method": (payment_method or "sslcommerz").strip().lower(),
        "coupon": coupon,
        "coupon_code": coupon_code,
        "coupon_error": coupon_error,
    }


def sync_buyer_points(buyer_id: int) -> int:
    try:
        if _table_exists("buyer_point_ledger"):
            row = db_fetchone("SELECT COALESCE(SUM(points_delta),0) AS pts FROM buyer_point_ledger WHERE buyer_id=%s", (buyer_id,)) or {}
            pts = int(row.get("pts") or 0)
        else:
            row = db_fetchone(
                """
                SELECT COALESCE(SUM(oi.quantity),0) * 10 AS pts
                FROM `order` o
                JOIN order_item oi ON oi.order_id=o.order_id
                WHERE o.buyer_id=%s AND LOWER(o.status)='delivered'
                """,
                (buyer_id,),
            ) or {}
            pts = int(row.get("pts") or 0)
        try:
            existing = db_fetchone("SELECT buyer_id FROM buyer_profile WHERE buyer_id=%s LIMIT 1", (buyer_id,))
            if existing:
                db_execute("UPDATE buyer_profile SET points=%s WHERE buyer_id=%s", (pts, buyer_id))
            else:
                db_execute("INSERT INTO buyer_profile (buyer_id, points, guardian_id) VALUES (%s, %s, %s)", (buyer_id, pts, get_or_create_guardian_id(buyer_id)))
        except Exception:
            pass
        return pts
    except Exception:
        return 0


def build_order_timeline(status: str, created_at: Optional[datetime.datetime] = None, delivered_at: Optional[datetime.datetime] = None) -> List[Dict[str, Any]]:
    s = (status or "pending").lower()
    base_dt = created_at if isinstance(created_at, datetime.datetime) else None
    crafting_dt = (base_dt + datetime.timedelta(hours=4)) if base_dt and s in ["paid", "processing", "packed", "shipped", "delivered"] else None
    shipped_dt = (base_dt + datetime.timedelta(days=1, hours=2)) if base_dt and s in ["shipped", "delivered"] else None
    delivered_dt = delivered_at if isinstance(delivered_at, datetime.datetime) else ((base_dt + datetime.timedelta(days=2, hours=3)) if base_dt and s == "delivered" else None)
    steps = [
        ("Order Confirmed", "Your order has been secured in the archive.", True, base_dt),
        ("Crafting / Packing", "Artisan and operations team are preparing the piece.", s in ["paid", "processing", "packed", "shipped", "delivered"], crafting_dt),
        ("Out for Delivery", "The collection is on its way.", s in ["shipped", "delivered"], shipped_dt),
        ("Delivered", "Safely delivered to your address.", s == "delivered", delivered_dt),
    ]
    out = []
    for label, desc, completed, dt in steps:
        out.append({"label": label, "desc": desc, "completed": bool(completed), "date": dt.strftime("%d %b %Y, %I:%M %p") if getattr(dt, 'strftime', None) else ""})
    return out


def get_order_current_phase(order_id: int, status: str, created_at: Optional[datetime.datetime] = None, delivered_at: Optional[datetime.datetime] = None) -> Dict[str, str]:
    s = (status or "pending").lower()
    phase_map = {
        "pending": ("Order Confirmed", "Your order has been secured in the archive."),
        "paid": ("Crafting / Packing", "Artisan and operations team are preparing the piece."),
        "processing": ("Crafting / Packing", "Artisan and operations team are preparing the piece."),
        "packed": ("Crafting / Packing", "Artisan and operations team are preparing the piece."),
        "shipped": ("Out for Delivery", "The collection is on its way."),
        "delivered": ("Delivered", "Safely delivered to your address."),
    }
    label, desc = phase_map.get(s, ("Order Confirmed", "Your order has been secured in the archive."))
    dt = created_at if isinstance(created_at, datetime.datetime) else None
    try:
        if s == "delivered" and isinstance(delivered_at, datetime.datetime):
            dt = delivered_at
        elif s in ["paid", "processing", "packed"]:
            row = db_fetchone(
                """
                SELECT ope.created_at AS event_time
                FROM order_provenance_event ope
                JOIN order_item oi ON oi.order_item_id=ope.order_item_id
                WHERE oi.order_id=%s
                  AND ope.event_type IN ('artisan_confirmed','crafting_started','quality_checked','packed')
                ORDER BY ope.created_at DESC
                LIMIT 1
                """,
                (order_id,),
            ) or {}
            dt = row.get("event_time") or (created_at + datetime.timedelta(hours=4) if isinstance(created_at, datetime.datetime) else None)
        elif s == "shipped":
            row = db_fetchone(
                """
                SELECT ope.created_at AS event_time
                FROM order_provenance_event ope
                JOIN order_item oi ON oi.order_item_id=ope.order_item_id
                WHERE oi.order_id=%s
                  AND ope.event_type IN ('shipped','packed','quality_checked')
                ORDER BY ope.created_at DESC
                LIMIT 1
                """,
                (order_id,),
            ) or {}
            dt = row.get("event_time") or (created_at + datetime.timedelta(days=1, hours=2) if isinstance(created_at, datetime.datetime) else None)
        else:
            row = db_fetchone(
                "SELECT created_at AS event_time FROM order_status_history WHERE order_id=%s ORDER BY created_at DESC LIMIT 1",
                (order_id,),
            ) or {}
            dt = row.get("event_time") or created_at
    except Exception:
        if s == "delivered" and isinstance(delivered_at, datetime.datetime):
            dt = delivered_at
        elif s in ["paid", "processing", "packed"] and isinstance(created_at, datetime.datetime):
            dt = created_at + datetime.timedelta(hours=4)
        elif s == "shipped" and isinstance(created_at, datetime.datetime):
            dt = created_at + datetime.timedelta(days=1, hours=2)
        else:
            dt = created_at
    return {"label": label, "desc": desc, "time": dt.strftime("%d %b %Y, %I:%M %p") if getattr(dt, "strftime", None) else ""}


def wishlist_count(buyer_id: Optional[int]) -> int:
    if not buyer_id or current_role() != "buyer":
        return 0
    row = db_fetchone("SELECT COUNT(*) AS c FROM wishlist WHERE buyer_id=%s", (buyer_id,))
    return int(row["c"] or 0) if row else 0


def fetch_home_stats() -> Dict[str, int]:
    """Homepage stats counters (DB-driven where possible)."""
    artisans_row = db_fetchone("SELECT COUNT(*) AS c FROM artisan WHERE is_active=TRUE")
    total_artisans = int(artisans_row["c"] or 0) if artisans_row else 0

    gi_row = db_fetchone(
        "SELECT COUNT(DISTINCT product_id) AS c FROM gi_tag WHERE status='active'"
    )
    gi_products = int(gi_row["c"] or 0) if gi_row else 0

    orders_row = db_fetchone("SELECT COUNT(*) AS c FROM `order`")
    orders = int(orders_row["c"] or 0) if orders_row else 0
    orders_k = int((orders + 999) // 1000)  # display as "K" on UI

    # No country table exists yet; keep a config-driven number (still backend-driven).
    try:
        countries = int(os.getenv("HOMEPAGE_COUNTRIES_COUNT", "15"))
    except Exception:
        countries = 42

    return {
        "total_artisans": total_artisans,
        "gi_products": gi_products,
        "orders_k": orders_k,
        "countries": countries,
    }


def fetch_nav_menu_data() -> Tuple[Dict[str, List[str]], List[str]]:
    """Build navbar categories/districts from live seller product selections when possible."""
    nav_categories: Dict[str, List[str]] = {}
    nav_districts: List[str] = []

    try:
        rows = db_fetchall(
            """
            SELECT
                c.name AS category_name,
                COALESCE(NULLIF(TRIM(sc.name), ''), '') AS subcategory_name,
                COUNT(*) AS item_count
            FROM product p
            JOIN category c ON c.category_id = p.category_id
            LEFT JOIN subcategory sc ON sc.subcategory_id = p.subcategory_id
            WHERE p.is_active = TRUE
            GROUP BY c.name, COALESCE(NULLIF(TRIM(sc.name), ''), '')
            ORDER BY c.name ASC, item_count DESC, subcategory_name ASC
            """
        ) or []

        for r in rows:
            main = (r.get('category_name') or '').strip()
            sub = (r.get('subcategory_name') or '').strip()
            if not main:
                continue
            nav_categories.setdefault(main, [])
            if sub and sub not in nav_categories[main]:
                nav_categories[main].append(sub)

        district_rows = db_fetchall(
            """
            SELECT d.name AS district_name, COUNT(*) AS item_count
            FROM product p
            JOIN district d ON d.district_id = p.district_id
            WHERE p.is_active = TRUE AND p.district_id IS NOT NULL
            GROUP BY d.name
            ORDER BY item_count DESC, d.name ASC
            LIMIT 16
            """
        ) or []
        nav_districts = [
            (r.get('district_name') or '').strip()
            for r in district_rows
            if (r.get('district_name') or '').strip()
        ]
    except Exception:
        nav_categories = {}
        nav_districts = []

    if not nav_categories:
        nav_categories = CATEGORIES
    if not nav_districts:
        nav_districts = DISTRICTS[:16]

    return nav_categories, nav_districts


@app.context_processor
def inject_globals():
    uid = current_user_id()
    count, total_bdt = cart_summary(uid)
    wcount = wishlist_count(uid)
    code = get_currency()
    symbol = "৳" if code == "BDT" else "$"

    # Navbar mega-menu data (dynamic from active seller product selections when available)
    nav_categories, nav_districts = fetch_nav_menu_data()

    role = current_role()

    # Display name in navbar.
    # - Buyer: user_account.name (cached in session)
    # - Seller: seller_profile.shop_name (fallback to session name)
    nav_user_name = session.get("name") or ""
    if uid and role == "seller":
        nav_user_name = session.get("seller_shop_name") or nav_user_name
        if not nav_user_name:
            try:
                srow = db_fetchone("SELECT shop_name FROM seller_profile WHERE seller_id=%s LIMIT 1", (uid,)) or {}
                nav_user_name = srow.get("shop_name") or nav_user_name
            except Exception:
                pass

    # Avatar URL (for navbar). Prefer session cache; fall back to DB when available.
    nav_avatar_url = session.get("avatar_url") or ""
    if uid and not nav_avatar_url:
        try:
            if role == "buyer":
                prow = db_fetchone("SELECT avatar_url FROM buyer_profile WHERE buyer_id=%s LIMIT 1", (uid,)) or {}
                nav_avatar_url = prow.get("avatar_url") or ""
            elif role == "seller":
                # seller_profile may not have avatar_url in older schemas; safe-try
                prow = db_fetchone("SELECT avatar_url FROM seller_profile WHERE seller_id=%s LIMIT 1", (uid,)) or {}
                nav_avatar_url = prow.get("avatar_url") or ""
        except Exception:
            nav_avatar_url = ""

    return dict(
        # Keep both legacy and navbar keys so templates won't break
        CATEGORIES=CATEGORIES,
        DISTRICTS=DISTRICTS,
        NAV_CATEGORIES=nav_categories,
        NAV_DISTRICTS=nav_districts,
        NAV_CART_COUNT=count,
        NAV_CART_TOTAL_FMT=fmt_money(total_bdt),
        NAV_WISHLIST_COUNT=wcount,
        NAV_CURRENCY=code,
        NAV_CURRENCY_SYMBOL=symbol,
        IS_LOGGED_IN=bool(uid),
        NAV_ROLE=current_role(),
        NAV_USER_ID=uid,
        NAV_USER_NAME=nav_user_name,
        NAV_AVATAR_URL=nav_avatar_url,
    )



def _safe_int(v: Any, default: int = 0) -> int:
    try:
        return int(v or 0)
    except Exception:
        return default


def _safe_decimal(v: Any) -> Decimal:
    try:
        return Decimal(str(v or 0))
    except Exception:
        return Decimal("0")


def _fmt_dt(dt: Any, fmt: str = "%d %b %Y") -> str:
    try:
        return dt.strftime(fmt) if dt else ""
    except Exception:
        return ""


def _seller_order_ui_status(status: str) -> str:
    s = (status or "").lower().strip()
    return {
        "pending": "Pending",
        "paid": "Processing",
        "processing": "Processing",
        "shipped": "Ready to Ship",
        "delivered": "Delivered",
        "cancelled": "Cancelled",
    }.get(s, s.title() or "Pending")


def _ensure_seller_session_state(seller_id: int) -> None:
    try:
        row = db_fetchone(
            """
            SELECT shop_name, is_verified, verification_status, avatar_url
            FROM seller_profile
            WHERE seller_id=%s
            LIMIT 1
            """,
            (seller_id,),
        ) or {}
        if row.get("shop_name"):
            session["seller_shop_name"] = row.get("shop_name")
        session["seller_is_verified"] = bool(row.get("is_verified"))
        session["seller_verification_status"] = row.get("verification_status") or "draft"
        if row.get("avatar_url"):
            session["avatar_url"] = row.get("avatar_url")
    except Exception:
        session["seller_is_verified"] = False
        session["seller_verification_status"] = session.get("seller_verification_status") or "draft"


def _build_seller_dashboard_data(seller_id: int) -> Dict[str, Any]:
    profile = db_fetchone(
        """
        SELECT u.name AS account_name, u.email, u.phone,
               sp.shop_name, sp.owner_name, sp.location, sp.category, sp.story,
               sp.is_verified, sp.created_at,
               COALESCE(sp.verification_status, CASE WHEN sp.is_verified THEN 'approved' ELSE 'draft' END) AS verification_status,
               sp.reviewed_at, sp.rejection_reason,
               COALESCE(sp.avatar_url, '') AS avatar_url
        FROM user_account u
        LEFT JOIN seller_profile sp ON sp.seller_id=u.user_id
        WHERE u.user_id=%s
        LIMIT 1
        """,
        (seller_id,),
    ) or {}

    wallet = {}
    try:
        wallet = db_fetchone(
            "SELECT available_balance, pending_balance FROM seller_wallet WHERE seller_id=%s LIMIT 1",
            (seller_id,),
        ) or {}
    except Exception:
        wallet = {}

    sales_row = db_fetchone(
        """
        SELECT
          COALESCE(SUM(CASE WHEN LOWER(o.status) IN ('paid','shipped','delivered') THEN oi.quantity * oi.unit_price_bdt ELSE 0 END), 0) AS total_sales,
          COALESCE(COUNT(DISTINCT CASE WHEN LOWER(o.status) IN ('paid','shipped','delivered') THEN o.order_id END), 0) AS completed_orders,
          COALESCE(COUNT(DISTINCT CASE WHEN LOWER(o.status) IN ('pending','paid','shipped') THEN o.order_id END), 0) AS active_orders,
          COALESCE(COUNT(DISTINCT CASE WHEN LOWER(o.status)='pending' THEN o.order_id END), 0) AS attention_orders,
          COALESCE(COUNT(DISTINCT o.buyer_id), 0) AS customers
        FROM order_item oi
        JOIN `order` o ON o.order_id=oi.order_id
        JOIN product p ON p.product_id=oi.product_id
        WHERE p.seller_id=%s
        """,
        (seller_id,),
    ) or {}

    products_row = db_fetchone(
        """
        SELECT COUNT(*) AS total_products,
               COALESCE(SUM(CASE WHEN is_active=TRUE THEN 1 ELSE 0 END), 0) AS active_products,
               COALESCE(SUM(CASE WHEN stock <= 0 THEN 1 ELSE 0 END), 0) AS out_of_stock_products
        FROM product
        WHERE seller_id=%s
        """,
        (seller_id,),
    ) or {}

    gi_rows = []
    try:
        gi_rows = db_fetchall(
            """
            SELECT app_id, product_name, category, details, certificate_path, status, feedback, submitted_at
            FROM seller_gi_application
            WHERE seller_id=%s
            ORDER BY submitted_at DESC, app_id DESC
            """,
            (seller_id,),
        ) or []
    except Exception:
        gi_rows = []

    recent_order_rows = db_fetchall(
        """
        SELECT o.order_id, o.status, o.total_bdt, o.created_at, o.buyer_id,
               u.name AS customer_name,
               u.email AS customer_email,
               GROUP_CONCAT(CONCAT(oi.quantity, 'x ', p.title) ORDER BY oi.order_item_id SEPARATOR ', ') AS items,
               MAX(CASE WHEN o.status='pending' THEN 1 ELSE 0 END) AS needs_attention
        FROM `order` o
        JOIN order_item oi ON oi.order_id=o.order_id
        JOIN product p ON p.product_id=oi.product_id AND p.seller_id=%s
        LEFT JOIN user_account u ON u.user_id=o.buyer_id
        GROUP BY o.order_id, o.status, o.total_bdt, o.created_at, o.delivered_at, o.buyer_id, u.name, u.email
        ORDER BY o.created_at DESC, o.order_id DESC
        LIMIT 20
        """,
        (seller_id,),
    ) or []

    orders = []
    for r in recent_order_rows:
        ui_status = _seller_order_ui_status(r.get("status") or "pending")
        orders.append({
            "id": format_order_id(r.get('order_id')),
            "customer": r.get("customer_name") or f"Buyer #{_safe_int(r.get('buyer_id'))}",
            "email": r.get("customer_email") or "",
            "items": r.get("items") or "1x Heritage Item",
            "total": float(_safe_decimal(r.get("total_bdt"))),
            "status": ui_status,
            "date": _fmt_dt(r.get("created_at"), "%d %b %Y, %I:%M %p"),
            "payment": "Online",
            "acc": "Paid via gateway",
        })

    docs = []
    try:
        docs = db_fetchall(
            "SELECT doc_type, file_path, uploaded_at FROM seller_verification_doc WHERE seller_id=%s ORDER BY uploaded_at DESC",
            (seller_id,),
        ) or []
    except Exception:
        docs = []
    doc_map = {}
    for d in docs:
        path = d.get("file_path") or ""
        name = os.path.basename(path)
        ext = os.path.splitext(name)[1].lower()
        mime = "application/octet-stream"
        if ext in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
            mime = f"image/{'jpeg' if ext in {'.jpg', '.jpeg'} else ext.lstrip('.')}"
        elif ext == ".pdf":
            mime = "application/pdf"
        elif ext == ".doc":
            mime = "application/msword"
        elif ext == ".docx":
            mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        doc_map[str(d.get("doc_type") or "")] = {
            "url": path,
            "name": name,
            "type": mime,
            "uploaded_at": _fmt_dt(d.get("uploaded_at")),
        }

    payout_methods = []
    try:
        payout_methods_rows = db_fetchall(
            "SELECT method_id, provider, account_number, created_at FROM seller_payout_method WHERE seller_id=%s ORDER BY created_at DESC, method_id DESC",
            (seller_id,),
        ) or []
        for r in payout_methods_rows:
            provider = r.get("provider") or "Payout Method"
            payout_methods.append({
                "id": f"m{_safe_int(r.get('method_id'))}",
                "name": provider,
                "acc": r.get("account_number") or "",
                "type": "bank" if "bank" in provider.lower() else "mobile",
            })
    except Exception:
        payout_methods = []

    txs = []
    try:
        tx_rows = db_fetchall(
            "SELECT trx_id, type, method, amount, status, created_at FROM seller_transaction WHERE seller_id=%s ORDER BY created_at DESC, trx_id DESC LIMIT 50",
            (seller_id,),
        ) or []
        for r in tx_rows:
            txs.append({
                "id": format_trx_id(r.get('trx_id')),
                "date": _fmt_dt(r.get("created_at"), "%d %b %Y"),
                "time": _fmt_dt(r.get("created_at"), "%I:%M %p"),
                "accountNumber": r.get("method") or "",
                "type": "Payment Cash In" if (r.get("type") or "") == "cash_in" else "Cash Withdraw",
                "method": r.get("method") or "",
                "amount": float(_safe_decimal(r.get("amount"))),
                "status": (r.get("status") or "pending").upper(),
                "color": "emerald" if (r.get("type") or "") == "cash_in" else "slate",
            })
    except Exception:
        txs = []

    total_sales = _safe_decimal(sales_row.get("total_sales"))
    customers = _safe_int(sales_row.get("customers"))
    active_orders = _safe_int(sales_row.get("active_orders"))
    attention_orders = _safe_int(sales_row.get("attention_orders"))
    rating_score = Decimal("3.8")
    if customers > 0:
        rating_score = min(Decimal("5.0"), Decimal("3.9") + (Decimal(str(min(customers, 200))) / Decimal("200")) + (Decimal(str(min(_safe_int(products_row.get('active_products')), 50))) / Decimal("250")))
    impact_score = float(rating_score.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))

    notifications = []
    if attention_orders:
        notifications.append({"id": 1, "title": "Orders need action", "desc": f"{attention_orders} order(s) are waiting for your response.", "time": "Now", "icon": "package", "color": "amber", "read": False, "targetView": "orders"})
    if (profile.get("verification_status") or "draft") in ("submitted", "under_review"):
        notifications.append({"id": 2, "title": "Verification in review", "desc": "Your submitted documents are under admin review.", "time": "Now", "icon": "shield-check", "color": "blue", "read": False, "targetView": "verification"})
    if _safe_decimal(wallet.get("pending_balance")) > 0:
        notifications.append({"id": 3, "title": "Pending payout", "desc": f"{fmt_money(_safe_decimal(wallet.get('pending_balance')))} will move to available after settlement.", "time": "Now", "icon": "wallet", "color": "emerald", "read": False, "targetView": "wallet"})

    gi_apps = []
    for idx, r in enumerate(gi_rows, start=1):
        gi_apps.append({
            "id": _safe_int(r.get("app_id")) or idx,
            "product": r.get("product_name") or "",
            "category": r.get("category") or "",
            "details": r.get("details") or "",
            "certificate": r.get("certificate_path"),
            "submitted": _fmt_dt(r.get("submitted_at")),
            "status": (r.get("status") or "pending").title(),
            "feedback": r.get("feedback") or "",
        })

    verification_status = (profile.get("verification_status") or ("approved" if profile.get("is_verified") else "draft")).lower()
    locked = verification_status != "approved"

    return {
        "seller_info": {
            "shop_name": profile.get("shop_name") or session.get("seller_shop_name") or (profile.get("account_name") or "Seller"),
            "owner_name": profile.get("owner_name") or profile.get("account_name") or "",
            "location": profile.get("location") or "",
            "category": profile.get("category") or "",
            "story": profile.get("story") or "",
            "avatar_url": profile.get("avatar_url") or session.get("avatar_url") or "",
            "is_verified": verification_status == "approved",
            "member_since": _fmt_dt(profile.get("created_at"), "%Y-%m-%d"),
            "verification_status": verification_status,
            "rejection_reason": profile.get("rejection_reason") or "",
            "reviewed_at": _fmt_dt(profile.get("reviewed_at")),
        },
        "dashboard": {
            "impact_score": impact_score,
            "customers_reached": customers,
            "total_sales": float(total_sales),
            "total_sales_fmt": fmt_money(total_sales),
            "pending_payout": float(_safe_decimal(wallet.get("pending_balance"))),
            "pending_payout_fmt": fmt_money(_safe_decimal(wallet.get("pending_balance"))),
            "active_orders": active_orders,
            "orders_needing_attention": attention_orders,
            "verification_status": verification_status,
            "locked": locked,
            "products_total": _safe_int(products_row.get("total_products")),
            "products_active": _safe_int(products_row.get("active_products")),
            "products_out_of_stock": _safe_int(products_row.get("out_of_stock_products")),
        },
        "orders": orders,
        "products": [{
            "id": _safe_int(r.get("product_id")),
            "name": r.get("title") or "",
            "price": float(_safe_decimal(r.get("price_bdt"))),
            "stock": _safe_int(r.get("stock")),
            "status": "Live" if bool(r.get("is_active")) else "Draft",
            "gi_status": "Verified" if (r.get("gi_tag") or "").strip() else "None",
            "category": r.get("category_name") or (profile.get("category") or "General"),
            "story": r.get("description") or "",
            "image": r.get("image_path") or "/static/assets/img/placeholder.jpg",
        } for r in (db_fetchall("""
            SELECT p.product_id, p.title, p.description, p.price_bdt, p.stock, p.gi_tag, p.image_path, p.is_active,
                   c.name AS category_name
            FROM product p
            LEFT JOIN category c ON c.category_id=p.category_id
            WHERE p.seller_id=%s
            ORDER BY p.created_at DESC, p.product_id DESC
            LIMIT 100
        """, (seller_id,)) or [])],
        "gi_apps": gi_apps,
        "flash_sales": [{"id": a.get("id", idx+1), "campaign": "Pending Campaign", "product": a.get("product") or "", "discount": 0, "status": a.get("status") or "Pending"} for idx, a in enumerate(gi_apps[:10])],
        "transactions": txs,
        "methods": payout_methods,
        "notifications": notifications,
        "verification_docs": doc_map,
    }


def _build_admin_dashboard_data() -> Dict[str, Any]:
    summary = db_fetchone(
        """
        SELECT
          COALESCE((SELECT SUM(total_bdt) FROM `order` WHERE LOWER(status) IN ('paid','shipped','delivered')), 0) AS revenue,
          COALESCE((SELECT COUNT(*) FROM seller_profile), 0) AS artisans,
          COALESCE((SELECT COUNT(*) FROM product WHERE COALESCE(NULLIF(TRIM(gi_tag), ''), '') <> ''), 0) AS gi_products,
          COALESCE((SELECT COUNT(*) FROM `order`), 0) AS orders,
          COALESCE((SELECT COUNT(*) FROM seller_profile WHERE COALESCE(verification_status, CASE WHEN is_verified THEN 'approved' ELSE 'draft' END) IN ('submitted','under_review')), 0) AS pending_verifications,
          COALESCE((SELECT COUNT(*) FROM seller_gi_application WHERE status='pending'), 0) AS pending_gi,
          COALESCE((SELECT COUNT(*) FROM product WHERE is_active=FALSE), 0) AS hidden_products,
          COALESCE((SELECT COUNT(*) FROM gi_journal_article), 0) AS journal_count,
          COALESCE((SELECT COUNT(*) FROM district_atlas WHERE is_active=TRUE), 0) AS atlas_active,
          COALESCE((SELECT COUNT(*) FROM user_account WHERE role='seller' AND is_active=TRUE), 0) AS active_seller_accounts
        """
    ) or {}

    revenue = _safe_decimal(summary.get("revenue"))
    revenue_analytics_rows = db_fetchall(
        """
        SELECT DATE_FORMAT(created_at, '%Y-%m') AS ym,
               COALESCE(SUM(total_bdt),0) AS revenue,
               COUNT(*) AS orders
        FROM `order`
        WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
        GROUP BY DATE_FORMAT(created_at, '%Y-%m')
        ORDER BY ym ASC
        """
    ) or []
    revenue_analytics = [{"month": r.get("ym") or "", "revenue": float(_safe_decimal(r.get("revenue"))), "orders": _safe_int(r.get("orders"))} for r in revenue_analytics_rows]

    seller_rows = db_fetchall(
        """
        SELECT sp.seller_id AS id, sp.shop_name AS name, u.email, COALESCE(sp.category,'General') AS type,
               CASE
                 WHEN COALESCE(sp.verification_status, CASE WHEN sp.is_verified THEN 'approved' ELSE 'draft' END)='approved' THEN 'Active'
                 WHEN COALESCE(sp.verification_status, CASE WHEN sp.is_verified THEN 'approved' ELSE 'draft' END) IN ('submitted','under_review') THEN 'Pending Verification'
                 WHEN COALESCE(sp.verification_status, CASE WHEN sp.is_verified THEN 'approved' ELSE 'draft' END)='rejected' THEN 'Rejected'
                 ELSE 'Draft'
               END AS status,
               COALESCE(sp.location,'Bangladesh') AS district,
               COUNT(DISTINCT p.product_id) AS sales,
               AVG(CASE WHEN LOWER(o.status) IN ('paid','shipped','delivered') THEN 5 ELSE NULL END) AS rating,
               COALESCE(sp.avatar_url, '/static/assets/img/basic-avatar.svg') AS img
        FROM seller_profile sp
        JOIN user_account u ON u.user_id=sp.seller_id
        LEFT JOIN product p ON p.seller_id=sp.seller_id
        LEFT JOIN order_item oi ON oi.product_id=p.product_id
        LEFT JOIN `order` o ON o.order_id=oi.order_id
        GROUP BY sp.seller_id, sp.shop_name, u.email, sp.category, sp.location, sp.verification_status, sp.is_verified, sp.avatar_url
        ORDER BY sp.created_at DESC, sp.seller_id DESC
        LIMIT 100
        """
    ) or []

    verification_rows = db_fetchall(
        """
        SELECT sp.seller_id AS id, sp.shop_name AS name, COALESCE(sp.location,'Bangladesh') AS loc,
               sp.created_at, COUNT(svd.doc_type) AS docs,
               COALESCE(sp.verification_status, CASE WHEN sp.is_verified THEN 'approved' ELSE 'draft' END) AS status,
               u.email
        FROM seller_profile sp
        JOIN user_account u ON u.user_id=sp.seller_id
        LEFT JOIN seller_verification_doc svd ON svd.seller_id=sp.seller_id
        WHERE COALESCE(sp.verification_status, CASE WHEN sp.is_verified THEN 'approved' ELSE 'draft' END) IN ('submitted','under_review')
        GROUP BY sp.seller_id, sp.shop_name, sp.location, sp.created_at, sp.verification_status, sp.is_verified, u.email
        ORDER BY sp.created_at DESC, sp.seller_id DESC
        LIMIT 100
        """
    ) or []

    products = db_fetchall(
        """
        SELECT p.product_id AS id, p.title AS name, p.price_bdt AS price, p.stock,
               COALESCE(SUM(oi.quantity),0) AS sold,
               sp.shop_name AS seller, u.email AS seller_mail,
               CASE WHEN p.is_active THEN 'Live' ELSE 'Draft' END AS status,
               CASE WHEN COALESCE(NULLIF(TRIM(p.gi_tag),''),'')<>'' THEN 'Certified' ELSE 'None' END AS gi_status,
               'box' AS img
        FROM product p
        JOIN seller_profile sp ON sp.seller_id=p.seller_id
        JOIN user_account u ON u.user_id=sp.seller_id
        LEFT JOIN order_item oi ON oi.product_id=p.product_id
        GROUP BY p.product_id, p.title, p.price_bdt, p.stock, sp.shop_name, u.email, p.is_active, p.gi_tag
        ORDER BY p.created_at DESC, p.product_id DESC
        LIMIT 100
        """
    ) or []

    orders = db_fetchall(
        """
        SELECT o.order_id, u.name AS customer, u.email,
               GROUP_CONCAT(CONCAT(oi.quantity, 'x ', p.title) ORDER BY oi.order_item_id SEPARATOR ', ') AS items,
               o.total_bdt AS total, o.order_id AS displayOrderIdRaw, o.order_id AS trxIdRaw,
               CASE LOWER(o.status)
                 WHEN 'pending' THEN 'Processing'
                 WHEN 'paid' THEN 'Processing'
                 WHEN 'shipped' THEN 'Shipped'
                 WHEN 'delivered' THEN 'Delivered'
                 WHEN 'cancelled' THEN 'Cancelled'
                 ELSE 'Processing'
               END AS status,
               DATE_FORMAT(o.created_at, '%d %b %Y, %h:%i %p') AS date
        FROM `order` o
        JOIN user_account u ON u.user_id=o.buyer_id
        LEFT JOIN order_item oi ON oi.order_id=o.order_id
        LEFT JOIN product p ON p.product_id=oi.product_id
        GROUP BY o.order_id, u.name, u.email, o.total_bdt, o.status, o.created_at
        ORDER BY o.created_at DESC, o.order_id DESC
        LIMIT 100
        """
    ) or []
    for o in orders:
        o["id"] = format_order_id(o.get("displayOrderIdRaw") or o.get("order_id") or o.get("id"))
        o["trxId"] = format_trx_id(o.get("trxIdRaw") or o.get("order_id") or o.get("trxId"))

    gi_requests = []
    try:
        gi_requests = db_fetchall(
            """
            SELECT a.app_id AS id, a.product_name AS product, COALESCE(sp.location,'Bangladesh') AS district,
                   sp.shop_name AS seller, a.status, DATE_FORMAT(a.submitted_at, '%d %b %Y') AS date
            FROM seller_gi_application a
            JOIN seller_profile sp ON sp.seller_id=a.seller_id
            WHERE a.status='pending'
            ORDER BY a.submitted_at DESC, a.app_id DESC
            LIMIT 100
            """
        ) or []
    except Exception:
        gi_requests = []

    journal = db_fetchall(
        """
        SELECT article_id AS id, title, COALESCE(quote_author, 'Editorial Team') AS author,
               DATE_FORMAT(COALESCE(published_at, CURRENT_TIMESTAMP), '%M %e, %Y') AS date,
               CASE WHEN published_at IS NULL THEN 'Draft' ELSE 'Published' END AS status,
               COALESCE(thumb_image_url, hero_image_url, '/static/assets/img/placeholder.jpg') AS img
        FROM gi_journal_article
        ORDER BY COALESCE(published_at, created_at) DESC, article_id DESC
        LIMIT 50
        """
    ) or []

    atlas = db_fetchall(
        """
        SELECT a.atlas_id AS id, d.district_id AS district_id, d.name AS district, a.density, a.product_name AS product, a.category,
               a.story, COALESCE(a.image_url,'') AS img, COALESCE(a.shop_link,'') AS link,
               COALESCE(a.dot_x,0) AS x, COALESCE(a.dot_y,0) AS y, a.is_active AS isActive
        FROM district_atlas a
        JOIN district d ON d.district_id=a.district_id
        ORDER BY d.name ASC
        LIMIT 100
        """
    ) or []

    logs = db_fetchall(
        """
        SELECT a.audit_id, a.action, a.created_at, COALESCE(u.name, 'System') AS user
        FROM audit_log a
        LEFT JOIN user_account u ON u.user_id=a.actor_user_id
        ORDER BY a.created_at DESC, a.audit_id DESC
        LIMIT 100
        """
    ) or []
    logs = [{
        'id': r0.get('audit_id'),
        'action': str(r0.get('action') or '').replace('_', ' ').title(),
        'user': r0.get('user') or 'System',
        'date': (r0.get('created_at').strftime('%b %d') if r0.get('created_at') else ''),
        'time': (r0.get('created_at').strftime('%I:%M %p') if r0.get('created_at') else ''),
    } for r0 in logs]

    featured = fetch_featured_artisan() or {}
    featured_artisan = {
        "name": featured.get("name") or "No featured artisan",
        "desc": " • ".join([x for x in [featured.get("specialty_title") or "", featured.get("location_text") or ""] if x]).strip(" •"),
        "rating": f"{max(4.5, min(5.0, float(featured.get('years_mastery') or 5) / 10 + 4)):.1f} ★" if featured else "4.8 ★",
        "prods": f"{_safe_int(featured.get('pieces_created'))}+" if featured.get("pieces_created") else "—",
        "since": str(featured.get("started_year") or ""),
        "img": featured.get("hero_image") or "/static/assets/img/placeholder.jpg",
    }

    action_required = []
    if _safe_int(summary.get("pending_verifications")):
        action_required.append({"label": "Verification Hub", "count": _safe_int(summary.get("pending_verifications")), "detail": "seller(s) awaiting review", "target": "verification"})
    if _safe_int(summary.get("pending_gi")):
        action_required.append({"label": "GI Certification", "count": _safe_int(summary.get("pending_gi")), "detail": "pending GI request(s)", "target": "gi-verify"})
    if _safe_int(summary.get("hidden_products")):
        action_required.append({"label": "Product Catalog", "count": _safe_int(summary.get("hidden_products")), "detail": "product(s) hidden or draft", "target": "products"})

    featured_queue = _build_featured_selection_queue()

    transactions = db_fetchall(
        """
        SELECT order_id AS raw_id,
               DATE_FORMAT(created_at, '%b %d') AS date,
               DATE_FORMAT(created_at, '%h:%i %p') AS time,
               'Order Payment' AS type,
               total_bdt AS amount,
               'Order' AS method,
               CASE WHEN LOWER(status) IN ('cancelled') THEN 'Cancelled' ELSE 'Completed' END AS status,
               COALESCE((SELECT name FROM user_account u WHERE u.user_id=o.buyer_id), 'Buyer') AS party,
               COALESCE((SELECT email FROM user_account u WHERE u.user_id=o.buyer_id), '-') AS email
        FROM `order` o
        ORDER BY created_at DESC, order_id DESC
        LIMIT 100
        """
    ) or []
    for t in transactions:
        t["id"] = format_trx_id(t.get("raw_id") or t.get("id"))
    transactions = _mix_demo_rows(transactions, [
        {'id': format_trx_id(970001), 'date': 'Demo', 'time': '09:00 AM', 'type': 'Order Payment', 'amount': 6500, 'method': 'Order', 'status': 'Completed', 'party': 'Demo Buyer One', 'email': 'buyer1@demo.bd'},
        {'id': format_trx_id(970002), 'date': 'Demo', 'time': '11:15 AM', 'type': 'Payout', 'amount': -3200, 'method': 'Manual', 'status': 'Completed', 'party': 'Demo Loom Legacy', 'email': 'demo-loom@origins.bd'},
        {'id': format_trx_id(970003), 'date': 'Demo', 'time': '02:40 PM', 'type': 'Order Payment', 'amount': 2450, 'method': 'Order', 'status': 'Completed', 'party': 'Demo Buyer Three', 'email': 'buyer3@demo.bd'},
    ], minimum=3)

    verification_rows = _mix_demo_rows(verification_rows, [
        {'id': 91001, 'name': 'Demo Loom Legacy', 'loc': 'Tangail', 'docs': 3, 'status': 'Pending', 'time': 'Demo data'},
        {'id': 91002, 'name': 'Demo Nakshi Katha Co.', 'loc': 'Jessore', 'docs': 2, 'status': 'Pending', 'time': 'Demo data'},
        {'id': 91003, 'name': 'Demo Cane Craft', 'loc': 'Rangpur', 'docs': 4, 'status': 'Pending', 'time': 'Demo data'},
    ], minimum=3)
    products = _mix_demo_rows(products, [
        {'id': 92001, 'name': 'Demo Jamdani Saree', 'price': 6500, 'stock': 8, 'sold': 11, 'seller': 'Demo Loom Legacy', 'seller_mail': 'demo-loom@origins.bd', 'status': 'Live', 'gi_status': 'Certified', 'img': 'ph-shirt-folded'},
        {'id': 92002, 'name': 'Demo Clay Vase', 'price': 1800, 'stock': 12, 'sold': 5, 'seller': 'Demo Terracotta Craft', 'seller_mail': 'demo-clay@origins.bd', 'status': 'Draft', 'gi_status': 'None', 'img': 'ph-vase'},
        {'id': 92003, 'name': 'Demo Bamboo Lamp', 'price': 2450, 'stock': 6, 'sold': 3, 'seller': 'Demo Cane Craft', 'seller_mail': 'demo-bamboo@origins.bd', 'status': 'Hidden', 'gi_status': 'None', 'img': 'ph-lamp'},
    ], minimum=3)
    orders = _mix_demo_rows(orders, [
        {'order_id': 93001, 'id': format_order_id(93001), 'customer': 'Demo Buyer One', 'email': 'buyer1@demo.bd', 'items': '1x Demo Jamdani Saree', 'total': 6500, 'trxId': format_trx_id(93001), 'status': 'Processing', 'date': 'Demo order'},
        {'order_id': 93002, 'id': format_order_id(93002), 'customer': 'Demo Buyer Two', 'email': 'buyer2@demo.bd', 'items': '2x Demo Clay Vase', 'total': 3600, 'trxId': format_trx_id(93002), 'status': 'Shipped', 'date': 'Demo order'},
        {'order_id': 93003, 'id': format_order_id(93003), 'customer': 'Demo Buyer Three', 'email': 'buyer3@demo.bd', 'items': '1x Demo Bamboo Lamp', 'total': 2450, 'trxId': format_trx_id(93003), 'status': 'Delivered', 'date': 'Demo order'},
    ], key='order_id', minimum=3)
    gi_requests = _mix_demo_rows(gi_requests, [
        {'id': 94001, 'product': 'Demo Jamdani Saree', 'district': 'Narayanganj', 'seller': 'Demo Loom Legacy', 'status': 'pending', 'date': 'Demo request'},
        {'id': 94002, 'product': 'Demo Clay Horse', 'district': 'Comilla', 'seller': 'Demo Terracotta Craft', 'status': 'pending', 'date': 'Demo request'},
        {'id': 94003, 'product': 'Demo Cane Tray', 'district': 'Sylhet', 'seller': 'Demo Cane Craft', 'status': 'pending', 'date': 'Demo request'},
    ], minimum=3)
    return {
        "summary": {
            "revenue": float(revenue),
            "revenue_fmt": fmt_money(revenue),
            "artisans": _safe_int(summary.get("artisans")),
            "gi_products": _safe_int(summary.get("gi_products")),
            "orders": _safe_int(summary.get("orders")),
            "journal_count": _safe_int(summary.get("journal_count")),
            "atlas_active": _safe_int(summary.get("atlas_active")),
            "active_seller_accounts": _safe_int(summary.get("active_seller_accounts")),
            "pending_verifications": _safe_int(summary.get("pending_verifications")),
            "pending_gi": _safe_int(summary.get("pending_gi")),
        },
        "revenue_analytics": revenue_analytics,
        "action_required": action_required,
        "sellers": seller_rows,
        "verification": verification_rows,
        "products": products,
        "orders": orders,
        "gi_requests": gi_requests,
        "journal": journal,
        "atlas": atlas,
        "logs": logs,
        "featured_artisan": featured_artisan,
        "site_experience": {
            **fetch_site_experience_settings(),
            "search_enabled": True,
            "cart_enabled": True,
            "wishlist_enabled": True,
            "atlas_entries": len(atlas),
        },
        "profile_settings": {
            "admin_name": ((db_fetchone("SELECT name, email FROM user_account WHERE user_id=%s", (current_user_id(),)) or {}).get("name") or session.get("name") or "Admin"),
            "role": current_role() or "admin",
            "email": ((db_fetchone("SELECT name, email FROM user_account WHERE user_id=%s", (current_user_id(),)) or {}).get("email") or session.get("email") or ""),
            "pic": (db_fetchone("SELECT avatar_url FROM admin_profile WHERE admin_id=%s", (current_user_id(),)) or {}).get("avatar_url") or "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='-32 -32 320 320'%3E%3Cpath d='M230.92,212c-15.23-26.33-38.7-45.21-66.09-54.16a72,72,0,1,0-73.66,0C63.78,166.78,40.31,185.66,25.08,212a8,8,0,1,0,13.85,8c18.84-32.56,52.14-52,89.07-52s70.23,19.44,89.07,52a8,8,0,1,0,13.85-8ZM72,96a56,56,0,1,1,56,56A56.06,56.06,0,0,1,72,96Z' fill='%23A39A8E'/%3E%3C/svg%3E",
        },
        "messages": db_fetchall(
            """
            SELECT t.thread_id AS id, sp.shop_name AS seller, u.email, t.subject, t.last_message,
                   DATE_FORMAT(t.updated_at, '%d %b %Y, %h:%i %p') AS time
            FROM admin_message_thread t
            JOIN seller_profile sp ON sp.seller_id=t.seller_id
            JOIN user_account u ON u.user_id=sp.seller_id
            ORDER BY t.updated_at DESC, t.thread_id DESC
            LIMIT 100
            """
        ) or [],
        "qc": (db_fetchall(
            """
            SELECT q.qc_id AS id, p.title, sp.shop_name AS seller,
                   DATE_FORMAT(q.created_at, '%d %b %Y, %h:%i %p') AS date,
                   q.status, p.product_id
            FROM admin_qc_item q
            JOIN product p ON p.product_id=q.product_id
            LEFT JOIN seller_profile sp ON sp.seller_id=q.seller_id
            WHERE q.status='Pending'
            ORDER BY q.created_at DESC, q.qc_id DESC
            LIMIT 100
            """
        ) or []),
        "team": db_fetchall(
            "SELECT team_id AS id, name, role, article_count AS art, email FROM admin_team_member WHERE is_active=1 ORDER BY updated_at DESC, team_id DESC LIMIT 100"
        ) or [],
        "featured_queue": featured_queue,
        "users": _mix_demo_rows(db_fetchall(
            """
            SELECT user_id AS id, name, email,
                   CASE role WHEN 'seller' THEN 'Merchant' WHEN 'buyer' THEN 'Buyer' ELSE UPPER(role) END AS role,
                   CASE WHEN is_active THEN 'Active' ELSE 'Banned' END AS status,
                   DATE_FORMAT(COALESCE(updated_at, created_at), '%d %b %Y, %h:%i %p') AS time
            FROM user_account
            WHERE role NOT IN ('admin','superadmin')
            ORDER BY created_at DESC, user_id DESC
            LIMIT 200
            """
        ) or [], [
            {'id': 96001, 'name': 'Demo Buyer One', 'email': 'buyer1@demo.bd', 'role': 'Buyer', 'status': 'Active', 'time': 'Demo data'},
            {'id': 96002, 'name': 'Demo Seller One', 'email': 'seller1@demo.bd', 'role': 'Merchant', 'status': 'Active', 'time': 'Demo data'},
            {'id': 96003, 'name': 'Demo Buyer Two', 'email': 'buyer2@demo.bd', 'role': 'Buyer', 'status': 'Banned', 'time': 'Demo data'},
        ], minimum=3),
        "disputes": db_fetchall(
            "SELECT COALESCE(order_id, dispute_id) AS id, issue, priority, status FROM admin_dispute WHERE status='Open' ORDER BY created_at DESC, dispute_id DESC LIMIT 100"
        ) or [],
        "transactions": transactions,
        "coupons": db_fetchall(
            """
            SELECT coupon_id AS id, code,
                   CASE discount_type
                     WHEN 'Percentage' THEN CONCAT(TRIM(TRAILING '.00' FROM CAST(discount_value AS CHAR)), '%')
                     WHEN 'Fixed Amount' THEN CONCAT('BDT ', TRIM(TRAILING '.00' FROM CAST(discount_value AS CHAR)))
                     ELSE 'Free Delivery'
                   END AS discount,
                   discount_type AS type,
                   COALESCE(usage_limit, 'Unlimited') AS `limit`,
                   used_count AS used,
                   COALESCE(DATE_FORMAT(expires_at, '%Y-%m-%d'), 'Never') AS expires,
                   is_new_user_only AS isNewUser,
                   CASE WHEN is_active THEN 'Active' ELSE 'Paused' END AS status,
                   discount_value,
                   expires_at
            FROM admin_coupon
            ORDER BY created_at DESC, coupon_id DESC
            LIMIT 100
            """
        ) or [],
        "finance_summary": {
            "pending_payouts": _safe_int((db_fetchone("SELECT COUNT(*) AS c FROM payout_request WHERE status='Pending'") or {}).get('c')),
            "pending_amount": float(_safe_decimal((db_fetchone("SELECT COALESCE(SUM(amount_bdt),0) AS s FROM payout_request WHERE status='Pending'") or {}).get('s'))),
        },
        "commission_rules": db_fetchall(
            "SELECT rule_id AS id, title, percentage, is_active FROM admin_commission_rule ORDER BY is_active DESC, rule_id ASC"
        ) or [],
        "artisan_hour": {
            "live": get_setting('artisan_hour_live', '0') == '1',
            "start_date": get_setting('artisan_hour_start_date', datetime.date.today().isoformat()),
            "end_date": get_setting('artisan_hour_end_date', datetime.date.today().isoformat()),
            "start": get_setting('artisan_hour_start', '14:00'),
            "end": get_setting('artisan_hour_end', '16:00'),
            "total_hours_display": get_setting('artisan_hour_total_hours_display', '2h'),
            "start_at": f"{get_setting('artisan_hour_start_date', datetime.date.today().isoformat())}T{get_setting('artisan_hour_start', '14:00')}:00",
            "end_at": f"{get_setting('artisan_hour_end_date', datetime.date.today().isoformat())}T{get_setting('artisan_hour_end', '16:00')}:00",
            "requests": _mix_demo_rows(db_fetchall(
                """
                SELECT a.app_id AS id, a.product_name AS product, sp.shop_name AS seller,
                       COALESCE(p.price_bdt,0) AS old_price,
                       COALESCE(p.price_bdt,0) AS new_price,
                       CASE WHEN a.status='pending' THEN 'Pending' ELSE a.status END AS status
                FROM seller_gi_application a
                JOIN seller_profile sp ON sp.seller_id=a.seller_id
                LEFT JOIN product p ON p.product_id = a.product_id
                WHERE a.status='pending'
                ORDER BY a.submitted_at DESC, a.app_id DESC
                LIMIT 100
                """
            ) or [], [
                {'id': 98001, 'product': 'Demo Jamdani Saree', 'seller': 'Demo Loom Legacy', 'old_price': 6500, 'new_price': 5200, 'status': 'Pending'},
                {'id': 98002, 'product': 'Demo Clay Vase', 'seller': 'Demo Terracotta Craft', 'old_price': 1800, 'new_price': 1500, 'status': 'Pending'},
                {'id': 98003, 'product': 'Demo Cane Tray', 'seller': 'Demo Cane Craft', 'old_price': 2200, 'new_price': 1750, 'status': 'Pending'},
            ], minimum=3),
        },
    }


# -----------------------
# Routes - Currency
# -----------------------
@app.get("/set-currency/<code>")
def set_currency(code: str):
    session["currency"] = "BDT"
    nxt = request.referrer or url_for("shop")
    return redirect(nxt)


# -----------------------
# Public Pages
# -----------------------
@app.get("/")
def home():
    flash_data = fetch_flash_products(limit=12, include_total=True)
    flash_products = flash_data["items"]
    flash_products_total = flash_data["total"]
    uid = current_user_id()
    discovery_data = fetch_discovery_products(limit=20, buyer_id=uid, include_total=True)
    discovery_products = discovery_data["items"]
    discovery_products_total = discovery_data["total"]
    featured_artisan = fetch_featured_artisan()
    journal_featured, journal_side, journal_quote = fetch_journal_home()
    sound_tracks = fetch_soundscape_tracks(limit=8)
    home_slider_products = fetch_home_slider_products()
    home_active_coupons = fetch_active_home_coupons()
    home_stats = fetch_home_stats()
    site_experience = fetch_site_experience_settings()
    return render_template(
        "pages/home.html",
        flash_products=flash_products,
        flash_products_total=flash_products_total,
        discovery_products=discovery_products,
        discovery_products_total=discovery_products_total,
        featured_artisan=featured_artisan,
        journal_featured=journal_featured,
        journal_side=journal_side,
        journal_quote=journal_quote,
        sound_tracks=sound_tracks,
        home_slider_products=home_slider_products,
        home_active_coupons=home_active_coupons,
        home_stats=home_stats,
        site_experience=site_experience,
    )



@app.get("/verify")
def verify_page():
    code = (request.args.get("code") or "").strip()
    result = None
    if code:
        try:
            result = verify_gi_tag(code)
        except Exception:
            result = {"ok": False, "status": "error", "message": "We couldn't verify that code right now. Please try again."}
    return render_template("pages/verify.html", initial_code=code, result=result)


@app.post("/verify")
def verify_submit():
    code = (request.form.get("code") or "").strip()
    try:
        result = verify_gi_tag(code)
    except Exception:
        result = {"ok": False, "status": "error", "message": "We couldn't verify that code right now. Please try again."}
    return render_template("pages/verify.html", initial_code=code, result=result)


@app.post("/api/gi/verify")
def api_verify_gi():
    payload = request.get_json(silent=True) or {}
    code = (payload.get("code") or "").strip()
    try:
        result = verify_gi_tag(code)
    except Exception:
        result = {"ok": False, "status": "error", "message": "Verification service unavailable. Please try again."}
    return jsonify(result)


@app.get("/api/atlas/districts")
def api_atlas_districts():
    """Heritage Atlas dataset (DB-backed).

    Returns the same array shape as static /static/assets/data/districts.json
    so the existing atlas.js UI stays unchanged.
    """

    # Serve from cache when fresh
    now = time.time()
    cached = _ATLAS_CACHE.get("data")
    cached_ts = float(_ATLAS_CACHE.get("ts") or 0.0)
    cached_etag = _ATLAS_CACHE.get("etag")
    if cached is not None and (now - cached_ts) < _ATLAS_CACHE_TTL_SECONDS:
        # Conditional GET support
        inm = request.headers.get("If-None-Match")
        if inm and cached_etag and inm == cached_etag:
            return ("", 304, {"ETag": cached_etag, "Cache-Control": f"public, max-age={_ATLAS_CACHE_TTL_SECONDS}"})
        return (jsonify(cached), 200, {"ETag": cached_etag or "", "Cache-Control": f"public, max-age={_ATLAS_CACHE_TTL_SECONDS}"})

    # Build fresh payload
    rows = db_fetchall(
        """
        SELECT
            d.district_id,
            d.name AS zilla,
            a.density,
            a.product_name AS product,
            a.category AS category,
            a.story,
            a.image_url AS image,
            a.shop_link,
            a.dot_x,
            a.dot_y
        FROM district d
        LEFT JOIN district_atlas a ON a.district_id=d.district_id AND a.is_active=TRUE
        ORDER BY d.name ASC
        """
    )

    default_story = (
        "Currently, this district does not have an officially registered "
        "Geographical Indication (GI) product of Bangladesh."
    )
    payload: List[Dict[str, Any]] = []
    for r in rows:
        density = r.get("density") or "low"
        product = r.get("product") or "No Official GI Product"
        category = r.get("category") or "N/A"
        story = r.get("story") or default_story
        image = r.get("image") or ""
        shop_link = r.get("shop_link") or ("#" if product == "No Official GI Product" else f"/shop?district={quote(r.get('zilla') or '')}")

        dot_x = r.get("dot_x")
        dot_y = r.get("dot_y")
        dot_obj = {"x": float(dot_x), "y": float(dot_y)} if dot_x is not None and dot_y is not None else {"x": 0.0, "y": 0.0}

        payload.append(
            {
                "zilla": r.get("zilla"),
                "density": density,
                "product": product,
                "category": category,
                "story": story,
                "image": image,
                "shop_link": shop_link,
                "dot": dot_obj,
            }
        )

    # Cache + ETag
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    etag = 'W/"' + hashlib.md5(raw).hexdigest() + '"'
    _ATLAS_CACHE["ts"] = now
    _ATLAS_CACHE["data"] = payload
    _ATLAS_CACHE["etag"] = etag

    inm = request.headers.get("If-None-Match")
    if inm and inm == etag:
        return ("", 304, {"ETag": etag, "Cache-Control": f"public, max-age={_ATLAS_CACHE_TTL_SECONDS}"})
    return (jsonify(payload), 200, {"ETag": etag, "Cache-Control": f"public, max-age={_ATLAS_CACHE_TTL_SECONDS}"})



@app.get("/shop")
def shop():
    q = (request.args.get("q") or "").strip()
    category = (request.args.get("category") or "").strip()
    sub = (request.args.get("sub") or "").strip()
    district = (request.args.get("district") or "").strip()
    artisan = (request.args.get("artisan") or "").strip()

    # Resolve category/subcategory ids
    params: List[Any] = []
    where: List[str] = ["p.is_active=TRUE"]

    if q:
        where.append("(p.title LIKE %s OR p.description LIKE %s)")
        like = f"%{q}%"
        params.extend([like, like])

    if category:
        where.append("c.name=%s")
        params.append(category)

    if sub:
        where.append("sc.name=%s")
        params.append(sub)

    if district:
        # District names come from the Heritage Atlas map (e.g., "Mymensingh").
        # We filter by district table name.
        where.append("d.name=%s")
        params.append(district)

    join_artisan = ""
    if artisan:
        try:
            artisan_id = int(artisan)
        except ValueError:
            artisan_id = 0
        if artisan_id > 0:
            join_artisan = "JOIN artisan_product ap ON ap.product_id=p.product_id"
            where.append("ap.artisan_id=%s")
            params.append(artisan_id)

    sql = f"""
        SELECT
            p.product_id, p.title, p.price_bdt, p.stock, p.image_path,
            c.name AS category_name,
            sc.name AS subcategory_name,
            d.name AS district_name
        FROM product p
        {join_artisan}
        JOIN category c ON c.category_id=p.category_id
        LEFT JOIN subcategory sc ON sc.subcategory_id=p.subcategory_id
        LEFT JOIN district d ON d.district_id=p.district_id
        WHERE {" AND ".join(where)}
        ORDER BY p.created_at DESC
        LIMIT 60
    """
    products = db_fetchall(sql, tuple(params))

    # Mark wished for current buyer (for heart button)
    wished_ids = set()
    uid = current_user_id()
    if uid and current_role() == "buyer":
        wrows = db_fetchall("SELECT product_id FROM wishlist WHERE buyer_id=%s", (uid,))
        wished_ids = {int(r["product_id"]) for r in wrows}

    for p in products:
        p["price_fmt"] = fmt_money(Decimal(str(p["price_bdt"])))
        p["is_wished"] = int(p["product_id"]) in wished_ids

    return render_template(
        "pages/shop.html",
        products=products,
        q=q,
        active_category=category,
        active_sub=sub,
        active_district=district,
    )




@app.route('/admin/resend-otp', methods=['POST'])
def admin_resend_otp():
    email = request.form.get('email')
    
    flash('A new OTP has been sent to your email.', 'success')
    return render_template('admin_login.html', step='verify', email=email, role_label='Admin')

@app.route('/superadmin/resend-otp', methods=['POST'])
def superadmin_resend_otp():
    email = request.form.get('email')
    
    flash('A new OTP has been sent to your email.', 'success')
    return render_template('admin_login.html', step='verify', email=email, role_label='Super Admin', is_super=True)
@app.get("/flash-deals")
def flash_deals():
    flash_products = fetch_flash_products(limit=None)
    return render_template("pages/flash-deals.html", flash_products=flash_products)


@app.get("/api/artisan-hour")
def api_artisan_hour_public():
    runtime = sync_artisan_hour_runtime()
    start_date = (get_setting("artisan_hour_start_date", datetime.date.today().isoformat()) or "").strip()
    end_date = (get_setting("artisan_hour_end_date", datetime.date.today().isoformat()) or "").strip()
    start = (get_setting("artisan_hour_start", "14:00") or "14:00").strip()[:5]
    end = (get_setting("artisan_hour_end", "16:00") or "16:00").strip()[:5]
    total_hours_display = (get_setting("artisan_hour_total_hours_display", "") or "").strip()
    start_at = f"{start_date}T{start}:00" if start_date and start else ""
    end_at = f"{end_date}T{end}:00" if end_date and end else ""
    return jsonify({
        "ok": True,
        "live": runtime["live"],
        "start_date": start_date,
        "end_date": end_date,
        "start": start,
        "end": end,
        "start_at": start_at,
        "end_at": end_at,
        "total_hours_display": total_hours_display,
        "duration_seconds": runtime["duration_seconds"],
        "remaining_seconds": runtime["remaining_seconds"],
        "live_started_at": runtime["live_started_at"],
    })

@app.get("/product/<int:product_id>")
def product_details(product_id: int):
    sql = """
        SELECT
            p.product_id, p.title, p.description, p.price_bdt, p.stock, p.image_path,
            c.name AS category_name,
            sc.name AS subcategory_name,
            d.name AS district_name
        FROM product p
        JOIN category c ON c.category_id=p.category_id
        LEFT JOIN subcategory sc ON sc.subcategory_id=p.subcategory_id
        LEFT JOIN district d ON d.district_id=p.district_id
        WHERE p.product_id=%s AND p.is_active=TRUE
        LIMIT 1
    """
    p = db_fetchone(sql, (product_id,))
    if not p:
        abort(404)

    p["price_fmt"] = fmt_money(Decimal(str(p["price_bdt"])))

    uid = current_user_id()
    is_wished = False
    if uid and current_role() == "buyer":
        row = db_fetchone("SELECT 1 AS x FROM wishlist WHERE buyer_id=%s AND product_id=%s", (uid, product_id))
        is_wished = bool(row)

    return render_template("pages/product-details.html", product=p, is_wished=is_wished)



# -----------------------
# GI Journal Routes (Premium)
# -----------------------
@app.get("/journal")
def journal_index():
    # Filters
    page = request.args.get("page", "1")
    category = (request.args.get("category") or "").strip()
    archive = (request.args.get("archive") or "").strip()

    featured = fetch_journal_featured_for_index()
    featured_id = int(featured["article_id"]) if featured and featured.get("article_id") else None

    categories = fetch_journal_categories()
    archives = fetch_journal_archives()

    pager = fetch_journal_index_page(
        page=int(page) if str(page).isdigit() else 1,
        per_page=9,
        category=category,
        archive=archive,
        exclude_article_id=featured_id,
    )

    # Jinja resolves dict attributes like `.items` to the dict method instead of the "items" key.
    # Convert to an attribute object so templates can safely access `pager.items`.
    pager = SimpleNamespace(**pager)

    # Simple SEO defaults
    meta = {
        "title": "The GI Journal | Origins Bangladesh",
        "description": "Long-form chapters on craft, place, and provenance — curated to deepen every discovery.",
        "image": (featured.get("hero_image_url") if featured else ""),
    }

    return render_template(
        "pages/journal/index.html",
        featured=featured,
        categories=categories,
        archives=archives,
        pager=pager,
        meta=meta,
    )

@app.get("/journal/<slug>")
def journal_article(slug: str):
    article = fetch_article_by_slug(slug)
    if not article:
        abort(404)
    return render_template(
        "pages/journal/article.html",
        article=article,
        user_id=current_user_id(),
    )





@app.get("/heritage-atlas")
def heritage_atlas():
    # You can use ?district=... in template; existing UI already supports this
    return render_template("pages/heritage-atlas.html")





# -----------------------
# Informational Pages (Footer)
# -----------------------
@app.get("/info/heirlooms")
def info_heirlooms():
    return render_template("pages/info/heirlooms.html")


@app.get("/info/essentials")
def info_essentials():
    return render_template("pages/info/essentials.html")


@app.get("/info/curios")
def info_curios():
    return render_template("pages/info/curios.html")


@app.get("/info/masterpieces")
def info_masterpieces():
    return render_template("pages/info/masterpieces.html")


@app.get("/support/track-order")
def support_track_order():
    return render_template("pages/support/track-order.html")


@app.get("/support/shipping-returns")
def support_shipping_returns():
    return render_template("pages/support/shipping-returns.html")


@app.get("/support/help-center")
def support_help_center():
    return render_template("pages/support/help-center.html")


@app.get("/business/wholesale")
def business_wholesale():
    return render_template("pages/business/wholesale-b2b.html")


@app.get("/impact/artisan-welfare")
def impact_artisan_welfare():
    return render_template("pages/impact/artisan-welfare.html")


@app.get("/impact/sustainability")
def impact_sustainability():
    return render_template("pages/impact/sustainability.html")


@app.get("/legal/privacy-terms")
def legal_privacy_terms():
    return render_template("pages/legal/privacy-terms.html")


# -----------------------
# Wishlist (Buyer)
# -----------------------
@app.post("/wishlist/toggle/<int:product_id>")
def wishlist_toggle(product_id: int):
    redir = request.form.get("next") or request.referrer or url_for("shop")
    gate = require_buyer()
    if gate:
        return gate

    uid = current_user_id()
    assert uid is not None

    exists = db_fetchone("SELECT wishlist_id FROM wishlist WHERE buyer_id=%s AND product_id=%s", (uid, product_id))
    if exists:
        db_execute("DELETE FROM wishlist WHERE buyer_id=%s AND product_id=%s", (uid, product_id))
        flash("Removed from wishlist.", "success")
    else:
        db_execute("INSERT INTO wishlist(buyer_id, product_id) VALUES (%s,%s)", (uid, product_id))
        flash("Added to wishlist.", "success")

    return redirect(redir)


@app.get("/wishlist")
def wishlist():
    gate = require_buyer()
    if gate:
        return gate

    uid = current_user_id()
    assert uid is not None

    sql = """
        SELECT
            w.created_at,
            p.product_id, p.title, p.price_bdt, p.image_path, p.stock,
            c.name AS category_name,
            sc.name AS subcategory_name,
            d.name AS district_name
        FROM wishlist w
        JOIN product p ON p.product_id=w.product_id
        JOIN category c ON c.category_id=p.category_id
        LEFT JOIN subcategory sc ON sc.subcategory_id=p.subcategory_id
        LEFT JOIN district d ON d.district_id=p.district_id
        WHERE w.buyer_id=%s AND p.is_active=TRUE
        ORDER BY w.created_at DESC
    """
    items = db_fetchall(sql, (uid,))
    for it in items:
        it["price_fmt"] = fmt_money(Decimal(str(it["price_bdt"])))

    return render_template("pages/wishlist.html", items=items)


# -----------------------
# Cart (Buyer)
# -----------------------
@app.post("/cart/add/<int:product_id>")
def cart_add(product_id: int):
    gate = require_buyer()
    if gate:
        return gate

    uid = current_user_id()
    assert uid is not None
    cart_id = ensure_cart(uid)

    qty_raw = request.form.get("qty", "1").strip()
    try:
        qty = max(1, min(99, int(qty_raw)))
    except ValueError:
        qty = 1

    # Validate product stock
    prow = db_fetchone("SELECT stock, is_active FROM product WHERE product_id=%s", (product_id,))
    if not prow or not prow.get("is_active"):
        abort(404)
    stock = int(prow.get("stock") or 0)
    if stock <= 0:
        flash("Out of stock.", "warning")
        return redirect(request.referrer or url_for("shop"))

    # Upsert
    existing = db_fetchone("SELECT quantity FROM cart_item WHERE cart_id=%s AND product_id=%s", (cart_id, product_id))
    if existing:
        new_qty = min(stock, int(existing["quantity"]) + qty)
        db_execute(
            "UPDATE cart_item SET quantity=%s WHERE cart_id=%s AND product_id=%s",
            (new_qty, cart_id, product_id),
        )
    else:
        qty = min(stock, qty)
        db_execute(
            "INSERT INTO cart_item(cart_id, product_id, quantity) VALUES (%s,%s,%s)",
            (cart_id, product_id, qty),
        )

    flash("Added to cart.", "success")
    return redirect(request.form.get("next") or request.referrer or url_for("cart"))


@app.post("/cart/update")
def cart_update():
    gate = require_buyer()
    if gate:
        return gate

    uid = current_user_id()
    assert uid is not None
    cart_id = ensure_cart(uid)

    # quantities dict: qty_<product_id>
    for key, val in request.form.items():
        if not key.startswith("qty_"):
            continue
        try:
            pid = int(key.split("_", 1)[1])
        except Exception:
            continue
        try:
            qty = int(val)
        except ValueError:
            qty = 1
        qty = max(0, min(99, qty))
        if qty == 0:
            db_execute("DELETE FROM cart_item WHERE cart_id=%s AND product_id=%s", (cart_id, pid))
        else:
            # cap to stock
            prow = db_fetchone("SELECT stock FROM product WHERE product_id=%s", (pid,))
            stock = int((prow or {}).get("stock") or 0)
            qty = min(qty, max(stock, 0) if stock else qty)
            db_execute(
                "UPDATE cart_item SET quantity=%s WHERE cart_id=%s AND product_id=%s",
                (qty, cart_id, pid),
            )

    flash("Cart updated.", "success")
    return redirect(url_for("cart"))


@app.post("/cart/remove/<int:product_id>")
def cart_remove(product_id: int):
    gate = require_buyer()
    if gate:
        return gate

    uid = current_user_id()
    assert uid is not None
    cart_id = ensure_cart(uid)
    db_execute("DELETE FROM cart_item WHERE cart_id=%s AND product_id=%s", (cart_id, product_id))
    flash("Removed item from cart.", "success")
    return redirect(url_for("cart"))


@app.get("/cart")
def cart():
    gate = require_buyer()
    if gate:
        return gate

    uid = current_user_id()
    assert uid is not None
    cart_id = ensure_cart(uid)

    sql = """
        SELECT
            ci.product_id, ci.quantity,
            p.title, p.price_bdt, p.stock, p.image_path,
            c.name AS category_name
        FROM cart_item ci
        JOIN product p ON p.product_id=ci.product_id
        JOIN category c ON c.category_id=p.category_id
        WHERE ci.cart_id=%s AND p.is_active=TRUE
        ORDER BY ci.created_at DESC
    """
    items = db_fetchall(sql, (cart_id,))
    total_bdt = Decimal("0")
    for it in items:
        price = Decimal(str(it["price_bdt"]))
        line = price * Decimal(int(it["quantity"]))
        it["price_fmt"] = fmt_money(price)
        it["line_total_fmt"] = fmt_money(line)
        total_bdt += line

    return render_template(
        "pages/cart.html",
        items=items,
        total_fmt=fmt_money(total_bdt),
        total_bdt=total_bdt,
    )


# -----------------------
# Checkout (placeholder flow)
# -----------------------
@app.get("/checkout")
def checkout():
    gate = require_buyer()
    if gate:
        return gate
    uid = current_user_id()
    assert uid is not None
    coupon_code = (request.args.get("coupon") or "").strip()
    country = (request.args.get("country") or "BD").strip().upper()
    payment_method = (request.args.get("payment_method") or "sslcommerz").strip().lower()
    summary = build_checkout_summary(uid, coupon_code=coupon_code, country=country, payment_method=payment_method)
    try:
        user = db_fetchone("SELECT name, email, phone FROM user_account WHERE user_id=%s LIMIT 1", (uid,)) or {}
        buyer_profile = db_fetchone("SELECT address FROM buyer_profile WHERE buyer_id=%s LIMIT 1", (uid,)) or {}
    except Exception:
        user = {}
        buyer_profile = {}
    if not summary["items"]:
        flash("Your cart is empty. Add something beautiful before checkout.", "warning")
        return redirect(url_for("cart"))
    return render_template(
        "pages/checkout.html",
        cart_items=summary["items"],
        subtotal=summary["subtotal_bdt"],
        subtotal_fmt=summary["subtotal_fmt"],
        shipping_bdt=summary["shipping_bdt"],
        shipping_fmt=summary["shipping_fmt"],
        cod_fee_bdt=summary["cod_fee_bdt"],
        cod_fee_fmt=summary["cod_fee_fmt"],
        discount_bdt=summary["discount_bdt"],
        discount_fmt=summary["discount_fmt"],
        total_bdt=summary["total_bdt"],
        total_fmt=summary["total_fmt"],
        applied_coupon=summary["coupon"],
        coupon_code=summary["coupon_code"],
        coupon_error=summary["coupon_error"],
        selected_country=summary["country"],
        selected_payment_method=summary["payment_method"],
        buyer_name=user.get("name") or session.get("name") or "",
        buyer_email=user.get("email") or "",
        buyer_phone=user.get("phone") or "",
        buyer_address=buyer_profile.get("address") or "",
        process_checkout=True,
    )


@app.post("/api/checkout/apply-coupon")
def api_checkout_apply_coupon():
    gate = require_buyer()
    if gate:
        return jsonify({"ok": False, "message": "Please sign in as buyer."}), 401
    uid = current_user_id()
    payload = request.get_json(silent=True) or {}
    coupon_code = (payload.get("coupon_code") or payload.get("code") or "").strip()
    country = (payload.get("country") or "BD").strip().upper()
    payment_method = (payload.get("payment_method") or "sslcommerz").strip().lower()
    summary = build_checkout_summary(int(uid or 0), coupon_code=coupon_code, country=country, payment_method=payment_method)
    body = {
        "subtotal_bdt": float(summary["subtotal_bdt"]),
        "shipping_bdt": float(summary["shipping_bdt"]),
        "cod_fee_bdt": float(summary["cod_fee_bdt"]),
        "discount_bdt": float(summary["discount_bdt"]),
        "total_bdt": float(summary["total_bdt"]),
        "subtotal_fmt": summary["subtotal_fmt"],
        "shipping_fmt": summary["shipping_fmt"],
        "cod_fee_fmt": summary["cod_fee_fmt"],
        "discount_fmt": summary["discount_fmt"],
        "total_fmt": summary["total_fmt"],
    }
    if summary["coupon_error"]:
        return jsonify({"ok": False, "message": summary["coupon_error"], "summary": body}), 400
    return jsonify({"ok": True, "message": f"Coupon {summary['coupon']['code']} applied.", "summary": body, "coupon": summary["coupon"]})


@app.post("/checkout/process")
def process_checkout():
    gate = require_buyer()
    if gate:
        return gate
    buyer_id = int(current_user_id() or 0)
    country = (request.form.get("country") or "BD").strip().upper()
    payment_method = (request.form.get("payment_method") or "sslcommerz").strip().lower()
    coupon_code = (request.form.get("discount_code") or "").strip()
    summary = build_checkout_summary(buyer_id, coupon_code=coupon_code, country=country, payment_method=payment_method)
    if not summary["items"]:
        flash("Your cart is empty.", "warning")
        return redirect(url_for("cart"))
    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)
        for item in summary["items"]:
            cur.execute("SELECT stock, price_bdt, title FROM product WHERE product_id=%s FOR UPDATE", (item["product_id"],))
            prow = cur.fetchone() or {}
            if int(prow.get("stock") or 0) < int(item["quantity"]):
                raise ValueError(f"Insufficient stock for {prow.get('title') or item['name']}.")
        order_status = 'pending' if payment_method == 'cod' else 'paid'
        payment_status = 'pending' if payment_method == 'cod' else 'paid'
        shipping_name = f"{(request.form.get('first_name') or '').strip()} {(request.form.get('last_name') or '').strip()}".strip()
        cur.execute(
            """
            INSERT INTO `order`
            (buyer_id, status, subtotal_bdt, shipping_bdt, discount_bdt, coupon_id, total_bdt, payment_status, payment_method,
             shipping_name, shipping_phone, shipping_email, shipping_address_line, shipping_apartment, shipping_country, shipping_city, postal_code, invoice_no, placed_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())
            """,
            (
                buyer_id, order_status, summary['subtotal_bdt'], summary['shipping_bdt'] + summary['cod_fee_bdt'],
                summary['discount_bdt'], int(summary['coupon'].get('coupon_id')) if summary['coupon'] else None,
                summary['total_bdt'], payment_status, payment_method, shipping_name,
                (request.form.get('phone') or '').strip(), (request.form.get('email') or '').strip(),
                (request.form.get('address') or '').strip(), (request.form.get('apartment') or '').strip(),
                country, (request.form.get('city') or '').strip(), (request.form.get('postal_code') or '').strip(), ''
            ),
        )
        order_id = int(cur.lastrowid or 0)
        invoice_no = format_prefixed_id('INV', order_id, 6)
        cur.execute("UPDATE `order` SET invoice_no=%s WHERE order_id=%s", (invoice_no, order_id))
        item_points = 0
        for item in summary['items']:
            cur.execute("INSERT INTO order_item (order_id, product_id, quantity, unit_price_bdt) VALUES (%s,%s,%s,%s)", (order_id, item['product_id'], item['quantity'], item['price_bdt']))
            order_item_id = int(cur.lastrowid or 0)
            cur.execute("UPDATE product SET stock=stock-%s WHERE product_id=%s", (item['quantity'], item['product_id']))
            item_points += int(item['quantity']) * 10
            try:
                cur.execute("INSERT INTO order_provenance_event (order_item_id, event_type, title, description, actor_type, metadata_json) VALUES (%s,%s,%s,%s,'system',%s)", (order_item_id, 'order_placed', 'Order placed', 'Your item was reserved and secured in our archive.', json.dumps({"product_id": item['product_id']})))
                cur.execute("INSERT INTO order_provenance_event (order_item_id, event_type, title, description, actor_type, metadata_json) VALUES (%s,%s,%s,%s,'system',%s)", (order_item_id, 'artisan_confirmed', 'Artisan assigned', ((item.get('artisan_name') or 'Verified artisan') + ' has been linked to this piece.'), json.dumps({"product_id": item['product_id']})))
                cur.execute("INSERT INTO order_provenance_event (order_item_id, event_type, title, description, actor_type, metadata_json) VALUES (%s,%s,%s,%s,'system',%s)", (order_item_id, 'quality_checked', 'Quality promise', 'This item will pass through Origins quality review before dispatch.', json.dumps({"product_id": item['product_id']})))
            except Exception:
                pass
        try:
            cur.execute("INSERT INTO order_status_history (order_id, status, note, actor_type) VALUES (%s,%s,%s,'system')", (order_id, order_status, 'Order created from checkout'))
        except Exception:
            pass
        if summary['coupon']:
            coupon_id = int(summary['coupon'].get('coupon_id') or 0)
            cur.execute("UPDATE admin_coupon SET used_count=used_count+1 WHERE coupon_id=%s", (coupon_id,))
            try:
                cur.execute("INSERT INTO coupon_redemption (coupon_id, buyer_id, order_id, discount_amount) VALUES (%s,%s,%s,%s)", (coupon_id, buyer_id, order_id, summary['discount_bdt']))
            except Exception:
                pass
        cur.execute("DELETE ci FROM cart_item ci JOIN cart c ON c.cart_id=ci.cart_id WHERE c.buyer_id=%s", (buyer_id,))
        if order_status == 'delivered':
            try:
                cur.execute("INSERT INTO buyer_point_ledger (buyer_id, order_id, points_delta, reason) VALUES (%s,%s,%s,'purchase')", (buyer_id, order_id, item_points))
            except Exception:
                pass
        conn.commit()
        sync_buyer_points(buyer_id)
        try:
            send_order_status_email(order_id, order_status, 'Your order has been confirmed successfully.')
        except Exception:
            pass
        flash(f"Order {format_order_id(order_id)} placed successfully.", "success")
        return redirect(url_for('buyer_dashboard', view='checkout-success'))
    except Exception as e:
        conn.rollback()
        flash(str(e) or 'Checkout failed. Please try again.', 'danger')
        return redirect(url_for('checkout', coupon=coupon_code, country=country, payment_method=payment_method))
    finally:
        try:
            conn.close()
        except Exception:
            pass


# -----------------------
# Auth
# -----------------------

@app.route("/auth/login", methods=["GET", "POST"])
def login():
    # Buyer & Seller login only (Admin/Superadmin will have a separate portal later)
    if request.method == "GET":
        return render_template("pages/auth/login.html", step="start")

    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    next_url = request.form.get("next") or request.args.get("next") or ""
    if next_url and not next_url.startswith("/"):
        next_url = ""

    if not email or not password:
        flash("Email and password are required.", "warning")
        return render_template("pages/auth/login.html", step="start", email=email, next_url=next_url)

    user = db_fetchone(
        "SELECT user_id, role, name, password_hash, is_email_verified, is_active FROM user_account WHERE email=%s",
        (email,),
    )

    generic_fail = "Incorrect email or password."

    if not user or not user.get("is_active", True):
        flash(generic_fail, "danger")
        return render_template("pages/auth/login.html", step="start", email=email, next_url=next_url)

    role = (user.get("role") or "").lower()
    if role not in ("buyer", "seller"):
        flash("This login is for buyers and sellers only. Admin login will be available separately.", "warning")
        return render_template("pages/auth/login.html", step="start", email=email, next_url=next_url)

    if not user.get("password_hash") or not check_password_hash(user["password_hash"], password):
        flash(generic_fail, "danger")
        return render_template("pages/auth/login.html", step="start", email=email, next_url=next_url)

    if not user.get("is_email_verified", False):
        otp, _ = create_auth_challenge(email=email, purpose="verify", user_id=int(user["user_id"]))
        send_otp_email(email=email, purpose="verify", otp=otp)
        flash("Please verify your email first. We sent a verification code.", "info")
        return redirect(url_for("register", role=role))

    otp, _ = create_auth_challenge(email=email, purpose="login", user_id=int(user["user_id"]))
    send_otp_email(email=email, purpose="login", otp=otp)

    flash("We sent a verification code to your email.", "success")
    return render_template("pages/auth/login.html", step="verify", email=email, next_url=next_url)


@app.post("/auth/login/verify")
def login_verify():
    email = (request.form.get("email") or "").strip().lower()
    otp = (request.form.get("otp") or "").strip()
    next_url = request.form.get("next") or ""
    if next_url and not next_url.startswith("/"):
        next_url = ""

    if not email or not otp:
        flash("Please enter the code we sent to your email.", "warning")
        return render_template("pages/auth/login.html", step="verify", email=email, next_url=next_url)

    row = consume_auth_challenge(email=email, purpose="login", otp=otp)
    if not row:
        flash("Invalid or expired code. Please try again.", "danger")
        return render_template("pages/auth/login.html", step="verify", email=email, next_url=next_url)

    user = db_fetchone("SELECT user_id, role, name, is_active FROM user_account WHERE email=%s", (email,))
    if not user or not user.get("is_active", True):
        flash("Account not available.", "danger")
        return redirect(url_for("login"))

    role = (user.get("role") or "").lower()
    if role not in ("buyer", "seller"):
        flash("This login is for buyers and sellers only.", "warning")
        return redirect(url_for("login"))

    session["user_id"] = int(user["user_id"])
    session["role"] = role
    session["name"] = user.get("name") or ""
    if role == "seller":
        _ensure_seller_session_state(int(user["user_id"]))

    if next_url:
        return redirect(next_url)

    return redirect(url_for("buyer_dashboard" if role == "buyer" else "seller_dashboard"))


@app.route("/auth/admin/login", methods=["GET", "POST"])
def admin_login():
    """Admin login: Email + Password + Email OTP + Secret Code"""
    if request.method == "GET":
        return render_template("pages/auth/admin_login.html", step="start", role_label="Admin")

    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    next_url = request.form.get("next") or request.args.get("next") or ""
    if next_url and not next_url.startswith("/"):
        next_url = ""

    if not email or not password:
        flash("Email and password are required.", "warning")
        return render_template("pages/auth/admin_login.html", step="start", email=email, next_url=next_url, role_label="Admin")

    user = db_fetchone(
        "SELECT user_id, role, name, password_hash, is_email_verified, is_active, secret_code_hash FROM user_account WHERE email=%s",
        (email,),
    )

    generic_fail = "Incorrect email or password."
    if not user or not user.get("is_active", True):
        flash(generic_fail, "danger")
        log_security_event("failed_login", severity="warn", actor_email=email, message="admin_login_user_not_found_or_inactive")
        maybe_send_failed_login_alert(actor_email=email)
        return render_template("pages/auth/admin_login.html", step="start", email=email, next_url=next_url, role_label="Admin")

    role = (user.get("role") or "").lower()
    if role != "admin":
        flash("This portal is for Admin users only.", "warning")
        log_security_event("failed_login", severity="warn", actor_email=email, message="admin_login_wrong_role", meta={"role": role})
        maybe_send_failed_login_alert(actor_email=email)
        return render_template("pages/auth/admin_login.html", step="start", email=email, next_url=next_url, role_label="Admin")

    if not user.get("password_hash") or not check_password_hash(user["password_hash"], password):
        flash(generic_fail, "danger")
        log_security_event("failed_login", severity="warn", actor_email=email, message="admin_login_bad_password")
        maybe_send_failed_login_alert(actor_email=email)
        return render_template("pages/auth/admin_login.html", step="start", email=email, next_url=next_url, role_label="Admin")

    if not user.get("is_email_verified", False):
        otp, _ = create_auth_challenge(email=email, purpose="verify", user_id=int(user["user_id"]))
        send_otp_email(email=email, purpose="verify", otp=otp)
        flash("Please verify your email first. We sent a verification code.", "info")
        return redirect(url_for("register", role="buyer"))

    otp, _ = create_auth_challenge(email=email, purpose="admin_login", user_id=int(user["user_id"]))
    send_otp_email(email=email, purpose="admin_login", otp=otp)
    flash("We sent a verification code to your email.", "success")
    return render_template("pages/auth/admin_login.html", step="verify", email=email, next_url=next_url, role_label="Admin")


@app.post("/auth/admin/login/verify")
def admin_login_verify():
    email = (request.form.get("email") or "").strip().lower()
    otp = (request.form.get("otp") or "").strip()
    secret_code = (request.form.get("secret_code") or "").strip()
    next_url = request.form.get("next") or ""
    if next_url and not next_url.startswith("/"):
        next_url = ""

    if not email or not otp or not secret_code:
        flash("OTP and secret code are required.", "warning")
        return render_template("pages/auth/admin_login.html", step="verify", email=email, next_url=next_url, role_label="Admin")

    row = consume_auth_challenge(email=email, purpose="admin_login", otp=otp)
    if not row:
        flash("Invalid or expired code. Please try again.", "danger")
        log_security_event("failed_login", severity="warn", actor_email=email, message="admin_login_bad_otp")
        maybe_send_failed_login_alert(actor_email=email)
        return render_template("pages/auth/admin_login.html", step="verify", email=email, next_url=next_url, role_label="Admin")

    user = db_fetchone(
        "SELECT user_id, role, name, is_active, secret_code_hash FROM user_account WHERE email=%s",
        (email,),
    )
    if not user or not user.get("is_active", True) or (user.get("role") or "").lower() != "admin":
        flash("Account not available.", "danger")
        return redirect(url_for("admin_login"))

    if not verify_secret_code(user=user, provided=secret_code, role="admin"):
        flash("Invalid secret code. Please contact Super Admin.", "danger")
        log_security_event("failed_login", severity="warn", actor_email=email, message="admin_login_bad_secret")
        maybe_send_failed_login_alert(actor_email=email)
        return render_template("pages/auth/admin_login.html", step="verify", email=email, next_url=next_url, role_label="Admin")

    session["user_id"] = int(user["user_id"])
    session["role"] = "admin"
    session["name"] = user.get("name") or ""
    session["email"] = email
    return redirect(next_url or url_for("admin_dashboard"))


@app.route("/auth/superadmin/login", methods=["GET", "POST"])
def superadmin_login():
    """Superadmin login: Email + Password + Email OTP + Secret Code"""
    if request.method == "GET":
        return render_template("pages/auth/admin_login.html", step="start", role_label="Super Admin", is_super=True)

    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    next_url = request.form.get("next") or request.args.get("next") or ""
    if next_url and not next_url.startswith("/"):
        next_url = ""

    if not email or not password:
        flash("Email and password are required.", "warning")
        return render_template("pages/auth/admin_login.html", step="start", email=email, next_url=next_url, role_label="Super Admin", is_super=True)

    user = db_fetchone(
        "SELECT user_id, role, name, password_hash, is_email_verified, is_active, secret_code_hash FROM user_account WHERE email=%s",
        (email,),
    )

    generic_fail = "Incorrect email or password."
    if not user or not user.get("is_active", True):
        flash(generic_fail, "danger")
        log_security_event("failed_login", severity="warn", actor_email=email, message="superadmin_login_user_not_found_or_inactive")
        maybe_send_failed_login_alert(actor_email=email)
        return render_template("pages/auth/admin_login.html", step="start", email=email, next_url=next_url, role_label="Super Admin", is_super=True)

    role = (user.get("role") or "").lower()
    if role != "superadmin":
        flash("This portal is for Super Admin users only.", "warning")
        log_security_event("failed_login", severity="warn", actor_email=email, message="superadmin_login_wrong_role", meta={"role": role})
        maybe_send_failed_login_alert(actor_email=email)
        return render_template("pages/auth/admin_login.html", step="start", email=email, next_url=next_url, role_label="Super Admin", is_super=True)

    if not user.get("password_hash") or not check_password_hash(user["password_hash"], password):
        flash(generic_fail, "danger")
        log_security_event("failed_login", severity="warn", actor_email=email, message="superadmin_login_bad_password")
        maybe_send_failed_login_alert(actor_email=email)
        return render_template("pages/auth/admin_login.html", step="start", email=email, next_url=next_url, role_label="Super Admin", is_super=True)

    if not user.get("is_email_verified", False):
        otp, _ = create_auth_challenge(email=email, purpose="verify", user_id=int(user["user_id"]))
        send_otp_email(email=email, purpose="verify", otp=otp)
        flash("Please verify your email first. We sent a verification code.", "info")
        return redirect(url_for("register", role="buyer"))

    otp, _ = create_auth_challenge(email=email, purpose="superadmin_login", user_id=int(user["user_id"]))
    send_otp_email(email=email, purpose="superadmin_login", otp=otp)
    flash("We sent a verification code to your email.", "success")
    return render_template("pages/auth/admin_login.html", step="verify", email=email, next_url=next_url, role_label="Super Admin", is_super=True)


@app.post("/auth/superadmin/login/verify")
def superadmin_login_verify():
    email = (request.form.get("email") or "").strip().lower()
    otp = (request.form.get("otp") or "").strip()
    secret_code = (request.form.get("secret_code") or "").strip()
    next_url = request.form.get("next") or ""
    if next_url and not next_url.startswith("/"):
        next_url = ""

    if not email or not otp or not secret_code:
        flash("OTP and secret code are required.", "warning")
        return render_template("pages/auth/admin_login.html", step="verify", email=email, next_url=next_url, role_label="Super Admin", is_super=True)

    row = consume_auth_challenge(email=email, purpose="superadmin_login", otp=otp)
    if not row:
        flash("Invalid or expired code. Please try again.", "danger")
        log_security_event("failed_login", severity="warn", actor_email=email, message="superadmin_login_bad_otp")
        maybe_send_failed_login_alert(actor_email=email)
        return render_template("pages/auth/admin_login.html", step="verify", email=email, next_url=next_url, role_label="Super Admin", is_super=True)

    user = db_fetchone(
        "SELECT user_id, role, name, is_active, secret_code_hash FROM user_account WHERE email=%s",
        (email,),
    )
    if not user or not user.get("is_active", True) or (user.get("role") or "").lower() != "superadmin":
        flash("Account not available.", "danger")
        return redirect(url_for("superadmin_login"))

    if not verify_secret_code(user=user, provided=secret_code, role="superadmin"):
        flash("Invalid secret code.", "danger")
        log_security_event("failed_login", severity="warn", actor_email=email, message="superadmin_login_bad_secret")
        maybe_send_failed_login_alert(actor_email=email)
        return render_template("pages/auth/admin_login.html", step="verify", email=email, next_url=next_url, role_label="Super Admin", is_super=True)

    session["user_id"] = int(user["user_id"])
    session["role"] = "superadmin"
    session["name"] = user.get("name") or ""
    session["email"] = email
    return redirect(next_url or url_for("super_admin_dashboard"))


@app.route("/auth/register", methods=["GET", "POST"])
def register():
    role = (request.args.get("role") or request.form.get("role") or "buyer").strip().lower()
    if role not in ("buyer", "seller"):
        role = "buyer"

    template = "pages/auth/register_buyer.html" if role == "buyer" else "pages/auth/register_seller.html"

    if request.method == "GET":
        return render_template(template, step="start", role=role)

    # resend verification OTP
    if request.form.get("resend") == "1":
        email = (request.form.get("email") or "").strip().lower()
        user = db_fetchone("SELECT user_id FROM user_account WHERE email=%s", (email,))
        if user:
            otp, _ = create_auth_challenge(email=email, purpose="verify", user_id=int(user["user_id"]))
            send_otp_email(email=email, purpose="verify", otp=otp)
        flash("We resent the verification code (if the account exists).", "info")
        return render_template(template, step="verify", role=role, email=email)

    # Required fields (both)
    name = (request.form.get("name") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    phone = (request.form.get("phone") or "").strip()
    password = request.form.get("password") or ""
    confirm = request.form.get("confirm") or ""

    # Seller-only fields (optional but supported)
    shop_name = (request.form.get("shop_name") or "").strip()
    location = (request.form.get("location") or "").strip()
    category = (request.form.get("category") or "").strip()
    story = (request.form.get("story") or "").strip()

    if not name or not email or not phone or not password or not confirm:
        flash("Please fill in all required fields.", "warning")
        return redirect(url_for("register", role=role))

    if password != confirm:
        flash("Passwords do not match.", "warning")
        return redirect(url_for("register", role=role))

    if len(password) < 6:
        flash("Password must be at least 6 characters.", "warning")
        return redirect(url_for("register", role=role))

    existing = db_fetchone("SELECT user_id FROM user_account WHERE email=%s", (email,))
    if existing:
        flash("Email already registered. Please login.", "warning")
        return redirect(url_for("login"))

    pw_hash = generate_password_hash(password)

    try:
        user_id = db_execute(
            "INSERT INTO user_account(role, name, email, phone, password_hash, is_email_verified, is_active) VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (role, name, email, phone, pw_hash, False, True),
            return_lastrowid=True,
        )
        issue_public_id(role, int(user_id))
        if role == "seller":
            if not shop_name:
                shop_name = "My Heritage Shop"
            db_execute(
                "INSERT INTO seller_profile(seller_id, shop_name, owner_name, is_verified, location, category, story) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (int(user_id), shop_name, name, False, location or None, category or None, story or None),
            )
    except MySQLError:
        flash("Could not create account. Please try again.", "danger")
        return redirect(url_for("register", role=role))

    otp, _ = create_auth_challenge(email=email, purpose="verify", user_id=int(user_id))
    send_otp_email(email=email, purpose="verify", otp=otp)

    flash("We sent a verification code to your email.", "success")
    return render_template(template, step="verify", role=role, email=email)


@app.post("/auth/register/verify")
def register_verify():
    email = (request.form.get("email") or "").strip().lower()
    otp = (request.form.get("otp") or "").strip()
    role = (request.form.get("role") or "buyer").strip().lower()
    if role not in ("buyer", "seller"):
        role = "buyer"

    template = "pages/auth/register_buyer.html" if role == "buyer" else "pages/auth/register_seller.html"

    if not email or not otp:
        flash("Please enter the code we sent to your email.", "warning")
        return render_template(template, step="verify", role=role, email=email)

    row = consume_auth_challenge(email=email, purpose="verify", otp=otp)
    if not row:
        flash("Invalid or expired code. Please try again.", "danger")
        return render_template(template, step="verify", role=role, email=email)

    db_execute("UPDATE user_account SET is_email_verified=TRUE WHERE email=%s", (email,))
    user = db_fetchone("SELECT user_id, role, name, is_active FROM user_account WHERE email=%s", (email,))
    if not user or not user.get("is_active", True):
        flash("Account not available.", "danger")
        return redirect(url_for("login"))

    role = (user.get("role") or "").lower()
    user_id = int(user["user_id"])
    member_id = format_member_id(role, user_id)

    # Premium success emails (after verification)
    if role == "buyer":
        html = render_email("buyer_welcome.html", name=user.get("name") or "Buyer", member_id=member_id)
        send_email(
            email,
            "Welcome to Origins Bangladesh",
            text=f"Welcome to Origins Bangladesh!\nYour Buyer ID: {member_id}\n",
            html=html,
        )
    elif role == "seller":
        html = render_email("seller_onboarding.html", name=user.get("name") or "Seller", member_id=member_id)
        send_email(
            email,
            "Seller onboarding: documents required",
            text=f"Welcome to Origins Bangladesh!\nYour Seller ID: {member_id}\nPlease submit your documents for verification.\n",
            html=html,
        )

    # Auto-login after verified
    session["user_id"] = user_id
    session["role"] = role
    session["name"] = user.get("name") or ""
    if role == "seller":
        _ensure_seller_session_state(user_id)

    flash("Your email is verified. Welcome!", "success")
    return redirect(url_for("buyer_dashboard" if role == "buyer" else "seller_dashboard"))


@app.route("/auth/forgot", methods=["GET", "POST"])
def forgot_password():
    if request.method == "GET":
        return render_template("pages/auth/forgot.html", step="start")

    email = (request.form.get("email") or "").strip().lower()
    user = db_fetchone("SELECT user_id, role, is_active FROM user_account WHERE email=%s", (email,))

    if user and user.get("is_active", True) and (user.get("role") or "").lower() in ("buyer", "seller"):
        otp, _ = create_auth_challenge(email=email, purpose="reset", user_id=int(user["user_id"]))
        send_otp_email(email=email, purpose="reset", otp=otp)

    # Always show same response
    return render_template("pages/auth/forgot.html", step="sent", email=email)


@app.route("/auth/reset", methods=["GET", "POST"])
def reset_password():
    if request.method == "GET":
        email = (request.args.get("email") or "").strip().lower()
        return render_template("pages/auth/reset.html", email=email)

    email = (request.form.get("email") or "").strip().lower()
    otp = (request.form.get("otp") or "").strip()
    password = request.form.get("password") or ""
    confirm = request.form.get("confirm") or ""

    if not email or not otp:
        flash("Please enter your email and the reset code.", "warning")
        return render_template("pages/auth/reset.html", email=email)

    if password != confirm:
        flash("Passwords do not match.", "warning")
        return render_template("pages/auth/reset.html", email=email)

    if len(password) < 6:
        flash("Password must be at least 6 characters.", "warning")
        return render_template("pages/auth/reset.html", email=email)

    row = consume_auth_challenge(email=email, purpose="reset", otp=otp)
    if not row:
        flash("Invalid or expired code. Please request a new one.", "danger")
        return redirect(url_for("forgot_password"))

    user = db_fetchone("SELECT role FROM user_account WHERE email=%s", (email,))
    if not user or (user.get("role") or "").lower() not in ("buyer", "seller"):
        flash("Password reset is available for buyers and sellers only.", "warning")
        return redirect(url_for("login"))

    pw_hash = generate_password_hash(password)
    db_execute("UPDATE user_account SET password_hash=%s WHERE email=%s", (pw_hash, email))

    flash("Password updated. You can login now.", "success")
    return redirect(url_for("login"))


@app.get("/auth/revoke-device")
def revoke_device():
    token = (request.args.get("token") or "").strip()
    if not token:
        abort(404)
    th = _device_hash(token)
    row = db_fetchone(
        """
        SELECT device_id
        FROM trusted_device
        WHERE revoke_hash=%s AND revoked_at IS NULL AND expires_at > UTC_TIMESTAMP()
        """,
        (th,),
    )
    if row:
        db_execute("UPDATE trusted_device SET revoked_at=UTC_TIMESTAMP() WHERE device_id=%s", (int(row["device_id"]),))
        flash("Device revoked. Please sign in again on that device.", "success")
    else:
        flash("Revoke link is invalid or expired.", "warning")
    resp = redirect(url_for("login"))
    resp.set_cookie("ob_device", "", expires=0)
    return resp


@app.get("/auth/persona-quiz")
def persona_quiz():
    return render_template("pages/auth/persona-quiz.html")


@app.get("/auth/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# -----------------------
# Dashboards (static templates)
# -----------------------
@app.get("/buyer/dashboard")
def buyer_dashboard():
    buyer_id = current_user_id()
    if not buyer_id:
        return redirect(url_for("login"))

    user = db_fetchone(
        "SELECT user_id, name, email, phone, created_at FROM user_account WHERE user_id=%s LIMIT 1",
        (buyer_id,),
    ) or {}

    # DB-backed summary cards
    cart_count, cart_total_bdt = cart_summary(buyer_id)
    wcount = wishlist_count(buyer_id)

    ocount_row = db_fetchone("SELECT COUNT(*) AS c FROM `order` WHERE buyer_id=%s", (buyer_id,)) or {}
    order_count = int(ocount_row.get("c") or 0)

    # Recent orders (DB-backed, shaped to match the existing buyer dashboard UI)
    recent_orders_rows = db_fetchall(
        """
        SELECT
            o.order_id,
            o.status,
            o.total_bdt,
            o.created_at,
            o.delivered_at,
            GROUP_CONCAT(DISTINCT p.title ORDER BY p.title SEPARATOR ', ') AS item_title,
            MAX(p.image_path) AS image_path,
            GROUP_CONCAT(DISTINCT sp.shop_name ORDER BY sp.shop_name SEPARATOR ', ') AS seller_name,
            MAX(a.artisan_id) AS artisan_id
        FROM `order` o
        LEFT JOIN order_item oi ON oi.order_id=o.order_id
        LEFT JOIN product p ON p.product_id=oi.product_id
        LEFT JOIN seller_profile sp ON sp.seller_id=p.seller_id
        LEFT JOIN artisan_product ap ON ap.product_id=p.product_id
        LEFT JOIN artisan a ON a.artisan_id=ap.artisan_id
        WHERE o.buyer_id=%s
        GROUP BY o.order_id, o.status, o.total_bdt, o.created_at
        ORDER BY o.created_at DESC
        LIMIT 6
        """,
        (buyer_id,),
    )

    recent_orders = []
    for r in (recent_orders_rows or []):
        created = r.get("created_at")
        recent_orders.append(
            {
                "order_id": int(r.get("order_id")),
                "display_id": format_order_id(r.get("order_id")),
                "status": (r.get("status") or "pending"),
                "total_bdt": float(Decimal(str(r.get("total_bdt") or 0))),
                "total_fmt": fmt_money(Decimal(str(r.get("total_bdt") or 0))),
                "created_at": (created.strftime("%d %b %Y") if created else ""),
                "item_title": r.get("item_title") or "",
                "seller_name": r.get("seller_name") or "",
                "image": r.get("image_path") or "/static/assets/img/placeholder.jpg",
                "artisan_id": int(r.get("artisan_id") or 0) if r.get("artisan_id") else None,
                "timeline": build_order_timeline(r.get("status") or "pending", r.get("created_at"), r.get("delivered_at")),
                "current_phase": get_order_current_phase(int(r.get("order_id") or 0), r.get("status") or "pending", r.get("created_at"), r.get("delivered_at")),
            }
        )

    # Wishlist preview (top 6)
    wrows = db_fetchall(
        """
        SELECT p.product_id, p.title, p.price_bdt, p.image_path
        FROM wishlist w
        JOIN product p ON p.product_id=w.product_id
        WHERE w.buyer_id=%s
        ORDER BY w.created_at DESC
        LIMIT 6
        """,
        (buyer_id,),
    )
    wishlist_preview = []
    for r in (wrows or []):
        wishlist_preview.append(
            {
                "product_id": int(r.get("product_id")),
                "title": r.get("title") or "",
                "price_bdt": float(Decimal(str(r.get("price_bdt") or 0))),
                "price_fmt": fmt_money(Decimal(str(r.get("price_bdt") or 0))),
                "image": r.get("image_path") or "/static/assets/img/placeholder.jpg",
            }
        )

    # Cart items (for dashboard cart view)
    cart_items_rows = db_fetchall(
        """
        SELECT
          p.product_id, p.title, p.image_path,
          ci.quantity, p.price_bdt
        FROM cart c
        JOIN cart_item ci ON ci.cart_id=c.cart_id
        JOIN product p ON p.product_id=ci.product_id
        WHERE c.buyer_id=%s
        ORDER BY ci.created_at DESC
        LIMIT 50
        """,
        (buyer_id,),
    )
    cart_items = []
    for r in (cart_items_rows or []):
        cart_items.append(
            {
                "product_id": int(r.get("product_id")),
                "name": r.get("title") or "",
                "img": r.get("image_path") or "/static/assets/img/placeholder.jpg",
                "qty": int(r.get("quantity") or 1),
                "price": float(Decimal(str(r.get("price_bdt") or 0))),
            }
        )

    # Vault certs (optional; if table doesn't exist yet, return empty)
    vault_certs = []
    try:
        vrows = db_fetchall(
            """
            SELECT t.tag_code, t.product_id, t.issued_at
            FROM buyer_vault_tag v
            JOIN gi_tag t ON t.tag_id=v.tag_id
            WHERE v.buyer_id=%s
            ORDER BY v.saved_at DESC
            LIMIT 50
            """,
            (buyer_id,),
        )
        for r in (vrows or []):
            created = r.get("issued_at")
            vault_certs.append(
                {
                    "id": r.get("tag_code") or "",
                    "product": f"Product #{int(r.get('product_id') or 0)}",
                    "origin": "",
                    "date": (created.strftime("%b %Y") if created else ""),
                    "hash": "",
                    "materials": "",
                    "process": "",
                    "img": "https://images.unsplash.com/photo-1610128079633-149867946571?q=80&w=1200&auto=format&fit=crop",
                }
            )
    except Exception:
        vault_certs = []

    # Notifications (derived, since we don't have a notifications table yet)
    notifications = []
    for o in recent_orders[:3]:
        notifications.append(
            {
                "id": f"order-{o['order_id']}",
                "type": "order",
                "text": f"Order #{o['order_id']} is currently {o['status']}.",
                "time": o.get("created_at") or "",
                "unread": False,
                "icon": "package",
                "date": o.get("created_at") or "",
            }
        )
    if wcount:
        notifications.append(
            {
                "id": "wishlist",
                "type": "wishlist",
                "text": f"You have {wcount} item(s) saved in your wishlist.",
                "time": "",
                "unread": False,
                "icon": "heart",
                "date": "",
            }
        )

    impact_artisans_row = db_fetchone(
        """
        SELECT COUNT(DISTINCT COALESCE(ap.artisan_id, p.seller_id)) AS c
        FROM `order` o
        JOIN order_item oi ON oi.order_id=o.order_id
        JOIN product p ON p.product_id=oi.product_id
        LEFT JOIN artisan_product ap ON ap.product_id=p.product_id
        WHERE o.buyer_id=%s AND LOWER(o.status) IN ('paid','shipped','delivered')
        """,
        (buyer_id,),
    ) or {}
    impact_heritage_row = db_fetchone(
        """
        SELECT COUNT(DISTINCT CASE WHEN p.gi_tag IS NOT NULL AND TRIM(p.gi_tag)<>'' THEN CONCAT('GI:', p.gi_tag) ELSE CONCAT('CAT:', p.category_id) END) AS c
        FROM `order` o
        JOIN order_item oi ON oi.order_id=o.order_id
        JOIN product p ON p.product_id=oi.product_id
        WHERE o.buyer_id=%s AND LOWER(o.status) IN ('paid','shipped','delivered')
        """,
        (buyer_id,),
    ) or {}
    live_points = sync_buyer_points(buyer_id)
    exclusive_campaign = None
    try:
        crow = db_fetchone(
            """
            SELECT campaign_id, title, subtitle, image_url, cta_label, cta_url, min_points
            FROM buyer_campaign
            WHERE is_active=1
              AND (starts_at IS NULL OR starts_at<=NOW())
              AND (ends_at IS NULL OR ends_at>=NOW())
              AND (access_rule='all_buyers' OR (access_rule='points_threshold' AND min_points<=%s))
            ORDER BY min_points DESC, campaign_id DESC
            LIMIT 1
            """,
            (live_points,),
        )
        if crow:
            exclusive_campaign = {
                'title': crow.get('title') or 'Guardian Exclusive',
                'subtitle': crow.get('subtitle') or '',
                'image_url': crow.get('image_url') or '/static/assets/img/placeholder.jpg',
                'cta_label': crow.get('cta_label') or 'Explore Collection',
                'cta_url': crow.get('cta_url') or '/shop',
            }
    except Exception:
        exclusive_campaign = None

    buyer_info = {
        "name": user.get("name") or (session.get("name") or "Buyer"),
        "email": user.get("email") or "",
        "phone": user.get("phone") or "",
        "member_since": (str(user.get("created_at").year) if user.get("created_at") else ""),
        "guardian_id": "",
# Keep your UI keys (if you used them) without hardcoding identity
        "persona": "Heritage Guardian",
        "badge": "",
        "points": live_points,
        "address": "",
        "bio": "",
        "impact": {"artisans_helped": int(impact_artisans_row.get("c") or 0), "motifs_saved": int(impact_heritage_row.get("c") or 0)},
    }
    # Enrich buyer_info from buyer_profile if available (migration 2026-03-05)
    try:
        prow = db_fetchone(
            "SELECT address, bio, avatar_url, points, guardian_id FROM buyer_profile WHERE buyer_id=%s LIMIT 1",
            (buyer_id,),
        ) or {}
        buyer_info["address"] = prow.get("address") or buyer_info.get("address") or ""
        buyer_info["bio"] = prow.get("bio") or buyer_info.get("bio") or ""
        buyer_info["points"] = int(prow.get("points") or buyer_info.get("points") or 0)
        if prow.get("avatar_url"):
            buyer_info["avatar_url"] = prow.get("avatar_url")
        # Guardian ID (OB-UID-YYMM-XXXX)
        buyer_info["guardian_id"] = normalize_guardian_id(prow.get("guardian_id") or get_or_create_guardian_id(buyer_id) or "", buyer_id)
    except Exception:
        pass


    dash_stats = {
        "cart_count": cart_count,
        "cart_total_fmt": fmt_money(cart_total_bdt),
        "wishlist_count": wcount,
        "order_count": order_count,
    }

    return render_template(
        "pages/buyer/dashboard.html",
        app_shell=True,
        buyer_name=buyer_info["name"],
        buyer_info=buyer_info,
        dash_stats=dash_stats,
        exclusive_campaign=exclusive_campaign,
        recent_orders=recent_orders,
        wishlist_preview=wishlist_preview,
        notifications=notifications,
        cart_items=cart_items,
        vault_certs=vault_certs,
    )


@app.get("/buyer/orders")
def buyer_orders():
    return render_template("pages/buyer/orders.html")


@app.get("/buyer/profile")
def buyer_profile():
    return render_template("pages/buyer/profile.html")


@app.get("/buyer/authenticity-vault")
def buyer_authenticity_vault():
    return render_template("pages/buyer/authenticity-vault.html")


@app.get("/seller/onboarding")
def seller_onboarding():
    # Onboarding UI is currently embedded in seller dashboard views.
    return redirect(url_for("seller_dashboard", view="verification"))


@app.get("/seller/dashboard")
def seller_dashboard():
    r = require_role("seller")
    if r:
        return r
    uid = int(current_user_id() or 0)
    payload = _build_seller_dashboard_data(uid)
    _ensure_seller_session_state(uid)
    return render_template(
        "pages/seller/dashboard.html",
        app_shell=True,
        seller_info=payload.get("seller_info") or {},
        seller_dashboard_data=payload,
    )

@app.get("/seller/products")
def seller_products():
    return redirect(url_for("seller_dashboard", view="product-studio"))


@app.get("/seller/orders")
def seller_orders():
    return redirect(url_for("seller_dashboard", view="orders"))


@app.get("/seller/wallet")
def seller_wallet():
    return redirect(url_for("seller_dashboard", view="wallet"))


@app.post("/api/admin/seller-verifications/<int:seller_id>/approve")
def api_admin_approve_seller_verification(seller_id: int):
    r = require_role("admin", "superadmin")
    if r:
        return r

    row = db_fetchone(
        """
        SELECT sp.seller_id, sp.shop_name, sp.owner_name, u.email
        FROM seller_profile sp
        JOIN user_account u ON u.user_id=sp.seller_id
        WHERE sp.seller_id=%s
        LIMIT 1
        """,
        (seller_id,),
    )
    if not row:
        return jsonify({"ok": False, "message": "Seller not found."}), 404

    now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
    db_execute(
        """
        UPDATE seller_profile
        SET is_verified=TRUE, verification_status='approved', reviewed_by=%s, reviewed_at=%s, rejection_reason=NULL
        WHERE seller_id=%s
        """,
        (int(current_user_id() or 0), now, seller_id),
    )

    try:
        notify_id = int(seller_id)
        db_execute(
            "INSERT INTO notification (recipient_user_id, type, severity, title, body, link, meta_json) VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (notify_id, 'seller_verification', 'success', 'Verification approved', 'Your seller account is now verified and unlocked.', '/seller/dashboard?view=verification', json.dumps({'seller_id': seller_id})),
        )
    except Exception:
        pass

    try:
        login_url = _base_url().rstrip('/') + url_for('login')
        subject, text_body, html = render_email_bundle(
            'seller_verification_approved',
            fallback_template='seller_verification_approved.html',
            default_subject='Your seller account has been approved',
            default_text=f"Hello {(row.get('owner_name') or row.get('shop_name') or 'Seller')},\n\nYour seller verification is approved. You can now access all seller features.\n\nLogin: {login_url}\n",
            name=row.get('owner_name') or row.get('shop_name') or 'Seller',
            shop_name=row.get('shop_name') or '',
            login_url=login_url,
        )
        send_email(str(row.get('email') or ''), subject, text=text_body, html=html)
    except Exception:
        pass

    audit_log('seller_verification_approved', target_user_id=seller_id, metadata={'seller_id': seller_id})
    return jsonify({"ok": True})


@app.post("/api/admin/artisan-hour/status")
def api_admin_artisan_hour_status():
    r = require_role("admin", "superadmin")
    if r:
        return r
    data = request.get_json(silent=True) or {}
    live = bool(data.get('live'))
    set_setting('artisan_hour_live', '1' if live else '0')
    if live:
        set_setting('artisan_hour_live_started_at', datetime.datetime.now().replace(microsecond=0).isoformat())
    else:
        set_setting('artisan_hour_live_started_at', '')
    audit_log('artisan_hour_status_updated', metadata={'live': live})
    return jsonify({"ok": True, "live": live, "live_started_at": get_setting('artisan_hour_live_started_at', '')})


@app.post("/api/admin/artisan-hour/schedule")
def api_admin_artisan_hour_schedule():
    r = require_role("admin", "superadmin")
    if r:
        return r
    data = request.get_json(silent=True) or {}
    start_date = str(data.get('start_date') or '').strip()
    end_date = str(data.get('end_date') or '').strip()
    start = str(data.get('start') or '14:00').strip()[:5]
    end = str(data.get('end') or '16:00').strip()[:5]

    if not start_date or not end_date or not start or not end:
        return jsonify({"ok": False, "message": "Please provide start date, start time, end date and end time."}), 400

    try:
        start_dt = datetime.datetime.strptime(f"{start_date} {start}", "%Y-%m-%d %H:%M")
        end_dt = datetime.datetime.strptime(f"{end_date} {end}", "%Y-%m-%d %H:%M")
    except Exception:
        return jsonify({"ok": False, "message": "Invalid date/time format."}), 400

    if end_dt <= start_dt:
        return jsonify({"ok": False, "message": "End date/time must be later than start date/time."}), 400

    delta = end_dt - start_dt
    total_minutes = int(delta.total_seconds() // 60)
    hours = total_minutes // 60
    minutes = total_minutes % 60
    total_hours_display = f"{hours}h" + (f" {minutes}m" if minutes else "")

    set_setting('artisan_hour_start_date', start_date)
    set_setting('artisan_hour_end_date', end_date)
    set_setting('artisan_hour_start', start)
    set_setting('artisan_hour_end', end)
    set_setting('artisan_hour_total_hours_display', total_hours_display)
    set_setting('artisan_hour_duration_seconds', str(int(delta.total_seconds())))
    set_setting('artisan_hour_live_started_at', '')
    audit_log('artisan_hour_schedule_updated', metadata={'start_date': start_date, 'start': start, 'end_date': end_date, 'end': end, 'total_hours_display': total_hours_display})
    return jsonify({
        "ok": True,
        "start_date": start_date,
        "end_date": end_date,
        "start": start,
        "end": end,
        "total_hours_display": total_hours_display,
        "duration_seconds": int(delta.total_seconds()),
    })


@app.post("/api/admin/featured-artisan/<int:seller_id>")
def api_admin_set_featured_artisan(seller_id: int):
    r = require_role("admin", "superadmin")
    if r:
        return r
    row = db_fetchone("SELECT seller_id FROM seller_profile WHERE seller_id=%s LIMIT 1", (seller_id,))
    if not row:
        return jsonify({"ok": False, "message": "Seller not found."}), 404
    set_setting('featured_seller_id', str(seller_id))
    audit_log('featured_artisan_updated', target_user_id=seller_id, metadata={'seller_id': seller_id})
    return jsonify({"ok": True, "featured": fetch_featured_artisan() or {}})


@app.post("/api/admin/site-experience")
def api_admin_site_experience():
    r = require_role("admin", "superadmin")
    if r:
        return r

    headline = (request.form.get('headline') or request.json.get('headline') if request.is_json else request.form.get('headline') or '').strip()
    subtext = (request.form.get('subtext') or request.json.get('subtext') if request.is_json else request.form.get('subtext') or '').strip()
    image_url = (request.form.get('image_url') or request.json.get('image_url') if request.is_json else request.form.get('image_url') or '').strip()
    if not headline:
        headline = 'Threads of\nTradition,\nWoven with Soul.'
    if not subtext:
        subtext = get_setting('home_hero_subtext', 'Discover the authenticity of Bengal. From the legendary Muslin to the royal Jamdani, bring home artifacts that carry a millennium of history.')

    uploaded = request.files.get('hero_image')
    if uploaded and uploaded.filename:
        ext = os.path.splitext(secure_filename(uploaded.filename))[1].lower() or '.jpg'
        folder = os.path.join(app.root_path, 'static', 'uploads', 'site')
        os.makedirs(folder, exist_ok=True)
        fname = f"hero_{int(time.time())}{ext}"
        uploaded.save(os.path.join(folder, fname))
        image_url = f"/static/uploads/site/{fname}"

    if not image_url:
        image_url = get_setting('home_hero_image', 'https://images.unsplash.com/photo-1621252179027-94459d278660?auto=format&fit=crop&q=80&w=1200')

    set_setting('home_hero_headline', headline)
    set_setting('home_hero_subtext', subtext)
    set_setting('home_hero_image', image_url)
    audit_log('site_experience_updated', metadata={'headline': headline, 'image_url': image_url})
    return jsonify({"ok": True, "site_experience": fetch_site_experience_settings()})


@app.get("/admin/dashboard")
def admin_dashboard():
    r = require_role("admin", "superadmin")
    if r:
        return r
    return render_template("pages/admin/dashboard.html", admin_dashboard_data=_build_admin_dashboard_data())


@app.get("/admin/seller-verification")
def admin_seller_verification():
    return render_template("pages/admin/seller-verification.html")


@app.get("/admin/product-review")
def admin_product_review():
    return render_template("pages/admin/product-review.html")


@app.get("/admin/flash-sale")
def admin_flash_sale():
    return render_template("pages/admin/flash-sale.html")


@app.get("/admin/orders")
def admin_orders():
    return render_template("pages/admin/orders.html")




def _admin_json_ok(**kwargs: Any):
    payload = {"ok": True}
    payload.update(kwargs)
    return jsonify(payload)


def _admin_json_error(error: str = "request_failed", status: int = 400, **kwargs: Any):
    payload = {"ok": False, "error": error}
    payload.update(kwargs)
    return jsonify(payload), status


def _db_execute_fallback(statements):
    last_error = None
    for sql, params in statements:
        try:
            db_execute(sql, params)
            return True
        except Exception as exc:
            last_error = exc
    if last_error:
        raise last_error
    return False


def _admin_require():
    return require_role("admin", "superadmin")


def _admin_upload_dir() -> str:
    folder = os.path.join(app.root_path, "static", "uploads", "admin")
    os.makedirs(folder, exist_ok=True)
    return folder


@app.get("/api/admin/dashboard/data")
def api_admin_dashboard_data():
    r = _admin_require()
    if r:
        return r
    return jsonify({"ok": True, "data": _build_admin_dashboard_data()})


@app.post("/api/admin/profile")
def api_admin_profile_update():
    r = _admin_require()
    if r:
        return r
    admin_id = int(current_user_id() or 0)
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"ok": False, "error": "name_required"}), 400
    db_execute("UPDATE user_account SET name=%s WHERE user_id=%s", (name, admin_id))
    session["name"] = name
    audit_log("admin_profile_self_updated", target_user_id=admin_id, metadata={"name": name})
    return _admin_json_ok(name=name)


@app.post("/api/admin/profile/avatar")
def api_admin_profile_avatar():
    r = _admin_require()
    if r:
        return r
    admin_id = int(current_user_id() or 0)
    f = request.files.get("avatar")
    if not f or not f.filename:
        return jsonify({"ok": False, "error": "file_required"}), 400
    ext = os.path.splitext(secure_filename(f.filename))[1].lower() or ".jpg"
    if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        return jsonify({"ok": False, "error": "invalid_file_type"}), 400
    rel = f"static/uploads/admin/admin_{admin_id}_{int(time.time())}{ext}"
    abs_path = os.path.join(app.root_path, rel)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    f.save(abs_path)
    db_execute(
        "INSERT INTO admin_profile (admin_id, designation, avatar_url) VALUES (%s,%s,%s) ON DUPLICATE KEY UPDATE avatar_url=VALUES(avatar_url)",
        (admin_id, 'Admin', '/' + rel.replace('\\', '/')),
    )
    audit_log("admin_avatar_updated", target_user_id=admin_id)
    return _admin_json_ok(url='/' + rel.replace('\\', '/'))


@app.post("/api/admin/profile/password")
def api_admin_profile_password():
    r = _admin_require()
    if r:
        return r
    admin_id = int(current_user_id() or 0)
    data = request.get_json(silent=True) or {}
    current_password = data.get("current_password") or ""
    new_password = data.get("new_password") or ""
    if len(new_password) < 6:
        return jsonify({"ok": False, "error": "weak_password"}), 400
    row = db_fetchone("SELECT password_hash FROM user_account WHERE user_id=%s", (admin_id,)) or {}
    if not check_password_hash(str(row.get("password_hash") or ""), current_password):
        return jsonify({"ok": False, "error": "invalid_current_password"}), 400
    db_execute("UPDATE user_account SET password_hash=%s WHERE user_id=%s", (generate_password_hash(new_password), admin_id))
    audit_log("admin_password_updated", target_user_id=admin_id)
    return _admin_json_ok()


@app.post("/api/admin/sellers/<int:seller_id>/status")
def api_admin_seller_status(seller_id: int):
    r = _admin_require()
    if r:
        return r
    data = request.get_json(silent=True) or {}
    status = (data.get("status") or "").strip()
    role_row = db_fetchone("SELECT user_id FROM user_account WHERE user_id=%s AND role='seller'", (seller_id,))
    if not role_row:
        return jsonify({"ok": False, "error": "not_found"}), 404
    if status in ("Active", "Banned"):
        db_execute("UPDATE user_account SET is_active=%s WHERE user_id=%s", (1 if status == 'Active' else 0, seller_id))
    if status in ("Active", "Pending Verification", "Rejected", "Draft"):
        vf = {'Active': 'approved', 'Pending Verification': 'under_review', 'Rejected': 'rejected', 'Draft': 'draft'}[status]
        db_execute("UPDATE seller_profile SET verification_status=%s, is_verified=%s WHERE seller_id=%s", (vf, 1 if vf == 'approved' else 0, seller_id))
    audit_log("admin_seller_status_updated", target_user_id=seller_id, metadata={"status": status})
    if status in ("Active", "Banned"):
        send_user_access_email(seller_id, status == "Active", reason=(data.get("reason") or "").strip())
    return _admin_json_ok(public_id=get_public_user_id(seller_id, role="seller"))


@app.post("/api/admin/products/<int:product_id>/status")
def api_admin_product_status(product_id: int):
    r = _admin_require()
    if r:
        return r
    data = request.get_json(silent=True) or {}
    status = (data.get("status") or "Draft").strip()
    is_active = 1 if status == 'Live' else 0
    row = db_fetchone("SELECT seller_id FROM product WHERE product_id=%s", (product_id,))
    if not row:
        return jsonify({"ok": False, "error": "not_found"}), 404
    db_execute("UPDATE product SET is_active=%s WHERE product_id=%s", (is_active, product_id))
    db_execute("INSERT IGNORE INTO admin_qc_item (product_id, seller_id, status) VALUES (%s,%s,'Pending')", (product_id, row.get('seller_id')))
    audit_log("admin_product_status_updated", metadata={"product_id": product_id, "status": status})
    return _admin_json_ok()


@app.post("/api/admin/orders/<int:order_id>/status")
def api_admin_order_status(order_id: int):
    r = _admin_require()
    if r:
        return r
    data = request.get_json(silent=True) or {}
    status = (data.get("status") or "Processing").strip()
    db_status = {'Processing': 'paid', 'Shipped': 'shipped', 'Delivered': 'delivered', 'Cancelled': 'cancelled'}.get(status, 'paid')
    db_execute("UPDATE `order` SET status=%s WHERE order_id=%s", (db_status, order_id))
    audit_log("admin_order_status_updated", metadata={"order_id": order_id, "status": status})
    send_order_status_email(order_id, db_status, f"Updated by admin to {status}.")
    return _admin_json_ok()


@app.post("/api/admin/verification/<int:seller_id>/action")
def api_admin_verification_action(seller_id: int):
    r = _admin_require()
    if r:
        return r
    try:
        data = request.get_json(silent=True) or {}
        action = (data.get("action") or "").strip().lower()
        note = (data.get("note") or "").strip()
        status_map = {
            'approve': ('approved', 1),
            'reject': ('rejected', 0),
            'resubmit': ('submitted', 0),
        }
        if action not in status_map:
            return _admin_json_error("invalid_action", 400)
        vf, is_verified = status_map[action]
        seller = db_fetchone("SELECT seller_id FROM seller_profile WHERE seller_id=%s", (seller_id,))
        if not seller:
            return _admin_json_error("seller_not_found", 404)
        _db_execute_fallback([
            ("UPDATE seller_profile SET verification_status=%s, is_verified=%s, reviewed_by=%s, reviewed_at=CURRENT_TIMESTAMP, rejection_reason=%s WHERE seller_id=%s", (vf, is_verified, current_user_id(), note or None, seller_id)),
            ("UPDATE seller_profile SET verification_status=%s, is_verified=%s, rejection_reason=%s WHERE seller_id=%s", (vf, is_verified, note or None, seller_id)),
            ("UPDATE seller_profile SET verification_status=%s, is_verified=%s WHERE seller_id=%s", (vf, is_verified, seller_id)),
        ])
        try:
            db_execute("INSERT INTO notification (recipient_user_id, type, severity, title, body, link, meta_json) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                       (seller_id, 'seller_verification', 'success' if action == 'approve' else 'info', 'Verification update',
                        ('Your seller verification has been approved.' if action == 'approve' else f'Your seller verification status is now {vf}.'),
                        '/seller/dashboard?view=verification', json.dumps({'seller_id': seller_id, 'status': vf})))
        except Exception:
            pass
        audit_log(f"admin_verification_{action}", target_user_id=seller_id, metadata={"note": note})
        try:
            send_seller_verification_email(seller_id, approved=(action == "approve"), note=note)
        except Exception:
            pass
        return _admin_json_ok(public_id=get_public_user_id(seller_id, role="seller"), status=vf)
    except Exception as exc:
        return _admin_json_error(str(exc) or "request_failed", 500)


@app.post("/api/admin/qc/<int:qc_id>/action")
def api_admin_qc_action(qc_id: int):
    r = _admin_require()
    if r:
        return r
    try:
        data = request.get_json(silent=True) or {}
        action = (data.get("action") or "").strip().lower()
        note = (data.get("note") or "").strip()
        new_status = {'approve': 'Approved', 'reject': 'Rejected', 'resubmit': 'Changes Requested'}.get(action)
        if not new_status:
            return _admin_json_error("invalid_action", 400)
        row = db_fetchone(
            "SELECT qc_id, product_id, seller_id FROM admin_qc_item WHERE qc_id=%s OR product_id=%s ORDER BY CASE WHEN qc_id=%s THEN 0 ELSE 1 END LIMIT 1",
            (qc_id, qc_id, qc_id),
        )
        if not row:
            return _admin_json_error("qc_not_found", 404)
        resolved_qc_id = int(row.get('qc_id') or qc_id)
        product_id = int(row.get('product_id') or 0)
        _db_execute_fallback([
            ("UPDATE admin_qc_item SET status=%s, note=%s, reviewed_by=%s, reviewed_at=CURRENT_TIMESTAMP WHERE qc_id=%s", (new_status, note or None, current_user_id(), resolved_qc_id)),
            ("UPDATE admin_qc_item SET status=%s, note=%s WHERE qc_id=%s", (new_status, note or None, resolved_qc_id)),
            ("UPDATE admin_qc_item SET status=%s WHERE qc_id=%s", (new_status, resolved_qc_id)),
        ])
        if product_id:
            if action == 'approve':
                db_execute("UPDATE product SET is_active=1 WHERE product_id=%s", (product_id,))
            elif action == 'reject':
                db_execute("UPDATE product SET is_active=0 WHERE product_id=%s", (product_id,))
        audit_log(f"admin_qc_{action}", metadata={"qc_id": resolved_qc_id, "product_id": product_id, "note": note})
        return _admin_json_ok(qc_id=resolved_qc_id, product_id=product_id, status=new_status)
    except Exception as exc:
        return _admin_json_error(str(exc) or "request_failed", 500)


@app.post("/api/admin/gi/<int:app_id>/action")
def api_admin_gi_action(app_id: int):
    r = _admin_require()
    if r:
        return r
    try:
        data = request.get_json(silent=True) or {}
        action = (data.get("action") or "").strip().lower()
        note = (data.get("note") or "").strip()
        new_status = {'approve': 'approved', 'reject': 'rejected', 'resubmit': 'needs_more_info'}.get(action)
        if not new_status:
            return _admin_json_error("invalid_action", 400)
        gi = db_fetchone("SELECT app_id, seller_id, product_name FROM seller_gi_application WHERE app_id=%s", (app_id,))
        if not gi:
            return _admin_json_error("gi_application_not_found", 404)
        _db_execute_fallback([
            ("UPDATE seller_gi_application SET status=%s, notes=%s WHERE app_id=%s", (new_status, note or None, app_id)),
            ("UPDATE seller_gi_application SET status=%s, feedback=%s WHERE app_id=%s", (new_status, note or None, app_id)),
            ("UPDATE seller_gi_application SET status=%s WHERE app_id=%s", (new_status, app_id)),
        ])
        try:
            if gi.get('seller_id'):
                db_execute("INSERT INTO notification (recipient_user_id, type, severity, title, body, link, meta_json) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                           (gi.get('seller_id'), 'gi_application', 'success' if action == 'approve' else 'info', 'GI application update',
                            f"Your GI application for {gi.get('product_name') or 'your product'} is now {new_status}.",
                            '/seller/dashboard?view=gi-center', json.dumps({'app_id': app_id, 'status': new_status})))
        except Exception:
            pass
        audit_log(f"admin_gi_{action}", metadata={"app_id": app_id, "note": note})
        return _admin_json_ok(app_id=app_id, status=new_status)
    except Exception as exc:
        return _admin_json_error(str(exc) or "request_failed", 500)


@app.get("/api/admin/verification/<int:seller_id>/documents")
def api_admin_verification_documents(seller_id: int):
    r = _admin_require()
    if r:
        return r
    try:
        return _admin_json_ok(**_get_admin_documents_payload('verification', seller_id))
    except Exception as exc:
        return _admin_json_error(str(exc) or "viewer_load_failed", 500)



@app.get("/api/admin/qc/<int:qc_id>/documents")
def api_admin_qc_documents(qc_id: int):
    r = _admin_require()
    if r:
        return r
    try:
        return _admin_json_ok(**_get_admin_documents_payload('qc', qc_id))
    except Exception as exc:
        return _admin_json_error(str(exc) or "viewer_load_failed", 500)



@app.get("/api/admin/gi/<int:app_id>/documents")
def api_admin_gi_documents(app_id: int):
    r = _admin_require()
    if r:
        return r
    try:
        return _admin_json_ok(**_get_admin_documents_payload('gi', app_id))
    except Exception as exc:
        return _admin_json_error(str(exc) or "viewer_load_failed", 500)





@app.get("/admin/documents/<kind>/<int:record_id>")
def admin_documents_viewer(kind: str, record_id: int):
    r = _admin_require()
    if r:
        return r
    return render_template("pages/admin/document-viewer.html", kind=kind, record_id=record_id)


@app.get("/api/admin/documents/<kind>/<int:record_id>")
def api_admin_documents(kind: str, record_id: int):
    r = _admin_require()
    if r:
        return r
    try:
        return _admin_json_ok(**_get_admin_documents_payload(kind, record_id))
    except Exception as exc:
        return _admin_json_error(str(exc) or "viewer_load_failed", 500)


@app.get("/api/admin/atlas/district-options")
def api_admin_atlas_district_options():
    r = _admin_require()
    if r:
        return r
    _ensure_atlas_districts_seeded()
    rows = db_fetchall(
        """
        SELECT d.district_id AS id, d.name, a.atlas_id
        FROM district d
        LEFT JOIN district_atlas a ON a.district_id=d.district_id
        ORDER BY d.name ASC
        """
    ) or []
    return _admin_json_ok(districts=[{'id': r0.get('id'), 'name': r0.get('name'), 'atlas_id': r0.get('atlas_id')} for r0 in rows])


@app.post("/api/admin/atlas")
def api_admin_atlas_create():
    r = _admin_require()
    if r:
        return r
    _ensure_atlas_districts_seeded()
    data = request.get_json(silent=True) or {}
    district_id = _safe_int(data.get('district_id'))
    if not district_id:
        return jsonify({'ok': False, 'error': 'district_required'}), 400
    existing = db_fetchone('SELECT atlas_id FROM district_atlas WHERE district_id=%s', (district_id,))
    if existing:
        return jsonify({'ok': False, 'error': 'district_already_exists'}), 400
    density = (data.get('density') or 'low').strip().lower()
    if density not in ('low', 'med', 'high'):
        density = 'low'
    category = (data.get('category') or 'other').strip().lower()[:80]
    product = (data.get('product') or '').strip()[:255] or 'No Official GI Product'
    story = (data.get('story') or '').strip() or None
    img = (data.get('img') or '').strip()[:500] or None
    link = (data.get('link') or '').strip()[:500] or None
    if not link and district_id:
        row_d = db_fetchone('SELECT name FROM district WHERE district_id=%s', (district_id,)) or {}
        if row_d.get('name'): link = f"/shop?district={quote(row_d.get('name'))}"
    try:
        x = float(data.get('x') or 0)
        y = float(data.get('y') or 0)
    except Exception:
        x, y = 0.0, 0.0
    db_execute(
        'INSERT INTO district_atlas (district_id, density, product_name, category, story, image_url, shop_link, dot_x, dot_y, is_active) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,TRUE)',
        (district_id, density, product, category, story, img, link, x, y)
    )
    audit_log('admin_atlas_created', metadata={'district_id': district_id, 'category': category})
    try:
        _ATLAS_CACHE['ts'] = 0.0; _ATLAS_CACHE['data'] = None; _ATLAS_CACHE['etag'] = None
    except Exception:
        pass
    return _admin_json_ok()


@app.post("/api/admin/atlas/<int:atlas_id>/toggle")
def api_admin_atlas_toggle(atlas_id: int):
    r = _admin_require()
    if r:
        return r
    row = db_fetchone("SELECT is_active FROM district_atlas WHERE atlas_id=%s", (atlas_id,))
    if not row:
        return jsonify({"ok": False, "error": "not_found"}), 404
    new_val = 0 if bool(row.get("is_active")) else 1
    db_execute("UPDATE district_atlas SET is_active=%s WHERE atlas_id=%s", (new_val, atlas_id))
    audit_log("admin_atlas_toggle", metadata={"atlas_id": atlas_id, "is_active": bool(new_val)})
    try:
        _ATLAS_CACHE["ts"] = 0.0
        _ATLAS_CACHE["data"] = None
        _ATLAS_CACHE["etag"] = None
    except Exception:
        pass
    return _admin_json_ok(is_active=bool(new_val))


@app.post("/api/admin/atlas/<int:atlas_id>")
def api_admin_atlas_update(atlas_id: int):
    r = _admin_require()
    if r:
        return r
    _ensure_atlas_districts_seeded()
    data = request.get_json(silent=True) or {}
    density = (data.get("density") or "low").strip().lower()
    if density not in ("low", "med", "high"):
        density = "low"
    category = (data.get("category") or "other").strip().lower()[:80]
    product = (data.get("product") or "").strip()[:255]
    story = (data.get("story") or "").strip()
    img = (data.get("img") or "").strip()[:500]
    link = (data.get("link") or "").strip()[:500]
    district_id = _safe_int(data.get("district_id"))
    try:
        x = float(data.get("x") or 0)
    except Exception:
        x = 0.0
    try:
        y = float(data.get("y") or 0)
    except Exception:
        y = 0.0
    row = db_fetchone("SELECT atlas_id FROM district_atlas WHERE atlas_id=%s", (atlas_id,))
    if not row:
        return jsonify({"ok": False, "error": "not_found"}), 404
    existing = db_fetchone('SELECT district_id FROM district_atlas WHERE atlas_id=%s', (atlas_id,)) or {}
    district_id = district_id or existing.get('district_id')
    if not link and district_id:
        row_d = db_fetchone('SELECT name FROM district WHERE district_id=%s', (district_id,)) or {}
        if row_d.get('name'): link = f"/shop?district={quote(row_d.get('name'))}"
    db_execute(
        "UPDATE district_atlas SET district_id=%s, density=%s, category=%s, product_name=%s, story=%s, image_url=%s, shop_link=%s, dot_x=%s, dot_y=%s WHERE atlas_id=%s",
        (district_id, density, category, product, story, img or None, link or None, x, y, atlas_id),
    )
    audit_log("admin_atlas_updated", metadata={"atlas_id": atlas_id, "density": density, "category": category})
    try:
        _ATLAS_CACHE["ts"] = 0.0
        _ATLAS_CACHE["data"] = None
        _ATLAS_CACHE["etag"] = None
    except Exception:
        pass
    return _admin_json_ok()


@app.delete('/api/admin/atlas/<int:atlas_id>')
def api_admin_atlas_delete(atlas_id: int):
    r = _admin_require()
    if r:
        return r
    row = db_fetchone('SELECT atlas_id FROM district_atlas WHERE atlas_id=%s', (atlas_id,))
    if not row:
        return jsonify({'ok': False, 'error': 'not_found'}), 404
    db_execute('DELETE FROM district_atlas WHERE atlas_id=%s', (atlas_id,))
    audit_log('admin_atlas_deleted', metadata={'atlas_id': atlas_id})
    try:
        _ATLAS_CACHE['ts'] = 0.0; _ATLAS_CACHE['data'] = None; _ATLAS_CACHE['etag'] = None
    except Exception:
        pass
    return _admin_json_ok()


@app.get("/api/admin/journal/<int:article_id>")
def api_admin_journal_get(article_id: int):
    r = _admin_require()
    if r:
        return r
    row = db_fetchone("SELECT article_id AS id, title, body_html FROM gi_journal_article WHERE article_id=%s", (article_id,))
    if not row:
        return jsonify({"ok": False, "error": "not_found"}), 404
    return _admin_json_ok(article=row)


@app.post("/api/admin/journal")
def api_admin_journal_create():
    r = _admin_require()
    if r:
        return r
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "Untitled Draft").strip() or "Untitled Draft"
    body_html = (data.get("body_html") or "").strip() or "<p>Draft content pending.</p>"
    conn = get_db(); cur = conn.cursor();
    cur.execute("INSERT INTO gi_journal_article (title, slug, body_html) VALUES (%s,%s,%s)", (title, re.sub(r'[^a-z0-9]+','-', title.lower()).strip('-')[:120] or f'draft-{int(time.time())}', body_html))
    conn.commit(); article_id = cur.lastrowid; conn.close()
    audit_log("admin_journal_created", metadata={"article_id": int(article_id), "title": title})
    return _admin_json_ok(id=int(article_id))


@app.put("/api/admin/journal/<int:article_id>")
def api_admin_journal_update(article_id: int):
    r = _admin_require()
    if r:
        return r
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "Untitled Draft").strip() or "Untitled Draft"
    body_html = (data.get("body_html") or "").strip() or "<p>Draft content pending.</p>"
    publish = bool(data.get("publish"))
    db_execute("UPDATE gi_journal_article SET title=%s, body_html=%s, published_at=%s WHERE article_id=%s", (title, body_html, datetime.datetime.utcnow() if publish else None, article_id))
    audit_log("admin_journal_updated", metadata={"article_id": article_id, "publish": publish})
    return _admin_json_ok()


@app.post("/api/admin/team")
def api_admin_team_create():
    r = _admin_require()
    if r:
        return r
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"ok": False, "error": "name_required"}), 400
    email = (data.get("email") or f"{name.lower().replace(' ', '.')}@origins.bd").strip().lower()
    role = (data.get("role") or "Editor").strip() or "Editor"
    db_execute("INSERT INTO admin_team_member (name, email, role, created_by) VALUES (%s,%s,%s,%s)", (name, email, role, current_user_id()))
    audit_log("admin_team_member_created", metadata={"name": name, "email": email})
    return _admin_json_ok()


@app.delete("/api/admin/team/<int:team_id>")
def api_admin_team_delete(team_id: int):
    r = _admin_require()
    if r:
        return r
    db_execute("UPDATE admin_team_member SET is_active=0 WHERE team_id=%s", (team_id,))
    audit_log("admin_team_member_deleted", metadata={"team_id": team_id})
    return _admin_json_ok()


@app.post("/api/admin/coupons")
def api_admin_coupon_create():
    r = _admin_require()
    if r:
        return r
    data = request.get_json(silent=True) or {}
    code = (data.get("code") or "").strip().upper()
    if not code:
        return jsonify({"ok": False, "error": "code_required"}), 400
    typ = (data.get("type") or 'Percentage').strip()
    val = Decimal(str(data.get("discount_value") or 0))
    usage_limit = data.get("usage_limit")
    expires = data.get("expires_at") or None
    is_new = 1 if data.get("is_new_user_only") else 0
    db_execute("INSERT INTO admin_coupon (code, discount_type, discount_value, usage_limit, expires_at, is_new_user_only, created_by) VALUES (%s,%s,%s,%s,%s,%s,%s)", (code, typ, val, int(usage_limit) if str(usage_limit).strip() else None, expires, is_new, current_user_id()))
    audit_log("admin_coupon_created", metadata={"code": code})
    return _admin_json_ok()


@app.put("/api/admin/coupons/<int:coupon_id>")
def api_admin_coupon_update(coupon_id: int):
    r = _admin_require()
    if r:
        return r
    data = request.get_json(silent=True) or {}
    code = (data.get("code") or "").strip().upper()
    typ = (data.get("type") or 'Percentage').strip()
    val = Decimal(str(data.get("discount_value") or 0))
    usage_limit = data.get("usage_limit")
    expires = data.get("expires_at") or None
    is_new = 1 if data.get("is_new_user_only") else 0
    status = (data.get("status") or 'Active').strip()
    db_execute("UPDATE admin_coupon SET code=%s, discount_type=%s, discount_value=%s, usage_limit=%s, expires_at=%s, is_new_user_only=%s, is_active=%s WHERE coupon_id=%s", (code, typ, val, int(usage_limit) if str(usage_limit).strip() else None, expires, is_new, 1 if status=='Active' else 0, coupon_id))
    audit_log("admin_coupon_updated", metadata={"coupon_id": coupon_id, "code": code})
    return _admin_json_ok()


@app.post("/api/admin/coupons/<int:coupon_id>/toggle")
def api_admin_coupon_toggle(coupon_id: int):
    r = _admin_require()
    if r:
        return r
    row = db_fetchone("SELECT is_active FROM admin_coupon WHERE coupon_id=%s", (coupon_id,)) or {}
    new_val = 0 if bool(row.get('is_active')) else 1
    db_execute("UPDATE admin_coupon SET is_active=%s WHERE coupon_id=%s", (new_val, coupon_id))
    audit_log("admin_coupon_toggled", metadata={"coupon_id": coupon_id, "is_active": bool(new_val)})
    return _admin_json_ok(status='Active' if new_val else 'Paused')


@app.delete("/api/admin/coupons/<int:coupon_id>")
def api_admin_coupon_delete(coupon_id: int):
    r = _admin_require()
    if r:
        return r
    db_execute("DELETE FROM admin_coupon WHERE coupon_id=%s", (coupon_id,))
    audit_log("admin_coupon_deleted", metadata={"coupon_id": coupon_id})
    return _admin_json_ok()


@app.post("/api/admin/users/<int:user_id>/toggle")
def api_admin_user_toggle(user_id: int):
    r = _admin_require()
    if r:
        return r
    row = db_fetchone("SELECT is_active FROM user_account WHERE user_id=%s", (user_id,))
    if not row:
        return jsonify({"ok": False, "error": "not_found"}), 404
    new_val = 0 if bool(row.get('is_active')) else 1
    db_execute("UPDATE user_account SET is_active=%s WHERE user_id=%s", (new_val, user_id))
    audit_log("admin_user_toggle", target_user_id=user_id, metadata={"is_active": bool(new_val)})
    send_user_access_email(user_id, bool(new_val))
    return _admin_json_ok(status='Active' if new_val else 'Banned')


@app.post("/api/admin/disputes/<int:dispute_id>/resolve")
def api_admin_dispute_resolve(dispute_id: int):
    r = _admin_require()
    if r:
        return r
    data = request.get_json(silent=True) or {}
    action = (data.get("action") or '').strip()
    if action not in ('Refunded', 'Dismissed'):
        return jsonify({"ok": False, "error": "invalid_action"}), 400
    db_execute("UPDATE admin_dispute SET status=%s, resolved_at=CURRENT_TIMESTAMP, resolved_by=%s WHERE dispute_id=%s", (action, current_user_id(), dispute_id))
    audit_log("admin_dispute_resolved", metadata={"dispute_id": dispute_id, "action": action})
    return _admin_json_ok()


@app.get("/api/admin/logs")
def api_admin_logs():
    r = _admin_require()
    if r:
        return r
    rows = db_fetchall(
        """
        SELECT a.audit_id, a.action, a.created_at, COALESCE(u.name, 'System') AS user
        FROM audit_log a
        LEFT JOIN user_account u ON u.user_id=a.actor_user_id
        ORDER BY a.created_at DESC, a.audit_id DESC
        LIMIT 100
        """
    ) or []
    logs = []
    for r0 in rows:
        logs.append({
            'id': r0.get('audit_id'),
            'action': str(r0.get('action') or '').replace('_', ' ').title(),
            'user': r0.get('user') or 'System',
            'date': (r0.get('created_at').strftime('%b %d') if r0.get('created_at') else ''),
            'time': (r0.get('created_at').strftime('%I:%M %p') if r0.get('created_at') else ''),
        })
    return _admin_json_ok(logs=logs)


@app.post("/api/admin/commission")
def api_admin_commission_save():
    r = _admin_require()
    if r:
        return r
    data = request.get_json(silent=True) or {}
    percentage = Decimal(str(data.get("percentage") or '10'))
    title = (data.get("title") or 'Default Platform Commission').strip() or 'Default Platform Commission'
    db_execute("UPDATE admin_commission_rule SET is_active=0")
    db_execute("INSERT INTO admin_commission_rule (title, percentage, is_active, updated_by) VALUES (%s,%s,1,%s)", (title, percentage, current_user_id()))
    audit_log("admin_commission_saved", metadata={"percentage": str(percentage), "title": title})
    return _admin_json_ok()


@app.post("/api/admin/messages")
def api_admin_message_send():
    r = _admin_require()
    if r:
        return r
    data = request.get_json(silent=True) or {}
    seller_id = int(data.get("seller_id") or 0)
    body = (data.get("body") or '').strip()
    subject = (data.get("subject") or f'Message for seller #{seller_id}').strip()
    if not seller_id or not body:
        return jsonify({"ok": False, "error": "seller_and_body_required"}), 400
    thread = db_fetchone("SELECT thread_id FROM admin_message_thread WHERE seller_id=%s ORDER BY thread_id DESC LIMIT 1", (seller_id,))
    if thread:
        thread_id = int(thread.get('thread_id'))
        db_execute("UPDATE admin_message_thread SET subject=%s, last_message=%s, updated_at=CURRENT_TIMESTAMP WHERE thread_id=%s", (subject, body, thread_id))
    else:
        conn = get_db(); cur = conn.cursor(); cur.execute("INSERT INTO admin_message_thread (seller_id, subject, last_message) VALUES (%s,%s,%s)", (seller_id, subject, body)); conn.commit(); thread_id = cur.lastrowid; conn.close()
    db_execute("INSERT INTO admin_message (thread_id, sender_role, body) VALUES (%s,'admin',%s)", (thread_id, body))
    audit_log("admin_message_sent", target_user_id=seller_id, metadata={"subject": subject})
    return _admin_json_ok()


@app.get("/super-admin/dashboard")
def super_admin_dashboard():
    return render_template("pages/super-admin/dashboard.html")


@app.get("/super-admin/admins")
def super_admin_admins():
    # Keep design unchanged: reuse the single Super Admin dashboard UI
    return redirect(url_for("super_admin_dashboard", tab="admins"))


@app.get("/super-admin/finance")
def super_admin_finance():
    return redirect(url_for("super_admin_dashboard", tab="finance"))


@app.get("/super-admin/system-settings")
def super_admin_system_settings():
    return redirect(url_for("super_admin_dashboard", tab="config"))


# -----------------------
# Super Admin APIs (DB-backed)
# -----------------------


def _rand_password(length: int = 12) -> str:
    # URL-safe, strong enough for temp passwords
    return secrets.token_urlsafe(max(8, length))[:length]


def _rand_security_code(length: int = 8) -> str:
    # Short human-typable code
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # avoid confusing chars
    return "".join(secrets.choice(alphabet) for _ in range(max(6, length)))


@app.get("/api/super-admin/admins")
def api_super_admin_list_admins():
    r = require_role("superadmin")
    if r:
        return r

    rows = db_fetchall(
        """
        SELECT u.user_id, u.name, u.email, u.phone, u.is_active, u.created_at,
               ap.designation
        FROM user_account u
        LEFT JOIN admin_profile ap ON ap.admin_id=u.user_id
        WHERE u.role='admin'
        ORDER BY u.user_id DESC
        """
    )
    out = []
    for row in rows:
        out.append(
            {
                "id": int(row["user_id"]),
                "name": row.get("name") or "",
                "email": row.get("email") or "",
                "phone": row.get("phone") or "",
                "designation": row.get("designation") or "Admin",
                "is_active": bool(row.get("is_active", True)),
                "created_at": (row.get("created_at").isoformat() if row.get("created_at") else None),
            }
        )
    return jsonify({"ok": True, "admins": out})


@app.post("/api/super-admin/admins")
def api_super_admin_create_admin():
    r = require_role("superadmin")
    if r:
        return r

    # Accept both JSON and form-encoded data
    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or request.form.get("name") or "").strip()
    email = (payload.get("email") or request.form.get("email") or "").strip().lower()
    phone = (payload.get("phone") or request.form.get("phone") or "").strip()
    designation = (payload.get("designation") or request.form.get("designation") or "Admin").strip()
    provided_secret = (payload.get("secret_code") or request.form.get("secret_code") or "").strip()

    if not name or not email:
        return jsonify({"ok": False, "error": "name and email are required"}), 400

    # Don't allow role escalation via this endpoint
    existing = db_fetchone("SELECT user_id FROM user_account WHERE email=%s", (email,))
    if existing:
        return jsonify({"ok": False, "error": "email already exists"}), 409

    temp_password = _rand_password(12)
    security_code = provided_secret or _rand_security_code(8)

    pw_hash = generate_password_hash(temp_password)
    sc_hash = generate_password_hash(security_code)

    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO user_account (role, name, email, phone, password_hash, secret_code_hash, is_email_verified, is_active)
            VALUES ('admin', %s, %s, %s, %s, %s, TRUE, TRUE)
            """,
            (name, email, phone or "N/A", pw_hash, sc_hash),
        )
        admin_id = cur.lastrowid
        admin_public_id = issue_public_id('admin', int(admin_id))
        cur.execute(
            "INSERT INTO admin_profile (admin_id, designation) VALUES (%s,%s)",
            (admin_id, designation or "Admin"),
        )
        conn.commit()
    except MySQLError as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return jsonify({"ok": False, "error": f"db_error: {e}"}), 500
    finally:
        try:
            conn.close()
        except Exception:
            pass

    # Send welcome mail (temp password + security code)
    login_url = _base_url().rstrip("/") + url_for("admin_login")
    subject = "Welcome to Origins Bangladesh Admin Portal"
    text = (
        f"Hello {name},\n\n"
        f"Admin ID: {admin_public_id}\n\n"
        "You have been added as an Admin.\n\n"
        f"Login URL: {login_url}\n"
        f"Email: {email}\n"
        f"Temporary Password: {temp_password}\n"
        f"Security Code: {security_code}\n\n"
        "Please login and change your password immediately.\n"
    )
    html = render_email(
        "admin_welcome.html",
        name=name,
        email=email,
        login_url=login_url,
        temp_password=temp_password,
        security_code=security_code,
        designation=designation,
        admin_public_id=admin_public_id,
    )
    send_email(email, subject, text=text, html=html)

    audit_log(
        "admin_created",
        target_user_id=int(admin_id),
        metadata={"email": email, "designation": designation},
    )

    return jsonify({"ok": True, "admin_id": int(admin_id), "public_id": admin_public_id})


@app.post("/api/super-admin/approvals/request")
def api_super_admin_request_approval_code():
    r = require_role("superadmin")
    if r:
        return r

    data = request.get_json(silent=True) or {}
    action_key = (data.get("action_key") or "").strip()
    target_id = data.get("target_user_id")
    try:
        target_id_int = int(target_id) if str(target_id).strip() else None
    except Exception:
        target_id_int = None

    if action_key not in ("admin_permanent_delete",):
        return jsonify({"ok": False, "error": "unsupported_action"}), 400

    actor_id = int(current_user_id() or 0)
    if not actor_id:
        return jsonify({"ok": False, "error": "auth_required"}), 401

    code = _create_action_approval(actor_id=actor_id, action_key=action_key, target_id=target_id_int)

    # Send code to current superadmin email
    row = db_fetchone("SELECT email, name FROM user_account WHERE user_id=%s", (actor_id,))
    to_email = str((row or {}).get("email") or "")
    if to_email:

        ttl = int(get_setting("approval_code_ttl_minutes", "10") or 10)
        default_subject = "Approval code required"
        default_text = f"Your approval code is: {code}\nExpires in {ttl} minutes."
        subject, text_body, html = render_email_bundle(
            "auth_code",
            fallback_template="auth_code.html",
            default_subject=default_subject,
            default_text=default_text,
            title="Approval Code",
            preheader="Confirm a sensitive action",
            otp=code,
            expires_minutes=ttl,
        )
        send_email(to_email, subject, text=text_body, html=html)


    audit_log("approval_code_requested", metadata={"action_key": action_key, "target_user_id": target_id_int})
    return jsonify({"ok": True, "sent_to": (to_email[:3] + "***" if to_email else "")})


@app.post("/api/super-admin/admins/<int:admin_id>/toggle-active")
def api_super_admin_toggle_admin_active(admin_id: int):
    r = require_role("superadmin")
    if r:
        return r

    row = db_fetchone("SELECT is_active, email, name FROM user_account WHERE user_id=%s AND role='admin'", (admin_id,))
    if not row:
        return jsonify({"ok": False, "error": "not_found"}), 404

    data = request.get_json(silent=True) or {}
    reason = (data.get("reason") or request.args.get("reason") or "").strip()

    # premium: reason required for access changes
    if not reason:
        return jsonify({"ok": False, "error": "reason_required"}), 400

    new_val = not bool(row.get("is_active", True))
    db_execute("UPDATE user_account SET is_active=%s WHERE user_id=%s", (new_val, admin_id))
    audit_log("admin_toggled_active", target_user_id=admin_id, metadata={"is_active": new_val, "reason": reason})

    # In-app notification (Super Admin)
    notify_current_superadmin(
        type="admin_access",
        title=("Admin re-activated" if new_val else "Admin suspended"),
        body=f"{row.get('name') or 'Admin'} ({row.get('email') or ''})",
        link="#tab-admins",
        severity=("success" if new_val else "warn"),
        meta={"admin_id": int(admin_id), "is_active": bool(new_val)},
    )

    # Email notification
    try:
        login_url = _base_url().rstrip("/") + url_for("admin_login")
        action_label = "Account re-activated" if new_val else "Account suspended"
        default_subject = f"{action_label} — Origins Bangladesh"
        default_text = f"""Hello {row.get('name')},

Your admin account status was updated: {action_label}.
Time (UTC): {datetime.datetime.utcnow().isoformat()}Z

Admin portal: {login_url}
"""
        subject, text_body, html = render_email_bundle(
            "admin_status_change",
            fallback_template="admin_status_change.html",
            default_subject=default_subject,
            default_text=default_text,
            name=row.get("name") or "Admin",
            email=row.get("email") or "",
            action_label=action_label,
            when_utc=f"{datetime.datetime.utcnow().isoformat()}Z",
            reason=reason,
            login_url=login_url,
            can_login=bool(new_val),
        )
        send_email(str(row.get("email") or ""), subject, text=text_body, html=html)

    except Exception:
        pass

    return jsonify({"ok": True, "is_active": new_val})


@app.put("/api/super-admin/admins/<int:admin_id>")
def api_super_admin_update_admin(admin_id: int):
    r = require_role("superadmin")
    if r:
        return r

    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    phone = (data.get("phone") or "").strip()
    designation = (data.get("designation") or "").strip() or "Admin"

    if not name or not email:
        return jsonify({"ok": False, "error": "name_and_email_required"}), 400

    row = db_fetchone(
        """
        SELECT u.user_id, u.email, u.name, u.phone, ap.designation
        FROM user_account u
        LEFT JOIN admin_profile ap ON ap.admin_id=u.user_id
        WHERE u.user_id=%s AND u.role='admin'
        """,
        (admin_id,),
    )
    if not row:
        return jsonify({"ok": False, "error": "not_found"}), 404

    # Prevent duplicate emails
    other = db_fetchone("SELECT user_id FROM user_account WHERE email=%s AND user_id<>%s", (email, admin_id))
    if other:
        return jsonify({"ok": False, "error": "email_already_exists"}), 409

    db_execute("UPDATE user_account SET name=%s, email=%s, phone=%s WHERE user_id=%s", (name, email, phone or "N/A", admin_id))
    db_execute(
        "INSERT INTO admin_profile (admin_id, designation) VALUES (%s,%s) ON DUPLICATE KEY UPDATE designation=VALUES(designation)",
        (admin_id, designation),
    )
    audit_log(
        "admin_updated",
        target_user_id=admin_id,
        metadata={"old_email": row.get("email"), "new_email": email, "designation": designation},
    )

    # Email: send updated details
    try:
        login_url = _base_url().rstrip("/") + url_for("admin_login")
        default_subject = "Your admin profile was updated"
        default_text = f"""Hello {name},

Your admin profile details were updated by Super Admin.

Name: {name}
Email: {email}
Phone: {phone or 'N/A'}
Designation: {designation}

Admin portal: {login_url}
Time (UTC): {datetime.datetime.utcnow().isoformat()}Z
"""
        subject, text_body, html = render_email_bundle(
            "admin_profile_updated",
            fallback_template="admin_profile_updated.html",
            default_subject=default_subject,
            default_text=default_text,
            name=name,
            email=email,
            phone=phone or "N/A",
            designation=designation,
            login_url=login_url,
            when_utc=f"{datetime.datetime.utcnow().isoformat()}Z",
        )
        send_email(email, subject, text=text_body, html=html)
    except Exception:
        pass

    notify_current_superadmin(
        type="admin_update",
        title="Admin updated",
        body=f"{name} ({email})",
        link="#tab-admins",
        severity="info",
        meta={"admin_id": int(admin_id)},
    )

    return jsonify({"ok": True})


@app.get("/api/super-admin/admins/<int:admin_id>/permissions")
def api_super_admin_get_admin_permissions(admin_id: int):
    r = require_role("superadmin")
    if r:
        return r
    # Ensure admin exists
    row = db_fetchone("SELECT user_id FROM user_account WHERE user_id=%s AND role='admin'", (admin_id,))
    if not row:
        return jsonify({"ok": False, "error": "not_found"}), 404

    rows = db_fetchall(
        "SELECT module_key, can_view, can_edit FROM admin_permission WHERE admin_id=%s ORDER BY module_key",
        (admin_id,),
    )
    perms = []
    for r0 in rows:
        perms.append(
            {
                "module": r0.get("module_key") or "",
                "can_view": bool(r0.get("can_view")),
                "can_edit": bool(r0.get("can_edit")),
            }
        )
    return jsonify({"ok": True, "permissions": perms})


@app.put("/api/super-admin/admins/<int:admin_id>/permissions")
def api_super_admin_set_admin_permissions(admin_id: int):
    r = require_role("superadmin")
    if r:
        return r
    row = db_fetchone("SELECT user_id FROM user_account WHERE user_id=%s AND role='admin'", (admin_id,))
    if not row:
        return jsonify({"ok": False, "error": "not_found"}), 404

    data = request.get_json(silent=True) or {}
    items = data.get("permissions") or []
    if not isinstance(items, list):
        return jsonify({"ok": False, "error": "invalid_payload"}), 400

    # Upsert each permission
    for it in items:
        try:
            module = str(it.get("module") or "").strip()[:60]
            if not module:
                continue
            can_view = 1 if bool(it.get("can_view")) else 0
            can_edit = 1 if bool(it.get("can_edit")) else 0
            db_execute(
                """
                INSERT INTO admin_permission (admin_id, module_key, can_view, can_edit)
                VALUES (%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE can_view=VALUES(can_view), can_edit=VALUES(can_edit)
                """,
                (admin_id, module, can_view, can_edit),
            )
        except Exception:
            continue

    audit_log("admin_permissions_updated", target_user_id=admin_id, metadata={"count": len(items)})
    notify_current_superadmin(type="admin_permissions", title="Permissions updated", body=f"Admin ID {admin_id}", link="#tab-admins")
    return jsonify({"ok": True})


@app.post("/api/super-admin/admins/<int:admin_id>/reset-credentials")
def api_super_admin_reset_admin_credentials(admin_id: int):
    r = require_role("superadmin")
    if r:
        return r

    row = db_fetchone(
        """
        SELECT u.email, u.name, ap.designation
        FROM user_account u
        LEFT JOIN admin_profile ap ON ap.admin_id=u.user_id
        WHERE u.user_id=%s AND u.role='admin'
        """,
        (admin_id,),
    )
    if not row:
        return jsonify({"ok": False, "error": "not_found"}), 404

    temp_password = _rand_password(12)
    security_code = _rand_security_code(8)
    db_execute(
        "UPDATE user_account SET password_hash=%s, secret_code_hash=%s WHERE user_id=%s",
        (generate_password_hash(temp_password), generate_password_hash(security_code), admin_id),
    )
    login_url = _base_url().rstrip("/") + url_for("admin_login")
    default_subject = "Your Admin Credentials Were Reset"
    default_text = f"""Hello {row.get('name')},

Your admin credentials have been reset by Super Admin.

Login URL: {login_url}
Email: {row.get('email')}
Temporary Password: {temp_password}
Security Code: {security_code}

Please login and change your password immediately.
"""
    subject, text_body, html = render_email_bundle(
        "admin_welcome",
        fallback_template="admin_welcome.html",
        default_subject=default_subject,
        default_text=default_text,
        name=row.get("name") or "Admin",
        email=row.get("email") or "",
        login_url=login_url,
        temp_password=temp_password,
        security_code=security_code,
        designation=row.get("designation") or "Admin",
        is_reset=True,
    )
    send_email(str(row.get("email") or ""), subject, text=text_body, html=html)
    audit_log("admin_reset_credentials", target_user_id=admin_id, metadata={"email": row.get("email")})
    return jsonify({"ok": True})


@app.delete("/api/super-admin/admins/<int:admin_id>")
def api_super_admin_soft_delete_admin(admin_id: int):
    r = require_role("superadmin")
    if r:
        return r

    row = db_fetchone("SELECT user_id, email, name FROM user_account WHERE user_id=%s AND role='admin'", (admin_id,))
    if not row:
        return jsonify({"ok": False, "error": "not_found"}), 404

    data = request.get_json(silent=True) or {}
    reason = (data.get("reason") or request.args.get("reason") or "").strip()

    # Soft delete = deactivate (keeps referential integrity & auditability)
    db_execute("UPDATE user_account SET is_active=FALSE WHERE user_id=%s", (admin_id,))
    audit_log("admin_deactivated", target_user_id=admin_id, metadata={"reason": reason})

    # Email notification
    try:
        login_url = _base_url().rstrip("/") + url_for("admin_login")
        action_label = "Account deactivated (soft delete)"
        default_subject = f"{action_label} — Origins Bangladesh"
        default_text = f"""Hello {row.get('name')},

Your admin account was deactivated by Super Admin.
Time (UTC): {datetime.datetime.utcnow().isoformat()}Z
If you think this was a mistake, contact support.
"""
        subject, text_body, html = render_email_bundle(
            "admin_status_change",
            fallback_template="admin_status_change.html",
            default_subject=default_subject,
            default_text=default_text,
            name=row.get("name") or "Admin",
            email=row.get("email") or "",
            action_label=action_label,
            when_utc=f"{datetime.datetime.utcnow().isoformat()}Z",
            reason=reason,
            login_url=login_url,
            can_login=False,
        )
        send_email(str(row.get("email") or ""), subject, text=text_body, html=html)

    except Exception:
        pass

    return jsonify({"ok": True})


@app.delete("/api/super-admin/admins/<int:admin_id>/permanent")
def api_super_admin_permanent_delete_admin(admin_id: int):
    data = request.get_json(silent=True) or {}
    reason = (data.get("reason") or request.args.get("reason") or "").strip()
    approval_code = (data.get("approval_code") or request.args.get("approval_code") or "").strip()

    # Optional 2-step approval workflow
    if get_setting("approval_required_permanent_delete", "1") == "1":
        if not approval_code:
            return jsonify({"ok": False, "error": "approval_code_required"}), 409
        if not _consume_action_approval(actor_id=int(current_user_id() or 0), action_key="admin_permanent_delete", target_id=admin_id, code=approval_code):
            return jsonify({"ok": False, "error": "invalid_or_expired_approval_code"}), 409

    r = require_role("superadmin")
    if r:
        return r

    row = db_fetchone(
        "SELECT user_id, email, name FROM user_account WHERE user_id=%s AND role='admin'",
        (admin_id,),
    )
    if not row:
        return jsonify({"ok": False, "error": "not_found"}), 404

    # Safety: block permanent delete if referenced as an order buyer (schema uses RESTRICT)
    try:
        cnt = db_fetchone("SELECT COUNT(*) AS c FROM `order` WHERE buyer_id=%s", (admin_id,))
        if int(cnt.get("c") or 0) > 0:
            return jsonify({"ok": False, "error": "has_orders_cannot_delete"}), 409
    except Exception:
        # if order table missing, ignore
        pass

    # Notify before deletion
    try:
        action_label = "Account permanently deleted"
        default_subject = f"{action_label} — Origins Bangladesh"
        default_text = f"""Hello {row.get('name')},

Your admin account was permanently removed by Super Admin.
Time (UTC): {datetime.datetime.utcnow().isoformat()}Z
"""
        subject, text_body, html = render_email_bundle(
            "admin_status_change",
            fallback_template="admin_status_change.html",
            default_subject=default_subject,
            default_text=default_text,
            name=row.get("name") or "Admin",
            email=row.get("email") or "",
            action_label=action_label,
            when_utc=f"{datetime.datetime.utcnow().isoformat()}Z",
            reason=reason,
            login_url="",
            can_login=False,
        )
        send_email(str(row.get("email") or ""), subject, text=text_body, html=html)

    except Exception:
        pass

    # Hard delete from DB
    db_execute("DELETE FROM user_account WHERE user_id=%s AND role='admin'", (admin_id,))
    audit_log("admin_deleted_permanent", target_user_id=admin_id, metadata={"reason": reason})
    return jsonify({"ok": True})


@app.get("/api/super-admin/audit")
def api_super_admin_audit():
    r = require_role("superadmin")
    if r:
        return r

    # Cursor pagination + filters (for infinite scroll)
    try:
        limit = int(request.args.get("limit") or 20)
    except Exception:
        limit = 20
    limit = max(10, min(50, limit))

    cursor = (request.args.get("cursor") or "").strip()
    action_f = (request.args.get("action") or "").strip()
    actor_q = (request.args.get("actor") or "").strip()
    date_from = (request.args.get("date_from") or "").strip()
    date_to = (request.args.get("date_to") or "").strip()

    where = ["1=1"]
    params: List[Any] = []
    if cursor:
        try:
            where.append("a.audit_id < %s")
            params.append(int(cursor))
        except Exception:
            pass
    if action_f:
        where.append("a.action=%s")
        params.append(action_f)
    if actor_q:
        where.append("(au.name LIKE %s OR au.email LIKE %s)")
        like = f"%{actor_q}%"
        params.extend([like, like])
    if date_from:
        where.append("a.created_at >= %s")
        params.append(date_from)
    if date_to:
        where.append("a.created_at <= %s")
        params.append(date_to)

    rows = db_fetchall(
        f"""
        SELECT a.audit_id, a.action, a.created_at, a.target_user_id,
               au.name AS actor_name, tu.name AS target_name
        FROM audit_log a
        LEFT JOIN user_account au ON au.user_id=a.actor_user_id
        LEFT JOIN user_account tu ON tu.user_id=a.target_user_id
        WHERE {' AND '.join(where)}
        ORDER BY a.audit_id DESC
        LIMIT {limit}
        """,
        tuple(params),
    )
    out = []
    for r0 in rows:
        out.append(
            {
                "id": int(r0["audit_id"]),
                "action": r0.get("action") or "",
                "actor": r0.get("actor_name") or "",
                "target": r0.get("target_name") or "",
                "created_at": (r0.get("created_at").isoformat() if r0.get("created_at") else None),
            }
        )

    next_cursor = str(out[-1]["id"]) if out else ""
    return jsonify({"ok": True, "items": out, "next_cursor": next_cursor, "limit": limit})


@app.get("/api/super-admin/notifications")
def api_super_admin_notifications_list():
    r = require_role("superadmin")
    if r:
        return r
    uid = int(current_user_id() or 0)
    try:
        limit = int(request.args.get("limit") or 12)
    except Exception:
        limit = 12
    limit = max(5, min(30, limit))

    rows = db_fetchall(
        """
        SELECT notification_id, type, severity, title, body, link, is_read, created_at
        FROM notification
        WHERE recipient_user_id=%s
        ORDER BY notification_id DESC
        LIMIT %s
        """,
        (uid, limit),
    )
    unread = db_fetchone(
        "SELECT COUNT(*) AS c FROM notification WHERE recipient_user_id=%s AND is_read=0",
        (uid,),
    )["c"]
    out = []
    for n0 in rows:
        out.append(
            {
                "id": int(n0["notification_id"]),
                "type": n0.get("type") or "event",
                "severity": n0.get("severity") or "info",
                "title": n0.get("title") or "",
                "body": n0.get("body") or "",
                "link": n0.get("link") or "",
                "is_read": bool(n0.get("is_read")),
                "created_at": (n0.get("created_at").isoformat() if n0.get("created_at") else None),
            }
        )
    return jsonify({"ok": True, "items": out, "unread": int(unread)})


@app.post("/api/super-admin/notifications/mark-read")
def api_super_admin_notifications_mark_read():
    r = require_role("superadmin")
    if r:
        return r
    uid = int(current_user_id() or 0)
    data = request.get_json(silent=True) or {}
    nid = data.get("id")
    try:
        nid_int = int(nid)
    except Exception:
        return jsonify({"ok": False, "error": "invalid_id"}), 400
    db_execute(
        "UPDATE notification SET is_read=1, read_at=NOW() WHERE notification_id=%s AND recipient_user_id=%s",
        (nid_int, uid),
    )
    return jsonify({"ok": True})


@app.post("/api/super-admin/notifications/clear")
def api_super_admin_notifications_clear_all():
    r = require_role("superadmin")
    if r:
        return r
    uid = int(current_user_id() or 0)
    db_execute(
        "UPDATE notification SET is_read=1, read_at=NOW() WHERE recipient_user_id=%s AND is_read=0",
        (uid,),
    )
    return jsonify({"ok": True})


@app.get("/api/super-admin/finance/summary")
def api_super_admin_finance_summary():
    r = require_role("superadmin")
    if r:
        return r

    row = db_fetchone(
        """
        SELECT
          COALESCE(SUM(total_bdt),0) AS sales_bdt,
          COALESCE(SUM(CASE WHEN status IN ('paid','shipped','delivered') THEN total_bdt ELSE 0 END),0) AS settled_bdt,
          COALESCE(COUNT(*),0) AS orders_total,
          COALESCE(SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END),0) AS pending_orders
        FROM `order`
        """
    )
    sales_bdt = Decimal(str(row.get("sales_bdt") or "0"))
    settled_bdt = Decimal(str(row.get("settled_bdt") or "0"))

    # Platform fee (configurable) — keeps it deterministic and “real”
    fee_rate = Decimal(str(app.config.get("PLATFORM_FEE_RATE") or "0.10"))
    fee_rate = max(Decimal("0"), min(Decimal("0.50"), fee_rate))
    platform_fee_bdt = (settled_bdt * fee_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return jsonify(
        {
            "ok": True,
            "sales_bdt": str(sales_bdt),
            "settled_bdt": str(settled_bdt),
            "platform_fee_bdt": str(platform_fee_bdt),
            "orders_total": int(row.get("orders_total") or 0),
            "pending_orders": int(row.get("pending_orders") or 0),
        }
    )


@app.get("/api/super-admin/finance/revenue")
def api_super_admin_finance_revenue():
    r = require_role("superadmin")
    if r:
        return r

    period = (request.args.get("period") or "Yearly").strip().lower()
    if period not in ("yearly", "monthly"):
        period = "yearly"

    if period == "monthly":
        rows = db_fetchall(
            """
            SELECT DATE_FORMAT(created_at, '%Y-%m') AS ym,
                   COALESCE(SUM(CASE WHEN status IN ('paid','shipped','delivered') THEN total_bdt ELSE 0 END),0) AS total
            FROM `order`
            WHERE created_at >= DATE_SUB(UTC_TIMESTAMP(), INTERVAL 12 MONTH)
            GROUP BY ym
            ORDER BY ym
            """
        )
        labels = [r0["ym"] for r0 in rows]
        values = [float(r0["total"] or 0) for r0 in rows]
        return jsonify({"ok": True, "period": "Monthly", "labels": labels, "values": values})

    rows = db_fetchall(
        """
        SELECT YEAR(created_at) AS yy,
               COALESCE(SUM(CASE WHEN status IN ('paid','shipped','delivered') THEN total_bdt ELSE 0 END),0) AS total
        FROM `order`
        WHERE created_at >= DATE_SUB(UTC_TIMESTAMP(), INTERVAL 5 YEAR)
        GROUP BY yy
        ORDER BY yy
        """
    )
    labels = [str(int(r0["yy"])) for r0 in rows]
    values = [float(r0["total"] or 0) for r0 in rows]
    return jsonify({"ok": True, "period": "Yearly", "labels": labels, "values": values})


@app.get("/api/super-admin/system/status")
def api_super_admin_system_status():
    r = require_role("superadmin")
    if r:
        return r
    maintenance = get_setting("maintenance_mode", "0") == "1"
    debug = get_setting("debug_mode", "0") == "1"
    return jsonify({"ok": True, "maintenance": maintenance, "debug": debug})


@app.post("/api/super-admin/system/maintenance")
def api_super_admin_toggle_maintenance():
    r = require_role("superadmin")
    if r:
        return r
    current = get_setting("maintenance_mode", "0")
    new_val = "0" if current == "1" else "1"
    set_setting("maintenance_mode", new_val)
    audit_log("system_maintenance_toggled", metadata={"maintenance": new_val})
    return jsonify({"ok": True, "maintenance": new_val == "1"})


@app.post("/api/super-admin/system/cache/clear")
def api_super_admin_clear_cache():
    r = require_role("superadmin")
    if r:
        return r
    try:
        _ATLAS_CACHE["ts"] = 0.0
        _ATLAS_CACHE["data"] = None
        _ATLAS_CACHE["etag"] = None
    except Exception:
        pass
    audit_log("system_cache_cleared")
    return jsonify({"ok": True})


@app.get("/api/super-admin/report.txt")
def api_super_admin_report_txt():
    r = require_role("superadmin")
    if r:
        return r

    # Small plain-text report for export button.
    finance = api_super_admin_finance_summary().get_json()  # type: ignore
    admins = api_super_admin_list_admins().get_json()  # type: ignore
    maintenance = get_setting("maintenance_mode", "0")
    lines = []
    lines.append("Origins Bangladesh — Super Admin Report")
    lines.append(f"Generated (UTC): {datetime.datetime.utcnow().isoformat()}Z")
    lines.append("")
    lines.append("System")
    lines.append(f"- Maintenance mode: {'ON' if maintenance=='1' else 'OFF'}")
    lines.append("")
    lines.append("Finance")
    lines.append(f"- Settled sales (BDT): {finance.get('settled_bdt')}")
    lines.append(f"- Platform fee (BDT): {finance.get('platform_fee_bdt')}")
    lines.append(f"- Orders total: {finance.get('orders_total')}")
    lines.append(f"- Pending orders: {finance.get('pending_orders')}")
    lines.append("")
    lines.append("Admin Accounts")
    lines.append(f"- Total admins: {len((admins.get('admins') or []))}")
    lines.append("")
    return Response("\n".join(lines), mimetype="text/plain")


def _collect_report_data() -> Dict[str, Any]:
    """Collect all data needed for premium exports (PDF/XLSX)."""
    finance = api_super_admin_finance_summary().get_json()  # type: ignore
    admins = api_super_admin_list_admins().get_json()  # type: ignore
    status = api_super_admin_system_status().get_json()  # type: ignore
    scan = api_super_admin_security_scan().get_json()  # type: ignore

    revenue_month = {"labels": [], "values": []}
    try:
        rows = db_fetchall(
            """
            SELECT DATE_FORMAT(created_at, '%Y-%m') AS ym,
                   COALESCE(SUM(CASE WHEN status IN ('paid','shipped','delivered') THEN total_bdt ELSE 0 END),0) AS total
            FROM `order`
            WHERE created_at >= DATE_SUB(UTC_TIMESTAMP(), INTERVAL 12 MONTH)
            GROUP BY ym
            ORDER BY ym
            """
        )
        revenue_month["labels"] = [r0["ym"] for r0 in rows]
        revenue_month["values"] = [float(r0["total"] or 0) for r0 in rows]
    except Exception:
        pass

    return {
        "finance": finance,
        "admins": admins,
        "status": status,
        "scan": scan,
        "revenue_month": revenue_month,
    }


def _register_report_export(*, fmt: str, file_rel: str, meta: Dict[str, Any]) -> str:
    """Store exported file metadata and return a short verification code."""
    code = secrets.token_hex(16)
    try:
        db_execute(
            "INSERT INTO report_export (report_code, format, file_path, created_by, meta_json) VALUES (%s,%s,%s,%s,%s)",
            (code, fmt, file_rel, current_user_id(), json.dumps(meta or {}, ensure_ascii=False)),
        )
    except Exception:
        # Best effort
        pass
    return code


def _pdf_header_footer(canvas, doc):
    canvas.saveState()
    w, h = A4

    org_name = get_setting("brand_org_name", "Origins Bangladesh")
    watermark = get_setting("brand_watermark_text", "CONFIDENTIAL")
    logo_rel = get_setting("brand_logo_path", "static/assets/img/brand_logo.png")
    logo_abs = os.path.join(app.root_path, logo_rel)

    # Watermark (subtle)
    try:
        if watermark:
            if hasattr(canvas, "setFillAlpha"):
                canvas.setFillAlpha(0.06)
            canvas.setFont("Helvetica-Bold", 52)
            canvas.setFillColor(colors.HexColor("#0f172a"))
            canvas.saveState()
            canvas.translate(w / 2, h / 2)
            canvas.rotate(30)
            canvas.drawCentredString(0, 0, watermark[:40])
            canvas.restoreState()
            if hasattr(canvas, "setFillAlpha"):
                canvas.setFillAlpha(1)
    except Exception:
        pass

    # Top accent bar
    canvas.setFillColorRGB(0.06, 0.09, 0.16)  # slate-ish
    canvas.rect(0, h - 18 * mm, w, 18 * mm, stroke=0, fill=1)

    # Logo (image preferred)
    drew_logo = False
    try:
        if os.path.exists(logo_abs):
            canvas.drawImage(logo_abs, 10 * mm, h - 15.5 * mm, width=10 * mm, height=10 * mm, mask='auto')
            drew_logo = True
    except Exception:
        drew_logo = False
    if not drew_logo:
        # Minimal vector mark fallback
        canvas.setFillColor(colors.HexColor("#6366f1"))
        canvas.circle(10 * mm, h - 9 * mm, 3.2 * mm, stroke=0, fill=1)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 8)
        canvas.drawCentredString(10 * mm, h - 11.2 * mm, "O")

    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(22 * mm if drew_logo else 16 * mm, h - 12 * mm, f"{org_name} — Super Admin Report")

    # Optional verification QR (if report_code is present)
    report_code = getattr(doc, "report_code", None)
    verify_url = getattr(doc, "verify_url", None)
    if report_code and verify_url:
        try:
            qr = QrCodeWidget(str(verify_url))
            bounds = qr.getBounds()
            size = 12 * mm
            w0 = bounds[2] - bounds[0]
            h0 = bounds[3] - bounds[1]
            d = Drawing(size, size, transform=[size / w0, 0, 0, size / h0, 0, 0])
            d.add(qr)
            renderPDF.draw(d, canvas, w - 14 * mm - size, h - 15.5 * mm)
        except Exception:
            pass

    # Footer
    canvas.setFillColorRGB(0.42, 0.45, 0.52)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(14 * mm, 10 * mm, f"Generated (UTC): {datetime.datetime.utcnow().isoformat()}Z")
    if report_code:
        canvas.drawString(14 * mm, 6 * mm, f"Verification Code: {report_code}")
    canvas.drawRightString(w - 14 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


@app.get("/api/super-admin/report.pdf")
def api_super_admin_report_pdf():
    r = require_role("superadmin")
    if r:
        return r

    os.makedirs(os.path.join(app.root_path, "exports"), exist_ok=True)
    ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_rel = f"exports/Origins_SuperAdmin_Report_{ts}.pdf"
    out_abs = os.path.join(app.root_path, out_rel)

    data = _collect_report_data()
    finance = data["finance"]
    admins = data["admins"]
    status = data["status"]
    scan = data["scan"]
    revenue_month = data["revenue_month"]

    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "title",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=20,
        spaceAfter=10,
        textColor=colors.HexColor("#0f172a"),
    )
    h2 = ParagraphStyle(
        "h2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=8,
        spaceAfter=6,
    )
    body = ParagraphStyle(
        "body",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=12,
        textColor=colors.HexColor("#0b1220"),
    )

    doc = SimpleDocTemplate(
        out_abs,
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=24 * mm,
        bottomMargin=16 * mm,
        title="Origins Super Admin Report",
        author="Origins Bangladesh",
    )

    story = []
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph("Executive Summary", title))
    story.append(
        Paragraph(
            "A consolidated operational + finance snapshot for platform leadership. Generated automatically from live database metrics and Super Admin controls.",
            body,
        )
    )
    story.append(Spacer(1, 6 * mm))

    # KPI cards (as a table)
    kpis = [
        ["Settled Sales (BDT)", str(finance.get("settled_bdt"))],
        ["Platform Fee (BDT)", str(finance.get("platform_fee_bdt"))],
        ["Orders (Total)", str(finance.get("orders_total"))],
        ["Pending Orders", str(finance.get("pending_orders"))],
        ["Maintenance Mode", "ON" if status.get("maintenance") else "OFF"],
        ["Debug Mode", "ON" if status.get("debug") else "OFF"],
    ]
    t = Table(kpis, colWidths=[70 * mm, 90 * mm])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#e2e8f0")),
                ("INNERGRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#e2e8f0")),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#0f172a")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(t)
    story.append(Spacer(1, 8 * mm))

    # Revenue chart
    story.append(Paragraph("Revenue Trend", h2))
    labels = (revenue_month or {}).get("labels") or []
    values = (revenue_month or {}).get("values") or []
    values = [float(v or 0) for v in values][:12]
    labels = [str(x) for x in labels][:12]
    if values:
        d = Drawing(180 * mm, 55 * mm)
        # Card background
        d.add(Rect(0, 0, 180 * mm, 55 * mm, rx=8, ry=8, fillColor=colors.HexColor("#ffffff"), strokeColor=colors.HexColor("#e2e8f0")))
        bc = VerticalBarChart()
        bc.x = 8 * mm
        bc.y = 10 * mm
        bc.height = 40 * mm
        bc.width = 165 * mm
        bc.data = [values]
        bc.valueAxis.valueMin = 0
        bc.valueAxis.labels.fontSize = 7
        bc.categoryAxis.labels.fontSize = 7
        bc.categoryAxis.categoryNames = labels
        bc.barSpacing = 2
        bc.groupSpacing = 6
        # No explicit colors (keeps it compatible); outline only
        bc.bars.strokeWidth = 0
        d.add(bc)
        d.add(String(8 * mm, 48 * mm, "Settled revenue (Monthly)", fontName="Helvetica-Bold", fontSize=9, fillColor=colors.HexColor("#0f172a")))
        story.append(d)
    else:
        story.append(Paragraph("No revenue history found for the selected window.", body))
    story.append(Spacer(1, 6 * mm))

    # Admin section
    story.append(Paragraph("Admin Accounts", h2))
    admin_rows = (admins.get("admins") or [])
    admin_table_data = [["Name", "Email", "Designation", "Active"]]
    for a in admin_rows[:25]:
        admin_table_data.append(
            [
                str(a.get("full_name") or ""),
                str(a.get("email") or ""),
                str(a.get("designation") or "Admin"),
                "YES" if a.get("is_active") else "NO",
            ]
        )
    at = Table(admin_table_data, colWidths=[45 * mm, 55 * mm, 45 * mm, 20 * mm])
    at.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
                ("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#e2e8f0")),
                ("FONTSIZE", (0, 1), (-1, -1), 8.5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(at)
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("Note: list truncated to 25 admins for readability.", ParagraphStyle("note", parent=body, textColor=colors.HexColor("#475569"), fontSize=8.5)))

    # Compliance / Audit
    story.append(PageBreak())
    story.append(Paragraph("Security & Compliance Snapshot", title))
    story.append(Paragraph(f"Pending payout requests: {scan.get('pending_payouts')}", body))
    story.append(Paragraph(f"Inactive admin accounts: {scan.get('inactive_admins')}", body))
    story.append(Paragraph(f"DB usage: {scan.get('db_percent_used')}%", body))
    story.append(Spacer(1, 4 * mm))

    anomalies = scan.get("anomalies") or []
    if anomalies:
        story.append(Paragraph("Detected anomalies", h2))
        an_tbl = [["Type", "Message"]] + [[a.get("type"), a.get("message")] for a in anomalies]
        an = Table(an_tbl, colWidths=[45 * mm, 120 * mm])
        an.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#e2e8f0")),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#fff7ed")),
                    ("FONTSIZE", (0, 1), (-1, -1), 8.5),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(an)
    else:
        story.append(Paragraph("No anomalies detected by current rules.", body))

    # Signature block
    story.append(Spacer(1, 10 * mm))
    sig_name = get_setting("brand_signature_name", "Authorized Signatory")
    sig_title = get_setting("brand_signature_title", "Super Admin Office")
    sig_tbl = Table(
        [
            [Paragraph("Digitally issued by", body)],
            [Paragraph(f"<b>{sig_name}</b><br/>{sig_title}", body)],
        ],
        colWidths=[80 * mm],
    )
    sig_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#e2e8f0")),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(sig_tbl)

    # Register + enable QR verification
    verify_code = _register_report_export(fmt="pdf", file_rel=out_rel, meta={"ts": ts})
    verify_url = _base_url().rstrip("/") + url_for("api_super_admin_verify_report", code=verify_code)
    doc.report_code = verify_code  # type: ignore
    doc.verify_url = verify_url  # type: ignore

    doc.build(story, onFirstPage=_pdf_header_footer, onLaterPages=_pdf_header_footer)
    audit_log("report_exported_pdf", metadata={"file": out_rel, "code": verify_code})
    return send_file(out_abs, as_attachment=True, download_name=os.path.basename(out_abs))


@app.get("/api/super-admin/report/verify/<code>")
def api_super_admin_verify_report(code: str):
    r = require_role("superadmin")
    if r:
        return r
    row = db_fetchone(
        "SELECT report_code, format, file_path, created_at, created_by, meta_json FROM report_export WHERE report_code=%s",
        (code,),
    )
    if not row:
        return jsonify({"ok": False, "error": "not_found"}), 404
    return jsonify(
        {
            "ok": True,
            "code": row.get("report_code"),
            "format": row.get("format"),
            "file": row.get("file_path"),
            "created_at": (row.get("created_at").isoformat() if row.get("created_at") else None),
            "created_by": row.get("created_by"),
            "meta": json.loads(row.get("meta_json") or "{}"),
        }
    )


@app.get("/api/super-admin/report.xlsx")
def api_super_admin_report_xlsx():
    r = require_role("superadmin")
    if r:
        return r

    data = _collect_report_data()
    finance = data["finance"]
    admins = data["admins"].get("admins") or []
    status = data["status"]
    scan = data["scan"]
    rev = data["revenue_month"]

    os.makedirs(os.path.join(app.root_path, "exports"), exist_ok=True)
    ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_rel = f"exports/Origins_SuperAdmin_Report_{ts}.xlsx"
    out_abs = os.path.join(app.root_path, out_rel)

    wb = Workbook()
    ws = wb.active
    ws.title = "Executive"

    # Styles
    head_fill = PatternFill("solid", fgColor="0F172A")
    sub_fill = PatternFill("solid", fgColor="F1F5F9")
    bold = Font(bold=True)
    white_bold = Font(bold=True, color="FFFFFF")
    center = Alignment(horizontal="center", vertical="center")
    left = Alignment(horizontal="left", vertical="center", wrap_text=True)
    thin = Side(style="thin", color="E2E8F0")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    ws["A1"] = "Origins Bangladesh — Super Admin Report"
    ws["A1"].font = Font(bold=True, size=16)
    ws.merge_cells("A1:D1")
    ws["A2"] = f"Generated (UTC): {datetime.datetime.utcnow().isoformat()}Z"
    ws.merge_cells("A2:D2")
    ws["A4"] = "Key Metrics"
    ws["A4"].font = Font(bold=True, size=12)
    ws.merge_cells("A4:D4")

    kpi_rows = [
        ("Settled Sales (BDT)", str(finance.get("settled_bdt"))),
        ("Platform Fee (BDT)", str(finance.get("platform_fee_bdt"))),
        ("Orders (Total)", str(finance.get("orders_total"))),
        ("Pending Orders", str(finance.get("pending_orders"))),
        ("Maintenance Mode", "ON" if status.get("maintenance") else "OFF"),
        ("Debug Mode", "ON" if status.get("debug") else "OFF"),
        ("DB usage", f"{scan.get('db_percent_used')}%"),
    ]
    start = 5
    for i, (k, v) in enumerate(kpi_rows):
        r0 = start + i
        ws[f"A{r0}"] = k
        ws[f"B{r0}"] = v
        ws[f"A{r0}"].font = bold
        for c in ("A", "B"):
            ws[f"{c}{r0}"].alignment = left
            ws[f"{c}{r0}"].border = border

    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 22
    ws.column_dimensions["C"].width = 20
    ws.column_dimensions["D"].width = 20

    # Revenue sheet
    ws2 = wb.create_sheet("Revenue")
    ws2.append(["Month", "Settled Revenue (BDT)"])
    for cell in ws2[1]:
        cell.fill = head_fill
        cell.font = white_bold
        cell.alignment = center
        cell.border = border
    for m, v in zip(rev.get("labels") or [], rev.get("values") or []):
        ws2.append([str(m), float(v or 0)])
    for row in ws2.iter_rows(min_row=2, max_col=2):
        for cell in row:
            cell.border = border
            cell.alignment = left
    ws2.column_dimensions["A"].width = 14
    ws2.column_dimensions["B"].width = 22

    # Admin sheet
    ws3 = wb.create_sheet("Admins")
    ws3.append(["Name", "Email", "Designation", "Active"])
    for cell in ws3[1]:
        cell.fill = head_fill
        cell.font = white_bold
        cell.alignment = center
        cell.border = border
    for a in admins:
        ws3.append([
            str(a.get("name") or ""),
            str(a.get("email") or ""),
            str(a.get("designation") or "Admin"),
            "YES" if a.get("is_active") else "NO",
        ])
    for row in ws3.iter_rows(min_row=2, max_col=4):
        for cell in row:
            cell.border = border
            cell.alignment = left
    for i, w in enumerate([22, 30, 20, 10], start=1):
        ws3.column_dimensions[get_column_letter(i)].width = w

    # Anomalies sheet
    ws4 = wb.create_sheet("Security")
    ws4.append(["Type", "Message"])
    for cell in ws4[1]:
        cell.fill = head_fill
        cell.font = white_bold
        cell.alignment = center
        cell.border = border
    anomalies = scan.get("anomalies") or []
    if anomalies:
        for a in anomalies:
            ws4.append([str(a.get("type") or ""), str(a.get("message") or "")])
    else:
        ws4.append(["OK", "No anomalies detected by current rules."])
    for row in ws4.iter_rows(min_row=2, max_col=2):
        for cell in row:
            cell.border = border
            cell.alignment = left
    ws4.column_dimensions["A"].width = 18
    ws4.column_dimensions["B"].width = 72

    wb.save(out_abs)

    verify_code = _register_report_export(fmt="xlsx", file_rel=out_rel, meta={"ts": ts})
    audit_log("report_exported_xlsx", metadata={"file": out_rel, "code": verify_code})
    return send_file(out_abs, as_attachment=True, download_name=os.path.basename(out_abs))



# -----------------------
# Super Admin: Dashboard + Payouts + Security & DB (DB-based)
# -----------------------

@app.get("/api/super-admin/dashboard/summary")
def api_super_admin_dashboard_summary():
    r = require_role("superadmin")
    if r:
        return r

    active_admins = db_fetchone(
        "SELECT COUNT(*) AS c FROM user_account WHERE role='admin' AND is_active=1"
    )["c"]
    total_admins = db_fetchone("SELECT COUNT(*) AS c FROM user_account WHERE role='admin'")["c"]
    pending_payouts = db_fetchone(
        "SELECT COUNT(*) AS c FROM payout_request WHERE status='Pending'"
    )["c"]

    live_traffic = 0
    try:
        live_traffic = db_fetchone(
            "SELECT COUNT(*) AS c FROM `order` WHERE created_at >= (NOW() - INTERVAL 15 MINUTE)"
        )["c"]
    except Exception:
        live_traffic = 0


    # DB health: basic ping
    db_ok = True
    try:
        db_fetchone("SELECT 1 AS ok")
    except Exception:
        db_ok = False

    last_backup = db_fetchone(
        "SELECT backup_id, started_at, finished_at, status FROM backup_log ORDER BY backup_id DESC LIMIT 1"
    )

    # Revenue metric shown in dashboard header
    settled_bdt = _finance_settled_bdt()

    return jsonify(
        {
            "active_admins": int(active_admins),
            "total_admins": int(total_admins),
            "pending_payouts": int(pending_payouts),
            "settled_bdt": str(settled_bdt),
            "maintenance_mode": get_setting("maintenance_mode", "0"),
            "debug_mode": get_setting("debug_mode", "0"),
            "ai_provider": get_setting("ai_provider", "openai"),
            "db_ok": db_ok,
            "last_backup": last_backup,
            "live_traffic": int(live_traffic),
        }
    )


@app.get("/api/super-admin/payouts")
def api_super_admin_list_payouts():
    r = require_role("superadmin")
    if r:
        return r

    status = (request.args.get("status") or "All").strip()
    params: Tuple[Any, ...] = tuple()
    sql = """
        SELECT payout_id, trx_id, shop_name, shop_email, amount_bdt,
               destination_type, destination_value, status, requested_at, processed_at, notes
        FROM payout_request
    """
    if status and status.lower() != "all":
        sql += " WHERE status=%s"
        params = (status,)
    sql += " ORDER BY payout_id DESC LIMIT 200"
    rows = db_fetchall(sql, params)
    return jsonify({"payouts": rows})


@app.post("/api/super-admin/payouts/<int:payout_id>/action")
def api_super_admin_payout_action(payout_id: int):
    r = require_role("superadmin")
    if r:
        return r

    data = request.get_json(silent=True) or {}
    action = (data.get("action") or "").strip()
    notes = (data.get("notes") or "").strip()

    if action not in ("Approved", "Rejected"):
        return jsonify({"ok": False, "error": "Invalid action"}), 400

    db_execute(
        """
        UPDATE payout_request
        SET status=%s, notes=%s, processed_at=NOW(), processed_by=%s
        WHERE payout_id=%s
        """,
        (action, notes, current_user_id(), payout_id),
    )
    audit_log("payout_" + action.lower(), metadata={"payout_id": payout_id})
    return jsonify({"ok": True})


@app.get("/api/super-admin/system/config")
def api_super_admin_get_config():
    r = require_role("superadmin")
    if r:
        return r

    def _b(key: str, default: str = "0") -> str:
        return "1" if get_setting(key, default) == "1" else "0"

    # NOTE: Some secrets may be returned because UI requests them (e.g., smtp_pass). Consider masking in production.
    return jsonify(
        {
            "maintenance_mode": _b("maintenance_mode", "0"),
            "debug_mode": _b("debug_mode", "0"),
            "autoscaling_enabled": _b("autoscaling_enabled", "0"),
            "ai_provider": get_setting("ai_provider", "openai"),
            "spam_filter_enabled": _b("spam_filter_enabled", "1"),
            "ai_api_key_set": "1" if get_setting("ai_api_key", "") else "0",
            "db_capacity_mb": get_setting("db_capacity_mb", "1024"),
            # SMTP (no password)
            "smtp_host": get_setting("smtp_host", app.config.get("SMTP_HOST") or ""),
            "smtp_port": get_setting("smtp_port", str(app.config.get("SMTP_PORT") or 587)),
            "smtp_user": get_setting("smtp_user", app.config.get("SMTP_USER") or ""),
            "smtp_from": get_setting("smtp_from", app.config.get("SMTP_FROM") or ""),
            "smtp_pass": get_setting("smtp_pass", app.config.get("SMTP_PASS") or ""),
            # Payment (no secret)
            "payment_provider": get_setting("payment_provider", "none"),
            "payment_enabled": _b("payment_enabled", "0"),
            "payment_sandbox": _b("payment_sandbox", "1"),
            # Logistics (no secret)
            "logistics_provider": get_setting("logistics_provider", "none"),
            "logistics_enabled": _b("logistics_enabled", "0"),
        }
    )


@app.post("/api/super-admin/system/config")
def api_super_admin_set_config():
    r = require_role("superadmin")
    if r:
        return r

    data = request.get_json(silent=True) or {}

    def as_bool(v: Any) -> str:
        return "1" if str(v).lower() in ("1", "true", "yes", "on") else "0"

    maintenance = as_bool(data.get("maintenance_mode", "0"))
    debug = as_bool(data.get("debug_mode", "0"))
    autoscaling = as_bool(data.get("autoscaling_enabled", "0"))

    ai_provider = (data.get("ai_provider") or "openai").strip().lower()
    if ai_provider not in ("openai", "gemini"):
        ai_provider = "openai"

    spam_filter = as_bool(data.get("spam_filter_enabled", "1"))

    db_capacity_mb = str(data.get("db_capacity_mb") or "1024").strip()
    if not db_capacity_mb.isdigit():
        db_capacity_mb = "1024"

    # non-secret saves
    set_setting("maintenance_mode", maintenance)
    set_setting("debug_mode", debug)
    set_setting("autoscaling_enabled", autoscaling)
    set_setting("ai_provider", ai_provider)
    set_setting("spam_filter_enabled", spam_filter)
    set_setting("db_capacity_mb", db_capacity_mb)

    # SMTP (non-secret)
    if "smtp_host" in data:
        set_setting("smtp_host", str(data.get("smtp_host") or "").strip())
    if "smtp_port" in data:
        set_setting("smtp_port", str(data.get("smtp_port") or "587").strip())
    if "smtp_user" in data:
        set_setting("smtp_user", str(data.get("smtp_user") or "").strip())
    if "smtp_from" in data:
        set_setting("smtp_from", str(data.get("smtp_from") or "").strip())

    # Payment (non-secret)
    if "payment_provider" in data:
        set_setting("payment_provider", str(data.get("payment_provider") or "none").strip().lower())
    if "payment_enabled" in data:
        set_setting("payment_enabled", as_bool(data.get("payment_enabled")))
    if "payment_sandbox" in data:
        set_setting("payment_sandbox", as_bool(data.get("payment_sandbox")))

    # Logistics (non-secret)
    if "logistics_provider" in data:
        set_setting("logistics_provider", str(data.get("logistics_provider") or "none").strip().lower())
    if "logistics_enabled" in data:
        set_setting("logistics_enabled", as_bool(data.get("logistics_enabled")))

    audit_log(
        "system_config_saved",
        metadata={
            "maintenance": maintenance,
            "debug": debug,
            "autoscaling": autoscaling,
            "ai_provider": ai_provider,
            "spam_filter": spam_filter,
            "payment_provider": get_setting("payment_provider", "none"),
            "logistics_provider": get_setting("logistics_provider", "none"),
        },
    )
    return jsonify({"ok": True})


@app.get("/api/super-admin/email/branding")
def api_super_admin_get_email_branding():
    r = require_role("superadmin")
    if r:
        return r
    return jsonify(
        {
            "ok": True,
            "email_footer_note": get_setting("email_footer_note", ""),
            "email_signature_name": get_setting("email_signature_name", ""),
            "email_signature_title": get_setting("email_signature_title", ""),
        }
    )


@app.post("/api/super-admin/email/branding")
def api_super_admin_set_email_branding():
    r = require_role("superadmin")
    if r:
        return r
    data = request.get_json(silent=True) or {}
    set_setting("email_footer_note", str(data.get("email_footer_note") or "").strip())
    set_setting("email_signature_name", str(data.get("email_signature_name") or "").strip())
    set_setting("email_signature_title", str(data.get("email_signature_title") or "").strip())
    audit_log("email_branding_saved")
    return jsonify({"ok": True})


# -----------------------
# Email Template Overrides (Super Admin)
# -----------------------
EMAIL_TEMPLATE_REGISTRY = {
    # key: fallback file
    'admin_status_change': 'admin_status_change.html',
    'admin_welcome': 'admin_welcome.html',
    'auth_code': 'auth_code.html',
    'security_alert': 'security_alert.html',
    'payout_spike_alert': 'payout_spike_alert.html',
    'buyer_welcome': 'buyer_welcome.html',
    'seller_onboarding': 'seller_onboarding.html',
    'otp_verification': 'otp_verification.html',
    'new_signin': 'new_signin.html',
}


def _read_email_template_source(fname: str) -> str:
    try:
        p = os.path.join(app.root_path, 'templates', 'emails', fname)
        with open(p, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception:
        return ''


@app.get('/api/super-admin/email-templates')
def api_super_admin_list_email_templates():
    r = require_role('superadmin')
    if r:
        return r

    rows = db_fetchall('SELECT template_key, subject_override, updated_at FROM email_template ORDER BY updated_at DESC')
    by_key = {str(r0['template_key']): r0 for r0 in rows}

    items = []
    for key, fallback in EMAIL_TEMPLATE_REGISTRY.items():
        ov = by_key.get(key)
        items.append({
            'template_key': key,
            'fallback_template': fallback,
            'has_override': bool(ov),
            'subject_override': str((ov or {}).get('subject_override') or ''),
            'updated_at': str((ov or {}).get('updated_at') or ''),
        })

    for key, ov in by_key.items():
        if key not in EMAIL_TEMPLATE_REGISTRY:
            items.append({
                'template_key': key,
                'fallback_template': '',
                'has_override': True,
                'subject_override': str((ov or {}).get('subject_override') or ''),
                'updated_at': str((ov or {}).get('updated_at') or ''),
            })

    return jsonify({'ok': True, 'items': items})


@app.get('/api/super-admin/email-templates/<template_key>')
def api_super_admin_get_email_template(template_key: str):
    r = require_role('superadmin')
    if r:
        return r

    key = (template_key or '').strip()
    row = db_fetchone('SELECT template_key, subject_override, html_override, text_override, updated_at FROM email_template WHERE template_key=%s', (key,))

    fallback = EMAIL_TEMPLATE_REGISTRY.get(key, '')
    return jsonify({
        'ok': True,
        'template_key': key,
        'fallback_template': fallback,
        'override': {
            'subject_override': str((row or {}).get('subject_override') or ''),
            'html_override': str((row or {}).get('html_override') or ''),
            'text_override': str((row or {}).get('text_override') or ''),
            'updated_at': str((row or {}).get('updated_at') or ''),
        },
        'fallback_source': _read_email_template_source(fallback) if fallback else '',
    })


@app.post('/api/super-admin/email-templates/<template_key>')
def api_super_admin_save_email_template(template_key: str):
    r = require_role('superadmin')
    if r:
        return r

    key = (template_key or '').strip()
    data = request.get_json(silent=True) or {}
    subj = str(data.get('subject_override') or '').strip()
    html = str(data.get('html_override') or '').strip()
    txt = str(data.get('text_override') or '').strip()

    if not key:
        return jsonify({'ok': False, 'error': 'template_key_required'}), 400

    if not any([subj, html, txt]):
        db_execute('DELETE FROM email_template WHERE template_key=%s', (key,))
        audit_log('email_template_cleared', metadata={'template_key': key})
        return jsonify({'ok': True, 'cleared': True})

    db_execute(
        'INSERT INTO email_template(template_key, subject_override, html_override, text_override) VALUES (%s,%s,%s,%s) '
        'ON DUPLICATE KEY UPDATE subject_override=VALUES(subject_override), html_override=VALUES(html_override), text_override=VALUES(text_override)',
        (key, subj or None, html or None, txt or None),
    )
    audit_log('email_template_saved', metadata={'template_key': key})
    return jsonify({'ok': True})


@app.post('/api/super-admin/email-templates/<template_key>/reset')
def api_super_admin_reset_email_template(template_key: str):
    r = require_role('superadmin')
    if r:
        return r

    key = (template_key or '').strip()
    db_execute('DELETE FROM email_template WHERE template_key=%s', (key,))
    audit_log('email_template_reset', metadata={'template_key': key})
    return jsonify({'ok': True})


@app.post('/api/super-admin/email-templates/<template_key>/send-test')
def api_super_admin_send_test_email_template(template_key: str):
    r = require_role('superadmin')
    if r:
        return r

    key = (template_key or '').strip()
    fallback = EMAIL_TEMPLATE_REGISTRY.get(key, '')
    if not fallback:
        return jsonify({'ok': False, 'error': 'unknown_template'}), 400

    me = int(current_user_id() or 0)
    row = db_fetchone('SELECT email, name FROM user_account WHERE user_id=%s', (me,))
    to_email = str((row or {}).get('email') or '')

    data = request.get_json(silent=True) or {}
    if data.get('to_email'):
        to_email = str(data.get('to_email') or '').strip()

    if not to_email:
        return jsonify({'ok': False, 'error': 'no_recipient_email'}), 400

    import datetime as _dt
    ctx = {
        'name': (row or {}).get('name') or 'Admin',
        'email': to_email,
        'action_label': 'Account suspended',
        'when_utc': f"{_dt.datetime.utcnow().isoformat()}Z",
        'reason': 'Test email (template preview)',
        'login_url': _base_url().rstrip('/') + '/admin/login',
        'can_login': False,
        'otp': '123456',
        'expires_minutes': 10,
        'title': 'Test Email',
        'preheader': 'Template preview',
        'seller_id': 1,
        'trx_id': 'TEST-TRX',
        'amount': '5000',
        'avg': '1200',
        'threshold': '3600',
        'count': 7,
        'window_minutes': 15,
    }

    default_subject = f"Test email: {key}"
    default_text = f"This is a test email for template: {key}"
    subject, text_body, html = render_email_bundle(
        key,
        fallback_template=fallback,
        default_subject=default_subject,
        default_text=default_text,
        **ctx,
    )

    send_email(to_email, subject, text=text_body, html=html)
    audit_log('email_template_test_sent', metadata={'template_key': key, 'to': to_email})
    return jsonify({'ok': True})


# -----------------------
# Security Event Viewer (Super Admin)
# -----------------------
@app.get('/api/super-admin/security/events')
def api_super_admin_list_security_events():
    r = require_role('superadmin')
    if r:
        return r

    limit = int(request.args.get('limit', '50') or 50)
    limit = max(1, min(200, limit))
    offset = int(request.args.get('offset', '0') or 0)
    offset = max(0, offset)

    event_type = (request.args.get('event_type') or '').strip()
    severity = (request.args.get('severity') or '').strip()
    q = (request.args.get('q') or '').strip()

    where = []
    params = []
    if event_type:
        where.append('event_type=%s')
        params.append(event_type)
    if severity:
        where.append('severity=%s')
        params.append(severity)
    if q:
        where.append('(actor_email LIKE %s OR ip LIKE %s OR message LIKE %s)')
        like = f"%{q}%"
        params.extend([like, like, like])

    where_sql = (' WHERE ' + ' AND '.join(where)) if where else ''

    total_row = db_fetchone('SELECT COUNT(*) AS c FROM security_event' + where_sql, tuple(params))
    total = int((total_row or {}).get('c') or 0)

    rows = db_fetchall(
        'SELECT event_id, event_type, severity, actor_email, ip, user_agent, message, meta_json, created_at '
        'FROM security_event' + where_sql + ' ORDER BY created_at DESC LIMIT %s OFFSET %s',
        tuple(params + [limit, offset]),
    )

    import json as _json
    items = []
    for r0 in rows:
        meta = {}
        try:
            meta = _json.loads(r0.get('meta_json') or '{}')
        except Exception:
            meta = {}
        items.append({
            'event_id': int(r0.get('event_id') or 0),
            'event_type': r0.get('event_type') or '',
            'severity': r0.get('severity') or '',
            'actor_email': r0.get('actor_email') or '',
            'ip': r0.get('ip') or '',
            'user_agent': r0.get('user_agent') or '',
            'message': r0.get('message') or '',
            'meta': meta,
            'created_at': str(r0.get('created_at') or ''),
        })

    return jsonify({'ok': True, 'total': total, 'items': items})



@app.get("/api/super-admin/branding")
def api_super_admin_get_branding():
    r = require_role("superadmin")
    if r:
        return r
    return jsonify(
        {
            "ok": True,
            "brand_org_name": get_setting("brand_org_name", "Origins Bangladesh"),
            "brand_watermark_text": get_setting("brand_watermark_text", "CONFIDENTIAL"),
            "brand_signature_name": get_setting("brand_signature_name", "Authorized Signatory"),
            "brand_signature_title": get_setting("brand_signature_title", "Super Admin Office"),
            "brand_logo_path": get_setting("brand_logo_path", "static/assets/img/brand_logo.png"),
        }
    )


@app.post("/api/super-admin/branding")
def api_super_admin_set_branding():
    r = require_role("superadmin")
    if r:
        return r
    data = request.get_json(silent=True) or {}
    set_setting("brand_org_name", str(data.get("brand_org_name") or "Origins Bangladesh").strip())
    set_setting("brand_watermark_text", str(data.get("brand_watermark_text") or "CONFIDENTIAL").strip())
    set_setting("brand_signature_name", str(data.get("brand_signature_name") or "Authorized Signatory").strip())
    set_setting("brand_signature_title", str(data.get("brand_signature_title") or "Super Admin Office").strip())
    audit_log("branding_saved")
    return jsonify({"ok": True})


@app.post("/api/super-admin/branding/logo")
def api_super_admin_upload_logo():
    r = require_role("superadmin")
    if r:
        return r
    if "logo" not in request.files:
        return jsonify({"ok": False, "error": "logo file required"}), 400
    f = request.files["logo"]
    if not f or not f.filename:
        return jsonify({"ok": False, "error": "invalid file"}), 400
    filename = secure_filename(f.filename)
    ext = os.path.splitext(filename)[1].lower()
    if ext not in (".png", ".jpg", ".jpeg"):
        return jsonify({"ok": False, "error": "only png/jpg supported"}), 400
    os.makedirs(os.path.join(app.root_path, "static", "assets", "img"), exist_ok=True)
    out_rel = "static/assets/img/brand_logo.png"
    out_abs = os.path.join(app.root_path, out_rel)
    f.save(out_abs)
    set_setting("brand_logo_path", out_rel)
    audit_log("branding_logo_uploaded")
    return jsonify({"ok": True, "brand_logo_path": out_rel})


@app.get("/api/super-admin/approvals/settings")
def api_super_admin_get_approval_settings():
    r = require_role("superadmin")
    if r:
        return r
    return jsonify(
        {
            "ok": True,
            "approval_required_permanent_delete": get_setting("approval_required_permanent_delete", "1"),
            "approval_code_ttl_minutes": get_setting("approval_code_ttl_minutes", "10"),
        }
    )


@app.post("/api/super-admin/approvals/settings")
def api_super_admin_set_approval_settings():
    r = require_role("superadmin")
    if r:
        return r
    data = request.get_json(silent=True) or {}
    req = "1" if str(data.get("approval_required_permanent_delete", "1")).lower() in ("1", "true", "yes", "on") else "0"
    ttl = str(data.get("approval_code_ttl_minutes", "10")).strip()
    if not ttl.isdigit():
        ttl = "10"
    ttl_i = max(2, min(60, int(ttl)))
    set_setting("approval_required_permanent_delete", req)
    set_setting("approval_code_ttl_minutes", str(ttl_i))
    audit_log("approval_settings_saved", metadata={"required": req, "ttl": ttl_i})
    return jsonify({"ok": True})


@app.get("/api/super-admin/alerts/settings")
def api_super_admin_get_alert_settings():
    r = require_role("superadmin")
    if r:
        return r
    return jsonify(
        {
            "ok": True,
            "alerts_enabled": get_setting("alerts_enabled", "1"),
            "alert_recipient_email": get_setting("alert_recipient_email", ""),
            "alert_failed_login_threshold": get_setting("alert_failed_login_threshold", "5"),
            "alert_failed_login_window_minutes": get_setting("alert_failed_login_window_minutes", "15"),
            "alert_payout_spike_multiplier": get_setting("alert_payout_spike_multiplier", "3"),
            "alert_payout_spike_min_bdt": get_setting("alert_payout_spike_min_bdt", "5000"),
        }
    )


@app.post("/api/super-admin/alerts/settings")
def api_super_admin_set_alert_settings():
    r = require_role("superadmin")
    if r:
        return r
    data = request.get_json(silent=True) or {}
    enabled = "1" if str(data.get("alerts_enabled", "1")).lower() in ("1", "true", "yes", "on") else "0"
    set_setting("alerts_enabled", enabled)
    if "alert_recipient_email" in data:
        set_setting("alert_recipient_email", str(data.get("alert_recipient_email") or "").strip().lower())
    for k in ("alert_failed_login_threshold", "alert_failed_login_window_minutes"):
        if k in data:
            v = str(data.get(k) or "").strip()
            if v.isdigit():
                set_setting(k, v)
    for k in ("alert_payout_spike_multiplier", "alert_payout_spike_min_bdt"):
        if k in data:
            set_setting(k, str(data.get(k) or "").strip())
    audit_log("alert_settings_saved")
    return jsonify({"ok": True})



@app.post("/api/super-admin/secrets/ai-key")
def api_super_admin_set_ai_key():
    r = require_role("superadmin")
    if r:
        return r
    data = request.get_json(silent=True) or {}
    key = (data.get("ai_api_key") or "").strip()
    if not key:
        return jsonify({"ok": False, "error": "ai_api_key required"}), 400
    # NOTE: For premium hardening, encrypt this value before storing.
    set_setting("ai_api_key", key)
    audit_log("ai_api_key_saved")
    return jsonify({"ok": True})


@app.post("/api/super-admin/secrets/smtp-pass")
def api_super_admin_set_smtp_pass():
    r = require_role("superadmin")
    if r:
        return r
    data = request.get_json(silent=True) or {}
    pwd = (data.get("smtp_pass") or "").strip()
    if not pwd:
        return jsonify({"ok": False, "error": "smtp_pass required"}), 400
    set_setting("smtp_pass", pwd)
    audit_log("smtp_password_saved")
    return jsonify({"ok": True})


@app.post("/api/super-admin/secrets/payment")
def api_super_admin_set_payment_secrets():
    r = require_role("superadmin")
    if r:
        return r
    data = request.get_json(silent=True) or {}
    provider = (data.get("provider") or get_setting("payment_provider", "none")).strip().lower()

    if provider == "sslcommerz":
        store_id = (data.get("sslcommerz_store_id") or "").strip()
        store_pass = (data.get("sslcommerz_store_pass") or "").strip()
        if not store_id or not store_pass:
            return jsonify({"ok": False, "error": "sslcommerz_store_id and sslcommerz_store_pass required"}), 400
        set_setting("sslcommerz_store_id", store_id)
        set_setting("sslcommerz_store_pass", store_pass)
        audit_log("payment_secrets_saved", metadata={"provider": "sslcommerz"})
        return jsonify({"ok": True})

    if provider == "stripe":
        secret = (data.get("stripe_secret_key") or "").strip()
        publishable = (data.get("stripe_publishable_key") or "").strip()
        if not secret or not publishable:
            return jsonify({"ok": False, "error": "stripe_secret_key and stripe_publishable_key required"}), 400
        set_setting("stripe_secret_key", secret)
        set_setting("stripe_publishable_key", publishable)
        audit_log("payment_secrets_saved", metadata={"provider": "stripe"})
        return jsonify({"ok": True})

    return jsonify({"ok": False, "error": "Unknown provider"}), 400


@app.post("/api/super-admin/secrets/logistics")
def api_super_admin_set_logistics_secrets():
    r = require_role("superadmin")
    if r:
        return r
    data = request.get_json(silent=True) or {}
    api_key = (data.get("api_key") or "").strip()
    if not api_key:
        return jsonify({"ok": False, "error": "api_key required"}), 400
    set_setting("logistics_api_key", api_key)
    audit_log("logistics_secret_saved")
    return jsonify({"ok": True})


@app.post("/api/super-admin/email/test")
def api_super_admin_email_test():
    r = require_role("superadmin")
    if r:
        return r
    data = request.get_json(silent=True) or {}
    to_email = (data.get("to_email") or "").strip().lower()
    if not to_email:
        return jsonify({"ok": False, "error": "to_email required"}), 400
    try:
        send_email(
            to_email,
            "SMTP Test — Origins Bangladesh",
            text="If you received this, SMTP is working.",
            html="<p>If you received this, <b>SMTP is working</b>.</p>",
        )
        audit_log("smtp_test_sent", metadata={"to": to_email})
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.post("/api/super-admin/payment/test")
def api_super_admin_payment_test():
    r = require_role("superadmin")
    if r:
        return r

    provider = get_setting("payment_provider", "none")
    enabled = get_setting("payment_enabled", "0") == "1"
    sandbox = get_setting("payment_sandbox", "1") == "1"

    if not enabled or provider == "none":
        return jsonify({"ok": False, "error": "Payment is disabled or provider not set"}), 400

    if provider == "sslcommerz":
        sid = get_setting("sslcommerz_store_id", "")
        sp = get_setting("sslcommerz_store_pass", "")
        if not sid or not sp:
            return jsonify({"ok": False, "error": "SSLCommerz secrets missing"}), 400

    if provider == "stripe":
        sk = get_setting("stripe_secret_key", "")
        pk = get_setting("stripe_publishable_key", "")
        if not sk or not pk:
            return jsonify({"ok": False, "error": "Stripe keys missing"}), 400
        # Light validation (no network calls)
        if sandbox and not sk.startswith("sk_test"):
            return jsonify({"ok": False, "error": "Stripe secret key should be sk_test... for sandbox"}), 400
        if (not sandbox) and not sk.startswith("sk_live"):
            return jsonify({"ok": False, "error": "Stripe secret key should be sk_live... for live"}), 400

    audit_log("payment_gateway_tested", metadata={"provider": provider, "sandbox": sandbox})
    return jsonify({"ok": True, "provider": provider, "sandbox": sandbox})


@app.post("/api/super-admin/logistics/test")
def api_super_admin_logistics_test():
    r = require_role("superadmin")
    if r:
        return r

    provider = get_setting("logistics_provider", "none")
    enabled = get_setting("logistics_enabled", "0") == "1"
    api_key = get_setting("logistics_api_key", "")

    if not enabled or provider == "none":
        return jsonify({"ok": False, "error": "Logistics disabled or provider not set"}), 400
    if not api_key:
        return jsonify({"ok": False, "error": "Logistics API key missing"}), 400

    audit_log("logistics_api_tested", metadata={"provider": provider})
    return jsonify({"ok": True, "provider": provider})


@app.get("/api/super-admin/ai/insights")
def api_super_admin_ai_insights():
    r = require_role("superadmin")
    if r:
        return r

    rev = db_fetchone(
        """
        SELECT COALESCE(SUM(CASE WHEN status IN ('paid','shipped','delivered') THEN total_bdt ELSE 0 END),0) AS total
        FROM `order`
        WHERE created_at >= DATE_SUB(UTC_TIMESTAMP(), INTERVAL 30 DAY)
        """
    )["total"]

    pending = db_fetchone("SELECT COUNT(*) AS c FROM payout_request WHERE status='Pending'")["c"]

    peak = None
    try:
        peak = db_fetchone(
            """
            SELECT HOUR(created_at) AS hh, COUNT(*) AS c
            FROM `order`
            WHERE created_at >= DATE_SUB(UTC_TIMESTAMP(), INTERVAL 7 DAY)
            GROUP BY hh
            ORDER BY c DESC
            LIMIT 1
            """
        )
    except Exception:
        peak = None

    insight_1 = f"Last 30 days revenue: ৳{float(rev or 0):,.0f}."
    insight_2 = f"Pending payout requests: {int(pending or 0)}."
    insight_3 = (
        f"Peak order hour (last 7d): {peak['hh']}:00 (~{peak['c']} orders)."
        if peak
        else "Peak order hour: not enough data."
    )

    return jsonify({"ok": True, "insights": [insight_1, insight_2, insight_3]})

def _db_size_mb() -> float:
    try:
        row = db_fetchone(
            """
            SELECT ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS size_mb
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
            """
        )
        return float(row["size_mb"] or 0.0)
    except Exception:
        return 0.0


def _slow_query_metrics() -> Dict[str, Any]:
    # Best effort. Works only if performance_schema enabled.
    try:
        exists = db_fetchone(
            "SELECT COUNT(*) AS c FROM information_schema.schemata WHERE schema_name='performance_schema'"
        )["c"]
        if int(exists) == 0:
            return {"enabled": False}

        rows = db_fetchall(
            """
            SELECT COUNT(*) AS slow_digests
            FROM performance_schema.events_statements_summary_by_digest
            WHERE (AVG_TIMER_WAIT/1000000000000) > 0.5
            """
        )
        slow_digests = int(rows[0]["slow_digests"]) if rows else 0
        return {"enabled": True, "slow_digests": slow_digests}
    except Exception:
        return {"enabled": False}


@app.get("/api/super-admin/db/health")
def api_super_admin_db_health():
    r = require_role("superadmin")
    if r:
        return r

    db_ok = True
    try:
        db_fetchone("SELECT 1 AS ok")
    except Exception:
        db_ok = False

    size_mb = _db_size_mb()
    cap_mb = float(get_setting("db_capacity_mb", "1024") or "1024")
    percent = 0.0
    try:
        percent = 0.0 if cap_mb <= 0 else min(100.0, round((size_mb / cap_mb) * 100.0, 2))
    except Exception:
        percent = 0.0

    version = None
    now = None
    try:
        version = db_fetchone("SELECT VERSION() AS v")["v"]
        now = db_fetchone("SELECT NOW() AS t")["t"]
    except Exception:
        pass

    slow = _slow_query_metrics()

    last_backup = db_fetchone(
        "SELECT backup_id, started_at, finished_at, status, file_path FROM backup_log ORDER BY backup_id DESC LIMIT 1"
    )

    return jsonify(
        {
            "db_ok": db_ok,
            "db_version": version,
            "db_time": str(now) if now else None,
            "size_mb": size_mb,
            "capacity_mb": cap_mb,
            "percent_used": percent,
            "slow_query": slow,
            "last_backup": last_backup,
        }
    )


@app.post("/api/super-admin/db/backup/start")
def api_super_admin_backup_start():
    r = require_role("superadmin")
    if r:
        return r

    os.makedirs(os.path.join(app.root_path, "exports"), exist_ok=True)

    db_execute(
        "INSERT INTO backup_log (status, created_by) VALUES ('RUNNING', %s)",
        (current_user_id(),),
    )
    backup_id = db_fetchone("SELECT LAST_INSERT_ID() AS id")["id"]

    ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    # Real DB backup: generate a SQL dump (schema + data) and ZIP it for safe download.
    sql_rel = f"exports/backup_{backup_id}_{ts}.sql"
    zip_rel = f"exports/backup_{backup_id}_{ts}.zip"
    sql_abs = os.path.join(app.root_path, sql_rel)
    zip_abs = os.path.join(app.root_path, zip_rel)

    details: Dict[str, Any] = {"backup_id": int(backup_id), "generated_utc": ts}

    try:
        # Dump schema + data.
        conn = get_db()
        cur = conn.cursor()
        db_name = (app.config.get("DB_NAME") or os.getenv("DB_NAME") or os.getenv("MYSQL_DATABASE") or "").strip()
        if not db_name:
            # Fallback: current database
            cur.execute("SELECT DATABASE()")
            db_name = (cur.fetchone() or [""])[0] or ""

        cur.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema=%s AND table_type='BASE TABLE'
            ORDER BY table_name
            """,
            (db_name,),
        )
        tables = [r0[0] for r0 in (cur.fetchall() or [])]

        with open(sql_abs, "w", encoding="utf-8") as f:
            f.write("-- Origins Bangladesh SQL Backup\n")
            f.write(f"-- Generated (UTC): {ts}\n")
            f.write(f"-- Database: {db_name}\n\n")
            f.write("SET NAMES utf8mb4;\n")
            f.write("SET FOREIGN_KEY_CHECKS=0;\n\n")

            for t in tables:
                # Schema
                cur.execute(f"SHOW CREATE TABLE `{t}`")
                row = cur.fetchone()
                create_sql = row[1] if row and len(row) > 1 else ""
                f.write(f"-- ----------------------------\n-- Table structure for `{t}`\n-- ----------------------------\n")
                f.write(f"DROP TABLE IF EXISTS `{t}`;\n")
                f.write(create_sql + ";\n\n")

                # Data
                cur.execute(f"SELECT * FROM `{t}`")
                cols = [d[0] for d in (cur.description or [])]
                rows_written = 0
                f.write(f"-- ----------------------------\n-- Data for `{t}`\n-- ----------------------------\n")
                while True:
                    batch = cur.fetchmany(500)
                    if not batch:
                        break
                    for r0 in batch:
                        values = []
                        for v in r0:
                            if v is None:
                                values.append("NULL")
                            elif isinstance(v, (int, float, Decimal)):
                                values.append(str(v))
                            elif isinstance(v, (datetime.datetime, datetime.date)):
                                values.append("'" + str(v).replace("'", "''") + "'")
                            else:
                                s = str(v)
                                s = s.replace("\\", "\\\\").replace("'", "''")
                                values.append("'" + s + "'")
                        f.write(
                            "INSERT INTO `{}` ({}) VALUES ({});\n".format(
                                t,
                                ",".join([f"`{c}`" for c in cols]),
                                ",".join(values),
                            )
                        )
                        rows_written += 1
                    f.write("\n")
                details.setdefault("counts", {})[t] = rows_written
                f.write("\n")

            f.write("SET FOREIGN_KEY_CHECKS=1;\n")

        # Compress
        try:
            import zipfile

            with zipfile.ZipFile(zip_abs, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                zf.write(sql_abs, arcname=os.path.basename(sql_abs))
            details["zipped"] = True
        except Exception as e_zip:
            # If zip fails, fall back to raw SQL download.
            details["zipped"] = False
            details["zip_error"] = str(e_zip)
            zip_rel = sql_rel

        db_execute(
            "UPDATE backup_log SET finished_at=NOW(), status='SUCCESS', file_path=%s, details_json=%s WHERE backup_id=%s",
            (zip_rel, json.dumps(details, ensure_ascii=False), backup_id),
        )
        audit_log("db_backup_initiated", metadata={"backup_id": int(backup_id)})

        notify_current_superadmin(
            type="db_backup",
            title="Backup ready",
            body=f"Backup #{int(backup_id)} generated successfully",
            link=f"/api/super-admin/db/backup/{int(backup_id)}/download",
            severity="success",
            meta={"backup_id": int(backup_id)},
        )

        return jsonify(
            {
                "ok": True,
                "backup_id": int(backup_id),
                "file_path": zip_rel,
                "download_url": f"/api/super-admin/db/backup/{int(backup_id)}/download",
            }
        )
    except Exception as e:
        db_execute(
            "UPDATE backup_log SET finished_at=NOW(), status='FAILED', details_json=%s WHERE backup_id=%s",
            (json.dumps({"error": str(e)}), backup_id),
        )
        notify_current_superadmin(type="db_backup", title="Backup failed", body=str(e)[:200], link="#tab-security", severity="error", meta={"backup_id": int(backup_id)})
        return jsonify({"ok": False, "error": "Backup export failed"}), 500


@app.get("/api/super-admin/db/backup/<int:backup_id>/download")
def api_super_admin_backup_download(backup_id: int):
    r = require_role("superadmin")
    if r:
        return r
    row = db_fetchone(
        "SELECT backup_id, file_path, status FROM backup_log WHERE backup_id=%s LIMIT 1",
        (backup_id,),
    )
    if not row or not row.get("file_path") or row.get("status") != "SUCCESS":
        return jsonify({"ok": False, "error": "Backup not available"}), 404
    rel = str(row["file_path"])
    # Only allow downloads from exports/
    if not rel.startswith("exports/"):
        return jsonify({"ok": False, "error": "Invalid path"}), 400
    abs_path = os.path.join(app.root_path, rel)
    if not os.path.exists(abs_path):
        return jsonify({"ok": False, "error": "File missing"}), 404
    return send_file(abs_path, as_attachment=True, download_name=os.path.basename(abs_path))


@app.get("/api/super-admin/security/blocks")
def api_super_admin_list_blocks():
    r = require_role("superadmin")
    if r:
        return r
    rows = db_fetchall(
        "SELECT block_id, block_type, block_value, reason, is_active, created_at FROM access_block ORDER BY block_id DESC LIMIT 200"
    )
    return jsonify({"blocks": rows})


@app.post("/api/super-admin/security/blocks")
def api_super_admin_create_block():
    r = require_role("superadmin")
    if r:
        return r
    data = request.get_json(silent=True) or {}
    value = (data.get("value") or "").strip()
    reason = (data.get("reason") or "").strip()[:255]

    if not value:
        return jsonify({"ok": False, "error": "Empty value"}), 400

    block_type = "ip"
    if value.isdigit():
        block_type = "user"

    db_execute(
        "INSERT INTO access_block (block_type, block_value, reason, is_active, created_by) VALUES (%s,%s,%s,1,%s)",
        (block_type, value, reason, current_user_id()),
    )
    audit_log("access_block_created", metadata={"block_type": block_type, "value": value})
    return jsonify({"ok": True})


@app.post("/api/super-admin/security/blocks/<int:block_id>/disable")
def api_super_admin_disable_block(block_id: int):
    r = require_role("superadmin")
    if r:
        return r
    db_execute("UPDATE access_block SET is_active=0 WHERE block_id=%s", (block_id,))
    audit_log("access_block_disabled", metadata={"block_id": block_id})
    return jsonify({"ok": True})


@app.get("/api/super-admin/security/scan")
def api_super_admin_security_scan():
    r = require_role("superadmin")
    if r:
        return r

    pending_payouts = db_fetchone("SELECT COUNT(*) AS c FROM payout_request WHERE status='Pending'")["c"]
    inactive_admins = db_fetchone("SELECT COUNT(*) AS c FROM user_account WHERE role='admin' AND is_active=0")["c"]
    size_mb = _db_size_mb()
    cap_mb = float(get_setting("db_capacity_mb", "1024") or "1024")
    pct = 0.0 if cap_mb <= 0 else (size_mb / cap_mb) * 100.0

    settled_bdt = _finance_settled_bdt()

    anomalies = []
    if int(pending_payouts) > 25:
        anomalies.append({"type": "payout_backlog", "message": "High pending payout backlog."})
    if int(inactive_admins) > 0:
        anomalies.append({"type": "inactive_admins", "message": f"{int(inactive_admins)} admin accounts are inactive."})
    if pct >= 90:
        anomalies.append({"type": "db_capacity", "message": "DB usage above 90% of configured capacity."})

    # Hardening checks (real checks; no fake “OK”)
    if (app.config.get("SUPERADMIN_SECRET_CODE") or "").strip() in ("", "1234", "0000", "admin"):
        anomalies.append({"type": "weak_superadmin_code", "message": "SUPERADMIN_SECRET_CODE looks weak or empty."})
    if os.path.exists(os.path.join(app.root_path, "exports")):
        try:
            test_path = os.path.join(app.root_path, "exports", ".write_test")
            with open(test_path, "w", encoding="utf-8") as f:
                f.write("ok")
            os.remove(test_path)
        except Exception:
            anomalies.append({"type": "exports_not_writable", "message": "exports/ directory is not writable by the app."})

    # Email configuration (alerts won't work without SMTP)
    smtp_host = (app.config.get("SMTP_HOST") or os.getenv("SMTP_HOST") or "").strip()
    smtp_user = (app.config.get("SMTP_USER") or os.getenv("SMTP_USER") or "").strip()
    if not smtp_host or not smtp_user:
        anomalies.append({"type": "smtp_not_configured", "message": "SMTP_HOST/SMTP_USER not configured; email alerts may fail."})

    # Very high payout spikes (simple sanity check)
    try:
        max_pending = db_fetchone("SELECT COALESCE(MAX(amount_bdt),0) AS m FROM payout_request WHERE status='Pending'")
        if Decimal(str(max_pending.get("m") or "0")) >= Decimal("50000"):
            anomalies.append({"type": "large_pending_payout", "message": "A very large pending payout request exists."})
    except Exception:
        pass

    audit_log("security_scan_run", metadata={"anomalies": len(anomalies)})

    # Notification + security event
    try:
        if anomalies:
            log_security_event("security_scan_anomalies", severity="warn", actor_email="", message="anomalies_found", meta={"count": len(anomalies), "types": [a.get("type") for a in anomalies]})
            notify_current_superadmin(
                type="security_scan",
                title=f"Security scan found {len(anomalies)} issue(s)",
                body=", ".join([str(a.get("type")) for a in anomalies[:3]])[:200],
                link="#tab-security",
                severity="warn",
            )
        else:
            notify_current_superadmin(type="security_scan", title="Security scan OK", body="No anomalies detected", link="#tab-security", severity="success")
    except Exception:
        pass
    return jsonify(
        {
            "ok": True,
            "pending_payouts": int(pending_payouts),
            "settled_bdt": str(settled_bdt),
            "inactive_admins": int(inactive_admins),
            "db_percent_used": round(pct, 2),
            "anomalies": anomalies,
        }
    )


@app.post("/api/seller/payouts/request")
def api_seller_create_payout_request():
    r = require_role("seller")
    if r:
        return r
    data = request.get_json(silent=True) or {}
    amount = Decimal(str(data.get("amount_bdt") or "0"))
    dest_type = (data.get("destination_type") or "").strip()
    dest_value = (data.get("destination_value") or "").strip()
    shop_name = (data.get("shop_name") or "").strip()
    shop_email = (data.get("shop_email") or "").strip()

    if amount <= 0 or not dest_value:
        return jsonify({"ok": False, "error": "Invalid request"}), 400

    trx_id = next_global_prefixed_id("TRX", "TRX")
    db_execute(
        """
        INSERT INTO payout_request (trx_id, seller_user_id, shop_name, shop_email, amount_bdt, destination_type, destination_value, status)
        VALUES (%s,%s,%s,%s,%s,%s,%s,'Pending')
        """,
        (trx_id, current_user_id(), shop_name, shop_email, str(amount), dest_type, dest_value),
    )

    # Alert (finance anomaly)
    try:
        maybe_send_payout_spike_alert(seller_id=int(current_user_id() or 0), amount_bdt=amount, trx_id=trx_id)
    except Exception:
        pass

    return jsonify({"ok": True, "trx_id": trx_id})


# -----------------------
# Error pages (simple)
# -----------------------
@app.errorhandler(404)
def not_found(e):
    return render_template("pages/error-404.html"), 404


@app.errorhandler(500)
def server_error(e):
    return render_template("pages/error-500.html"), 500




# -----------------------
# Buyer APIs (DB-backed)
# -----------------------

def _require_buyer_api():
    uid = current_user_id()
    if not uid:
        return jsonify({"ok": False, "message": "Not authenticated"}), 401
    if current_role() != "buyer":
        return jsonify({"ok": False, "message": "Forbidden"}), 403
    return None


@app.get("/api/buyer/profile")
def api_buyer_profile_get():
    guard = _require_buyer_api()
    if guard is not None:
        return guard
    buyer_id = current_user_id()

    # user_account basics
    user = db_fetchone(
        "SELECT user_id, name, email, phone, created_at FROM user_account WHERE user_id=%s LIMIT 1",
        (buyer_id,),
    ) or {}

    profile = {}
    try:
        prow = db_fetchone(
            "SELECT address, bio, avatar_url, points, guardian_id FROM buyer_profile WHERE buyer_id=%s LIMIT 1",
            (buyer_id,),
        ) or {}
        profile = {
            "address": prow.get("address") or "",
            "bio": prow.get("bio") or "",
            "avatar_url": prow.get("avatar_url") or "",
            "points": int(prow.get("points") or 0),
            "guardian_id": normalize_guardian_id(prow.get("guardian_id") or "", buyer_id),
        }
    except Exception:
        # Table might not exist yet (migration not run)
        profile = {"address": "", "bio": "", "avatar_url": "", "points": 0}

    user["public_id"] = get_public_user_id(buyer_id, role="buyer")
    return jsonify({"ok": True, "user": user, "profile": profile})


@app.put("/api/buyer/profile")
def api_buyer_profile_put():
    guard = _require_buyer_api()
    if guard is not None:
        return guard
    buyer_id = current_user_id()
    payload = request.get_json(silent=True) or {}

    # user_account fields
    name = payload.get("name")
    email = payload.get("email")
    phone = payload.get("phone")
    email = payload.get("email")

    # buyer_profile fields
    address = payload.get("address")
    bio = payload.get("bio")
    avatar_url = payload.get("avatar_url")

    # Update user_account if requested
    try:
        if name is not None:
            db_execute("UPDATE user_account SET name=%s WHERE user_id=%s", (name, buyer_id))
            session["name"] = name
        if email is not None:
            db_execute("UPDATE user_account SET email=%s WHERE user_id=%s", (email, buyer_id))
        if phone is not None:
            db_execute("UPDATE user_account SET phone=%s WHERE user_id=%s", (phone, buyer_id))
    except Exception as e:
        return jsonify({"ok": False, "message": "Account update failed", "detail": str(e)}), 500

    # Upsert: insert if missing, update provided fields only
    try:
        existing = db_fetchone("SELECT buyer_id FROM buyer_profile WHERE buyer_id=%s LIMIT 1", (buyer_id,))
        if not existing:
            db_execute(
                "INSERT INTO buyer_profile (buyer_id, address, bio, avatar_url) VALUES (%s, %s, %s, %s)",
                (buyer_id, address or "", bio or "", avatar_url or ""),
            )

        if address is not None:
            db_execute("UPDATE buyer_profile SET address=%s WHERE buyer_id=%s", (address, buyer_id))
        if bio is not None:
            db_execute("UPDATE buyer_profile SET bio=%s WHERE buyer_id=%s", (bio, buyer_id))
        if avatar_url is not None:
            db_execute("UPDATE buyer_profile SET avatar_url=%s WHERE buyer_id=%s", (avatar_url, buyer_id))
    except Exception as e:
        return jsonify({"ok": False, "message": "Profile update failed. Did you run the migration SQL?", "detail": str(e)}), 500

    return jsonify({"ok": True})


@app.post("/api/buyer/profile/avatar")
def api_buyer_profile_avatar_upload():
    guard = _require_buyer_api()
    if guard is not None:
        return guard
    buyer_id = current_user_id()

    file = request.files.get("avatar")
    if not file or not file.filename:
        return jsonify({"ok": False, "message": "No file uploaded"}), 400

    filename = secure_filename(file.filename)
    ext = os.path.splitext(filename)[1].lower()
    if ext not in [".png", ".jpg", ".jpeg", ".webp"]:
        return jsonify({"ok": False, "message": "Only PNG/JPG/WEBP allowed"}), 400

    # Save under static so it can be served directly
    rel_dir = f"static/assets/pic/buyers/{buyer_id}"
    abs_dir = os.path.join(app.root_path, rel_dir)
    os.makedirs(abs_dir, exist_ok=True)

    save_name = f"avatar{ext}"
    abs_path = os.path.join(abs_dir, save_name)
    file.save(abs_path)

    avatar_url = f"/{rel_dir}/{save_name}"

    # Keep navbar in sync on next request
    session["avatar_url"] = avatar_url

    # Persist to DB
    try:
        existing = db_fetchone("SELECT buyer_id FROM buyer_profile WHERE buyer_id=%s LIMIT 1", (buyer_id,))
        if not existing:
            db_execute("INSERT INTO buyer_profile (buyer_id, avatar_url) VALUES (%s, %s)", (buyer_id, avatar_url))
        else:
            db_execute("UPDATE buyer_profile SET avatar_url=%s WHERE buyer_id=%s", (avatar_url, buyer_id))
    except Exception as e:
        return jsonify({"ok": False, "message": "Avatar save failed. Did you run the migration SQL?", "detail": str(e)}), 500

    return jsonify({"ok": True, "avatar_url": avatar_url})


@app.get("/api/buyer/collection")
def api_buyer_collection():
    guard = _require_buyer_api()
    if guard is not None:
        return guard
    buyer_id = current_user_id()

    status = (request.args.get("status") or "").strip().lower()
    q = (request.args.get("q") or "").strip()

    where = ["o.buyer_id=%s"]
    params: List[Any] = [buyer_id]

    if status:
        where.append("LOWER(o.status)=%s")
        params.append(status)

    if q:
        where.append("(p.title LIKE %s OR a.name LIKE %s)")
        params.extend([f"%{q}%", f"%{q}%"])

    sql = f"""
        SELECT
            o.order_id,
            o.status,
            o.created_at,
            oi.quantity,
            p.product_id,
            p.title,
            p.price_bdt,
            p.image_path,
            a.artisan_id,
            a.name AS artisan_name
        FROM `order` o
        JOIN order_item oi ON oi.order_id=o.order_id
        JOIN product p ON p.product_id=oi.product_id
        LEFT JOIN artisan_product ap ON ap.product_id=p.product_id
        LEFT JOIN artisan a ON a.artisan_id=ap.artisan_id
        WHERE {' AND '.join(where)}
        ORDER BY o.created_at DESC, oi.order_item_id DESC
        LIMIT 200
    """

    rows = db_fetchall(sql, tuple(params))
    items = []
    for r in rows:
        items.append(
            {
                "order_id": int(r.get("order_id") or 0),
                "status": r.get("status") or "",
                "created_at": (r.get("created_at").strftime("%Y-%m-%d %H:%M:%S") if r.get("created_at") else ""),
                "product_id": int(r.get("product_id") or 0),
                "title": r.get("title") or "",
                "price_bdt": float(Decimal(str(r.get("price_bdt") or 0))),
                "image": r.get("image_path") or "/static/assets/img/placeholder.jpg",
                "quantity": int(r.get("quantity") or 0),
                "artisan_id": int(r.get("artisan_id") or 0) if r.get("artisan_id") else None,
                "artisan_name": r.get("artisan_name") or None,
            }
        )
    return jsonify({"ok": True, "items": items})


@app.get("/api/buyer/chats")
def api_buyer_chats():
    guard = _require_buyer_api()
    if guard is not None:
        return guard
    buyer_id = current_user_id()

    try:
        rows = db_fetchall(
            """
            SELECT
              t.thread_id,
              t.artisan_id,
              a.name AS artisan_name,
              t.last_message_at,
              (
                SELECT cm.body
                FROM chat_message cm
                WHERE cm.thread_id=t.thread_id
                ORDER BY cm.created_at DESC
                LIMIT 1
              ) AS last_message,
              (
                SELECT COUNT(*)
                FROM chat_message cm2
                WHERE cm2.thread_id=t.thread_id AND cm2.is_read=0 AND cm2.sender_role='artisan'
              ) AS unread
            FROM chat_thread t
            LEFT JOIN artisan a ON a.artisan_id=t.artisan_id
            WHERE t.buyer_id=%s
            ORDER BY COALESCE(t.last_message_at, t.created_at) DESC
            LIMIT 50
            """,
            (buyer_id,),
        )
    except Exception as e:
        return jsonify({"ok": False, "message": "Chat is not available yet. Did you run the migration SQL?", "detail": str(e), "chats": []}), 200

    chats = []
    for r in rows:
        chats.append(
            {
                "thread_id": int(r.get("thread_id") or 0),
                "artisan_id": int(r.get("artisan_id") or 0),
                "artisan_name": r.get("artisan_name") or "Artisan",
                "last_message": r.get("last_message") or "",
                "last_message_at": (r.get("last_message_at").strftime("%Y-%m-%d %H:%M:%S") if r.get("last_message_at") else ""),
                "unread": int(r.get("unread") or 0),
            }
        )
    return jsonify({"ok": True, "chats": chats})


@app.post("/api/buyer/chats/start")
def api_buyer_chat_start():
    guard = _require_buyer_api()
    if guard is not None:
        return guard
    buyer_id = current_user_id()
    payload = request.get_json(silent=True) or {}
    artisan_id = int(payload.get("artisan_id") or 0)
    if not artisan_id:
        return jsonify({"ok": False, "message": "artisan_id required"}), 400

    try:
        # Create thread if not exists
        existing = db_fetchone(
            "SELECT thread_id FROM chat_thread WHERE buyer_id=%s AND artisan_id=%s LIMIT 1",
            (buyer_id, artisan_id),
        )
        if existing:
            return jsonify({"ok": True, "thread_id": int(existing.get("thread_id"))})
        thread_id = db_execute(
            "INSERT INTO chat_thread (buyer_id, artisan_id) VALUES (%s, %s)",
            (buyer_id, artisan_id),
            return_lastrowid=True,
        )
        return jsonify({"ok": True, "thread_id": int(thread_id or 0)})
    except Exception as e:
        return jsonify({"ok": False, "message": "Could not start chat. Did you run the migration SQL?", "detail": str(e)}), 500


@app.get("/api/buyer/chats/<int:thread_id>/messages")
def api_buyer_chat_messages(thread_id: int):
    guard = _require_buyer_api()
    if guard is not None:
        return guard
    buyer_id = current_user_id()

    # Verify ownership
    t = db_fetchone("SELECT buyer_id FROM chat_thread WHERE thread_id=%s LIMIT 1", (thread_id,))
    if not t or int(t.get("buyer_id") or 0) != int(buyer_id):
        return jsonify({"ok": False, "message": "Not found"}), 404

    rows = db_fetchall(
        """
        SELECT sender_role, sender_id, body, is_read, created_at
        FROM chat_message
        WHERE thread_id=%s
        ORDER BY created_at ASC
        LIMIT 500
        """,
        (thread_id,),
    )
    messages = []
    for r in rows:
        created = r.get("created_at")
        messages.append(
            {
                "sender_role": r.get("sender_role"),
                "sender_id": int(r.get("sender_id") or 0),
                "body": r.get("body") or "",
                "is_read": bool(r.get("is_read")),
                "time": (created.strftime("%I:%M %p").lstrip("0") if created else ""),
            }
        )

    # Mark artisan messages as read
    try:
        db_execute(
            "UPDATE chat_message SET is_read=1 WHERE thread_id=%s AND sender_role='artisan' AND is_read=0",
            (thread_id,),
        )
    except Exception:
        pass

    return jsonify({"ok": True, "messages": messages})


@app.post("/api/buyer/chats/<int:thread_id>/messages")
def api_buyer_chat_send(thread_id: int):
    guard = _require_buyer_api()
    if guard is not None:
        return guard
    buyer_id = current_user_id()
    payload = request.get_json(silent=True) or {}
    body = (payload.get("body") or "").strip()
    if not body:
        return jsonify({"ok": False, "message": "Message body required"}), 400

    # Verify ownership
    t = db_fetchone("SELECT buyer_id FROM chat_thread WHERE thread_id=%s LIMIT 1", (thread_id,))
    if not t or int(t.get("buyer_id") or 0) != int(buyer_id):
        return jsonify({"ok": False, "message": "Not found"}), 404

    try:
        db_execute(
            "INSERT INTO chat_message (thread_id, sender_role, sender_id, body, is_read) VALUES (%s, 'buyer', %s, %s, 0)",
            (thread_id, buyer_id, body),
        )
        db_execute("UPDATE chat_thread SET last_message_at=NOW() WHERE thread_id=%s", (thread_id,))
    except Exception as e:
        return jsonify({"ok": False, "message": "Could not send message. Did you run the migration SQL?", "detail": str(e)}), 500

    return jsonify({"ok": True})


@app.get("/api/buyer/orders/<int:order_id>")
def api_buyer_order_detail(order_id: int):
    guard = _require_buyer_api()
    if guard is not None:
        return guard
    buyer_id = current_user_id()
    order = db_fetchone(
        """
        SELECT order_id, status, subtotal_bdt, shipping_bdt, discount_bdt, total_bdt,
               payment_status, payment_method, shipping_name, shipping_phone, shipping_email,
               shipping_address_line, shipping_apartment, shipping_country, shipping_city, postal_code,
               invoice_no, created_at, delivered_at
        FROM `order`
        WHERE order_id=%s AND buyer_id=%s
        LIMIT 1
        """,
        (order_id, buyer_id),
    )
    if not order:
        return jsonify({"ok": False, "message": "Order not found"}), 404
    items = db_fetchall(
        """
        SELECT oi.order_item_id, oi.quantity, oi.unit_price_bdt,
               p.product_id, p.title, p.image_path,
               a.artisan_id, a.name AS artisan_name
        FROM order_item oi
        JOIN product p ON p.product_id=oi.product_id
        LEFT JOIN artisan_product ap ON ap.product_id=p.product_id
        LEFT JOIN artisan a ON a.artisan_id=ap.artisan_id
        WHERE oi.order_id=%s
        ORDER BY oi.order_item_id ASC
        """,
        (order_id,),
    ) or []
    item_payload=[]
    first_artisan_id=None
    for item in items:
        if first_artisan_id is None and item.get('artisan_id'):
            first_artisan_id=int(item.get('artisan_id'))
        item_payload.append({
            "order_item_id": int(item.get("order_item_id") or 0),
            "product_id": int(item.get("product_id") or 0),
            "title": item.get("title") or "",
            "image": item.get("image_path") or "/static/assets/img/placeholder.jpg",
            "quantity": int(item.get("quantity") or 0),
            "unit_price_bdt": float(Decimal(str(item.get("unit_price_bdt") or 0))),
            "artisan_id": int(item.get("artisan_id") or 0) if item.get("artisan_id") else None,
            "artisan_name": item.get("artisan_name") or "",
        })
    timeline = build_order_timeline(order.get('status') or 'pending', order.get('created_at'), order.get('delivered_at'))
    provenance = []
    try:
        prow = db_fetchall("SELECT event_type, title, description, created_at FROM order_provenance_event WHERE order_item_id IN (SELECT order_item_id FROM order_item WHERE order_id=%s) ORDER BY created_at ASC LIMIT 50", (order_id,)) or []
        provenance = [{"event_type": r.get("event_type") or "", "title": r.get("title") or "", "description": r.get("description") or "", "time": r.get("created_at").strftime("%d %b %Y, %I:%M %p") if r.get("created_at") else ""} for r in prow]
    except Exception:
        provenance = []
    if not provenance:
        try:
            hrows = db_fetchall(
                "SELECT status, note, created_at FROM order_status_history WHERE order_id=%s ORDER BY created_at ASC LIMIT 50",
                (order_id,),
            ) or []
            phase_desc = {
                'pending': 'Your order has been secured in the archive.',
                'paid': 'Artisan and operations team are preparing the piece.',
                'processing': 'Artisan and operations team are preparing the piece.',
                'packed': 'Artisan and operations team are preparing the piece.',
                'shipped': 'The collection is on its way.',
                'delivered': 'Safely delivered to your address.',
                'cancelled': 'This order has been cancelled.',
            }
            if hrows:
                provenance = [{
                    'event_type': str(r.get('status') or '').lower(),
                    'title': get_order_current_phase(order_id, r.get('status') or 'pending', r.get('created_at'), order.get('delivered_at')).get('label') or 'Order Update',
                    'description': r.get('note') or phase_desc.get(str(r.get('status') or '').lower(), 'Order status updated.'),
                    'time': r.get('created_at').strftime('%d %b %Y, %I:%M %p') if r.get('created_at') else '',
                } for r in hrows]
        except Exception:
            provenance = []
    if not provenance:
        for idx, step in enumerate(timeline):
            if not step.get('date'):
                continue
            provenance.append({
                'event_type': f'timeline_{idx+1}',
                'title': step.get('label') or 'Order Update',
                'description': step.get('desc') or '',
                'time': step.get('date') or '',
            })
    return jsonify({"ok": True, "order": {
        "order_id": int(order.get("order_id") or 0),
        "display_id": format_order_id(order.get("order_id") or 0),
        "invoice_no": order.get("invoice_no") or format_prefixed_id('INV', order.get('order_id') or 0, 6),
        "status": order.get("status") or "",
        "subtotal_fmt": fmt_money(Decimal(str(order.get("subtotal_bdt") or 0))),
        "shipping_fmt": fmt_money(Decimal(str(order.get("shipping_bdt") or 0))),
        "discount_fmt": fmt_money(Decimal(str(order.get("discount_bdt") or 0))),
        "total_fmt": fmt_money(Decimal(str(order.get("total_bdt") or 0))),
        "timeline": timeline,
        "current_phase": get_order_current_phase(order_id, order.get("status") or "pending", order.get("created_at"), order.get("delivered_at")),
        "provenance": provenance,
        "items": item_payload,
        "contact_artisan_id": first_artisan_id,
        "invoice_url": url_for('buyer_order_invoice_pdf', order_id=order_id),
    }})


@app.get("/buyer/orders/<int:order_id>/invoice.pdf")
def buyer_order_invoice_pdf(order_id: int):
    gate = require_buyer()
    if gate:
        return gate
    buyer_id = current_user_id()
    order = db_fetchone(
        """
        SELECT o.*, ua.name AS buyer_name, ua.email AS buyer_email, ua.phone AS buyer_phone,
               bp.guardian_id, bp.address AS buyer_address
        FROM `order` o
        JOIN user_account ua ON ua.user_id=o.buyer_id
        LEFT JOIN buyer_profile bp ON bp.buyer_id=o.buyer_id
        WHERE o.order_id=%s AND o.buyer_id=%s
        LIMIT 1
        """,
        (order_id, buyer_id),
    )
    if not order:
        abort(404)

    items = db_fetchall(
        """
        SELECT oi.quantity, oi.unit_price_bdt,
               p.title, p.gi_tag,
               a.name AS artisan_name
        FROM order_item oi
        JOIN product p ON p.product_id=oi.product_id
        LEFT JOIN artisan_product ap ON ap.product_id=p.product_id
        LEFT JOIN artisan a ON a.artisan_id=ap.artisan_id
        WHERE oi.order_id=%s
        ORDER BY oi.order_item_id ASC
        """,
        (order_id,),
    ) or []

    def _dt(v, with_time=True):
        if not v:
            return ""
        try:
            return v.strftime('%B %d, %Y' + (', %I:%M %p' if with_time else ''))
        except Exception:
            return str(v)

    def _clean_join(parts):
        return ", ".join([str(x).strip() for x in parts if str(x or '').strip()])

    issued_at = order.get('placed_at') or order.get('created_at')

    def _normalize_phone(v: Any) -> str:
        raw = str(v or '').strip()
        if not raw:
            return ''
        return raw.replace(' ', '')

    def _split_profile_address(raw: Any) -> list[str]:
        text = str(raw or '').strip()
        if not text:
            return []
        text = text.replace('\r', '\n')
        parts = [seg.strip(' ,') for seg in re.split(r'\n+|\s*\|\s*', text) if seg and seg.strip(' ,')]
        if len(parts) >= 2:
            return parts[:3]
        comma_parts = [seg.strip() for seg in text.split(',') if seg.strip()]
        if len(comma_parts) >= 2:
            if len(comma_parts) >= 4:
                return [', '.join(comma_parts[:-2]), ', '.join(comma_parts[-2:-1]), comma_parts[-1]]
            return comma_parts[:3]
        return [text]

    def _derive_address_lines() -> list[str]:
        shipping_line_1 = _clean_join([
            order.get('shipping_address_line'),
            order.get('shipping_apartment'),
        ])
        shipping_line_2 = _clean_join([
            order.get('shipping_city'),
            order.get('postal_code'),
        ])
        shipping_line_3 = str(order.get('shipping_country') or '').strip()
        shipping_lines = [x for x in [shipping_line_1, shipping_line_2, shipping_line_3] if x]
        if shipping_lines:
            return shipping_lines
        return _split_profile_address(order.get('buyer_address'))

    status_raw = str(order.get('status') or '').strip().lower()
    if order.get('delivered_at'):
        delivery_eta = order.get('delivered_at')
    elif issued_at:
        offset_days = 5 if status_raw in {'pending', 'confirmed', 'processing'} else 3
        delivery_eta = issued_at + datetime.timedelta(days=offset_days)
    else:
        delivery_eta = None

    unified_name = str(order.get('shipping_name') or order.get('buyer_name') or 'Origins Guardian').strip()
    unified_lines = _derive_address_lines()
    billed_to_name = unified_name
    billed_to_lines = unified_lines
    delivery_to_name = unified_name
    delivery_lines = unified_lines
    subtotal = Decimal(str(order.get('subtotal_bdt') or 0))
    shipping = Decimal(str(order.get('shipping_bdt') or 0))
    discount = Decimal(str(order.get('discount_bdt') or 0))
    total = Decimal(str(order.get('total_bdt') or 0))
    payment_cleared = str(order.get('payment_status') or '').lower() in {'paid', 'cleared', 'complete', 'completed'}

    contact_email = str(order.get('shipping_email') or order.get('buyer_email') or '').strip()
    contact_phone = _normalize_phone(order.get('shipping_phone') or order.get('buyer_phone') or '')

    invoice = {
        'invoice_no': order.get('invoice_no') or format_prefixed_id('INV', order_id, 6),
        'order_ref': format_order_id(order_id),
        'issue_date': _dt(issued_at, with_time=False),
        'issue_stamp': _dt(issued_at, with_time=True),
        'guardian_id': normalize_guardian_id(order.get('guardian_id'), buyer_id),
        'payment_cleared': payment_cleared,
        'payment_status': (order.get('payment_status') or 'pending').title(),
        'billed_to': {
            'name': billed_to_name,
            'email': contact_email,
            'phone': contact_phone,
            'lines': [x for x in billed_to_lines if x],
        },
        'delivery_to': {
            'name': delivery_to_name,
            'email': contact_email,
            'phone': contact_phone,
            'lines': [x for x in delivery_lines if x],
            'expected': _dt(delivery_eta, with_time=False),
        },
        'items': [],
        'subtotal_fmt': fmt_money(subtotal),
        'shipping_fmt': fmt_money(shipping),
        'discount_fmt': fmt_money(discount),
        'total_fmt': fmt_money(total),
        'verify_url': f"https://originsbangladesh.com/verify/{order.get('invoice_no') or format_prefixed_id('INV', order_id, 6)}",
    }
    for item in items:
        qty = int(item.get('quantity') or 0)
        unit = Decimal(str(item.get('unit_price_bdt') or 0))
        invoice['items'].append({
            'title': item.get('title') or 'Artifact',
            'artisan_name': item.get('artisan_name') or '',
            'gi_tag': item.get('gi_tag') or '',
            'qty': qty,
            'unit_fmt': fmt_money(unit),
            'line_total_fmt': fmt_money(unit * qty),
        })

    def _qr_data_uri(payload: str) -> str:
        try:
            import base64, io
            import qrcode  # type: ignore
            img = qrcode.make(payload)
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode('ascii')
        except Exception:
            import base64, hashlib
            digest = hashlib.sha256(payload.encode('utf-8')).hexdigest()
            cells = []
            size = 29
            cell = 4
            pad = 8
            for y in range(size):
                for x in range(size):
                    idx = (x + y * size) % len(digest)
                    if int(digest[idx], 16) % 2 == 0:
                        cells.append(f'<rect x="{pad + x*cell}" y="{pad + y*cell}" width="{cell}" height="{cell}" fill="#111827"/>')
            svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{pad*2 + size*cell}" height="{pad*2 + size*cell}" viewBox="0 0 {pad*2 + size*cell} {pad*2 + size*cell}"><rect width="100%" height="100%" fill="#fff"/>{"".join(cells)}</svg>'
            return 'data:image/svg+xml;base64,' + base64.b64encode(svg.encode('utf-8')).decode('ascii')

    invoice['qr_code'] = _qr_data_uri(invoice['verify_url'])

    html = render_template('pages/buyer/invoice_document.html', invoice=invoice)

    try:
        from weasyprint import HTML  # type: ignore
        pdf_bytes = HTML(string=html, base_url=request.host_url.rstrip('/')).write_pdf()
        return Response(
            pdf_bytes,
            mimetype='application/pdf',
            headers={'Content-Disposition': f'inline; filename=invoice-{order_id}.pdf'},
        )
    except Exception:
        return Response(html, mimetype='text/html')


# -----------------------
# Seller APIs (DB-backed)
# -----------------------

def _require_seller_api():
    uid = current_user_id()
    if not uid:
        return jsonify({"ok": False, "message": "Not authenticated"}), 401
    if current_role() != "seller":
        return jsonify({"ok": False, "message": "Forbidden"}), 403
    return None


@app.get("/api/seller/profile")
def api_seller_profile_get():
    guard = _require_seller_api()
    if guard is not None:
        return guard
    seller_id = current_user_id()

    user = db_fetchone(
        "SELECT user_id, name, email, phone, created_at FROM user_account WHERE user_id=%s LIMIT 1",
        (seller_id,),
    ) or {}

    profile = {}
    try:
        prow = db_fetchone(
            "SELECT shop_name, owner_name, location, category, story, is_verified, created_at, avatar_url "
            "FROM seller_profile WHERE seller_id=%s LIMIT 1",
            (seller_id,),
        ) or {}
        profile = {
            "shop_name": prow.get("shop_name") or "",
            "owner_name": prow.get("owner_name") or "",
            "location": prow.get("location") or "",
            "category": prow.get("category") or "",
            "story": prow.get("story") or "",
            "is_verified": bool(prow.get("is_verified")),
            "member_since": (str(prow.get("created_at"))[:10] if prow.get("created_at") else ""),
            "avatar_url": prow.get("avatar_url") or "",
        }
    except Exception:
        # If avatar_url column not present or table missing, fall back safely
        try:
            prow = db_fetchone(
                "SELECT shop_name, owner_name, location, category, story, is_verified, created_at "
                "FROM seller_profile WHERE seller_id=%s LIMIT 1",
                (seller_id,),
            ) or {}
            profile = {
                "shop_name": prow.get("shop_name") or "",
                "owner_name": prow.get("owner_name") or "",
                "location": prow.get("location") or "",
                "category": prow.get("category") or "",
                "story": prow.get("story") or "",
                "is_verified": bool(prow.get("is_verified")),
                "member_since": (str(prow.get("created_at"))[:10] if prow.get("created_at") else ""),
                "avatar_url": "",
            }
        except Exception:
            profile = {
                "shop_name": "",
                "owner_name": "",
                "location": "",
                "category": "",
                "story": "",
                "is_verified": False,
                "member_since": "",
                "avatar_url": "",
            }

    return jsonify({"ok": True, "user": user, "profile": profile})


@app.route("/api/seller/profile", methods=["PUT","POST"])
def api_seller_profile_put():
    guard = _require_seller_api()
    if guard is not None:
        return guard
    seller_id = current_user_id()
    payload = request.get_json(silent=True) or {}

    # user_account fields
    owner_account_name = payload.get("owner_account_name")
    phone = payload.get("phone")

    # seller_profile fields
    shop_name = payload.get("shop_name")
    owner_name = payload.get("owner_name")
    location = payload.get("location")
    category = payload.get("category")
    story = payload.get("story")
    avatar_url = payload.get("avatar_url")

    try:
        if owner_account_name is not None:
            db_execute("UPDATE user_account SET name=%s WHERE user_id=%s", (owner_account_name, seller_id))
            session["name"] = owner_account_name
        if phone is not None:
            db_execute("UPDATE user_account SET phone=%s WHERE user_id=%s", (phone, seller_id))
        if email is not None:
            db_execute("UPDATE user_account SET email=%s WHERE user_id=%s", (str(email).strip(), seller_id))
            session["email"] = str(email).strip()
    except Exception as e:
        return jsonify({"ok": False, "message": "Account update failed", "detail": str(e)}), 500

    # Upsert seller_profile
    try:
        existing = db_fetchone("SELECT seller_id FROM seller_profile WHERE seller_id=%s LIMIT 1", (seller_id,))
        if not existing:
            db_execute(
                "INSERT INTO seller_profile (seller_id, shop_name, owner_name, location, category, story, is_verified) "
                "VALUES (%s, %s, %s, %s, %s, %s, 0)",
                (
                    seller_id,
                    shop_name or "",
                    owner_name or (session.get("name") or ""),
                    location or "",
                    category or "",
                    story or "",
                ),
            )

        if shop_name is not None:
            db_execute("UPDATE seller_profile SET shop_name=%s WHERE seller_id=%s", (shop_name, seller_id))
            session["seller_shop_name"] = shop_name
        if owner_name is not None:
            db_execute("UPDATE seller_profile SET owner_name=%s WHERE seller_id=%s", (owner_name, seller_id))
        if location is not None:
            db_execute("UPDATE seller_profile SET location=%s WHERE seller_id=%s", (location, seller_id))
        if category is not None:
            db_execute("UPDATE seller_profile SET category=%s WHERE seller_id=%s", (category, seller_id))
        if story is not None:
            db_execute("UPDATE seller_profile SET story=%s WHERE seller_id=%s", (story, seller_id))
        if avatar_url is not None:
            # Column may not exist; safe try.
            try:
                db_execute("UPDATE seller_profile SET avatar_url=%s WHERE seller_id=%s", (avatar_url, seller_id))
                session["avatar_url"] = avatar_url
            except Exception:
                pass
    except Exception as e:
        return jsonify({"ok": False, "message": "Profile update failed. Did you run the seller migration SQL?", "detail": str(e)}), 500

    return jsonify({"ok": True})


@app.post("/api/seller/password")
def api_seller_password_update():
    guard = _require_seller_api()
    if guard is not None:
        return guard
    seller_id = current_user_id()
    payload = request.get_json(silent=True) or {}
    current_password = str(payload.get("current_password") or "")
    new_password = str(payload.get("new_password") or "")
    confirm_password = str(payload.get("confirm_password") or "")

    if not new_password or not confirm_password:
        return jsonify({"ok": False, "message": "New password and confirm password are required."}), 400
    if new_password != confirm_password:
        return jsonify({"ok": False, "message": "Passwords do not match."}), 400
    if len(new_password) < 6:
        return jsonify({"ok": False, "message": "Password must be at least 6 characters long."}), 400

    user = db_fetchone("SELECT password_hash FROM user_account WHERE user_id=%s LIMIT 1", (seller_id,)) or {}
    stored = user.get("password_hash") or ""
    if current_password and stored and not check_password_hash(stored, current_password):
        return jsonify({"ok": False, "message": "Current password is incorrect."}), 400

    db_execute("UPDATE user_account SET password_hash=%s WHERE user_id=%s", (generate_password_hash(new_password), seller_id))
    audit_log("seller_password_updated", target_user_id=seller_id)
    return jsonify({"ok": True, "message": "Password updated successfully."})


@app.post("/api/seller/profile/avatar")
def api_seller_profile_avatar_upload():
    guard = _require_seller_api()
    if guard is not None:
        return guard
    seller_id = current_user_id()

    file = request.files.get("avatar")
    if not file or not file.filename:
        return jsonify({"ok": False, "message": "No file uploaded"}), 400

    filename = secure_filename(file.filename)
    ext = os.path.splitext(filename)[1].lower()
    if ext not in [".png", ".jpg", ".jpeg", ".webp"]:
        return jsonify({"ok": False, "message": "Only PNG/JPG/WEBP allowed"}), 400

    rel_dir = f"static/assets/pic/sellers/{seller_id}"
    abs_dir = os.path.join(app.root_path, rel_dir)
    os.makedirs(abs_dir, exist_ok=True)

    save_name = f"avatar{ext}"
    abs_path = os.path.join(abs_dir, save_name)
    file.save(abs_path)

    avatar_url = f"/{rel_dir}/{save_name}"
    session["avatar_url"] = avatar_url

    # Persist to DB if column exists
    try:
        db_execute("UPDATE seller_profile SET avatar_url=%s WHERE seller_id=%s", (avatar_url, seller_id))
    except Exception as e:
        return jsonify({"ok": True, "avatar_url": avatar_url, "warning": "Avatar saved to static, but DB column missing.", "detail": str(e)})

    return jsonify({"ok": True, "avatar_url": avatar_url})




# -----------------------
# Seller dashboard mutation APIs
# -----------------------

def _seller_basic_avatar_url() -> str:
    return "/static/assets/img/basic-avatar.svg"

def _parse_order_ref(order_ref: str) -> int:
    raw = str(order_ref or "").strip()
    m = re.search(r"(\d+)$", raw)
    return int(m.group(1)) if m else 0

def _save_upload(file_storage, rel_dir: str, *, allowed_ext=None, name_prefix="file") -> str:
    filename = secure_filename(file_storage.filename or "")
    ext = os.path.splitext(filename)[1].lower()
    if allowed_ext and ext not in allowed_ext:
        raise ValueError("unsupported_file_type")
    abs_dir = os.path.join(app.root_path, rel_dir)
    os.makedirs(abs_dir, exist_ok=True)
    save_name = f"{name_prefix}-{int(time.time()*1000)}{ext}"
    abs_path = os.path.join(abs_dir, save_name)
    file_storage.save(abs_path)
    return f"/{rel_dir}/{save_name}"

def _ensure_category(name: str) -> int:
    nm = (name or "General").strip() or "General"
    row = db_fetchone("SELECT category_id FROM category WHERE LOWER(name)=LOWER(%s) LIMIT 1", (nm,))
    if row:
        return int(row.get("category_id") or 0)
    return int(db_execute("INSERT INTO category (name) VALUES (%s)", (nm,), return_lastrowid=True) or 0)

def _seller_owns_product(product_id: int, seller_id: int) -> bool:
    row = db_fetchone("SELECT product_id FROM product WHERE product_id=%s AND seller_id=%s LIMIT 1", (product_id, seller_id))
    return bool(row)

def _seller_owns_order(order_id: int, seller_id: int) -> bool:
    row = db_fetchone(
        """
        SELECT o.order_id
        FROM `order` o
        JOIN order_item oi ON oi.order_id=o.order_id
        JOIN product p ON p.product_id=oi.product_id
        WHERE o.order_id=%s AND p.seller_id=%s
        LIMIT 1
        """,
        (order_id, seller_id),
    )
    return bool(row)

def _create_order_event(order_id: int, status: str, note: str, actor_type: str = "seller") -> None:
    try:
        db_execute(
            "INSERT INTO order_status_history (order_id, status, note, actor_type) VALUES (%s,%s,%s,%s)",
            (order_id, status, note, actor_type),
        )
    except Exception:
        pass

@app.get("/api/seller/dashboard-data")
def api_seller_dashboard_data():
    guard = _require_seller_api()
    if guard is not None:
        return guard
    uid = int(current_user_id() or 0)
    return jsonify({"ok": True, "data": _build_seller_dashboard_data(uid)})

@app.post("/api/seller/products/upload-image")
def api_seller_product_image_upload():
    guard = _require_seller_api()
    if guard is not None:
        return guard
    file = request.files.get("image")
    if not file or not file.filename:
        return jsonify({"ok": False, "message": "No image uploaded."}), 400
    try:
        url = _save_upload(
            file,
            f"static/uploads/seller-products/{int(current_user_id() or 0)}",
            allowed_ext={".png", ".jpg", ".jpeg", ".webp"},
            name_prefix="product",
        )
        return jsonify({"ok": True, "image_url": url})
    except ValueError:
        return jsonify({"ok": False, "message": "Only PNG/JPG/WEBP allowed."}), 400
    except Exception as e:
        return jsonify({"ok": False, "message": "Image upload failed.", "detail": str(e)}), 500

@app.post("/api/seller/products")
def api_seller_products_create():
    guard = _require_seller_api()
    if guard is not None:
        return guard
    seller_id = int(current_user_id() or 0)
    payload = request.get_json(silent=True) or {}
    title = str(payload.get("name") or payload.get("title") or "").strip()
    if not title:
        return jsonify({"ok": False, "message": "Product name is required."}), 400
    try:
        price = Decimal(str(payload.get("price") or "0"))
    except Exception:
        price = Decimal("0")
    stock = _safe_int(payload.get("stock"))
    category_id = _ensure_category(str(payload.get("category") or "General"))
    description = str(payload.get("story") or payload.get("description") or "").strip()
    image_path = str(payload.get("image") or payload.get("image_path") or "").strip() or None
    is_active = str(payload.get("status") or "Live").lower() != "draft"
    pid = db_execute(
        """
        INSERT INTO product (seller_id, title, description, price_bdt, stock, category_id, image_path, is_active)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (seller_id, title, description, price, stock, category_id, image_path, 1 if is_active else 0),
        return_lastrowid=True,
    )
    try:
        db_execute(
            "INSERT IGNORE INTO admin_qc_item (product_id, seller_id, status) VALUES (%s,%s,%s)",
            (pid, seller_id, "Pending"),
        )
    except Exception:
        pass
    return jsonify({"ok": True, "product_id": pid})

@app.put("/api/seller/products/<int:product_id>")
def api_seller_products_update(product_id: int):
    guard = _require_seller_api()
    if guard is not None:
        return guard
    seller_id = int(current_user_id() or 0)
    if not _seller_owns_product(product_id, seller_id):
        return jsonify({"ok": False, "message": "Product not found."}), 404
    payload = request.get_json(silent=True) or {}
    title = str(payload.get("name") or payload.get("title") or "").strip()
    if not title:
        return jsonify({"ok": False, "message": "Product name is required."}), 400
    try:
        price = Decimal(str(payload.get("price") or "0"))
    except Exception:
        price = Decimal("0")
    stock = _safe_int(payload.get("stock"))
    category_id = _ensure_category(str(payload.get("category") or "General"))
    description = str(payload.get("story") or payload.get("description") or "").strip()
    image_path = str(payload.get("image") or payload.get("image_path") or "").strip() or None
    is_active = str(payload.get("status") or "Live").lower() != "draft"
    db_execute(
        """
        UPDATE product
        SET title=%s, description=%s, price_bdt=%s, stock=%s, category_id=%s, image_path=%s, is_active=%s
        WHERE product_id=%s AND seller_id=%s
        """,
        (title, description, price, stock, category_id, image_path, 1 if is_active else 0, product_id, seller_id),
    )
    return jsonify({"ok": True})

@app.delete("/api/seller/products/<int:product_id>")
def api_seller_products_delete(product_id: int):
    guard = _require_seller_api()
    if guard is not None:
        return guard
    seller_id = int(current_user_id() or 0)
    if not _seller_owns_product(product_id, seller_id):
        return jsonify({"ok": False, "message": "Product not found."}), 404
    dep = db_fetchone("SELECT COUNT(*) AS c FROM order_item WHERE product_id=%s", (product_id,)) or {}
    if int(dep.get("c") or 0) > 0:
        db_execute("UPDATE product SET is_active=0 WHERE product_id=%s AND seller_id=%s", (product_id, seller_id))
        return jsonify({"ok": True, "message": "Product archived because it already has orders."})
    db_execute("DELETE FROM product WHERE product_id=%s AND seller_id=%s", (product_id, seller_id))
    return jsonify({"ok": True})

@app.post("/api/seller/orders/<order_ref>/status")
def api_seller_order_status(order_ref: str):
    guard = _require_seller_api()
    if guard is not None:
        return guard
    seller_id = int(current_user_id() or 0)
    order_id = _parse_order_ref(order_ref)
    if not order_id or not _seller_owns_order(order_id, seller_id):
        return jsonify({"ok": False, "message": "Order not found."}), 404
    payload = request.get_json(silent=True) or {}
    action = str(payload.get("action") or payload.get("status") or "").strip().lower()
    current = db_fetchone("SELECT status FROM `order` WHERE order_id=%s LIMIT 1", (order_id,)) or {}
    cur = str(current.get("status") or "pending").lower()
    action_map = {
        "accept": ("paid", "Order accepted by seller."),
        "processing": ("paid", "Order moved to processing."),
        "ready": ("shipped", "Order packed and ready for dispatch."),
        "ship": ("shipped", "Order shipped by seller."),
        "delivered": ("delivered", "Order marked delivered by seller."),
        "cancel": ("cancelled", "Order cancelled by seller."),
    }
    if action not in action_map:
        return jsonify({"ok": False, "message": "Invalid order action."}), 400
    new_status, note = action_map[action]
    if new_status == "delivered":
        db_execute("UPDATE `order` SET status=%s, delivered_at=NOW() WHERE order_id=%s", (new_status, order_id))
    else:
        db_execute("UPDATE `order` SET status=%s WHERE order_id=%s", (new_status, order_id))
    _create_order_event(order_id, new_status, note)
    buyer = db_fetchone("SELECT buyer_id FROM `order` WHERE order_id=%s LIMIT 1", (order_id,)) or {}
    if buyer.get("buyer_id"):
        create_notification(
            recipient_user_id=int(buyer.get("buyer_id")),
            type="order_update",
            title=f"Order {format_order_id(order_id)} updated",
            body=note,
            link="/buyer/dashboard?view=orders",
        )
    send_order_status_email(order_id, action, note)
    return jsonify({"ok": True, "status": new_status, "previous_status": cur})

@app.get("/api/seller/payout-methods")
def api_seller_payout_methods_list():
    guard = _require_seller_api()
    if guard is not None:
        return guard
    seller_id = int(current_user_id() or 0)
    rows = db_fetchall(
        "SELECT method_id, provider, account_number, created_at FROM seller_payout_method WHERE seller_id=%s ORDER BY created_at DESC, method_id DESC",
        (seller_id,),
    )
    return jsonify({"ok": True, "methods": rows})

@app.post("/api/seller/payout-methods")
def api_seller_payout_methods_create():
    guard = _require_seller_api()
    if guard is not None:
        return guard
    seller_id = int(current_user_id() or 0)
    payload = request.get_json(silent=True) or {}
    provider = str(payload.get("provider") or "").strip()
    account_number = str(payload.get("account_number") or "").strip()
    if not provider or not account_number:
        return jsonify({"ok": False, "message": "Provider and account number are required."}), 400
    mid = db_execute(
        "INSERT INTO seller_payout_method (seller_id, provider, account_number) VALUES (%s,%s,%s)",
        (seller_id, provider, account_number),
        return_lastrowid=True,
    )
    return jsonify({"ok": True, "method_id": mid})

@app.delete("/api/seller/payout-methods/<int:method_id>")
def api_seller_payout_methods_delete(method_id: int):
    guard = _require_seller_api()
    if guard is not None:
        return guard
    seller_id = int(current_user_id() or 0)
    db_execute("DELETE FROM seller_payout_method WHERE method_id=%s AND seller_id=%s", (method_id, seller_id))
    return jsonify({"ok": True})

@app.post("/api/seller/gi-applications")
def api_seller_gi_create():
    guard = _require_seller_api()
    if guard is not None:
        return guard
    seller_id = int(current_user_id() or 0)
    payload = request.get_json(silent=True) if request.is_json else None
    product_name = str((request.form.get("product_name") if not payload else payload.get("product_name")) or "").strip()
    category = str((request.form.get("category") if not payload else payload.get("category")) or "").strip()
    details = str((request.form.get("details") if not payload else payload.get("details")) or "").strip()
    if not product_name or not details:
        return jsonify({"ok": False, "message": "Product name and details are required."}), 400
    cert_path = None
    file = request.files.get("certificate")
    if file and file.filename:
        try:
            cert_path = _save_upload(
                file,
                f"static/uploads/gi/{seller_id}",
                allowed_ext={".png", ".jpg", ".jpeg", ".webp", ".pdf", ".doc", ".docx"},
                name_prefix="gi",
            )
        except ValueError:
            return jsonify({"ok": False, "message": "Unsupported GI certificate type."}), 400
    app_id = db_execute(
        "INSERT INTO seller_gi_application (seller_id, product_name, category, details, certificate_path, status, feedback) VALUES (%s,%s,%s,%s,%s,%s,%s)",
        (seller_id, product_name, category or None, details, cert_path, "pending", "Awaiting committee review."),
        return_lastrowid=True,
    )
    return jsonify({"ok": True, "app_id": app_id})

@app.delete("/api/seller/gi-applications/<int:app_id>")
def api_seller_gi_delete(app_id: int):
    guard = _require_seller_api()
    if guard is not None:
        return guard
    seller_id = int(current_user_id() or 0)
    db_execute("DELETE FROM seller_gi_application WHERE app_id=%s AND seller_id=%s", (app_id, seller_id))
    return jsonify({"ok": True})

@app.post("/api/seller/verification/upload")
def api_seller_verification_upload():
    guard = _require_seller_api()
    if guard is not None:
        return guard
    seller_id = int(current_user_id() or 0)
    doc_type = str(request.form.get("doc_type") or "").strip()
    file = request.files.get("file")
    if not doc_type or not file or not file.filename:
        return jsonify({"ok": False, "message": "Document type and file are required."}), 400
    try:
        file_path = _save_upload(
            file,
            f"static/uploads/verification/{seller_id}",
            allowed_ext={".png", ".jpg", ".jpeg", ".webp", ".pdf", ".doc", ".docx"},
            name_prefix=doc_type,
        )
    except ValueError:
        return jsonify({"ok": False, "message": "Unsupported verification document type."}), 400
    db_execute(
        """
        INSERT INTO seller_verification_doc (seller_id, doc_type, file_path) VALUES (%s,%s,%s)
        ON DUPLICATE KEY UPDATE file_path=VALUES(file_path), uploaded_at=CURRENT_TIMESTAMP
        """,
        (seller_id, doc_type, file_path),
    )
    return jsonify({"ok": True, "file_path": file_path})

@app.post("/api/seller/verification/submit")
def api_seller_verification_submit():
    guard = _require_seller_api()
    if guard is not None:
        return guard
    seller_id = int(current_user_id() or 0)
    try:
        rows = db_fetchall("SELECT doc_type FROM seller_verification_doc WHERE seller_id=%s", (seller_id,))
        have = {str(r.get("doc_type") or "") for r in rows}
        needed = {"nidFront", "nidBack", "tradeLicense", "tin", "bankCheque"}
        if not needed.issubset(have):
            return jsonify({"ok": False, "message": "Please upload all required verification documents."}), 400
        profile_exists = db_fetchone("SELECT seller_id FROM seller_profile WHERE seller_id=%s", (seller_id,))
        if not profile_exists:
            user_row = db_fetchone("SELECT name FROM user_account WHERE user_id=%s", (seller_id,)) or {}
            shop_name = (user_row.get("name") or "Seller").strip() or "Seller"
            db_execute(
                "INSERT INTO seller_profile (seller_id, shop_name, owner_name, verification_status, is_verified) VALUES (%s,%s,%s,'draft',0)",
                (seller_id, shop_name, shop_name),
            )
        db_execute("UPDATE seller_profile SET verification_status='submitted', is_verified=0, rejection_reason=NULL WHERE seller_id=%s", (seller_id,))
        create_notification(
            recipient_user_id=seller_id,
            type="seller_verification",
            title="Verification submitted",
            body="Your documents were submitted for review.",
            link="/seller/dashboard?view=verification",
        )
        return jsonify({"ok": True})
    except Exception as exc:
        return jsonify({"ok": False, "message": str(exc) or "Verification submission failed."}), 500

@app.get("/api/seller/support/<channel>")
def api_seller_support_list(channel: str):
    guard = _require_seller_api()
    if guard is not None:
        return guard
    seller_id = int(current_user_id() or 0)
    ch = "b2b" if str(channel).lower() == "b2b" else "admin"
    rows = db_fetchall(
        "SELECT msg_id, sender, body, created_at, is_read FROM seller_support_message WHERE seller_id=%s AND channel=%s ORDER BY msg_id ASC LIMIT 200",
        (seller_id, ch),
    )
    return jsonify({"ok": True, "messages": rows})

@app.post("/api/seller/support/<channel>")
def api_seller_support_send(channel: str):
    guard = _require_seller_api()
    if guard is not None:
        return guard
    seller_id = int(current_user_id() or 0)
    ch = "b2b" if str(channel).lower() == "b2b" else "admin"
    payload = request.get_json(silent=True) or {}
    body = str(payload.get("body") or "").strip()
    if not body:
        return jsonify({"ok": False, "message": "Message body is required."}), 400
    msg_id = db_execute(
        "INSERT INTO seller_support_message (seller_id, channel, sender, body, is_read) VALUES (%s,%s,%s,%s,%s)",
        (seller_id, ch, "seller", body, 0),
        return_lastrowid=True,
    )
    return jsonify({"ok": True, "msg_id": msg_id})

@app.post("/api/seller/campaign-requests")
def api_seller_campaign_request():
    guard = _require_seller_api()
    if guard is not None:
        return guard
    seller_id = int(current_user_id() or 0)
    payload = request.get_json(silent=True) or {}
    product = str(payload.get("product") or "").strip()
    campaign = str(payload.get("campaign") or "").strip()
    discount = _safe_int(payload.get("discount"))
    if not product or not campaign or discount <= 0:
        return jsonify({"ok": False, "message": "Product, campaign and discount are required."}), 400
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS seller_campaign_request (
              request_id BIGINT AUTO_INCREMENT PRIMARY KEY,
              seller_id INT NOT NULL,
              product_name VARCHAR(180) NOT NULL,
              campaign_name VARCHAR(180) NOT NULL,
              discount_pct INT NOT NULL DEFAULT 0,
              status VARCHAR(40) NOT NULL DEFAULT 'Pending Review',
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              INDEX idx_scr_seller (seller_id, created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )
        cur.execute(
            "INSERT INTO seller_campaign_request (seller_id, product_name, campaign_name, discount_pct) VALUES (%s,%s,%s,%s)",
            (seller_id, product, campaign, discount),
        )
        conn.commit()
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(debug=True)
