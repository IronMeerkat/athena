CREATE EXTENSION IF NOT EXISTS vector;
-- Optional useful extension
do $$ begin
    perform 1 from pg_extension where extname = 'pg_trgm';
    if not found then
        execute 'create extension pg_trgm';
    end if;
end $$;
