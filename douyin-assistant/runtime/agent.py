#!/usr/bin/env python3
"""Douyin creator executor: model-independent JSON CLI and shared state."""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
import sys
import time
from pathlib import Path

import runtime as rt
from ledger import Ledger

VERSION = "2.0.0"


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)

    def print_help(self, file=None):
        print(json.dumps({'ok':True,'data':{'help':self.format_help()}},ensure_ascii=False))


def load_json(path):
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("JSON 顶层须为对象")
    return data


def file_hash(path):
    path = Path(path).resolve()
    if not path.is_file():
        raise ValueError(f"素材不存在：{path}")
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def policy():
    path = rt.ROOT / 'policy.json'
    return load_json(path if path.is_file() else rt.ROOT / 'policy.example.json')


def authorized(kind):
    p = policy()
    if p.get('mode') != 'autonomous_creator' or not p.get('authorization'):
        raise ValueError('尚未设置此电脑主人的自主运营授权；先由用户说明范围，再配置 policy.json')
    key = 'publish_videos' if kind == 'video' else 'reply_to_own_video_comments'
    if not p.get(key):
        raise ValueError('当前运营设置不包含此操作')


def global_args(args):
    return ['--port','19323'] + (['--headed'] if args.headed else [])


class UserVerificationRequired(ValueError):
    """The user must handle the platform's verification in the browser."""


def verify_page(page, expected_url=None):
    info = page.evaluate(r'''(() => {
      const visible=e=>!!(e.offsetWidth||e.offsetHeight||e.getClientRects().length);
      const body=(document.body?.innerText||'');
      const challenge=Array.from(document.querySelectorAll('iframe,[role="dialog"],[id*="captcha"],[class*="captcha"]')).filter(visible).some(e=>{
        if(e.tagName==='IFRAME')return /captcha|verify/.test(e.getAttribute('src')||'');
        return /拖动滑块|完成下方验证|完成安全验证|访问过于频繁|操作过于频繁|接收短信验证码|请输入验证码|身份验证/.test(e.innerText||'');
      });
      // Some verification overlays have no dialog role. Require both a visible
      // code input and a short verification heading; never read the code value.
      const codeInput=Array.from(document.querySelectorAll('input')).some(e=>visible(e)&&/验证码/.test([e.getAttribute('placeholder'),e.getAttribute('aria-label')].filter(Boolean).join(' ')));
      const verificationHeading=Array.from(document.querySelectorAll('h1,h2,h3,div,span')).some(e=>{
        const text=(e.innerText||'').trim();
        return visible(e)&&text.length<100&&/接收短信验证码|完成安全验证|验证身份|身份验证/.test(text);
      });
      return {url:location.href,title:document.title,text:body.slice(0,16000),verification_ui:challenge||(codeInput&&verificationHeading)||(body.length<600&&/访问过于频繁|账号异常|拖动滑块/.test(body))};
    })()''') or {}
    if info.get('verification_ui'):
        raise UserVerificationRequired('页面出现验证或风控提示；停止操作，请用户在该浏览器处理，随后先核对远端结果，勿自动重发')
    if expected_url and expected_url.split('?')[0] != info.get('url','').split('?')[0]:
        raise ValueError('页面已经离开任务目标，未发送')
    return info


def match_creator_cards(cards, profile_items):
    """Join visible creator cards to the explicit self-post list; fail on ambiguity."""
    norm = lambda text: ' '.join(str(text).split())
    result = []
    used = set()
    for card in cards:
        title = norm(card.get('title', ''))
        matches = [item for item in profile_items if title and title in norm(item.get('title', ''))]
        if len(matches) != 1 or matches[0]['id'] in used:
            continue
        item = matches[0]
        used.add(item['id'])
        result.append({**item, 'title': card['title'], 'platform_status': card.get('platform_status', ''), 'ownership_evidence': 'creator_card_and_self_post_list'})
    return result


