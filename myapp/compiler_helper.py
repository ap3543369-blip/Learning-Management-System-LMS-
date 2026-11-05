import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from django.conf import settings


# Judge0 CE language IDs verified against the official CE /languages endpoint.
# We deliberately use stable modern runtimes rather than whichever runtime is
# newest on a given day, so student code behaves consistently.
LANGUAGES = {
    'python': {
        'name': 'Python 3', 'runtime': 'Python 3.13.2', 'file': 'main.py', 'judge0_id': 109,
    },
    'java': {
        'name': 'Java', 'runtime': 'JDK 17.0.6', 'file': 'Main.java', 'judge0_id': 91,
    },
    'cpp': {
        'name': 'C++', 'runtime': 'GCC 14.1.0', 'file': 'main.cpp', 'judge0_id': 105,
    },
    'c': {
        'name': 'C', 'runtime': 'GCC 14.1.0', 'file': 'main.c', 'judge0_id': 103,
    },
    'javascript': {
        'name': 'JavaScript', 'runtime': 'Node.js 22.08.0', 'file': 'main.js', 'judge0_id': 102,
    },
    'php': {
        'name': 'PHP', 'runtime': 'PHP 8.3.11', 'file': 'main.php', 'judge0_id': 98,
    },
    'csharp': {
        'name': 'C#', 'runtime': 'Mono 6.6', 'file': 'Main.cs', 'judge0_id': 51,
    },
    'go': {
        'name': 'Go', 'runtime': 'Go 1.23.5', 'file': 'main.go', 'judge0_id': 107,
    },
    'rust': {
        'name': 'Rust', 'runtime': 'Rust 1.85.0', 'file': 'main.rs', 'judge0_id': 108,
    },
    'ruby': {
        'name': 'Ruby', 'runtime': 'Ruby 2.7.0', 'file': 'main.rb', 'judge0_id': 72,
    },
    'typescript': {
        'name': 'TypeScript', 'runtime': 'TypeScript 5.6.2', 'file': 'main.ts', 'judge0_id': 101,
    },
    'bash': {
        'name': 'Bash', 'runtime': 'Bash 5.0.0', 'file': 'main.sh', 'judge0_id': 46,
    },
}

STARTER_CODE = {
    'python': 'print("Hello, NOU e-Gyan!")\n',
    'java': 'public class Main {\n    public static void main(String[] args) {\n        System.out.println("Hello, NOU e-Gyan!");\n    }\n}\n',
    'cpp': '#include <iostream>\nusing namespace std;\n\nint main() {\n    cout << "Hello, NOU e-Gyan!" << endl;\n    return 0;\n}\n',
    'c': '#include <stdio.h>\n\nint main() {\n    printf("Hello, NOU e-Gyan!\\n");\n    return 0;\n}\n',
    'javascript': 'console.log("Hello, NOU e-Gyan!");\n',
    'php': '<?php\necho "Hello, NOU e-Gyan!\\n";\n?>\n',
    'csharp': 'using System;\n\nclass Program {\n    static void Main() {\n        Console.WriteLine("Hello, NOU e-Gyan!");\n    }\n}\n',
    'go': 'package main\n\nimport "fmt"\n\nfunc main() {\n    fmt.Println("Hello, NOU e-Gyan!")\n}\n',
    'rust': 'fn main() {\n    println!("Hello, NOU e-Gyan!");\n}\n',
    'ruby': 'puts "Hello, NOU e-Gyan!"\n',
    'typescript': 'console.log("Hello, NOU e-Gyan!");\n',
    'bash': 'echo "Hello, NOU e-Gyan!"\n',
}


def _api_config():
    """Return Judge0 endpoint + auth headers.

    Default is Judge0 CE public preview. If a RapidAPI key is provided, the
    exact same portal code automatically uses Judge0's managed RapidAPI route.
    A custom/self-hosted Judge0 URL can also be supplied with JUDGE0_API_URL.
    """
    rapid_key = (getattr(settings, 'JUDGE0_RAPID_API_KEY', '') or '').strip()
    custom_url = (getattr(settings, 'JUDGE0_API_URL', '') or '').strip()

    if rapid_key:
        return (
            'https://judge0-ce.p.rapidapi.com',
            {
                'x-rapidapi-key': rapid_key,
                'x-rapidapi-host': 'judge0-ce.p.rapidapi.com',
                'Content-Type': 'application/json',
            },
            'Judge0 CE (RapidAPI)',
        )

    endpoint = (custom_url or 'https://ce.judge0.com').rstrip('/')
    headers = {'Content-Type': 'application/json'}
    token = (getattr(settings, 'JUDGE0_AUTH_TOKEN', '') or '').strip()
    if token:
        header = (getattr(settings, 'JUDGE0_AUTH_HEADER', '') or 'X-Auth-Token').strip()
        headers[header] = token
    return endpoint, headers, 'Judge0 CE'


def _session():
    # GET polling can safely be retried. POST is intentionally not retried by
    # urllib3 because an ambiguous network failure could otherwise create a
    # duplicate Judge0 submission.
    retries = Retry(
        total=3,
        connect=2,
        read=2,
        status=2,
        backoff_factor=0.7,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({'GET'}),
        raise_on_status=False,
    )
    session = requests.Session()
    session.mount('https://', HTTPAdapter(max_retries=retries))
    session.mount('http://', HTTPAdapter(max_retries=retries))
    return session


