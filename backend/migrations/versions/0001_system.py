"""Create the system management schema."""

from alembic import op

revision = "0001_system"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE sys_config (
	id BIGSERIAL NOT NULL,
	config_name VARCHAR(64) NOT NULL,
	config_key VARCHAR(128) NOT NULL,
	config_value VARCHAR(512) NOT NULL,
	config_type CHAR(1) DEFAULT '1' NOT NULL CHECK (config_type IN ('0','1')),
	remark VARCHAR(256),
	create_time TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	update_time TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (config_key)
)""")
    op.execute("""CREATE TABLE sys_dept (
	id BIGSERIAL NOT NULL,
	parent_id BIGINT DEFAULT '0' NOT NULL,
	dept_name VARCHAR(64) NOT NULL,
	order_num INTEGER DEFAULT '0' NOT NULL,
	leader VARCHAR(64),
	phone VARCHAR(20),
	status CHAR(1) DEFAULT '0' NOT NULL CHECK (status IN ('0','1')),
	create_time TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	update_time TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id)
)""")
    op.execute("""CREATE TABLE sys_dict_type (
	id BIGSERIAL NOT NULL,
	dict_name VARCHAR(64) NOT NULL,
	dict_code VARCHAR(64) NOT NULL,
	status CHAR(1) DEFAULT '0' NOT NULL CHECK (status IN ('0','1')),
	remark VARCHAR(256),
	PRIMARY KEY (id),
	UNIQUE (dict_code)
)""")
    op.execute("""CREATE TABLE sys_oper_log (
	id BIGSERIAL NOT NULL,
	operator_id BIGINT,
	operator_name VARCHAR(64),
	module VARCHAR(64) NOT NULL,
	operation VARCHAR(128) NOT NULL,
	method VARCHAR(256) NOT NULL,
	request_url VARCHAR(256) NOT NULL,
	request_param TEXT,
	ip VARCHAR(64),
	status CHAR(1) DEFAULT '0' NOT NULL CHECK (status IN ('0','1')),
	error_msg VARCHAR(512),
	cost_time BIGINT NOT NULL,
	oper_time TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id)
)""")
    op.execute("""CREATE INDEX ix_sys_oper_log_oper_time_id ON sys_oper_log (oper_time, id)""")
    op.execute("""CREATE TABLE sys_permission (
	id BIGSERIAL NOT NULL,
	parent_id BIGINT DEFAULT '0' NOT NULL,
	perm_name VARCHAR(64) NOT NULL,
	perm_type VARCHAR(16) NOT NULL,
	permission_code VARCHAR(128) NOT NULL,
	path VARCHAR(128),
	component VARCHAR(128),
	icon VARCHAR(64),
	order_num INTEGER DEFAULT '0' NOT NULL,
	visible CHAR(1) DEFAULT '0' NOT NULL CHECK (visible IN ('0','1')),
	status CHAR(1) DEFAULT '0' NOT NULL CHECK (status IN ('0','1')),
	PRIMARY KEY (id),
	CHECK (perm_type IN ('DIR','MENU','BUTTON')),
	UNIQUE (permission_code)
)""")
    op.execute("""CREATE TABLE sys_role (
	id BIGSERIAL NOT NULL,
	role_name VARCHAR(64) NOT NULL,
	role_code VARCHAR(64) NOT NULL,
	data_scope VARCHAR(20) NOT NULL,
	is_super CHAR(1) DEFAULT '0' NOT NULL CHECK (is_super IN ('0','1')),
	remark VARCHAR(256),
	create_time TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	update_time TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	CHECK (data_scope IN ('ALL','CUSTOM','DEPT','DEPT_CHILD','SELF')),
	UNIQUE (role_code)
)""")
    op.execute("""CREATE TABLE sys_dict_data (
	id BIGSERIAL NOT NULL,
	dict_code VARCHAR(64) NOT NULL,
	dict_label VARCHAR(64) NOT NULL,
	dict_value VARCHAR(64) NOT NULL,
	order_num INTEGER DEFAULT '0' NOT NULL,
	status CHAR(1) DEFAULT '0' NOT NULL CHECK (status IN ('0','1')),
	PRIMARY KEY (id),
	UNIQUE (dict_code, dict_value),
	FOREIGN KEY(dict_code) REFERENCES sys_dict_type (dict_code)
)""")
    op.execute("""CREATE TABLE sys_role_dept (
	role_id BIGINT NOT NULL,
	dept_id BIGINT NOT NULL,
	PRIMARY KEY (role_id, dept_id),
	FOREIGN KEY(role_id) REFERENCES sys_role (id),
	FOREIGN KEY(dept_id) REFERENCES sys_dept (id)
)""")
    op.execute("""CREATE INDEX ix_sys_role_dept_dept_id ON sys_role_dept (dept_id)""")
    op.execute("""CREATE TABLE sys_role_permission (
	role_id BIGINT NOT NULL,
	permission_id BIGINT NOT NULL,
	PRIMARY KEY (role_id, permission_id),
	FOREIGN KEY(role_id) REFERENCES sys_role (id),
	FOREIGN KEY(permission_id) REFERENCES sys_permission (id)
)""")
    op.execute("""CREATE INDEX ix_sys_role_permission_permission_id ON sys_role_permission (permission_id)""")
    op.execute("""CREATE TABLE sys_user (
	id BIGSERIAL NOT NULL,
	username VARCHAR(64) NOT NULL,
	password_hash VARCHAR(128) NOT NULL,
	real_name VARCHAR(64) NOT NULL,
	dept_id BIGINT NOT NULL,
	phone VARCHAR(20),
	email VARCHAR(128),
	status CHAR(1) DEFAULT '0' NOT NULL CHECK (status IN ('0','1')),
	del_flag CHAR(1) DEFAULT '0' NOT NULL CHECK (del_flag IN ('0','1')),
	is_builtin CHAR(1) DEFAULT '0' NOT NULL CHECK (is_builtin IN ('0','1')),
	last_login_time TIMESTAMP WITH TIME ZONE,
	create_by BIGINT,
	update_by BIGINT,
	create_time TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	update_time TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (username),
	FOREIGN KEY(dept_id) REFERENCES sys_dept (id)
)""")
    op.execute("""CREATE INDEX ix_sys_user_dept_id ON sys_user (dept_id)""")
    op.execute("""CREATE TABLE sys_user_role (
	user_id BIGINT NOT NULL,
	role_id BIGINT NOT NULL,
	PRIMARY KEY (user_id, role_id),
	FOREIGN KEY(user_id) REFERENCES sys_user (id),
	FOREIGN KEY(role_id) REFERENCES sys_role (id)
)""")
    op.execute("""CREATE INDEX ix_sys_user_role_role_id ON sys_user_role (role_id)""")
    op.execute("""CREATE TABLE sys_user_session (
	id BIGSERIAL NOT NULL,
	user_id BIGINT NOT NULL,
	refresh_token_hash VARCHAR(64) NOT NULL,
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
	revoked_at TIMESTAMP WITH TIME ZONE,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	last_used_at TIMESTAMP WITH TIME ZONE,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES sys_user (id),
	UNIQUE (refresh_token_hash)
)""")
    op.execute("""CREATE INDEX ix_sys_user_session_user_id ON sys_user_session (user_id)""")


def downgrade():
    op.drop_table("sys_user_session")
    op.drop_table("sys_user_role")
    op.drop_table("sys_user")
    op.drop_table("sys_role_permission")
    op.drop_table("sys_role_dept")
    op.drop_table("sys_dict_data")
    op.drop_table("sys_role")
    op.drop_table("sys_permission")
    op.drop_table("sys_oper_log")
    op.drop_table("sys_dict_type")
    op.drop_table("sys_dept")
    op.drop_table("sys_config")
