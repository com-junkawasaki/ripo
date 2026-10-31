"""AWAI-127 bounded research measurement of an existing native backend.

No server, model, route, authority or scheduler is installed. The remote helper
runs from stdin, uses localhost only, and emits JSONL telemetry. This Python
research driver is not a Kotoba runtime or an enforcement qualification.
"""
import argparse
import concurrent.futures
import hashlib
import http.client
import json
import math
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time


def guard_reasons(sample, baseline_swap=0):
    required = ('cpu_idle_pct', 'memory_pressure_free_pct', 'wired_compressor_pct',
                'swap_used_MiB', 'thermal_warning', 'disk_free_GiB')
    if any(sample.get(k) is None for k in required) or any(
            type(sample.get(k)) not in (int, float) or not math.isfinite(sample[k]) or sample[k] < 0
            for k in required if k != 'thermal_warning') or type(sample.get('thermal_warning')) is not bool:
        return ['missing_guard_sensor']
    reasons = []
    if sample['cpu_idle_pct'] < 25:
        reasons.append('cpu_idle_below_25pct')
    if sample['memory_pressure_free_pct'] < 30:
        reasons.append('memory_pressure_free_below_30pct')
    if sample['wired_compressor_pct'] > 75:
        reasons.append('wired_compressor_above_75pct')
    if sample['swap_used_MiB'] - baseline_swap > 64:
        reasons.append('swap_growth_above_64MiB')
    if sample['thermal_warning']:
        reasons.append('thermal_warning')
    if sample['disk_free_GiB'] < 10:
        reasons.append('disk_free_below_10GiB')
    return reasons


def validate_output(text):
    try:
        d = json.loads(text)
    except (TypeError, ValueError):
        return False
    return d == {'cpu_reserve_pct': 25, 'memory_reserve_pct': 25,
                 'gpu_busy': 'unmeasured', 'energy_per_job': 'unmeasured'}


def command(args):
    return subprocess.check_output(args, text=True, timeout=5)


def sample():
    # All are observed proxies. memory_pressure -Q is NOT allocatable bytes.
    top = command(['top', '-l', '2', '-s', '1', '-n', '0'])
    vm = command(['vm_stat'])
    pressure = command(['memory_pressure', '-Q'])
    thermal = command(['pmset', '-g', 'therm'])
    disk = command(['df', '-Pk', '/System/Volumes/Data']).splitlines()[-1].split()
    mem = int(command(['sysctl', '-n', 'hw.memsize']).strip())
    swap = command(['sysctl', '-n', 'vm.swapusage'])
    page = int(re.search(r'page size of (\d+)', vm).group(1))
    counts = {m.group(1): int(m.group(2)) for m in re.finditer(r'^([^:\n]+):\s+(\d+)\.', vm, re.M)}
    idle = re.findall(r'([\d.]+)% idle', top)
    free = re.search(r'free percentage:\s*(\d+)%', pressure)
    used = re.search(r'used\s*=\s*([\d.]+)([MG])', swap)
    thermal_known = 'No thermal warning level has been recorded' in thermal
    return {'monotonic': time.monotonic(), 'cpu_idle_pct': float(idle[-1]) if idle else None,
            'memory_pressure_free_pct': float(free.group(1)) if free else None,
            'wired_compressor_pct': 100 * page * (counts['Pages wired down'] +
                                      counts['Pages occupied by compressor']) / mem if
                                      all(k in counts for k in ['Pages wired down', 'Pages occupied by compressor']) else None,
            'swap_used_MiB': float(used.group(1)) * (1024 if used.group(2) == 'G' else 1) if used else None,
            'thermal_warning': False if thermal_known else True,
            'disk_free_GiB': int(disk[3]) / 1024**2}


def get_json(port, path, timeout=3):
    c = http.client.HTTPConnection('127.0.0.1', port, timeout=timeout)
    try:
        c.request('GET', path); r = c.getresponse()
        if r.status != 200:
            raise RuntimeError(f'GET {path}: HTTP {r.status}')
        return json.loads(r.read(65536))
    finally:
        c.close()


def emit(value):
    print(json.dumps(value, ensure_ascii=False, allow_nan=False), flush=True)


def remote_program(config):
    source = Path(__file__).read_text()
    source = source.rsplit("\nif __name__ == '__main__':", 1)[0]
    source += '\ntry:\n    remote_run(' + repr(config) + ')\n'
    source += "except Exception as error:\n    emit({'event':'stop','reason':['remote_exception'],'error':type(error).__name__,'detail':str(error)[:160]})\n"
    compile(source, 'remote-measurement-helper', 'exec')
    return source


def evidence_status(events):
    if not events:
        raise ValueError('empty measurement evidence')
    if events[-1].get('event') not in ('complete', 'stop'):
        raise ValueError('missing terminal measurement record')
    return events[-1]['event']


