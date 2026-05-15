USE origins_bangladesh;

-- =========================================================
-- USERS
-- =========================================================
INSERT INTO user_account
(user_id, role, name, email, phone, password_hash, secret_code_hash, is_email_verified, is_active)
VALUES
(1, 'superadmin', 'System Super Admin', 'compilebreakers@gmail.com', '8801700000001', 'pbkdf2:sha256:600000$VZFLVGeP$19a1c6d59ac7599b17ccfb6f5726d6204d0fdabc56fab6b6395649da1521da97', 'pbkdf2:sha256:600000$VZFLVGeP$19a1c6d59ac7599b17ccfb6f5726d6204d0fdabc56fab6b6395649da1521da97', 1, 1),
(2, 'admin', 'Admin', 'mrtarikulislamtarek69@gmail.com', '8801700000002', 'pbkdf2:sha256:600000$VZFLVGeP$19a1c6d59ac7599b17ccfb6f5726d6204d0fdabc56fab6b6395649da1521da97', 'pbkdf2:sha256:600000$VZFLVGeP$19a1c6d59ac7599b17ccfb6f5726d6204d0fdabc56fab6b6395649da1521da97', 1, 1),
(3, 'buyer', 'Anis', 'mdanisahmed283@gmail.com', '8801700000003', 'pbkdf2:sha256:600000$VZFLVGeP$19a1c6d59ac7599b17ccfb6f5726d6204d0fdabc56fab6b6395649da1521da97', 'pbkdf2:sha256:600000$VZFLVGeP$19a1c6d59ac7599b17ccfb6f5726d6204d0fdabc56fab6b6395649da1521da97', 1, 1),
(4, 'seller', 'Tarikul', 'titarek2211@gmail.com', '8801700000004', 'pbkdf2:sha256:600000$VZFLVGeP$19a1c6d59ac7599b17ccfb6f5726d6204d0fdabc56fab6b6395649da1521da97', 'pbkdf2:sha256:600000$VZFLVGeP$19a1c6d59ac7599b17ccfb6f5726d6204d0fdabc56fab6b6395649da1521da97', 1, 1),
(5, 'seller', 'Konok', 'konok@gmail.com', '8801700000005', 'pbkdf2:sha256:600000$VZFLVGeP$19a1c6d59ac7599b17ccfb6f5726d6204d0fdabc56fab6b6395649da1521da97', 'pbkdf2:sha256:600000$VZFLVGeP$19a1c6d59ac7599b17ccfb6f5726d6204d0fdabc56fab6b6395649da1521da97', 1, 1),
(6, 'buyer', 'Ankan', 'ankan@gmail.com', '8801700000006', 'pbkdf2:sha256:600000$VZFLVGeP$19a1c6d59ac7599b17ccfb6f5726d6204d0fdabc56fab6b6395649da1521da97', 'pbkdf2:sha256:600000$VZFLVGeP$19a1c6d59ac7599b17ccfb6f5726d6204d0fdabc56fab6b6395649da1521da97', 1, 1);

-- =========================================================
-- PROFILES
-- =========================================================
INSERT INTO admin_profile (admin_id, designation)
VALUES
(1, 'Platform Super Administrator'),
(2, 'Operations Administrator');

INSERT INTO buyer_profile (buyer_id, address, bio, avatar_url, points, guardian_id)
VALUES
(3, 'Gazipur, Bangladesh', 'Loves handmade heritage products and verified crafts.', '/static/assets/img/boy.png', 120, 'OB-0003'),
(6, 'Dhaka, Bangladesh', 'Collector of rare handcrafted and GI-inspired items.', '/static/assets/img/boy.png', 80, 'OB-0006');

