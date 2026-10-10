#!/usr/bin/env python3
"""One command: fetch everything for a state + industry and build survivors.csv.

  python run_state.py --state FL --naics 238220 --min-years 30 --min-loan 150000

Each stage is skipped if its output already exists, so re-runs are cheap.
Supported registries: FL (Sunbiz public SFTP). Other states: see references/state-coverage.md.
"""
import argparse, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REGISTRY_FETCHERS = {'FL': 'fetch_sunbiz.py'}

def run(args):
    print('>>', ' '.join(args)); r = subprocess.run([sys.executable] + args, cwd=HERE)
    if r.returncode != 0:
        sys.exit(f'stage failed: {args[0]}')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--state', required=True)
    ap.add_argument('--naics', required=True)
    ap.add_argument('--min-years', type=int, default=30)
    ap.add_argument('--min-loan', type=float, default=150000)
    ap.add_argument('--mode', choices=['sba-first', 'registry-first', 'both'], default='both')
    ap.add_argument('--datadir', default=os.path.abspath('data'))
    ap.add_argument('--local-registry', help='folder with registry files already downloaded (skips SFTP)')
    ap.add_argument('--ppp-small', action='store_true', help='include the under-$150k PPP files (slower, more recall)')
    a = ap.parse_args()
    state = a.state.upper(); d = a.datadir; os.makedirs(d, exist_ok=True)

    if state not in REGISTRY_FETCHERS:
        sys.exit(f'{state} has no registry adapter yet. See references/state-coverage.md for what it takes to add one.')

    sba_out = os.path.join(d, f'sba_ppp_{state}_{a.naics}.csv')
    if not os.path.exists(sba_out):
        cmd = ['fetch_sba.py', '--state', state, '--naics', a.naics, '--min-loan', str(a.min_loan), '--outdir', d]
        if a.ppp_small: cmd.append('--ppp-small')
        run(cmd)
    reg_out = os.path.join(d, 'sunbiz_active.csv' if state == 'FL' else f'registry_{state}_active.csv')
    if not os.path.exists(reg_out):
        cmd = [REGISTRY_FETCHERS[state], '--outdir', d]
        if a.local_registry: cmd += ['--local', a.local_registry]
        run(cmd)
    f5500_out = os.path.join(d, f'f5500_{state}.csv')
    if not os.path.exists(f5500_out):
        run(['fetch_5500.py', '--state', state, '--outdir', d])
    modes = ['sba-first', 'registry-first'] if a.mode == 'both' else [a.mode]
    for m in modes:
        run(['build_survivors.py', '--state', state, '--naics', a.naics, '--min-years', str(a.min_years), '--mode', m, '--datadir', d])
    print('\nDone. Files in', d)

if __name__ == '__main__':
    main()
