"""Portable browser execution adapter. Shared by any agent that can invoke Python."""
from __future__ import annotations
import argparse
import base64
import contextlib
import io
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENDOR = ROOT / "vendor" / "douyin-skills-09e9ccb6c484c59d69e11dbb4bc975c47e5510e5"
STATE = Path(os.environ.get("DOUYIN_AGENT_HOME", ROOT / "data")).resolve()
os.environ["DOUYIN_SKILLS_HOME"] = str(STATE / "browser")
if not os.environ.get("CHROME_BIN"):
    for candidate in [Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"), Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")]:
        if candidate.is_file():
            os.environ["CHROME_BIN"] = str(candidate)
            break
local_node = ROOT / 'runtime' / 'node' / ('node.exe' if os.name == 'nt' else 'bin/node')
if local_node.is_file():
    os.environ['PATH'] = str(local_node.parent) + os.pathsep + os.environ.get('PATH', '')
sys.path.insert(0, str(VENDOR / "scripts"))
import cli as upstream
from local_state import file_lock
from platform_adapter import get_default_adapter


def invoke(arguments):
    """No background update worker; stdout stays one JSON result."""
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        try:
            upstream.main(arguments, background_updates=False)
        except SystemExit:
            pass
    return json.loads(buffer.getvalue())


def connect(target=None, headed=False, fresh=False):
    args = argparse.Namespace(host="127.0.0.1", port=19323, account="", target_id=target, headed=headed, command="operator")
    browser,page = upstream._connect(args)
    return browser.new_page() if fresh else page


def browser_lock():
    return file_lock(STATE / "browser-action.lock")


def screenshot(page, name='browser.png'):
    from browser_runtime import _run_node
    result=_run_node('screenshot',{'host':page.host,'port':page.port,'targetId':page.target_id})
    STATE.mkdir(parents=True,exist_ok=True)
    path=STATE/name
    path.write_bytes(base64.b64decode(result['data'],validate=True))
    return str(path)


def snapshot(page):
    """Expose visible UI only. IDs are attached to DOM elements for later native input."""
    return page.evaluate(r'''(() => {
      const visible = el => !!(el && (el.offsetWidth || el.offsetHeight || el.getClientRects().length));
      const token = Math.random().toString(36).slice(2,10);
      const primary = Array.from(document.querySelectorAll('button, a, input, textarea, select, [role="button"], [role="radio"], [role="checkbox"], [role="combobox"], [contenteditable="true"], label')).filter(visible);
      const names = new Set(['登录','扫码登录','自主声明','内容由AI生成','内容由 AI 生成','确定','公开','选择封面','回复','保存','取消','仅自己可见']);
      const extra = Array.from(document.querySelectorAll('div,span')).filter(e=>visible(e)&&names.has((e.innerText||'').trim())&&!e.closest('button,a,label,[role="button"]')&&!Array.from(e.children).some(c=>(c.innerText||'').trim()===(e.innerText||'').trim()));
      const nodes = Array.from(new Set([...primary,...extra])).slice(0,300);
      const items = nodes.map((el, i) => {
        const id = token + '-' + i;
        el.setAttribute('data-dy-agent-node', id);
        return {id,tag:el.tagName.toLowerCase(),role:el.getAttribute('role'),type:el.getAttribute('type'),
          text:(el.innerText || el.getAttribute('aria-label') || '').trim().slice(0,160),
          placeholder:el.getAttribute('placeholder') || el.getAttribute('data-placeholder'),
          href:el.tagName === 'A' ? el.href : null,
          value:/password|tel/.test(el.type||'') || /验证码|手机号|密码/.test(el.getAttribute('placeholder')||'') ? '[redacted]' : ((el.value || '').slice(0,300)),
          checked: typeof el.checked === 'boolean' ? el.checked : el.getAttribute('aria-checked'),
          disabled:!!el.disabled, editable:!!el.isContentEditable};
      });
      return {url:location.href,title:document.title,text:(document.body.innerText || '').slice(0,14000),nodes:items};
    })()''')


