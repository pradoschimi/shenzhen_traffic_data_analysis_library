-- ===================================================
-- 数据库初始化脚本（仅建表 + 默认管理员）
--
-- 注意：建库、建用户、授权 全部在 start.sh 里用命令行完成，
-- 不放在 SQL 文件中，避免 sed 替换密码的特殊字符陷阱。
-- 本文件通过 mysql -u root db_name < init.sql 执行，
-- 已经 USE 了目标数据库，不需要 USE 语句。
-- ===================================================
SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;
-- ===================================================
-- 用户表
-- ===================================================
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '用户ID',
    username VARCHAR(64) NOT NULL UNIQUE COMMENT '用户名',
    hashed_password VARCHAR(256) NOT NULL COMMENT 'bcrypt哈希密码',
    nickname VARCHAR(64) DEFAULT '' COMMENT '昵称',
    is_active TINYINT(1) DEFAULT 1 COMMENT '是否激活',
    is_admin TINYINT(1) DEFAULT 0 COMMENT '是否管理员',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_username (username)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '用户表';
-- ===================================================
-- 路段基本信息表
-- ===================================================
CREATE TABLE IF NOT EXISTS road_sections (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    roadsect_id VARCHAR(64) NOT NULL UNIQUE COMMENT '路段ID（来源数据）',
    road_name VARCHAR(128) DEFAULT '' COMMENT '路段名称',
    district VARCHAR(64) DEFAULT '' COMMENT '所属区域',
    direction VARCHAR(32) DEFAULT '' COMMENT '方向',
    length_m DOUBLE DEFAULT 0.0 COMMENT '路段长度(米)',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_roadsect_id (roadsect_id),
    INDEX idx_district (district)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '基础路段信息表';
-- ===================================================
-- 路段速度记录表（核心数据表）
-- ===================================================
CREATE TABLE IF NOT EXISTS road_speed_records (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    roadsect_id VARCHAR(64) NOT NULL COMMENT '路段ID',
    record_date DATE NOT NULL COMMENT '记录日期',
    period VARCHAR(16) NOT NULL COMMENT '时间片',
    go_time DOUBLE DEFAULT 0.0 COMMENT '总行驶时间(秒)',
    go_count INT DEFAULT 0 COMMENT '车辆数',
    go_len DOUBLE DEFAULT 0.0 COMMENT '总行驶距离(米)',
    avg_speed DOUBLE DEFAULT 0.0 COMMENT '平均速度(km/h)',
    is_peak TINYINT(1) DEFAULT 0 COMMENT '是否高峰时段',
    is_workday TINYINT(1) DEFAULT 1 COMMENT '是否工作日',
    peak_type VARCHAR(16) DEFAULT '平峰' COMMENT '高峰类型',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_road_date_period (roadsect_id, record_date, period),
    INDEX idx_record_date (record_date),
    INDEX idx_peak_type (peak_type),
    UNIQUE KEY uq_road_date_period (roadsect_id, record_date, period),
    CONSTRAINT fk_speed_road FOREIGN KEY (roadsect_id) REFERENCES road_sections(roadsect_id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '路段时序速度表';
-- ===================================================
-- 用户收藏表
-- ===================================================
CREATE TABLE IF NOT EXISTS user_favorites (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    user_id INT NOT NULL COMMENT '用户ID',
    roadsect_id VARCHAR(64) NOT NULL COMMENT '收藏的路段ID',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '收藏时间',
    UNIQUE KEY uq_user_road_fav (user_id, roadsect_id),
    INDEX idx_fav_user (user_id),
    CONSTRAINT fk_fav_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '用户收藏路段表';
-- ===================================================
-- 用户建议表
-- ===================================================
CREATE TABLE IF NOT EXISTS user_suggestions (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    user_id INT NOT NULL COMMENT '用户ID',
    roadsect_id VARCHAR(64) DEFAULT '' COMMENT '相关路段ID',
    title VARCHAR(128) NOT NULL COMMENT '建议标题',
    content TEXT NOT NULL COMMENT '建议内容',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_suggestion_user (user_id),
    CONSTRAINT fk_suggestion_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '用户建议记录表';
-- ===================================================
-- 默认管理员 admin / admin123 （bcrypt 哈希）
-- ===================================================
INSERT IGNORE INTO users (
        username,
        hashed_password,
        nickname,
        is_active,
        is_admin
    )
VALUES (
        'admin',
        '$2b$12$mGU9sgfNjI91fDYAizqOXuzBqS9BJ5sq9Rs7I.CTfqYmlSyvF/oNa',
        '系统管理员',
        1,
        1
    );