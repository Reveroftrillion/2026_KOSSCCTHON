-- Apply once after 001. Existing owner memberships are backfilled.
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
    recommended_time VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (trip_id) REFERENCES trips(trip_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE KEY unique_shortform (trip_id, user_id, url),
    INDEX idx_shortform_trip (trip_id),
    INDEX idx_shortform_user (user_id)
);

ALTER TABLE trip_itineraries ADD COLUMN preference_coverage JSON;
ALTER TABLE trip_itineraries ADD COLUMN preference_reflection JSON;
ALTER TABLE trip_itineraries ADD COLUMN result_json JSON;
ALTER TABLE itinerary_places ADD COLUMN user_scores JSON;
ALTER TABLE itinerary_places ADD COLUMN group_score DOUBLE;

INSERT INTO trip_members (trip_member_id, trip_id, user_id)
SELECT UUID(), t.trip_id, t.owner_user_id FROM trips t
WHERE NOT EXISTS (SELECT 1 FROM trip_members m WHERE m.trip_id=t.trip_id AND m.user_id=t.owner_user_id);
