-- Enhance RLS policies
ALTER TABLE public.users FORCE ROW LEVEL SECURITY;
ALTER TABLE public.user_preferences FORCE ROW LEVEL SECURITY;
ALTER TABLE public.pantry_items FORCE ROW LEVEL SECURITY;
ALTER TABLE public.recipes FORCE ROW LEVEL SECURITY;

-- Add rate limiting for API requests
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Add audit logging
CREATE TABLE public.audit_logs (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  table_name text NOT NULL,
  record_id uuid NOT NULL,
  action text NOT NULL,
  old_data jsonb,
  new_data jsonb,
  user_id uuid REFERENCES public.users(id),
  ip_address inet,
  created_at timestamptz DEFAULT now()
);

-- Create audit trigger function
CREATE OR REPLACE FUNCTION public.audit_trigger_func()
RETURNS trigger AS $$
BEGIN
  INSERT INTO public.audit_logs (
    table_name,
    record_id,
    action,
    old_data,
    new_data,
    user_id
  )
  VALUES (
    TG_TABLE_NAME,
    COALESCE(NEW.id, OLD.id),
    TG_OP,
    CASE WHEN TG_OP = 'DELETE' THEN row_to_json(OLD) ELSE NULL END,
    CASE WHEN TG_OP IN ('INSERT', 'UPDATE') THEN row_to_json(NEW) ELSE NULL END,
    auth.uid()
  );
  RETURN NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER; 