def list_own_videos(page, db, limit):
    manage_url = 'https://creator.douyin.com/creator-micro/content/manage'
    page.navigate(manage_url)
    page.wait_for_load(15)
    cards = []
    for attempt in range(10):
        info = verify_page(page)
        if 'creator.douyin.com/creator-micro/content/manage' not in info.get('url', '') or '扫码登录' in info.get('text', ''):
            return {'ok': False, 'error': {'code': 'not_logged_in', 'message': '请登录创作者中心'}}
        cards = page.evaluate(r'''(() => {
          const visible=e=>!!(e.offsetWidth||e.offsetHeight||e.getClientRects().length);
          return Array.from(document.querySelectorAll('[class*="video-card-content-"]')).filter(visible).map(e=>({
            title:(e.querySelector('[class*="info-title-text-"]')?.innerText||'').trim(),
            platform_status:(e.querySelector('[class*="info-status-"]')?.innerText||'').trim()
          })).filter(e=>e.title);
        })()''') or []
        rows = page.evaluate(r'''(() => {
          const out=[],seen=new Set();
          for(const a of document.querySelectorAll('a[href]')){
            if(!(a.offsetWidth||a.offsetHeight||a.getClientRects().length))continue;
            const u=new URL(a.href),m=u.pathname.match(/\/(video|note)\/(\d+)/);
            const id=m?.[2]||u.searchParams.get('item_id')||u.searchParams.get('video_id');
            if(!id||!/^\d+$/.test(id)||seen.has(id))continue;seen.add(id);
            out.push({id,url:m?'https://www.douyin.com/'+m[1]+'/'+id:a.href,title:(a.innerText||a.closest('li')?.innerText||'').trim().slice(0,500)});
          }return out;
        })()''') or []
        if rows or cards:
            break
        if attempt < 9:
            time.sleep(1)
    profile_source = None
    if not rows and cards:
        # Current creator cards are DIVs without hrefs. Read only the explicit
        # self-post container, never recommendations, likes, or page-wide links.
        page.navigate('https://www.douyin.com/user/self?showTab=post')
        page.wait_for_load(15)
        profile_items = []
        for attempt in range(10):
            own_info = verify_page(page)
            if '/user/self' not in own_info.get('url', '') or '扫码登录' in own_info.get('text', ''):
                break
            profile_items = page.evaluate(r'''(() => {
              const visible=e=>!!(e.offsetWidth||e.offsetHeight||e.getClientRects().length);
              const root=Array.from(document.querySelectorAll('[data-e2e="user-post-list"]')).find(visible);
              if(!root)return [];
              const seen=new Set(),out=[];
              for(const a of root.querySelectorAll('a[href]')){
                if(!visible(a))continue;
                const u=new URL(a.href),m=u.pathname.match(/^\/(video|note)\/(\d+)$/);
                if(u.hostname!=='www.douyin.com'||!m||seen.has(m[2]))continue;
                seen.add(m[2]);out.push({id:m[2],url:'https://www.douyin.com/'+m[1]+'/'+m[2],title:(a.innerText||'').trim()});
              }return out;
            })()''') or []
            if profile_items:
                break
            if attempt < 9:
                time.sleep(1)
        rows = match_creator_cards(cards, profile_items)
        profile_source = own_info.get('url')
    for row in rows:
        db.observe('own-video:' + row['id'], {'video': row, 'source': info['url'], 'profile_source': profile_source})
    return {'ok': bool(rows), 'data': {'items': rows[:limit], 'loaded_count': len(rows), 'scope': '当前已加载作品；无链接卡片与本人作品容器交叉核对', 'target_id': page.target_id, 'creator_card_count': len(cards), 'profile_source': profile_source},
            **({} if rows else {'error': {'code': 'ui_changed', 'message': '当前作品列表没有可安全核对的链接；不将空解析当成没有作品。'}})}


def require_own(db, video_id):
    known = db.observation('own-video:'+video_id)
    if not known or time.time()-known['observed_at'] > 1800:
        raise ValueError('尚未在最近的本人作品列表核对该视频；先运行 video mine')


