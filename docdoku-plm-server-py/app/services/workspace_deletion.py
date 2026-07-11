"""工作区级联删除 — 对齐 Payara WorkspaceDAO.removeWorkspace + JPA cascade。

从 routers/workspaces.py 原地抽取，消除 admin.py 和 workspace_manager.py 中
删单行 workspace 的危险 stub（W-1/W-3）。
"""
import shutil
import logging
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.config import settings

logger = logging.getLogger(__name__)


def cascade_delete_workspace(db: Session, ws: str) -> None:
    """完整级联删除工作区：ES 索引 + DB 全表 + vault 磁盘目录。

    对齐 Payara:
      - deleteWorkspace:80  → customDeleteWorkspaceFolder (ES 索引)
      - WorkspaceDAO.removeWorkspace:106-200 → 各表 DELETE（REPLICA 模式关 FK）
      - deleteWorkspaceFolder（异步） → FileUtils.deleteDirectory
    """
    # ── ES 索引 ──
    try:
        from app.services.indexer_manager import indexer_manager
        indexer_manager.delete_index(ws)
    except Exception:
        pass

    # ── 完整级联删除 ──
    # SET LOCAL session_replication_role='replica' 关闭 FK 触发器，避免严格删除顺序要求；
    # 但仍按从叶到根的顺序删除，确保稳定性。
    db.execute(text("SET LOCAL session_replication_role='replica'"))

    # ── 0. 预先捕获未按 workspace 列定位的叶子表 ID ──
    # workflow 实例
    wf_rows = db.execute(text(
        "SELECT wf.id FROM workflow wf WHERE id IN ("
        "  SELECT workflow_id FROM partrevision WHERE workspace_id=:ws AND workflow_id IS NOT NULL UNION "
        "  SELECT workflow_id FROM documentrevision WHERE workspace_id=:ws AND workflow_id IS NOT NULL UNION "
        "  SELECT workflow_id FROM workspace_workflow WHERE workspace_id=:ws UNION "
        "  SELECT workflow_id FROM part_aborted_workflow WHERE partmaster_workspace_id=:ws UNION "
        "  SELECT workflow_id FROM document_aborted_workflow WHERE documentmaster_workspace_id=:ws)"
    ), {"ws": ws}).fetchall()
    wf_ids = [r[0] for r in wf_rows]

    # workflowmodel
    wfm_rows = db.execute(text(
        "SELECT id FROM workflowmodel WHERE workspace_id=:ws"
    ), {"ws": ws}).fetchall()
    wfm_ids = [r[0] for r in wfm_rows]

    # pathdatamaster
    pdm_rows = db.execute(text(
        "SELECT pm.id FROM pathdatamaster pm JOIN prdinstiteration_pathdatamstr lk "
        "ON lk.pathdatamaster_id=pm.id WHERE lk.workspace_id=:ws"
    ), {"ws": ws}).fetchall()
    pdm_ids = [r[0] for r in pdm_rows]

    # pathtopathlink
    ptl_rows = db.execute(text(
        "SELECT id FROM pathtopathlink WHERE id IN ("
        "  SELECT pathtopathlink_id FROM configurationitem_p2plink WHERE workspace_id=:ws UNION "
        "  SELECT pathtopathlink_id FROM productbaseline_p2plink p2 JOIN productbaseline pb "
        "    ON pb.id=p2.productbaseline_id WHERE pb.configurationitem_workspace_id=:ws UNION "
        "  SELECT pathtopathlink_id FROM prdinstiteration_p2plink WHERE workspace_id=:ws)"
    ), {"ws": ws}).fetchall()
    ptl_ids = [r[0] for r in ptl_rows]

    # instanceattribute
    ia_rows = db.execute(text(
        "SELECT ia.id FROM instanceattribute ia WHERE ia.id IN ("
        "  SELECT instanceattribute_id FROM partiteration_attribute WHERE workspace_id=:ws UNION "
        "  SELECT instanceattribute_id FROM documentiteration_attribute WHERE workspace_id=:ws UNION "
        "  SELECT instanceattribute_id FROM pathdataiteration_attribute pdia "
        "    JOIN pathdataiteration pdi ON pdia.pathdata_iteration=pdi.iteration AND pdia.pathdatamaster_id=pdi.pathdatamaster_id "
        "    WHERE pdi.pathdatamaster_id=ANY(:pdm_ids2) UNION "
        "  SELECT instanceattribute_id FROM prdinstiteration_attribute WHERE workspace_id=:ws"
        ")"
    ), {"ws": ws, "pdm_ids2": pdm_ids if pdm_ids else [0]}).fetchall()
    ia_ids = [r[0] for r in ia_rows]

    # queryrule
    qr_rows = db.execute(text(
        "WITH RECURSIVE rtree AS ("
        "  SELECT qr.qid FROM queryrule qr"
        "  JOIN query q ON q.queryrule_id=qr.qid OR q.pathdata_queryrule_id=qr.qid"
        "  WHERE q.author_workspace_id=:ws"
        "  UNION SELECT child.qid FROM queryrule child JOIN rtree rt ON child.parent_query_rule=rt.qid"
        ") SELECT DISTINCT qid FROM rtree"
    ), {"ws": ws}).fetchall()
    qr_ids = [r[0] for r in qr_rows]

    def _del(sql, **params):
        db.execute(text(sql), params)

    # ── 1. workflow 子系统 ──
    if wf_ids:
        _del("DELETE FROM task_user WHERE activity_step||'/'||workflow_id IN (SELECT step||'/'||CAST(id AS TEXT) FROM activity WHERE workflow_id=ANY(:ids))", ids=wf_ids)
        _del("DELETE FROM task_usergroup WHERE activity_step||'/'||workflow_id IN (SELECT step||'/'||CAST(id AS TEXT) FROM activity WHERE workflow_id=ANY(:ids))", ids=wf_ids)
        _del("DELETE FROM task WHERE activity_step IN (SELECT step FROM activity WHERE workflow_id=ANY(:ids)) AND workflow_id=ANY(:ids)", ids=wf_ids)
        _del("DELETE FROM activity_relaunch WHERE activity_step IN (SELECT step FROM activity WHERE workflow_id=ANY(:ids)) AND activity_workflow_id=ANY(:ids)", ids=wf_ids)
        _del("DELETE FROM activity WHERE workflow_id=ANY(:ids)", ids=wf_ids)
        _del("DELETE FROM workspace_aborted_workflow WHERE workflow_id=ANY(:ids)", ids=wf_ids)
        _del("DELETE FROM part_aborted_workflow WHERE partmaster_workspace_id=:ws", ws=ws)
        _del("DELETE FROM document_aborted_workflow WHERE documentmaster_workspace_id=:ws", ws=ws)
        _del("DELETE FROM workflow WHERE id=ANY(:ids)", ids=wf_ids)
    _del("DELETE FROM workspace_workflow WHERE workspace_id=:ws", ws=ws)

    if wfm_ids:
        _del("DELETE FROM task_user WHERE activity_step||'/'||workflow_id IN (SELECT step||'/'||CAST(workflow_id AS TEXT) FROM activity WHERE workflow_id IN (SELECT id FROM workflow WHERE id IN (SELECT workflow_id FROM workspace_workflow WHERE workspace_id=:ws)))", ws=ws)
        _del("DELETE FROM task_usergroup WHERE activity_step||'/'||workflow_id IN (SELECT step||'/'||CAST(workflow_id AS TEXT) FROM activity WHERE workflow_id IN (SELECT id FROM workflow WHERE id IN (SELECT workflow_id FROM workspace_workflow WHERE workspace_id=:ws)))", ws=ws)
        _del("DELETE FROM task WHERE activity_step IN (SELECT step FROM activity WHERE workflow_id IN (SELECT id FROM workflow WHERE id IN (SELECT workflow_id FROM workspace_workflow WHERE workspace_id=:ws)))", ws=ws)
        _del("DELETE FROM activity_relaunch WHERE activity_step IN (SELECT step FROM activity WHERE workflow_id IN (SELECT id FROM workflow WHERE id IN (SELECT workflow_id FROM workspace_workflow WHERE workspace_id=:ws)))", ws=ws)
        _del("DELETE FROM activity WHERE workflow_id IN (SELECT id FROM workflow WHERE id IN (SELECT workflow_id FROM workspace_workflow WHERE workspace_id=:ws))", ws=ws)
        _del("DELETE FROM taskmodel WHERE activitymodel_id IN (SELECT id FROM activitymodel WHERE workflowmodel_id=ANY(:ids))", ids=wfm_ids)
        _del("DELETE FROM activitymodel_relaunch WHERE activitymodel_id IN (SELECT id FROM activitymodel WHERE workflowmodel_id=ANY(:ids))", ids=wfm_ids)
        _del("DELETE FROM activitymodel WHERE workflowmodel_id=ANY(:ids)", ids=wfm_ids)
        _del("DELETE FROM workflowmodel WHERE workspace_id=:ws", ws=ws)

    # ── 2. PathData 叶子表 → P2P → CI 子表 ──
    if pdm_ids:
        _del("DELETE FROM pathdataiteration_attribute WHERE pathdata_iteration IN (SELECT iteration FROM pathdataiteration WHERE pathdatamaster_id=ANY(:ids)) AND pathdatamaster_id=ANY(:ids)", ids=pdm_ids)
        _del("DELETE FROM pathdataiteration_documentlink WHERE pathdata_iteration IN (SELECT iteration FROM pathdataiteration WHERE pathdatamaster_id=ANY(:ids)) and pathdatamaster_id=ANY(:ids)", ids=pdm_ids)
        _del("DELETE FROM pathdataiteration_binres WHERE pathdatamaster_id=ANY(:ids)", ids=pdm_ids)
        _del("DELETE FROM pathdataiteration WHERE pathdatamaster_id=ANY(:ids)", ids=pdm_ids)
        _del("DELETE FROM prdinstiteration_pathdatamstr WHERE workspace_id=:ws", ws=ws)
        _del("DELETE FROM pathdatamaster WHERE id=ANY(:ids)", ids=pdm_ids)
    if ptl_ids:
        _del("DELETE FROM prdinstiteration_p2plink WHERE pathtopathlink_id=ANY(:ids)", ids=ptl_ids)
        _del("DELETE FROM productbaseline_p2plink WHERE pathtopathlink_id=ANY(:ids)", ids=ptl_ids)
        _del("DELETE FROM configurationitem_p2plink WHERE workspace_id=:ws", ws=ws)
        _del("DELETE FROM pathtopathlink WHERE id=ANY(:ids)", ids=ptl_ids)

    # ── 3. 变更管理 ──
    _del("DELETE FROM changeissue_affected_part WHERE changeissue_id IN (SELECT id FROM changeissue WHERE workspace_id=:ws)", ws=ws)
    _del("DELETE FROM changeissue_affected_document WHERE changeissue_id IN (SELECT id FROM changeissue WHERE workspace_id=:ws)", ws=ws)
    _del("DELETE FROM changeissue_tag WHERE changeissue_id IN (SELECT id FROM changeissue WHERE workspace_id=:ws)", ws=ws)
    _del("DELETE FROM changerequest_changeissue WHERE changerequest_id IN (SELECT id FROM changerequest WHERE workspace_id=:ws)", ws=ws)
    _del("DELETE FROM changerequest_changeissue WHERE changeissue_id IN (SELECT id FROM changeissue WHERE workspace_id=:ws)", ws=ws)
    _del("DELETE FROM changeorder_changerequest WHERE changeorder_id IN (SELECT id FROM changeorder WHERE workspace_id=:ws)", ws=ws)
    _del("DELETE FROM changeorder_changerequest WHERE changerequest_id IN (SELECT id FROM changerequest WHERE workspace_id=:ws)", ws=ws)
    _del("DELETE FROM changeorder_affected_part WHERE changeorder_id IN (SELECT id FROM changeorder WHERE workspace_id=:ws)", ws=ws)
    _del("DELETE FROM changeorder_affected_document WHERE changeorder_id IN (SELECT id FROM changeorder WHERE workspace_id=:ws)", ws=ws)
    _del("DELETE FROM changeorder_tag WHERE changeorder_id IN (SELECT id FROM changeorder WHERE workspace_id=:ws)", ws=ws)
    _del("DELETE FROM changereq_affected_part WHERE changerequest_id IN (SELECT id FROM changerequest WHERE workspace_id=:ws)", ws=ws)
    _del("DELETE FROM changereq_affected_document WHERE changerequest_id IN (SELECT id FROM changerequest WHERE workspace_id=:ws)", ws=ws)
    _del("DELETE FROM changerequest_tag WHERE changerequest_id IN (SELECT id FROM changerequest WHERE workspace_id=:ws)", ws=ws)
    _del("DELETE FROM changeissue WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM changerequest WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM changeorder WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM milestone WHERE workspace_id=:ws", ws=ws)

    # ── 4. 产品实例 / 基线 / 配置项 ──
    _del("DELETE FROM prdinstanceiteration_optlink WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM prdinstanceiteration_sublink WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM prdinstiteration_documentlink WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM prdinstiteration_binres WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM prdinstiteration_attribute WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM productinstanceiteration WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM productinstancemaster WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM productbaseline_optionallink WHERE productbaseline_id IN (SELECT id FROM productbaseline WHERE configurationitem_workspace_id=:ws)", ws=ws)
    _del("DELETE FROM productbaseline_substitutelink WHERE productbaseline_id IN (SELECT id FROM productbaseline WHERE configurationitem_workspace_id=:ws)", ws=ws)
    _del("DELETE FROM prdcfg_optionallink WHERE productbaseline_id IN (SELECT id FROM productbaseline WHERE configurationitem_workspace_id=:ws)", ws=ws)
    _del("DELETE FROM prdcfg_substitutelink WHERE productbaseline_id IN (SELECT id FROM productbaseline WHERE configurationitem_workspace_id=:ws)", ws=ws)
    _del("DELETE FROM productconfiguration WHERE configurationitem_workspace_id=:ws", ws=ws)
    _del("DELETE FROM productbaseline WHERE configurationitem_workspace_id=:ws", ws=ws)
    _del("DELETE FROM effectivity WHERE configurationitem_id IN (SELECT id FROM configurationitem WHERE workspace_id=:ws)", ws=ws)
    _del("DELETE FROM partrevision_effectivity WHERE partmaster_workspace_id=:ws", ws=ws)
    _del("DELETE FROM layer WHERE configurationitem_workspace_id=:ws", ws=ws)
    _del("DELETE FROM configurationitem WHERE workspace_id=:ws", ws=ws)

    # ── 5. 模板 ──
    iat_rows = db.execute(text(
        "SELECT instanceattributetemplate_id FROM partmastertemplate_attr WHERE workspace_id=:ws "
        "UNION SELECT instanceattributetemplate_id FROM documentmastertemplate_attr WHERE workspace_id=:ws "
        "UNION SELECT instanceattribute_template_id FROM partiteration_pathdata_attr WHERE workspace_id=:ws"
    ), {"ws": ws}).fetchall()
    iat_ids = [r[0] for r in iat_rows if r[0] is not None]
    _del("DELETE FROM partmastertemplate_attr WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM partmastertemplate WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM documentmastertemplate_attr WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM documentmastertemplate_binres WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM documentmastertemplate WHERE workspace_id=:ws", ws=ws)

    # ── 6. 零件子表 ──
    _del("DELETE FROM partiteration_pathdata_attr WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM partiteration_attribute WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM partiteration_documentlink WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM partiteration_binres WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM partiteration_geometry WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM partiteration_partusagelink WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM partrevision_tag WHERE partmaster_workspace_id=:ws", ws=ws)
    _del("DELETE FROM baselinedpart WHERE target_workspace_id=:ws", ws=ws)
    _del("DELETE FROM conversion WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM modificationnotification WHERE impacted_workspace_id=:ws OR modified_workspace_id=:ws", ws=ws)
    _del("DELETE FROM partsubstitutelink WHERE substitute_workspace_id=:ws", ws=ws)
    _del("DELETE FROM partusagelink WHERE component_workspace_id=:ws", ws=ws)
    _del("DELETE FROM partiteration WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM partrevision WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM partmaster_alternate WHERE partmaster_workspace_id=:ws OR alternate_workspace_id=:ws", ws=ws)
    _del("DELETE FROM partmaster WHERE workspace_id=:ws", ws=ws)

    # ── 7. 文档子表 ──
    _del("DELETE FROM documentiteration_attribute WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM documentiteration_documentlink WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM documentiteration_binres WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM baselineddocument WHERE target_workspace_id=:ws", ws=ws)
    _del("DELETE FROM documentrevision_tag WHERE documentmaster_workspace_id=:ws", ws=ws)
    _del("DELETE FROM documentlink WHERE target_workspace_id=:ws", ws=ws)
    _del("DELETE FROM documentiteration WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM documentrevision WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM documentmaster WHERE workspace_id=:ws", ws=ws)

    # ── 8. 订阅 / shared entity / marker / collection ──
    _del("DELETE FROM iterationchangesubscription WHERE documentmaster_workspace_id=:ws OR subscriber_workspace_id=:ws", ws=ws)
    _del("DELETE FROM statechangesubscription WHERE documentmaster_workspace_id=:ws OR subscriber_workspace_id=:ws", ws=ws)
    _del("DELETE FROM tagusersubscription WHERE subscriber_workspace_id=:ws OR tag_workspace_id=:ws", ws=ws)
    _del("DELETE FROM tagusergroupsubscription WHERE subscriber_workspace_id=:ws OR tag_workspace_id=:ws", ws=ws)
    _del("DELETE FROM sharedentity WHERE entity_workspace_id=:ws OR author_workspace_id=:ws", ws=ws)
    _del("DELETE FROM marker_partmaster WHERE relatedpart_workspace_id=:ws OR relatedpart_partnumber IN (SELECT partmaster_partnumber FROM partrevision WHERE workspace_id=:ws)", ws=ws)
    _del("DELETE FROM marker WHERE author_workspace_id=:ws", ws=ws)
    _del("DELETE FROM partcollection WHERE author_workspace_id=:ws", ws=ws)
    _del("DELETE FROM documentcollection WHERE author_workspace_id=:ws", ws=ws)
    _del("DELETE FROM documentbaseline WHERE author_workspace_id=:ws", ws=ws)

    # ── 9. instanceattribute + instanceattributetemplate ──
    if ia_ids:
        _del("DELETE FROM instanceattribute WHERE id=ANY(:ids)", ids=ia_ids)
    if iat_ids:
        _del("DELETE FROM instanceattributetemplate WHERE id=ANY(:ids)", ids=iat_ids)
    _del("DELETE FROM instanceattributetemplate WHERE lov_workspace_id=:ws", ws=ws)

    # ── 10. 标签 ──
    _del("DELETE FROM tag WHERE workspace_id=:ws", ws=ws)

    # ── 11. LOV ──
    _del("DELETE FROM lov_namevalue WHERE lov_workspace_id=:ws", ws=ws)
    _del("DELETE FROM lov WHERE workspace_id=:ws", ws=ws)

    # ── 12. 查询 ──
    if qr_ids:
        _del("DELETE FROM queryrule_values WHERE queryrule_id=ANY(:ids)", ids=qr_ids)
        _del("DELETE FROM queryrule WHERE qid=ANY(:ids)", ids=qr_ids)
    _del("DELETE FROM querycontext WHERE workspaceid=:ws", ws=ws)
    _del("DELETE FROM query_selects WHERE query_id IN (SELECT id FROM query WHERE author_workspace_id=:ws)", ws=ws)
    _del("DELETE FROM query_order_by WHERE query_id IN (SELECT id FROM query WHERE author_workspace_id=:ws)", ws=ws)
    _del("DELETE FROM query_grouped_by WHERE query_id IN (SELECT id FROM query WHERE author_workspace_id=:ws)", ws=ws)
    _del("DELETE FROM query WHERE author_workspace_id=:ws", ws=ws)

    # ── 13. Import 记录 ──
    _del("DELETE FROM import_error WHERE import_id IN (SELECT id FROM import WHERE user_workspace_id=:ws)", ws=ws)
    _del("DELETE FROM import_warning WHERE import_id IN (SELECT id FROM import WHERE user_workspace_id=:ws)", ws=ws)
    _del("DELETE FROM import WHERE user_workspace_id=:ws", ws=ws)

    # ── 14. 角色 ──
    _del("DELETE FROM role_user WHERE role_workspace_id=:ws OR user_workspace_id=:ws", ws=ws)
    _del("DELETE FROM role_usergroup WHERE role_workspace_id=:ws OR usergroup_workspace_id=:ws", ws=ws)
    _del("DELETE FROM role WHERE workspace_id=:ws", ws=ws)

    # ── 15. 用户 / 组 / 成员关系 ──
    _del("DELETE FROM acluserentry WHERE principal_workspace_id=:ws", ws=ws)
    _del("DELETE FROM aclusergroupentry WHERE principal_workspace_id=:ws", ws=ws)
    _del("DELETE FROM usergroup_user WHERE usergroup_id_workspace_id=:ws OR user_workspace_id=:ws", ws=ws)
    _del("DELETE FROM userdata WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM workspaceusermembership WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM workspaceusergroupmembership WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM usergroup WHERE workspace_id=:ws", ws=ws)

    # ── 16. 剩余工作区级配置 ──
    _del("DELETE FROM webhook WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM workspacebackoptions WHERE workspace_id=:ws", ws=ws)
    _del("DELETE FROM workspacefrontoptions WHERE workspace_id=:ws", ws=ws)

    # ── 16b. BinaryResource DB 行 ──
    br_prefix = ws.replace("_", "\\_").replace("%", "\\%") + "/%"
    _del("DELETE FROM binaryresource WHERE fullname LIKE :p ESCAPE '\\'", p=br_prefix)

    # ── 17. 工作区本身 ──
    db.execute(text("DELETE FROM workspace WHERE id = :id"), {"id": ws})

    db.execute(text("SET LOCAL session_replication_role='origin'"))
    db.commit()

    # ── 18. vault 磁盘文件夹 ──
    try:
        vault_dir = Path(settings.VAULT_PATH) / ws
        if vault_dir.exists():
            shutil.rmtree(vault_dir, ignore_errors=True)
    except Exception as e:
        logger.warning(
            "删除工作区 %s 的 vault 文件夹失败（DB 已删除，不影响一致性）: %s", ws, e)
