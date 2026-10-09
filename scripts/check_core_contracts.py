#!/usr/bin/env python
"""Offline report-only contract checks; static evidence is not a harness test."""
import sys
sys.dont_write_bytecode = True
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import unittest
try:
    import yaml
except ImportError:
    yaml = None

ROOT = Path(__file__).resolve().parents[1]
PLAN = '.agentic-workflow/plans/004-core-goals-milestones-and-synergies.md'
GROUP_TASK = dict(milestones='T02', shared='T03', workflows='T04', domains='T05', setup='T06', docs='T07')
GROUPS = ('selftest', *GROUP_TASK, 'all')

class ContractError(ValueError):
    pass

def require(condition, message):
    if not condition:
        raise ContractError(message)

def load_yaml(text):
    require(yaml is not None, 'PyYAML fehlt; keine Installation ausgeführt')
    class Loader(yaml.SafeLoader):
        pass
    def mapping(loader, node, deep=False):
        result = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node, deep=deep)
            require(isinstance(key, (str, int, float, bool)), 'ungültiger YAML-Schlüssel')
            require(key not in result, 'doppelter YAML-Schlüssel: ' + str(key))
            result[key] = loader.construct_object(value_node, deep=deep)
        return result
    Loader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)
    try:
        return yaml.load(text, Loader=Loader)
    except yaml.YAMLError as exc:
        raise ContractError('ungültiges/sicherheitswidriges YAML: ' + str(exc)) from exc

def blocks(text):
    fence = chr(96) * 3
    return [load_yaml(x) for x in re.findall(r'^\s*' + fence + r'ya?ml[^\n]*\n(.*?)^\s*' + fence, text, re.M | re.S)]

def unique(items, label):
    require(isinstance(items, list), label + ': Liste erforderlich')
    require(len(items) == len(set(items)), label + ': doppelte Kennungen')

def graph(nodes):
    visiting, done = set(), set()
    def visit(key):
        require(key in nodes, 'fehlende Abhängigkeit: ' + str(key))
        require(key not in visiting, 'zyklische Abhängigkeit: ' + str(key))
        if key in done:
            return
        visiting.add(key)
        unique(nodes[key], 'dependencies')
        for dep in nodes[key]:
            visit(dep)
        visiting.remove(key)
        done.add(key)
    for key in nodes:
        visit(key)

def validate_plan(data, agents=None, tools=None):
    require(isinstance(data, dict) and data.get('schema') == 'plan/v1', 'plan/v1 erforderlich')
    require(data.get('status') == 'Confirmed', 'Plan nicht bestätigt')
    tasks = data.get('tasks')
    require(isinstance(tasks, list) and tasks, 'Tasks fehlen')
    unique([t['id'] for t in tasks], 'tasks')
    for task in tasks:
        for field in ('title', 'agent', 'task', 'context_paths', 'scope', 'dependencies', 'required_mcps', 'optional_mcps', 'acceptance', 'checks'):
            require(field in task, 'Taskfeld fehlt: ' + field)
        require(re.fullmatch(r'T\d{2,}', task['id']), 'ungültige Task-ID')
        require(agents is None or task['agent'] in agents, 'unbekannter Agent')
        for field in ('context_paths', 'scope', 'dependencies', 'required_mcps', 'optional_mcps'):
            unique(task[field], field)
        require(tools is None or set(task['required_mcps'] + task['optional_mcps']) <= set(tools), 'unbekanntes Tool')
        ac = [a['id'] for a in task['acceptance']]
        unique(ac, 'acceptance')
        require(ac and all(a.get('description') for a in task['acceptance']), 'Kriterien fehlen')
        unique([c['id'] for c in task['checks']], 'checks')
        covered = set()
        for check in task['checks']:
            require(isinstance(check.get('command'), list) and check['command'] and all(isinstance(s, str) for s in check['command']), 'command muss Argumentarray sein')
            require(check.get('cwd') is not None and check.get('pass'), 'Checkbeobachtung/cwd fehlt')
            require(check.get('covers') and set(check['covers']) <= set(ac), 'unbekanntes Checkkriterium')
            covered.update(check['covers'])
        require(covered == set(ac), 'ungedeckte Akzeptanzkriterien')
    graph({t['id']: t['dependencies'] for t in tasks})

def validate_catalog(data):
    require(data.get('catalog_version') == 1, 'Katalogversion')
    require(data.get('max_automatic_review_repair_rounds') == 2, 'Reparaturlimit')
    workflows = data.get('workflows', [])
    unique([w['id'] for w in workflows], 'workflows')
    by_id = {w['id']: w for w in workflows}
    require({'core-plan', 'core-execute', 'core-review', 'core-brainstorm', 'core-milestone', 'core-handoff'} <= set(by_id), 'Etappen/Handoff-Katalog unvollständig')
    edges = set()
    for transition in data.get('transitions', []):
        source, target = transition['from'], transition['to']
        require(source in by_id and (target in by_id or target == 'completed'), 'unbekanntes Routingziel')
        require(target in by_id[source]['successors'], 'Transition fehlt in successors')
        if target in by_id:
            require(source in by_id[target]['predecessors'], 'Transition fehlt in predecessors')
        edges.add((source, target))
    require({('core-plan', 'core-execute'), ('core-execute', 'core-review'), ('core-execute', 'core-milestone'), ('core-milestone', 'core-plan'), ('core-milestone', 'core-handoff')} <= edges, 'bedingte Workflowübergänge fehlen')
    require(by_id['core-review'].get('fresh_context_on_entry') is True and by_id['core-execute'].get('fresh_context_on_entry') is True, 'Fresh-Context-Grenze')
    unique(data.get('known_agent_ids'), 'agents')
    unique(data.get('known_tool_ids'), 'tools')
    # milestone/v1 is a read-only legacy entry: readable, never a new output.
    require('milestone/v1' in by_id['core-milestone'].get('input_schemas', []), 'Legacy milestone/v1 nicht mehr lesbar')
    for workflow in workflows:
        require('milestone/v1' not in workflow.get('output_schemas', []), 'Legacy milestone/v1 als Ausgabe erlaubt: ' + workflow['id'])

def positive_int(value):
    # bool is an int subclass and 1.0 == 1; neither may pose as a version.
    return type(value) is int and value > 0

