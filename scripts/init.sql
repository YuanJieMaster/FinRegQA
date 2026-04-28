-- FinRegQA 数据库初始化脚本
-- 此脚本在 MySQL 容器首次启动时自动执行
-- 表结构定义与 SQLAlchemy ORM 模型保持一致

-- ============================================================================
-- 用户认证相关表
-- ============================================================================

-- 用户表
CREATE TABLE IF NOT EXISTS `users` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `username` VARCHAR(50) NOT NULL UNIQUE,
    `email` VARCHAR(100) NOT NULL UNIQUE,
    `password_hash` VARCHAR(255) NOT NULL,
    `status` VARCHAR(20) DEFAULT 'active',
    `email_verified` BOOLEAN DEFAULT FALSE,
    `verification_token` VARCHAR(255),
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `last_login` DATETIME,
    INDEX `idx_user_username` (`username`),
    INDEX `idx_user_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 密码重置令牌表
CREATE TABLE IF NOT EXISTS `password_reset_tokens` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `token` VARCHAR(255) NOT NULL UNIQUE,
    `token_type` VARCHAR(20) DEFAULT 'reset',
    `expires_at` DATETIME NOT NULL,
    `used` BOOLEAN DEFAULT FALSE,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
    INDEX `idx_token` (`token`),
    INDEX `idx_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 用户会话表
CREATE TABLE IF NOT EXISTS `user_sessions` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `refresh_token` VARCHAR(255) NOT NULL UNIQUE,
    `user_agent` VARCHAR(255),
    `ip_address` VARCHAR(50),
    `expires_at` DATETIME NOT NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `is_active` BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
    INDEX `idx_session_user_id` (`user_id`),
    INDEX `idx_session_expires` (`expires_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 知识库相关表
-- ============================================================================

-- 文档表
CREATE TABLE IF NOT EXISTS `document` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(255) NOT NULL,
    `source` VARCHAR(255),
    `file_type` VARCHAR(50),
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_document_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 知识条目表
CREATE TABLE IF NOT EXISTS `knowledge` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `document_id` INT NOT NULL,
    `content` TEXT NOT NULL,
    `category` VARCHAR(100),
    `region` VARCHAR(100),
    `regulation_type` VARCHAR(100),
    `article_number` VARCHAR(50),
    `section_number` VARCHAR(50),
    `milvus_id` BIGINT,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`document_id`) REFERENCES `document`(`id`) ON DELETE CASCADE,
    INDEX `idx_knowledge_document_id` (`document_id`),
    INDEX `idx_knowledge_category` (`category`),
    INDEX `idx_knowledge_region` (`region`),
    INDEX `idx_knowledge_article` (`article_number`),
    INDEX `idx_knowledge_milvus_id` (`milvus_id`),
    FULLTEXT INDEX `idx_knowledge_fulltext` (
        `content`,
        `category`,
        `regulation_type`,
        `article_number`,
        `section_number`
    ) WITH PARSER ngram
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 操作日志表
CREATE TABLE IF NOT EXISTS `log` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `operation` VARCHAR(50) NOT NULL,
    `knowledge_id` INT,
    `status` VARCHAR(20),
    `message` TEXT,
    `duration_ms` FLOAT,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`knowledge_id`) REFERENCES `knowledge`(`id`) ON DELETE SET NULL,
    INDEX `idx_log_operation` (`operation`),
    INDEX `idx_log_status` (`status`),
    INDEX `idx_log_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 完成提示
-- ============================================================================

SELECT '✅ FinRegQA 数据库初始化完成' AS `Status`;
