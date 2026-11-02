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
              for key in ('CANDIDATE', 'BUILD', 'SOURCE', 'ASSOCIATION', 'PROVISION', 'READY', 'ADBD')}
    report_path = args.evidence / 'adbd/report.json'
    adbd = json.loads(report_path.read_text()) if report_path.exists() else {}
    scope = adbd.get('scope', {})
    checks = adbd.get('consumer', {}).get('checks_executed', 0)
    complete = (adbd.get('status') == 'passed' and checks == 15
                and all(phases[k] == 'success' for k in ('candidate', 'build', 'source', 'association', 'ready', 'adbd')))
    authenticated = scope.get('rsa_auth_positive_interop_observed') is True and scope.get('unauthorized_key_rejection_observed') is True
    result = {
        'schema': 1, 'milestone': 'M3', 'commit': os.environ['GITHUB_SHA'],
        'run_url': f"{os.environ['GITHUB_SERVER_URL']}/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{os.environ['GITHUB_RUN_ID']}",
        'recorded_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'phases': phases,
        'M3-A': {'verdict': ('PASS' if authenticated else 'CONDITIONAL PASS') if complete else 'NOT VERIFIED',
                 'layer': 'Native public API to actual Android Emulator adbd', 'checks_executed': checks,
                 'auth_positive_verified': scope.get('rsa_auth_positive_interop_observed', False),
                 'auth_denial_verified': scope.get('unauthorized_key_rejection_observed', False),
                 'scope': scope, 'report_status': adbd.get('status', 'not executed')},
        'M3-B': {'verdict': 'NOT VERIFIED', 'reason': 'This checkpoint runs ADB transport, not wireless SPAKE2 pairing.'},
        'M3-C': {'verdict': 'NOT VERIFIED', 'reason': 'No physical device is selected by this workflow.'},
        'main_goal_verdict': 'NOT VERIFIED',
    }
    args.evidence.mkdir(parents=True, exist_ok=True)
    (args.evidence / 'm3-status.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
