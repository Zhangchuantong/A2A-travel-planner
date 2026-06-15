DROP DATABASE IF EXISTS travel_planner;
CREATE DATABASE travel_planner CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE travel_planner;

-- =========================================================
-- 1. 天气数据表
-- =========================================================
DROP TABLE IF EXISTS weather_data;

CREATE TABLE IF NOT EXISTS weather_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    city VARCHAR(50) NOT NULL COMMENT '城市名称',
    fx_date DATE NOT NULL COMMENT '预报日期',
    sunrise TIME COMMENT '日出时间',
    sunset TIME COMMENT '日落时间',
    moonrise TIME COMMENT '月升时间',
    moonset TIME COMMENT '月落时间',
    moon_phase VARCHAR(20) COMMENT '月相名称',
    moon_phase_icon VARCHAR(10) COMMENT '月相图标代码',
    temp_max INT COMMENT '最高温度',
    temp_min INT COMMENT '最低温度',
    icon_day VARCHAR(10) COMMENT '白天天气图标代码',
    text_day VARCHAR(20) COMMENT '白天天气描述',
    icon_night VARCHAR(10) COMMENT '夜间天气图标代码',
    text_night VARCHAR(20) COMMENT '夜间天气描述',
    wind360_day INT COMMENT '白天风向360角度',
    wind_dir_day VARCHAR(20) COMMENT '白天风向',
    wind_scale_day VARCHAR(10) COMMENT '白天风力等级',
    wind_speed_day INT COMMENT '白天风速 (km/h)',
    wind360_night INT COMMENT '夜间风向360角度',
    wind_dir_night VARCHAR(20) COMMENT '夜间风向',
    wind_scale_night VARCHAR(10) COMMENT '夜间风力等级',
    wind_speed_night INT COMMENT '夜间风速 (km/h)',
    precip DECIMAL(5,1) COMMENT '降水量 (mm)',
    uv_index INT COMMENT '紫外线指数',
    humidity INT COMMENT '相对湿度 (%)',
    pressure INT COMMENT '大气压强 (hPa)',
    vis INT COMMENT '能见度 (km)',
    cloud INT COMMENT '云量 (%)',
    update_time DATETIME COMMENT '数据更新时间',
    UNIQUE KEY unique_city_date (city, fx_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='天气数据表';


-- =========================================================
-- 2. 火车票表
-- =========================================================
DROP TABLE IF EXISTS train_tickets;

CREATE TABLE train_tickets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    departure_city VARCHAR(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
    arrival_city VARCHAR(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
    departure_time DATETIME NOT NULL,
    arrival_time DATETIME NOT NULL,
    train_number VARCHAR(20) NOT NULL,
    seat_type VARCHAR(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
    total_seats INT NOT NULL,
    remaining_seats INT NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_train (departure_time, train_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- =========================================================
-- 3. 插入天气测试数据
-- =========================================================
INSERT INTO weather_data
(city, fx_date, sunrise, sunset, moonrise, moonset, moon_phase, moon_phase_icon,
 temp_max, temp_min, icon_day, text_day, icon_night, text_night,
 wind360_day, wind_dir_day, wind_scale_day, wind_speed_day,
 wind360_night, wind_dir_night, wind_scale_night, wind_speed_night,
 precip, uv_index, humidity, pressure, vis, cloud, update_time)
VALUES
('东京', '2026-06-20', '04:25:00', '19:00:00', '10:00:00', '23:30:00', '盈凸月', '803',
 29, 23, '101', '多云', '150', '晴',
 180, '南风', '3-4', 18,
 160, '东南风', '1-3', 10,
 0.5, 6, 65, 1008, 15, 40, '2026-06-19 18:00:00'),

('东京', '2026-06-21', '04:25:00', '19:00:00', '11:00:00', '23:59:00', '盈凸月', '803',
 30, 24, '100', '晴', '151', '多云',
 190, '南风', '3-4', 20,
 170, '东南风', '1-3', 12,
 0.0, 7, 60, 1006, 18, 20, '2026-06-20 18:00:00'),

('富山', '2026-06-20', '04:32:00', '19:12:00', '10:10:00', '23:40:00', '盈凸月', '803',
 25, 20, '305', '小雨', '305', '小雨',
 90, '东风', '1-3', 8,
 80, '东风', '1-3', 7,
 4.5, 3, 82, 1005, 8, 85, '2026-06-19 18:00:00'),

('大阪', '2026-06-20', '04:45:00', '19:15:00', '10:20:00', '23:45:00', '盈凸月', '803',
 31, 24, '100', '晴', '150', '晴',
 200, '西南风', '1-3', 12,
 190, '南风', '1-3', 8,
 0.0, 8, 58, 1007, 20, 10, '2026-06-19 18:00:00');


-- =========================================================
-- 4. 插入火车票测试数据
-- =========================================================
INSERT INTO train_tickets
(departure_city, arrival_city, departure_time, arrival_time, train_number,
 seat_type, total_seats, remaining_seats, price)
VALUES
('富山', '东京', '2026-06-20 09:21:00', '2026-06-20 11:32:00',
 'Kagayaki 508', '普通指定席', 300, 42, 12760.00),

('富山', '东京', '2026-06-20 10:33:00', '2026-06-20 13:00:00',
 'Hakutaka 560', '普通自由席', 300, 86, 12100.00),

('富山', '东京', '2026-06-20 14:21:00', '2026-06-20 16:52:00',
 'Hakutaka 566', '普通自由席', 300, 65, 12100.00),

('东京', '富山', '2026-06-20 16:24:00', '2026-06-20 18:33:00',
 'Kagayaki 509', '普通指定席', 300, 34, 12760.00),

('富山', '大阪', '2026-06-20 08:00:00', '2026-06-20 11:10:00',
 'Tsurugi + Thunderbird', '普通指定席', 280, 58, 9500.00);


-- =========================================================
-- 5. 检查数据
-- =========================================================
SELECT 'weather_data' AS table_name, COUNT(*) AS row_count FROM weather_data;
SELECT 'train_tickets' AS table_name, COUNT(*) AS row_count FROM train_tickets;