INSERT INTO seller_profile
(seller_id, shop_name, owner_name, location, category, story, avatar_url, is_verified, verification_status, reviewed_by, reviewed_at, rejection_reason)
VALUES
(4, 'Artisan Shop', 'Tarik', 'Kaliganj, Gazipur', 'Textiles', 'A growing seller profile used for login, verification and dashboard testing.', '/static/assets/img/images.jpg', 0, 'under_review', 2, NOW(), NULL),
(5, 'Sonar Bangla Crafts', 'Rahim Uddin', 'Narayanganj', 'Jamdani & Heritage Crafts', 'A verified shop selling GI-inspired heritage products and featured artisan collections.', '/static/assets/img/images.jpg', 1, 'approved', 2, NOW(), NULL);

-- =========================================================
-- AUTH / SECURITY
-- =========================================================
INSERT INTO trusted_device
(device_id, user_id, device_hash, revoke_hash, label, ip, user_agent, created_at, last_seen_at, expires_at, revoked_at)
VALUES
(1, 2, REPEAT('a',64), REPEAT('b',64), 'Admin Chrome on Windows', '127.0.0.1', 'Mozilla/5.0 Admin', NOW(), NOW(), DATE_ADD(NOW(), INTERVAL 180 DAY), NULL),
(2, 4, REPEAT('c',64), REPEAT('d',64), 'Seller Laptop', '127.0.0.1', 'Mozilla/5.0 Seller', NOW(), NOW(), DATE_ADD(NOW(), INTERVAL 180 DAY), NULL);

INSERT INTO auth_token
(token_id, email, user_id, purpose, code_hash, token_hash, salt, expires_at, consumed_at)
VALUES
(1, 'mrtarikulislamtarek69@gmail.com', 2, 'admin_login', REPEAT('1',64), REPEAT('2',64), 'saltadmin0000001', DATE_ADD(NOW(), INTERVAL 10 MINUTE), NOW()),
(2, 'titarek2211@gmail.com', 4, 'login', REPEAT('3',64), REPEAT('4',64), 'saltseller000001', DATE_ADD(NOW(), INTERVAL 10 MINUTE), NOW()),
(3, 'compilebreakers@gmail.com', 1, 'superadmin_login', REPEAT('5',64), REPEAT('6',64), 'saltsuper0000001', DATE_ADD(NOW(), INTERVAL 10 MINUTE), NOW());

INSERT INTO action_approval
(approval_id, actor_user_id, action_key, target_user_id, code_hash, salt, expires_at, consumed_at)
VALUES
(1, 2, 'approve_seller_verification', 4, REPEAT('7',64), 'approve000000001', DATE_ADD(NOW(), INTERVAL 1 DAY), NULL);

INSERT INTO security_event
(event_id, event_type, severity, actor_email, ip, user_agent, message, meta_json)
VALUES
(1, 'login_success', 'info', 'mrtarikulislamtarek69@gmail.com', '127.0.0.1', 'Mozilla/5.0 Admin', 'Admin completed secure login.', '{"role":"admin"}'),
(2, 'login_success', 'info', 'titarek2211@gmail.com', '127.0.0.1', 'Mozilla/5.0 Seller', 'Seller completed secure login.', '{"role":"seller"}');

-- =========================================================
-- MASTER DATA
-- =========================================================
INSERT INTO currency_rate (code, rate_to_bdt)
VALUES
('BDT', 1.000000),
('USD', 121.500000),
('EUR', 132.750000),
('GBP', 154.900000);

INSERT INTO category (category_id, name)
VALUES
(1, 'Textiles'),
(2, 'Pottery'),
(3, 'Wood Crafts'),
(4, 'Jute & Natural Fibers');

INSERT INTO subcategory (subcategory_id, category_id, name)
VALUES
(1, 1, 'Jamdani'),
(2, 1, 'Nakshi Kantha'),
(3, 2, 'Decorative Pottery'),
(4, 3, 'Carved Home Decor'),
(5, 4, 'Jute Lifestyle');

