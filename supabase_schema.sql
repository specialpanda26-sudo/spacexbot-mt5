-- Optional: the app creates these itself on first boot. Paste into Supabase > SQL Editor only if you want the tables before deploying.
-- Row Level Security is ON with no policies: nobody can read these tables through Supabase's public API. Only our server can.
CREATE TABLE IF NOT EXISTS users(uid TEXT PRIMARY KEY,email TEXT,name TEXT,plan_until BIGINT DEFAULT 0,created BIGINT,
  username TEXT,phone TEXT,country TEXT,bio TEXT,exp_level TEXT,goal TEXT,risk_pref TEXT,av INTEGER,notif TEXT,dob TEXT,gender TEXT);
CREATE UNIQUE INDEX IF NOT EXISTS ux_users_username ON users(username) WHERE username IS NOT NULL;
CREATE TABLE IF NOT EXISTS signals(id BIGSERIAL PRIMARY KEY,symbol TEXT,side TEXT,entry DOUBLE PRECISION,sl DOUBLE PRECISION,tp DOUBLE PRECISION,
  risk_pct DOUBLE PRECISION,strategy TEXT,score INTEGER,status TEXT,created BIGINT,ticket TEXT,lots DOUBLE PRECISION,fill DOUBLE PRECISION,
  pnl DOUBLE PRECISION,closed BIGINT,note TEXT);
CREATE TABLE IF NOT EXISTS payments(ref TEXT PRIMARY KEY,uid TEXT,provider TEXT,plan TEXT,amount DOUBLE PRECISION,currency TEXT,status TEXT,
  created BIGINT,extra TEXT,phone TEXT,checkout_id TEXT,receipt TEXT,paid_at BIGINT,last_check BIGINT);
CREATE TABLE IF NOT EXISTS kv(k TEXT PRIMARY KEY,v TEXT);
ALTER TABLE users ADD COLUMN IF NOT EXISTS onboarded INTEGER;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE kv ENABLE ROW LEVEL SECURITY;
CREATE TABLE IF NOT EXISTS push_tokens(token TEXT PRIMARY KEY,uid TEXT,platform TEXT,created BIGINT,seen BIGINT);
CREATE INDEX IF NOT EXISTS ix_push_tokens_uid ON push_tokens(uid);
CREATE TABLE IF NOT EXISTS push_log(uid TEXT,kind BIGINT,k TEXT,ts BIGINT);
CREATE INDEX IF NOT EXISTS ix_push_log_uid ON push_log(uid,ts);
CREATE UNIQUE INDEX IF NOT EXISTS ux_push_log_key ON push_log(uid,k) WHERE k IS NOT NULL;
ALTER TABLE push_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE push_log ENABLE ROW LEVEL SECURITY;

-- Phone mode (created by the app on boot; paste here only if you want the tables before deploying)
CREATE TABLE IF NOT EXISTS assist(uid TEXT PRIMARY KEY,enabled INTEGER DEFAULT 0,balance DOUBLE PRECISION,risk DOUBLE PRECISION,updated BIGINT);
CREATE TABLE IF NOT EXISTS assist_log(uid TEXT,sid BIGINT,action TEXT,ts BIGINT,lots DOUBLE PRECISION,outcome TEXT,pnl DOUBLE PRECISION,done BIGINT,PRIMARY KEY(uid,sid));
CREATE INDEX IF NOT EXISTS ix_assist_log_uid ON assist_log(uid,ts);
ALTER TABLE assist ENABLE ROW LEVEL SECURITY;
ALTER TABLE assist_log ENABLE ROW LEVEL SECURITY;
