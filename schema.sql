-- Job Application Tracker - database creation script
-- Run with:  mysql -u root -p < schema.sql
-- WARNING: drops and recreates the job_tracker database.

DROP DATABASE IF EXISTS job_tracker;
CREATE DATABASE job_tracker CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE job_tracker;

-- ---------------------------------------------------------------
-- companies
-- ---------------------------------------------------------------
CREATE TABLE companies (
    company_id   INT PRIMARY KEY AUTO_INCREMENT,
    company_name VARCHAR(100) NOT NULL,
    industry     VARCHAR(50),
    website      VARCHAR(200),
    city         VARCHAR(50),
    state        VARCHAR(50),
    notes        TEXT
);

-- ---------------------------------------------------------------
-- jobs
-- requirements JSON example:
--   {"skills": ["Python", "SQL"], "experience_years": 2, "education": "Bachelor's"}
-- ---------------------------------------------------------------
CREATE TABLE jobs (
    job_id       INT PRIMARY KEY AUTO_INCREMENT,
    company_id   INT NOT NULL,
    job_title    VARCHAR(100) NOT NULL,
    job_type     ENUM('Full-time', 'Part-time', 'Contract', 'Internship') DEFAULT 'Full-time',
    salary_min   INT,
    salary_max   INT,
    job_url      VARCHAR(300),
    date_posted  DATE,
    requirements JSON,
    CONSTRAINT fk_jobs_company
        FOREIGN KEY (company_id) REFERENCES companies (company_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT chk_jobs_salary
        CHECK (salary_min IS NULL OR salary_max IS NULL OR salary_min <= salary_max)
);

-- ---------------------------------------------------------------
-- applications
-- interview_data JSON example:
--   {"rounds": [{"date": "2026-11-20", "type": "Phone Screen",
--                "interviewer": "Jane Doe", "notes": "Went well"}]}
-- ---------------------------------------------------------------
CREATE TABLE applications (
    application_id    INT PRIMARY KEY AUTO_INCREMENT,
    job_id            INT NOT NULL,
    application_date  DATE NOT NULL,
    status            ENUM('Applied', 'Screening', 'Interview', 'Offer', 'Rejected', 'Withdrawn')
                      NOT NULL DEFAULT 'Applied',
    resume_version    VARCHAR(50),
    cover_letter_sent BOOLEAN NOT NULL DEFAULT FALSE,
    interview_data    JSON,
    CONSTRAINT fk_applications_job
        FOREIGN KEY (job_id) REFERENCES jobs (job_id)
        ON DELETE CASCADE ON UPDATE CASCADE
);

-- ---------------------------------------------------------------
-- contacts
-- ---------------------------------------------------------------
CREATE TABLE contacts (
    contact_id   INT PRIMARY KEY AUTO_INCREMENT,
    company_id   INT NOT NULL,
    contact_name VARCHAR(100) NOT NULL,
    title        VARCHAR(100),
    email        VARCHAR(100),
    phone        VARCHAR(20),
    linkedin_url VARCHAR(200),
    notes        TEXT,
    CONSTRAINT fk_contacts_company
        FOREIGN KEY (company_id) REFERENCES companies (company_id)
        ON DELETE CASCADE ON UPDATE CASCADE
);

-- ---------------------------------------------------------------
-- Sample data
-- ---------------------------------------------------------------
INSERT INTO companies (company_name, industry, website, city, state, notes) VALUES
('TechCorp', 'Technology', 'https://www.techcorp.example.com', 'Orlando', 'FL',
 'Mid-size software company. Strong mentorship program for new grads.'),
('DataCo', 'Data Analytics', 'https://www.dataco.example.com', 'Tampa', 'FL',
 'Analytics consulting firm with many healthcare and retail clients.'),
('CloudNine Systems', 'Cloud Computing', 'https://www.cloudnine.example.com', 'Austin', 'TX',
 'Fast-growing startup. Hybrid work, 2 days in office.'),
('HealthBridge', 'Healthcare', 'https://www.healthbridge.example.com', 'Miami', 'FL',
 'Hospital network with a large internal IT department.'),
('FinEdge Bank', 'Finance', 'https://www.finedge.example.com', 'Charlotte', 'NC',
 'Regional bank modernizing its backend systems.');

INSERT INTO jobs (company_id, job_title, job_type, salary_min, salary_max, job_url, date_posted, requirements) VALUES
(1, 'Software Developer', 'Full-time', 70000, 90000, 'https://www.techcorp.example.com/careers/101', '2026-10-01',
 '{"skills": ["Python", "SQL", "Flask"], "experience_years": 1, "education": "Bachelor''s in Computer Science"}'),
(2, 'Data Analyst', 'Full-time', 60000, 75000, 'https://www.dataco.example.com/jobs/data-analyst', '2026-10-05',
 '{"skills": ["Python", "SQL", "Tableau"], "experience_years": 1, "education": "Bachelor''s"}'),
(3, 'Cloud Engineering Intern', 'Internship', 40000, 50000, 'https://www.cloudnine.example.com/interns', '2026-10-12',
 '{"skills": ["AWS", "Python", "Docker", "Linux"], "experience_years": 0, "education": "Currently enrolled"}'),
(4, 'Database Administrator', 'Contract', 80000, 100000, 'https://www.healthbridge.example.com/it/dba', '2026-10-20',
 '{"skills": ["MySQL", "SQL", "Linux", "Backup and Recovery"], "experience_years": 3, "education": "Bachelor''s"}'),
(5, 'Junior Backend Developer', 'Full-time', 65000, 80000, 'https://www.finedge.example.com/careers/backend', '2026-10-25',
 '{"skills": ["Java", "SQL", "Spring", "Git"], "experience_years": 0, "education": "Bachelor''s"}'),
(1, 'Frontend Developer', 'Part-time', 35000, 45000, 'https://www.techcorp.example.com/careers/102', '2026-11-02',
 '{"skills": ["HTML", "CSS", "JavaScript", "React"], "experience_years": 1, "education": "Any"}'),
(2, 'Machine Learning Intern', 'Internship', 30000, 40000, 'https://www.dataco.example.com/jobs/ml-intern', '2026-11-06',
 '{"skills": ["Python", "Pandas", "Scikit-learn", "SQL"], "experience_years": 0, "education": "Currently enrolled"}');

INSERT INTO applications (job_id, application_date, status, resume_version, cover_letter_sent, interview_data) VALUES
(1, '2026-10-03', 'Interview', 'v3-software', TRUE,
 '{"rounds": [{"date": "2026-10-15", "type": "Phone Screen", "interviewer": "Maria Lopez", "notes": "Asked about Flask projects."},
              {"date": "2026-12-02", "type": "Technical", "interviewer": "David Kim", "notes": "Live coding, SQL joins."}]}'),