def prepare_video(args, db):
    authorized('video')
    manifest = load_json(args.manifest)
    for key in ('video','cover','title','caption_file','topic'):
        if not manifest.get(key):
            raise ValueError('发布清单缺少字段：'+key)
    manifest_path = Path(args.manifest).resolve()
    for key in ('video','cover','caption_file'):
        manifest[key] = str((manifest_path.parent / manifest[key]).resolve())
    manifest['hashes'] = {key:file_hash(manifest[key]) for key in ('video','cover','caption_file')}
    if manifest.get('ai_generated') is not True:
        raise ValueError('本自主创作流程要求明确 ai_generated: true；非 AI 素材请单独说明发布方式')
    key = 'video:'+manifest['hashes']['video']
    job = db.add('video',manifest,key)
    if job['status'] not in ('planned','ready'):
        return {'ok':False,'error':{'code':'duplicate_or_uncertain','message':'此视频已有提交记录，不重复上传发布'},'job':job}
    from douyin.publish import fill_publish_video
    page = rt.connect(headed=args.headed,fresh=True)
    caption = Path(manifest['caption_file']).read_text(encoding='utf-8-sig').strip()
    result = fill_publish_video(page, video=manifest['video'], desc=caption, title=manifest['title'], cover=manifest['cover'])
    marker=page.evaluate("document.querySelector('video')?.currentSrc || document.querySelector('video')?.src || ''") if result.get('success') else ''
    job = db.ready(job['id'],{'target_id':page.target_id,'page_url':page.evaluate('location.href'),'fill_result':result,'video_marker':marker}) if result.get('success') else job
    return {'ok':bool(result.get('success')),'job_id':job['id'],'result':result,'next':'核对 AI 声明、公开可见、封面及完整文案后运行 video publish --job ...；已授权范围内由 AI 完成核对。'}


def form_value_matches(expected, values):
    # Douyin's contenteditable inserts a trailing U+200B sentinel.
    # Ignore only that terminal editor marker, retaining internal content.
    return any(str(value).strip().rstrip('\u200b').strip() == expected.strip() for value in values)


def publish_video(args, db):
    authorized('video')
    job = db.get(args.job)
    if job['kind']!='video' or job['status']!='ready':
        raise ValueError('任务不是就绪的视频，或已有提交记录')
    p = job['payload']
    for key,digest in p['hashes'].items():
        if file_hash(p[key])!=digest:
            raise ValueError('准备后素材或文案改变，请建立新任务，未点击发布')
    page = rt.connect(target=p['target_id'])
    info = verify_page(page,p['page_url'])
    from douyin.publish import validate_video_publish_state, _dispatch_publish_click
    validation = validate_video_publish_state(page)
    if not validation.get('success'):
        return {'ok':False,'data':{'job_id':args.job,'validation':validation,'clicked':False}}
    fields=page.evaluate("({values:Array.from(document.querySelectorAll('input,textarea,[contenteditable=\"true\"]')).filter(e=>e.offsetWidth||e.offsetHeight||e.getClientRects().length).map(e=>(e.value||e.innerText||'').trim()),video:document.querySelector('video')?.currentSrc || document.querySelector('video')?.src || ''})") or {}
    expected_caption=Path(p['caption_file']).read_text(encoding='utf-8-sig').strip()
    if not form_value_matches(p['title'], fields.get('values',[])) or not form_value_matches(expected_caption, fields.get('values',[])):
        raise ValueError('当前表单标题/简介与此任务不一致，未发布')
    if p.get('video_marker') and fields.get('video') != p['video_marker']:
        raise ValueError('当前表单的视频预览发生变化，需要重新准备和核对')
    settings = page.evaluate(r'''(() => {
      const visible=e=>!!(e.offsetWidth||e.offsetHeight||e.getClientRects().length);
      const nodes=Array.from(document.querySelectorAll('label,[role="radio"],[role="checkbox"],[role="switch"],span,div,section')).filter(visible);
      const ai=nodes.some(e=>{const t=(e.innerText||'').replace(/\s/g,'');
        if(t.length>160)return false;
        const selected=e.getAttribute('aria-checked')==='true'||e.querySelector('input:checked,[aria-checked="true"]');
        return /内容由AI生成|作品由AI生成/.test(t)&&(selected||(t.includes('自主声明')&&t.length<100));});
      const publicVisibility=nodes.some(e=>{const t=(e.innerText||'').replace(/\s/g,'');return t.length<120&&/谁可以看|可见范围/.test(t)&&t.includes('公开')&&!/私密|仅自己|朋友/.test(t);})||nodes.some(e=>(e.innerText||'').trim()==='公开'&&(e.getAttribute('aria-checked')==='true'||e.querySelector('input:checked')));
      const dialogOpen=Array.from(document.querySelectorAll('[role="dialog"]')).some(visible);
      return {ai:ai&&!dialogOpen,publicVisibility,dialogOpen};
    })()''') or {}
    if not settings.get('ai') or not settings.get('publicVisibility'):
        return {'ok':False,'error':{'code':'settings_unverified','message':'请通过 browser snapshot/click 设置并核对 AI 声明与公开可见；未点击发布'},'settings':settings,'job_id':args.job}
    # Persist before crossing the remote side-effect boundary.
    before_image=rt.screenshot(page,'before-publish-'+args.job+'.png')
    db.dispatch(args.job)
    try:
        sent = _dispatch_publish_click(page,rt.get_default_adapter())
        if sent.get('clicked') is False:
            result={'clicked':False,'effect':'not_attempted','retry_safe':True,'dispatch':sent}
            db.unattempted(args.job,result)
            return {'ok':False,'data':{'job_id':args.job,**result}}
        result={'clicked':sent.get('clicked'),'effect':'unconfirmed','retry_safe':False,'dispatch':sent,'before_image':before_image}
        # A URL change or disappearing button alone does not prove publication.
        for _ in range(5):
            time.sleep(1)
            observed=verify_page(page)
            if any(line.strip() in ('发布成功','发布完成','已提交审核') for line in observed.get('text','').splitlines()):
                result.update(effect='confirmed',platform_status='submitted',evidence=observed['text'][:3000],url=observed.get('url'))
                break
    except Exception as exc:
        result={'clicked':None,'effect':'unknown','retry_safe':False,'error':str(exc)}
    final=db.finish(args.job,result.get('effect')=='confirmed',result)
    return {'ok':final['status']=='confirmed','data':{'job_id':args.job,'status':final['status'],**result}}


