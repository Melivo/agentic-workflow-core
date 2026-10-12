#!/usr/bin/env python
"""Offline read-only guard for the software design principles (S00, background, skill linkage, docs).

Static text and file evidence only: a pass never proves how an agent behaves.
Exit codes: 0 pass, 1 findings, 2 usage error, 3 missing check prerequisite.
"""
import sys
sys.dont_write_bytecode = True
import argparse
import hashlib
from pathlib import Path
import re
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
SKILLS = '.apm/skills'
BASELINE = 'core-architecture/references/design-baseline.md'
BACKGROUND = 'core-architecture/references/principles-background.md'
ASSET = 'core-architecture/assets/software-design-principles.png'
ASSET_SHA256 = '878f2297c71134e8f4489a8982096c0cdfe6a3564bbec926be8fbc45b6ae1397'
ASSET_DIMENSIONS = (1672, 941)
PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'
# The user's original wording stays verbatim in the background appendix; stripped text digest.
APPENDIX_START = '# Anweisungen zum Schreiben von Code'
APPENDIX_SHA256 = '576056321844e0572aa96c335dbf03001601b3a3f44bae2084564bf677e29d87'
CS50_LINKS = (
    'https://cs50.harvard.edu/ap/2020/assets/pdfs/principles_of_good_design.pdf',
    'https://cs50.harvard.edu/ap/2026/curriculum/modules/impact_of_computing/notes/#developing-computational-artifacts',
    'https://cs50.harvard.edu/ap/2021/curriculum/x/references/mvc.pdf',
    'https://cs50.harvard.edu/x/notes/6/',
)
PRINCIPLE_HEADINGS = ('Modularität', 'Hohe Kohäsion', 'Trennung der Verantwortlichkeiten', 'Abstraktion und Information Hiding', 'Kopplung')
CODING_SKILLS = ('core-backend', 'core-frontend', 'core-mobile', 'core-database', 'core-tf-infra', 'core-debug', 'core-refactor')
# Every source that must reach S00 through a relative link from its own location.
S00_LINKED = tuple(n + '/SKILL.md' for n in ('core-plan', 'core-execute', 'core-review', 'core-architecture', 'core-devops', 'core-init-project') + CODING_SKILLS) + ('core-devops/references/development-automation.md',)
DOCS = ('README.md', 'DESIGN.md')
GROUPS = ('background', 'rules', 'integration', 'docs', 'all')
EXIT_PASS, EXIT_FINDINGS, EXIT_USAGE, EXIT_MISSING = 0, 1, 2, 3

LINK = re.compile(r'(!?)\[[^\]]*\]\(([^)\s]+)\)')
IMAGE = re.compile(r'!\[[^\]]*\]\([^)]*\)')

