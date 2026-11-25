CREATE TABLE agent.work_order (
id bigserial NOT NULL,
order_uuid uuid DEFAULT gen_random_uuid() NOT NULL,
title varchar(512) NOT NULL,
"content" text NULL,
status varchar(32) DEFAULT 'pending'::character varying NOT NULL,
order_type varchar(64) NULL,
priority varchar(32) DEFAULT 'medium'::character varying NULL,
creator_id int8 NOT NULL,
handler_id int8 NULL,
remark text NULL,
created_at timestamptz DEFAULT now() NOT NULL,
updated_at timestamptz DEFAULT now() NOT NULL,
finished_at timestamptz NULL,
deleted_at timestamptz NULL,
is_deleted bool DEFAULT false NOT NULL,
CONSTRAINT work_order_pkey PRIMARY KEY (id)
);