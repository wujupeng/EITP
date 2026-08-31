"""WMS 空间管理表 - 仓库/库区/区域/库位/料箱/设备。

Revision ID: 030
Revises: 027
Create Date: 2026-08-31
"""

from __future__ import annotations

from alembic import op

revision = "030"
down_revision = "027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE TABLE wms_warehouse ("
        "    warehouse_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
        "    tenant_id             UUID NOT NULL,"
        "    hierarchy_node_id     UUID,"
        "    warehouse_code        VARCHAR(64) NOT NULL,"
        "    warehouse_name        VARCHAR(256) NOT NULL,"
        "    address               VARCHAR(512),"
        "    wms_config            JSONB NOT NULL DEFAULT '{}'::jsonb,"
        "    status                VARCHAR(10) NOT NULL DEFAULT 'active',"
        "    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    CONSTRAINT uk_wms_warehouse_code UNIQUE (tenant_id, warehouse_code),"
        "    CONSTRAINT chk_wms_warehouse_status CHECK (status IN ('active', 'disabled'))"
        ")"
    )
    op.execute("CREATE INDEX idx_wms_warehouse_tenant_status ON wms_warehouse (tenant_id, status)")

    op.execute(
        "CREATE TABLE wms_zone ("
        "    zone_id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
        "    tenant_id             UUID NOT NULL,"
        "    warehouse_id          UUID NOT NULL REFERENCES wms_warehouse(warehouse_id),"
        "    zone_code             VARCHAR(64) NOT NULL,"
        "    zone_name             VARCHAR(256) NOT NULL,"
        "    zone_function         VARCHAR(16) NOT NULL DEFAULT 'storage',"
        "    status                VARCHAR(10) NOT NULL DEFAULT 'active',"
        "    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    CONSTRAINT uk_wms_zone_code UNIQUE (tenant_id, warehouse_id, zone_code),"
        "    CONSTRAINT chk_wms_zone_function CHECK (zone_function IN ('receiving','storage','picking','shipping','qc','blocked')),"
        "    CONSTRAINT chk_wms_zone_status CHECK (status IN ('active','disabled'))"
        ")"
    )
    op.execute("CREATE INDEX idx_wms_zone_warehouse ON wms_zone (tenant_id, warehouse_id)")
    op.execute("CREATE INDEX idx_wms_zone_function ON wms_zone (tenant_id, zone_function, status)")

    op.execute(
        "CREATE TABLE wms_area ("
        "    area_id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
        "    tenant_id             UUID NOT NULL,"
        "    zone_id               UUID NOT NULL REFERENCES wms_zone(zone_id),"
        "    area_code             VARCHAR(64) NOT NULL,"
        "    area_name             VARCHAR(256) NOT NULL,"
        "    status                VARCHAR(10) NOT NULL DEFAULT 'active',"
        "    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    CONSTRAINT uk_wms_area_code UNIQUE (tenant_id, zone_id, area_code),"
        "    CONSTRAINT chk_wms_area_status CHECK (status IN ('active','disabled'))"
        ")"
    )
    op.execute("CREATE INDEX idx_wms_area_zone ON wms_area (tenant_id, zone_id)")

    op.execute(
        "CREATE TABLE wms_location ("
        "    location_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
        "    tenant_id             UUID NOT NULL,"
        "    warehouse_id          UUID NOT NULL REFERENCES wms_warehouse(warehouse_id),"
        "    zone_id               UUID NOT NULL REFERENCES wms_zone(zone_id),"
        "    area_id               UUID REFERENCES wms_area(area_id),"
        "    location_code         VARCHAR(64) NOT NULL,"
        "    location_type         VARCHAR(16) NOT NULL DEFAULT 'shelf',"
        "    capacity_max_qty      NUMERIC(18,6),"
        "    capacity_max_weight   NUMERIC(18,6),"
        "    capacity_max_volume   NUMERIC(18,6),"
        "    capacity_enforce_mode VARCHAR(8) NOT NULL DEFAULT 'reject',"
        "    coordinate_x          NUMERIC(18,6),"
        "    coordinate_y          NUMERIC(18,6),"
        "    coordinate_z          NUMERIC(18,6),"
        "    status                VARCHAR(10) NOT NULL DEFAULT 'active',"
        "    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    CONSTRAINT uk_wms_location_code UNIQUE (tenant_id, warehouse_id, location_code),"
        "    CONSTRAINT chk_wms_location_type CHECK (location_type IN ('floor','shelf','cold','frozen')),"
        "    CONSTRAINT chk_wms_location_enforce CHECK (capacity_enforce_mode IN ('warn','reject')),"
        "    CONSTRAINT chk_wms_location_status CHECK (status IN ('active','disabled'))"
        ")"
    )
    op.execute("CREATE INDEX idx_wms_location_zone ON wms_location (tenant_id, zone_id)")
    op.execute("CREATE INDEX idx_wms_location_wh_status ON wms_location (tenant_id, warehouse_id, status)")
    op.execute("CREATE INDEX idx_wms_location_area ON wms_location (tenant_id, area_id)")

    op.execute(
        "CREATE TABLE wms_bin ("
        "    bin_id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
        "    tenant_id             UUID NOT NULL,"
        "    location_id           UUID NOT NULL REFERENCES wms_location(location_id),"
        "    bin_code              VARCHAR(64) NOT NULL,"
        "    status                VARCHAR(10) NOT NULL DEFAULT 'active',"
        "    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    CONSTRAINT uk_wms_bin_code UNIQUE (tenant_id, location_id, bin_code),"
        "    CONSTRAINT chk_wms_bin_status CHECK (status IN ('active','inactive'))"
        ")"
    )
    op.execute("CREATE INDEX idx_wms_bin_location ON wms_bin (tenant_id, location_id)")

    op.execute(
        "CREATE TABLE wms_equipment ("
        "    equipment_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
        "    tenant_id             UUID NOT NULL,"
        "    warehouse_id          UUID NOT NULL REFERENCES wms_warehouse(warehouse_id),"
        "    equipment_code        VARCHAR(64) NOT NULL,"
        "    equipment_type        VARCHAR(16) NOT NULL DEFAULT 'forklift',"
        "    status                VARCHAR(16) NOT NULL DEFAULT 'active',"
        "    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    CONSTRAINT uk_wms_equipment_code UNIQUE (tenant_id, warehouse_id, equipment_code),"
        "    CONSTRAINT chk_wms_equipment_type CHECK (equipment_type IN ('forklift','pda','scanner','conveyor','agv')),"
        "    CONSTRAINT chk_wms_equipment_status CHECK (status IN ('active','inactive','maintenance'))"
        ")"
    )
    op.execute("CREATE INDEX idx_wms_equipment_warehouse ON wms_equipment (tenant_id, warehouse_id, status)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS wms_equipment CASCADE")
    op.execute("DROP TABLE IF EXISTS wms_bin CASCADE")
    op.execute("DROP TABLE IF EXISTS wms_location CASCADE")
    op.execute("DROP TABLE IF EXISTS wms_area CASCADE")
    op.execute("DROP TABLE IF EXISTS wms_zone CASCADE")
    op.execute("DROP TABLE IF EXISTS wms_warehouse CASCADE")