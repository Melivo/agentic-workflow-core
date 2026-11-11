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
# Versioned explicit targetsets; characterized from the former plan-004 task scopes.
TARGETS = 'scripts/ci_contract_targets.json'
TARGET_GROUPS = ('milestones', 'shared', 'workflows', 'domains', 'setup', 'docs')
GROUPS = ('selftest', *TARGET_GROUPS, 'all')

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
    # G04: rigid repair-round limits are replaced by evidence-based continuation;
    # the canonical catalog must not reintroduce a numeric stop.
    require('max_automatic_review_repair_rounds' not in data, 'starres Reparaturlimit im Katalog')
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
    # Plan review runs before confirmation, returns text and never creates a run.
    require({('core-plan', 'core-review'), ('core-review', 'core-plan')} <= edges and 'text' in by_id['core-review'].get('output_schemas', []), 'Planreviewübergang fehlt')
    require(by_id['core-review'].get('fresh_context_on_entry') is True and by_id['core-execute'].get('fresh_context_on_entry') is True, 'Fresh-Context-Grenze')
    # Direct entry: `text` names the request basis (no new schema); execute escalates to core-plan, never writes plans.
    execute = by_id['core-execute']
    require({'text', 'plan/v1'} <= set(execute.get('input_schemas', [])) and 'plan/v1' not in execute.get('output_schemas', []) and 'core-plan' in execute.get('successors', []), 'Execute-Plan-/Direkteingang oder Eskalation fehlt')
    unique(data.get('known_agent_ids'), 'agents')
    unique(data.get('known_tool_ids'), 'tools')
    # milestone/v1 is a read-only legacy entry: readable, never a new output.
    require('milestone/v1' in by_id['core-milestone'].get('input_schemas', []), 'Legacy milestone/v1 nicht mehr lesbar')
    for workflow in workflows:
        require('milestone/v1' not in workflow.get('output_schemas', []), 'Legacy milestone/v1 als Ausgabe erlaubt: ' + workflow['id'])
        require('max_automatic_review_repair_rounds' not in workflow, 'starres Reparaturlimit im Katalog: ' + workflow['id'])

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
# Derived execution coverage of one linked plan; never a personal approval.
GOAL_COVERED = 'goal-covered'

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
    numbers, runs, highest, bases = [], {}, {}, set()
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
                # Evidence-based continuation, no numeric stop: the next attempt must
                # name a new insight or a distinguishable testable hypothesis, and
                # repeating the same justification is not a new attempt.
                basis = event.get('basis')
                require(isinstance(basis, str) and basis.strip(), 'Reparatur ohne neue Erkenntnis oder unterscheidbare prüfbare Hypothese')
                # The modeled chain survives replacement plans and new runs.
                require(basis not in bases, 'Reparatur wiederholt dieselbe Begründung ohne neue Erkenntnis')
                bases.add(basis)
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
    if data.get('purpose') in ('handoff-first-plan', 'stage-first-plan'):
        validate_handoff_first_plan(data)
        return
    selected_entries(data['index'])
    current = [e for e in data['index']['milestones'] if e['current']]
    require(len(current) == 1, 'keine freigegebene aktuelle Etappe')
    entry, prompt = current[0], data['prompt']
    require(entry.get('current_approval') in (CONFIRMED, GOAL_COVERED), 'keine freigegebene aktuelle Etappe')
    if entry['current_approval'] == GOAL_COVERED:
        # The index value alone is no evidence; the prompt must name the coverage originals.
        refs = set(prompt.get('coverage_refs', []))
        require({prompt['goal_path'], prompt['definition_path'], prompt['index_path'], prompt['plan_path']} <= refs, 'goal-covered ohne Originalbelege')
    goal = parse_path(GOAL_RE, prompt['goal_path'], 'Prompt-Ziel')[1]
    definition = parse_path(DEF_RE, prompt['definition_path'], 'Prompt-Definition')
    require(positive_int(prompt['version']), 'Promptversion ist keine positive Ganzzahl: ' + repr(prompt['version']))
    require((definition[1], definition[2], int(definition[3])) == (goal, prompt['milestone_id'], prompt['version']), 'Prompt Name/ID/Version widerspricht Inhalt')
    require(prompt['index_path'] == prompt['goal_path'].removesuffix('goal.md') + 'index.yaml', 'Prompt-Index gehört zu anderem Ziel')
    require((prompt['milestone_id'], prompt['version'], prompt['definition_path']) == (entry['id'], entry['version'], entry['definition_path']), 'veralteter Start-/Goal-Prompt')
    require(entry['plan_paths'] and prompt['plan_path'] == entry['plan_paths'][-1], 'veralteter Start-/Goal-Prompt: Plan abgelöst')
    if prompt.get('run_path'):
        require(prompt['run_path'] in entry['run_paths'] and run_key(prompt['run_path'])[1] == plan_key(prompt['plan_path']), 'veralteter Start-/Goal-Prompt: Run nicht an Plan gebunden')

COVERAGE_DEVIATIONS = {
    'extra_function': 'Zusatzfunktion außerhalb der Kriterien',
    'changed_criteria': 'geänderte Kriterien oder Nichtziele',
    'open_decision': 'wesentliche offene Entscheidung',
    'security_risk': 'ungedecktes Sicherheitsrisiko',
    'uncovered_cost': 'ungedeckte Geld-/Usagekosten',
    'special_effect': 'ungedeckte Build-/Installations-/SCM-/Produktivwirkung',
    'stale_originals': 'veraltete Originale',
    'planning_only': 'ausdrücklicher Nur-Planen-Auftrag',
}

def coverage_gap(data, entry, prompt, handoff):
    """Return why derived coverage is not proven, or None; never grants a personal approval."""
    cov = data['coverage']
    if cov['source_kind'] != 'goal-frame':
        # Write-only, content-only, historical approval fields or a previous stage's execution order never cover.
        return 'keine belegte Gesamtfreigabe: ' + cov['source_kind']
    if not (cov['frame_explained_before_question'] and cov['frame_confirmed']):
        return 'Ausführungsrahmen nicht sichtbar vorgelegt und bestätigt'
    if cov['source_path'] != prompt['goal_path'] or cov['source_path'] not in data['original_paths']:
        return 'Gesamtfreigabequelle nicht im aktuellen Original belegt'
    if entry['definition_path'] not in cov['frame_definitions']:
        return 'Gesamtfreigabe deckt diese Definitionsversion nicht'
    required = {prompt['goal_path'], prompt['index_path'], prompt['definition_path']} | ({data['handoff_path']} if handoff else set())
    if cov['expected_verdict_given'] or not required <= set(cov['review_inputs']):
        return 'Deckungsreview ohne neutrale vollständige Originalbelege'
    if cov['review_verdict'] != 'gedeckt':
        return 'Deckungsreview: ' + cov['review_verdict']
    unknown = set(cov['deviations']) - COVERAGE_DEVIATIONS.keys()
    require(not unknown, 'unbekannte Deckungsabweichung: ' + ', '.join(sorted(unknown)))
    if cov['deviations']:
        # A reviewer verdict cannot override a concrete deviation; the user decides.
        return 'Nutzerentscheidung nötig: ' + ', '.join(COVERAGE_DEVIATIONS[d] for d in sorted(cov['deviations']))
    # Exact lookup against the concretely confirmed frame; no semantic classification.
    unconfirmed = [m for m in cov['confirmed_security_measures'] if m not in cov['frame_security_measures']]
    if unconfirmed:
        return 'Nutzerentscheidung nötig: Sicherheitsmaßnahme ohne Rahmenbeleg: ' + ', '.join(unconfirmed)
    if not cov['plan_text_evidence']:
        return 'Deckungsbeleg fehlt im Planreviewabschnitt'
    return None

def validate_handoff_first_plan(data):
    """Static prompt/index/plan relationships, never an authorization or display service."""
    handoff = data['purpose'] == 'handoff-first-plan'
    marker = 'handoff-planning' if handoff else CONFIRMED
    require(data['current_user_order'] and not data['quoted_handoff'], 'Handoff ist kein aktueller Arbeitsauftrag')
    require(handoff or data['handoff_path'] is None, 'Etappenerstplan ohne Handoff zitiert Handoff')
    require(data['originals_read'] and data['original_paths'] and all(safe_relative(p) for p in data['original_paths']), 'exakte Originalprüfung fehlt')
    require(not data['aborted'] and not data['concurrent_change'], 'Abbruch/konkurrierende Indexänderung')
    require(not data['active_plan_or_run'], 'aktive Arbeit bleibt Resume')
    require(not data['goal_completed'], 'Gesamtabschluss ohne Folgearbeit')
    require(data['activation_owner'] == 'core-milestone', 'Planungsaktivierung durch falschen Owner')
    require(data['authority'] == marker and not data['personal_approval_claim'], 'Planungsbefugnis ist keine persönliche Einzelgenehmigung')
    documents = data['documents']
    validate_artifacts(documents)
    before = next(d for d in documents if d['schema'] == 'milestone-index/v1')
    activated = data['index']
    check_index(activated)
    entries = [e for e in activated['milestones'] if e['current']]
    require(len(entries) == 1, 'genau eine Planungsaktivierung erforderlich')
    entry = entries[0]
    require(entry['current_approval'] == marker, 'Planungsaktivierung ist keine Erstplanfreigabe')
    require(not any(e['current'] for e in before['milestones']), 'aktive Arbeit bleibt Resume')
    old = next((e for e in before['milestones'] if (e['id'], e['version']) == (entry['id'], entry['version'])), None)
    require(old is not None and old['selected'] and old['selection_approval'] == CONFIRMED, 'keine bestätigte ausgewählte Version')
    expected = dict(before, revision=before['revision'] + 1, milestones=[dict(e, current=True, current_approval=marker) if e == old else e for e in before['milestones']])
    require(activated == expected and data['conditional_atomic_write'], 'Auswahl/Definition/Index unzulässig verändert')
    # Reuse the complete artifact validator for selected dependency versions and evidence.
    validate_artifacts([activated if d is before else d for d in documents])
    prompt = data['prompt']
    require(prompt == data['handoff_binding'], 'Handoff/Promptbindung widerspricht Originalen')
    originals = {prompt['goal_path'], prompt['index_path'], prompt['definition_path']} | ({data['handoff_path']} if handoff else set())
    require(originals <= set(data['original_paths']), 'exakte Originalprüfung fehlt')
    require((prompt['goal_path'], prompt['index_path']) == (before['goal_path'], before['goal_path'].removesuffix('goal.md') + 'index.yaml'), 'Handoff-Ziel/Indexbindung')
    require((prompt['milestone_id'], prompt['version'], prompt['definition_path']) == (entry['id'], entry['version'], entry['definition_path']), 'Handoff-Versions-/Auswahlkonflikt')
    require(positive_int(prompt['version']) and plan_key(prompt['plan_path'])[:3] == (parse_path(GOAL_RE, prompt['goal_path'], 'Prompt-Ziel')[1], entry['id'], entry['version']), 'Handoff-Planbindung')
    require(data['draft_path'] == prompt['plan_path'] == data['final_path'] and data['plan_file_count'] == 1, 'kein gleicher einzelner Planpfad')
    draft = data['draft']
    require(draft['status'] == 'Draft', 'statischer Erstplan ist kein Draft')
    # Validate every existing task invariant on a copy; validate_plan itself still rejects Draft.
    validate_plan(dict(draft, status='Confirmed'))
    require(data['plan_owner'] == 'core-plan' and not data['review_writes'], 'Draft-/Review-Dateibesitz')
    require(data['static_before_write'] and data['independent_review'] and data['review_pass'], 'statische Validierung/unabhängiges Planreview fehlt')
    display = data['display']
    route = 'native' if display['native_available'] else 'os' if display['gui_available'] else 'chat'
    if route != 'chat' and not display['success']:
        route = 'chat'
    require(display['route'] == route, 'Anzeige ignoriert Harness-/OS-Fallback')
    require(display['full_content'] and display['actual'] and display['after_review'], 'vollständige tatsächliche Anzeige nach Review fehlt')
    require(route != 'chat' or display['limitation_reported'], 'Anzeigeausfall/Headless verschwiegen')
    require(not display['read_claim'] and not display['approval_claim'] and not display['installs'], 'Anzeige ist keine Lese-/Freigabeevidenz oder Installation')
    gap = coverage_gap(data, entry, prompt, handoff)
    if data['new_user_approval']:
        # Real single-plan confirmation remains valid without any historical overall approval.
        require(data['approval_after_display'], 'Erstplanfreigabe vor vollständiger Anzeige')
        approval = CONFIRMED
    elif gap is None:
        approval = GOAL_COVERED if handoff else entry['current_approval']
    else:
        require(data['final_plan'] == draft and data['final_index'] == activated and not data['execute'], 'Erstplan-Halt ohne belegte Deckung verletzt: ' + gap)
        return
    require(data['final_plan'] == dict(draft, status='Confirmed'), 'bestätigte Datei/Inhalt verändert')
    require(data['link_owner'] == 'core-milestone', 'Confirmed-Verknüpfung durch falschen Owner')
    require(data['link_recheck'], 'Planlink ohne erneute Original-/Index-/Konkurrenzprüfung')
    # goal-covered replaces only handoff-planning; a real user-confirmed activation stays unchanged.
    linked = dict(entry, current_approval=approval, plan_paths=[prompt['plan_path']])
    expected = dict(activated, revision=activated['revision'] + 1, milestones=[linked if e == entry else e for e in activated['milestones']])
    require(data['final_index'] == expected, 'Confirmed-Link verändert ID-Version/Auswahl/Aktivierung')
    validate_plan(data['final_plan'])
    if data['new_user_approval']:
        require(not data['execute'] or data['execution_order'], 'Planfreigabe ist kein Ausführungsauftrag')
    elif gap is None:
        require(data['execute'], 'gedeckter Übergang wartet grundlos statt Execute')
    require(not data['execute'] or data['execute_checks'], 'Execute ohne eigene Original-/Review-/Indexprüfung')


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

