"""Frozen resource runtime with conditional IGASPIN reporting; detector unchanged."""
import json,sys
from pathlib import Path
from gnss_jamming import pilot_runtime as runtime
_original_summary=runtime.summarize

def summarize(spec,output):
    result=_original_summary(spec,output)
    result.update(protocol='igaspin-resource-20261104',conditions=[],eligible_episode=False,
                  confirmed_delay_s=None,information_delay_s=None,active_before_onset=False,
                  FAR_status='NOT EVALUABLE',physical_deadline_status='NOT EVALUABLE',
                  adapter_cost_included=False,measurement_boundary='accepted prepared NAV-trigger message -> event-ready; offline UBX adapter excluded',
                  ordinal_arm=spec['session']['ordinal_arm'],recording=spec['session']['recording'],
                  no_target_hardware_equivalence=True)
    reference=spec.get('provider_reference_s')
    if reference is not None:
        fresh=[e for e in result['events'] if e['start_s']>=reference]
        ready_delay=min((e['ready_s']-reference for e in fresh),default=None)
        result.update(provider_reference_utc=spec['provider_reference_utc'],provider_reference_s=reference,
                      mapped_reference_execution_clock_s=result['clock_origin']+reference if result['clock_origin'] is not None else None,
                      conditional_first_new_alarm_information_delay_s=min((e['start_s']-reference for e in fresh),default=None),
                      conditional_first_new_alarm_execution_delay_s=ready_delay,
                      conditional_new_alarm_ready_within_reference_10s=ready_delay is not None and 0<=ready_delay<=10,
                      conditional_active_carry_in_at_reference=any(e['start_s']<reference and (e['end_s'] is None or e['end_s']>reference) for e in result['events']),
                      conditional_active_carry_in_clock='source_NAV_information_clock; not a historical execution-clock reconstruction',
                      reference_semantics='provider annotated reference only; not verified physical jammer-on; ordinal RF identity only')
    else:
        result.update(provider_reference_utc=None,conditional_first_new_alarm_execution_delay_s=None,
                      conditional_new_alarm_ready_within_reference_10s=None,conditional_active_carry_in_at_reference=None)
    runtime.dump(Path(output)/'summary.json',result)
    return result

runtime.summarize=summarize


def parity():
    import numpy as np
    source=Path('/scope')
    reference=json.loads((source/'reference_subset.json').read_text())
    sessions=json.loads(Path('/inputs/configs/sessions.json').read_text())
    policy=json.loads((source/'policy.json').read_text())
    checks=[]
    for session in sessions:
        rows=runtime.records('/inputs',session['session_id'])
        for config in reference['configs']:
            runner=runtime.make_runner('/inputs',config,policy)
            expected=reference['scores'][session['session_id']][config.rsplit('_d',1)[0]]
            expected_events=reference['events'][session['session_id']][config]
            events=[];current=None
            for index,row in enumerate(rows):
                actual=runtime.runner_step(runner,row)
                item=expected[index]
                assert row['elapsed_s']==item['elapsed_s']
                if item['score'] is None:assert actual['score'] is None,(session['session_id'],config,index,'none')
                else:
                    assert np.isclose(actual['score'],item['score'],atol=policy['score_atol'],rtol=policy['score_rtol']),(session['session_id'],config,index,'score')
                    threshold=runtime.parse_config_id(config)[1]
                    assert (actual['score']>=threshold)==(item['score']>=threshold)
                assert actual['state']==item['state'],(session['session_id'],config,index,'state',actual['state'],item['state'])
                if actual['event_started'] is not None:
                    current={'start_ns':int(str(row['utc_ns_exact'])[3:]),'end_ns':None};events.append(current)
                if actual['event_closed'] is not None:current['end_ns']=int(str(row['utc_ns_exact'])[3:]);current=None
            assert events==expected_events,(session['session_id'],config,'events',events,expected_events)
            checks.append({'session_id':session['session_id'],'config_id':config,'rows':len(rows),'scores_crossings_states_events_exact':True})
    runtime.dump('/outputs/parity.json',{'status':'PASS','checks':checks,'comparisons':len(checks),'rows_compared':sum(c['rows'] for c in checks),'score_atol':policy['score_atol'],'score_rtol':policy['score_rtol'],'event_integer_ns_exact':True,'offline_adapter_not_timed':True})

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='parity':parity()
    else:runtime.main()
