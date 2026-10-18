import io,json,math,queue,time,unittest
from types import SimpleNamespace
from unittest.mock import Mock,patch
from navigation_language import validate_proposal,grounded_intent,candidate_request,interpret

class LanguageTests(unittest.TestCase):
    def proposal(self,steps):return {'kind':'execute','message':'','steps':steps}
    def test_named_goals_are_resolved_from_map(self):
        r=validate_proposal(self.proposal([{'action':'goal','name':'desk'}]),{'desk':[2,3]})
        self.assertEqual(r['intent']['xy'],[2,3])
        with self.assertRaises(ValueError):validate_proposal(self.proposal([{'action':'goal','name':'chair'}]),{'desk':[2,3]})
    def test_limits_types_and_extra_fields(self):
        for step in [{'action':'turn','degrees':math.nan},{'action':'turn','degrees':0},{'action':'turn','degrees':720},
                     {'action':'forward','distance':True},{'action':'forward','distance':6},{'action':'shell','command':'anything'},
                     {'action':'turn','degrees':90,'code':'anything'}]:
            with self.subTest(step=step),self.assertRaises(ValueError):validate_proposal(self.proposal([step]),{})
    def test_clarification_cannot_execute(self):
        with self.assertRaises(ValueError):validate_proposal({'kind':'clarify','message':'What distance?','steps':[{'action':'stop'}]}, {})
        self.assertIsNone(validate_proposal({'kind':'clarify','message':'What distance?','steps':[]},{})['intent'])
    def test_sequences_and_stop(self):
        self.assertEqual(validate_proposal(self.proposal([{'action':'turn','degrees':180},{'action':'goal','name':'start'}]),{'start':[0,0]})['intent']['action'],'sequence')
        with self.assertRaises(ValueError):validate_proposal(self.proposal([{'action':'turn','degrees':90}]*9),{})
        with self.assertRaises(ValueError):validate_proposal(self.proposal([{'action':'stop'},{'action':'turn','degrees':90}]),{})
    def test_missing_slots_and_unmentioned_names_are_rejected(self):
        with self.assertRaises(ValueError):grounded_intent({'action':'forward','distance':1},'move forward')
        with self.assertRaises(ValueError):grounded_intent({'action':'goal','name':'start'},'go to the chair')
        with self.assertRaises(ValueError):grounded_intent({'action':'turn','degrees':360},'rotate')
    def test_questions_are_not_command_candidates(self):
        self.assertFalse(candidate_request('How do you spin around?'))
        self.assertFalse(candidate_request('Explain how to drive forward'))
        self.assertFalse(candidate_request("Don't move forward one metre"))
        self.assertFalse(candidate_request('Could you tell me how to spin 360 degrees?'))
        self.assertTrue(candidate_request('Make one full clockwise revolution'))
    def test_ollama_requires_complete_structured_response(self):
        content=json.dumps(self.proposal([{'action':'turn','degrees':-360}]))
        raw=json.dumps({'done':True,'message':{'content':content}}).encode()
        with patch('urllib.request.urlopen',return_value=io.BytesIO(raw)) as request:
            result=interpret('http://localhost','qwen','Make a full clockwise revolution',{})
        self.assertEqual(result['intent']['degrees'],-360)
        body=json.loads(request.call_args.args[0].data);self.assertIsInstance(body['format'],dict)
        self.assertNotIn('tools',body)
        with patch('urllib.request.urlopen',return_value=io.BytesIO(b'{"done":false,"message":{"content":"{}"}}')):
            with self.assertRaises(ValueError):interpret('http://localhost','qwen','rotate',{})
    def test_cancel_discards_delayed_model_plan(self):
        from gateway import StationGateway
        state=SimpleNamespace(ai_results=queue.Queue(),command_epoch=2,navigation_at=time.monotonic(),reply=Mock(),nav_request=Mock(),plan=Mock())
        state.ai_results.put(('id',True,'plan',{'type':'navigation_simulation','epoch':1,'request':{'action':'turn','degrees':360}}))
        StationGateway.drain_chat(state)
        state.nav_request.publish.assert_not_called()
        self.assertIn('cancelled',state.reply.call_args.args[2])
