-- Who the data belongs to
CREATE TABLE person (
  person_id    BIGSERIAL PRIMARY KEY,
  external_key TEXT UNIQUE,              -- optional: username/uuid/etc.
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Where the data came from (vendor/device/app)
CREATE TABLE data_source (
  source_id      BIGSERIAL PRIMARY KEY,
  vendor         TEXT NOT NULL,          -- 'apple', 'google', 'fitbit', etc.
  product        TEXT,                   -- 'health', 'pixel_watch', etc.
  device_model   TEXT,
  device_raw     TEXT,
  source_version TEXT
);

-- Optional traceability to the raw vendor record
-- (useful when you want to link back to Apple HK types or vendor IDs)
CREATE TABLE source_event (
  source_event_id BIGSERIAL PRIMARY KEY,
  source_id       BIGINT REFERENCES data_source(source_id),
  vendor_type     TEXT,                  -- e.g. Apple HK type string
  vendor_id       TEXT,                  -- vendor record UUID if available
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE hr_sample (
  hr_id           BIGSERIAL PRIMARY KEY,
  person_id       BIGINT NOT NULL REFERENCES person(person_id),
  source_id       BIGINT REFERENCES data_source(source_id),
  source_event_id BIGINT REFERENCES source_event(source_event_id),

  ts              TIMESTAMPTZ NOT NULL,   -- timestamp of measurement
  bpm             SMALLINT NOT NULL,      -- beats per minute

  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_hr_person_ts ON hr_sample (person_id, ts);

CREATE TABLE steps_sample (
  steps_id        BIGSERIAL PRIMARY KEY,
  person_id       BIGINT NOT NULL REFERENCES person(person_id),
  source_id       BIGINT REFERENCES data_source(source_id),
  source_event_id BIGINT REFERENCES source_event(source_event_id),

  start_ts        TIMESTAMPTZ NOT NULL,
  end_ts          TIMESTAMPTZ NOT NULL,
  steps           INTEGER NOT NULL CHECK (steps >= 0),

  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (end_ts >= start_ts)
);

CREATE INDEX idx_steps_person_start ON steps_sample (person_id, start_ts);

CREATE TABLE sleep_session (
  sleep_session_id BIGSERIAL PRIMARY KEY,
  person_id        BIGINT NOT NULL REFERENCES person(person_id),
  source_id        BIGINT REFERENCES data_source(source_id),
  source_event_id  BIGINT REFERENCES source_event(source_event_id),

  start_ts         TIMESTAMPTZ NOT NULL,
  end_ts           TIMESTAMPTZ NOT NULL,

  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (end_ts >= start_ts)
);

CREATE INDEX idx_sleep_session_person_start ON sleep_session (person_id, start_ts);

-- Optional: stage/interval breakdown tied to a session
CREATE TABLE sleep_stage (
  sleep_stage_id    BIGSERIAL PRIMARY KEY,
  sleep_session_id  BIGINT NOT NULL REFERENCES sleep_session(sleep_session_id) ON DELETE CASCADE,

  start_ts          TIMESTAMPTZ NOT NULL,
  end_ts            TIMESTAMPTZ NOT NULL,

  stage             TEXT NOT NULL,        -- 'awake', 'in_bed', 'light', 'deep', 'rem', 'unknown'
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),

  CHECK (end_ts >= start_ts)
);

CREATE INDEX idx_sleep_stage_session_start ON sleep_stage (sleep_session_id, start_ts);