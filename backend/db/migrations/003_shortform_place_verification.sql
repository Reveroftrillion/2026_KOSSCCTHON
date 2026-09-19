ALTER TABLE shortform_contents
ADD COLUMN place_id VARCHAR(36) NULL AFTER place_name;

CREATE INDEX idx_shortform_place
ON shortform_contents(place_id);

ALTER TABLE shortform_contents
ADD CONSTRAINT fk_shortform_place
FOREIGN KEY (place_id)
REFERENCES places(place_id)
ON DELETE SET NULL;