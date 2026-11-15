# Entwicklung und Paketpflege

Dieser Leitfaden enthält die technischen Entwicklungs-, Prüf-, Paket- und Releaseangaben des Projekts. Die [README](../README.md) bleibt der Einstieg; kanonische Workflowregeln stehen in den verlinkten Core-Verträgen und Skills.

## Repositorystruktur

| Pfad | Inhalt |
| --- | --- |
| `.apm/skills/` | Kanonische Skills, Methoden, Verträge und Ressourcen |
| `.apm/agents/` | Native Fachagentenprofile |
| `scripts/` | Prüfungen, Toolchain, Paket- und Releasewerkzeuge |
| `tests/` | Vertrags-, Sicherheits- und Integrationstests |
| `.github/workflows/` | CI und getrennte Releasekette |
| [DESIGN.md](../DESIGN.md) | Architektur und Workflowüberblick |
| `.agentic-workflow/` | Lokale Pläne und Run-Artefakte; in diesem Repository von Git ignoriert |

Core-Skills liegen unter `.apm/skills/core-<name>/`; Ordnername und Frontmatter-`name` stimmen überein. `core-init-project` enthält die Providerintegration als interne Komponente. Bestätigte Pläne werden nicht mit Laufstatus überschrieben.

## Paketinstallation

