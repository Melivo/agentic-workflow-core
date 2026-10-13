/** SDK contract: @opencode/plugin and @opencode/schema exactly 2.0.25. */
import type { Plugin } from "@opencode/plugin"
import type { Tool } from "@opencode/schema/tool"
import { spawn } from "node:child_process"
import { existsSync, realpathSync, statSync } from "node:fs"
import { dirname, join, isAbsolute } from "node:path"
import { fileURLToPath } from "node:url"

const BRIDGE_TIMEOUT_MS = Math.min(120000, Math.max(100, Number(process.env.HABIT_FEEDBACK_BRIDGE_TIMEOUT_MS) || 120000))
const KILL_GRACE_MS = 2000
const MAX_INPUT = 8 * 1024 * 1024
const MAX_OUTPUT = 1024 * 1024
const MAX_STDERR = 65536
const moduleFile = join(dirname(fileURLToPath(import.meta.url)), "..", "hook", "habit_feedback_hook.py")
type Outcome = { status: string; feedback?: string | null; reasons?: string[] }
type EventBase = { tool: string; sessionID: string; id: string; input: unknown }

type BridgeBinding = { env: Record<string, string | undefined>; python: string; error?: string }

// ctx.options is the SDK2.0.25 Readonly<Record<string, any>> host configuration.
// Snapshot once per instance; never mutate process.env or read grants from events.
function bridgeBinding(options: Readonly<Record<string, unknown>>): BridgeBinding {
  const env: Record<string, string | undefined> = { PATH: process.env.PATH || "/usr/bin:/bin" }
  let python = "/usr/bin/python3"
  const names = { sensor: "HABIT_FEEDBACK_SENSOR", mapper: "HABIT_FEEDBACK_MAPPER",
    python: "HABIT_FEEDBACK_PYTHON", stateRoot: "HABIT_FEEDBACK_STATE_ROOT" }
  const absolute = (value: unknown): value is string => typeof value === "string"
    && value.length > 0 && isAbsolute(value) && !value.includes("\0")
    && !value.split("/").includes("..")
  for (const [name, key] of Object.entries(names)) {
    const value = Object.hasOwn(options, name) ? options[name] : process.env[key]
    if (value === undefined && !Object.hasOwn(options, name)) continue
    if (!absolute(value)) return {env, python, error: "invalid plugin installation option: " + name}
    if (name === "python") python = value
    else env[key] = value
  }
  const toolRoots: string[] = []
  const rootOption = Object.hasOwn(options, "trustedToolRoots")
  let roots: unknown = options.trustedToolRoots
  if (!rootOption && process.env.HABIT_FEEDBACK_TRUSTED_TOOL_ROOTS !== undefined) {
    try { roots = JSON.parse(process.env.HABIT_FEEDBACK_TRUSTED_TOOL_ROOTS) }
    catch { return {env, python, error: "invalid plugin installation option: trustedToolRoots"} }
  }
  if (rootOption || roots !== undefined) {
    if (!Array.isArray(roots) || !roots.every(root => absolute(root) && root !== "/"))
      return {env, python, error: "invalid plugin installation option: trustedToolRoots"}
    env.HABIT_FEEDBACK_TRUSTED_TOOL_ROOTS = JSON.stringify(roots)
    toolRoots.push(...roots)
  }
  // Explicit installations must work without login-shell PATH setup. Preserve
  // inherited lookup evidence too: the adapter still refuses unsafe entries.
  const cliDirs = [env.HABIT_FEEDBACK_SENSOR, env.HABIT_FEEDBACK_MAPPER]
    .filter((path): path is string => path !== undefined).map(path => dirname(path))
  env.PATH = [...cliDirs, ...toolRoots, env.PATH].join(":")
  return {env, python}
}

