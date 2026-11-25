CREATE TABLE agent.users (
	id bigserial NOT NULL,
	user_uuid uuid DEFAULT gen_random_uuid() NOT NULL,
	username varchar(32) NOT NULL,
	"password" varchar(255) NOT NULL,
	email varchar(255) NULL,
	full_name varchar(50) NULL,
	phone varchar(20) NULL,
	role_id int8 NOT NULL,
	status varchar(32) DEFAULT 'active'::character varying NOT NULL,
	remark text NULL,
	created_at timestamptz DEFAULT now() NOT NULL,
	updated_at timestamptz DEFAULT now() NOT NULL,
	deleted_at timestamptz NULL,
	is_deleted bool DEFAULT false NOT NULL,
	CONSTRAINT users_pkey PRIMARY KEY (id)
);

CREATE TABLE agent.roles (
	id bigserial NOT NULL,
	role_name varchar(32) NOT NULL,
	remark varchar(255) NULL,
	created_at timestamptz DEFAULT now() NOT NULL,
	updated_at timestamptz DEFAULT now() NOT NULL,
	deleted_at timestamptz NULL,
	is_deleted bool DEFAULT false NOT NULL,
	CONSTRAINT roles_pkey PRIMARY KEY (id)
);