# Relation clauses inside the S00 section; wording may change, the relation may not.
S00_RULES = (
    ('Sollzustand', r'Verbindlicher Sollzustand'),
    ('Modularität', r'\*\*Modularität'),
    ('Kohäsion', r'\*\*Hohe Kohäsion'),
    ('Verantwortungstrennung', r'\*\*Trennung der Verantwortlichkeiten'),
    ('Information Hiding', r'\*\*Abstraktion und Information Hiding'),
    ('Kopplung', r'\*\*[^*\n]*Kopplung'),
    ('Austauschbarkeit', r'\*\*Austauschbarkeit:\*\*[^.\n]*vertragskonforme[^.\n]*ohne Anpassung unabhängiger Verbraucher'),
    ('Vertragselemente', r'Vertrag[^.\n]*Eingaben[^.\n]*Ergebnis[^.\n]*Fehler[^.\n]*Nebenwirkungen'),
    ('keine künstliche Austauschbarkeit', r'[Kk]eine künstliche Austauschbarkeit'),
    ('benannte Konstanten', r'[Bb]edeutsame Werte[^\n]*benannte Konstante'),
    ('Konstante am Eigentümer', r'verantwortlichen Eigentümer[^.\n]*nicht in einer globalen Sammelstelle'),
    ('keine Auslagerungspflicht', r'[Nn]icht jeder Wert'),
    ('Abschluss', r'\*\*Abschluss:\*\*'),
    ('Austauschfrage', r'Austauschfrage[^\n]*begründete Ausnahme'),
    ('keine Abstraktionspflicht', r'[Kk]eine Pflicht zu Interfaces'),
    ('Projektvorrang', r'Projektarchitektur hat Vorrang'),
    ('Refactoring nur im bestätigten Task', r'Refactoring[^.\n]*nur innerhalb eines dafür bestätigten Tasks[^.\n]*Safety-Net'),
    ('Beispiel ohne Freigabe', r'erteilt keine Freigabe'),
    ('Review read-only', r'Review bleibt read-only'),
    ('Urteil ohne Automutation', r'nicht automatisch eine Mutation'),
    ('übergreifender Geltungsbereich', r'Tools[^.\n]*Paket[^.\n]*Einrichtung[^.\n]*Automation'),
    ('keine Informationsfragen', r'[Nn]icht anwendbar auf beliebige Informationsfragen'),
    ('Ergebnis', r'\*\*Ergebnis:\*\*'),
)
# Scope and authorization limits the cross-cutting application must keep.
SKILL_RULES = (
    ('core-plan/SKILL.md', 'S00 bei Lösungswahl', r'S00-Basis\]\([^)]*\) bereits bei der Lösungswahl'),
    ('core-plan/SKILL.md', 'Informationsprüfungen ohne S00-Pflicht', r'Informations- oder Bereitschaftsprüfungen lösen diese Pflicht nicht aus'),
    ('core-plan/SKILL.md', 'Austausch-/Entfernungspfad', r'Tools, Paketen, Einrichtung und Automation zusätzlich Zustand, Daten, Konfiguration, Abhängigkeiten[^.\n]*Entfernungspfad'),
    ('core-execute/SKILL.md', 'S00 nur bei strukturrelevanten Tasks', r'schreibenden strukturrelevanten Tasks ergänze zusätzlich die kanonische \[S00'),
    ('core-execute/SKILL.md', 'Restprüfung vor rückstandsfrei', r'Restprüfung[^.\n]*;[^.\n]*„rückstandsfrei“ ohne diese Prüfung ist nicht zulässig'),
    ('core-database/SKILL.md', 'öffentliche Schemaverträge', r'[Bb]ewusst öffentliche Schemaverträge sind keine Leckage'),
    ('core-init-mcps/SKILL.md', 'read-only Bestandsprüfung', r'installiert oder konfiguriert nichts'),
    ('core-init-mcps/SKILL.md', 'kein Vollscan', r'Bestandsprüfung ist keine S00-Pflicht, löst keinen Vollscan aus'),
    ('core-init-mcps/SKILL.md', 'keine pauschale Planpflicht', r'zusätzlicher Core-Plan wird dadurch nicht pauschal vorgeschrieben'),
    ('core-init-project/SKILL.md', 'Readiness ohne Vollscan/Installation', r'Readiness-Preflight löst keinen Vollscan und keine Installation aus'),
    ('core-tf-infra/SKILL.md', 'keine abgeleitete Live-Aktion', r'Keine Ausführung von plan/apply/destroy'),
    ('core-tf-infra/SKILL.md', 'getrennte Live-Freigaben', r'\x60plan\x60, \x60apply\x60 und \x60destroy\x60 benötigen jeweils eine passende ausdrückliche Autorisierung'),
    ('core-devops/SKILL.md', 'Prüfen ohne Installation', r'Einrichten oder Prüfen autorisiert weder Toolinstallation'),
    ('core-devops/references/development-automation.md', 'Nur prüfen ohne Installation', r'Nur prüfen:[^\n]*Keine Installation'),
    ('core-devops/references/development-automation.md', 'belegte Restprüfung', r'„rückstandsfrei“ ist nur zulässig, wenn diese Restprüfung belegt ist'),
    ('core-debug/SKILL.md', 'minimaler Fix vor Struktur', r'minimale Fix hat Vorrang'),
)
# Scope expansions that must never appear.
SKILL_FORBIDDEN = (
    ('core-init-mcps/SKILL.md', 'Installationsschritt', r'(?m)^\s*\d+\.\s*(?:Installiere|Konfiguriere|Aktiviere)\b'),
    ('core-shared/SKILL.md', 'duplizierte S00-Regel', r'Verbindlicher Sollzustand|Austauschfrage'),
)
DOC_RULES = (
    ('Sollzustand', r'Sollzustand'),
    ('M02 abgegrenzt', r'M02[^.\n]*(?:nicht|kein|getrennt|separat|Folge)'),
    ('Prüfgrenze', r'[Ss]tatisch[^.\n]*(?:nicht|kein)[^.\n]*(?:Agent|Sprachmodell|Verhalten)'),
)