def node_selector(node):
    import re
    if not re.fullmatch(r"[a-z0-9]+-[0-9]+", node):
        raise ValueError("节点标识无效；先执行 browser snapshot")
    return '[data-dy-agent-node="' + node + '"]'


def inspect_node(page, node):
    selector = node_selector(node)
    return page.evaluate("(() => {const e=document.querySelector(" + json.dumps(selector) + "); return !e ? null : {text:(e.innerText||e.getAttribute('aria-label')||'').trim(),type:e.type||'',value:e.value||e.innerText||'',editable:e.isContentEditable,visible:!!(e.offsetWidth||e.offsetHeight||e.getClientRects().length)};})()")


def click_node(page, node, allow_send=False):
    item = inspect_node(page, node)
    if not item or not item["visible"]:
        raise ValueError("页面节点已失效，重新观察页面")
    if not allow_send and any(word in item["text"] for word in ["发布", "发送", "删除", "支付", "充值", "同意协议", "确认授权"]):
        raise ValueError("这是提交或敏感控件；发片/回复应使用有任务记录的 commit，其他操作不在自主运营范围")
    return page.click(node_selector(node))


def fill_node(page, node, text):
    item = inspect_node(page, node)
    if not item or item["type"] in {"password", "file"}:
        raise ValueError("输入框不可用或应由用户完成")
    if item["value"].strip() and item["value"].strip() != text.strip():
        raise ValueError("输入框已有不同草稿，未覆盖；请先核对并明确处理原草稿")
    if item["value"].strip() == text.strip():
        return {"applied":True,"already_present":True}
    if not page.click(node_selector(node)) or not page.insert_text(text):
        raise ValueError("输入未成功")
    after = inspect_node(page, node)
    return {"applied": bool(after and after["value"].strip() == text.strip())}


def comments(page, limit=20):
    selectors = list(get_default_adapter().selectors.comment_item_selectors)
    expression = r'''(() => {
      const selectors = __SELECTORS__;
      const visible = e => !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length);
      let rows=[];
      for(const s of selectors){rows=Array.from(document.querySelectorAll(s)).filter(visible);if(rows.length)break;}
      return rows.slice(0,__LIMIT__).map(e=>({
        text:(e.innerText||'').trim().slice(0,2000),
        author_url:e.querySelector('a[href*="/user/"]')?.href || null,
        author:e.querySelector('a[href*="/user/"]')?.innerText.trim() || null,
        cid:e.getAttribute('data-id')||e.getAttribute('data-comment-id')||null,
        can_reply:Array.from(e.querySelectorAll('button,span,a,div')).some(x=>visible(x)&&(x.innerText||'').trim()==='回复')
      }));
    })()'''.replace("__SELECTORS__", json.dumps(selectors)).replace("__LIMIT__", str(max(1,min(limit,50))))
    return page.evaluate(expression) or []


def open_reply(page, saved):
    """Match the previously observed entire card and author, then click its Reply."""
    expression = r'''(() => {
      const expected=__SAVED__, selectors=__SELECTORS__;
      const visible=e=>!!(e.offsetWidth||e.offsetHeight||e.getClientRects().length);
      let rows=[];for(const s of selectors){rows=Array.from(document.querySelectorAll(s)).filter(visible);if(rows.length)break;}
      const matches=rows.filter(e=>(e.innerText||'').trim().slice(0,2000)===expected.text && (!expected.author_url || e.querySelector('a[href*="/user/"]')?.href===expected.author_url));
      if(matches.length!==1)return {ok:false,reason:'reply_target_ambiguous_or_changed'};
      const row=matches[0];
      const candidates=Array.from(row.querySelectorAll('button,a,span,[role="button"]')).filter(e=>visible(e)&&(e.innerText||'').trim()==='回复');
      const target=candidates.find(e=>!candidates.some(other=>other!==e&&e.contains(other)));
      if(!target)return {ok:false,reason:'reply_button_unavailable'};
      document.querySelectorAll('[data-dy-agent-reply-root]').forEach(e=>{e.removeAttribute('data-dy-agent-reply-root');e.removeAttribute('data-dy-agent-reply-key');});
      document.querySelectorAll('[data-dy-agent-reply-editor]').forEach(e=>e.removeAttribute('data-dy-agent-reply-editor'));
      row.setAttribute('data-dy-agent-reply-root','current');row.setAttribute('data-dy-agent-reply-key',expected.key||'');target.click();return {ok:true,author:expected.author};
    })()'''.replace("__SAVED__", json.dumps(saved, ensure_ascii=False)).replace("__SELECTORS__", json.dumps(list(get_default_adapter().selectors.comment_item_selectors)))
    return page.evaluate(expression)