Voraussetzung für die Installation ist [APM](https://microsoft.github.io/apm/getting-started/installation/). Eine globale Installation verwendet das gemeinsame Skill-Verzeichnis:

```bash
apm install Melivo/agentic-workflow-core --global --target agent-skills --only apm
```

Mit `--dry-run` lässt sich vorab die geplante Änderung anzeigen. Zum Aktualisieren:

```bash
apm install Melivo/agentic-workflow-core --global --target agent-skills --only apm --update
```

Unter APM 0.31 verwendet dieses Beispiel `install --update`, weil `apm update` keinen entsprechenden `--only apm`-Filter anbietet. Ein vorhandenes Release-Tag enthält nicht automatisch neuere Änderungen auf `main`.

Setze im globalen Verbrauchsmanifest `~/.apm/apm.yml` `targets: [agent-skills]`, damit spätere Installationen dasselbe Ziel verwenden. APM hält aufgelöste Paketstände in `apm.lock.yaml` fest. Für reproduzierbare Stände kann die Quelle mit `#<commit-sha>` gepinnt werden; Updates überspringen einen Pin nicht automatisch.

Für bewusst ausgewählte OpenCode-/Codex-Ziele im Projekt:

```bash
apm install Melivo/agentic-workflow-core --target opencode,codex
```

Dieser Modus integriert auch die vorgesehenen Agentendefinitionen und kann Harness-Konfiguration erzeugen. Generierte `.agents/`, `.opencode/` und `.codex/` werden nicht von Hand gepflegt. Skill-Installation richtet MCP-Server, Modellanbieter oder native Fachagenten nicht automatisch ein. Es gibt keine externe APM-Skillabhängigkeit.

## Lokale Prüfungen

Die lokalen und CI-Aufgaben benötigen `mise` mindestens `2026.10.19` und Python exakt `3.13.14`. Die zentrale Mindestversion der Toolchain muss mit `min_version` in `mise.toml` übereinstimmen. Stabile neuere mise-Versionen sind zulässig; RPM-verwaltetes mise wird weder ersetzt noch heruntergestuft. Versionsabfrage muss erfolgreich sein; ältere, ungültige und Vorabversionen werden abgewiesen. Bootstrap protokolliert mise-Version und Minimum als `RUNTIME`, andere Werkzeugversionen als `TOOLS` beziehungsweise Setupausgabe. CI lässt `version` und `sha256` bei der SHA-gepinnten mise-action weg: deren stabile Standardauswahl prüft Downloads gegen Minisign-signierte Prüfsummen (geprüfter Action-Commit `2d8d4cafcbd33be2ea37d2b6f5ad595363d1f1ca`).

Toolversionen und Integritätswerte stehen in [ci_toolchain.json](../scripts/ci_toolchain.json), [requirements-ci.txt](../scripts/requirements-ci.txt) und [Habit-Testtoolchain](../scripts/habit-ci/package.json).

```bash
# Setup installiert gepinnte Werkzeuge in den isolierten Arbeitsbereich.
mise run tools:setup

# Diese Prüfungen installieren nichts automatisch.
mise run check
mise run version:check
mise run release:test
mise run workflows:check
mise run docs:check
```

`mise run tools:setup` benötigt ausdrückliche Freigabe und kann bei Bedarf erneut ausgeführt werden. Die qualifizierte Entwicklungs- und CI-Laufzeit ist Linux x64; daraus folgt keine universelle Betriebssystemfreigabe.

Die portable TypeSafe-Collection und ihre synthetischen Tests bleiben versioniert. Optionale hostgebundene Runtime-Abnahmen sind lokale Betreiberprüfungen, keine CI- oder Verbrauchervoraussetzung; Zweck und aktueller Entscheidungsstand der Evaluation stehen in der [Operationsreferenz](operations/typesafe-collection.md#evaluationszweck).

Die vollständige Abnahme `mise run acceptance` führt die Prüfungen zusammen und baut zusätzlich ein Paket, das in einem frischen Scratch-Verbraucher installiert und kontrolliert wird. Sie hat ausdrücklich Paket- und Installationswirkung. Geprüft werden Quellen, Lizenzhinweise, Core-Bundles, Konfigurator und relative Links. Ein Exitcode allein genügt nicht; temporäre Reports sind keine dauerhaft gesicherten Nachweise. Die [Habit-Paketvorbereitung](../scripts/check_habit_feedback.py) baut und installiert ebenfalls offline im Scratchbereich und benötigt eine ausdrückliche Setup-/Installationsfreigabe.

Mit vorhandenem SDK lässt sich die Habit-Testinstallation gezielt und offline im Scratchbereich erneuern, zum Beispiel aus dem Standard-CI-Arbeitsbereich:

```bash
AWC_CI_WORKSPACE=/tmp/opencode/agentic-workflow-core-ci AWC_HABIT_SDK=/tmp/opencode/agentic-workflow-core-ci/habit-sdk python3 -B scripts/check_habit_feedback.py setup
```

`AWC_CI_WORKSPACE` kann auf einen anderen isolierten Arbeitsbereich zeigen; dessen SDK-Pfad ist dann `<Arbeitsbereich>/habit-sdk` und kann mit `AWC_HABIT_SDK` ausdrücklich gesetzt werden. Fehlt das SDK, blockiert der Setupbefehl statt es automatisch zu installieren.

## Paket bauen und lokal installieren

Nach freigegebenem Werkzeugsetup kann der geprüfte Producer aus einem sauberen Checkout verwendet werden:

```bash
python3 -B scripts/build_core_package.py verify --output /tmp/opencode/core-package
```

Der Befehl baut und prüft ein isoliertes ZIP und installiert es zur Abnahme in einem frischen Verbraucher. Nicht aus einem Verbrauchsprojekt mit dessen `apm_modules`-Cache packen, weil nicht portable Cache-Verweise ins Bundle geraten könnten.

Ein geprüftes ZIP lässt sich separat installieren:

```bash
apm install /path/to/agentic-workflow-core-X.Y.Z.zip --global --target agent-skills
```

Bei lokalen Bundles ist `--only apm` nicht erlaubt. Beim manuellen Packen mit APM 0.31/0.33 `--target agent-skills` ausdrücklich setzen: Das Standardziel `minimal` kann dort eine nicht installierbare Ausgabe erzeugen. Der Producer verwendet das geprüfte Plugin-Bundle-Format, nicht `--format apm`.

## CI, Releases und Versionsregeln

[CI](../.github/workflows/ci.yaml) prüft Pull Requests und Pushes auf `main` über dieselben Tasks wie lokal. Sie benötigt keine private Skillabhängigkeit, hat nur lesende Repositoryrechte und keine Veröffentlichungssecrets.

Die getrennte [Releasekette](../.github/workflows/release.yaml) ist standardmäßig deaktiviert. `RELEASE_PR_AUTOMATION_ENABLED` und `RELEASE_PUBLICATION_ENABLED` müssen für ihre jeweiligen Wirkungen exakt `true` sein. Release Please darf einen Release-PR vorschlagen; automatisches Merge gibt es nicht. Veröffentlichung setzt einen bewusst gemergten, geprüften Release-PR sowie die Bedingungen in [release_guard.py](../scripts/release_guard.py) voraus. Ein normaler Push ist keine Releasefreigabe.

Für 0.x gilt: Fehlerkorrektur → Patch; neue Funktion oder inkompatible Änderung → Minor. Der Wechsel auf `1.0.0` braucht eine gesonderte Entscheidung. Fehlende, laufende oder fehlgeschlagene Pflichtchecks blockieren die Veröffentlichung; bestehende Tags und Assets werden nicht beiläufig überschrieben. App-Authentifizierung und Branchschutz sind separat einzurichten.

## Optionales Qualitätsfeedback

[opencode-habit-feedback@0.1.0](https://www.npmjs.com/package/opencode-habit-feedback) ist ein getrenntes npm-Paket und für andere Core-Verbraucher optional. Es nutzt Original-Sensoren und -Mapper von Habit Hooks. Die APM-Skill-Installation aktiviert es nicht automatisch. Installation, Werkzeugbindung und Registrierung als OpenCode-V2-Eintrag `{package, options}` im `plugins`-Array sind getrennte Einrichtungsschritte; vorhandene Plugins bleiben erhalten und der Laufzeit-Hook installiert nichts.

Qualifiziert ist der Linux-Einzeldatei-Pfad mit Python-/generischen Sensoren und Ruff; Versionen stehen in [VERSIONS.md](../.apm/skills/core-devops/assets/opencode-habit-feedback/VERSIONS.md). Repositoryweite Sensoren wie jscpd und deptry werden im automatischen Dateihook ausgeschlossen. Nicht unterstützte Toolformen, deaktivierte Sensoren und nicht qualifizierte Sensor-Scopes erscheinen als `not_scanned`, nicht als „alles sauber“. Hinweise sind keine Benutzeranweisungen oder Freigaben. Statische Checks und kontrollierte Hosttests belegen weder zuverlässige Modellbefolgung noch allgemeinen Qualitätsgewinn. [Technische Optionen, Sicherheitsgrenzen und Prüfkommandos](../.apm/skills/core-devops/references/habit-feedback.md).

## Herkunft und Lizenzen

[MIT](../LICENSE). Die integrierte Providerkomponente enthält ihren [MIT-Lizenznachweis](../.apm/skills/core-init-project/LICENSE), ihre [Herkunftsdokumentation](../.apm/skills/core-init-project/PROVENANCE.md) und [Requirements](../.apm/skills/core-init-project/REQUIREMENTS.md). Hinweise auf adaptierte Architekturmethoden stehen in [THIRD_PARTY_NOTICES.md](../.apm/skills/core-architecture/THIRD_PARTY_NOTICES.md).