def validate_name(data):
    goal, milestone, version = data['goal_id'], data['milestone_id'], data['version']
    require(re.fullmatch(r'G\d{2,}', goal) and re.fullmatch(r'M\d{2,}', milestone), 'ID braucht mindestens zwei Stellen')
    require(positive_int(version), 'Definitionsversion ist positive Ganzzahl')
    p, r = data['plan_number'], data['run_number']
    require(re.fullmatch(r'\d{2,}', p) and re.fullmatch(r'\d{2,}', r), 'Plan-/Runnummer braucht mindestens zwei Stellen')
    base = '.agentic-workflow/goals/' + goal
    expected = dict(goal_path=base + '/goal.md', index_path=base + '/index.yaml', definition_path=base + '/milestones/' + milestone + '-v' + str(version) + '.yaml', plan_path='.agentic-workflow/plans/plan-' + goal + '-' + milestone + '-v' + str(version) + '-p' + p + '.md', run_path='.agentic-workflow/runs/run-' + goal + '-' + milestone + '-v' + str(version) + '-p' + p + '-r' + r + '/state.yaml')
    for field, value in expected.items():
        require(data.get(field) == value, 'Namens-/Zuordnungskonflikt: ' + field)
    if 'resume_run_path' in data:
        require(data['resume_run_path'] == expected['run_path'], 'Resume/Reparatur verändert Run-ID')
    occupied = data.get('occupied_paths', [])
    unique(occupied, 'Namenskollision')
    # Goal and index are existing references; definition and plan are new targets.
    for field in ('definition_path', 'plan_path'):
        require(expected[field] not in occupied, 'Namenskollision: belegter neuer Zielpfad ' + field + ': ' + expected[field])

GOAL_RE = r'\.agentic-workflow/goals/(G\d{2,})/goal\.md'
DEF_RE = r'\.agentic-workflow/goals/(G\d{2,})/milestones/(M\d{2,})-v([1-9]\d*)\.yaml'
PLAN_RE = r'\.agentic-workflow/plans/plan-(G\d{2,})-(M\d{2,})-v([1-9]\d*)-p(\d{2,})\.md'
RUN_RE = r'\.agentic-workflow/runs/(run-(G\d{2,})-(M\d{2,})-v([1-9]\d*)-p(\d{2,})-r(\d{2,}))/state\.yaml'
REVALIDATION_RE = r'\.agentic-workflow/runs/run-(G\d{2,})-(M\d{2,})-v([1-9]\d*)-p\d{2,}-r\d{2,}/tasks/T\d{2,}(?:/attempt-\d{2,})?\.yaml'
CONFIRMED = 'user-confirmed'

def parse_path(pattern, path, label):
    match = re.fullmatch(pattern, str(path))
    require(match is not None, label + ': Namensschema verletzt: ' + str(path))
    return match

def plan_key(path):
    match = parse_path(PLAN_RE, path, 'Plan')
    return match[1], match[2], int(match[3]), int(match[4])

def run_key(path):
    match = parse_path(RUN_RE, path, 'Run')
    return match[1], (match[2], match[3], int(match[4]), int(match[5])), int(match[6])

def validate_progression(data):
    """Ordered events: a replacement plan raises p; resume/review/repair keep the exact Run-ID."""
    require(positive_int(data['version']), 'gepinnte Version ist keine positive Ganzzahl: ' + repr(data['version']))
    pinned = (data['goal_id'], data['milestone_id'], data['version'])
    numbers, runs, highest = [], {}, {}
    for event in data['events']:
        action = event['action']
        if action == 'plan':
            key = plan_key(event['plan_path'])
            require(key[:3] == pinned, 'Plan gehört nicht zur gepinnten ID-Version')
            require(not numbers or key[3] > numbers[-1], 'Ersatzplannummer nicht steigend/wiederverwendet')
            numbers.append(key[3])
            continue
        run_id, key, r = run_key(event['run_path'])
        require(key[:3] == pinned, 'Run gehört nicht zur gepinnten ID-Version')
        require(key[3] in numbers, 'Run verweist auf unbekannten Plan')
        if action == 'new':
            require(run_id not in runs and r > highest.get(key[3], 0), 'neuer Run erhöht r nicht/Run-ID wiederverwendet')
            require(key[3] == numbers[-1], 'neuer Run auf abgelöstem Plan')
            runs[run_id], highest[key[3]] = 0, r
        elif action in ('resume', 'review', 'repair'):
            require(event['previous_run_path'] == event['run_path'] and run_id in runs, 'Resume/Reparatur verändert Run-ID')
            require(key[3] == numbers[-1], 'Resume auf abgelöstem Plan')
            if action == 'repair':
                runs[run_id] += 1
                require(runs[run_id] <= 2, 'dritte automatische Reparaturrunde')
        else:
            raise ContractError('unbekannte Runaktion: ' + str(action))

def selected_entries(index):
    selected = {}
    for entry in index['milestones']:
        require(positive_int(entry['version']), 'Indexversion ist keine positive Ganzzahl: ' + repr(entry['version']))
        require(type(entry['selected']) is bool and type(entry['current']) is bool, 'selected/current müssen boolesch sein')
        if entry['selected']:
            require(entry['id'] not in selected, 'mehrere ausgewählte Versionen einer M-ID')
            selected[entry['id']] = entry
        else:
            require(not entry['current'], 'nicht ausgewählte Version ist aktuell')
    return selected

def validate_selection(data):
    """The index alone selects; unreferenced or newer files never do."""
    selected = selected_entries(data['index'])
    files = set(data['files'])
    for entry in data['index']['milestones']:
        require(entry['definition_path'] in files, 'Index referenziert fehlende Definition')
    resolved = {k: v['version'] for k, v in selected.items()}
    require(data['resolved'] == resolved, 'nicht ausgewählte neuere Datei als Auswahl verwendet')