def comment_list(args, db):
    from douyin.interact import _open_detail, _open_comment_composer
    page=rt.connect(headed=args.headed)
    opened=_open_detail(page,args.video)
    if not opened.get('success'):
        return {'ok':False,'data':opened}
    _open_comment_composer(page)
    rows=rt.comments(page,args.limit)
    for row in rows:
        key=hashlib.sha256((args.video+json.dumps(row,sort_keys=True,ensure_ascii=False)).encode()).hexdigest()[:24]
        row['key']=key
        row['video_id']=args.video
        row['target_id']=page.target_id
        row['url']=page.evaluate('location.href')
        db.observe('comment:'+key,row)
    return {'ok':True,'data':{'items':rows,'scope':'当前已加载可见评论','target_id':page.target_id}}


def prepare_reply(args, db):
    authorized('reply')
    observation=db.observation('comment:'+args.key)
    if not observation:
        raise ValueError('先运行 comment list 获取评论 key')
    saved=observation['data']
    require_own(db,saved['video_id'])
    text=Path(args.text_file).read_text(encoding='utf-8-sig').strip()
    if not text or len(text)>1000:
        raise ValueError('回复为空或过长')
    job=db.add('reply',{'comment':saved,'text':text},'reply:'+args.key)
    if job['status'] not in ('planned','ready'):
        raise ValueError('这条评论已有提交记录，未重复回复')
    page=rt.connect(target=saved['target_id'])
    verify_page(page,saved['url'])
    selected=rt.open_reply(page,saved)
    if not selected or not selected.get('ok') or not rt.reply_target_visible(page,saved.get('author'),saved.get('key')):
        return {'ok':False,'error':{'code':'reply_target_unverified','message':'没有明确进入该作者的回复模式；未发送'},'job_id':job['id']}
    from douyin.interact import _prepare_comment
    filled=_prepare_comment(page,text,adapter=rt.reply_adapter())
    if filled.get('ok'):
        db.ready(job['id'],{'target_id':page.target_id,'page_url':saved['url']})
    return {'ok':bool(filled.get('ok')),'job_id':job['id'],'result':filled}