def reply_adapter():
    """Restrict upstream editor and send discovery to the verified reply card."""
    from dataclasses import replace
    base = get_default_adapter()
    root = '[data-dy-agent-reply-root="current"]'
    selectors = replace(base.selectors,
        comment_input_selectors=(root + ' [data-dy-agent-reply-editor="current"]',),
        comment_submit_selectors=tuple(root + ' ' + selector for selector in base.selectors.comment_submit_selectors))
    return replace(base, selectors=selectors)


def reply_target_visible(page, author, key=None):
    if not author or not key:
        return False
    return bool(page.evaluate(r'''(() => {
      const author=__AUTHOR__,key=__KEY__;
      const visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
      const root=document.querySelector('[data-dy-agent-reply-root="current"]');
      if(!visible(root)||root.getAttribute('data-dy-agent-reply-key')!==key)return false;
      const authorNode=root.querySelector('a[href*="/user/"]');
      if(!authorNode||(authorNode.innerText||'').trim()!==author)return false;
      const fields=Array.from(root.querySelectorAll('textarea,[contenteditable="true"]')).filter(visible);
      if(fields.length!==1)return false;
      const field=fields[0];
      const described=(field.getAttribute('aria-describedby')||'').split(/\s+/).map(id=>document.getElementById(id)?.innerText||'').join(' ');
      const label=[field.getAttribute('placeholder'),field.getAttribute('data-placeholder'),field.getAttribute('aria-label'),described].filter(Boolean).join(' ').replace(/\s/g,'');
      const replying=Array.from(root.querySelectorAll('button,a,span,div')).some(e=>visible(e)&&(e.innerText||'').trim()==='回复中');
      if(!replying||(!(label===('回复@'+author).replace(/\s/g,'')||label===('回复'+author).replace(/\s/g,''))&&!(field.innerText||field.value||'').trim()))return false;
      field.setAttribute('data-dy-agent-reply-editor','current');
      return true;
    })()'''.replace('__AUTHOR__',json.dumps(author,ensure_ascii=False)).replace('__KEY__',json.dumps(key))))


def reply_thread_text(page):
    return reply_thread_state(page).get('text','')


def reply_thread_state(page):
    """Exclude editors even when verification disables contenteditable."""
    return page.evaluate(r'''(() => {
      const roots=document.querySelectorAll('[data-dy-agent-reply-root="current"]');
      if(roots.length!==1)return {valid:false,text:'',editors_empty:false};
      const root=roots[0];
      const editorSelector='[data-dy-agent-reply-editor],input,textarea,[contenteditable],[role="textbox"],[role="combobox"]';
      const editors=Array.from(root.querySelectorAll(editorSelector));
      const empty=editors.every(e=>!(e.value||e.textContent||'').trim());
      const copy=root.cloneNode(true);
      copy.querySelectorAll(editorSelector).forEach(e=>e.remove());
      return {valid:true,text:copy.textContent||'',editors_empty:empty};
    })()''') or {'valid':False,'text':'','editors_empty':False}