DOX_GAP_STATES = ('missing', 'partial', 'conflict')
RUN_ARTIFACT_PREFIX = '.agentic-workflow/'
DOCS_FIELDS = ('mode', 'tree', 'initializes', 'setup_planned', 'setup_available', 'conflict_resolved', 'reported_blocked', 'docs_needed', 'dox_pass_reason', 'evidence', 'sources_exist', 'task_confirmed', 'diff_evidence', 'unrelated_legacy', 'new_interface', 'connections_documented', 'parallel_docs', 'secret_values', 'secret_store_access', 'changes_goal_decisions', 'changed_paths', 'scope')

def validate_docs(data):
    """Modeled DOX documentation relations of one task; not observed agent behavior."""
    missing = [f for f in DOCS_FIELDS if f not in data]
    require(not missing, 'Docsmodell unvollständig: ' + ', '.join(missing))
    changed = data['changed_paths']
    require(set(changed) <= set(data['scope']), 'Docs erweitert Scope')
    require(not data['changes_goal_decisions'], 'Docs überschreibt bestätigte Zielentscheidung')
    require(not data['secret_values'] and not data['secret_store_access'], 'Docs enthält Secretwert oder durchsucht Secretablage')
    require(not data['parallel_docs'], 'parallele Dokumentationsstruktur ohne Auftrag')
    initializes = data['initializes']
    if data['mode'] == 'read-only':
        require(not changed and not initializes, 'Read-only-Arbeit schreibt Docs oder DOX-Setup')
        return
    require(data['mode'] == 'write', 'unbekannter Docsmodus: ' + str(data['mode']))
    tree = data['tree']
    require(tree == 'valid' or tree in DOX_GAP_STATES, 'unbekannter DOX-Zustand: ' + str(tree))
    if initializes:
        require(tree != 'valid', 'DOX-Initialisierung trotz gültigem Baum')
        require(data['setup_planned'], 'unautorisierte DOX-Initialisierung ohne bestätigten Plan')
        require(data['setup_available'], 'DOX-Setupfähigkeit oder gültige Quelle fehlt')
        require(tree != 'conflict' or data['conflict_resolved'], 'DOX-Konflikt ungeklärt')
    if data['reported_blocked']:
        require(not changed and not initializes, 'blockierter DOX-Task schreibt dennoch')
        return
    if not data['docs_needed']:
        # Harmless change: no guide edit and no setup duty, but a reasoned DOX pass.
        require(not changed, 'Docs ohne belegte Drift oder Lücke')
        require(data['dox_pass_reason'], 'DOX-Pass ohne geprüfte Pfade/Grund')
        return
    require(tree == 'valid' or initializes, 'unvollständiger DOX-Baum weder geplant noch blockiert')
    require(changed, 'erforderliche Dokumentation fehlt')
    require(not all(p.startswith(RUN_ARTIFACT_PREFIX) for p in changed), 'Laufartefakt ersetzt Projektdokumentation')
    require(data['evidence'] in ('drift', 'new_gap'), 'Docs ohne belegte Drift oder Lücke')
    require(data['sources_exist'], 'Docs ohne autoritative Quelle')
    require(data['evidence'] != 'new_gap' or (data['task_confirmed'] and data['diff_evidence']), 'neue Lücke ohne bestätigten Task/aktuellen Diff')
    require(not data['unrelated_legacy'], 'unabhängige Altlast nebenbei dokumentiert')
    require(not data['new_interface'] or data['connections_documented'], 'neue Schnittstelle/Konfiguration ohne dokumentierte Verbindungen')

def validate_artifacts(documents):
    for document in documents:
        check_format(document['schema'], document)
    check_example_relations(documents)

def validate_execute_entry(data):
    """Plan and direct entries are exclusive; lost or bound plan work never becomes direct."""
    mode = data.get('mode') or ('plan' if data.get('plan_path') else None)  # legacy plan_path without mode
    require(mode in ('plan', 'direct'), 'unbestimmter Execute-Eingang')
    require(bool(data.get('plan_path')) != bool(data.get('request_path')), 'Execute-Eingang nicht exklusiv')
    if mode == 'plan':
        require(data.get('plan_path') and data['plan_confirmed'], 'Planmodus ohne bestätigten Plan')
        return
    require(data.get('request_path'), 'Direktlauf ohne request_path')
    require(not data['plan_lost'] and not data['bound_plan_or_milestone'], 'Plan-/Etappenarbeit in Direktmodus umgedeutet')
    require(data['explicit_change_order'], 'Direktmodus ohne ausdrücklichen Änderungsauftrag')
    require(not data['needs_decomposition'] and not data['material_decision'], 'Direktgrenze überschritten')
    require(data['request_before_mutation'] and data['owner_count'] == 1, 'Auftragsgrundlage oder eindeutiger Owner fehlt')
    require(not data['fake_plan'], 'fingierter Plan im Direktmodus')
    require(set(data['changed_paths']) <= set(data['request_scope']), 'Direktscope erweitert')
    require(data['resume_reads_exact_input'] and data['review_reads_exact_input'], 'Resume/Review ohne exakten Eingang')

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
        validate_docs(data)
    elif kind == 'legacy':
        require(data['schema'] == 'milestone/v1' and not data['mixed_formats'], 'Legacyformat vermischt')
        require(not data['automatic_migration'] and not data['automatic_rename'], 'automatische Legacy-Migration/Umbenennung')
        require(data['explicit_entry'], 'vermeintlich neueste Datei statt exaktem Einstieg')
    elif kind == 'authorization':
        # Z01/Z02: purpose-bound frame, technical alternatives vs. goal change,
        # effort vs. additional money; fail closed on unclear impact or coverage.
        require(data['frame_confirmed'], 'Erstplanung ohne bestätigten Rahmen bleibt bestätigungspflichtig')
        require(not data['goal_changed'], 'geändertes Ziel benötigt Nutzerentscheidung')
        if data['technical_change']:
            require(data['within_frame'], 'technische Anpassung außerhalb des Rahmens')
        require(data['coverage_known'], 'unbekannte Deckung vor kostenauslösender Aktion klären')
        require(not data['extra_monetary_cost'] or data['consent_given'], 'zusätzliche monetäre Kosten ohne vorherige Zustimmung')
        require(not data['uncovered_usage'], 'ungedeckte KI-/Harnessusage ohne Rücksprache')
        if data['production_effect']:
            require(data['impact_clear'] and data['recovery_safe'], 'ungedeckte oder unklare Produktionswirkung stoppt')
    elif kind == 'safety':
        # Z04: decisive assumption, indirect effects, evidence strength; no external duties.
        require(data['assumption_named'] and data['indirect_effects_considered'], 'entscheidende Sicherheitsannahme oder indirekte Folgen unbenannt')
        require(data['evidence_strength'] in ('belegt', 'widerlegt', 'offen'), 'Evidenzstärke nicht klassifiziert')
        require(data['checked_or_marked_open'], 'Annahme weder geprüft noch offen markiert')
        require(not data['external_skill_duty'], 'Blast-Radius-/Arena-/Modellanbieterpflicht')
    elif kind == 'delegation':
        # Z06: delegated tests stay with the agent; personal consent handed over.
        require(not data['personal_repetition'] or data['requirement_confirmed'], 'persönliche Wiederholung ohne bestätigte Anforderung')
        require(not data['personal_action'] or data['handed_over'], 'persönliche Anmeldung/Zustimmung/Abnahme nicht übergeben')
        require(not data['sandbox_delegated'] or data['agent_operates'], 'delegierte Testbedienung zum Nutzer verlagert')
        require(data['session_artifacts_exact'] and data['drift_checked'], 'Sitzungswechsel ohne exakte Artefakte oder Driftprüfung')
        require(not data['new_start_formula'], 'neue Startformel statt bestehender Freigaben')
        require(not data['auto_follow_up'], 'automatische Folgeetappe')
        require(not data['time_budget_loop'], 'neue Zeitbudget-/Bereitschaftsschleife')
    elif kind == 'execute_entry':
        validate_execute_entry(data)
    elif kind == 'approval_override':
        # A current task-bound order replaces lower-priority confirmation gates, nothing more.
        if data['gate_skipped']:
            require(data['current_task_instruction'] and data['explicit_change_order'], 'Freigabehinweis ohne Änderungsauftrag')
            require(not data['overrides_higher_priority'], 'höherrangige Grenze überstimmt')
            require(not (data['new_goal'] or data['uncovered_cost'] or data['uncovered_effect']), 'Freigaberahmen überschritten')
        require(data['preview_kept'] and data['drift_marker_checked'] and data['foreign_content_protected'], 'Vorschau/Drift/Marker/Fremdschutz entfallen')
        require(not data['preview_claimed_seen'], 'Vorschau als gesehen dargestellt')
    elif kind == 'support_delegation':
        require(data['dispatcher'] == 'core-execute' == data['integrator'], 'Zusatzdelegation nicht durch Execute')
        require(data['owner_after'] == data['owner_before'], 'Taskowner gewechselt')
        require(data['within_task_goal'] and set(data['support_paths']) <= set(data['task_scope']), 'Zusatzdelegation außerhalb Taskziel/-scope')
        require(not data['nested_delegation'], 'Unterstützer delegiert weiter')
        require(not data['parallel_same_scope_write'], 'gleicher Schreibscope parallel')
        require(not data['plan_mutated'] and not data['new_plan_task'], 'Planmutation durch Zusatzdelegation')
        require(data['recorded_in_run'], 'Zusatzdelegation nicht im Run belegt')
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
        require(not data['milestone_mode'] or not data['next_started'], 'Etappenabschluss verlangt Handoff und Halt statt Folgestart')
        require(not data['goal_completed'] or data['goal_evidence'], 'Gesamterfolg unbelegt')
    elif kind == 'goal_binding':
        validate_goal_binding(data)
    elif kind == 'task_cut':
        validate_task_cut(data)
    elif kind == 'tool_choice':
        validate_tool_choice(data)
    elif kind == 'goal_check':
        validate_goal_check(data)
    elif kind == 'plan_review':
        validate_plan_review(data)
    else:
        raise ContractError('unbekannter Szenariotyp: ' + str(kind))


def validate_goal_binding(data):
    # Optional goal source: sighting is no selection authority; unclear stays unclear.
    require(not data['recursive_history'], 'rekursive Historienlektüre statt begrenzter Sichtung')
    require(not data['artifact_created'], 'Zielartefakt auf Vorrat')
    require(not data['agent_selected'], 'eigenmächtige Etappenauswahl')
    outcome = data['outcome']
    require(outcome in ('bind', 'ordinary', 'clarify'), 'unbekanntes Bindungsergebnis')
    if data['read_error']:
        require(outcome == 'clarify', 'Lese-/Parsefehler als Abwesenheit gewertet')
        return
    relevant = [c for c in data['candidates'] if c['matches']]
    if not relevant:
        require(outcome == 'ordinary', 'fehlende/sachfremde Etappe blockiert normalen Auftrag')
    elif len(relevant) == 1 and all(relevant[0][k] for k in ('current', 'selected', 'confirmed')):
        require(outcome == 'bind' and data['originals_checked'], 'passende Etappe nicht originalgeprüft gebunden')
    else:
        require(outcome == 'clarify', 'mehrdeutige oder unbestätigte Bindung nicht geklärt')


def validate_task_cut(data):
    # Result boundaries decide the cut, not tool calls or a bare size verdict.
    require(not data['split_per_tool_call'], 'Zerlegung pro Toolaufruf')
    if data['atomic']:
        require(not data['split'], 'notwendiger atomarer Vorgang zerlegt')
    elif data['independent_results'] > 1 or data['effect_boundaries'] > 1 or data['hidden_phases']:
        require(data['split'], 'übergroßer Task nicht zerlegt')
    require(not data['review_rejects'] or data['named_boundaries'], 'Größenurteil ohne belegte Grenze')

def validate_tool_choice(data):
    # Necessity order: omit, existing means, justified tool, smallest own code; no silent effects.
    choice = data['choice']
    require(choice in ('omit', 'existing', 'new_tool', 'own_code'), 'unbekannte Werkzeugwahl')
    require(not data['installed'] or data['install_approved'], 'Installation ohne Freigabe')
    require(not data['gate_disabled'] or data['scope_decision'], 'Schutzgate still abgeschaltet')
    require(not data['security_requirement_dropped'], 'Sicherheitsanforderung mit Umsetzung entfernt')
    if not data['result_needed']:
        require(choice == 'omit', 'nicht benötigtes Ergebnis gebaut oder repariert')
        return
    require(choice != 'omit', 'benötigtes Ergebnis weggelassen')
    require(choice != 'existing' or data['existing_fits'], 'ungeeignete vorhandene Funktion gewählt')
    if data['existing_fits']:
        require(choice == 'existing', 'vorhandene Funktion übergangen')
    elif choice == 'new_tool':
        require(data['relevant_advantage'] and data['tool_risks_weighed'], 'neues Werkzeug ohne Vorteil/Abwägung')
    elif choice == 'own_code':
        require(data['gap_named'] and data['smallest'], 'Eigenbau ohne belegte Lücke oder nicht minimal')

def validate_plan_review(data):
    # Whole path before details; formally correct bloat is no pass, lean legitimate work is.
    verdict = data['verdict']
    require(verdict in ('pass', 'changes_requested', 'blocked'), 'unbekanntes Planreviewurteil')
    require(data['fresh_context'] and not data['extra_review_level'], 'Frischkontext oder Reviewebene verändert')
    require(data['originals_anchor'], 'gewünschtes Urteil oder Vorgänger-pass als Anker')
    bloated = data['unneeded_tasks'] or data['inherited_gate_unjustified'] or data['smaller_path_ignored'] or data['oversized_task']
    if verdict == 'pass':
        require(data['whole_path_checked'], 'Detailkorrektheit ohne Gesamtwegprüfung')
        require(not bloated, 'formal korrekter aufgeblähter Plan bestanden')
        require(not data['other_defect'], 'Plan mit anderem Defekt bestanden')
    else:
        require(data['named_decisions'], 'Urteil ohne konkret geprüfte Entscheidung oder Lücke')
        require(bloated or data['other_defect'], 'legitime schlanke Arbeit zurückgewiesen')
        require(not data['split_demanded'] or data['named_boundaries'], 'Größenurteil ohne belegte Grenze')