def validate_prompt(data):
    """A start/goal prompt is stale unless it matches the current index selection."""
    selected_entries(data['index'])
    current = [e for e in data['index']['milestones'] if e['current']]
    require(len(current) == 1, 'keine freigegebene aktuelle Etappe')
    entry, prompt = current[0], data['prompt']
    require(entry.get('current_approval') == CONFIRMED, 'keine freigegebene aktuelle Etappe')
    goal = parse_path(GOAL_RE, prompt['goal_path'], 'Prompt-Ziel')[1]
    definition = parse_path(DEF_RE, prompt['definition_path'], 'Prompt-Definition')
    require(positive_int(prompt['version']), 'Promptversion ist keine positive Ganzzahl: ' + repr(prompt['version']))
    require((definition[1], definition[2], int(definition[3])) == (goal, prompt['milestone_id'], prompt['version']), 'Prompt Name/ID/Version widerspricht Inhalt')
    require(prompt['index_path'] == prompt['goal_path'].removesuffix('goal.md') + 'index.yaml', 'Prompt-Index gehört zu anderem Ziel')
    require((prompt['milestone_id'], prompt['version'], prompt['definition_path']) == (entry['id'], entry['version'], entry['definition_path']), 'veralteter Start-/Goal-Prompt')
    require(entry['plan_paths'] and prompt['plan_path'] == entry['plan_paths'][-1], 'veralteter Start-/Goal-Prompt: Plan abgelöst')
    if prompt.get('run_path'):
        require(prompt['run_path'] in entry['run_paths'] and run_key(prompt['run_path'])[1] == plan_key(prompt['plan_path']), 'veralteter Start-/Goal-Prompt: Run nicht an Plan gebunden')

def validate_write_sequence(data):
    """New files at free paths, index last, conditional on revision and content."""
    occupied, verified, failed = set(data['existing_paths']), set(data.get('verified_existing', [])), False
    operations = data['operations']
    for position, op in enumerate(operations):
        kind = op['op']
        if kind in ('write_goal', 'write_definition'):
            require(op['path'] not in occupied, 'Nicht-Überschreiben-Guard verletzt')
            occupied.add(op['path'])
            if op['result'] == 'ok' and op['verified']:
                verified.add(op['path'])
            else:
                failed = True
        elif kind == 'write_index':
            require(position == len(operations) - 1, 'Index nicht zuletzt geschrieben')
            require(not failed, 'teilweise Struktur freigegeben')
            require(set(op['selects']) <= verified, 'Index wählt ungeprüfte/teilweise Datei')
            base = data['base_index']
            require((op['observed_revision'], op['observed_sha256']) == (base['revision'], base['sha256']), 'konkurrierende Änderung überschrieben')
            require(op['new_revision'] == base['revision'] + 1, 'revision nicht um eins erhöht')
        elif kind in ('delete', 'rename', 'auto_select', 'blind_retry'):
            raise ContractError('automatische Bereinigung/Wiederholung nach Teilfehler')
        else:
            raise ContractError('unbekannte Schreiboperation: ' + str(kind))

def validate_goal_change(data):
    before, after = data['before'], data['after']
    if before['content'] != after['content']:
        require(after['id'] != before['id'], 'bestätigtes Ziel überschrieben')
        require(after['id'] not in data['existing_goal_ids'], 'Ziel-ID wiederverwendet')
        require(data['successor_confirmed'], 'Nachfolgeziel nicht bestätigt')
        require(before['id'] in data['retained_goal_ids'], 'referenziertes historisches Ziel entfernt')

def validate_artifacts(documents):
    for document in documents:
        check_format(document['schema'], document)
    check_example_relations(documents)

def validate_scenario(data):
    """Explicit inputs and observed relationships; unknown kinds fail closed."""
    kind = data.get('kind')
    if kind == 'name':
        validate_name(data)
    elif kind == 'graph':
        graph(data['nodes'])
    elif kind == 'marker':
        require((data['starts'], data['ends']) in ((0, 0), (1, 1)), 'beschädigte/einzelne/doppelte Marker')
        require(not data['damaged'], 'beschädigte Marker')
        require(data['starts'] == 1 or data['confirmed_creation'], 'Neuanlage nicht bestätigt')
        require(data['outside_before'] == data['outside_after'], 'Außenbereich verändert')
        require(data['first_output'] == data['second_output'], 'nicht idempotent')
    elif kind == 'handoff':
        require(data['actor'] == 'core-execute', 'Fachagent dispatcht')
        require(data['confirmed_task'] and not data['material_change'], 'Rückgabe an Plan erforderlich')
        require(data['required_dependency'] in data['dependencies'], 'Übergabe: Abhängigkeit fehlt')
        require(set(data['required_sources']) <= set(data['context_paths']), 'Vertragsquelle fehlt')
        require(set(data['changed_paths']) <= set(data['scope']), 'Scope erweitert')
        require(not data['changes_goal_selection'], 'Fachagent verändert Zielauswahl')
    elif kind == 'result_owner':
        require(data['writer'] == ('core-execute' if not data['scope'] else data['agent']), 'falscher Ergebnisbesitz')
        require(not data['scope'] or data['explicit_result_exception'], 'Ergebnisdateiausnahme fehlt')
        unique(data['attempt_paths'], 'überschriebener Taskversuch')
    elif kind == 'provider':
        require(data['mode'] == 'read-only', 'MCP-Prüfung mutiert')
        require(not any(data[k] for k in ('install', 'config_write', 'secret_search', 'requires_lockfile', 'requires_declaration')), 'unerlaubte Setupwirkung/Voraussetzung')
        require(data['available'] or data['reported_missing'], 'fehlender Provider verschwiegen')
    elif kind == 'version':
        require(data['confirmed'] and data['definition_exists'], 'unbestätigte/fehlende Definition')
        require(data['selected'] == data['plan_binding'] == data['prompt_binding'], 'veraltete Versionsbindung')
        require(data['before_definition'] == data['after_definition'], 'historische Definition überschrieben')
        require(not data['inherited_completion'], 'Abschluss automatisch übertragen')
        require(not data['running_switched'], 'laufender Run still umgebunden')
        require(data['dependencies_exact'] and data['sources_exist'] and not data['concurrent_change'], 'Abhängigkeit/Quelle/konkurrierende Änderung')
        require(data['index_updated_last'], 'teilweise Struktur freigegeben')
    elif kind == 'planning':
        require(not data['dispatch'] and not data['product_write'], 'Planungsmethode startet Agent/Implementierung')
        require(set(data['methods']) <= set(data['signals']), 'Fachmethode ohne konkretes Signal')
        require(data['decision_owner'] == 'core-milestone' and data['decision_confirmed'], 'bestätigte Entscheidung an falschen Eigentümer')
        require(not data['refactor'] or data['characterization_task'] in data['refactor_dependencies'], 'Refactoring ohne getrenntes Safety Net')
    elif kind == 'audit':
        require(data['requested_remediation'], 'Audit erfindet Behebungsauftrag')
        require(data['next_owner'] == ('core-brainstorm' if data['material_uncertainty'] else 'core-plan'), 'Auditroute widerspricht Entscheidungsbedarf')
        require(not data['product_write'], 'Audit implementiert')
    elif kind == 'docs':
        require(data['proven_drift'] and data['sources_exist'], 'Docs ohne belegte Drift/Quelle')
        require(not data['changes_goal_decisions'], 'Docs überschreibt bestätigte Zielentscheidung')
        require(set(data['changed_paths']) <= set(data['scope']), 'Docs erweitert Scope')
    elif kind == 'legacy':
        require(data['schema'] == 'milestone/v1' and not data['mixed_formats'], 'Legacyformat vermischt')
        require(not data['automatic_migration'] and not data['automatic_rename'], 'automatische Legacy-Migration/Umbenennung')
        require(data['explicit_entry'], 'vermeintlich neueste Datei statt exaktem Einstieg')
    elif kind == 'progression':
        validate_progression(data)
    elif kind == 'selection':
        validate_selection(data)
    elif kind == 'prompt':
        validate_prompt(data)
    elif kind == 'write_sequence':
        validate_write_sequence(data)
    elif kind == 'goal_change':
        validate_goal_change(data)
    elif kind == 'artifacts':
        validate_artifacts(data['documents'])
    elif kind == 'completion':
        require(data['review_pass'] and data['evidence_valid'], 'Run-pass ohne gültige Evidenz')
        require(not data['milestone_mode'] or data['milestone_checked'], 'Run-pass ist kein Etappenabschluss')
        require(not data['next_started'] or data['next_authorized'], 'automatische Folgefreigabe')
        require(not data['goal_completed'] or data['goal_evidence'], 'Gesamterfolg unbelegt')
    else:
        raise ContractError('unbekannter Szenariotyp: ' + str(kind))