(2, '2026-10-07', 'Screening', 'v2-data', TRUE,
 '{"rounds": [{"date": "2026-11-24", "type": "Phone Screen", "interviewer": "Priya Shah", "notes": "Prepare Tableau portfolio."}]}'),
(3, '2026-10-14', 'Applied', 'v3-software', FALSE, NULL),
(4, '2026-10-22', 'Rejected', 'v1-general', FALSE,
 '{"rounds": [{"date": "2026-10-30", "type": "Phone Screen", "interviewer": "Tom Reed", "notes": "Wanted more DBA experience."}]}'),
(5, '2026-10-28', 'Offer', 'v3-software', TRUE,
 '{"rounds": [{"date": "2026-11-04", "type": "Phone Screen", "interviewer": "Alicia Grant", "notes": "Friendly team."},
              {"date": "2026-11-10", "type": "Onsite", "interviewer": "Panel", "notes": "Offer received on 11/13."}]}'),
(7, '2026-11-08', 'Withdrawn', 'v2-data', FALSE, NULL);

INSERT INTO contacts (company_id, contact_name, title, email, phone, linkedin_url, notes) VALUES
(1, 'Maria Lopez', 'Technical Recruiter', 'maria.lopez@techcorp.example.com', '407-555-0101',
 'https://www.linkedin.com/in/maria-lopez-example', 'Met at the UCF career fair.'),
(1, 'David Kim', 'Engineering Manager', 'david.kim@techcorp.example.com', '407-555-0102',
 'https://www.linkedin.com/in/david-kim-example', 'Hiring manager for the Software Developer role.'),
(2, 'Priya Shah', 'Talent Acquisition', 'priya.shah@dataco.example.com', '813-555-0140',
 'https://www.linkedin.com/in/priya-shah-example', 'Prefers email over phone.'),
(4, 'Tom Reed', 'IT Director', 'tom.reed@healthbridge.example.com', '305-555-0177',
 NULL, 'Suggested reapplying next year.'),
(5, 'Alicia Grant', 'HR Business Partner', 'alicia.grant@finedge.example.com', '704-555-0123',
 'https://www.linkedin.com/in/alicia-grant-example', 'Sent the offer letter.');
