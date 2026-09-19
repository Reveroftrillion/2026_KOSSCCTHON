-- 1. 사용자 테이블
CREATE TABLE users (
    user_id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    bio TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    profile_image_url VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. 사용자 취향 점수 테이블 (개인 취향 DB)
CREATE TABLE user_preferences (
    preference_id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL UNIQUE,
    category_scores JSON, -- 예: {"Cafe": 0.82, "Food": 0.71, "Exhibition": 0.64}
    tag_scores JSON,      -- 예: {"한식": 0.7, "야경": 0.8}
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- 3. 여행 그룹(방) 테이블
CREATE TABLE trips (
    trip_id VARCHAR(36) PRIMARY KEY,
    owner_user_id VARCHAR(36) NOT NULL, -- 방장 ID
    trip_name VARCHAR(200) NOT NULL,
    region VARCHAR(100) NOT NULL,       -- 예: "성수"
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    day_start_time TIME DEFAULT '13:00:00',
    day_end_time TIME DEFAULT '20:00:00',
    description TEXT,
    status VARCHAR(20) DEFAULT 'planning', -- planning, ongoing, completed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    INDEX idx_trip_region (region)
);

-- 4. 여행 그룹 멤버 테이블 (다대다 관계 해소: 여러 명이 하나의 그룹에 참여)
CREATE TABLE trip_members (
    trip_member_id VARCHAR(36) PRIMARY KEY,
    trip_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (trip_id) REFERENCES trips(trip_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE KEY unique_trip_user (trip_id, user_id)
);

-- 5. 장소 원본 정보 테이블 (지도 API 등으로 검증된 장소 정보)
CREATE TABLE places (
    place_id VARCHAR(36) PRIMARY KEY,
    place_name VARCHAR(200) NOT NULL,
    category VARCHAR(50) NOT NULL, -- cafe, exhibition, shopping, food 등
    description TEXT,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    address VARCHAR(255),
    region VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_place_category (category),
    INDEX idx_place_region (region)
);

-- 6. 사용자들이 저장한 장소 테이블 (Shared Trip Basket)
CREATE TABLE saved_places (
    saved_place_id VARCHAR(36) PRIMARY KEY,
    trip_id VARCHAR(36) NOT NULL,   -- 어떤 그룹의 장바구니인지
    user_id VARCHAR(36) NOT NULL,   -- 누가 저장했는지
    place_id VARCHAR(36) NOT NULL,  -- 어떤 장소인지
    tags JSON,                      -- 예: ["팝업", "쇼핑"]
    short_form_video_url VARCHAR(255), -- 숏폼 원본 URL
    description TEXT,
    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (trip_id) REFERENCES trips(trip_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (place_id) REFERENCES places(place_id) ON DELETE CASCADE,
    INDEX idx_saved_places_trip (trip_id)
);

-- 7. AI가 생성한 여행 코스(일정) 메인 테이블
CREATE TABLE trip_itineraries (
    itinerary_id VARCHAR(36) PRIMARY KEY,
    trip_id VARCHAR(36) NOT NULL,
    day_number INT NOT NULL,        -- 1일차, 2일차...
    summary TEXT,                   -- AI가 요약한 일정 설명
    preference_coverage JSON,
    preference_reflection JSON,
    result_json JSON,
    preference_reflection_rates JSON, -- 예: {"원영": 83, "민수": 78, "지수": 85} (취향 반영도)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (trip_id) REFERENCES trips(trip_id) ON DELETE CASCADE,
    UNIQUE KEY unique_trip_day (trip_id, day_number)
);

-- 8. 여행 코스 상세 (일정별 방문 장소 순서 및 추천 이유)
CREATE TABLE itinerary_places (
    itinerary_place_id VARCHAR(36) PRIMARY KEY,
    itinerary_id VARCHAR(36) NOT NULL,
    place_id VARCHAR(36) NOT NULL,
    sequence_order INT NOT NULL,    -- 방문 순서 (1, 2, 3...)
    visit_start_time TIME NOT NULL,
    visit_end_time TIME NOT NULL,
    user_scores JSON,
    group_score DOUBLE,
    related_users JSON,             -- 예: ["민수"] 또는 ["원영", "지수"] (어떤 사람들의 취향이 반영되었는지)
    notes TEXT,                     -- AI가 남긴 추천 이유 ("민수의 팝업 및 쇼핑 취향을 반영했습니다.")
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (itinerary_id) REFERENCES trip_itineraries(itinerary_id) ON DELETE CASCADE,
    FOREIGN KEY (place_id) REFERENCES places(place_id) ON DELETE CASCADE,
    INDEX idx_itinerary_places_order (itinerary_id, sequence_order)
);

CREATE TABLE shortform_contents (
    content_id VARCHAR(36) PRIMARY KEY,
    trip_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    platform VARCHAR(30) DEFAULT 'youtube',
    url VARCHAR(500) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    title VARCHAR(500),
    category VARCHAR(50),
    keywords JSON,
    area VARCHAR(100),
    activity VARCHAR(255),
    place_name VARCHAR(255),
    place_id VARCHAR(36),
    recommended_time VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (trip_id) REFERENCES trips(trip_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (place_id) REFERENCES places(place_id) ON DELETE SET NULL,
    UNIQUE KEY unique_shortform (trip_id, user_id, url),
    INDEX idx_shortform_trip (trip_id),
    INDEX idx_shortform_user (user_id),
    INDEX idx_shortform_place (place_id)
);