def snapshot(paths):
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None for p in paths}

def guarded_run(paths, action):
    before = snapshot(paths)
    try:
        return action()
    finally:
        require(snapshot(paths) == before, 'Read-only-Guard: geprüfte Quellen verändert')

def local_path(root, relative):
    path = (root / relative).resolve()
    require(path.is_relative_to(root.resolve()), 'Referenz verlässt Workspace: ' + relative)
    return path

def check_links(root, path, text):
    for reference in re.findall(r'(?<!!)\[[^\]]*\]\(([^)]+)\)', text):
        if re.match(r'^[a-z]+://', reference) or reference.startswith('#'):
            continue
        relative = reference.split('#')[0]
        require('<' not in relative and '*' not in relative, 'nicht konkreter Markdownlink: ' + reference)
        target = (path.parent / relative).resolve()
        require(target.is_relative_to(root.resolve()) and target.exists(), 'fehlende/lokalfremde Referenz: ' + reference)

def check_format(schema, data):
    require(isinstance(data, dict), 'Schema-Beispiel ist kein Mapping')
    fields = {
        'goal/v1': ('id', 'approval', 'goal', 'non_goals', 'constraints', 'decisions', 'goal_acceptance'),
        'milestone-definition/v1': ('id', 'version', 'approval', 'goal_path', 'title', 'outcome', 'scope', 'dependencies', 'acceptance'),
        'milestone-index/v1': ('goal_path', 'revision', 'milestones', 'goal_completion_refs'),
        'milestone/v1': ('id', 'goal', 'milestones', 'goal_acceptance'),
        'task-result/v1': ('task_id', 'attempt', 'status', 'changed_paths', 'acceptance', 'checks', 'limitations'),
        'review/v1': ('run_id', 'verdict', 'findings'),
    }
    require(schema in fields, 'unbekanntes Schema: ' + schema)
    for field in fields[schema]:
        require(field in data, schema + ': Pflichtfeld fehlt: ' + field)
    progress = {'status', 'run_status', 'task_status', 'findings', 'plan_paths', 'run_paths', 'completion_refs', 'current_milestone'}
    if schema in ('goal/v1', 'milestone-definition/v1'):
        require(data['approval'] == CONFIRMED, 'unbestätigte Ziel-/Definitionsfassung')
        require(not progress & data.keys(), 'Ziel/Definition enthält Laufzustand')
        for ref in data.get('decision_refs', []):
            require(safe_relative(ref), 'Designquelle nicht exakt projektrelativ')
    if schema == 'milestone-definition/v1':
        require(re.fullmatch(r'M\d{2,}', str(data['id'])), 'Milestone-ID')
        require(positive_int(data['version']), 'Version')
        parse_path(GOAL_RE, data['goal_path'], 'Definitions-Zielpfad')
        require(data['title'] and data['outcome'] and data['acceptance'], 'Outcome/Kriterien fehlen')
        unique([a['id'] for a in data['acceptance']], 'Definitionskriterien')
        require(isinstance(data['scope'], list), 'Scope ist keine Liste')
    if schema in ('goal/v1', 'milestone/v1'):
        require(re.fullmatch(r'G\d{2,}', str(data['id'])), 'Ziel-ID')
        require(data['goal'] and data['goal_acceptance'], 'Gesamtzielkriterien fehlen')
        unique([a['id'] for a in data['goal_acceptance']], 'Gesamtzielkriterien')
    if schema == 'milestone/v1':
        entries = data['milestones']
        unique([m['id'] for m in entries], 'milestones')
        graph({m['id']: m['dependencies'] for m in entries})
        require(data.get('current_milestone') is None or data['current_milestone'] in [m['id'] for m in entries], 'unbekannte aktuelle Etappe')
    if schema == 'milestone-index/v1':
        check_index(data)

