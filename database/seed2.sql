USE origins_bangladesh;

INSERT INTO system_setting (setting_key, setting_value)
VALUES
('home_hero_image', '/static/assets/img/hero.png'),
('flash_sale_enabled', '1')
ON DUPLICATE KEY UPDATE
setting_value = VALUES(setting_value);

UPDATE product
SET
    is_flash_sale = 1,
    flash_discount = CASE
        WHEN product_id = 1 THEN 25
        WHEN product_id = 2 THEN 15
        WHEN product_id = 3 THEN 20
        WHEN product_id = 4 THEN 30
        WHEN product_id = 5 THEN 18
        ELSE 10
    END,
    is_active = 1
WHERE product_id IN (1,2,3,4,5);