
-- Origins Bangladesh - app.py compatible master schema
-- Based on: database/schema.sql + migrations + app.py bootstrap tables
-- MySQL 8+

DROP DATABASE IF EXISTS origins_bangladesh;
CREATE DATABASE origins_bangladesh CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE origins_bangladesh;

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS=0;

DROP TABLE IF EXISTS buyer_vault_tag;
DROP TABLE IF EXISTS admin_permission;
DROP TABLE IF EXISTS notification;
DROP TABLE IF EXISTS security_event;
DROP TABLE IF EXISTS action_approval;
DROP TABLE IF EXISTS email_template;
DROP TABLE IF EXISTS report_export;
DROP TABLE IF EXISTS access_block;
DROP TABLE IF EXISTS backup_log;
DROP TABLE IF EXISTS payout_request;
DROP TABLE IF EXISTS audit_log;
DROP TABLE IF EXISTS system_setting;
DROP TABLE IF EXISTS admin_profile;
DROP TABLE IF EXISTS chat_message;
DROP TABLE IF EXISTS chat_thread;
DROP TABLE IF EXISTS ob_id_sequence;
DROP TABLE IF EXISTS seller_support_message;
DROP TABLE IF EXISTS seller_gi_application;
DROP TABLE IF EXISTS seller_transaction;
DROP TABLE IF EXISTS seller_payout_method;
DROP TABLE IF EXISTS seller_wallet;
DROP TABLE IF EXISTS seller_verification_doc;
DROP TABLE IF EXISTS auth_token;
DROP TABLE IF EXISTS trusted_device;
DROP TABLE IF EXISTS order_item;
DROP TABLE IF EXISTS `order`;
DROP TABLE IF EXISTS cart_item;
DROP TABLE IF EXISTS cart;
DROP TABLE IF EXISTS wishlist;
DROP TABLE IF EXISTS gi_tag_verification_log;
DROP TABLE IF EXISTS buyer_profile;
DROP TABLE IF EXISTS gi_tag;
DROP TABLE IF EXISTS soundscape_track;
DROP TABLE IF EXISTS gi_journal_article;
DROP TABLE IF EXISTS artisan_product;
DROP TABLE IF EXISTS artisan_story;
DROP TABLE IF EXISTS product;
DROP TABLE IF EXISTS artisan;
DROP TABLE IF EXISTS district_atlas;
DROP TABLE IF EXISTS district;
DROP TABLE IF EXISTS subcategory;
DROP TABLE IF EXISTS category;
DROP TABLE IF EXISTS seller_profile;
DROP TABLE IF EXISTS currency_rate;
DROP TABLE IF EXISTS user_account;

SET FOREIGN_KEY_CHECKS=1;