def check_index(data):
    goal = parse_path(GOAL_RE, data['goal_path'], 'Index-Zielpfad')[1]
    require(not {'findings', 'task_status', 'status', 'run_status', 'events'} & data.keys(), 'Index dupliziert Runstatus/Findings')
    require(type(data['revision']) is int and data['revision'] > 0, 'Indexrevision')
    entries = data['milestones']
    require(isinstance(entries, list) and entries, 'Index milestones ist keine nicht leere Liste')
    require(isinstance(data['goal_completion_refs'], list), 'goal_completion_refs ist keine Liste')
    entry_fields = {'id', 'version', 'definition_path', 'selected', 'current', 'selection_approval', 'plan_paths', 'run_paths', 'completion_refs'}
    for entry in entries:
        require(entry_fields <= entry.keys(), 'Indexeintrag unvollständig')
        require(not entry.keys() - entry_fields - {'current_approval', 'goal_path'}, 'Index dupliziert Runstatus/Findings')
        require(positive_int(entry['version']), 'Indexversion ist keine positive Ganzzahl: ' + repr(entry['version']))
        match = parse_path(DEF_RE, entry['definition_path'], 'Indexdefinition')
        require((match[1], match[2], int(match[3])) == (goal, entry['id'], entry['version']), 'Index Definition Name/ID/Version widerspricht Inhalt')
        require(entry.get('goal_path', data['goal_path']) == data['goal_path'], 'Indexeintrag widerspricht Zielbezug')
        require(entry['selection_approval'] == CONFIRMED, 'Auswahl ohne bestätigte Freigabe')
    unique([(m['id'], m['version']) for m in entries], 'Index ID-Version')
    selected = selected_entries(data)
    current = [m for m in entries if m['current']]
    require(len(current) <= 1, 'mehrere aktuelle Etappen')
    require(all(m.get('current_approval') == CONFIRMED for m in current), 'aktuelle Etappe ohne Freigabe')
    require(set(selected) == {m['id'] for m in entries}, 'M-ID ohne ausgewählte Version')
    for entry in entries:
        pinned = (goal, entry['id'], entry['version'])
        plans = [plan_key(path) for path in entry['plan_paths']]
        require(all(k[:3] == pinned for k in plans), 'Plan gehört nicht zur gepinnten ID-Version')
        require([k[3] for k in plans] == sorted({k[3] for k in plans}), 'Ersatzplannummer nicht steigend/wiederverwendet')
        for path in entry['run_paths']:
            require(run_key(path)[1] in plans, 'Run verweist auf unbekannten Plan')
        for ref in entry['completion_refs']:
            check_completion_ref(entry, pinned, ref)

def safe_relative(path):
    # Concrete project-relative form: no absolute, drive, backslash, empty, '.' or '..' segment.
    return isinstance(path, str) and bool(path) and '\\' not in path and ':' not in path and not path.startswith('/') and all(part not in ('', '.', '..') for part in path.split('/'))

def check_completion_ref(entry, pinned, ref):
    for field in ('version', 'definition_path', 'acceptance_ids', 'plan_path', 'run_path', 'review_path', 'evidence_paths'):
        require(ref.get(field), 'Abschluss ohne Originalnachweise/Kriterien: ' + field)
    require(positive_int(ref['version']), 'Abschlussversion ist keine positive Ganzzahl: ' + repr(ref['version']))
    require((ref['version'], ref['definition_path']) == (entry['version'], entry['definition_path']), 'historischer Abschluss falsch zugeordnet')
    plan = plan_key(ref['plan_path'])
    run_id, run_plan, _ = run_key(ref['run_path'])
    require(run_plan == plan, 'Abschlussrun gehört nicht zum Abschlussplan')
    base = '.agentic-workflow/runs/' + run_id + '/'
    require(ref['review_path'] == base + 'review.yaml', 'Review gehört nicht zum Abschlussrun')
    require(isinstance(ref['evidence_paths'], list) and ref['evidence_paths'] and all(safe_relative(p) and p.startswith(base) for p in ref['evidence_paths']), 'Evidenz gehört nicht zum Abschlussrun oder ist kein sicherer projektrelativer Pfad: ' + str(ref['evidence_paths']))
    if plan[:3] == pinned:
        require(ref['plan_path'] in entry['plan_paths'] and ref['run_path'] in entry['run_paths'], 'Abschlussnachweis nicht im Eintrag verknüpft')
        require('revalidation_path' not in ref, 'Revalidierung ohne Versionswechsel')
    else:
        require(plan[:2] == pinned[:2] and plan[2] != pinned[2], 'Abschluss fremder Etappe zugeordnet')
        path = ref.get('revalidation_path')
        require(path, 'Abschluss automatisch übertragen: revalidation_path fehlt')
        # Exact written task evidence of a Run for the new pinned version.
        require(path not in ref['evidence_paths'], 'Abschluss automatisch übertragen: revalidation_path ist Originalevidenz')
        match = re.fullmatch(REVALIDATION_RE, path) if isinstance(path, str) else None
        require(match is not None and (match[1], match[2], int(match[3])) == pinned, 'revalidation_path ist kein exakter projektrelativer Prüfpfad der neuen Fassung: ' + str(path))

# Relational evidence clauses, not a claim of natural-language equivalence.
POLICIES = {
    'milestones': [(r'bestätigt\w* Definition\w*[^.!\n]*(?:unveränder|nicht.*(?:überschreib|veränder))', 'unveränderliche Definition'), (r'(?:Versionsauswahl|Ersatzdefinition|Versionswechsel)[^.!\n]*Bestätigung', 'bestätigter Versionswechsel'), (r'(?:Abschluss|Nachweis)[^.!\n]*(?:nicht automatisch|keine automatische)', 'keine Erfolgsübertragung')],
    'shared': [(r'(?:Execute|core-execute)[^.!\n]*(?:persistiert|schreibt)[^.!\n]*read-only', 'Execute persistiert read-only Ergebnisse'), (r'(?:Versuch|attempt)[^.!\n]*unveränder|unveränder[^.!\n]*(?:Versuch|attempt)', 'unveränderliche Versuche'), (r'(?:referenz|angewiesen)[^.!\n]*(?:erhalten|aufbewahr)', 'referenzabhängige Aufbewahrung')],
    'workflows': [(r'(?:Start|Resume)[^.!\n]*(?:Version|Auswahl|Definition)', 'Start/Resume Versionsprüfung'), (r'(?:Folgeetappe|nächste Etappe)[^.!\n]*(?:Freigabe|Bestätigung)', 'Folgefreigabe'), (r'(?:Review|core-review)[^.!\n]*(?:gepinnt|festgelegt|Definitionsversion)', 'Review gegen gepinnte Fassung')],
    'domains': [(r'(?:Bedarf|Übergabe)[^.!\n]*(?:Execute|core-execute)', 'vermittelter Domainbedarf'), (r'(?:fehlend\w* Task|fehlt[^.!\n]*Task|materiell\w* Vertragsänderung)[^.!\n]*(?:Plan|core-plan)', 'fehlender Task zurück an Plan'), (r'(?:Fachagent|Fachskill)[^.!\n]*(?:nicht|keine|weder)[^.!\n]*(?:Version|Ziel|Index)', 'Zielschutz')],
    'setup': [(r'(?:MCP|Provider)[^.!\n]*read-only|read-only[^.!\n]*(?:MCP|Provider)', 'read-only Providerprüfung'), (r'(?:keine|kein|nicht)[^.!\n]*(?:Installation|Installer|installiert)', 'kein Installer'), (r'(?:einzeln|beschädigt|doppelt)[^.!\n]*(?:block|stopp)', 'beschädigte Marker blockieren')],
    'docs': [(r'(?:einfache Vorhaben|ohne Milestones)[^.!\n]*(?:keine|nur|ohne)[^.!\n]*(?:Zielstruktur|Plan|Ziel)', 'einfacher Einstieg'), (r'Resume[^.!\n]*(?:dieselbe|gleichen|unverändert)[^.!\n]*Run', 'Resume behält Run'), (r'(?:Definition|Version)[^.!\n]*unveränder', 'unveränderliche Definition')],
}

