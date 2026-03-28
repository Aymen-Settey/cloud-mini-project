CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT DEFAULT '',
    done BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO tasks (title, description, done) VALUES
    ('Learn Docker', 'Understand containers, images, and Docker Compose', FALSE),
    ('Build Flask API', 'Create a REST API with Flask and SQLAlchemy', TRUE),
    ('Set up monitoring', 'Configure Prometheus and Grafana for observability', FALSE);