def validate_goal_check(data):
    # Short goal check at every result/resume trigger, inside existing result fields only.
    require(data['trigger'] in ('result', 'resume', 'new_helper', 'own_blocker'), 'unbekannter Zielabgleichsauslöser')
    require(data['goal_checked'], 'Zielabgleich am Auslöser ausgelassen')
    require(not data['new_status_or_field'] and not data['mandatory_model_or_review'], 'Zielabgleich als neuer Status, Feld oder Pflichtaufruf')
    require(not data['helper_effects'] or data['helper_effects_recorded'], 'privater/externer Helper unsichtbar')
    require(not data['read_only_task'] or not data['helper_effects'], 'read-only Task durch Helper umgangen')
    require(not data['only_helper_tests_green'] or data['goal_progress'] or data['simplified_or_replanned'], 'grüne Helpertests ersetzen Zielfortschritt')
    if data['repeated_local_repair'] and not data['goal_progress']:
        require(data['whole_path_reviewed'], 'wiederholte Reparatur ohne Gesamtwegprüfung')
        require(data['decision'] in ('continue_justified', 'simplify', 'replan', 'stop'), 'Gesamtwegprüfung ohne Folge')
    require(not data['fixed_limit_stop'], 'starrer Retry-/Zeitstopp')

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
    require(all(m.get('current_approval') in (CONFIRMED, 'handoff-planning', GOAL_COVERED) for m in current), 'aktuelle Etappe ohne Freigabe')
    for entry in current:
        if entry['current_approval'] == 'handoff-planning':
            require(not entry['plan_paths'] and not entry['run_paths'] and not entry['completion_refs'], 'Planungsaktivierung enthält bestätigten Plan/Run/Abschluss')
        if entry['current_approval'] == GOAL_COVERED:
            # The value only labels a linked covered plan; it never proves coverage by itself.
            require(entry['plan_paths'], 'goal-covered ohne verknüpften Confirmed-Plan')
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
    # Original sources and prior-run evidence may live outside the completion run.
    # This validates path syntax, not existence or substantive criterion coverage.
    require(isinstance(ref['evidence_paths'], list) and ref['evidence_paths'] and all(safe_relative(p) for p in ref['evidence_paths']), 'Evidenz ist kein sicherer projektrelativer Pfad: ' + str(ref['evidence_paths']))
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
    'shared': [(r'(?:Execute|core-execute)[^.!\n]*(?:persistiert|schreibt)[^.!\n]*read-only', 'Execute persistiert read-only Ergebnisse'), (r'(?:Versuch|attempt)[^.!\n]*unveränder|unveränder[^.!\n]*(?:Versuch|attempt)', 'unveränderliche Versuche'), (r'(?:referenz|angewiesen)[^.!\n]*(?:erhalten|aufbewahr)', 'referenzabhängige Aufbewahrung'),
               (r'Dateiscope[^.!\n]*(?:keine|nicht)[^.!\n]*Verantwortlich', 'Dateiscope ist keine Funktionsfreigabe'), (r'kumulativ[^.!\n]*(?:ursprünglich|Original)', 'kumulativer Scope gegen Originalbezug'), (r'Ersatzplanzyklus[^.!\n]*früh', 'Vereinfachungsstopp'), (r'Umbenennung[^.!\n]*nicht zurück', 'Umbenennung setzt nicht zurück'), (r'Planreview[^.!\n]*keinen Run', 'Planreview ohne Run'), (r'(?:Planreview-pass[^.!\n]*nicht[^.!\n]*bestätigt|Review-pass bedeutet nur prüffähig, niemals Nutzerbestätigung|Qualität `pass` heißt bestätigungsfähig, niemals bestätigt)', 'Planreview-pass ist keine Bestätigung'),
               (r'Eigenentwicklung[^.!\n]*belegte Lücke', 'Standard vor unbegründeter Eigenentwicklung'), (r'(?:keine|kein)[^.!\n]*präventiv', 'kein präventiver Zusatz'), (r'Übernommen\w* technisch\w* Voraussetzung\w*[^.!\n]*neu begründet', 'übernommene Voraussetzung neu begründen'), (r'(?:entfernt|vereinfach)[^.!\n]*nicht durch weitere Mechanismen', 'Vereinfachen statt kompensieren'),
               (r'beobachtbar\w* Verhalten[^.!\n]*Fehler\w*[^.!\n]*getrennt von technischen Entscheidungen', 'Verhalten getrennt von Lösung'), (r'technisch\w* Nutzerconstraints?[^.!\n]*verbindlich', 'Nutzerconstraint bleibt verbindlich'), (r'Agentenpräferenz[^.!\n]*nicht[^.!\n]*Nutzeranforderung', 'Agentenpräferenz keine Nutzeranforderung'), (r'Kleinfix[^.!\n]*nur[^.!\n]*Regressionstest', 'schlanker Kleinfix'),
               (r'(?:jede|alle) ursprünglich\w* Anforderung\w*[^.!\n]*Fehlerf', 'vollständige Originalabdeckung'), (r'Grün\w* selbst gewählt\w* Kriterien genügen nicht[^.!\n]*ursprünglich\w* Fehlerfall', 'grüne Eigenkriterien genügen nicht'), (r'Unbegründet\w* Zusätze entfallen', 'keine ungefragten Zusätze'), (r'keine zusätzlichen YAML-Felder', 'Abdeckung ohne neue Felder'),
               (r'bestätigt\w* Verhalten[^.!\n]*Vorher/Nachher', 'Verhaltensänderung über Ersatzplanung'), (r'technische Alternative ohne Verhaltens[^.!\n]*keine neue Nutzeranforderung', 'technische Alternative ohne neue Freigabe'),
               # DOX documentation contract (T02 of plan-dox-projektdokumentation).
               (r'Root-to-Target-Kette[^.!\n]*AGENTS\.md', 'DOX Root-to-Target-Dokumentation'), (r'nicht ohne erforderliche Dokumentationsaktualisierung abgeschlossen', 'kein Abschluss ohne Dokumentation'), (r'kein Guide-Edit nötig[^.!\n]*geprüfte Pfade[^.!\n]*Grund', 'begründeter DOX-Pass'),
               (r'Read-only-Arbeit[^.!\n]*harmlose Änderungen[^.!\n]*weder Schreib- noch Setup-Pflicht', 'read-only ohne DOX-Setuppflicht'), (r'Laufartefakte ersetzen keine Projektdokumentation', 'Laufartefakt ist keine Projektdokumentation'), (r'neue Dokumentationslücke[^.!\n]*bestätigt\w* Task[^.!\n]*Diff[^.!\n]*autoritativ', 'belegte neue Dokumentationslücke'),
               (r'Erst Planbestätigung autorisiert[^.!\n]*Setupwirkung', 'DOX-Setup nur nach Planbestätigung'), (r'Fehlt es oder eine gültige Quelle[^.!\n]*blockiert', 'fehlende DOX-Setupfähigkeit blockiert'), (r'Secrets nennt nur[^.!\n]*Referenznamen[^.!\n]*weder Secretwerte', 'kein Secretwert in Dokumentation'),
               # G04 Z01-Z06: purpose-bound authorization, effort vs. money, evidence-based attempts, decisive assumptions, delegation.
               (r'Mehr Arbeitsaufwand[^.!\n]*keine erneute Rückfrage', 'Aufwand allein keine Rückfrage'), (r'materiell unklare oder ungedeckte Wirkung stoppt', 'unklare Wirkung stoppt'), (r'Zusätzliche monetäre Kosten[^.!\n]*brauchen vorherige Zustimmung', 'monetäre Kosten brauchen Zustimmung'),
               (r'Der nächste Versuch benennt neue Erkenntnis[^.!\n]*unterscheidbare prüfbare Hypothese', 'evidenzbasierte Fortsetzung statt starrer Rundenzahl'), (r'ohne tragfähigen Korrekturansatz folgt die Nutzerentscheidung', 'Planreviewfortsetzung evidenzbasiert'),
               (r'entscheidende Sicherheitsannahme', 'entscheidende Sicherheitsannahme'), (r'indirekte\w* Folgen jenseits direkter Aufrufer', 'indirekte Folgen jenseits Aufrufer'), (r'Evidenzstärke[^.!\n]*belegt, widerlegt oder offen', 'Evidenzstärke klassifizieren'),
               (r'Delegierte Sandbox- und Testbedienung bleibt beim Agenten', 'delegierte Testbedienung beim Agenten'), (r'persönliche Wiederholung erfolgt nur nach bestätigter Anforderung', 'keine unbestätigte persönliche Wiederholung'), (r'ohne neue Startformel und ohne automatische Folgeetappe', 'keine neue Startformel'), (r'keine neuen Zeitbudget- oder Bereitschaftsschleifenregeln', 'keine Zeitbudget- oder Bereitschaftsschleifen'),
               # G04/M02 K1: bounded canonical clauses, not a general prose oracle.
               (r'Nur ein konkreter Auftrag mit tatsächlich benötigtem Vorher-/Nachher-Messvergleich aktiviert die Vergleichbarkeitsregeln:', 'Messvergleich nur bei Auftragsbedarf'),
               (r'benannte Metrik mit Einheit und Richtung', 'Messvergleich mit Metrik, Einheit und Richtung'),
               (r'gleiche Methode und gleicher Befehl, gleiche Daten und gleiche Umgebung', 'Messvergleich mit gleichem Befehl'),
               (r'aktuelle Originalbelege mit Runbezug sowie die relevante fachliche Akzeptanz', 'Messvergleich mit aktuellen Belegen und Akzeptanz'),
               (r'Bei rauschenden Metriken gilt die vorhandene projektspezifische Stichproben- oder Toleranzmethode;', 'Projektmethode nur bei Rauschen'),
               (r'Pflichtkriterien, Korrektheit sowie Sicherheits- und Freigabegrenzen bleiben unabhängig vom Messergebnis', 'unabhängige Pflicht- und Freigabegrenzen'),
               (r'Vorher-/Nachher-Messvergleich[^.!\n]*gleiche Methode[^.!\n]*gleiche Daten[^.!\n]*gleiche Umgebung', 'Messvergleich mit gleicher Methode, Daten und Umgebung'),
               (r'einzelne Timingprobe[^.!\n]*keine Regression', 'Einzelprobe beweist keine Regression'),
               (r'fehlende Evidenz offen[^.!\n]*nicht als Verbesserung', 'fehlende Messung ist keine Verbesserung'),
               (r'gewöhnliche Tests und Lint[^.!\n]*keine Mess- oder Scoringphase', 'gewöhnliche Checks lösen keine Messphase aus'),
               (r'Geschwindigkeitsgewinn kompensiert keine Verletzung', 'Messergebnis kompensiert keine Grenzverletzung')],
    'workflows': [(r'(?:Start|Resume)[^.!\n]*(?:Version|Auswahl|Definition)', 'Start/Resume Versionsprüfung'), (r'(?:Folgeetappe|nächste Etappe)[^.!\n]*(?:Freigabe|Bestätigung)', 'Folgefreigabe'), (r'(?:Review|core-review)[^.!\n]*(?:gepinnt|festgelegt|Definitionsversion)', 'Review gegen gepinnte Fassung'),
                  (r'Ausschließlich für das \[?Planreview\]?(?:\([^)\s]*\))?[^.!\n]*qa-reviewer', 'schmale Planreview-Dispatchausnahme'), (r'ohne historisch\w* Planreview[^.!\n]*Kompatibilitätsprüfung', 'Legacy-Kompatibilitätsprüfung'), (r'Bloat[^.!\n]*(?:Verwerfen|Rückbau)', 'Bloat verwerfen statt ausbauen'),
                  (r'Trenne Verhalten[^.!\n]*Anforderungsherkunft[^.!\n]*technischen Entscheidungen', 'Plan trennt Anforderung und Lösung'), (r'Alle ursprünglichen Anforderungen[^.!\n]*gedeckt[^.!\n]*unbegründete Zusätze fehlen', 'Plan prüft Originalabdeckung'),
                  (r'DOX-Zustand[^.!\n]*vorhanden, fehlend, teilweise oder widersprüchlich', 'Plan prüft DOX-Zustand'), (r'Initialisierung oder Ergänzung darf nur ausgeführt werden, wenn konkrete Pfade[^.!\n]*bestätigten Task-Scope', 'Execute initialisiert nur gescopt'), (r'Laufprotokoll ist kein Ersatz für Projektdokumentation', 'Review prüft Projektdokumentation'),
                  (r'nächste automatische `execute ↔ review`-Reparatur nur gemäß', 'evidenzbasierte Review-Reparatur')],
    'domains': [(r'(?:Bedarf|Übergabe)[^.!\n]*(?:Execute|core-execute)', 'vermittelter Domainbedarf'), (r'(?:fehlend\w* Task|fehlt[^.!\n]*Task|materiell\w* Vertragsänderung)[^.!\n]*(?:Plan|core-plan)', 'fehlender Task zurück an Plan'), (r'(?:Fachagent|Fachskill)[^.!\n]*(?:nicht|keine|weder)[^.!\n]*(?:Version|Ziel|Index)', 'Zielschutz'),
                (r'widersprüchlich\w* Prosa[^.!\n]*Dokumentationslücke nicht erforderlich', 'neue belegte Lücke ohne Driftpflicht'), (r'Fehlt die Fähigkeit oder eine gültige Quelle, blockiere', 'Docs blockiert ohne DOX-Setupfähigkeit'),
                (r'zusätzliche monetäre Kosten brauchen vorherige Zustimmung', 'Domain-Kostenklausel')],
    'setup': [(r'(?:MCP|Provider)[^.!\n]*read-only|read-only[^.!\n]*(?:MCP|Provider)', 'read-only Providerprüfung'), (r'(?:keine|kein|nicht)[^.!\n]*(?:Installation|Installer|installiert)', 'kein Installer'), (r'(?:einzeln|beschädigt|doppelt)[^.!\n]*(?:block|stopp)', 'beschädigte Marker blockieren')],
    'docs': [(r'(?:einfache Vorhaben|ohne Milestones)[^.!\n]*(?:keine|nur|ohne)[^.!\n]*(?:Zielstruktur|Plan|Ziel)', 'einfacher Einstieg'), (r'Resume[^.!\n]*(?:dieselbe|gleichen|unverändert)[^.!\n]*Run', 'Resume behält Run'), (r'(?:Definition|Version)[^.!\n]*unveränder', 'unveränderliche Definition')],
}