# Plan 003 K1-K6, its synergies and every T08 case named by plan 004.
REQUIRED_COVERAGE = (
    'K1-read-only-ergebnisbesitz', 'K2-run-pass-kein-etappenabschluss', 'K3-katalog-etappenzyklus', 'K4-eigentum-aufbewahrung', 'K5-marker-neuanlage', 'K6-mcp-pruefung-statt-installer',
    'S-brainstorm-plan-milestone', 'S-plan-fachmethoden', 'S-refactor-safety-net', 'S-execute-review-debug', 'S-audit-plan-brainstorm', 'S-milestone-handoff-wiedereinstieg', 'S-domain-uebergaben', 'S-fachskill-docs',
    'gueltige-neuanlage', 'legacy-einstieg', 'bestaetigter-ersatz', 'nicht-ausgewaehlte-neuere-datei', 'veralteter-plan-goal-prompt', 'laufender-run-versionswechsel', 'geaenderte-abhaengigkeit', 'fehlende-definition-designquelle', 'id-versionskonflikt', 'zyklischer-graph', 'teilweise-geschriebene-struktur', 'konkurrierende-aenderung', 'historische-abschlusszuordnung',
    'namenskollision', 'widerspruechliche-ids', 'falsche-versionszuordnung', 'ersatzplannummer', 'run-id-resume-review-reparatur', 'keine-automatische-umbenennung', 'kein-geerbter-abschluss', 'resume', 'review-ready', 'folgefreigabe', 'gesamtabschluss', 'unveraenderliches-ziel', 'hoechstens-eine-aktuelle-etappe',
)

def check_coverage(fixture):
    by_id = {c['id']: c for c in fixture['cases']}
    coverage = fixture.get('coverage', {})
    require(set(REQUIRED_COVERAGE) <= coverage.keys(), 'Regressionsabdeckung fehlt: ' + ', '.join(sorted(set(REQUIRED_COVERAGE) - coverage.keys())))
    for key, entry in coverage.items():
        cases = entry.get('cases', [])
        require(set(cases) <= by_id.keys(), key + ': unbekannte Szenario-ID')
        # A named independent review scenario is explicit, never a silent gap.
        require(any(by_id[c]['expected'] == 'fail' for c in cases) or entry.get('review_scenario'), key + ': keine Negativregression/kein benanntes Reviewszenario')

def check_scenarios(root, group=None):
    fixture = json.loads((root / 'tests/core_scenario_cases.json').read_text())
    require(fixture.get('schema') == 'core-scenarios/v1', 'Szenarioschema fehlt')
    check_coverage(fixture)
    cases = [c for c in fixture['cases'] if group is None or c['group'] == group]
    require(cases and {'pass', 'fail'} <= {c['expected'] for c in cases}, 'positive/negative Kontrollfixtures fehlen')
    unique([c['id'] for c in cases], 'Szenario-IDs')
    for case in cases:
        require(case.get('source') and local_path(root, case['source']).is_file(), 'Szenarioquellbezug fehlt')
        try:
            validate_scenario(case['input'])
        except ContractError as exc:
            require(case['expected'] == 'fail' and case['observation'] in str(exc), case['id'] + ': unerwartete Verletzung: ' + str(exc))
        else:
            require(case['expected'] == 'pass', case['id'] + ': Verletzung nicht erkannt')
    print('SCENARIOS', group or 'all', len(cases), 'erwartete Beobachtungen')


def check_owners(text):
    rows = [line for line in text.splitlines() if line.startswith('|') and '|' in line[1:]]
    relations = [('goal/v1', 'core-milestone'), ('milestone-definition/v1', 'core-milestone'), ('milestone-index/v1', 'core-milestone'), ('plan/v1', 'core-plan'), ('review/v1', 'core-review')]
    for schema, owner in relations:
        require(any(schema in row and owner in row.split('|')[-2] for row in rows), 'Eigentümertabelle: ' + schema + ' gehört nicht nachweisbar ' + owner)


def check_example_relations(examples):
    # Exact name/content consistency without inventing real goal artifacts.
    goals, definitions = {}, {}
    # Collect goals first; source order must not decide whether a goal is missing.
    for data in examples:
        if data.get('schema') == 'goal/v1':
            require(data['id'] not in goals, 'doppeltes Zieleintrag-Beispiel')
            goals[data['id']] = data
    for data in examples:
        if data.get('schema') == 'milestone-definition/v1':
            require(positive_int(data['version']), 'Definitionsversion ist keine positive Ganzzahl: ' + repr(data['version']))
            key = (data['goal_path'], data['id'], data['version'])
            require(key not in definitions, 'doppelte Definitionsversion')
            definitions[key] = data
            match = re.fullmatch(r'\.agentic-workflow/goals/(G\d{2,})/goal\.md', data['goal_path'])
            require(match is not None, 'Definitions-Zielpfad verletzt Namensschema')
            # A complete artifact set fails closed on missing referenced goals.
            require(match[1] in goals, 'Definition verweist auf fehlendes/falsches Ziel')
            if 'definition_path' in data:
                expected = '.agentic-workflow/goals/' + match[1] + '/milestones/' + data['id'] + '-v' + str(data['version']) + '.yaml'
                require(data['definition_path'] == expected, 'Definition Name/ID/Version widerspricht Inhalt')
    nodes = {}
    for key, data in definitions.items():
        dependencies = []
        for dep in data['dependencies']:
            require(isinstance(dep, dict) and {'id', 'version', 'definition_path'} <= dep.keys(), 'Abhängigkeit muss ID/Version/exakten Definitionspfad pinnen')
            require(positive_int(dep['version']), 'Abhängigkeitsversion ist keine positive Ganzzahl: ' + repr(dep['version']))
            match = re.fullmatch(r'(\.agentic-workflow/goals/G\d{2,})/milestones/(M\d{2,})-v([1-9]\d*)\.yaml', dep['definition_path'])
            require(match is not None and (match[2], int(match[3])) == (dep['id'], dep['version']), 'Abhängigkeit Name/ID/Version widerspricht Inhalt')
            require(match[1] + '/goal.md' == data['goal_path'], 'Abhängigkeit verlässt das Gesamtziel')
            dependencies.append((match[1] + '/goal.md', dep['id'], dep['version']))
        nodes[key] = dependencies
    if nodes:
        graph(nodes)
    for data in examples:
        if data.get('schema') == 'milestone-index/v1':
            check_index(data)
            check_index_relations(data, goals, definitions)