def _friendly_http_error(response, action):
    try:
        payload = response.json()
        detail = payload.get('error') if isinstance(payload, dict) else payload
        if not detail and isinstance(payload, dict):
            detail = payload.get('message') or payload
    except Exception:
        detail = response.text.strip()

    if response.status_code == 429:
        return 'Judge0 is temporarily rate-limiting requests. Please wait a few seconds and run the code again.'
    if response.status_code in (401, 403):
        return 'Judge0 authentication was rejected. Check the configured Judge0 API credentials.'
    suffix = f': {detail}' if detail else ''
    return f'Judge0 {action} failed with HTTP {response.status_code}{suffix}'


def _clean(value):
    return '' if value is None else str(value)


def _result_from_payload(data, language_data, provider):
    stdout = _clean(data.get('stdout'))
    stderr = _clean(data.get('stderr'))
    compile_output = _clean(data.get('compile_output'))
    message = _clean(data.get('message'))
    status_obj = data.get('status') or {}
    status = _clean(status_obj.get('description')) or 'Finished'

    chunks = []
    if stdout:
        chunks.append(stdout.rstrip())
    if compile_output:
        chunks.append(compile_output.rstrip())
    if stderr:
        chunks.append(stderr.rstrip())
    if message:
        chunks.append(message.rstrip())
    output = '\n'.join(chunk for chunk in chunks if chunk)
    if not output:
        output = '(program finished without output)'

    return {
        'output': output,
        'stdout': stdout,
        'stderr': stderr,
        'compile_output': compile_output,
        'message': message,
        'status': status,
        'time': _clean(data.get('time')),
        'memory': _clean(data.get('memory')),
        'language_name': language_data['name'],
        'runtime': language_data['runtime'],
        'provider': provider,
    }


def run_code(language, source_code, stdin=''):
    """Compile/run student code with the official Judge0 CE HTTP API.

    The previous implementation used a 10-second read timeout, which made the
    UI fail whenever the public Judge0 service was briefly slow. This version
    creates an asynchronous submission, then polls its token with retries and
    a larger bounded timeout.
    """
    language_data = LANGUAGES.get(language)
    if not language_data:
        return None, 'Unsupported programming language.'
    if not (source_code or '').strip():
        return None, 'Please write some code before running it.'

    endpoint, headers, provider = _api_config()
    connect_timeout = int(getattr(settings, 'JUDGE0_CONNECT_TIMEOUT', 10))
    read_timeout = int(getattr(settings, 'JUDGE0_READ_TIMEOUT', 60))
    max_wait = int(getattr(settings, 'JUDGE0_MAX_WAIT_SECONDS', 55))
    poll_interval = float(getattr(settings, 'JUDGE0_POLL_INTERVAL', 1.0))

    submission = {
        'source_code': source_code,
        'language_id': language_data['judge0_id'],
        'stdin': stdin or '',
        'cpu_time_limit': 5,
        'wall_time_limit': 12,
        'memory_limit': 128000,
    }

    session = _session()
    try:
        try:
            response = session.post(
                f'{endpoint}/submissions',
                params={'base64_encoded': 'false', 'wait': 'false'},
                headers=headers,
                json=submission,
                timeout=(connect_timeout, read_timeout),
            )
        except requests.Timeout:
            return None, (
                'Judge0 did not respond in time while creating the submission. '
                'Please click Run Code once more. If this happens repeatedly, the public Judge0 service is busy.'
            )
        except requests.RequestException as exc:
            return None, f'Judge0 could not be reached: {exc}'

        if response.status_code not in (200, 201):
            return None, _friendly_http_error(response, 'submission')

        try:
            token = response.json().get('token')
        except Exception:
            token = None
        if not token:
            return None, 'Judge0 accepted the request but did not return a submission token.'

        deadline = time.monotonic() + max_wait
        fields = 'stdout,stderr,compile_output,message,status,time,memory'
        while time.monotonic() < deadline:
            try:
                result_response = session.get(
                    f'{endpoint}/submissions/{token}',
                    params={'base64_encoded': 'false', 'fields': fields},
                    headers=headers,
                    timeout=(connect_timeout, read_timeout),
                )
            except requests.Timeout:
                # Keep within the overall deadline. A single slow poll should
                # not immediately kill a student's run.
                if time.monotonic() >= deadline:
                    break
                time.sleep(poll_interval)
                continue
            except requests.RequestException as exc:
                return None, f'Judge0 result could not be read: {exc}'

            if result_response.status_code != 200:
                return None, _friendly_http_error(result_response, 'result request')

            try:
                data = result_response.json()
            except Exception:
                return None, 'Judge0 returned an invalid result response.'

            status_id = (data.get('status') or {}).get('id')
            if status_id not in (1, 2):  # 1=In Queue, 2=Processing
                return _result_from_payload(data, language_data, provider), None

            time.sleep(poll_interval)

        return None, (
            f'Judge0 is still processing this program after {max_wait} seconds. '
            'Please run it again in a moment.'
        )
    finally:
        session.close()
