"""Optional about:blank DOM smoke; connects only to an explicitly supplied loopback port.

Requires the project's installed browser bridge dependencies. Never visits Douyin
or sends a platform comment. Run separately from offline unittest discovery.
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'runtime'))
import runtime as rt
from agent import UserVerificationRequired, verify_page
from browser_runtime import Browser
from douyin.interact import _prepare_comment, _submit_comment


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,required=True)
    args=parser.parse_args()
    page=Browser(host='127.0.0.1',port=args.port).new_page()
    page.navigate('about:blank')
    fixture='''<title>Local reply safety fixture</title>
<div contenteditable="true" id="top"></div><button type="submit" id="top-send" onclick="window.topSent++">发送</button>
<div data-dy-agent-reply-root="current" data-dy-agent-reply-key="fixture-key">
<a href="https://www.douyin.com/user/fixture">Fixture Author</a><span>回复中</span>
<div id="reply-label">回复@Fixture Author</div>
<div><div contenteditable="true" id="reply" aria-describedby="reply-label"></div><button type="submit" id="reply-send" onclick="window.replySent++">发送</button></div>
</div>'''
    results={}
    try:
        page.evaluate('document.body.innerHTML='+json.dumps(fixture)+';window.topSent=0;window.replySent=0;true')
        results['reject_wrong_author']=not rt.reply_target_visible(page,'Wrong Author','fixture-key')
        results['reject_wrong_key']=not rt.reply_target_visible(page,'Fixture Author','wrong-key')
        results['accept_exact_target']=rt.reply_target_visible(page,'Fixture Author','fixture-key')
        filled=_prepare_comment(page,'offline fixture reply',adapter=rt.reply_adapter())
        results['target_fill_only']=bool(filled.get('ok')) and page.evaluate("document.getElementById('top').innerText===''&&document.getElementById('reply').innerText==='offline fixture reply'")
        results['exclude_unsent_draft']='offline fixture reply' not in rt.reply_thread_text(page)
        results['target_verified_after_fill']=rt.reply_target_visible(page,'Fixture Author','fixture-key')
        sent=_submit_comment(page,'offline fixture reply',adapter=rt.reply_adapter())
        results['target_send_only']=bool(sent.get('ok')) and page.evaluate('window.topSent===0&&window.replySent===1')
        page.evaluate("document.getElementById('reply').setAttribute('contenteditable','false');true")
        state=rt.reply_thread_state(page)
        results['disabled_draft_excluded']='offline fixture reply' not in state['text'] and not state['editors_empty']
        page.evaluate("document.getElementById('reply').style.display='none';true")
        state=rt.reply_thread_state(page)
        results['hidden_draft_excluded']='offline fixture reply' not in state['text'] and not state['editors_empty']
        page.evaluate("document.body.insertAdjacentHTML('beforeend','<div style=\"display:none\">unrelated hidden preview</div>');true")
        results['outside_preview_excluded']='unrelated hidden preview' not in rt.reply_thread_text(page)
        page.evaluate("document.getElementById('reply').style.display='';true")
        page.evaluate("document.body.insertAdjacentHTML('beforeend','<div id=verification><h2>接收短信验证码</h2><input placeholder=请输入验证码></div>');true")
        try:
            verify_page(page)
            results['sms_verification_stops']=False
        except UserVerificationRequired:
            results['sms_verification_stops']=True
        page.evaluate("document.getElementById('verification').remove();document.getElementById('reply').setAttribute('contenteditable','true');true")
        page.evaluate("document.querySelector('[data-dy-agent-reply-root]').insertAdjacentHTML('beforeend','<div contenteditable=true>second</div>');true")
        results['reject_ambiguous_editors']=not rt.reply_target_visible(page,'Fixture Author','fixture-key')
        print(json.dumps({'ok':all(results.values()),'scope':'local about:blank only','checks':results}))
        return 0 if all(results.values()) else 2
    finally:
        page.navigate('about:blank')


if __name__=='__main__':
    raise SystemExit(main())