def remote_run(config):
    port = config['port']
    emit({'event': 'protocol', 'protocol': config, 'qualification': 'observed_headroom_proxies_only'})
    baseline = [sample() for _ in range(3)]
    for s in baseline:
        emit({'event': 'baseline_sample', 'sample': s})
    baseline_swap = baseline[0]['swap_used_MiB']
    for s in baseline:
        why = guard_reasons(s, baseline_swap)
        if why:
            emit({'event': 'stop', 'reason': why, 'phase': 'baseline'}); return
    models = get_json(port, '/v1/models')
    model = models['data'][0]['id']
    if 'Ternary-Bonsai-2-27B-PTQ1_0.gguf' not in model:
        emit({'event': 'stop', 'reason': ['unexpected_model']}); return
    for local_index, use_cache in enumerate(config['cache_sequence']):
        index = config.get('trial_offset', 0) + local_index
        pre = sample()
        emit({'event': 'pre_sample', 'trial': index, 'sample': pre})
        why = guard_reasons(pre, baseline_swap)
        slots = get_json(port, '/slots')
        if len(slots) != 1 or any(s.get('is_processing') is not False for s in slots):
            why.append('backend_not_single_idle_slot')
        if why:
            emit({'event': 'stop', 'reason': why, 'phase': 'admission'}); return
        body = {'model': model, 'messages': config['messages'], 'max_tokens': 96,
                'temperature': 0, 'seed': 42, 'cache_prompt': use_cache, 'stream': False,
                'chat_template_kwargs': {'enable_thinking': False},
                'response_format': {'type': 'json_object'}}
        if use_cache is None:
            del body['cache_prompt']  # measure the server's actual default
        payload = json.dumps(body).encode()
        connection = http.client.HTTPConnection('127.0.0.1', port, timeout=90)
        start = time.monotonic()
        def request():
            try:
                connection.request('POST', '/v1/chat/completions', payload,
                                   {'Content-Type': 'application/json'})
                response = connection.getresponse()
                raw = response.read(262144)
                if response.status != 200:
                    raise RuntimeError(f'completion HTTP {response.status}')
                result = json.loads(raw)
                result['_driver_http_seconds'] = time.monotonic() - start
                return result
            finally:
                connection.close()
        pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = pool.submit(request)
        violations, telemetry = [], []
        while not future.done():
            current = sample(); telemetry.append(current)
            emit({'event': 'during_sample', 'trial': index, 'sample': current})
            violations.extend(guard_reasons(current, baseline_swap))
            if time.monotonic() - start > 90:
                violations.append('trial_wall_timeout')
            if violations:
                try:
                    connection.sock.shutdown(socket.SHUT_RDWR)
                except (AttributeError, OSError):
                    pass
                connection.close()
                break
            time.sleep(1)
        try:
            result = future.result(timeout=5 if violations else 95)
            text = result.get('choices', [{}])[0].get('message', {}).get('content')
            record = {'event': 'trial_result', 'trial': index, 'cache_prompt': use_cache,
                      'seconds': result['_driver_http_seconds'], 'quality_pass': validate_output(text),
                      'output': text, 'usage': result.get('usage'), 'timings': result.get('timings'),
                      'finish_reason': result.get('choices', [{}])[0].get('finish_reason'),
                      'violations': sorted(set(violations))}
            emit(record)
        except Exception as e:
            emit({'event': 'trial_error', 'trial': index, 'error': type(e).__name__,
                  'detail': str(e)[:150], 'violations': sorted(set(violations))})
            violations.append('request_or_quality_unqualified')
        finally:
            pool.shutdown(wait=False, cancel_futures=True)
        # Disconnect/timeout is never proof of server-side cancellation.
        after = get_json(port, '/slots', timeout=10)
        emit({'event': 'post_slots', 'trial': index,
              'slots': [{k: s.get(k) for k in ['id', 'is_processing', 'n_ctx']} for s in after]})
        if violations or any(s.get('is_processing') is not False for s in after):
            emit({'event': 'stop', 'reason': sorted(set(violations)) or ['server_state_unknown']}); return
        if not record['quality_pass']:
            emit({'event': 'stop', 'reason': ['output_quality_failed']}); return
    emit({'event': 'complete', 'trials': len(config['cache_sequence'])})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--ssh-host', required=True)
    p.add_argument('--tailscale-address', required=True)
    p.add_argument('--protocol', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--execute', action='store_true', required=True)
    p.add_argument('--trial-index', type=int)
    args = p.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._@-]*', args.ssh_host):
        p.error('invalid configured SSH host')
    if not re.fullmatch(r'100\.\d+\.\d+\.\d+', args.tailscale_address):
        p.error('explicit Tailscale IPv4 address required')
    cfg = json.loads(args.protocol.read_text())
    if args.trial_index is not None:
        if not 0 <= args.trial_index < len(cfg['cache_sequence']):
            p.error('trial index outside registered sequence')
        cfg['trial_offset'] = args.trial_index
        cfg['cache_sequence'] = [cfg['cache_sequence'][args.trial_index]]
    code = remote_program(cfg)
    cmd = ['ssh', '-oBatchMode=yes', '-oStrictHostKeyChecking=yes', '-oConnectTimeout=5',
           '-oServerAliveInterval=5', '-oServerAliveCountMax=2',
           '-oHostname=' + args.tailscale_address, args.ssh_host, 'python3', '-']
    args.output.parent.mkdir(parents=True, exist_ok=True)
    os.umask(0o077)
    events = []
    with args.output.open('x') as log:
        process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True)
        process.stdin.write(code); process.stdin.close()
        for line in process.stdout:
            log.write(line); log.flush()
            try:
                d = json.loads(line)
                events.append(d)
                if d.get('event') in ['trial_result', 'trial_error', 'stop', 'complete']:
                    print(json.dumps({k: v for k, v in d.items() if k != 'output'}), flush=True)
            except ValueError:
                print('non-JSON remote output; evidence unqualified', flush=True)
        error = process.stderr.read(2000)
        args.output.with_suffix(args.output.suffix + '.stderr').write_text(error)
        status = process.wait()
        if status:
            raise SystemExit(f'SSH failed ({status}): {error[:200]}')
        try:
            state = evidence_status(events)
            print('Measurement terminal state: ' + state, flush=True)
            if state == 'stop':
                raise SystemExit(3)
        except ValueError as e:
            raise SystemExit(str(e))


if __name__ == '__main__':
    main()
