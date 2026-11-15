"""Offline request-serialization probe; run ONLY in a --network none container.

The loopback server rejects every request. No real key, model response, benchmark
task, or generated repository is involved. Output contains settings, not prompts.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading


def main():
    source, destination = Path(sys.argv[1]), Path(sys.argv[2])
    sys.path.insert(0, str(source))
    with tempfile.TemporaryDirectory(prefix='codex-settings-probe-') as temp:
        os.chdir(temp)
        from codex_backend.runner import generation_args, resolve_model
        os.environ['NL2REPO_API_KEY'] = 'offline-placeholder'
        configured = {'moduleName': 'gpt-6.1-sol', 'protocol': 'openai-responses',
                      'baseUrl': 'https://example.invalid/v1', 'contextWindow': 200000,
                      'reasoningEffort': 'medium'}
        model, _ = resolve_model(configured)
        requests = []

        class RejectRequests(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                self.send_error(404, 'Offline audit: no model service exists')

            def do_POST(self):
                raw = self.rfile.read(int(self.headers.get('Content-Length', 0)))
                body = json.loads(raw)
                selected = {key: body[key] for key in ('model', 'reasoning', 'max_output_tokens',
                            'max_tokens', 'max_completion_tokens', 'temperature', 'top_p', 'stream') if key in body}
                requests.append({'path': self.path, 'body_keys': sorted(body), 'settings': selected})
                response = b'{"error":{"message":"Offline audit rejects all requests","type":"invalid_request_error"}}'
                self.send_response(401)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(response)))
                self.end_headers()
                self.wfile.write(response)

        server = ThreadingHTTPServer(('127.0.0.1', 0), RejectRequests)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        cases = {}
        try:
            for name, extra in [('configured', []), ('candidate_output_override', ['-c', 'model_max_output_tokens=16384'])]:
                home = Path(temp) / name
                home.mkdir()
                local_model = {**model, 'base_url': f'http://127.0.0.1:{server.server_port}/v1'}
                arguments = generation_args('offline-image', Path(temp), home, local_model)
                cli = ['codex', *arguments[arguments.index('offline-image') + 1:-1], *extra,
                       'Offline settings audit. No task implementation is requested.']
                before = len(requests)
                completed = subprocess.run(cli, cwd=temp, env={**os.environ, 'HOME': str(home),
                    'CODEX_HOME': str(home), 'NL2REPO_MODEL_API_KEY': 'offline-placeholder'},
                    capture_output=True, text=True, timeout=45)
                events = []
                for line in completed.stdout.splitlines():
                    try:
                        events.append(json.loads(line).get('type'))
                    except (ValueError, AttributeError):
                        continue
                cases[name] = {'cli_exit_code': completed.returncode, 'requests': requests[before:],
                               'event_types': events, 'extra_cli_settings': extra}
                if not requests[before:]:
                    cases[name]['startup_diagnostic'] = completed.stderr[-3000:]
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=2)
        report = {'cli_version': subprocess.check_output(['codex', '--version'], text=True).strip(),
                  'configured_model': model, 'generation_performed': False,
                  'external_model_calls': 0, 'all_local_requests_rejected_with': 401, 'cases': cases}
        destination.write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report, indent=2))
        return 0 if all(v['requests'] and v['cli_exit_code'] != 0 for v in cases.values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