INSERT INTO district (district_id, name)
VALUES
(1, 'Bagerhat'),
(2, 'Bandarban'),
(3, 'Barguna'),
(4, 'Barishal'),
(5, 'Bhola'),
(6, 'Bogura'),
(7, 'Brahmanbaria'),
(8, 'Chandpur'),
(9, 'Chapainawabganj'),
(10, 'Chattogram'),
(11, 'Chuadanga'),
(12, 'Cox''s Bazar'),
(13, 'Cumilla'),
(14, 'Dhaka'),
(15, 'Dinajpur'),
(16, 'Faridpur'),
(17, 'Feni'),
(18, 'Gaibandha'),
(19, 'Gazipur'),
(20, 'Gopalganj'),
(21, 'Habiganj'),
(22, 'Jamalpur'),
(23, 'Jashore'),
(24, 'Jhalokathi'),
(25, 'Jhenaidah'),
(26, 'Joypurhat'),
(27, 'Khagrachhari'),
(28, 'Khulna'),
(29, 'Kishoreganj'),
(30, 'Kurigram'),
(31, 'Kushtia'),
(32, 'Lakshmipur'),
(33, 'Lalmonirhat'),
(34, 'Madaripur'),
(35, 'Magura'),
(36, 'Manikganj'),
(37, 'Meherpur'),
(38, 'Moulvibazar'),
(39, 'Munshiganj'),
(40, 'Mymensingh'),
(41, 'Naogaon'),
(42, 'Narail'),
(43, 'Narayanganj'),
(44, 'Narsingdi'),
(45, 'Natore'),
(46, 'Netrokona'),
(47, 'Nilphamari'),
(48, 'Noakhali'),
(49, 'Pabna'),
(50, 'Panchagarh'),
(51, 'Patuakhali'),
(52, 'Pirojpur'),
(53, 'Rajbari'),
(54, 'Rajshahi'),
(55, 'Rangamati'),
(56, 'Rangpur'),
(57, 'Satkhira'),
(58, 'Shariatpur'),
(59, 'Sherpur'),
(60, 'Sirajganj'),
(61, 'Sunamganj'),
(62, 'Sylhet'),
(63, 'Tangail'),
(64, 'Thakurgaon');

INSERT INTO district_atlas
(atlas_id, district_id, density, product_name, category, story, image_url, shop_link, dot_x, dot_y, is_active)
VALUES
(1, 1, 'high', 'Jamdani Saree', 'Textiles', 'Narayanganj is widely associated with Jamdani weaving heritage.', '/static/assets/img/placeholder.jpg', '/atlas/narayanganj', 54.20, 32.10, 1),
(2, 2, 'med', 'Khadi Fabric', 'Textiles', 'Cumilla continues to inspire handloom revival and local pride.', '/static/assets/img/placeholder.jpg', '/atlas/cumilla', 61.40, 39.80, 1),
(3, 3, 'med', 'Nakshi Kantha', 'Textiles', 'Rajshahi folklore and stitch storytelling remain iconic.', '/static/assets/img/placeholder.jpg', '/atlas/rajshahi', 26.50, 28.10, 1),
(4, 5, 'low', 'Emerging Heritage Crafts', 'Mixed', 'Gazipur showcases evolving artisan entrepreneurship.', '/static/assets/img/placeholder.jpg', '/atlas/gazipur', 57.90, 25.30, 1);

-- =========================================================
-- ARTISANS / STORIES / MEDIA
-- =========================================================
INSERT INTO artisan
(artisan_id, name, specialty_title, location_text, badge_text, hero_image, tag, quote_text, started_year, years_mastery, pieces_created, is_featured, is_active)
VALUES
(1, 'Amena Khatun', 'Jamdani Weaver', 'Narayanganj, Bangladesh', 'Master Weaver', '/static/assets/img/images.jpg', 'Jamdani', 'Every thread carries memory.', 2003, 22, 860, 1, 1),
(2, 'Harun Mia', 'Pottery Artist', 'Rajshahi, Bangladesh', 'Clay Heritage', '/static/assets/img/images.jpg', 'Pottery', 'Clay remembers the hand that shaped it.', 2008, 17, 430, 0, 1);

