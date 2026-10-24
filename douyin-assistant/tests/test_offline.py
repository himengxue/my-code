import os,sys,tempfile,unittest,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'runtime'
os.environ['DOUYIN_AGENT_HOME']=str(ROOT/'data')
sys.path.insert(0,str(ROOT))
import agent
from ledger import Ledger
from browser_runtime import normalize_host
from unittest.mock import patch

class OfflineTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  self.db=Ledger(Path(self.tmp.name))
 def tearDown(self):
  self.db.close();self.tmp.cleanup()
 def job(self):
  return self.db.add('video',{'title':'offline'},'unique')
 def test_dedupe(self):
  a=self.job();b=self.job();self.assertEqual(a['id'],b['id']);self.assertTrue(b['existing'])
 def test_dispatch_requires_ready(self):
  with self.assertRaises(ValueError):self.db.dispatch(self.job()['id'])
 def test_no_repeat_dispatch(self):
  j=self.job()['id'];self.db.ready(j,{});self.db.dispatch(j)
  with self.assertRaises(ValueError):self.db.dispatch(j)
 def test_uncertain_not_reprepared(self):
  j=self.job()['id'];self.db.ready(j,{});self.db.dispatch(j);self.db.finish(j,False,{})
  with self.assertRaises(ValueError):self.db.ready(j,{})
 def test_only_confirmed_no_click_can_retry(self):
  j=self.job()['id'];self.db.ready(j,{});self.db.dispatch(j)
  with self.assertRaises(ValueError):self.db.unattempted(j,{'clicked':None})
  self.assertEqual(self.db.unattempted(j,{'clicked':False})['status'],'ready')
 def test_policy_disallows_publish(self):
  with self.assertRaises(ValueError):agent.authorized('video')
 def test_policy_disallows_reply(self):
  with self.assertRaises(ValueError):agent.authorized('comment')
 def test_publish_denied_before_browser(self):
  args=agent.build_parser().parse_args(['video','publish','--job','test'])
  with patch.object(agent.rt,'connect',side_effect=AssertionError('browser forbidden')):
   with self.assertRaises(ValueError):agent.publish_video(args,self.db)
 def test_loopback_only(self):
  self.assertEqual(normalize_host('localhost'),'127.0.0.1')
  with self.assertRaises(ValueError):normalize_host('example.com')
  with self.assertRaises(ValueError):normalize_host('192.168.1.1')
 def test_observation_required(self):
  with self.assertRaises(ValueError):agent.require_own(self.db,'123')
 def test_binding(self):
  binding=json.loads((ROOT.parent/'.agents/skills/douyin-assistant/runtime.json').read_text())
  skill=ROOT.parent/'.agents/skills/douyin-assistant'
  home=(skill/binding['home']).resolve()
  self.assertEqual(home,ROOT)
  self.assertTrue((home/binding['entrypoint']).is_file())
 def test_no_operator_grant(self):
  p=agent.policy()
  self.assertEqual(p['mode'],'not_configured')
  self.assertIsNone(p['authorization'])
  self.assertFalse(p['scheduled_runs'])

if __name__=='__main__':unittest.main(verbosity=2)
