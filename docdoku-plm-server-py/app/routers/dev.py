"""开发调试端点（仅开发环境使用）。

GET  /dev/errors          — 查看最近 4xx/5xx 错误列表
GET  /dev/errors?limit=N  — 限制条数
GET  /dev/errors?min=500  — 只看 5xx
DELETE /dev/errors        — 清空
"""
from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse, JSONResponse
from app.core.error_collector import get_errors, clear

router = APIRouter(prefix="/dev", tags=["dev"])


@router.get("/errors", response_class=HTMLResponse)
def dev_errors(
    limit: int = Query(100, ge=1, le=500),
    min_status: int = Query(400, alias="min"),
    fmt: str = Query("html"),
):
    """以 HTML 表格或 JSON 返回最近错误记录。"""
    errors = get_errors(limit=limit, min_status=min_status)

    if fmt == "json":
        return JSONResponse(errors)

    # HTML 表格视图（方便直接在浏览器查看）
    rows = ""
    for e in errors:
        status_color = "#c00" if e["status"] >= 500 else "#e60"
        req_escaped = (e["req"] or "").replace("<", "&lt;").replace(">", "&gt;")
        res_escaped = (e["res"] or "").replace("<", "&lt;").replace(">", "&gt;")
        rows += f"""
        <tr>
          <td style="color:{status_color};font-weight:bold">{e["status"]}</td>
          <td><code>{e["method"]}</code></td>
          <td style="word-break:break-all;max-width:350px"><code>{e["url"]}</code></td>
          <td>{e["user"]}</td>
          <td>{e["ts"]}</td>
          <td><pre style="max-width:250px;overflow:auto;font-size:11px">{req_escaped}</pre></td>
          <td><pre style="max-width:250px;overflow:auto;font-size:11px">{res_escaped}</pre></td>
        </tr>"""

    count_badge = f'<span style="background:#888;color:#fff;padding:2px 8px;border-radius:4px">{len(errors)} 条</span>'
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>API Error Log</title>
<style>
  body {{font-family:monospace;font-size:12px;margin:16px;background:#1e1e1e;color:#ccc}}
  h2 {{color:#fff}} a {{color:#7af}} table {{border-collapse:collapse;width:100%}}
  th {{background:#333;color:#fff;padding:6px 8px;text-align:left}}
  td {{border-bottom:1px solid #333;padding:5px 8px;vertical-align:top}}
  tr:hover td {{background:#2a2a2a}}
  pre {{margin:0;white-space:pre-wrap;word-break:break-all}}
  .toolbar {{margin-bottom:12px}}
</style>
</head><body>
<h2>API Error Log {count_badge}</h2>
<div class="toolbar">
  <a href="/dev/errors?min=400">全部 4xx/5xx</a> |
  <a href="/dev/errors?min=500">仅 5xx</a> |
  <a href="/dev/errors?fmt=json">JSON</a> |
  <a href="#" onclick="fetch('/dev/errors',{{method:'DELETE'}}).then(()=>location.reload())">清空</a>
  <span style="margin-left:16px;color:#888">自动刷新：</span>
  <a href="#" onclick="setInterval(()=>location.reload(),3000);return false">每3s</a>
</div>
<table>
  <thead><tr>
    <th>状态</th><th>方法</th><th>URL</th><th>用户</th><th>时间</th>
    <th>请求体</th><th>响应体</th>
  </tr></thead>
  <tbody>{rows if rows else '<tr><td colspan=7 style="text-align:center;padding:24px;color:#666">暂无错误记录</td></tr>'}</tbody>
</table>
</body></html>"""
    return html


@router.delete("/errors")
def clear_errors():
    """清空错误记录。"""
    clear()
    return {"cleared": True}