INSERT INTO artisan_story
(story_id, artisan_id, headline, video_url, body, is_active, published_at)
VALUES
(1, 1, 'How Jamdani survives through patience and practice', 'https://example.com/jamdani-story', 'A long-form narrative about heritage weaving, intergenerational skill and ethical craft commerce.', 1, NOW()),
(2, 2, 'Clay, kiln and memory', 'https://example.com/pottery-story', 'A short feature on balancing rural craft identity with modern marketplace demand.', 1, NOW());

INSERT INTO soundscape_track
(track_id, title, subtitle, duration_sec, audio_url, cover_image_url, craft_tag, district_id, is_featured, sort_order, is_active)
VALUES
(1, 'Amar Sonar Bangla', 'National Anthem of Bangladesh', 269, '/static/audio/bd.mp3', '/static/assets/img/bd.jpg', 'National Heritage', 1, 1, 1, 1);

INSERT INTO gi_journal_article
(article_id, slug, title, subtitle, category, read_minutes, hero_image_url, thumb_image_url, teaser, content_html, is_featured, quote_text, quote_author, published_at)
VALUES
(1, 'jamdani-woven-by-the-river', 'Jamdani: Woven by the River''s Edge', 'How the Shitalakhya River Shaped a Geographical Indication', 'Heritage Journal', 6, '/static/assets/img/book1.jpg', '/static/assets/img/book1.jpg', 'Discover the profound connection between Bengal''s riverine ecosystem and the intricate, breathable cotton weaves of authentic Jamdani.', '<p>For centuries, the banks of the Shitalakhya river have nurtured the artisans of Jamdani. The unique humidity and mineral-rich water have not only shaped the fine cotton but also the very soul of this Geographical Indication (GI) craft.</p><p>Every motif woven into the fabric tells a timeless story of monsoon rains, local flora, and the rhythmic clatter of the traditional loom.</p>', 1, 'The finest Jamdani is not just woven with cotton, but with the mist of the river and the breath of the artisan.', 'Editorial Desk', NOW()),
(2, 'building-trust-artisan-economy', 'Building Trust in the Artisan Economy', 'The Architecture of Authenticity for GI Crafts', 'Marketplace', 5, '/static/assets/img/book2.jpg', '/static/assets/img/book2.jpg', 'In a digital marketplace, how do traditional artisans convey the authenticity of their craft? Learn the pillars of verification, storytelling, and buyer trust.', '<p>Transitioning from local bazaars to global digital marketplaces requires more than just listing a product. For GI craft artisans, building buyer trust is paramount.</p><p>Through transparent verification processes, rich storytelling, and consistent quality, new sellers can forge meaningful, long-lasting connections with conscious consumers worldwide.</p>', 0, 'Trust is the invisible thread that binds the artisan''s loom to the buyer''s heart.', 'Marketplace Insights', NOW());

-- =========================================================
-- PRODUCTS / GI / ARTISAN MAP
-- =========================================================
INSERT INTO product
(product_id, seller_id, title, description, price_bdt, stock, category_id, subcategory_id, district_id, gi_tag, image_path, is_flash_sale, flash_discount, discovery_score, is_active)
VALUES
(1, 5, 'Handwoven Jamdani Saree', 'Verified heritage-inspired saree with premium handwoven motifs.', 8500.00, 12, 1, 1, 1, 'GI-JAM-0001', '/static/assets/img/js.jpg', 1, 10, 92.4500, 1),
(2, 5, 'Nakshi Kantha Throw', 'Decorative embroidered throw inspired by folk storytelling patterns.', 4200.00, 8, 1, 2, 3, 'GI-NK-0002', '/static/assets/img/nk.jpg', 0, NULL, 87.2300, 1),
(3, 4, 'Khadi Panjabi', 'Seller verification test product for locked seller flows.', 2500.00, 5, 1, 1, 2, NULL, '/static/assets/img/kp.jpg', 0, NULL, 71.0000, 1),
(4, 5, 'Terracotta Vase', 'Decorative handcrafted clay vase suitable for modern interiors.', 1800.00, 15, 2, 3, 3, NULL, '/static/assets/img/tv.jpg', 0, NULL, 66.5000, 1),
(5, 5, 'Jute Storage Basket', 'Natural fiber storage basket with heritage-inspired weaving.', 1200.00, 20, 4, 5, 4, NULL, '/static/assets/img/jsb.jpg', 1, 15, 61.4000, 1);