function runBridge(scope: string, event: EventBase & { phase: string; status?: string; result?: Tool.Result }, binding: BridgeBinding): Promise<Outcome> {
  return new Promise(resolve => {
    const failure = (reason: string): Outcome => ({status:"not_scanned", reasons:[reason]})
    if (binding.error) { resolve(failure(binding.error)); return }
    // Explicit Python options are executable too: refuse repository aliases
    // before launching the bridge, not after untrusted Python has executed.
    if (isAbsolute(binding.python)) {
      try {
        const real = realpathSync(binding.python)
        if (real === scope || real.startsWith(scope + "/") || !statSync(real).isFile()) {
          resolve(failure("unsafe plugin installation option: python")); return
        }
      } catch { resolve(failure("spawn failed: unavailable plugin installation option: python")); return }
    }
    let input: string
    try { input = JSON.stringify(event) } catch { resolve(failure("event cannot be serialized")); return }
    if (Buffer.byteLength(input) > MAX_INPUT) { resolve(failure("event payload exceeds input limit")); return }
    if (!existsSync(moduleFile)) { resolve(failure("hook module missing: " + moduleFile)); return }
    const child = spawn(binding.python, ["-B", moduleFile, "event"], {
      detached:true, stdio:["pipe","pipe","pipe"], env:{
        ...binding.env, HABIT_FEEDBACK_SCOPE:scope,
        HABIT_FEEDBACK_SESSION:event.sessionID,
      }
    })
    let stdout = Buffer.alloc(0), stderr = Buffer.alloc(0)
    let reason: string | null = null, killTimer: ReturnType<typeof setTimeout> | undefined
    function kill(signal: NodeJS.Signals) {
      try { if (child.pid) process.kill(-child.pid, signal) } catch { try { child.kill(signal) } catch {} }
    }
    function abort(message: string) {
      if (reason) return
      reason = message
      // Python SIGTERM handler kills and reaps separately grouped pipeline stages.
      kill("SIGTERM")
      killTimer = setTimeout(() => kill("SIGKILL"), KILL_GRACE_MS)
    }
    const timer = setTimeout(() => abort("bridge timed out"), BRIDGE_TIMEOUT_MS)
    child.stdout.on("data", (chunk: Buffer) => {
      if (reason) return
      if (stdout.length + chunk.length > MAX_OUTPUT) { abort("bridge output exceeded limit"); return }
      stdout = Buffer.concat([stdout,chunk])
    })
    child.stderr.on("data", (chunk: Buffer) => { stderr = Buffer.concat([stderr,chunk]).subarray(-MAX_STDERR) })
    child.on("error", err => { reason = "spawn failed: " + err.message })
    // Resolve only at close: process exit and all pipes have been observed.
    child.on("close", code => {
      clearTimeout(timer); if (killTimer) clearTimeout(killTimer)
      const tail = stderr.toString("utf8").slice(-400)
      if (reason || code !== 0) { resolve(failure((reason || "bridge exit code " + code) + "; stderr tail: " + tail)); return }
      try {
        const obj = JSON.parse(stdout.toString("utf8"))
        if (!obj || !["scanned","not_scanned","not_mutating","error"].includes(obj.status)) throw Error("invalid outcome")
        resolve(obj)
      } catch { resolve(failure("bridge stdout not JSON/valid outcome; stderr tail: " + tail)) }
    })
    child.stdin.on("error", () => {})
    child.stdin.end(input)
  })
}

function appendFeedback(result: Tool.Result, feedback: string): Tool.Result {
  const text = feedback.slice(0,4000)
  const content = result.content
  return {...result, content: typeof content === "string"
    ? content + "\n\n" + text
    : [...(content ?? []), {type:"text", text}]}
}

const plugin: Plugin.Plugin = {
  id:"opencode-habit-feedback",
  async setup(ctx) {
    const binding = bridgeBinding(ctx.options ?? {})
    const before = await ctx.tool.hook("execute.before", () => {})
    const after = await ctx.tool.hook("execute.after", async event => {
      if (event.status !== "completed") return // preserve original errors exactly
      if (event.tool.startsWith("habit")) return
      let outcome: Outcome
      try {
        // Session location, never plugin-instance location or process.cwd fallback.
        const session = await ctx.session.get({ sessionID: event.sessionID })
        const directory = session.location?.directory
        if (!directory || !isAbsolute(directory)) throw Error("session has no location.directory")
        const scope = realpathSync(directory)
        if (!statSync(scope).isDirectory()) throw Error("session location is not a directory")
        outcome = await runBridge(scope, {phase:"after",tool:event.tool, sessionID:event.sessionID,
          id:event.id,input:event.input,status:event.status,result:event.result}, binding)
      } catch (err) {
        outcome = {status:"not_scanned",reasons:["session lookup failed: " + String(err)]}
      }
      const feedback = outcome.feedback || (["not_scanned","error"].includes(outcome.status)
        ? "[habit-feedback v0.1.0] scan NOT RUN: " + (outcome.reasons || ["unknown failure"]).join("; ") : null)
      if (feedback) event.result = appendFeedback(event.result, feedback)
    })
    return async () => { await before.dispose(); await after.dispose() }
  }
}
export default plugin