class MissingPrerequisite(Exception):
    """A required source is absent or unreadable; the check cannot judge it."""


class Sources:
    """Bounded reader over fixed paths; remembers digests for the read-only guard."""

    def __init__(self, root, skills=None):
        self.root = Path(root).resolve()
        self.skills = Path(skills).resolve() if skills else self.root / SKILLS
        self.digests = {}

    def skill(self, relative):
        return self.skills / relative

    def data(self, path):
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise MissingPrerequisite('Prüfquelle fehlt/unlesbar: ' + str(path)) from exc
        self.digests.setdefault(path, hashlib.sha256(data).hexdigest())
        return data

    def text(self, path):
        try:
            return self.data(path).decode('utf-8')
        except UnicodeDecodeError as exc:
            raise MissingPrerequisite('Prüfquelle nicht UTF-8: ' + str(path)) from exc

    def changed(self):
        return [str(p) for p, digest in self.digests.items() if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != digest]


def slug(heading):
    plain = unicodedata.normalize('NFKD', heading.replace(chr(96), '').strip().lower())
    plain = ''.join(c for c in plain if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9 \-]', '', plain).replace(' ', '-')


def section(text, prefix):
    match = re.search(r'^(#+) ' + re.escape(prefix) + r'.*$', text, re.M)
    if not match:
        return ''
    rest = text[match.end():]
    end = re.search(r'^#{1,%d} ' % len(match.group(1)), rest, re.M)
    return rest[:end.start()] if end else rest


def is_external(reference):
    """Official web sources and mail links are not package files."""
    return bool(re.match(r'^(?:https?://|mailto:)', reference))


def is_portable(reference):
    """Package-internal links must be relative: no POSIX/UNC/home root, drive letter or other URI scheme."""
    return not re.match(r'^(?:[A-Za-z][A-Za-z0-9+.-]*:|[/\\~])', reference)


def resolve(source, reference):
    return (source.parent / reference.partition('#')[0]).resolve()


def link_findings(sources, source, text, boundary):
    """Relative links and images must exist inside the boundary; Markdown anchors must exist."""
    findings = []
    for _, reference in LINK.findall(text):
        if is_external(reference) or reference.startswith('#'):
            continue
        if not is_portable(reference):
            findings.append(f'{source.name}: nicht portable absolute Referenz: {reference}')
            continue
        target, fragment = resolve(source, reference), reference.partition('#')[2]
        if not target.is_relative_to(boundary) or not target.is_file():
            findings.append(f'{source.name}: Referenz fehlt/verlässt {boundary.name}: {reference}')
        elif fragment and target.suffix == '.md':
            headings = re.findall(r'^#+ (.+?)\s*$', sources.text(target), re.M)
            if fragment not in {slug(h) for h in headings}:
                findings.append(f'{source.name}: Anker fehlt: {reference}')
    return findings


def links_to(source, text, target, image=False):
    return any(bool(bang) == image and is_portable(ref) and resolve(source, ref) == target.resolve() for bang, ref in LINK.findall(text))