def send_reply(args, db):
    authorized('reply')
    job=db.get(args.job)
    if job['kind']!='reply' or job['status']!='ready':
        raise ValueError('回复任务未就绪或已有提交记录')
    p=job['payload']; saved=p['comment']; require_own(db,saved['video_id'])
    page=rt.connect(target=p['target_id']); verify_page(page,p['page_url'])
    if not rt.reply_target_visible(page,saved.get('author'),saved.get('key')):
        raise ValueError('回复对象标记已变化，未发送')
    from douyin.interact import _prepare_comment, _submit_comment
    if not _prepare_comment(page,p['text'],adapter=rt.reply_adapter()).get('ok'):
        raise ValueError('编辑器中的回复正文未核对通过')
    before=rt.reply_thread_state(page)
    db.dispatch(args.job)
    clicked=None
    try:
        sent=_submit_comment(page,p['text'],adapter=rt.reply_adapter())
        clicked=bool(sent.get('ok'))
        result={'clicked':clicked,'effect':'unconfirmed','retry_safe':False}
        for _ in range(5):
            time.sleep(1)
            verify_page(page,p['page_url'])
            after=rt.reply_thread_state(page)
            if clicked and reply_observed(before,after,p['text']):
                # The site may optimistically render a reply before accepting it.
                # Without a receipt or independent read bound to this thread,
                # preserve uncertain state and prohibit automatic redispatch.
                result.update(evidence=after['text'][-2000:],confirmation_scope='current_page_only',needs_independent_verification=True)
                break
    except UserVerificationRequired as exc:
        result={'clicked':clicked,'effect':'blocked','retry_safe':False,'needs_user_verification':True,'error':str(exc)}
    except Exception as exc:
        result={'clicked':clicked,'effect':'unknown','retry_safe':False,'error':str(exc)}
    final=db.finish(args.job,result['effect']=='confirmed',result)
    return {'ok':final['status']=='confirmed','data':{'job_id':args.job,'status':final['status'],**result}}


def reply_observed(before, after, text):
    """A disabled/unsent editor is never evidence of a posted reply."""
    return bool(text and before.get('valid') and after.get('valid')
                and after.get('editors_empty')
                and after.get('text','').count(text)>before.get('text','').count(text))


def build_parser():
    p=Parser(description='抖音自主创作执行器；模型负责选题与生成，本工具执行浏览器操作和保存任务记录。')
    p.add_argument('--headed',action='store_true')
    sub=p.add_subparsers(dest='command',required=True)
    for name in ('version','doctor','brief','policy','jobs'):
        sub.add_parser(name)
    p1=sub.add_parser('auth');p1.add_argument('action',choices=['login','status','wait'])
    p1=sub.add_parser('topic');p1.add_argument('--file',required=True)
    p1=sub.add_parser('render');p1.add_argument('--storyboard',required=True);p1.add_argument('--out',required=True)
    p1=sub.add_parser('video');p1.add_argument('action',choices=['mine','prepare','publish']);p1.add_argument('--manifest');p1.add_argument('--job');p1.add_argument('--limit',type=int,default=20)
    p1=sub.add_parser('comment');p1.add_argument('action',choices=['list','prepare','send']);p1.add_argument('--video');p1.add_argument('--key');p1.add_argument('--text-file');p1.add_argument('--job');p1.add_argument('--limit',type=int,default=20)
    p1=sub.add_parser('browser');p1.add_argument('action',choices=['snapshot','screenshot','open','click','fill']);p1.add_argument('--target');p1.add_argument('--url');p1.add_argument('--node');p1.add_argument('--text-file')
    p1=sub.add_parser('search');p1.add_argument('keyword');p1.add_argument('--limit',type=int,default=5)
    sub.add_parser('trending')
    return p


