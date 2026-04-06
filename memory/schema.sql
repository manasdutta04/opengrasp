PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL UNIQUE,
    company TEXT,
    role TEXT,
    jd_raw TEXT,
    jd_extracted TEXT,
    scraped_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'new' CHECK (status IN (
        'new', 'evaluated', 'applied', 'interview', 'offer', 'rejected', 'skipped'
    ))
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_company_role ON jobs(company, role);

CREATE TABLE IF NOT EXISTS evaluations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    score_total REAL NOT NULL CHECK (score_total >= 1.0 AND score_total <= 5.0),
    grade TEXT NOT NULL CHECK (grade IN ('A', 'B', 'C', 'D', 'F')),
    score_role_match REAL NOT NULL CHECK (score_role_match >= 1.0 AND score_role_match <= 5.0),
    score_skills REAL NOT NULL CHECK (score_skills >= 1.0 AND score_skills <= 5.0),
    score_seniority REAL NOT NULL CHECK (score_seniority >= 1.0 AND score_seniority <= 5.0),
    score_compensation REAL NOT NULL CHECK (score_compensation >= 1.0 AND score_compensation <= 5.0),
    score_geographic REAL NOT NULL CHECK (score_geographic >= 1.0 AND score_geographic <= 5.0),
    score_company_stage REAL NOT NULL CHECK (score_company_stage >= 1.0 AND score_company_stage <= 5.0),
    score_pmf REAL NOT NULL CHECK (score_pmf >= 1.0 AND score_pmf <= 5.0),
    score_growth REAL NOT NULL CHECK (score_growth >= 1.0 AND score_growth <= 5.0),
    score_interview_likelihood REAL NOT NULL CHECK (score_interview_likelihood >= 1.0 AND score_interview_likelihood <= 5.0),
    score_timeline REAL NOT NULL CHECK (score_timeline >= 1.0 AND score_timeline <= 5.0),
    report_path TEXT,
    evaluated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    model_used TEXT,
    notes TEXT,
    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_evaluations_job_id ON evaluations(job_id);
CREATE INDEX IF NOT EXISTS idx_evaluations_grade ON evaluations(grade);

CREATE TABLE IF NOT EXISTS cvs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    evaluation_id INTEGER,
    cv_path TEXT,
    pdf_path TEXT,
    keywords_injected TEXT,
    archetype_used TEXT,
    generated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
    FOREIGN KEY (evaluation_id) REFERENCES evaluations(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_cvs_job_id ON cvs(job_id);
CREATE INDEX IF NOT EXISTS idx_cvs_evaluation_id ON cvs(evaluation_id);

CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    cv_id INTEGER,
    applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    auto_applied INTEGER NOT NULL DEFAULT 0 CHECK (auto_applied IN (0, 1)),
    human_reviewed INTEGER NOT NULL DEFAULT 0 CHECK (human_reviewed IN (0, 1)),
    response_received_at DATETIME,
    outcome TEXT NOT NULL DEFAULT 'pending' CHECK (outcome IN (
        'pending', 'interview', 'rejected', 'offer', 'ghosted'
    )),
    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
    FOREIGN KEY (cv_id) REFERENCES cvs(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_applications_job_id ON applications(job_id);
CREATE INDEX IF NOT EXISTS idx_applications_outcome ON applications(outcome);

CREATE TABLE IF NOT EXISTS outcomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id INTEGER NOT NULL,
    outcome_type TEXT NOT NULL CHECK (outcome_type IN (
        'interview', 'rejected', 'offer', 'ghosted'
    )),
    notes TEXT,
    logged_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_outcomes_application_id ON outcomes(application_id);
CREATE INDEX IF NOT EXISTS idx_outcomes_type ON outcomes(outcome_type);

CREATE TABLE IF NOT EXISTS scoring_weights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dimension TEXT NOT NULL UNIQUE,
    weight REAL NOT NULL CHECK (weight >= 0.0 AND weight <= 1.0),
    last_updated DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_scoring_weights_dimension ON scoring_weights(dimension);

CREATE TABLE IF NOT EXISTS portals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN (
        'greenhouse', 'ashby', 'lever', 'linkedin', 'custom'
    )),
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1))
);

CREATE INDEX IF NOT EXISTS idx_portals_active ON portals(active);
