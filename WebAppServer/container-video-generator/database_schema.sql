-- Database schema for AI Video Generator
-- Adjust table and column names according to your existing structure

CREATE DATABASE IF NOT EXISTS video_generator_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE video_generator_db;

-- Sample postings table structure
-- Modify this according to your existing table structure
CREATE TABLE IF NOT EXISTS postings (
    id INT PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    video_url VARCHAR(500) NULL DEFAULT NULL,
    youtube_embed_url VARCHAR(500) NULL DEFAULT NULL,
    youtube_video_id VARCHAR(50) NULL DEFAULT NULL,
    s3_video_url VARCHAR(500) NULL DEFAULT NULL,
    script_text TEXT NULL DEFAULT NULL,
    heygen_video_id VARCHAR(100) NULL DEFAULT NULL,
    processing_status ENUM('pending', 'generating_script', 'generating_video', 'uploading_s3', 'uploading_youtube', 'completed', 'failed') DEFAULT 'pending',
    error_message TEXT NULL DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_video_url (video_url),
    INDEX idx_processing_status (processing_status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB;

-- Sample data (optional - for testing)
INSERT INTO postings (title, content) VALUES 
('공공주택 신규 공급 계획', '2024년 공공주택 신규 공급이 전년 대비 15% 증가할 예정입니다. 서울 및 수도권 지역을 중심으로 청년층과 신혼부부를 위한 임대주택이 대폭 확충됩니다.'),
('주택도시기금 지원 확대', '주택도시기금을 통한 저금리 대출 지원이 확대됩니다. 무주택 서민과 실수요자를 위한 금융 지원 정책이 강화되어 내 집 마련의 기회가 늘어날 것으로 예상됩니다.'),
('스마트 공공주택 시범사업', 'IoT와 AI 기술을 활용한 스마트 공공주택 시범사업이 시작됩니다. 에너지 효율성과 거주자 편의성을 극대화한 미래형 주거 공간을 제공할 예정입니다.');

-- Additional indexes for performance
CREATE INDEX idx_title_content ON postings(title, content(100));
CREATE INDEX idx_updated_at ON postings(updated_at);