INSERT INTO artisan_product (artisan_id, product_id)
VALUES
(1, 1),
(1, 2),
(2, 4);

INSERT INTO gi_tag
(tag_id, tag_code, product_id, issued_to_artisan_id, status, issued_at, first_verified_at, last_verified_at, verify_count, last_verified_ip, last_verified_user_agent, note)
VALUES
(1, 'OBGI-JAM-000001', 1, 1, 'active', NOW(), NOW(), NOW(), 5, '127.0.0.1', 'Mozilla/5.0', 'Seeded active GI tag for verification demos.'),
(2, 'OBGI-NKS-000002', 2, 1, 'active', NOW(), NOW(), NOW(), 2, '127.0.0.1', 'Mozilla/5.0', 'Seeded active GI tag for buyer vault.'),
(3, 'OBGI-OLD-000003', 4, 2, 'revoked', NOW(), NOW(), NOW(), 1, '127.0.0.1', 'Mozilla/5.0', 'Revoked sample tag for negative testing.');

INSERT INTO gi_tag_verification_log
(log_id, tag_id, attempted_code, result, ip, user_agent, created_at)
VALUES
(1, 1, 'OBGI-JAM-000001', 'verified', '127.0.0.1', 'Mozilla/5.0', NOW()),
(2, 3, 'OBGI-OLD-000003', 'revoked', '127.0.0.1', 'Mozilla/5.0', NOW()),
(3, NULL, 'OBGI-FAKE-999999', 'not_found', '127.0.0.1', 'Mozilla/5.0', NOW());

INSERT INTO buyer_vault_tag (buyer_id, tag_id)
VALUES
(3, 1),
(3, 2),
(6, 2);

-- =========================================================
-- BUYER WISHLIST / CART
-- =========================================================
INSERT INTO wishlist (wishlist_id, buyer_id, product_id, created_at)
VALUES
(1, 3, 1, NOW()),
(2, 3, 4, NOW()),
(3, 6, 2, NOW());

INSERT INTO cart (cart_id, buyer_id, created_at)
VALUES
(1, 3, NOW()),
(2, 6, NOW());

INSERT INTO cart_item (cart_item_id, cart_id, product_id, quantity, created_at)
VALUES
(1, 1, 1, 1, NOW()),
(2, 1, 5, 2, NOW()),
(3, 2, 2, 1, NOW());

-- =========================================================
-- ORDERS
-- =========================================================
INSERT INTO `order` (order_id, buyer_id, status, total_bdt, created_at)
VALUES
(1, 3, 'delivered', 8500.00, DATE_SUB(NOW(), INTERVAL 20 DAY)),
(2, 3, 'shipped', 5400.00, DATE_SUB(NOW(), INTERVAL 5 DAY)),
(3, 6, 'paid', 1800.00, DATE_SUB(NOW(), INTERVAL 2 DAY)),
(4, 3, 'pending', 2500.00, DATE_SUB(NOW(), INTERVAL 1 DAY));

INSERT INTO order_item (order_item_id, order_id, product_id, quantity, unit_price_bdt, created_at)
VALUES
(1, 1, 1, 1, 8500.00, DATE_SUB(NOW(), INTERVAL 20 DAY)),
(2, 2, 2, 1, 4200.00, DATE_SUB(NOW(), INTERVAL 5 DAY)),
(3, 2, 5, 1, 1200.00, DATE_SUB(NOW(), INTERVAL 5 DAY)),
(4, 3, 4, 1, 1800.00, DATE_SUB(NOW(), INTERVAL 2 DAY)),
(5, 4, 3, 1, 2500.00, DATE_SUB(NOW(), INTERVAL 1 DAY));