def run(args):
    if args.command=='version':
        return {'ok':True,'data':{'version':VERSION,'clients':['Codex','DeepSeek Harness','其他可执行本地命令的 Agent'],'execution':'shared local browser CLI'}}
    if args.command=='doctor':
        result=rt.invoke(['doctor']);return {'ok':bool(result.get('success')),'data':result}
    db=Ledger(rt.STATE)
    if args.command=='policy':return {'ok':True,'data':policy()}
    if args.command=='jobs':return {'ok':True,'data':db.list()}
    if args.command=='brief':return {'ok':True,'data':{'policy':policy(),'recent_jobs':db.list(20),'next':'AI 自主观察账号与观众问题，选题、生成并质检原创视频，按发布流程提交，再回复本人作品下的普通评论。'}}
    if args.command=='topic':return {'ok':True,'data':db.add('topic',load_json(args.file))}
    if args.command=='render':
        from render import render
        return {'ok':True,'data':render(args.storyboard,args.out)}
    with rt.browser_lock():
        if args.command=='auth':
            command={'login':'get-qrcode','status':'check-login','wait':'wait-login'}[args.action]
            result=rt.invoke(global_args(args)+[command])
            image=result.pop('qrcode_data_url',None)
            if image and image.startswith('data:image/'):
                path=rt.STATE/'login-qr.png';path.write_bytes(base64.b64decode(image.split(',',1)[1]));result['qr_image']=str(path)
            elif args.action=='login' and not result.get('risk_page'):
                page=rt.connect(headed=args.headed)
                info=verify_page(page)
                if '扫码登录' in info.get('text',''):
                    result={'success':True,'status':'login_page_ready','login_page_image':rt.screenshot(page,'login-page.png'),
                            'target_id':page.target_id,'message':'已打开官方扫码页；截图展示登录页，是否登录以 auth status 为准。'}
            return {'ok':bool(result.get('success')),'data':result}
        if args.command=='search':
            data=rt.invoke(global_args(args)+['search-videos','--keyword',args.keyword,'--limit',str(args.limit)])
            return {'ok':bool(data.get('success')),'data':data}
        if args.command=='trending':
            data=rt.invoke(global_args(args)+['get-trending-topics'])
            return {'ok':bool(data.get('success')),'data':data}
        if args.command=='video':
            if args.action=='mine':return list_own_videos(rt.connect(headed=args.headed),db,args.limit)
            if args.action=='prepare' and args.manifest:return prepare_video(args,db)
            if args.action=='publish' and args.job:return publish_video(args,db)
            raise ValueError('prepare 需要 --manifest；publish 需要 --job')
        if args.command=='comment':
            if args.action=='list' and args.video:return comment_list(args,db)
            if args.action=='prepare' and args.key and args.text_file:return prepare_reply(args,db)
            if args.action=='send' and args.job:return send_reply(args,db)
            raise ValueError('缺少评论参数；查看 comment --help')
        if args.command=='browser':
            page=rt.connect(target=args.target,headed=args.headed)
            if args.action=='screenshot':return {'ok':True,'data':{'image':rt.screenshot(page),'target_id':page.target_id}}
            if args.action=='open':
                if not args.url or not rt.get_default_adapter().is_platform_url(args.url):raise ValueError('仅允许抖音官方站点地址')
                page.navigate(args.url);page.wait_for_load(15)
            elif args.action=='click':rt.click_node(page,args.node)
            elif args.action=='fill':
                if not args.text_file:raise ValueError('使用 --text-file 提供 UTF-8 文本')
                result=rt.fill_node(page,args.node,Path(args.text_file).read_text(encoding='utf-8-sig'))
                if not result.get('applied'):raise ValueError('输入框未完整接收文本')
            return {'ok':True,'data':{'target_id':page.target_id,**rt.snapshot(page)}}
    raise ValueError('命令未实现')


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    try:
        result=run(build_parser().parse_args())
    except UserVerificationRequired as exc:
        result={'ok':False,'error':{'code':'needs_user_verification','message':str(exc)},'needs_user_verification':True,'retry_safe':False}
    except Exception as exc:
        result={'ok':False,'error':{'code':'execution_error','message':str(exc),'hint':'若已有提交记录，先核对网页结果，勿重复发送。'}}
    print(json.dumps(result,ensure_ascii=False))
    return 0 if result.get('ok') else 2


if __name__=='__main__':
    raise SystemExit(main())