def check_index_relations(data, goals, definitions):
    goal = parse_path(GOAL_RE, data['goal_path'], 'Index-Zielpfad')[1]
    require(goal in goals, 'Index verweist auf fehlendes/falsches Ziel')
    selected = selected_entries(data)
    complete = {}
    for entry in data['milestones']:
        key = (data['goal_path'], entry['id'], entry['version'])
        ids = {i for ref in entry['completion_refs'] for i in ref['acceptance_ids']}
        # An empty definitions mapping is a missing definition, not a skipped check.
        require(key in definitions, 'Index referenziert fehlende/falsche Definitionsversion')
        required = {a['id'] for a in definitions[key]['acceptance']}
        require(ids <= required, 'unbekannte Abschlusskriterien')
        require(not ids or ids == required, 'Abschluss deckt nicht alle Etappenkriterien')
        complete[(entry['id'], entry['version'])] = bool(ids)
    for entry in data['milestones']:
        if not entry['current']:
            continue
        for dep in definitions[(data['goal_path'], entry['id'], entry['version'])]['dependencies']:
            chosen = selected.get(dep['id'])
            require(chosen is not None and chosen['version'] == dep['version'], 'Abhängigkeit passt nicht zur Indexauswahl')
            require(complete.get((dep['id'], dep['version'])), 'aktuelle Etappe vor belegtem Abhängigkeitsabschluss')
    if data['goal_completion_refs']:
        ids = set()
        for ref in data['goal_completion_refs']:
            require(ref.get('goal_path') == data['goal_path'] and ref.get('acceptance_ids') and ref.get('evidence_paths'), 'Gesamterfolg ohne Originalnachweise')
            require(isinstance(ref['evidence_paths'], list) and all(safe_relative(p) for p in ref['evidence_paths']), 'Gesamterfolg-Evidenz ist kein sicherer projektrelativer Pfad')
            ids.update(ref['acceptance_ids'])
        require(ids == {a['id'] for a in goals[goal]['goal_acceptance']}, 'Gesamterfolg deckt nicht alle goal_acceptance-Kriterien')
        require(all(complete.get((e['id'], e['version'])) for e in selected.values()), 'Gesamterfolg ohne alle ausgewählten Etappenabschlüsse')


def targets(root, group):
    plan_blocks = [b for b in blocks((root / PLAN).read_text()) if isinstance(b, dict) and b.get('schema') == 'plan/v1']
    require(len(plan_blocks) == 1, 'exakter Implementierungsplan benötigt einen Taskgraphen')
    plan = plan_blocks[0]
    catalog = load_yaml((root / '.apm/skills/core-shared/assets/workflow-catalog.yaml').read_text())
    validate_plan(plan, catalog['known_agent_ids'], catalog['known_tool_ids'])
    task = next(t for t in plan['tasks'] if t['id'] == GROUP_TASK[group])
    paths = [local_path(root, p) for p in task['scope']]
    if group == 'shared':
        paths.append(local_path(root, '.apm/skills/core-shared/assets/review-finding.yaml'))
    return paths

def authoring(root, paths, tool_root=None):
    home = Path(tool_root) if tool_root else Path.home() / '.agents/skills'
    validator = home / 'skill-creator/scripts/quick_validate.py'
    analyzer = home / 'context-debloater/scripts/analyze_markdown.py'
    consolidator = home / 'context-debloater/scripts/consolidate_duplicates.py'
    for tool in (validator, analyzer, consolidator):
        require(tool.is_file(), 'Authoringtool fehlt: ' + str(tool))
    markdown = [p for p in paths if p.suffix == '.md']
    require(markdown, 'kein explizites Markdown-Targetset')
    # Creator validates the owning skill even when this phase edits only references.
    owners = set()
    for path in markdown:
        for parent in (path.parent, *path.parents):
            if parent == root:
                break
            if (parent / 'SKILL.md').is_file():
                owners.add(parent / 'SKILL.md')
                break
    protected = list(dict.fromkeys([*paths, *owners]))
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    def run(command, payload=None):
        result = subprocess.run(command, input=payload, text=True, capture_output=True, cwd=root, env=environment, timeout=90)
        require(result.returncode == 0, 'Authoringtool meldet Fehler: ' + result.stderr[:1000] + result.stdout[:1000])
        if payload is not None:
            report = json.loads(result.stdout)
            require(report.get('status') == 'ok', 'Authoringreport nicht ok')
            print('AUTHORING', Path(command[2]).name, 'status=ok; Hinweise sind Reviewevidenz, keine automatischen Fixes')
        else:
            require('valid' in result.stdout.lower(), 'Creator ohne Validierungsbeobachtung')
            print('AUTHORING', Path(command[2]).name, result.stdout.strip())
    def action():
        for path in sorted(owners):
            run([sys.executable, '-B', str(validator), str(path.parent)])
        for path in markdown:
            # Bound Debloater's reference inventory to this target's folder.
            payload = json.dumps({'workspace': str(path.parent), 'targets': [str(path)]})
            for tool in (analyzer, consolidator):
                run([sys.executable, '-B', str(tool)], payload)
    guarded_run(protected, action)

def check_decision_refs(root, data):
    # Explicit design sources in real format sources must exist; illustrative
    # plan/run paths of index examples are not file obligations.
    refs = data.get('decision_refs', [])
    require(isinstance(refs, list), 'decision_refs ist keine Liste')
    for ref in refs:
        require(isinstance(ref, str) and local_path(root, ref).is_file(), 'Designquelle fehlt/nicht projektrelativ: ' + str(ref))


LEGACY_ATTEMPT = '.agentic-workflow/runs/<run-id>/tasks/<task-id>.yaml'
NEW_ATTEMPT = '.agentic-workflow/runs/<run-id>/tasks/<task-id>/attempt-<nn>.yaml'

