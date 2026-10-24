import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
from agent import form_value_matches
from agent import reply_observed
import runtime
import chrome_launcher
import os
import tempfile
from unittest.mock import patch

class EditorSentinelTests(unittest.TestCase):
    def test_platform_terminal_marker(self):
        self.assertTrue(form_value_matches('原创测试正文', ['原创测试正文\u200b']))
    def test_changed_or_truncated_text_is_rejected(self):
        self.assertFalse(form_value_matches('原创测试正文', ['原创测试\u200b']))
        self.assertFalse(form_value_matches('原创测试正文', ['非原创测试正文\u200b']))
    def test_internal_marker_is_not_ignored(self):
        self.assertFalse(form_value_matches('原创测试正文', ['原创\u200b测试正文']))


from agent import match_creator_cards

class OwnCardMatchingTests(unittest.TestCase):
    def test_unique_card_and_self_post_match(self):
        rows=match_creator_cards([{'title':'原创短片','platform_status':'已发布'}],[{'id':'123','url':'https://www.douyin.com/video/123','title':'0\n原创短片'}])
        self.assertEqual([r['id'] for r in rows],['123'])
        self.assertEqual(rows[0]['platform_status'],'已发布')
    def test_ambiguous_titles_fail_closed(self):
        self.assertEqual(match_creator_cards([{'title':'相同标题'}],[{'id':'1','title':'相同标题'},{'id':'2','title':'相同标题'}]),[])
    def test_unmatched_and_empty_card_fail_closed(self):
        self.assertEqual(match_creator_cards([{'title':'本人作品'},{'title':''}],[{'id':'1','title':'其他作品'}]),[])


class ProfileIsolationTests(unittest.TestCase):
    def test_profile_respects_explicit_state_root(self):
        with tempfile.TemporaryDirectory(prefix='profile space ') as directory:
            root=Path(directory)/'中文状态'
            with patch.dict(os.environ,{'DOUYIN_SKILLS_HOME':str(root)}):
                self.assertEqual(chrome_launcher.default_profile_dir(19323),str(root/'chrome'/'profile-19323'))

    def test_default_profile_fallback_unchanged(self):
        environment={key:value for key,value in os.environ.items() if key!='DOUYIN_SKILLS_HOME'}
        with patch.dict(os.environ,environment,clear=True):
            self.assertEqual(chrome_launcher.default_profile_dir(19323),str(Path.home()/'.douyin-skills/chrome/profile-19323'))

    def test_reply_adapter_is_scoped_without_changing_default(self):
        base=runtime.get_default_adapter()
        original=base.selectors.comment_input_selectors
        scoped=runtime.reply_adapter()
        self.assertEqual(base.selectors.comment_input_selectors,original)
        self.assertTrue(all(selector.startswith('[data-dy-agent-reply-root="current"] ') for selector in scoped.selectors.comment_input_selectors+scoped.selectors.comment_submit_selectors))


class ReplyConfirmationTests(unittest.TestCase):
    before={'valid':True,'text':'original comment','editors_empty':False}

    def test_disabled_editor_draft_is_not_confirmation(self):
        self.assertFalse(reply_observed(self.before,{'valid':True,'text':'reply','editors_empty':False},'reply'))

    def test_empty_editor_without_new_reply_is_not_confirmation(self):
        self.assertFalse(reply_observed(self.before,{'valid':True,'text':'original comment','editors_empty':True},'reply'))

    def test_old_identical_reply_is_not_new_evidence(self):
        before={'valid':True,'text':'original comment reply','editors_empty':False}
        after={'valid':True,'text':'original comment reply','editors_empty':True}
        self.assertFalse(reply_observed(before,after,'reply'))

    def test_missing_target_is_not_confirmation(self):
        self.assertFalse(reply_observed(self.before,{'valid':False,'text':'reply','editors_empty':True},'reply'))

    def test_visible_new_reply_with_empty_editor(self):
        self.assertTrue(reply_observed(self.before,{'valid':True,'text':'original comment reply','editors_empty':True},'reply'))

    def test_current_page_echo_does_not_confirm_remote_persistence(self):
        import agent
        from ledger import Ledger
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as directory:
            db=Ledger(Path(directory))
            try:
                saved={'video_id':'1','author':'Fixture Author','key':'fixture-key'}
                job=db.add('reply',{'comment':saved,'text':'reply'},'reply:fixture-key')
                db.ready(job['id'],{'target_id':'fixture','page_url':'https://www.douyin.com/video/1'})
                after={'valid':True,'text':'original comment reply','editors_empty':True}
                with patch.object(agent,'authorized'), patch.object(agent,'require_own'), \
                     patch.object(agent.rt,'connect'), patch.object(agent,'verify_page',return_value={}), \
                     patch.object(agent.rt,'reply_target_visible',return_value=True), \
                     patch.object(agent.rt,'reply_thread_state',side_effect=[self.before,after]), \
                     patch.object(agent.time,'sleep'), \
                     patch('douyin.interact._prepare_comment',return_value={'ok':True}), \
                     patch('douyin.interact._submit_comment',return_value={'ok':True}) as submit:
                    result=agent.send_reply(SimpleNamespace(job=job['id']),db)
                self.assertFalse(result['ok'])
                self.assertTrue(result['data']['needs_independent_verification'])
                self.assertEqual(db.get(job['id'])['status'],'uncertain')
                submit.assert_called_once()
            finally:
                db.close()

    def test_post_click_verification_is_uncertain_and_never_retried(self):
        import agent
        from ledger import Ledger
        from contextlib import ExitStack
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as directory:
            db=Ledger(Path(directory))
            try:
                saved={'video_id':'1','author':'Fixture Author','key':'fixture-key'}
                job=db.add('reply',{'comment':saved,'text':'reply'},'reply:fixture-key')
                db.ready(job['id'],{'target_id':'fixture','page_url':'https://www.douyin.com/video/1'})
                with ExitStack() as stack:
                    for name in ('authorized','require_own'):
                        stack.enter_context(patch.object(agent,name))
                    stack.enter_context(patch.object(agent.rt,'connect'))
                    stack.enter_context(patch.object(agent.rt,'reply_target_visible',return_value=True))
                    stack.enter_context(patch.object(agent.rt,'reply_thread_state',return_value=self.before))
                    stack.enter_context(patch.object(agent,'verify_page',side_effect=[{},agent.UserVerificationRequired('verification')]))
                    stack.enter_context(patch.object(agent.time,'sleep'))
                    stack.enter_context(patch('douyin.interact._prepare_comment',return_value={'ok':True}))
                    submit=stack.enter_context(patch('douyin.interact._submit_comment',return_value={'ok':True}))
                    result=agent.send_reply(SimpleNamespace(job=job['id']),db)
                self.assertFalse(result['ok'])
                self.assertTrue(result['data']['needs_user_verification'])
                self.assertFalse(result['data']['retry_safe'])
                self.assertEqual(db.get(job['id'])['status'],'uncertain')
                submit.assert_called_once()
                with self.assertRaises(ValueError):
                    db.dispatch(job['id'])
            finally:
                db.close()