-- =========================================================
-- SELLER VERIFICATION / WALLET / PAYOUT / GI APP / SUPPORT
-- =========================================================
INSERT INTO seller_verification_doc (seller_id, doc_type, file_path, uploaded_at)
VALUES
(4, 'nid_front', '/uploads/verification/seller4_nid_front.jpg', NOW()),
(4, 'nid_back', '/uploads/verification/seller4_nid_back.jpg', NOW()),
(4, 'trade_license', '/uploads/verification/seller4_trade_license.pdf', NOW()),
(5, 'nid_front', '/uploads/verification/seller5_nid_front.jpg', NOW());

INSERT INTO seller_wallet (seller_id, available_balance, pending_balance)
VALUES
(4, 0.00, 2500.00),
(5, 6700.00, 3000.00);

INSERT INTO seller_payout_method (method_id, seller_id, provider, account_number, created_at)
VALUES
(1, 4, 'bKash', '01700000004', NOW()),
(2, 5, 'Bank', '123456789012', NOW());

INSERT INTO seller_transaction (trx_id, seller_id, type, method, amount, status, created_at)
VALUES
(1, 5, 'cash_in', 'order_settlement', 8500.00, 'paid', DATE_SUB(NOW(), INTERVAL 20 DAY)),
(2, 5, 'withdraw', 'Bank', 3000.00, 'pending', DATE_SUB(NOW(), INTERVAL 1 DAY)),
(3, 4, 'cash_in', 'order_pending_release', 2500.00, 'pending', DATE_SUB(NOW(), INTERVAL 1 DAY));

INSERT INTO payout_request
(payout_id, trx_id, seller_user_id, shop_name, shop_email, amount_bdt, destination_type, destination_value, status, notes, requested_at, processed_at, processed_by)
VALUES
(1, 'PO-202603-0001', 5, 'Sonar Bangla Crafts', 'seller2@origins.local', 3000.00, 'bank', '123456789012', 'Pending', 'Awaiting finance review.', DATE_SUB(NOW(), INTERVAL 1 DAY), NULL, NULL),
(2, 'PO-202603-0002', 5, 'Sonar Bangla Crafts', 'seller2@origins.local', 1800.00, 'bkash', '01700000005', 'Approved', 'Processed by admin.', DATE_SUB(NOW(), INTERVAL 10 DAY), DATE_SUB(NOW(), INTERVAL 8 DAY), 2);

INSERT INTO seller_gi_application
(app_id, seller_id, product_id, product_name, category, details, certificate_path, status, feedback, submitted_at, updated_at)
VALUES
(1, 4, 3, 'Khadi Panjabi', 'Textiles', 'Seller requested GI-linked review for source authenticity.', '/uploads/gi_apps/khadi_panjabi.pdf', 'pending', NULL, DATE_SUB(NOW(), INTERVAL 3 DAY), DATE_SUB(NOW(), INTERVAL 3 DAY)),
(2, 5, 1, 'Handwoven Jamdani Saree', 'Textiles', 'Legacy certificate verification for premium listing.', '/uploads/gi_apps/jamdani_certificate.pdf', 'verified', 'Approved after document review.', DATE_SUB(NOW(), INTERVAL 15 DAY), DATE_SUB(NOW(), INTERVAL 12 DAY));

INSERT INTO seller_support_message
(msg_id, seller_id, channel, sender, body, created_at, is_read)
VALUES
(1, 4, 'admin', 'seller', 'I have submitted my documents. Please review them.', DATE_SUB(NOW(), INTERVAL 2 DAY), 0),
(2, 4, 'admin', 'other', 'Your verification is under review by the admin team.', DATE_SUB(NOW(), INTERVAL 1 DAY), 1),
(3, 5, 'b2b', 'seller', 'Interested in a corporate gifting partnership.', DATE_SUB(NOW(), INTERVAL 4 DAY), 0);