def png_findings(data):
    if data[:8] != PNG_SIGNATURE or data[12:16] != b'IHDR' or len(data) < 24:
        return ['Asset ist kein gültiges PNG']
    size = (int.from_bytes(data[16:20], 'big'), int.from_bytes(data[20:24], 'big'))
    findings = [] if size == ASSET_DIMENSIONS else ['Asset hat abweichende Abmessungen: %dx%d' % size]
    if hashlib.sha256(data).hexdigest() != ASSET_SHA256:
        findings.append('Asset weicht von der freigegebenen SHA256 ab')
    return findings


def check_background(sources):
    path = sources.skill(BACKGROUND)
    text = sources.text(path)
    findings = link_findings(sources, path, text, sources.skills)
    asset = sources.skill(ASSET)
    if not links_to(path, text, asset, image=True):
        findings.append('Hintergrund bindet das Bild nicht relativ ein')
    findings += png_findings(sources.data(asset))
    if any(p.suffix.lower() == '.pdf' for p in asset.parent.iterdir()):
        findings.append('kopiertes PDF neben dem Bild')
    if not links_to(path, text, sources.skill(BASELINE)):
        findings.append('Hintergrund verlinkt S00 nicht')
    urls = [ref for _, ref in LINK.findall(text) if 'cs50.harvard.edu' in ref]
    findings += ['CS50-Link fehlt: ' + url for url in CS50_LINKS if url not in urls]
    findings += ['unerwarteter CS50-Link: ' + url for url in urls if url not in CS50_LINKS]
    start = text.find(APPENDIX_START)
    # The explanation before the verbatim appendix must stand on its own without the image.
    plain = IMAGE.sub('', text[:start] if start >= 0 else text)
    findings += ['Prinzip ohne Bild nicht erklärt: ' + h for h in PRINCIPLE_HEADINGS if not re.search(r'^#+ [^\n]*' + h, plain, re.M)]
    if not re.search(r'Bild[^.\n]*keine Voraussetzung', plain):
        findings.append('Bild nicht als entbehrliche Zusammenfassung gekennzeichnet')
    if not re.search(r'nur bei Auslegungs', plain):
        findings.append('Hintergrund nicht als bedingte Lektüre gekennzeichnet')
    if not re.search(r'[Ss]tatische[^\n]*nicht[^\n]*Agent', plain):
        findings.append('Nachweisgrenze statischer Prüfungen fehlt')
    if start < 0 or hashlib.sha256(text[start:].strip().encode('utf-8')).hexdigest() != APPENDIX_SHA256:
        findings.append('Originaltext im Anhang fehlt oder wurde verändert')
    return findings


def check_rules(sources):
    path = sources.skill(BASELINE)
    text = sources.text(path)
    s00 = section(text, 'S00')
    if not s00:
        return ['S00-Abschnitt fehlt']
    findings = ['S00-Regel fehlt: ' + label for label, pattern in S00_RULES if not re.search(pattern, s00)]
    if not links_to(path, s00, sources.skill(BACKGROUND)):
        findings.append('S00 verlinkt den Hintergrund nicht')
    findings += ['Methode fehlt: M%02d' % n for n in range(1, 11) if not re.search(r'\[M%02d [^\]]+\]\([^)]+#m%02d--' % (n, n), text)]
    return findings + link_findings(sources, path, text, sources.skills)


