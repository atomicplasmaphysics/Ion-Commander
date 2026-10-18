"""
Creates CHANGELOG.md automatically from the git commit messages.

Commit subjects starting with a version ("v0.1.52 ...", "v0.1.40b ...") start a new version entry, the commit body is
added as details. Commits without version are listed under the next newer version ("Unversioned changes" if there is
none). Merge commits are skipped.

Usage (from the project folder):
    python -m Utility.Changelog                      # writes CHANGELOG.md
    python -m Utility.Changelog --next-message FILE  # also includes the commit that is about to be created
                                                     # (FILE contains its commit message, e.g. git commit -F FILE)
"""

import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path


PROJECT_FOLDER = Path(__file__).parents[1]
CHANGELOG_FILE = PROJECT_FOLDER / 'CHANGELOG.md'

VERSION_PATTERN = re.compile(r'^v(\d+\.\d+\.\d+[a-z]?)\b\s*(.*)$')
SEPARATOR = '\x1e'  # record separator, does not appear in commit messages
FIELD = '\x1f'      # unit separator

# trailer lines that are not part of the change description
IGNORED_LINES = re.compile(r'^(Co-Authored-By|Claude-Session|Signed-off-by):', re.IGNORECASE)


def readCommits() -> list[tuple[str, str, str, str]]:
    """Returns list of (hash, date, subject, body) from newest to oldest, without merge commits"""

    output = subprocess.run(
        ['git', 'log', '--no-merges', f'--format=%h{FIELD}%ad{FIELD}%s{FIELD}%b{SEPARATOR}', '--date=short'],
        cwd=PROJECT_FOLDER,
        capture_output=True,
        text=True,
        encoding='utf-8',
        check=True
    ).stdout

    commits = []
    for record in output.split(SEPARATOR):
        record = record.strip('\n')
        if not record:
            continue
        commit_hash, date, subject, body = (record.split(FIELD) + ['', '', '', ''])[:4]
        commits.append((commit_hash, date, subject.strip(), body.strip()))
    return commits


def cleanBody(body: str) -> str:
    """Removes trailers (Co-Authored-By, ...) from a commit body"""

    lines = [line.rstrip() for line in body.splitlines() if not IGNORED_LINES.match(line.strip())]
    return '\n'.join(lines).strip()


def createChangelog(commits: list[tuple[str, str, str, str]]) -> str:
    """
    Creates the markdown text of the changelog

    :param commits: list of (hash, date, subject, body) from newest to oldest
    """

    entries: list[dict] = []
    pending: list[tuple[str, str, str, str]] = []  # commits without version (belong to the next newer version)

    # oldest first, so commits without version can be attached to the next version
    for commit_hash, date, subject, body in reversed(commits):
        match = VERSION_PATTERN.match(subject)
        if match is None:
            pending.append((commit_hash, date, subject, body))
            continue

        version, title = match.groups()
        entry = {'version': version, 'date': date, 'items': []}
        for item_hash, _, item_subject, _ in pending:
            entry['items'].append(f'- {item_subject} ({item_hash})')
        pending = []
        entry['items'].append({'title': title or '(no description)', 'hash': commit_hash, 'body': cleanBody(body)})
        entries.append(entry)

    text = '# Changelog\n\n'
    text += '*Automatically created from the commit messages with `python -m Utility.Changelog` - do not edit by hand.*\n\n'

    if pending:
        text += '## Unversioned changes\n\n'
        text += '\n'.join(f'- {subject} ({commit_hash})' for commit_hash, _, subject, _ in reversed(pending)) + '\n\n'

    for entry in reversed(entries):
        text += f'## v{entry["version"]} ({entry["date"]})\n\n'
        for item in entry['items']:
            if isinstance(item, str):
                text += f'{item}\n'
                continue
            text += f'**{item["title"]}** ({item["hash"]})\n'
            if item['body']:
                text += '\n' + item['body'] + '\n'
        text += '\n'

    return text


def main(arguments: list[str]) -> int:
    commits = readCommits()

    if '--next-message' in arguments:
        message_file = Path(arguments[arguments.index('--next-message') + 1])
        message = message_file.read_text(encoding='utf-8').strip()
        subject, _, body = message.partition('\n')
        commits.insert(0, ('next', datetime.now().strftime('%Y-%m-%d'), subject.strip(), body.strip()))

    CHANGELOG_FILE.write_text(createChangelog(commits), encoding='utf-8', newline='\r\n')
    print(f'Changelog with {len(commits)} commits written to {CHANGELOG_FILE}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