-- =========================================================
-- CHAT
-- =========================================================
INSERT INTO chat_thread (thread_id, buyer_id, artisan_id, created_at, last_message_at)
VALUES
(1, 3, 1, DATE_SUB(NOW(), INTERVAL 6 DAY), DATE_SUB(NOW(), INTERVAL 1 DAY)),
(2, 6, 2, DATE_SUB(NOW(), INTERVAL 4 DAY), DATE_SUB(NOW(), INTERVAL 2 DAY));

INSERT INTO chat_message (message_id, thread_id, sender_role, sender_id, body, is_read, created_at)
VALUES
(1, 1, 'buyer', 3, 'Can this Jamdani piece be customized?', 1, DATE_SUB(NOW(), INTERVAL 6 DAY)),
(2, 1, 'artisan', 1, 'Yes, custom color accents are possible on request.', 1, DATE_SUB(NOW(), INTERVAL 6 DAY)),
(3, 1, 'buyer', 3, 'Great, I will place the order this week.', 0, DATE_SUB(NOW(), INTERVAL 1 DAY)),
(4, 2, 'buyer', 6, 'Is the terracotta vase kiln-fired twice?', 1, DATE_SUB(NOW(), INTERVAL 4 DAY)),
(5, 2, 'artisan', 2, 'Yes, it is double-fired for durability.', 0, DATE_SUB(NOW(), INTERVAL 2 DAY));

-- =========================================================
-- SYSTEM / SETTINGS / EMAIL / LOGS / NOTIFICATIONS
-- =========================================================
INSERT INTO ob_id_sequence (type_code, yymm, last_seq)
VALUES
('PO', DATE_FORMAT(NOW(), '%y%m'), 2),
('GI', DATE_FORMAT(NOW(), '%y%m'), 2);

INSERT INTO system_setting (setting_key, setting_value)
VALUES
('site_name', 'Origins Bangladesh'),
('site_tagline', 'Heritage • Craft • Trust'),
('default_currency', 'BDT'),
('platform_fee_percent', '5'),
('support_email', 'support@origins.local'),
('support_phone', '+8801700000099'),
('admin_notice', 'Seeded environment for dashboard and verification testing.'),
('featured_artisan_id', '1'),
('featured_story_id', '1'),
('hero_journal_slug', 'jamdani-river-heritage')
ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value);

INSERT INTO email_template (template_key, subject_override, html_override, text_override)
VALUES
('seller_verification_approved', 'Your seller account is approved', '<p>Congratulations. Your seller profile has been approved and unlocked.</p>', 'Congratulations. Your seller profile has been approved and unlocked.'),
('seller_verification_received', 'We received your verification documents', '<p>Your documents are now under review.</p>', 'Your documents are now under review.'),
('admin_login_otp', 'Admin secure login code', '<p>Your secure login code is ready.</p>', 'Your secure login code is ready.');

INSERT INTO notification
(notification_id, recipient_user_id, type, severity, title, body, link, meta_json, is_read, created_at, read_at)
VALUES
(1, 4, 'verification', 'info', 'Documents under review', 'Your seller documents are currently under admin review.', '/seller/dashboard?view=verification', '{"status":"under_review"}', 0, NOW(), NULL),
(2, 2, 'payout', 'warning', 'Pending payout requires review', 'A seller payout request is waiting for action.', '/admin/dashboard', '{"payout_id":1}', 0, NOW(), NULL),
(3, 3, 'order', 'success', 'Your order has been delivered', 'Order #1 was delivered successfully.', '/buyer/dashboard', '{"order_id":1}', 1, DATE_SUB(NOW(), INTERVAL 15 DAY), DATE_SUB(NOW(), INTERVAL 14 DAY));