def check_execute_attempts(text):
    sentences = re.split(r'(?<=[.!?])\s+', text)
    writes = [s for s in sentences if NEW_ATTEMPT in s and re.search(r'\b(?:Verlange|schreib|persistier)', s, re.I)]
    require(writes, 'Execute verlangt keinen neuen unveränderlichen attempt-Pfad')
    require(any(re.search(r'fortlaufend', s) for s in writes) and re.search(r'Retry[^.!\n]*nächste[^.!\n]*(?:überschreibt|überschreiben)[^.!\n]*kein', text), 'Execute sichert fortlaufende, nicht überschreibende Versuche nicht')
    for sentence in sentences:
        if LEGACY_ATTEMPT in sentence:
            # The legacy path may appear only as a read-only legacy result.
            require('Legacy' in sentence and re.search(r'gelesen|lesen', sentence) and re.search(r'weder neu beschrieben|nicht neu beschrieben', sentence) and not re.search(r'\bVerlange\b', sentence), 'Execute schreibt Legacy-Taskpfad statt attempt-Pfad')


def check_setup_source(front, text):
    description = front['description']
    require(re.search(r'(?:prüft|Prüfung|Prüfskill)[^.!]*read-only|read-only[^.!]*(?:prüft|Prüfung|Prüfskill)', description, re.I), 'core-init-mcps beschreibt Einrichtung statt read-only Prüfung')
    require(not re.search(r'(?mi)^\s*(?:\d+[.)]\s*)?(?:Materialisiere|Installiere|Provisioniere|Aktiviere)\s+(?!nicht\b|keine\b|keinen\b|kein\b)', text), 'core-init-mcps fordert eigene Installation/Materialisierung')
    require(not re.search(r'(?mi)^\s*(?:\d+[.)]\s*)?Lies[^\n]*apm\.lock', text), 'MCP-Prüfung fordert Lockfile')
    require(re.search(r'(?:keine|kein|nicht|ohne)[^.!\n]*(?:Secretzugriff|Secret.*such|Secrets.*such|Schlüsselbund)', text, re.I), 'MCP-Prüfung ohne belegte Secretzugriffsgrenze')


def check_group(root, group, with_authoring=False, tool_root=None):
    paths = targets(root, group)
    def action():
        texts, examples = [], []
        for path in paths:
            require(path.is_file(), 'Phasenvoraussetzung fehlt: ' + str(path.relative_to(root)))
            text = path.read_text(encoding='utf-8')
            texts.append(text)
            if path.suffix == '.md':
                check_links(root, path, text)
                examples.extend(b for b in blocks(text) if isinstance(b, dict) and 'schema' in b)
                if path.name == 'SKILL.md':
                    match = re.match(r'---\n(.*?)\n---', text, re.S)
                    require(match is not None, 'Skillfrontmatter fehlt')
                    front = load_yaml(match[1])
                    require(front.get('name') == path.parent.name and isinstance(front.get('description'), str), 'Skillname/Ordner inkonsistent')
                    if group == 'setup' and path.parent.name == 'core-init-mcps':
                        check_setup_source(front, text)
                if path.parent.name == 'core-execute' and path.name == 'SKILL.md':
                    check_execute_attempts(text)
            elif path.suffix == '.yaml':
                value = load_yaml(text)
                if path.name == 'workflow-catalog.yaml':
                    validate_catalog(value)
                elif isinstance(value, dict) and 'schema' in value:
                    examples.append(value)
        joined = '\n'.join(texts)
        for pattern, label in POLICIES[group]:
            require(re.search(pattern, joined, re.I), 'semantische Klausel nicht belegt: ' + label)
        schemas = set()
        for example in examples:
            schema = example['schema']
            schemas.add(schema)
            if schema == 'plan/v1':
                validate_plan(example)
            else:
                check_format(schema, example)
            if schema in ('goal/v1', 'milestone-definition/v1', 'milestone/v1'):
                check_decision_refs(root, example)
        if group == 'milestones':
            require({'goal/v1', 'milestone-definition/v1', 'milestone-index/v1', 'milestone/v1'} <= schemas, 'neue/Legacy-Formatbeispiele fehlen')
            check_example_relations(examples)
        if group == 'shared':
            require({'plan/v1', 'task-result/v1', 'review/v1'} <= schemas, 'Kernschemabeispiele fehlen')
            check_owners(joined)
        check_scenarios(root, group)
        if group == 'docs':
            skills = list((root / '.apm/skills').glob('core-*/SKILL.md'))
            counts = [int(n) for n in re.findall(r'(\d+)\s+(?:Core-)?(?:Skill-)?Bundles?', joined, re.I)]
            require(counts and all(n == len(skills) for n in counts), 'Bundleanzahl fehlt/inkonsistent')
        if with_authoring:
            authoring(root, paths, tool_root)
        print('PASS', group, len(paths), 'explizite Quellen; Schemata:', ', '.join(sorted(schemas)))
    return guarded_run(paths, action)

def selftest(root):
    test_path, fixture_path = root / 'tests/test_core_contracts.py', root / 'tests/core_scenario_cases.json'
    require(test_path.is_file() and fixture_path.is_file(), 'Selbsttestvoraussetzung fehlt')
    def action():
        suite = unittest.defaultTestLoader.discover(str(test_path.parent), pattern=test_path.name)
        require(suite.countTestCases() > 0, 'keine Selbsttests gefunden')
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        require(result.wasSuccessful(), 'Selbsttests fehlgeschlagen')
        print('PASS selftest: positive/negative Beziehungen und Read-only-Guards geprüft')
    return guarded_run([root / 'scripts/check_core_contracts.py', test_path, fixture_path], action)

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--group', choices=GROUPS, required=True)
    parser.add_argument('--authoring', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.group == 'selftest':
            selftest(ROOT)
            if args.authoring:
                raise ContractError('selftest besitzt keine Markdown-Authoringziele; konkrete Fachgruppe wählen')
        else:
            failures = []
            for group in GROUP_TASK if args.group == 'all' else [args.group]:
                try:
                    check_group(ROOT, group, args.authoring)
                except (ContractError, OSError, KeyError, TypeError, StopIteration, subprocess.SubprocessError) as exc:
                    failures.append(group + ': ' + str(exc))
            require(not failures, '\n'.join(failures))
        return 0
    except (ContractError, OSError, KeyError, TypeError, StopIteration, subprocess.SubprocessError) as exc:
        print('FAIL:', exc, file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
