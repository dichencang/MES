"""Create basic-data tables and seed module reference data."""

from alembic import op

from app.models.basic_seed import seed_statements

revision = "0003_basic_data"
down_revision = "0002_session_rotation"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE basic_material (
	id BIGSERIAL NOT NULL, 
	code VARCHAR(50) NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	category_code VARCHAR(64) NOT NULL, 
	unit_code VARCHAR(64) NOT NULL, 
	category_dict_code VARCHAR(64) GENERATED ALWAYS AS ('material_category') STORED NOT NULL, 
	unit_dict_code VARCHAR(64) GENERATED ALWAYS AS ('material_unit') STORED NOT NULL, 
	spec VARCHAR(100), 
	remark VARCHAR(200), 
	status CHAR(1) DEFAULT '0' NOT NULL CHECK (status IN ('0','1')), 
	is_product BOOLEAN NOT NULL, 
	bom_max_version INTEGER DEFAULT '0' NOT NULL, 
	routing_max_version INTEGER DEFAULT '0' NOT NULL, 
	PRIMARY KEY (id), 
	CHECK (code ~ '^[A-Za-z0-9_-]+$'), 
	CHECK (bom_max_version >= 0 AND routing_max_version >= 0), 
	FOREIGN KEY(category_dict_code, category_code) REFERENCES sys_dict_data (dict_code, dict_value) ON DELETE RESTRICT ON UPDATE RESTRICT, 
	FOREIGN KEY(unit_dict_code, unit_code) REFERENCES sys_dict_data (dict_code, dict_value) ON DELETE RESTRICT ON UPDATE RESTRICT, 
	UNIQUE (code)
)""")
    op.execute("""CREATE TABLE basic_process (
	id BIGSERIAL NOT NULL, 
	code VARCHAR(50) NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	description VARCHAR(200), 
	status CHAR(1) DEFAULT '0' NOT NULL CHECK (status IN ('0','1')), 
	PRIMARY KEY (id), 
	CHECK (code ~ '^[A-Za-z0-9_-]+$'), 
	UNIQUE (code)
)""")
    op.execute("""CREATE TABLE basic_bom (
	id BIGSERIAL NOT NULL, 
	product_id BIGINT NOT NULL, 
	version INTEGER NOT NULL, 
	status CHAR(1) DEFAULT '0' NOT NULL, 
	draft_token UUID, 
	create_time TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	update_time TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	last_editor_id BIGINT NOT NULL, 
	published_at TIMESTAMP WITH TIME ZONE, 
	publisher_id BIGINT, 
	base_qty NUMERIC(18, 4) DEFAULT '1.0000' NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (product_id, version), 
	CHECK (version > 0), 
	CHECK (status IN ('0', '1', '2')), 
	CHECK ((status = '0' AND draft_token IS NOT NULL AND published_at IS NULL AND publisher_id IS NULL) OR (status IN ('1', '2') AND draft_token IS NULL AND published_at IS NOT NULL AND publisher_id IS NOT NULL)), 
	FOREIGN KEY(product_id) REFERENCES basic_material (id) ON DELETE RESTRICT, 
	FOREIGN KEY(last_editor_id) REFERENCES sys_user (id) ON DELETE RESTRICT, 
	FOREIGN KEY(publisher_id) REFERENCES sys_user (id) ON DELETE RESTRICT
)""")
    op.execute("""CREATE UNIQUE INDEX uq_basic_bom_active_product ON basic_bom (product_id) WHERE status = '1'""")
    op.execute("""CREATE TABLE basic_routing (
	id BIGSERIAL NOT NULL, 
	product_id BIGINT NOT NULL, 
	version INTEGER NOT NULL, 
	status CHAR(1) DEFAULT '0' NOT NULL, 
	draft_token UUID, 
	create_time TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	update_time TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	last_editor_id BIGINT NOT NULL, 
	published_at TIMESTAMP WITH TIME ZONE, 
	publisher_id BIGINT, 
	PRIMARY KEY (id), 
	UNIQUE (product_id, version), 
	CHECK (version > 0), 
	CHECK (status IN ('0', '1', '2')), 
	CHECK ((status = '0' AND draft_token IS NOT NULL AND published_at IS NULL AND publisher_id IS NULL) OR (status IN ('1', '2') AND draft_token IS NULL AND published_at IS NOT NULL AND publisher_id IS NOT NULL)), 
	FOREIGN KEY(product_id) REFERENCES basic_material (id) ON DELETE RESTRICT, 
	FOREIGN KEY(last_editor_id) REFERENCES sys_user (id) ON DELETE RESTRICT, 
	FOREIGN KEY(publisher_id) REFERENCES sys_user (id) ON DELETE RESTRICT
)""")
    op.execute("""CREATE UNIQUE INDEX uq_basic_routing_active_product ON basic_routing (product_id) WHERE status = '1'""")
    op.execute("""CREATE TABLE basic_bom_item (
	id BIGSERIAL NOT NULL, 
	bom_id BIGINT NOT NULL, 
	material_id BIGINT NOT NULL, 
	qty NUMERIC(18, 4) NOT NULL, 
	sort_no INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	CHECK (sort_no > 0), 
	FOREIGN KEY(bom_id) REFERENCES basic_bom (id) ON DELETE CASCADE, 
	FOREIGN KEY(material_id) REFERENCES basic_material (id) ON DELETE RESTRICT
)""")
    op.execute("""CREATE INDEX ix_basic_bom_item_material_id ON basic_bom_item (material_id)""")
    op.execute("""CREATE INDEX ix_basic_bom_item_order ON basic_bom_item (bom_id, sort_no, id)""")
    op.execute("""CREATE TABLE basic_routing_step (
	id BIGSERIAL NOT NULL, 
	routing_id BIGINT NOT NULL, 
	process_id BIGINT NOT NULL, 
	seq INTEGER NOT NULL, 
	remark VARCHAR(200), 
	PRIMARY KEY (id), 
	FOREIGN KEY(routing_id) REFERENCES basic_routing (id) ON DELETE CASCADE, 
	FOREIGN KEY(process_id) REFERENCES basic_process (id) ON DELETE RESTRICT
)""")
    op.execute("""CREATE INDEX ix_basic_routing_step_order ON basic_routing_step (routing_id, seq, id)""")
    op.execute("""CREATE INDEX ix_basic_routing_step_process_id ON basic_routing_step (process_id)""")
    for statement in seed_statements():
        op.execute(statement)


def downgrade():
    # Keep shared permissions and dictionary entries, including user customizations.
    op.drop_table("basic_routing_step")
    op.drop_table("basic_bom_item")
    op.drop_table("basic_routing")
    op.drop_table("basic_bom")
    op.drop_table("basic_process")
    op.drop_table("basic_material")
