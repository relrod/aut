#!/usr/bin/env python

import re
import sys
import yaml

MAX_MATRIX_ENTRIES = 256

YAML = {
    'name': 'Ansible User Artifact Tests',
    'on': {
        'push': None,
        'pull_request': None,
        'schedule': [
            { 'cron': '0 0 * * *', }
        ],
    },
    'jobs': {
        'build': {
            'runs-on': 'ubuntu-latest',
            'timeout-minutes': 20,  # TODO: config?
            'strategy': {
                # We want to see all failures.
                'fail-fast': False,
                'matrix': {
                    'include': [],
                },
            },
            'steps': [
                {
                    'name': 'Clone repo',
                    'uses': 'actions/checkout@v2',
                },
                {
                    'name': 'Build container image',
                    'run': 'docker build -t "aut-${{ matrix.dockerfile }}" '
                           '${{ matrix.build_args }}'
                           '-f "dockerfiles/${{ matrix.dockerfile }}" .',
                },
                {
                    'name': 'Run tests',
                    'run': 'docker run -t '
                           '-e PYTHONPATH="/opt/pre/${{ matrix.product }}-'
                           '${{ matrix.version }}/lib" '
                           '-e PRE="${{ matrix.pre }}" '
                           '-e PRODUCT="${{ matrix.product }}" '
                           '-e VERSION="${{ matrix.version }}" '
                           '-e PPA="${{ matrix.ppa }}" '
                           '-e DOCKERFILE="${{ matrix.dockerfile }}" '
                           '"aut-${{ matrix.dockerfile }}"'
                },
            ],
        },
        'macos-build': {
            # This is kind of a hack, it's not a "dockerfile" but we use the key
            'runs-on': '${{ matrix.dockerfile }}',
            'timeout-minutes': 20,  # TODO: config?
            'strategy': {
                # We want to see all failures.
                'fail-fast': False,
                'matrix': {
                    'include': [],
                },
            },
            'steps': [
                {
                    'name': 'Clone repo',
                    'uses': 'actions/checkout@v2',
                },
                {
                    'name': 'Run tests',
                    'run': 'bash entrypoint.sh',
                    'env': {
                        'PRE': '${{ matrix.pre }}',
                        'PRODUCT': '${{ matrix.product }}',
                        'VERSION': '${{ matrix.version }}',
                        'PPA': '${{ matrix.ppa }}',
                        'DOCKERFILE': '${{ matrix.dockerfile }}',
                    },
                },
            ],
        },
    },
}

def fill_matrix(job, data, entries):
    for os_env, pres in entries.items():
        for pre_dict in pres:
            for pre, premeta in pre_dict.items():
                for product in ('ansible', 'ansible-base', 'ansible-core'):
                    if premeta:
                        if product in premeta.get('exclude', []):
                            continue

                    # Handle the case where we define a product, but no versions
                    # for it.
                    if data[product] is None:
                        continue

                    for version in data[product]:
                        matrix_entry = {
                            'dockerfile': os_env,
                            'version': version,
                            'product': product,
                            'pre': pre,
                            'build_args': '',
                        }
                        if premeta:
                            version_re = premeta.get('version_re', '')
                            if version_re and not re.search(version_re, version):
                                continue

                            if 'rc' in premeta.get('exclude', []) and 'rc' in version:
                                continue

                            if 'beta' in premeta.get('exclude', []) and 'b' in version:
                                continue

                            build_args = premeta.get('build-args')
                            if build_args:
                                for k, v in build_args.items():
                                    matrix_entry['build_args'] += \
                                        ' --build-arg %s=%s' % (k, v)

                            env = premeta.get('env', {})
                            if env:
                                for k, v in env.items():
                                    matrix_entry[k] = v
                        YAML['jobs'][job]['strategy']['matrix']['include'].append(matrix_entry)


def main():
    with open('matrix.yml', 'r') as f:
        data = yaml.safe_load(f.read())

    fill_matrix('build', data, data['dockerfiles'])
    fill_matrix('macos-build', data, data['macOS'])

    total_entries = \
        len(YAML['jobs']['build']['strategy']['matrix']['include']) + \
        len(YAML['jobs']['macos-build']['strategy']['matrix']['include'])

    print(yaml.dump(YAML))
    print(
        'Matrix entries in use: %d/%d' % (total_entries, MAX_MATRIX_ENTRIES),
        file=sys.stderr)

if __name__ == '__main__':
    main()