# Plan 003 K1-K6, its synergies and every T08 case named by plan 004.
REQUIRED_COVERAGE = (
    'K1-read-only-ergebnisbesitz', 'K2-run-pass-kein-etappenabschluss', 'K3-katalog-etappenzyklus', 'K4-eigentum-aufbewahrung', 'K5-marker-neuanlage', 'K6-mcp-pruefung-statt-installer',
    'S-brainstorm-plan-milestone', 'S-plan-fachmethoden', 'S-refactor-safety-net', 'S-execute-review-debug', 'S-audit-plan-brainstorm', 'S-milestone-handoff-wiedereinstieg', 'S-domain-uebergaben', 'S-fachskill-docs',
    'gueltige-neuanlage', 'legacy-einstieg', 'bestaetigter-ersatz', 'nicht-ausgewaehlte-neuere-datei', 'veralteter-plan-goal-prompt', 'laufender-run-versionswechsel', 'geaenderte-abhaengigkeit', 'fehlende-definition-designquelle', 'id-versionskonflikt', 'zyklischer-graph', 'teilweise-geschriebene-struktur', 'konkurrierende-aenderung', 'historische-abschlusszuordnung',
    'namenskollision', 'widerspruechliche-ids', 'falsche-versionszuordnung', 'ersatzplannummer', 'run-id-resume-review-reparatur', 'keine-automatische-umbenennung', 'kein-geerbter-abschluss', 'resume', 'review-ready', 'folgefreigabe', 'gesamtabschluss', 'unveraenderliches-ziel', 'hoechstens-eine-aktuelle-etappe',
    'S-dox-projektdokumentation',
    'g04-authorization-rahmen', 'g04-kosten-aufwand-trennung', 'g04-reparatur-evidenzbasis', 'g04-blast-radius', 'g04-delegation-consent', 'g04-katalog-ohne-limit',
    'execute-direkt-eingang', 'execute-freigabevorrang', 'execute-zusatzdelegation',
    'handoff-planungsbefugnis', 'handoff-erstplan-halt', 'handoff-sichtbare-anzeige', 'handoff-gesamtdeckung',
    'initialer-rahmen-und-erhaltene-handoffdeckung',
    'zielbindung-optional', 'taskgrenzen', 'notwendigkeitsfolge', 'zielabgleich', 'planreview-gesamtweg',
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


def validate_targetsets(data):
    require(isinstance(data, dict) and data.get('schema') == 'ci-contract-targets/v1', 'Targetsetschema ci-contract-targets/v1 erforderlich')
    groups = data.get('groups')
    require(isinstance(groups, dict) and tuple(groups) == TARGET_GROUPS, 'Targetsets müssen exakt die Gruppen ' + ', '.join(TARGET_GROUPS) + ' nennen')
    for group, paths in groups.items():
        require(isinstance(paths, list) and paths, 'leeres Targetset: ' + group)
        unique(paths, 'Targetset ' + group)
        require(all(safe_relative(p) for p in paths), 'Targetset ' + group + ': kein sicherer projektrelativer Pfad')
    return groups

def targets(root, group):
    try:
        data = json.loads((root / TARGETS).read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        raise ContractError('ungültige Targetsets: ' + str(exc)) from exc
    return [local_path(root, p) for p in validate_targetsets(data)[group]]

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


# RV05: source-local clauses for the real replacement-plan path, not an authorization engine.
REPLACEMENT_SOURCES = {
    '.apm/skills/core-shared/references/workflow-contract.md': (
        r'Für einen gedeckten technischen Ersatzplan[^.]*abgeleitete Freigabe[^.]*exakter Original- und Vorgängerpfade[^.]*unveränderter Ziel-/Meilensteinkriterien[^.]*Wirkungs-/Risikorahmens',
        r'Nach statischer Validierung und unabhängigem Planreview-pass[^.]*ohne neue Nutzerbestätigung schreiben[^.]*bestehendem Ausführungsauftrag',
        r'Ohne bestätigten Rahmen[^.]*neuen eigenständigen Zielen[^.]*Meilensteinänderungen[^.]*Ausschlüssen[^.]*materiell offenen Entscheidungen[^.]*unklaren oder ungedeckten Wirkungen[^.]*ungedeckten Geldkosten[^.]*vor Schreiben und Ausführung[^.]*Nutzerentscheidung',
        r'Scopes blockieren[^.]*ausdrücklich oder abgeleitet freigegebenen neuen Plan',
        r'abgeleitet freigegebener Ersatzplan[^.]*neuen Run[^.]*Vorgängerplan und -run',
        r'Qualität `pass` heißt bestätigungsfähig, niemals bestätigt',
        r'abgeleitet freigegebener Ersatzplan[^.]*bestehendem Ausführungsauftrag[^.]*neuen Run',
        r'Der bestätigte Plan bleibt während der Ausführung unverändert',
    ),
    '.apm/skills/core-plan/SKILL.md': (
        r'Nutze anschließend Schritt 5[^.]*statische Validierung[^.]*unabhängige Planreview',
        r'technische Ersatzpläne[^.]*innerhalb des freigegebenen Rahmens benötigen keine erneute Nutzerentscheidung[^.]*abgeleitete Planfreigabe[^.]*exakte Original- und Vorgängerpfade',
        r'Eine offene Unsicherheit[^.]*Ziel, Sicherheit, Architektur, Scope oder Akzeptanz[^.]*verhindert `Confirmed`',
        r'Reguläre und technische Ersatzpläne behalten[^.]*status: Confirmed',
        r'Technische Ersatzplanung und reguläre Erstplanung ohne Etappenbindung folgen unverändert ihren bisherigen Regeln',
        r'Bloße Planerstellung startet keine Ausführung',
        r'Eine gegebenenfalls noch erforderliche Nutzerbestätigung erfolgt erst nach dem Review',
    ),
    '.apm/skills/core-review/SKILL.md': (
        r'Planentwurf \(regulär vor kanonischem Schreiben, Erstplan-Draft einer Etappe oder eines Handoffs nach dessen Schreiben\) vor einer gegebenenfalls noch erforderlichen Nutzerbestätigung',
        r'reguläres Planreview vor kanonischem Schreiben[^.]*Draft-Review eines Erstplans im Etappenmodus oder aus einem Handoff[^.]*jeweils vor einer gegebenenfalls noch erforderlichen Nutzerbestätigung',
    ),
    '.apm/skills/core-execute/SKILL.md': (
        r'prüfe vor Annahme des Ersatzplans[^.]*abgeleitete Freigabe[^.]*statische Validierung und unabhängigen Planreview-pass',
        r'gedeckter technischer Ersatzplan[^.]*bestehendem Ausführungsauftrag keine neue Nutzerbestätigung',
    ),
    '.apm/skills/core-milestone/SKILL.md': (
        r'Ohne diesen Rahmen erlauben sie nur die Inhaltsbestätigung und die erste Detailplanung nach ausdrücklicher Nutzerfreigabe',
        r'Die Planerstellung allein startet keine Ausführung',
        r'neue Plan- oder Ersatzplanpfade[^.]*statischer Validierung[^.]*unabhängigem Planreview[^.]*abgeleiteter Freigabe[^.]*ohne neue Einzelbestätigung',
    ),
    '.apm/skills/core-handoff/assets/start-prompt.md': (
        r'abgeleitet freigegebenen Plan und bestehenden Ausführungsauftrag[^.]*gedeckte technische Ersatzpläne verlangen keine neue Nutzerbestätigung',
        r'statische Validierung, unabhängiges Planreview[^.]*abgeleitete Freigabe gemäß Workflowvertrag bleiben erforderlich',
        r'Bloße Zieldefinition oder Planerstellung startet keine Ausführung',
    ),
    'README.md': (
        r'statischer Validierung[^.]*core-review[^.]*vor dem kanonischen Schreiben und einer noch erforderlichen Nutzerbestätigung',
        r'belegte abgeleitete Freigabe[^.]*neue Nutzerbestätigung entfällt',
        r'Ohne bestätigten Rahmen[^.]*neuen eigenständigen Zielen[^.]*Meilensteinänderungen[^.]*Ausschlüssen[^.]*materiell offenen Entscheidungen[^.]*unklaren oder ungedeckten Wirkungen[^.]*ungedeckten Geldkosten[^.]*Nutzerentscheidung vor Schreiben und Ausführung',
        r'Umsetzung setzt stets eine ausdrückliche oder belegte abgeleitete Planfreigabe und einen bestehenden Ausführungsauftrag voraus',
    ),
    'DESIGN.md': (
        r'Nach statischer Validierung und unabhängigem Planreview-pass[^.]*belegter abgeleiteter Freigabe ohne neue Nutzerbestätigung kanonisch geschrieben[^.]*bestehendem Ausführungsauftrag',
        r'Ohne bestätigten Rahmen[^.]*neuen eigenständigen Zielen[^.]*Meilensteinänderungen[^.]*Ausschlüssen[^.]*materiell offenen Entscheidungen[^.]*unklaren oder ungedeckten Wirkungen[^.]*ungedeckten Geldkosten[^.]*Nutzerentscheidung vor Schreiben und Ausführung',
        r'Planreview-pass erteilt selbst keine Freigabe[^.]*bloße Planerstellung startet keine Ausführung',
        r'Nach vollständigem, statisch validiertem Entwurf und vor kanonischem Schreiben sowie einer noch erforderlichen Nutzerbestätigung',
    ),
}

# Handoff first-plan clauses stay source-local; these are bounded textual contracts,
# not a natural-language oracle or a live harness/display test.
# Der Bullet "Autorisierte Arbeit" steht wortgleich in Root und Init-Vorlage.
AUTHORIZED_WORK_CLAUSES = (
    r'Eine Gesamtfreigabe deckt nur die im sichtbaren Freigabebeleg genannten Etappen innerhalb des bestätigten Rahmens; fehlt diese Reichweite, klärt `core-milestone` gezielt nach',
    r'Die erste Indexauswahl begrenzt die bestätigte Gesamtdeckung nicht, und keine Etappe wird automatisch ausgewählt',
    r'Neue Ziele, Scopeänderungen, nicht gedeckte Folgeetappen und gesondert freigabepflichtige Aktionen benötigen eigene ausdrückliche Autorisierung; ein ausdrücklicher Nur-Planen-Auftrag erlaubt keine Umsetzung',
    r'Beachte die evidenzbasierten Reparatur- und Stopgrenzen des zuständigen Skills statt starrer Rundenzahlen',
)
HANDOFF_SOURCES = {
    '.apm/skills/core-shared/references/workflow-contract.md': (
        r'Für Neuanlage, ersten Etappenstart und ausdrücklich beauftragten Folge-Handoff gilt derselbe interne Übergang aus den exakten Originalartefakten',
        r'`core-milestone` übergibt die ausgewählte und freigegebene aktuelle Etappe direkt an `core-plan`, ohne separate Goal-/Reinject-Prompt-Ausgabe oder zusätzliche Startformel',
        r'Nach Qualitäts-pass und belegter Deckung, vollständiger tatsächlicher Anzeige, `Confirmed` derselben Datei und korrekter Indexbindung übergibt `core-plan` intern in frischem Kontext an `core-execute`, ohne neue Nutzerantwort abzuwarten',
        r'Ein ausdrücklicher Nur-Planen-Auftrag verhindert Umsetzung auch bei historischer Gesamtdeckung',
        r'Nach verifiziertem Etappenabschluss ist `core-handoff` mit exakten Originalartefakten und kopierbarem Startprompt im Chat verpflichtend; danach halte an, ohne unmittelbar die nächste Etappe zu planen oder zu starten und ohne Auswahl oder Freigabe zu wechseln',
        r'Ist das Gesamtziel belegt erfüllt, liefert `core-handoff` stattdessen den belegten Gesamtabschluss ohne erfundene Folgearbeit',
        r'Das interne Run-Handoff bleibt für Review und Resume bei `core-execute` und wird durch den Sitzungsstartprompt nicht ersetzt',
        r'Ausdrückliche Einschränkungen, fehlende Deckung, Konflikte, Abbruch, Resume-Grenzen und ungedeckte Wirkungen bleiben unverändert bindend',
        r'Die Gesamtfreigabe wählt umgekehrt keine weitere Etappe automatisch aus und ersetzt nicht die bestehende Auswahl- und Planungsaktivierung',
        r'Nur wenn die aktuelle Nutzeranweisung[^.]*Handoff ausdrücklich als Arbeitsauftrag[^.]*Originalprüfung genau eine[^.]*bereits ausgewählte und bestätigte Definitionsversion mit belegten Abhängigkeiten ausschließlich zur Planung aktivieren',
        r'current_approval: handoff-planning[^.]*unverändertem \x60selected\x60, \x60selection_approval\x60 und Definition[^.]*kein Ausführungsrecht',
        r'Ein Handoff als Zitat oder Kontext aktiviert nichts',
        r'keine persönliche Einzelgenehmigung[^.]*kein Ersatz für Auswahl/Bestätigung der Definition[^.]*keine Ausführungsfreigabe',
        r'Fehlende/widersprüchliche Pfade[^.]*Abhängigkeiten, Abbruch, aktive wiederaufnehmbare Plan-/Runarbeit oder konkurrierende Indexänderung stoppen die Neuplanung; Resume bleibt Resume',
        r'Nach `Confirmed` aktualisiert ausschließlich `core-milestone` nach erneuter Original- und Indexprüfung dieselbe aktuelle ID-Version: bei belegter Gesamtdeckung von `handoff-planning` auf `current_approval: goal-covered`, sonst nach ausdrücklicher Nutzerfreigabe auf `current_approval: user-confirmed`',
        r'auch wenn die Deckung belegt ist',
        r'Ist die Deckung im Plantext belegt, setzt `core-plan` dieselbe Datei auf `Confirmed`',
        r'Fehlt die Deckung oder bleibt eine wesentliche Entscheidung offen, bleibt die Datei `Draft`, nicht ausführbar und nicht in `plan_paths`, bis der Nutzer konkret entscheidet',
        r'Review-pass, Anzeige, Schweigen, alte Ausführungsfreigabe und abgeleitete Planungsbefugnis allein sind keine Bestätigung',
        r'Aktuelle ausdrückliche Direktaufträge und gedeckte technische Ersatzplanung folgen ihren eigenen Regeln',
        r'Ein besonderer Freigabesatz pro Ziel oder Handoff ist nicht nötig',
        r'Eine bloße Schreib- oder Inhaltsbestätigung ohne vorgelegten Rahmen deckt keine Ausführung',
        r'vor der Bestätigungsfrage[^.]*Ziel, Etappen, Nichtziele sowie Wirkungs-, Risiko- und Kostengrenzen[^.]*sichtbar vor[^.]*bestätigt der Nutzer genau diesen vorgelegten Rahmen',
        r'im sichtbaren Freigabebeleg genannte Liste exakter ID-Versionen[^.]*erste beziehungsweise aktuelle Indexauswahl[^.]*verengt die Gesamtfreigabe nicht',
        r'Die Übergabe erhält dennoch den vollständigen ursprünglichen Freigaberahmen samt allen ausdrücklich gedeckten ID-Versionen und Ausschlüssen, nicht nur die erste oder aktuelle Indexauswahl',
        r'Nach Qualitäts-pass, belegter Deckung, vollständiger Anzeige, `Confirmed` und korrekter Indexbindung bleibt gedeckte Umsetzung ohne zusätzliches persönliches Einzelgate zulässig',
        r'Die Deckung endet bei neuen Zielen, Scopeänderungen, wesentlich offenen Entscheidungen, nicht gedeckten Sonderwirkungen[^.]*neuen oder wesentlich erhöhten ungedeckten Sicherheitsrisiken, neuen Definitionsversionen und Abbruch',
        r'Konkret vereinbarte Sicherheitsmaßnahmen brauchen keine erneute Routinefreigabe; unklare Deckung ist eine Nutzerentscheidung',
        r'Bei Etappenplänen mit Gesamtfreigabe gehören dazu `goal\.md` samt tatsächlicher Gesamtfreigabequelle, die exakt ausgewählte Definitionsdatei, der aktuelle Index, Abhängigkeitsnachweise und bei Handoff der exakte Handoff samt aktueller Fortsetzungsanweisung',
        r'nie aus Planstatus, Indexwert, Dateiname, Anzeige oder Review-pass',
        r'Der Reviewer erhält kein gewünschtes Urteil und erteilt keine Vollmacht',
    ),
    '.apm/skills/core-milestone/references/milestone-index-format.md': (
        r'`handoff-planning` ist nur zulässig, wenn der aktuelle Nutzerauftrag[^.]*ausdrücklich als Arbeitsauftrag[^.]*Originalprüfung[^.]*bereits ausgewählte und bestätigte ID-Version samt Abhängigkeiten',
        r'Nach ausdrücklicher Freigabe des vollständigen Erstplans bei fehlender Deckung darf ausschließlich `core-milestone` bei derselben aktuellen ID-Version[^.]*user-confirmed[^.]*Confirmed-Plan in `plan_paths`[^.]*selected[^.]*selection_approval[^.]*Definition bleiben unverändert',
        r'Nur `core-milestone` setzt ihn, ausschließlich als Ersatz für `handoff-planning`, und nur bei verknüpftem Confirmed-Plan in `plan_paths`',
        r'ist `goal-covered` ungültig; er beweist keine Freigabe allein',
        r'Eine echte `user-confirmed`-Aktivierung wird nie in `goal-covered` umgeschrieben',
        r'plan_paths\x60 enthält ausschließlich bestätigte Pläne für genau diese Definitionsversion',
        r'Ein Zähler allein erkennt keine fremden Änderungen[^.]*Inhalt[^.]*bedingte atomare Schreiboperation',
    ),
    '.apm/skills/core-plan/SKILL.md': (
        r'Ausschließlich beim Erstplan einer Etappe mit Gesamtfreigabe \(auch der ersten Etappe\) und beim Handoff-Erstplan[^.]*nach vollständiger statischer Validierung als `status: Draft` am vorgesehenen Planpfad',
        r'Bei gedeckter Etappenarbeit übergib nach vollständiger Anzeige, `Confirmed` und korrekter Indexbindung intern ohne neue Nutzerantwort an `core-execute`',
        r'Ist die Deckung belegt, setzt `core-plan` dieselbe Datei auf `Confirmed`; fehlt sie, wartet `core-plan` auf die ausdrückliche neue Nutzerfreigabe',
        r'Danach prüft \x60core-review\x60 genau diese Datei unabhängig und schreibt keine Datei',
        r'Draft ist nicht ausführbar und wird nicht in \x60plan_paths\x60 geführt\. Keine Entwurfsduplikate',
        r'Für Erstpläne einer Etappe mit Gesamtfreigabe oder aus einem Handoff gilt der \[Erstplan-Ablauf des Workflowvertrags\]',
        r'Alte Etappenausführungsfreigabe, abgeleitete Planungsbefugnis, Review-pass, Anzeige oder Schweigen allein geben den Plan nicht frei',
        r'Technische Ersatzpläne und reguläre Pläne ohne Etappenbindung bleiben von dieser Sonderregel unberührt',
    ),
    '.apm/skills/core-review/SKILL.md': (
        r'Beim Erstplan einer Etappe mit Gesamtfreigabe oder aus einem Handoff prüfe den statisch validierten Draft unabhängig und getrennt nach Qualität und Deckung',
        r'Indexbindung durch `core-milestone` und Übergabe an Execute ohne neue Nutzerantwort gemäß Workflowvertrag',
        r'`core-plan` setzt die Datei nur bei belegter Deckung auf `Confirmed`, sonst wartet es auf die ausdrückliche neue Nutzerfreigabe',
        r'Leite Deckung nie aus Planstatus, Indexwert, Dateiname, Anzeige oder Review-pass ab',
        r'Fehlt eine Gesamtfreigabe, lautet das Deckungsurteil `nicht gedeckt`',
        r'Diese Sonderregel gilt nicht für technische Ersatzpläne',
    ),
    '.apm/skills/core-milestone/SKILL.md': (
        r'Der Rahmen deckt genau die im Freigabebeleg benannten Etappen-IDs und Versionen',
        r'Übergib die ausgewählte und freigegebene aktuelle Etappe intern an `core-plan`, bei Neuanlage ebenso wie beim ersten Start oder originalgeprüften Handoff-Auftrag',
        r'Erhalte den vollständigen ursprünglichen Freigaberahmen samt allen gedeckten ID-Versionen und Ausschlüssen getrennt von der aktuellen Auswahl',
        r'Nach verifiziertem Etappenabschluss rufe verpflichtend `core-handoff` mit exakten Originalartefakten auf und gib dessen kopierbaren Startprompt im Chat aus',
        r'Danach halte an: keine unmittelbare Folgeplanung, kein Folgestart und kein Auswahl- oder Freigabewechsel',
        r'eine solche Planungserlaubnis ist keine Ausführungsfreigabe',
        r'current_approval: handoff-planning[^.]*ausschließlich zur Planung aktivieren[^.]*keine persönliche Einzelgenehmigung und kein Ausführungsrecht',
        r'Nach `Confirmed` aktualisiert ausschließlich `core-milestone` nach erneuter Original- und Indexprüfung dieselbe ID-Version: bei belegter Gesamtdeckung von `handoff-planning` auf `goal-covered`, sonst nach ausdrücklicher Nutzerfreigabe auf `user-confirmed`',
        r'Für Erstpläne einer Etappe mit Gesamtfreigabe oder aus einem Handoff gilt der \[Erstplan-Ablauf des Workflowvertrags\]',
        r'Bei der ersten Etappe einer Gesamtfreigabe aktiviert `core-milestone` die ausgewählte ID-Version zunächst mit `current_approval: user-confirmed`',
        r'Eine echte `user-confirmed`-Aktivierung bleibt unverändert',
        r'lege vor der Bestätigungsfrage Ziel, Etappen, Nichtziele und den konkret gedeckten Wirkungs-, Risiko- und Kostenrahmen sichtbar vor',
        r'Vor dem Schreiben kläre bei unklarer Reichweite gezielt, welche Etappen-ID-Versionen zur Umsetzung mitbestätigt werden',
        r'„Mit M01 beginnen“ allein bedeutet weder „nur M01 freigegeben“ noch Gesamtdeckung; eine bloße Inhaltsbestätigung ist keine Gesamtfreigabe',
        r'Die erste Auswahl im Index bezeichnet nur die aktuelle Etappe und verengt diesen bestätigten Gesamtrahmen nicht; sie wählt jedoch keine weitere Etappe aus und ersetzt nicht deren bestehende Auswahl- und Planungsaktivierung',
        r'Für eine gedeckte, ordnungsgemäß ausgewählte Etappe ist nach bestätigtem Plan und dessen korrekter Indexbindung keine zusätzliche persönliche Einzelbestätigung zur Umsetzung erforderlich',
        r'Ziel- und Definitionsbestätigung mit vorgelegtem und mitbestätigtem begrenztem Ausführungsrahmen \(Gesamtfreigabe\) erlauben Planung und Umsetzung der bestätigten Etappe',
    ),
    '.apm/skills/core-handoff/SKILL.md': (
        r'Dieser zeigt Gesamtziel, Etappenübersicht und aktuelle ID und übergibt aus den Originalartefakten intern an den zuständigen Workflow',
        r'Nach Qualitäts-/Deckungsreview, vollständiger Anzeige, `Confirmed` und Indexbindung setzt gedeckte Arbeit intern ohne neue Nutzerantwort zu Execute fort',
        r'Nach verifiziertem Etappenabschluss ist dagegen dieser Handoff verpflichtend, gefolgt von Halt ohne unmittelbare Folgeplanung oder Folgestart',
        r'Handoff und Startprompt referenzieren den vollständigen ursprünglichen Rahmen \(Freigabequelle in `goal\.md` samt gedeckten Etappen-IDs/Versionen und Ausschlüssen, Definition, Index\)',
        r'die Auswahl verengt den bestätigten Rahmen nicht, und der Rahmen wählt keine weitere Etappe automatisch aus',
        r'Bei gedeckter, ordnungsgemäß ausgewählter Arbeit führt ein bestätigter Plan nach Qualitäts- und Deckungsprüfung, vollständiger Anzeige und korrekter Indexbindung ohne zusätzliche persönliche Einzelbestätigung zur Umsetzung; ausdrückliche Einschränkungen und ungedeckte Wirkungen bleiben Stopgrenzen',
    ),
    '.apm/skills/core-handoff/assets/start-prompt.md': (
        r'Mit Milestones übergibt core-milestone die ausgewählte und freigegebene ID-Version aus exakten Ziel-, Index- und Definitionspfaden intern an core-plan, ohne separate Goal-/Reinject-Prompt-Ausgabe',
        r'Bei belegter Deckung folgen Confirmed derselben Datei, erneute Original-/Indexprüfung und korrekte Indexbindung durch core-milestone; danach intern zu Execute ohne neue Nutzerantwort',
        r'Nach verifiziertem Etappenabschluss sind core-handoff und Halt verpflichtend: keine unmittelbare Folgeplanung oder Folgestart',
        r'Geltungsbereich der Freigabe: <vollständiger bestätigter Rahmen, alle gedeckten Etappen-IDs/Versionen und Ausschlüsse; getrennt von der ersten/aktuellen Indexauswahl>',
        r'Die erste beziehungsweise aktuelle Indexauswahl verengt den bestätigten Gesamtrahmen nicht; sie wählt auch keine weitere Etappe automatisch aus',
        r'Für gedeckte, ordnungsgemäß ausgewählte Umsetzung ist nach Qualitäts- und Deckungsprüfung, vollständiger Anzeige, `Confirmed` und korrekter Indexbindung keine zusätzliche persönliche Einzelbestätigung erforderlich',
        r'Explizite Einschränkungen, fehlende Deckung, Konflikte, Abbruch, Resume-Grenzen und ungedeckte Wirkungen bleiben bindend',
        r'Handoff aktiviert Planung nur, wenn die aktuelle Nutzeranweisung ihn ausdrücklich als Arbeitsauftrag übergibt[^.]*Originalprüfung[^.]*bereits ausgewählte und bestätigte Definitionsversion samt belegten Abhängigkeiten',
        r'abgeleitete Planungsbefugnis anhand exakter Originalpfade, nicht als persönliche Einzelgenehmigung',
        r'vollständige Erstplan[^.]*unabhängigem Review tatsächlich sichtbar gezeigt; er bleibt Draft, nicht in `plan_paths` und nicht ausführbar, bis belegte Gesamtdeckung oder eine neue ausdrückliche Nutzerfreigabe ihn bestätigt',
        r'Freigabequelle: <exakter Abschnitt in goal\.md mit der Gesamtfreigabe',
        r'Bei Abbruch, Resume, Konkurrenz-, Abhängigkeits-, Versions- oder Auswahlfehler stoppe',
    ),
    '.apm/skills/core-shared/references/artifact-contract.md': (
        r'Nur der Erstplan einer Etappe mit Gesamtfreigabe oder aus einem Handoff darf nach statischer Validierung vor dem unabhängigen Planreview als Draft am einen vorgesehenen Pfad geschrieben werden',
        r'Draft ist nicht ausführbar, kein bestätigter Plan und nicht in \x60plan_paths\x60',
        r'Nach Review, vollständiger tatsächlicher Anzeige und belegter Deckung oder neuer ausdrücklicher Nutzerfreigabe wird dieselbe Datei Confirmed',
        r'`Confirmed` bedeutet ausführbar nur mit belegter Freigabequelle \(persönliche Einzelbestätigung oder Gesamtdeckung\); der Statuswert allein beweist keine Freigabe',
        r'Technische Ersatzplanung und reguläre Pläne ohne Etappenbindung bleiben unberührt',
        r'historische Inhalts- oder Schreibbestätigungen erzeugen keine rückwirkende Gesamtvollmacht',
        r'eine Massenmigration oder Freigabefiktion findet nicht statt',
    ),
    '.apm/skills/core-shared/references/tool-routing.md': (
        r'zuerst eine tatsächlich verfügbare native Plan-/Dateianzeige des aktuellen Harnesses \(OpenChamber ist nur ein Beispiel\)',
        r'Fehlt diese Fähigkeit, öffne den exakten lokalen Markdownpfad mit der OS-Standardanwendung',
        r'Bei Headless-Betrieb oder fehlgeschlagener Anzeige nenne die Einschränkung[^.]*vollständigen Planinhalt im Chat[^.]*ein Pfad oder eine Zusammenfassung genügt nicht',
        r'Behaupte weder Öffnung noch Lesen oder Freigabe ohne Nachweis',
        r'als geprüfter Erstplan einer gedeckten Etappe sichtbar werden muss',
        r'Anzeige ist keine Lesebestätigung oder Autorisierung\. Auch ein gedeckter Plan wird angezeigt, ohne eine erneute Antwort zu verlangen; auf eine Antwort wartet er nur, wenn die Deckung fehlt\. Keine Viewermechanik, Providerinstallation oder neue Abhängigkeit',
    ),
    '.apm/skills/core-init-project/assets/core-routing.md': (
        r'Bei Neuanlage, erstem Start und beauftragtem Folge-Handoff erfolgt die Übergabe intern aus Originalartefakten an `core-plan`; nach Qualitäts-/Deckungsreview, vollständiger Anzeige, Confirmed und korrekter Indexbindung geht gedeckte Arbeit ohne neue Nutzerantwort intern zu `core-execute`, ohne separate Goal-/Reinject-Prompt-Ausgabe',
        *AUTHORIZED_WORK_CLAUSES,
        r'ausdrücklich als Arbeitsauftrag übergebener Handoff aktiviert nach Originalprüfung nur die Planung genau einer[^.]*bereits ausgewählten und bestätigten Etappendefinition mit belegten Abhängigkeiten',
        r'Der unabhängig geprüfte Erstplan wird vollständig tatsächlich sichtbar gezeigt; er bleibt Draft und nicht ausführbar, bis belegte Gesamtdeckung oder eine neue ausdrückliche Planfreigabe ihn bestätigt',
    ),
    'AGENTS.md': (
        r'Bei Neuanlage, erstem Start und beauftragtem Folge-Handoff erfolgt die Übergabe intern aus Originalartefakten an `core-plan`; nach Qualitäts-/Deckungsreview, vollständiger Anzeige, Confirmed und korrekter Indexbindung geht gedeckte Arbeit ohne neue Nutzerantwort intern zu `core-execute`, ohne separate Goal-/Reinject-Prompt-Ausgabe',
        *AUTHORIZED_WORK_CLAUSES,
        r'abgeleitete Planungsbefugnis, nicht als persönliche Einzelgenehmigung',
        r'Planungsbefugnis bestätigt keinen Erstplan',
        r'er bleibt Draft und nicht ausführbar, bis belegte Gesamtdeckung oder eine neue ausdrückliche Planfreigabe ihn bestätigt',
    ),
    '.apm/skills/core-milestone/references/goal-format.md': (
        r'Hat der Nutzer den vorgelegten begrenzten Ausführungsrahmen mitbestätigt, nennt ein Abschnitt in der Markdown-Prosa dieser Datei die Autorisierungsquelle',
        r'Diese Liste bestimmt den Umfang der Gesamtfreigabe; die erste Auswahl im Index bezeichnet nur die aktuelle Etappe und verengt sie nicht',
        r'Umgekehrt wählt die Gesamtfreigabe keine weitere Etappe automatisch aus',
        r'zusätzliche YAML-Pflichtfelder entstehen nicht',
    ),
    '.apm/skills/core-milestone/references/milestone-format.md': (
        r'eine Gesamtfreigabe für v1 deckt keine spätere Version stillschweigend',
    ),
    '.apm/skills/core-execute/SKILL.md': (
        r'Nach erfolgreicher eigener Eingangsprüfung führe die intern übergebene gedeckte Etappe ohne neue Nutzerantwort aus',
        r'Bei gepinnter Etappe folgt nach verifiziertem Etappenabschluss verpflichtend `core-handoff` und anschließend Halt',
        r'Bei einem Etappenplan mit Gesamtfreigabe oder Handoff prüft `core-execute` selbst die Eingangsbedingungen',
        r'eine historische Gesamtfreigabe ist dann nicht nötig',
        r'`Confirmed`, ein Indexwert oder bloße Auswahl allein genügen nicht',
        r'`core-execute` repariert die Indexbindung nicht selbst',
    ),
}
HANDOFF_WIDENING = r'Mit M01 beginnen bedeutet Gesamtfreigabe|Die Gesamtfreigabe wählt weitere Etappen automatisch aus|Ausdrückliches Nur-Planen erlaubt Umsetzung|Handoff erlaubt sofortige Ausführung|Draft ist ausführbar|handoff-planning ersetzt selection_approval|Anzeige gilt als Nutzerfreigabe|Ein Dateipfad genügt als vollständige Anzeige|Handoff-Sperre gilt auch für technische Ersatzpläne|goal-covered ersetzt user-confirmed|goal-covered ersetzt selection_approval|Qualitäts-pass genügt als Deckung|Der Indexwert beweist die Ausführungsdeckung|Eine Schreibfreigabe gilt rückwirkend als Gesamtfreigabe|Die Gesamtfreigabe deckt jede spätere Definitionsversion|Die gedeckte Etappe startet automatisch die nächste Etappe|Für Erstpläne (?:im Etappenmodus )?gilt der \[Erstplan-Ablauf'
# The old mandatory single-plan halt is replaced by coverage criteria, not merely deleted.
HANDOFF_LEGACY = r'Mit M01 beginnen bedeutet nur M01 freigegeben|Die erste Indexauswahl begrenzt die Gesamtfreigabe|Handoffs geben nur die aktuelle Etappenfreigabe weiter|Gedeckte Umsetzung braucht eine zusätzliche persönliche Einzelbestätigung|Erst eine neue ausdrückliche Nutzerfreigabe macht dieselbe Datei \x60Confirmed\x60|bleibt bis zur ausdrücklichen neuen (?:Nutzer)?[Ff]reigabe Draft|auf die ausdrückliche neue Nutzerfreigabe warten, bevor dieselbe Datei Confirmed wird|(?<!nicht gedeckte )Folgeetappen und gesondert freigabepflichtige Aktionen benötigen'


def check_handoff_sources(sources):
    for path, patterns in HANDOFF_SOURCES.items():
        text = sources[path]
        require(not re.search(r'assets/goal-prompt\.md|(?:fülle|gib|verlange)[^.!\n]*(?:den|einen) Goal-Prompt|Gedeckte Arbeit wartet auf eine neue Nutzerantwort|Nach Etappenabschluss plane unmittelbar die nächste Etappe|Nach Etappenabschluss ist Handoff optional', text, re.I), 'direkter Etappenübergang verletzt: ' + path)
        require(not re.search(HANDOFF_WIDENING, text), 'Handoff-Ausweitung: ' + path)
        require(not re.search(HANDOFF_LEGACY, text), 'Handoff-Einzelplanhalt ohne Deckungskriterien: ' + path)
        for pattern in patterns:
            require(re.search(pattern, text), 'Handoff-Klausel fehlt: ' + path + ': ' + pattern)


# Execute direct mode, task-bound support and task-bound approval precedence (static source clauses only).
DIRECT_SOURCES = {
    '.apm/skills/core-execute/references/direct-mode.md': (
        r'erfindet keinen Plan, `Confirmed`-Status, Taskgraphen oder `plan/v1`',
        r'Aktive Planbindung, gepinnte Etappe/Milestone-Arbeit, fehlende/verlorene Planartefakte[^.]*niemals als Direktauftrag umgedeutet',
        r'vor jeder Produktmutation in `\.agentic-workflow/runs/<run-id>/request\.md`[^.]*genau einen verantwortlichen registrierten Fachagenten',
        r'`mode: direct` und `request_path`, nicht `plan_path`',
        r'Execute bleibt einziger Dispatcher und Integrator',
        r'Unterstützer delegieren nicht weiter',
        r'Fehlender oder driftender Eingang blockiert Resume und Review',
        r'Ein fehlender Pfad wird nicht geraten',
        r'Direktmodus hat keine Etappenbindung; gebundene Etappenarbeit bleibt im Planmodus',
        r'ausschließlich Execute integriert Ergebnisse',
        r'Auftrag, eingesetzter Agent, Elterntask, abgegrenzter Teilscope, Ergebnis und Checks werden dem bestehenden Taskversuch',
        r'stoppe betroffene Produktmutationen und route zu `core-plan`',
    ),
    '.apm/skills/core-execute/SKILL.md': (
        r'Plan- und Direktmodus sind exklusiv',
        r'fehlende/verlorene Planartefakte werden nicht in Direktmodus umgedeutet',
        r'Ein aktiver gebundener Plan, eine gepinnte Etappe oder Milestone-Arbeit bleibt im Planweg',
        r'Legacy-Zustände mit `plan_path` ohne `mode` bleiben Planmodus',
        r'erforderliche Vorschau, Verifikation, Scope-/Drift-/Markerprüfung und Schutz fremder Inhalte bleiben bestehen',
        r'Execute allein formuliert und dispatcht zusätzliche, eng begrenzte Unterstützungsaufträge; der ursprüngliche Taskowner bleibt für Ergebnis und Belege verantwortlich, während ausschließlich `core-execute` Ergebnisse integriert',
        r'Halte Auftrag, eingesetzten Agenten, Elterntask, abgegrenzten Teilscope, Ergebnis und Checks dem bestehenden Taskversuch zugeordnet',
        r'S00-Referenz\]\([^)]*\) im selben Dispatchauftrag',
    ),
    '.apm/skills/core-review/SKILL.md': (
        r'im Direktmodus `request_path` mit `request\.md` statt eines Planartefakts',
        r'fehlende Pfade blockieren, sie werden nicht geraten',
        r'Legacy-Zustand ohne `mode`, aber mit `plan_path`, behandle den Lauf wie im Planmodus',
    ),
    '.apm/skills/core-shared/references/workflow-contract.md': (
        r'ein fehlender/verlorener Plan, aktive Plan-/Milestone-Arbeit oder ein mehrdeutiger Eingang wird nie als Direktauftrag umgedeutet',
        r'Vorrang vor separaten Bestätigungs- oder Diff-Gates niedriger priorisierter Skills und AGENTS\.md',
        r'read-only Vorschau, Scope-/Drift-/Markerprüfung und Schutz fremder Inhalte bleiben bestehen',
        r'erzeugt weder neue Ziele noch ungedeckte Kosten, Sonderwirkungen oder höherrangige Erlaubnis',
        r'Fachagenten delegieren nicht weiter',
        r'Die bloße Aussage, eine Freigabe sei nicht nötig oder es solle nicht erneut gefragt werden, autorisiert ohne ausdrücklichen Änderungsauftrag keine Ausführung',
        r'Unterstützung außerhalb des Taskziels/-scopes[^.]*geht an `core-plan`',
    ),
    '.apm/skills/core-shared/references/artifact-contract.md': (
        r'Planruns referenzieren `plan_path`; Direktläufe referenzieren `request_path` und kein `plan_path`',
        r'Bestehende Runs mit `plan_path` bleiben als Planmodus lesbar',
        r'`task-result/v1` und `review/v1` bleiben unverändert',
    ),
    '.apm/skills/core-shared/assets/handoff.md': (
        r'Fülle exakt einen Eingangspfad entsprechend dem Ausführungsmodus',
    ),
    '.apm/skills/core-shared/references/user-instructions-contract.md': (
        r'Sie ersetzt nicht die read-only Vorschau, genaue Scope-/Drift-/Markerprüfung oder den Schutz fremder Inhalte',
    ),
}
# Reintroduced widening: lost plans continued directly, nested support, automatic scope release, replaced safety checks.
DIRECT_WIDENING = r'(?:fehlende|verlorene)[^.\n]*Plan\w*[^.\n]*(?:im|als|in den) Direkt\w* (?:fort\w*setz|aus\w*führ|behandel|um\w*deut)\w*|Unterstützer (?:dürfen|darf) weiter delegieren|automatische Scopefreigabe gilt|ersetzt (?:die )?(?:Vorschau|Drift-|Markerprüfung)'

def check_direct_sources(sources):
    for path, patterns in DIRECT_SOURCES.items():
        text = sources[path]
        # Negated sentences ("niemals als Direktauftrag umgedeutet") are the contract itself, not a widening.
        widened = [s for s in re.split(r'(?<=[.!?])\s+|\n', text) if re.search(DIRECT_WIDENING, s, re.I) and not re.search(r'\b(?:nicht|niemals|nie|kein\w*)\b', s, re.I)]
        # A bare "no approval needed" sentence must keep its change-order condition despite containing "nicht".
        widened += [s for s in re.split(r'(?<=[.!?])\s+|\n', text) if re.search(r'Freigabe sei nicht nötig|nicht erneut gefragt', s) and re.search(r'autorisier|erlaub|genügt', s) and 'ohne ausdrücklichen Änderungsauftrag keine Ausführung' not in s]
        require(not widened, 'Direktmodus-Ausweitung: ' + path)
        for pattern in patterns:
            require(re.search(pattern, text), 'Direktmodus-Klausel fehlt: ' + path + ': ' + pattern)


def check_replacement_sources(sources):
    # Reject old unconditional gates even when a positive frame paragraph survives.
    legacy = r'Erst nach ausdrücklicher Bestätigung wird der Ersatzplan geschrieben|Die bisherige Planfreigabe bestätigt keinen unbekannten Ersatzplan|bereits genau diesen Plan autorisiert|ohne Nutzerbestätigung wird nichts ausgeführt|die Bestätigung des Ersatzplans bleibt erforderlich|die Planbestätigung bleibt erforderlich|Ziel-/Definitionsbestätigung und aktuelle Etappenfreigabe sind weder Planbestätigung noch Ausführungsfreigabe|Der Nutzer aktiviert ihn erst nach Bestätigung des eigenen Plans|Ausführung beginnt erst nach Planbestätigung und ausdrücklicher Execute-Autorisierung|Execute beginnt erst nach bestätigtem Plan und ausdrücklicher Ausführungsautorisierung|erst nach deren Bestätigung verknüpft|Nutze anschließend denselben Validierungs-, Planreview- und Bestätigungsschritt wie bei Erstplanung|core-plan → core-execute \(erst nach Nutzerbestätigung\)|erst deine ausdrückliche Bestätigung erlaubt die Umsetzung|Planreview vor deiner Bestätigung|Planreview vor Nutzerbestätigung|Planreview; Textantwort vor Bestätigung|Nach vollständigem Entwurf und vor Nutzerbestätigung|unabhängiges Planreview vor Bestätigung|Entwurf vor deiner Bestätigung|→ Nutzerbestätigung → core-execute|→ deine Freigabe → core-execute|(?:Planreview|Planentwurf) vor (?:der |deiner )?(?:Nutzer)?Bestätigung|Prüfe vor der Bestätigung:'
    for path, patterns in REPLACEMENT_SOURCES.items():
        text = sources[path]
        require(not re.search(legacy, text, re.I), 'RV05 widersprechendes Bestätigungsgate: ' + path)
        for pattern in patterns:
            require(re.search(pattern, text, re.I), 'RV05 Ersatzplan-Ablaufklausel fehlt: ' + path + ': ' + pattern)


# Source-local goal-source and task-boundary clauses; static consistency only.
GOAL_SOURCES = {
    '.apm/skills/core-shared/references/workflow-contract.md': (
        r'sichtet die Planung einmal begrenzt die Metadaten vorhandener Zielindizes, ohne rekursive Historienlektüre',
        r'YAML einschließlich gültiger JSON-Schreibweise wird mit dem vorhandenen Parser strukturiert ausgewertet',
        r'Lese- oder Parsefehler belegen keine Abwesenheit',
        r'Die Sichtung ist keine Auswahlvollmacht[^.]*eindeutig passende aktuelle, ausgewählte und bestätigte Etappe[^.]*Originale gebunden',
        r'Mehrere passende, widersprüchliche oder unbestätigte Kandidaten werden gezielt geklärt',
        r'Ohne passende Etappe genügt der Originalauftrag[^.]*nicht auf Vorrat',
        r'Der Wegfalltest fragt',
        r'Ein notwendiger atomarer Vorgang bleibt zusammen; zerlegt wird nicht pro Toolaufruf',
        r'Zerlegung vor der Bestätigung',
        r'ein bloßes Größenurteil genügt nicht',
        r'zuerst Weglassen oder eine kleinere Alternative[^.]*dann eine vorhandene Projektfunktion oder native API/CLI/MCP; dann ein etabliertes geeignetes Werkzeug',
        r'Eigenentwicklung braucht eine belegte Lücke[^.]*kleiner Eigenbau ist legitim',
        r'Triviale Details brauchen keine Marktstudie',
        r'vorgeschlagenes Werkzeug ist keine Installationsfreigabe',
        r'Sicherheitsanforderung wird von ihrer bisher gewählten Umsetzung getrennt',
        r'vor einer kompensierenden Reparatur wird geprüft',
        r'Bei jedem Taskresultat einschließlich `partial`, `blocked` und `failed` sowie bei Resume',
        r'fachliche Beitrag oder tragende Erkenntnisgewinn[^?]*\?[^?]*kumuliert hinzu\?[^?]*kleinste sinnvolle Weg\?',
        r'grüne Helpertests allein rechtfertigen keine weitere Helperarbeit',
        r'bevor ein weiterer wesentlicher Helper entsteht oder ein selbst erzeugter Prüfblocker repariert wird',
        r'keinen neuen Status, kein neues Feld, keinen Pflichtmodellaufruf und kein Review pro Task',
        r'Private, temporäre und extern ausgeführte Helper sind nach Zweck und Wirkung Implementierung',
        r'read-only Task \(`scope: \[\]`\) wird weder durch solche Helper noch durch Eigenbau des Coordinators umgangen',
        r'prüft dieses Review zuerst den Gesamtweg gegen den Originalauftrag, nicht nur das zuletzt fehlerhafte Skript',
        r'begründet fortsetzen, innerhalb bestehender Rechte vereinfachen, bei materieller Planänderung Ersatzplanung oder bei ungedeckter Wirkung sicher stoppen',
        r'weder starre Retry- oder Zeitlimits noch eine Nutzerpause für jede operative Anpassung',
        r'Zuerst wird der Gesamtweg geprüft: Originalziel, Wegfalltest je Task, geerbte Voraussetzungen und Gates, realistisch lieferbare Taskgrößen[^;]*kleinerer Alternativweg; danach technische Details und Checkabdeckung',
        r'technisch korrekte Übernahme alter Gates genügt nicht',
        r'Anker sind die Originale, nicht ein gewünschtes Urteil oder ein Vorgänger-pass',
        r'Qualitätsurteil nennt konkret geprüfte problematische Entscheidungen oder offene Lücken',
        r'Zerlegung wird nur mit benannten Ergebnis- oder Schnittstellengrenzen verlangt, legitime Schutzmaßnahmen, notwendige atomare Vorgänge und schlanke Aufträge werden akzeptiert',
        r'keine weitere Reviewebene und keine neue Pauschalcheckliste',
    ),
    '.apm/skills/core-review/SKILL.md': (
        r'Prüfe zuerst den Gesamtweg nach der \[Prüfreihenfolge\]\([^)]*#planreview\)',
        r'formal korrekte Übernahme alter Gates oder ein Vorgänger-pass genügt nicht',
        r'Verlange Zerlegung nur mit konkret benannten Ergebnis- oder Schnittstellengrenzen; akzeptiere legitime Schutzmaßnahmen, notwendige atomare Vorgänge und schlanke Aufträge',
        r'Prüfe danach die Task-Kriterium-Zuordnung',
        r'den geprüften problematischen Entscheidungen oder offenen Lücken',
    ),
    '.apm/skills/core-shared/references/artifact-contract.md': (
        r'tatsächlichen Änderungen im Repository, einschließlich dort angelegter Helper',
        r'exakten freigegebenen Pfaden und Existenz- oder Änderungsnachweis in der vorhandenen `acceptance\[\]\.evidence`, `checks\[\]\.evidence` und `limitations`',
        r'ohne Secretinhalte, ohne globale Dateisysteminventur und ohne neues Feld',
        r'Verwende Pfade und Metadaten statt Inhalte geheimnistragender Dateien',
        r'Falls Struktur nötig ist, redigiere sie lokal vor jeder Toolausgabe',
        r'Secretwerte gelangen weder in Toolargumente noch in Tooloutput, Evidenz oder Dispatch',
        r'nachträgliches Redigieren eines bereits ausgegebenen Inhalts genügt nicht',
    ),
    '.apm/skills/core-shared/references/verification.md': (
        r'Grüne Tests eines selbst erstellten Helpers belegen nur den Helper, nicht den fachlichen Fortschritt',
    ),
    '.apm/skills/core-execute/SKILL.md': (
        r'führe den kurzen \[Zielabgleich\]\([^)]*\) für den nächsten Schritt aus',
        r'bei jedem Status den kurzen \[Zielabgleich\]',
        r'private oder externe Helper sind gemäß \[Artefaktvertrag\]\([^)]*\) sichtbar und im Scope',
    ),
    '.apm/skills/core-shared/references/tool-routing.md': (
        r'installierbares Werkzeug bleibt eine begründete Option nach der \[Notwendigkeitsfolge\]',
        r'mit eigener Freigabegrenze',
    ),
    '.apm/skills/core-debug/SKILL.md': (
        r'prüfe vor einer kompensierenden Reparatur Weglassen oder die vorhandene einfachere Alternative',
        r'Rückbau außerhalb des Scopes oder eines Schutzgates meldest du als Entscheidung an `core-execute`',
    ),
    '.apm/skills/core-plan/SKILL.md': (
        r'Binde nur eine eindeutig passende aktuelle, ausgewählte und bestätigte Etappe nach Originalprüfung; wähle selbst keine Etappe aus',
        r'Ohne passende Etappe plane den Originalauftrag ohne Pflichtmilestone; bei Mehrdeutigkeit oder Lese-/Parsefehler kläre gezielt',
        r'Zerlege mehrere eigenständig abnehmbare Ergebnisse[^.]*vor der Bestätigung; halte einen notwendigen atomaren Vorgang zusammen',
        r'Wegfalltest',
    ),
}
GOAL_LEGACY = r'(?:wähle|nimm)[^.\n]*(?:höchste|neueste)[^.\n]*(?:Etappe|Meilenstein)|jeder Plan (?:benötigt|braucht) einen Meilenstein|Parsefehler[^.\n]*(?:gilt|gelten) als (?:kein|fehlend)|Eigenbau ist (?:stets |immer )?verboten|installiere[^.\n]*(?:automatisch|ohne Freigabe)|Schutzgate[^.\n]*(?:abschalten|deaktivieren), um|Zielabgleich[^.\n]*nur bei `completed`|nach (?:jedem|allen) (?:Task|Taskresultat)[^.\n]*(?:Pflichtreview|Pflichtmodellaufruf)|(?:höchstens|maximal) \d+ (?:Reparatur|Retry|Versuch)|Vorgänger-pass (?:genügt|reicht)(?! nicht)|(?:höchstens|maximal) \d+ Tasks pro Plan'


def check_goal_sources(sources):
    for path, patterns in GOAL_SOURCES.items():
        text = sources[path]
        require(not re.search(GOAL_LEGACY, text, re.I), 'Zielbindung: Auswahl-/Pflichtmilestone-Regress: ' + path)
        for pattern in patterns:
            require(re.search(pattern, text), 'Zielbindungsklausel fehlt: ' + path + ': ' + pattern)


# Source-local TypeSafe consumer contracts, not a harness or an authorization engine.
TYPESAFE_SOURCES = {
    '.apm/skills/core-plan/SKILL.md': (
        r'Bei jedem Core-Planreview versucht \x60core-plan\x60 regulär eine minimierte TypeSafe-Vorbewertung ohne Projektpilot-Auswahl',
        r'Fehlende Datenfreigabe, Fähigkeit oder technische Fehler lassen die Beobachtung offen; normales Review und Produktarbeit gehen weiter',
        r'puffert der Owner minimierte Vergleichsdaten nur bei erlaubter lokaler Config und stellt sie nur bei freigegebener konfigurierter Collection zu',
        r'keine privaten Text- oder Kostenvollmachten[^.]*garantiert keine zukünftige Agentenbefolgung',
        r'bindet zuerst die exakten Planbytes und vorab festgelegten Kriterien',
        r'Vor jedem Versand prüft der Owner Daten-, Kosten- und Requestfreigabe[^.]*fehlt eine davon, wird nicht gesendet',
        r'ohnehin bestehende unabhängige Planreviewrunde erhält ausschließlich Originalplan, Kriterien und nötige Quellen[^.]*externe Leseregel[^.]*Modellhinweise und fremde Sessions',
        r'Modellresultate gehören nicht in Prompt, Titel oder Handoff',
        r'nach der unveränderten Erstantwort deren Originalbytes und Hash',
        r'Erst danach erhält derselbe Reviewer in derselben Session Modellresultat und Originale[^.]*Ersturteil bleibt unverändert',
        r'Geänderte Planbytes benötigen eine neue Bindung und Erstprüfung',
        r'Das Modul prüft Wertgleichheit, nicht Objektidentität über Prozesse',
        r'HTTPS ist nur bei vor möglichem Versand nachweislich fehlendem MCP/Endpoint eine bewusste Alternative',
        r'Fehlen Originale, Zustimmung oder die deklarierte \x60sessionID\x60-Fortsetzung[^.]*offen beziehungsweise nur hinsichtlich des Vergleichs blockiert; eine neue Session ist kein stiller Ersatz',
    ),
    '.apm/skills/core-review/SKILL.md': (
        r'Der Owner versucht regulär eine minimierte Vorbewertung ohne Projektpilot-Auswahl',
        r'Fehlende Datenfreigabe, Fähigkeit oder technische Fehler lassen die Beobachtung offen; normales Review und Produktarbeit gehen weiter',
        r'ohnehin bestehende unabhängige Erstreviewrunde vor Modelloffenlegung',
        r'derselbe Reviewer in derselben Session separat adjudizieren, ohne das fixierte Ersturteil zu ändern',
        r'Leseregel ist organisatorisch, keine technisch erzwungene Zugriffssperre[^.]*Kontaminationsverdacht[^.]*offen beziehungsweise ausgeschlossen',
        r'Ein Modellresultat ist kein Reviewurteil',
        r'soll der Owner die Modellbewertung vor dem unabhängigen Erstreview durchführen und verborgen speichern; der Reviewer erhält sie erst nach Fixierung des Ersturteils',
    ),
    '.apm/skills/core-execute/SKILL.md': (
        r'Profil \x60claim_support\x60 gezielt nutzen',
        r'\x60typesafe-mcp-arbitype\.evaluate\x60[^.]*bevorzugten optionalen Transport',
        r'Daten-/Kosten-/Requestfreigabe[^.]*ersetzt weder Pflichtchecks noch Status, Autorisierung oder Reviewurteil',
        r'Nutzung bleibt optional und löst keinen zusätzlichen Aufruf aus',
        r'Das Modul prüft Wertgleichheit, nicht Objektidentität über Prozesse',
    ),
    '.apm/skills/core-docs/SKILL.md': (
        r'bedingt \x60claim_support\x60',
        r'\x60typesafe-mcp-arbitype\.evaluate\x60[^.]*zuerst dessen aktuelles Schema',
        r'Quellenprüfung, Dokumentationsscope und Freigabe bleiben beim Curator; keine Rohpassagen ohne Daten-/Kosten-/Requestfreigabe',
    ),
    '.apm/skills/core-shared/references/tool-routing.md': (
        r'Bei jedem Core-Planreview versucht \x60core-plan\x60 regulär eine minimierte Vorbewertung ohne Projektpilot-Auswahl und ordnet \x60skill_relevance\x60, \x60requirement_coverage\x60 und \x60claim_support\x60',
        r'Der reguläre Versuch ist kein Setupzwang: Autorisierung, Daten-/Kostenfreigabe, Status und menschliche Entscheidungen bleiben unverändert',
        r'der bekannte Toolkatalog führt ihn nicht als Pflicht oder globale Setupanforderung',
        r'das Pythonmodul ist kein MCP-Client',
    ),
    '.apm/skills/core-shared/references/typesafe-contract.md': (
        r'bei jedem Core-Planreview für einen regulären minimierten TypeSafe-Beobachtungsversuch ohne Projektpilot-Auswahl',
        r'puffert minimierte Vergleichsdaten nur bei erlaubter lokaler Config und stellt sie nur bei freigegebener konfigurierter Collection zu',
        r'Fehlende Datenfreigabe, Fähigkeit oder technische Fehler lassen die Beobachtung offen; normales Review und Produktarbeit gehen weiter',
        r'identische ID bei anderer Nutzlast ist Konflikt, nicht Update',
        r'append-only Revisionen mit Vorgänger-ID und explizitem supersedes-Verweis; alte Ereignisse und Originalreferenzen bleiben erhalten',
        r'Fehlende oder unzugängliche Originalquellen bleiben unresolved',
        r'Es gibt keine bestätigten Schwellen und keine Modellhoheit über Freigabe, Dispatch oder Urteil',
        r'Vollständige Ereignishistorie, unveränderte Originalwerte und Dateikonflikte prüft der Owner',
        # Optional MCP route: discovery, exact payload, value binding, safe fallback, metadata limits.
        r'nach einer vorgängigen \x60search\x60-Discovery für den exakten Namespace und die Operation',
        r'übergibt exakt \x60state\x60, \x60questions\x60 und \x60model\x60 aus dem tatsächlich vorbereiteten Payload',
        r'ruft der Abschlussprozess \x60build_request\x60 mit den erhaltenen Originalinputs frisch auf[^.]*exakt',
        r'Das Modul prüft Wertgleichheit mit dem intern aus Originalinputs neu gebauten Request, nicht Objektidentität über Prozesse',
        r'HTTPS-Fallback ist nur zulässig, wenn MCP-Tool oder Endpoint nachweislich vor einem möglichen Bewertungsversand nicht verfügbar ist',
        r'kein automatischer Retry oder HTTP-Zweitversand',
        r'\x60health\(false\)\x60 ohne Modellaufruf ist kein Bewertungsnachweis',
        r'nicht beobachtete Werte bleiben unbekannt',
        r'Originalinputs, Profil-/Modellkennung, Fragenversion, Core-Version, Referenzen, Fingerprint und den tatsächlich übergebenen Payload unverändert',
        r'die unveränderte strukturierte Rohantwort über \x60finalize_response\(prepared, response, \*, core_version, duration_seconds\)\x60 der gemeinsamen strengen Prüfung',
        r'Ein sichtbarer MCP-Toolaufruf begrenzt nicht die Zahl interner Provideranfragen',
        r'Timeout-, Auth-, API-, Schema- und Antwortfehler offen',
    ),
    '.apm/skills/core-review/references/typesafe-evaluation.md': (
        r'Bei jedem Core-Planreview',
        r'Der Owner versucht regulär eine minimierte Vorbewertung ohne Projektpilot-Auswahl',
        r'Erst danach sieht derselbe Reviewer das Modellresultat',
        r'separates Ereignis[^.]*überschreibt das Ersturteil nicht',
        r'material_defect, no_material_defect, unresolved',
        r'beweisen keine technische Zugriffssperre',
        r'Die Modellbewertung soll der Owner vor der unabhängigen Reviewrunde durchführen und verborgen speichern; der Reviewer erhält das Ergebnis erst nach Fixierung des Ersturteils',
        r'Vorabzugriff, mitgegebene Modellhinweise oder begründeter Kontaminationsverdacht[^.]*offen beziehungsweise ausgeschlossen',
    ),
    '.apm/skills/core-typesafe/SKILL.md': (
        r'Bei jedem Core-Planreview versucht der Owner regulär eine minimierte Vorbewertung ohne Projektpilot-Auswahl',
        r'fehlende Datenfreigabe, Fähigkeit oder technische Fehler lassen die Beobachtung offen, normales Review und Produktarbeit gehen weiter',
        r'bind_plan\x60, \x60model_event\x60, \x60fix_review\x60, \x60comparison_event\x60, \x60append_event\x60',
        r'weder IO noch Modellaufrufe oder Workflowänderungen',
        r'Owner bewahrt Originale, vollständige Ereignishistorie und freie Zielpfade',
        r'Für den bevorzugten optionalen MCP-Weg braucht Core keinen lokalen Schlüssel',
        r'Rufe zuerst \x60search\x60 für den exakten Namespace \x60typesafe-mcp-arbitype\x60 und die Operation \x60evaluate\x60 auf, prüfe das zurückgegebene aktuelle Schema',
        r'leite nur \x60state\x60, \x60questions\x60 und \x60model\x60 aus \x60prepared\.payload\x60 weiter',
        r'ruft der Abschlussprozess \x60build_request\x60 mit diesen Originalinputs frisch auf[^.]*exakt',
        r'Das Modul validiert Wertgleichheit, nicht Objektidentität über Prozesse',
        r'HTTPS darf nur bewusst gewählt werden, wenn der MCP bzw\. sein Endpoint bereits vor einem möglichen Bewertungsversand nachweislich nicht verfügbar ist',
        r'keinen automatischen Retry und keinen HTTP-Zweitversand',
    ),
    '.apm/skills/core-typesafe/AGENTS.md': (
        r'Keine Datei-, Log- oder Statusschreibzugriffe',
        r'Aktionsschwellen fehlen bewusst',
    ),
    '.apm/skills/core-typesafe/assets/evaluation-directory-AGENTS.md': (
        r'Vor dem fixierten unabhängigen Erstreview darf der externe Reviewer[^.]*nicht lesen; der Owner darf sie diesem Reviewer nicht offenlegen',
        r'Erst danach erhält derselbe Reviewer in derselben Session Modellresultate und Originale',
        r'Originale und alle Ereignisrevisionen unverändert',
        r'freie Pfade[^.]*Dateikonflikte',
        r'keine Rohtexte, Secrets oder vollständigen Chats exportieren',
        r'organisatorische Leseregel erzwingt keine technische Zugriffssperre',
        r'fremde vorhandene lokale Dateien nicht überschreiben',
    ),
    '.apm/skills/core-shared/SKILL.md': (r'regulärer minimierter Beobachtungsversuch bei jedem Core-Planreview',),
    '.apm/skills/core-shared/AGENTS.md': (r'regulärer minimierter Beobachtungsversuch bei jedem Core-Planreview',),
    '.apm/skills/AGENTS.md': (r'TypeSafe-Vertrag gilt bei jedem Core-Planreview',),
    'scripts/AGENTS.md': (r'CORE_FILES[^.]*geschlossene transitive',),
    'tests/AGENTS.md': (r'synthetische Projektfixtures; sie setzen die echte \x60\.agentic-workflow/\x60-Kopie\s+weder voraus noch legen sie sie an',),
    'AGENTS.md': (
        r'TypeSafe-Evaluationsartefakte entstehen nur bei ausdrücklich beauftragter Evaluation und vorhandenem Artefaktschreibrecht',
        r'lokale gitignorierte Anleitung wird nicht vorausgesetzt',
    ),
}
TYPESAFE_WIDENING = (r'Modellresultate dürfen vor dem Ersturteil gelesen werden|Eine neue Session ersetzt die Erstprüfung|Wahrscheinlichkeiten entscheiden die Freigabe|Die Leseregel garantiert technische Isolation'
                     r'|Nach einem MCP-(?:Timeout|Fehler) folgt automatisch ein HTTP-(?:Zweitversand|Fallback)|API-Schlüssel wird als Toolargument übergeben'
                     r'|health\(false\) belegt Livekompatibilität'
                     r'|Fehlende TypeSafe-Beobachtung blockiert das normale Review'
                     r'|Regulärer Versuch erlaubt private Volltexte ohne Datenfreigabe'
                     r'|Collection wird ohne lokale Config zugestellt')
# Superseded over-narrow M03 wording: cross-process object identity, blanket ban on earlier model runs.
TYPESAFE_STALE = (r'PreparedRequest-Objekt muss über Prozesse identisch bleiben|Modellbewertung darf erst nach dem Ersturteil erzeugt werden'
                  r'|keine aktive Pflichtphase|keine aktive Phase|kein automatischer Aufruf'
                  r'|Planvergleich (?:bleibt optional|nur für Pilotprojekte)|Kein Pflichtaufruf:'
                  r'|Bei ausdrücklich beauftragter Plan-Evaluation')
TYPESAFE_MCP_TOOL = 'typesafe-mcp-arbitype'


def check_typesafe_sources(sources):
    # Same bounded pattern checks as other consumer contracts; no semantic labels inferred.
    for path, patterns in TYPESAFE_SOURCES.items():
        text = sources[path]
        require(not re.search(TYPESAFE_WIDENING, text), 'TypeSafe-Ausweitung: ' + path)
        require(not re.search(TYPESAFE_STALE, text), 'TypeSafe-Altregel: ' + path)
        for pattern in patterns:
            require(re.search(pattern, text), 'TypeSafe-Klausel fehlt: ' + path + ': ' + pattern)


def check_typesafe_catalog(catalog):
    # Exact optional provider vocabulary only; declaring it never makes the MCP required.
    require(TYPESAFE_MCP_TOOL in catalog.get('known_tool_ids', ()), 'TypeSafe-MCP fehlt im Toolkatalog: ' + TYPESAFE_MCP_TOOL)


DOCS_EXCLUSIVE = re.compile(r'\b(?:ausschließlich|nur|einzig)\b', re.I)
DOCS_ACTION = re.compile(r'\b(?:Ändere|Dokumentiere|dokumentiert|Bearbeite|bearbeitet|Korrigiere|korrigiert|ergänz\w*)\b', re.I)

def check_docs_source(text):
    # One work rule must not limit docs work exclusively to drift while another allows a proven new gap.
    for sentence in re.split(r'(?<=[.!?])\s+|\n', text):
        if re.search(r'Drift|veraltet', sentence) and DOCS_EXCLUSIVE.search(sentence) and DOCS_ACTION.search(sentence):
            require(re.search(r'Lücke', sentence, re.I), 'core-docs beschränkt Arbeit ausschließlich auf Drift: ' + sentence.strip()[:120])

def check_setup_source(front, text):
    description = front['description']
    require(re.search(r'(?:prüft|Prüfung|Prüfskill)[^.!]*read-only|read-only[^.!]*(?:prüft|Prüfung|Prüfskill)', description, re.I), 'core-init-mcps beschreibt Einrichtung statt read-only Prüfung')
    require(not re.search(r'(?mi)^\s*(?:\d+[.)]\s*)?(?:Materialisiere|Installiere|Provisioniere|Aktiviere)\s+(?!nicht\b|keine\b|keinen\b|kein\b)', text), 'core-init-mcps fordert eigene Installation/Materialisierung')
    require(not re.search(r'(?mi)^\s*(?:\d+[.)]\s*)?Lies[^\n]*apm\.lock', text), 'MCP-Prüfung fordert Lockfile')
    require(re.search(r'(?:keine|kein|nicht|ohne)[^.!\n]*(?:Secretzugriff|Secret.*such|Secrets.*such|Schlüsselbund)', text, re.I), 'MCP-Prüfung ohne belegte Secretzugriffsgrenze')


def check_group(root, group, with_authoring=False, tool_root=None):
    paths = targets(root, group)
    if group == 'workflows':
        paths = list(dict.fromkeys([*paths, *(root / p for p in (*REPLACEMENT_SOURCES, *DIRECT_SOURCES, *HANDOFF_SOURCES, *TYPESAFE_SOURCES, *GOAL_SOURCES))]))
    def action():
        # Missing inputs take precedence over content findings in earlier targets.
        for path in paths:
            require(path.is_file(), 'Phasenvoraussetzung fehlt: ' + str(path.relative_to(root)))
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
                if path.parent.name == 'core-docs' and path.name == 'SKILL.md':
                    check_docs_source(text)
                if path.parent.name == 'core-execute' and path.name == 'SKILL.md':
                    check_execute_attempts(text)
            elif path.suffix == '.yaml':
                value = load_yaml(text)
                if path.name == 'workflow-catalog.yaml':
                    validate_catalog(value)
                    check_typesafe_catalog(value)
                elif isinstance(value, dict) and 'schema' in value:
                    examples.append(value)
        if group == 'workflows':
            sources = {str(p.relative_to(root)): t for p, t in zip(paths, texts)}
            check_replacement_sources(sources)
            check_direct_sources(sources)
            check_handoff_sources(sources)
            check_typesafe_sources(sources)
            check_goal_sources(sources)
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
            for group in TARGET_GROUPS if args.group == 'all' else [args.group]:
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
