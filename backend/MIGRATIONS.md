# Database migrations

Run Alembic from `backend/` (or pass `-c backend/alembic.ini` from the repository root).

## New database

`alembic upgrade head`

The backend Docker image runs this command before starting the API. Normal startup
does not call `Base.metadata.create_all`. For disposable local development only,
set `DEV_AUTO_CREATE_TABLES=true`.

## Database created by the old `create_all` startup

Back up the database first. If `students.teacher_id` is missing, apply
`migrations/0001_students_teacher_id.sql` and resolve any students whose owner
cannot be inferred. Compare the resulting tables and indexes with
`versions/0001_initial.py`. Only when they match, run `alembic stamp 0001_initial`.
This records the baseline without recreating existing tables. Then run
`alembic upgrade head` for future revisions. Do not stamp an incomplete schema.
