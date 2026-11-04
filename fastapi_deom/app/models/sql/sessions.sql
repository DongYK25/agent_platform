CREATE TABLE public.sessions (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	user_uid uuid NULL,
	prompt_name text DEFAULT 'assistant'::text NOT NULL,
	model text NULL,
	title text NULL,
	created_at timestamptz DEFAULT now() NOT NULL,
	updated_at timestamptz DEFAULT now() NOT NULL,
	metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
	CONSTRAINT sessions_pkey PRIMARY KEY (id)
);
-- CREATE INDEX idx_sessions_user ON public.sessions USING btree (user_id, updated_at DESC);