def check_linkage(sources):
    findings = []
    architecture, shared = sources.skill('core-architecture/SKILL.md'), sources.skill('core-shared/SKILL.md')
    if not links_to(architecture, sources.text(architecture), sources.skill(BACKGROUND)):
        findings.append('core-architecture verlinkt den Hintergrund nicht')
    if not links_to(shared, sources.text(shared), sources.skill(BACKGROUND)):
        findings.append('core-shared verlinkt den Hintergrund nicht')
    for relative in S00_LINKED:
        path = sources.skill(relative)
        text = sources.text(path)
        if not links_to(path, text, sources.skill(BASELINE)):
            findings.append(relative + ': kein relativer S00-Link')
        findings += link_findings(sources, path, text, sources.skills)
    for name in CODING_SKILLS:
        text = sources.text(sources.skill(name + '/SKILL.md'))
        duty = next((p for p in text.split('\n\n') if 'Vor der ersten Codeänderung' in p), '')
        for label, needle in (('Vorab-Pflicht', 'Vor der ersten Codeänderung'), ('Abschlussprüfung', 'zum Abschluss'), ('kein Vollscan', 'nicht als Vollscan'), ('keine ungeplanten Refactorings', 'keine ungeplanten Refactorings')):
            if needle not in duty:
                findings.append(name + ': ' + label + ' fehlt')
    for relative, label, pattern in SKILL_RULES:
        if not re.search(pattern, sources.text(sources.skill(relative))):
            findings.append(relative + ': Grenze fehlt: ' + label)
    for relative, label, pattern in SKILL_FORBIDDEN:
        if re.search(pattern, sources.text(sources.skill(relative))):
            findings.append(relative + ': unzulässig: ' + label)
    return findings


def check_docs(sources):
    findings, joined = [], []
    linked = {'Hintergrund': False, 'S00': False}
    for name in DOCS:
        path = sources.root / name
        text = sources.text(path)
        joined.append(text)
        findings += link_findings(sources, path, text, sources.root)
        linked['Hintergrund'] |= links_to(path, text, sources.skill(BACKGROUND))
        linked['S00'] |= links_to(path, text, sources.skill(BASELINE))
    findings += ['Dokumentation verlinkt ' + k + ' nicht' for k, ok in linked.items() if not ok]
    text = '\n'.join(joined)
    return findings + ['Dokumentation: ' + label + ' fehlt' for label, pattern in DOC_RULES if not re.search(pattern, text)]


CHECKS = {
    'background': (check_background,),
    'rules': (check_rules,),
    'integration': (check_background, check_rules, check_linkage),
    'docs': (check_docs,),
}
CHECKS['all'] = tuple(dict.fromkeys(c for g in ('integration', 'docs') for c in CHECKS[g]))


def run(group, root=ROOT, skills=None):
    """Return (findings, missing); never writes, fixes, installs or uses the network."""
    sources = Sources(root, skills)
    findings, missing = [], []
    for check in CHECKS[group]:
        try:
            findings += check(sources)
        except MissingPrerequisite as exc:
            missing.append(check.__name__ + ': ' + str(exc))
    findings += ['Read-only-Guard: Quelle verändert: ' + p for p in sources.changed()]
    return findings, missing


def contract_violations(reference, candidate, cases):
    """Compare two implementations only by public contract: result, error and recorded side effects.

    Each implementation is called as impl(effects, *args) and appends its side effects to effects.
    Internal structure, including branch count, is deliberately not inspected.
    """
    def observe(implementation, args):
        effects = []
        try:
            return 'result', implementation(effects, *args), effects
        except Exception as exc:
            return 'error', (type(exc), str(exc)), effects
    return ['Vertragsabweichung bei %r: %r != %r' % (args, observe(reference, args), observe(candidate, args)) for args in cases if observe(reference, args) != observe(candidate, args)]


def main(argv=None, root=ROOT, skills=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--group', choices=GROUPS, required=True)
    args = parser.parse_args(argv)
    findings, missing = run(args.group, root, skills)
    for item in missing:
        print('MISSING:', item, file=sys.stderr)
    for item in findings:
        print('FINDING:', item, file=sys.stderr)
    if missing:
        return EXIT_MISSING
    if findings:
        return EXIT_FINDINGS
    print('PASS', args.group, '- statische Text-/Dateievidenz, kein Nachweis von Agentenverhalten')
    return EXIT_PASS


if __name__ == '__main__':
    sys.exit(main())
