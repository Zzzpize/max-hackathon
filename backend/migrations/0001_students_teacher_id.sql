-- Run once against an existing PostgreSQL database before deploying the new backend.
-- Students without a submission cannot be assigned safely and must be assigned manually.
BEGIN;
ALTER TABLE students ADD COLUMN teacher_id varchar;

UPDATE students AS student
SET teacher_id = owners.teacher_id
FROM (
    SELECT submission.student_id, min(work.teacher_id) AS teacher_id
    FROM submissions AS submission
    JOIN work_templates AS work ON work.id = submission.work_id
    GROUP BY submission.student_id
    HAVING count(DISTINCT work.teacher_id) = 1
) AS owners
WHERE student.id = owners.student_id;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM students WHERE teacher_id IS NULL) THEN
        RAISE EXCEPTION 'Assign teacher_id to students with no owner or multiple owners before completing migration';
    END IF;
END $$;

ALTER TABLE students ALTER COLUMN teacher_id SET NOT NULL;
CREATE INDEX ix_students_teacher_id ON students (teacher_id);
COMMIT;