INSERT INTO audit_log
(audit_id, actor_user_id, action, target_user_id, ip, user_agent, metadata_json, created_at)
VALUES
(1, 2, 'seller_verification_review_started', 4, '127.0.0.1', 'Mozilla/5.0 Admin', '{"seller_id":4}', DATE_SUB(NOW(), INTERVAL 2 DAY)),
(2, 2, 'payout_request_approved', 5, '127.0.0.1', 'Mozilla/5.0 Admin', '{"payout_id":2}', DATE_SUB(NOW(), INTERVAL 8 DAY)),
(3, 1, 'system_setting_updated', NULL, '127.0.0.1', 'Mozilla/5.0 SuperAdmin', '{"setting_key":"platform_fee_percent"}', DATE_SUB(NOW(), INTERVAL 7 DAY));

INSERT INTO admin_permission (admin_id, module_key, can_view, can_edit)
VALUES
(1, 'dashboard', 1, 1),
(1, 'artisans', 1, 1),
(1, 'verification', 1, 1),
(1, 'gi_center', 1, 1),
(1, 'orders', 1, 1),
(1, 'settings', 1, 1),
(2, 'dashboard', 1, 1),
(2, 'artisans', 1, 1),
(2, 'verification', 1, 1),
(2, 'gi_center', 1, 1),
(2, 'orders', 1, 0),
(2, 'settings', 1, 0);

INSERT INTO backup_log (backup_id, started_at, finished_at, status, file_path, details_json, created_by)
VALUES
(1, DATE_SUB(NOW(), INTERVAL 2 DAY), DATE_SUB(NOW(), INTERVAL 2 DAY) + INTERVAL 5 MINUTE, 'SUCCESS', '/exports/backup_seed.sql', '{"size_kb":128}', 1);

INSERT INTO access_block (block_id, block_type, block_value, reason, is_active, created_at, created_by)
VALUES
(1, 'ip', '203.0.113.10', 'Too many failed login attempts', 0, DATE_SUB(NOW(), INTERVAL 30 DAY), 2);

INSERT INTO report_export (report_id, report_code, format, file_path, created_at, created_by, meta_json)
VALUES
(1, 'RPT-SELLER-202603', 'csv', '/exports/reports/seller_metrics_march.csv', DATE_SUB(NOW(), INTERVAL 3 DAY), 2, '{"scope":"seller_dashboard"}');

-- =========================================================
-- FINAL AUTO_INCREMENT SYNC (optional but neat)
-- =========================================================
ALTER TABLE user_account AUTO_INCREMENT = 7;
ALTER TABLE category AUTO_INCREMENT = 5;
ALTER TABLE subcategory AUTO_INCREMENT = 6;
ALTER TABLE district AUTO_INCREMENT = 7;
ALTER TABLE artisan AUTO_INCREMENT = 3;
ALTER TABLE product AUTO_INCREMENT = 6;
ALTER TABLE gi_tag AUTO_INCREMENT = 4;
ALTER TABLE wishlist AUTO_INCREMENT = 4;
ALTER TABLE cart AUTO_INCREMENT = 3;
ALTER TABLE cart_item AUTO_INCREMENT = 4;
ALTER TABLE `order` AUTO_INCREMENT = 5;
ALTER TABLE order_item AUTO_INCREMENT = 6;
ALTER TABLE seller_payout_method AUTO_INCREMENT = 3;
ALTER TABLE seller_transaction AUTO_INCREMENT = 4;
ALTER TABLE seller_gi_application AUTO_INCREMENT = 3;
ALTER TABLE seller_support_message AUTO_INCREMENT = 4;
ALTER TABLE chat_thread AUTO_INCREMENT = 3;
ALTER TABLE chat_message AUTO_INCREMENT = 6;
ALTER TABLE notification AUTO_INCREMENT = 4;
ALTER TABLE audit_log AUTO_INCREMENT = 4;
ALTER TABLE payout_request AUTO_INCREMENT = 3;