CREATE TABLE user_account (
  user_id INT AUTO_INCREMENT PRIMARY KEY,
  role ENUM('buyer','seller','admin','superadmin') NOT NULL DEFAULT 'buyer',
  public_id VARCHAR(32) NULL UNIQUE,
  name VARCHAR(120) NOT NULL,
  email VARCHAR(180) NOT NULL UNIQUE,
  phone VARCHAR(30) NOT NULL,
  password_hash VARCHAR(255) NULL,
  secret_code_hash VARCHAR(255) NULL,
  is_email_verified BOOLEAN NOT NULL DEFAULT FALSE,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_user_role_active (role, is_active),
  INDEX idx_user_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE seller_profile (
  seller_id INT PRIMARY KEY,
  shop_name VARCHAR(160) NOT NULL,
  owner_name VARCHAR(120) NOT NULL,
  location VARCHAR(120) NULL,
  category VARCHAR(120) NULL,
  story TEXT NULL,
  avatar_url VARCHAR(500) NULL,
  is_verified BOOLEAN NOT NULL DEFAULT FALSE,
  verification_status ENUM('draft','submitted','under_review','approved','rejected') NOT NULL DEFAULT 'draft',
  reviewed_by INT NULL,
  reviewed_at TIMESTAMP NULL,
  rejection_reason VARCHAR(500) NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_seller_user FOREIGN KEY (seller_id)
    REFERENCES user_account(user_id) ON DELETE CASCADE,
  CONSTRAINT fk_seller_reviewed_by FOREIGN KEY (reviewed_by)
    REFERENCES user_account(user_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE buyer_profile (
  buyer_id INT PRIMARY KEY,
  address VARCHAR(255) NULL,
  bio TEXT NULL,
  avatar_url VARCHAR(255) NULL,
  points INT NOT NULL DEFAULT 0,
  guardian_id VARCHAR(32) NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_buyer_profile_buyer FOREIGN KEY (buyer_id)
    REFERENCES user_account(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE admin_profile (
  admin_id INT PRIMARY KEY,
  designation VARCHAR(120) NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_admin_profile_user FOREIGN KEY (admin_id)
    REFERENCES user_account(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE auth_token (
  token_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  email VARCHAR(180) NOT NULL,
  user_id INT NULL,
  purpose ENUM('login','verify','reset','admin_login','superadmin_login') NOT NULL,
  code_hash CHAR(64) NOT NULL,
  token_hash CHAR(64) NOT NULL,
  salt CHAR(16) NOT NULL,
  expires_at TIMESTAMP NOT NULL,
  consumed_at TIMESTAMP NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_auth_email_purpose (email, purpose),
  INDEX idx_auth_user (user_id),
  CONSTRAINT fk_auth_user FOREIGN KEY (user_id)
    REFERENCES user_account(user_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE trusted_device (
  device_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  device_hash CHAR(64) NOT NULL,
  revoke_hash CHAR(64) NOT NULL,
  label VARCHAR(120) NULL,
  ip VARCHAR(64) NULL,
  user_agent VARCHAR(255) NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  last_seen_at TIMESTAMP NULL,
  expires_at TIMESTAMP NOT NULL,
  revoked_at TIMESTAMP NULL,
  UNIQUE KEY uq_device (user_id, device_hash),
  INDEX idx_device_user (user_id),
  CONSTRAINT fk_device_user FOREIGN KEY (user_id)
    REFERENCES user_account(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE category (
  category_id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(120) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE subcategory (
  subcategory_id INT AUTO_INCREMENT PRIMARY KEY,
  category_id INT NOT NULL,
  name VARCHAR(120) NOT NULL,
  UNIQUE KEY uq_sub (category_id, name),
  CONSTRAINT fk_sub_cat FOREIGN KEY (category_id)
    REFERENCES category(category_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE district (
  district_id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(80) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE district_atlas (
  atlas_id INT AUTO_INCREMENT PRIMARY KEY,
  district_id INT NOT NULL,
  density ENUM('low','med','high') NOT NULL DEFAULT 'low',
  product_name VARCHAR(255) NOT NULL DEFAULT 'No Official GI Product',
  category VARCHAR(80) NOT NULL DEFAULT 'N/A',
  story TEXT NULL,
  image_url VARCHAR(500) NULL,
  shop_link VARCHAR(500) NULL,
  dot_x DECIMAL(8,2) NULL,
  dot_y DECIMAL(8,2) NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_district_atlas_district (district_id),
  INDEX idx_district_atlas_active (is_active, density),
  CONSTRAINT fk_district_atlas_district FOREIGN KEY (district_id)
    REFERENCES district(district_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE currency_rate (
  code CHAR(3) PRIMARY KEY,
  rate_to_bdt DECIMAL(12,6) NOT NULL,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE artisan (
  artisan_id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  specialty_title VARCHAR(200) NULL,
  location_text VARCHAR(160) NULL,
  badge_text VARCHAR(80) NULL,
  hero_image VARCHAR(255) NULL,
  tag VARCHAR(80) NULL,
  quote_text TEXT NULL,
  started_year INT NULL,
  years_mastery INT NULL,
  pieces_created INT NULL,
  is_featured BOOLEAN NOT NULL DEFAULT FALSE,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_artisan_featured (is_featured, is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE artisan_story (
  story_id INT AUTO_INCREMENT PRIMARY KEY,
  artisan_id INT NOT NULL,
  headline VARCHAR(200) NULL,
  video_url VARCHAR(255) NULL,
  body TEXT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_story_artisan (artisan_id, is_active, published_at),
  CONSTRAINT fk_story_artisan FOREIGN KEY (artisan_id)
    REFERENCES artisan(artisan_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE product (
  product_id INT AUTO_INCREMENT PRIMARY KEY,
  seller_id INT NOT NULL,
  title VARCHAR(200) NOT NULL,
  description TEXT NULL,
  price_bdt DECIMAL(12,2) NOT NULL,
  stock INT DEFAULT 0,
  category_id INT NOT NULL,
  subcategory_id INT NULL,
  district_id INT NULL,
  gi_tag VARCHAR(120) NULL,
  image_path VARCHAR(255) NULL,
  is_flash_sale BOOLEAN DEFAULT FALSE,
  flash_discount INT NULL,
  discovery_score DECIMAL(10,4) DEFAULT 0,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_prod_search (title),
  INDEX idx_prod_cat (category_id, subcategory_id),
  INDEX idx_prod_seller_active (seller_id, is_active, created_at),
  CONSTRAINT fk_prod_seller FOREIGN KEY (seller_id)
    REFERENCES seller_profile(seller_id) ON DELETE RESTRICT,
  CONSTRAINT fk_prod_cat FOREIGN KEY (category_id)
    REFERENCES category(category_id),
  CONSTRAINT fk_prod_sub FOREIGN KEY (subcategory_id)
    REFERENCES subcategory(subcategory_id),
  CONSTRAINT fk_prod_dist FOREIGN KEY (district_id)
    REFERENCES district(district_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE gi_tag (
  tag_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  tag_code VARCHAR(40) NOT NULL UNIQUE,
  product_id INT NOT NULL,
  issued_to_artisan_id INT NULL,
  status ENUM('active','revoked') NOT NULL DEFAULT 'active',
  issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  first_verified_at TIMESTAMP NULL,
  last_verified_at TIMESTAMP NULL,
  verify_count INT NOT NULL DEFAULT 0,
  last_verified_ip VARCHAR(64) NULL,
  last_verified_user_agent VARCHAR(255) NULL,
  note VARCHAR(255) NULL,
  INDEX idx_gi_product (product_id),
  INDEX idx_gi_status (status),
  CONSTRAINT fk_gi_product FOREIGN KEY (product_id)
    REFERENCES product(product_id) ON DELETE CASCADE,
  CONSTRAINT fk_gi_artisan FOREIGN KEY (issued_to_artisan_id)
    REFERENCES artisan(artisan_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE gi_tag_verification_log (
  log_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  tag_id BIGINT NULL,
  attempted_code VARCHAR(40) NOT NULL,
  result ENUM('verified','not_found','revoked','invalid_format') NOT NULL,
  ip VARCHAR(64) NULL,
  user_agent VARCHAR(255) NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_gi_log_tag (tag_id, created_at),
  INDEX idx_gi_log_code (attempted_code, created_at),
  CONSTRAINT fk_gi_log_tag FOREIGN KEY (tag_id)
    REFERENCES gi_tag(tag_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE gi_journal_article (
  article_id INT AUTO_INCREMENT PRIMARY KEY,
  slug VARCHAR(160) NOT NULL UNIQUE,
  title VARCHAR(220) NOT NULL,
  subtitle VARCHAR(260) NULL,
  category VARCHAR(60) NULL,
  read_minutes INT NULL,
  hero_image_url VARCHAR(500) NULL,
  thumb_image_url VARCHAR(500) NULL,
  teaser TEXT NULL,
  content_html MEDIUMTEXT NULL,
  is_featured BOOLEAN NOT NULL DEFAULT FALSE,
  quote_text TEXT NULL,
  quote_author VARCHAR(140) NULL,
  published_at TIMESTAMP NULL DEFAULT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_journal_featured (is_featured, published_at),
  INDEX idx_journal_category (category, published_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE soundscape_track (
  track_id INT AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(160) NOT NULL,
  subtitle VARCHAR(240) NULL,
  duration_sec INT NULL,
  audio_url VARCHAR(500) NOT NULL,
  cover_image_url VARCHAR(500) NULL,
  craft_tag VARCHAR(80) NULL,
  district_id INT NULL,
  is_featured BOOLEAN NOT NULL DEFAULT FALSE,
  sort_order INT NOT NULL DEFAULT 0,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_sound_active (is_active, is_featured, sort_order),
  CONSTRAINT fk_sound_district FOREIGN KEY (district_id)
    REFERENCES district(district_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE artisan_product (
  artisan_id INT NOT NULL,
  product_id INT NOT NULL,
  PRIMARY KEY (artisan_id, product_id),
  INDEX idx_ap_product (product_id),
  CONSTRAINT fk_ap_artisan FOREIGN KEY (artisan_id)
    REFERENCES artisan(artisan_id) ON DELETE CASCADE,
  CONSTRAINT fk_ap_product FOREIGN KEY (product_id)
    REFERENCES product(product_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE wishlist (
  wishlist_id INT AUTO_INCREMENT PRIMARY KEY,
  buyer_id INT NOT NULL,
  product_id INT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_wish (buyer_id, product_id),
  CONSTRAINT fk_wish_buyer FOREIGN KEY (buyer_id)
    REFERENCES user_account(user_id) ON DELETE CASCADE,
  CONSTRAINT fk_wish_product FOREIGN KEY (product_id)
    REFERENCES product(product_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE cart (
  cart_id INT AUTO_INCREMENT PRIMARY KEY,
  buyer_id INT NOT NULL UNIQUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_cart_buyer FOREIGN KEY (buyer_id)
    REFERENCES user_account(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE cart_item (
  cart_item_id INT AUTO_INCREMENT PRIMARY KEY,
  cart_id INT NOT NULL,
  product_id INT NOT NULL,
  quantity INT NOT NULL DEFAULT 1,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_cart_item (cart_id, product_id),
  CONSTRAINT fk_ci_cart FOREIGN KEY (cart_id)
    REFERENCES cart(cart_id) ON DELETE CASCADE,
  CONSTRAINT fk_ci_product FOREIGN KEY (product_id)
    REFERENCES product(product_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `order` (
  order_id INT AUTO_INCREMENT PRIMARY KEY,
  buyer_id INT NOT NULL,
  status ENUM('pending','paid','shipped','delivered','cancelled') DEFAULT 'pending',
  subtotal_bdt DECIMAL(12,2) NOT NULL DEFAULT 0,
  shipping_bdt DECIMAL(12,2) NOT NULL DEFAULT 0,
  discount_bdt DECIMAL(12,2) NOT NULL DEFAULT 0,
  coupon_id INT NULL,
  total_bdt DECIMAL(12,2) NOT NULL DEFAULT 0,
  payment_status VARCHAR(20) NOT NULL DEFAULT 'pending',
  payment_method VARCHAR(40) NULL,
  shipping_name VARCHAR(120) NULL,
  shipping_phone VARCHAR(40) NULL,
  shipping_email VARCHAR(180) NULL,
  shipping_address_line VARCHAR(255) NULL,
  shipping_apartment VARCHAR(255) NULL,
  shipping_country VARCHAR(120) NULL,
  shipping_city VARCHAR(120) NULL,
  postal_code VARCHAR(30) NULL,
  invoice_no VARCHAR(40) NULL,
  placed_at DATETIME NULL,
  delivered_at DATETIME NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_order_buyer FOREIGN KEY (buyer_id)
    REFERENCES user_account(user_id) ON DELETE RESTRICT,
  INDEX idx_order_buyer_status (buyer_id, status, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE order_item (
  order_item_id INT AUTO_INCREMENT PRIMARY KEY,
  order_id INT NOT NULL,
  product_id INT NOT NULL,
  quantity INT NOT NULL,
  unit_price_bdt DECIMAL(12,2) NOT NULL,
  product_title_snapshot VARCHAR(200) NULL,
  product_image_snapshot VARCHAR(255) NULL,
  artisan_name_snapshot VARCHAR(120) NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_oi_order FOREIGN KEY (order_id)
    REFERENCES `order`(order_id) ON DELETE CASCADE,
  CONSTRAINT fk_oi_product FOREIGN KEY (product_id)
    REFERENCES product(product_id) ON DELETE RESTRICT,
  INDEX idx_oi_order (order_id),
  INDEX idx_oi_product (product_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE coupon_redemption (
  redemption_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  coupon_id INT NOT NULL,
  buyer_id INT NOT NULL,
  order_id INT NULL,
  discount_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
  redeemed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_coupon_redemption_coupon (coupon_id, redeemed_at),
  INDEX idx_coupon_redemption_buyer (buyer_id, redeemed_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE buyer_point_ledger (
  ledger_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  buyer_id INT NOT NULL,
  order_id INT NULL,
  points_delta INT NOT NULL DEFAULT 0,
  reason VARCHAR(40) NOT NULL DEFAULT 'purchase',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_point_buyer (buyer_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE order_status_history (
  history_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  order_id INT NOT NULL,
  status VARCHAR(40) NOT NULL,
  note VARCHAR(255) NULL,
  actor_type VARCHAR(20) NOT NULL DEFAULT 'system',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_order_status_history (order_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE order_provenance_event (
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE buyer_campaign (
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
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE seller_verification_doc (
  seller_id INT NOT NULL,
  doc_type VARCHAR(40) NOT NULL,
  file_path VARCHAR(500) NOT NULL,
  uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (seller_id, doc_type),
  CONSTRAINT fk_svd_seller FOREIGN KEY (seller_id)
    REFERENCES seller_profile(seller_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE seller_wallet (
  seller_id INT PRIMARY KEY,
  available_balance DECIMAL(12,2) NOT NULL DEFAULT 0,
  pending_balance DECIMAL(12,2) NOT NULL DEFAULT 0,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_sw_seller FOREIGN KEY (seller_id)
    REFERENCES seller_profile(seller_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE seller_payout_method (
  method_id INT AUTO_INCREMENT PRIMARY KEY,
  seller_id INT NOT NULL,
  provider VARCHAR(60) NOT NULL,
  account_number VARCHAR(80) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_spm_seller FOREIGN KEY (seller_id)
    REFERENCES seller_profile(seller_id) ON DELETE CASCADE,
  INDEX idx_spm_seller (seller_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE seller_transaction (
  trx_id INT AUTO_INCREMENT PRIMARY KEY,
  seller_id INT NOT NULL,
  type ENUM('cash_in','withdraw') NOT NULL,
  method VARCHAR(120) NOT NULL,
  amount DECIMAL(12,2) NOT NULL,
  status ENUM('pending','paid','rejected') NOT NULL DEFAULT 'pending',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_st_seller FOREIGN KEY (seller_id)
    REFERENCES seller_profile(seller_id) ON DELETE CASCADE,
  INDEX idx_st_seller (seller_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE seller_gi_application (
  app_id INT AUTO_INCREMENT PRIMARY KEY,
  seller_id INT NOT NULL,
  product_id INT NULL,
  product_name VARCHAR(180) NOT NULL,
  category VARCHAR(120) NULL,
  details TEXT NULL,
  certificate_path VARCHAR(500) NULL,
  status ENUM('pending','verified','rejected') NOT NULL DEFAULT 'pending',
  feedback VARCHAR(500) NULL,
  submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_sga_seller FOREIGN KEY (seller_id)
    REFERENCES seller_profile(seller_id) ON DELETE CASCADE,
  CONSTRAINT fk_sga_product FOREIGN KEY (product_id)
    REFERENCES product(product_id) ON DELETE SET NULL,
  INDEX idx_sga_seller_status (seller_id, status, submitted_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE seller_support_message (
  msg_id INT AUTO_INCREMENT PRIMARY KEY,
  seller_id INT NOT NULL,
  channel ENUM('admin','b2b') NOT NULL DEFAULT 'admin',
  sender ENUM('seller','other') NOT NULL DEFAULT 'seller',
  body TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  is_read BOOLEAN NOT NULL DEFAULT FALSE,
  CONSTRAINT fk_ssm_seller FOREIGN KEY (seller_id)
    REFERENCES seller_profile(seller_id) ON DELETE CASCADE,
  INDEX idx_ssm_seller (seller_id, channel, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE chat_thread (
  thread_id INT AUTO_INCREMENT PRIMARY KEY,
  buyer_id INT NOT NULL,
  artisan_id INT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  last_message_at TIMESTAMP NULL,
  CONSTRAINT fk_chat_thread_buyer FOREIGN KEY (buyer_id)
    REFERENCES user_account(user_id) ON DELETE CASCADE,
  CONSTRAINT fk_chat_thread_artisan FOREIGN KEY (artisan_id)
    REFERENCES artisan(artisan_id) ON DELETE CASCADE,
  UNIQUE KEY uq_thread_pair (buyer_id, artisan_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE chat_message (
  message_id INT AUTO_INCREMENT PRIMARY KEY,
  thread_id INT NOT NULL,
  sender_role ENUM('buyer','artisan') NOT NULL,
  sender_id INT NOT NULL,
  body TEXT NOT NULL,
  is_read BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_chat_message_thread FOREIGN KEY (thread_id)
    REFERENCES chat_thread(thread_id) ON DELETE CASCADE,
  INDEX idx_thread_time (thread_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE ob_id_sequence (
  type_code VARCHAR(16) NOT NULL,
  yymm CHAR(4) NOT NULL,
  last_seq INT NOT NULL,
  PRIMARY KEY (type_code, yymm)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE system_setting (
  setting_key VARCHAR(64) PRIMARY KEY,
  setting_value TEXT NULL,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE audit_log (
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE payout_request (
  payout_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  trx_id VARCHAR(40) NOT NULL,
  seller_user_id INT NULL,
  shop_name VARCHAR(160) NULL,
  shop_email VARCHAR(160) NULL,
  amount_bdt DECIMAL(12,2) NOT NULL DEFAULT 0.00,
  destination_type VARCHAR(60) NULL,
  destination_value VARCHAR(160) NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'Pending',
  notes TEXT NULL,
  requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  processed_at TIMESTAMP NULL,
  processed_by INT NULL,
  INDEX idx_payout_status (status, requested_at),
  INDEX idx_payout_seller (seller_user_id, requested_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE backup_log (
  backup_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  finished_at TIMESTAMP NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'RUNNING',
  file_path VARCHAR(255) NULL,
  details_json TEXT NULL,
  created_by INT NULL,
  INDEX idx_backup_time (started_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE access_block (
  block_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  block_type VARCHAR(10) NOT NULL,
  block_value VARCHAR(120) NOT NULL,
  reason VARCHAR(255) NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  created_by INT NULL,
  INDEX idx_block_active (is_active, block_type, block_value)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE report_export (
  report_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  report_code CHAR(32) NOT NULL UNIQUE,
  format VARCHAR(10) NOT NULL,
  file_path VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  created_by INT NULL,
  meta_json TEXT NULL,
  INDEX idx_report_time (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE email_template (
  template_key VARCHAR(64) PRIMARY KEY,
  subject_override VARCHAR(160) NULL,
  html_override MEDIUMTEXT NULL,
  text_override MEDIUMTEXT NULL,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE action_approval (
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE security_event (
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE notification (
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE admin_permission (
  admin_id INT NOT NULL,
  module_key VARCHAR(60) NOT NULL,
  can_view TINYINT(1) NOT NULL DEFAULT 1,
  can_edit TINYINT(1) NOT NULL DEFAULT 0,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (admin_id, module_key),
  CONSTRAINT fk_perm_admin FOREIGN KEY (admin_id)
    REFERENCES user_account(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Optional table: app.py already handles absence gracefully, but adding it keeps buyer dashboard fully DB-backed.
CREATE TABLE buyer_vault_tag (
  buyer_id INT NOT NULL,
  tag_id BIGINT NOT NULL,
  saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (buyer_id, tag_id),
  CONSTRAINT fk_bvt_buyer FOREIGN KEY (buyer_id)
    REFERENCES user_account(user_id) ON DELETE CASCADE,
  CONSTRAINT fk_bvt_tag FOREIGN KEY (tag_id)
    REFERENCES gi_tag(tag_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO system_setting (setting_key, setting_value) VALUES
('maintenance_mode', '0'),
('debug_mode', '0'),
('ai_provider', 'openai'),
('db_capacity_mb', '1024'),
('smtp_host', ''),
('smtp_port', ''),
('smtp_username', ''),
('smtp_password', ''),
('smtp_use_tls', '1'),
('smtp_from_email', ''),
('smtp_from_name', 'Origins Bangladesh'),
('email_brand_name', 'Origins Bangladesh'),
('email_brand_tagline', 'Heritage • Craft • Trust'),
('email_logo_url', '/static/assets/img/placeholder.jpg');


ALTER TABLE admin_profile ADD COLUMN avatar_url VARCHAR(500) NULL AFTER designation;
ALTER TABLE admin_profile ADD COLUMN updated_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP AFTER created_at;

CREATE TABLE admin_team_member (
  team_id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  email VARCHAR(180) NOT NULL UNIQUE,
  role VARCHAR(80) NOT NULL DEFAULT 'Editor',
  article_count INT NOT NULL DEFAULT 0,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  created_by INT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE admin_coupon (
  coupon_id INT AUTO_INCREMENT PRIMARY KEY,
  code VARCHAR(64) NOT NULL UNIQUE,
  discount_type ENUM('Percentage','Fixed Amount','Free Delivery') NOT NULL DEFAULT 'Percentage',
  discount_value DECIMAL(12,2) NOT NULL DEFAULT 0,
  usage_limit INT NULL,
  used_count INT NOT NULL DEFAULT 0,
  expires_at DATE NULL,
  is_new_user_only BOOLEAN NOT NULL DEFAULT FALSE,
  minimum_subtotal_bdt DECIMAL(12,2) NULL,
  maximum_discount_bdt DECIMAL(12,2) NULL,
  starts_at DATETIME NULL,
  per_user_limit INT NULL,
  applicable_scope VARCHAR(20) NOT NULL DEFAULT 'all',
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  created_by INT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE admin_qc_item (
  qc_id INT AUTO_INCREMENT PRIMARY KEY,
  product_id INT NOT NULL,
  seller_id INT NULL,
  status ENUM('Pending','Approved','Rejected','Changes Requested') NOT NULL DEFAULT 'Pending',
  note TEXT NULL,
  reviewed_by INT NULL,
  reviewed_at TIMESTAMP NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_qc_product (product_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE admin_dispute (
  dispute_id INT AUTO_INCREMENT PRIMARY KEY,
  order_id INT NULL,
  issue TEXT NOT NULL,
  priority ENUM('Low','Medium','High') NOT NULL DEFAULT 'Medium',
  status ENUM('Open','Refunded','Dismissed') NOT NULL DEFAULT 'Open',
  resolution_note TEXT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  resolved_at TIMESTAMP NULL,
  resolved_by INT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE admin_commission_rule (
  rule_id INT AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(120) NOT NULL DEFAULT 'Default Platform Commission',
  percentage DECIMAL(5,2) NOT NULL DEFAULT 10.00,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  updated_by INT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE admin_message_thread (
  thread_id INT AUTO_INCREMENT PRIMARY KEY,
  seller_id INT NOT NULL,
  subject VARCHAR(180) NOT NULL,
  last_message TEXT NULL,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE admin_message (
  message_id INT AUTO_INCREMENT PRIMARY KEY,
  thread_id INT NOT NULL,
  sender_role ENUM('admin','seller') NOT NULL,
  body TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
