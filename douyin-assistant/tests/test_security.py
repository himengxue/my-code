import argparse, os, sys, unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]/'runtime'
os.environ['DOUYIN_AGENT_HOME']=str(ROOT/'data')
sys.path.insert(0,str(ROOT))
import runtime
import chrome_launcher as launcher
cli=runtime.upstream

class SecurityTests(unittest.TestCase):
 def test_headless_has_no_security_disabling_flags(self):
  for uid in (0,1000):
   with self.subTest(uid=uid), patch.object(os,'geteuid',return_value=uid), patch.dict(os.environ,{'DOUYIN_CHROME_NO_SANDBOX':'1'}):
    flags=launcher._prepare_launch_cmd('/usr/bin/chromium',19323,True,'/isolated-profile')
    self.assertIn('--headless=new',flags)
    self.assertIn('--remote-debugging-address=127.0.0.1',flags)
    self.assertNotIn('--no-sandbox',flags)
    self.assertFalse(any('AutomationControlled' in flag for flag in flags))
 def test_risk_immediately_stops_without_connect(self):
  for headed in (True,False):
   for target in (None,'target'):
    for recover in (True,False):
     with self.subTest(headed=headed,target=target,recover=recover), patch.object(cli,'_connect',side_effect=AssertionError('Must not connect')), patch.object(cli,'settle_login_state',side_effect=AssertionError('Must not recheck')):
      original={'success':False,'risk_page':True,'error':'verification'}
      result=cli._maybe_switch_to_headed_for_risk(argparse.Namespace(headed=headed,target_id=target),original,'test',None,accept_recovered_login=recover)
      self.assertTrue(result['needs_user_verification'])
      self.assertTrue(result['risk_page'])
      self.assertEqual(result['action'],'needs_user_verification')
      self.assertEqual(original,{'success':False,'risk_page':True,'error':'verification'})
 def test_nonrisk_unchanged(self):
  with patch.object(cli,'_connect',side_effect=AssertionError('Must not connect')):
   self.assertIsNone(cli._maybe_switch_to_headed_for_risk(argparse.Namespace(),{'success':True},'test',None))

if __name__=='__main__':unittest.main(verbosity=2)
