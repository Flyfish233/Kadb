#!/usr/bin/env python3
"""Record actual M3 phase outcomes without substituting CI success for protocol proof."""
import argparse
import datetime
import json
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    phases = {key.lower(): os.environ.get('M3_' + key, 'not executed')
              for key in ('CANDIDATE', 'BUILD', 'SOURCE', 'ASSOCIATION', 'PROVISION', 'READY', 'ADBD', 'PAIRING', 'CONTROLLED')}
    report_path = args.evidence / 'adbd/report.json'
    adbd = json.loads(report_path.read_text()) if report_path.exists() else {}
    scope = adbd.get('scope', {})
    checks = adbd.get('consumer', {}).get('checks_executed', 0)
    complete = (adbd.get('status') == 'passed' and checks == 15
                and all(phases[k] == 'success' for k in ('candidate', 'build', 'source', 'association', 'ready', 'adbd')))
    authenticated = scope.get('rsa_auth_positive_interop_observed') is True and scope.get('unauthorized_key_rejection_observed') is True
    def load_report(name):
        path = args.evidence / name / 'report.json'
        return json.loads(path.read_text()) if path.exists() else {}

    pairing = load_report('real-pairing')
    controlled = load_report('controlled-peer')
    sessions = pairing.get('sessions', [])
    real_pairing = (
        pairing.get('status') == 'passed'
        and pairing.get('peer', {}).get('kind') == 'android_system_AOSP_pairing_service'
        and pairing.get('paired_key_persisted_by_android') is True
        and pairing.get('authorized_key_set_restored') is True
        and pairing.get('emulator_auth_wifi_and_uid_restored') is True
        and pairing.get('cleanup_errors') == []
        and [s.get('mode') for s in sessions] == ['reject', 'pair']
        and all(s.get('exit_code') == 0 and s.get('consumer', {}).get('status') == 'passed' for s in sessions)
        and sessions[0].get('server_gcm_rejection_observed') is True
        and sessions[0].get('temporary_key_absent') is True
    )
    supplemental = (
        controlled.get('status') == 'passed'
        and controlled.get('native', {}).get('checks_executed') == 13
        and controlled.get('peer', {}).get('completed_sessions') == 13
        and controlled.get('peer', {}).get('negative_sessions_completed') == 11
        and controlled.get('scope', {}).get('real_adbd') is False
        and controlled.get('scope', {}).get('fresh_session_recovery') is True
    )
    source_verified = all(phases[k] == 'success' for k in ('candidate', 'build', 'source', 'association'))
    b_verdict = ('PASS' if supplemental and source_verified else 'CONDITIONAL PASS') if real_pairing else 'NOT VERIFIED'
    a_verdict = ('PASS' if authenticated else 'CONDITIONAL PASS') if complete else ('FAIL' if adbd.get('consumer') else 'NOT VERIFIED')
    result = {
        'schema': 1, 'milestone': 'M3', 'commit': os.environ['GITHUB_SHA'],
        'run_url': f"{os.environ['GITHUB_SERVER_URL']}/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{os.environ['GITHUB_RUN_ID']}",
        'recorded_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'phases': phases,
        'M3-A': {'verdict': a_verdict,
                 'layer': 'Native public API to actual Android Emulator adbd', 'checks_executed': checks,
                 'auth_positive_verified': scope.get('rsa_auth_positive_interop_observed', False),
                 'auth_denial_verified': scope.get('unauthorized_key_rejection_observed', False),
                 'scope': scope, 'report_status': adbd.get('status', 'not executed')},
        'M3-B': {'verdict': b_verdict,
                 'layer': 'Actual Android system pairing service; controlled faults are separate',
                 'real_pairing_and_wrong_code_complete': real_pairing,
                 'real_checks_executed': pairing.get('checks_executed', 0),
                 'real_pairing_verdict': pairing.get('pairing_verdict', 'NOT VERIFIED'),
                 'post_pair_connection_verdict': pairing.get('post_pair_connection_verdict', 'NOT VERIFIED'),
                 'post_pair_identity_enforcement_verdict': pairing.get('post_pair_identity_enforcement_verdict', 'NOT VERIFIED'),
                 'supplementary_controlled_peer_complete': supplemental,
                 'controlled_peer_checks_executed': controlled.get('native', {}).get('checks_executed', 0),
                 'controlled_peer_is_real_adbd': False,
                 'real_service_error': pairing.get('error'),
                 'controlled_peer_error': controlled.get('error')},
        'M3-C': {'verdict': 'NOT VERIFIED', 'reason': 'No physical device is selected by this workflow.'},
        'main_goal_verdict': b_verdict,
        'R3_K01': 'Inherited AOSP-compatible bidirectional GCM nonce behavior remains unchanged',
    }
    args.evidence.mkdir(parents=True, exist_ok=True)
    (args.evidence / 'm3-status.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
