/**
 * main.js — Stash Deleter UI Plugin
 *
 * Registers a React page at /stash_deleter in the StashApp UI.
 * Provides full ruleset management and dry-run execution.
 *
 * ⚠ SAFETY: This file only implements DRY RUN. No delete button exists here.
 *   Deletion capability is deferred to a future sprint after safety review.
 *
 * Requirements:
 *   - window.PluginApi and window.React must be present (provided by Stash)
 *   - Bootstrap 5 classes (provided by Stash)
 *   - No npm, no bundler, no imports — plain browser JS
 */
(function () {
  "use strict";

  const { PluginApi, React } = window;
  const { useState, useEffect } = React;

  // ---------------------------------------------------------------------------
  // GraphQL helper — uses Stash's existing session cookie (same-origin)
  // ---------------------------------------------------------------------------
  async function gql(query, variables = {}) {
    const res = await fetch("/graphql", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, variables }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status} ${res.statusText}`);
    const json = await res.json();
    if (json.errors) throw new Error(json.errors[0].message);
    return json.data;
  }

  // ---------------------------------------------------------------------------
  // GraphQL queries / mutations
  // ---------------------------------------------------------------------------

  /** Load all plugin configuration from Stash's configuration store */
  const LOAD_CONFIG = `
    query LoadConfig {
      configuration { plugins }
    }
  `;

  /**
   * Persist plugin configuration.
   * $input is the Map! scalar — Stash accepts any JSON object here.
   */
  const SAVE_CONFIG = `
    mutation SaveConfig($input: Map!) {
      configurePlugin(plugin_id: "stash_deleter", input: $input)
    }
  `;

  /**
   * Trigger the Python backend in dry-run mode.
   * NEVER called with mode: "delete" from this file.
   */
  const RUN_DRY_RUN = `
    mutation RunDryRun {
      runPluginOperation(plugin_id: "stash_deleter", args: { mode: "dry_run" })
    }
  `;

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  /** Build a human-readable summary of a rule's criteria for the table. */
  function criteriaSummary(rule) {
    const parts = [];
    if (rule.min_play_count) parts.push(`plays ≥ ${rule.min_play_count}`);
    if (rule.max_play_count) parts.push(`plays ≤ ${rule.max_play_count}`);
    if (rule.require_no_rating) parts.push("no rating");
    if (rule.require_no_o_counter) parts.push("no orgasm");
    if (rule.days_on_disk_without_play)
      parts.push(`${rule.days_on_disk_without_play}d unwatched`);
    if (rule.max_rating100) parts.push(`rating ≤ ${rule.max_rating100}`);
    return parts.length ? parts.join(", ") : "No criteria set";
  }

  /** Generate a unique ID for new rules. */
  function generateId() {
    return "rule_" + Date.now();
  }

  /** Return a blank rule object with defaults. */
  function emptyRule() {
    return {
      id: generateId(),
      name: "",
      label: "",
      enabled: true,
      min_play_count: 0,
      max_play_count: 0,
      require_no_rating: false,
      require_no_o_counter: false,
      days_on_disk_without_play: 0,
      max_rating100: 0,
    };
  }

  // ---------------------------------------------------------------------------
  // RuleEditor component — inline card form for creating / editing a rule
  // ---------------------------------------------------------------------------
  function RuleEditor({ rule, onSave, onCancel }) {
    const [form, setForm] = useState({ ...rule });
    const [nameError, setNameError] = useState("");

    const e = React.createElement;

    function setField(field, value) {
      setForm((prev) => ({ ...prev, [field]: value }));
    }

    function validateName(val) {
      if (!val) return "Name is required";
      if (!/^[a-z0-9_]+$/.test(val))
        return "Lowercase letters, numbers, and underscores only";
      return "";
    }

    function handleSave() {
      const nameErr = validateName(form.name);
      if (nameErr) {
        setNameError(nameErr);
        return;
      }
      if (!form.label.trim()) return; // label is required; browser will show gap
      onSave(form);
    }

    const isEditing = rule.name !== ""; // distinguish add vs edit in title
    const editorTitle = isEditing ? `Editing: ${rule.name}` : "New Rule";

    return e(
      "div",
      { className: "card mt-3 border-primary" },

      // Header
      e(
        "div",
        { className: "card-header bg-primary text-white" },
        e("h6", { className: "mb-0" }, editorTitle)
      ),

      // Body
      e(
        "div",
        { className: "card-body" },
        e(
          "div",
          { className: "row g-3" },

          // Name
          e(
            "div",
            { className: "col-md-6" },
            e("label", { className: "form-label" }, "Name (slug) *"),
            e("input", {
              type: "text",
              className: `form-control ${nameError ? "is-invalid" : ""}`,
              value: form.name,
              placeholder: "e.g. low_rating",
              onChange: (ev) => {
                setField("name", ev.target.value);
                setNameError(validateName(ev.target.value));
              },
            }),
            nameError && e("div", { className: "invalid-feedback" }, nameError),
            e(
              "small",
              { className: "text-muted" },
              "Tag applied: stash-deleter:candidate:{name}"
            )
          ),

          // Label
          e(
            "div",
            { className: "col-md-6" },
            e("label", { className: "form-label" }, "Label *"),
            e("input", {
              type: "text",
              className: "form-control",
              value: form.label,
              placeholder: "e.g. Low Rating Scenes",
              required: true,
              onChange: (ev) => setField("label", ev.target.value),
            })
          ),

          // Enabled toggle
          e(
            "div",
            { className: "col-12" },
            e(
              "div",
              { className: "form-check form-switch" },
              e("input", {
                type: "checkbox",
                className: "form-check-input",
                id: "editor-enabled",
                role: "switch",
                checked: form.enabled,
                onChange: (ev) => setField("enabled", ev.target.checked),
              }),
              e(
                "label",
                { className: "form-check-label", htmlFor: "editor-enabled" },
                "Rule enabled"
              )
            )
          ),

          // Min Play Count
          e(
            "div",
            { className: "col-md-4" },
            e(
              "label",
              { className: "form-label" },
              "Min Play Count (0 = disabled)"
            ),
            e("input", {
              type: "number",
              className: "form-control",
              min: 0,
              value: form.min_play_count || 0,
              onChange: (ev) =>
                setField("min_play_count", parseInt(ev.target.value, 10) || 0),
            })
          ),

          // Max Play Count
          e(
            "div",
            { className: "col-md-4" },
            e(
              "label",
              { className: "form-label" },
              "Max Play Count (0 = disabled)"
            ),
            e("input", {
              type: "number",
              className: "form-control",
              min: 0,
              value: form.max_play_count || 0,
              onChange: (ev) =>
                setField("max_play_count", parseInt(ev.target.value, 10) || 0),
            })
          ),

          // Days on Disk Without Play
          e(
            "div",
            { className: "col-md-4" },
            e(
              "label",
              { className: "form-label" },
              "Days on Disk Without Play (0 = disabled)"
            ),
            e("input", {
              type: "number",
              className: "form-control",
              min: 0,
              value: form.days_on_disk_without_play || 0,
              onChange: (ev) =>
                setField(
                  "days_on_disk_without_play",
                  parseInt(ev.target.value, 10) || 0
                ),
            })
          ),

          // Max Rating
          e(
            "div",
            { className: "col-md-4" },
            e(
              "label",
              { className: "form-label" },
              "Max Rating 0–100 (0 = disabled)"
            ),
            e("input", {
              type: "number",
              className: "form-control",
              min: 0,
              max: 100,
              value: form.max_rating100 || 0,
              onChange: (ev) =>
                setField("max_rating100", parseInt(ev.target.value, 10) || 0),
            })
          ),

          // Require No Rating checkbox
          e(
            "div",
            { className: "col-md-4 d-flex align-items-end pb-1" },
            e(
              "div",
              { className: "form-check" },
              e("input", {
                type: "checkbox",
                className: "form-check-input",
                id: "editor-no-rating",
                checked: form.require_no_rating || false,
                onChange: (ev) =>
                  setField("require_no_rating", ev.target.checked),
              }),
              e(
                "label",
                {
                  className: "form-check-label",
                  htmlFor: "editor-no-rating",
                },
                "Require No Rating"
              )
            )
          ),

          // Require No O-Counter checkbox
          e(
            "div",
            { className: "col-md-4 d-flex align-items-end pb-1" },
            e(
              "div",
              { className: "form-check" },
              e("input", {
                type: "checkbox",
                className: "form-check-input",
                id: "editor-no-o",
                checked: form.require_no_o_counter || false,
                onChange: (ev) =>
                  setField("require_no_o_counter", ev.target.checked),
              }),
              e(
                "label",
                { className: "form-check-label", htmlFor: "editor-no-o" },
                "Require No O-Counter"
              )
            )
          )
        ),

        // Action buttons
        e(
          "div",
          { className: "mt-3 d-flex gap-2" },
          e(
            "button",
            { className: "btn btn-primary", onClick: handleSave },
            "Save Rule"
          ),
          e(
            "button",
            { className: "btn btn-secondary", onClick: onCancel },
            "Cancel"
          )
        )
      )
    );
  }

  // ---------------------------------------------------------------------------
  // RulesetManager — main page component
  // ---------------------------------------------------------------------------
  function RulesetManager() {
    const [config, setConfig] = useState({
      deletion_scope: "db_only",
      rules: [],
    });
    const [saving, setSaving] = useState(false);
    const [saveStatus, setSaveStatus] = useState(null); // "success" | "error"
    const [running, setRunning] = useState(false);
    const [results, setResults] = useState(null);
    const [editingRule, setEditingRule] = useState(null); // null = not editing
    const [error, setError] = useState(null);

    const e = React.createElement;

    // Load config on mount
    useEffect(() => {
      gql(LOAD_CONFIG)
        .then((data) => {
          const pluginCfg =
            (data.configuration.plugins || {})["stash_deleter"];
          if (pluginCfg) {
            setConfig({
              deletion_scope: pluginCfg.deletion_scope || "db_only",
              rules: pluginCfg.rules || [],
            });
          }
        })
        .catch((err) => setError(`Failed to load configuration: ${err.message}`));
    }, []);

    // -------------------------------------------------------------------------
    // Save configuration
    // -------------------------------------------------------------------------
    async function handleSave() {
      setSaving(true);
      setSaveStatus(null);
      setError(null);
      try {
        await gql(SAVE_CONFIG, { input: config });
        setSaveStatus("success");
        setTimeout(() => setSaveStatus(null), 3000);
      } catch (err) {
        setError(`Save failed: ${err.message}`);
        setSaveStatus("error");
      } finally {
        setSaving(false);
      }
    }

    // -------------------------------------------------------------------------
    // Run dry run — ONLY mode ever sent from this UI
    // -------------------------------------------------------------------------
    async function handleDryRun() {
      setRunning(true);
      setResults(null);
      setError(null);
      try {
        const data = await gql(RUN_DRY_RUN);
        const raw = data.runPluginOperation;
        // The plugin writes JSON to stdout; Stash echoes it here as a string.
        let parsed;
        try {
          parsed = typeof raw === "string" ? JSON.parse(raw) : raw;
        } catch (_) {
          parsed = { raw };
        }
        setResults(parsed);
      } catch (err) {
        setError(`Dry run failed: ${err.message}`);
      } finally {
        setRunning(false);
      }
    }

    // -------------------------------------------------------------------------
    // Rule CRUD
    // -------------------------------------------------------------------------
    function handleAddRule() {
      setEditingRule({ ...emptyRule(), _isNew: true });
    }

    function handleEditRule(rule) {
      setEditingRule({ ...rule, _isNew: false });
    }

    function handleSaveRule(savedRule) {
      const { _isNew, ...rule } = savedRule;
      setConfig((prev) => ({
        ...prev,
        rules: _isNew
          ? [...prev.rules, rule]
          : prev.rules.map((r) => (r.id === rule.id ? rule : r)),
      }));
      setEditingRule(null);
    }

    function handleDeleteRule(ruleId) {
      setConfig((prev) => ({
        ...prev,
        rules: prev.rules.filter((r) => r.id !== ruleId),
      }));
    }

    function handleToggleRule(ruleId) {
      setConfig((prev) => ({
        ...prev,
        rules: prev.rules.map((r) =>
          r.id === ruleId ? { ...r, enabled: !r.enabled } : r
        ),
      }));
    }

    // -------------------------------------------------------------------------
    // Dry run results table
    // -------------------------------------------------------------------------
    function renderResults() {
      if (!results) return null;

      // Normalise: plugin output is wrapped in { output: {...}, error: null }
      const output = results.output || results;
      const ruleResults = output.rules || null;
      const totalCandidates = output.total_candidates ?? null;
      const pluginError = results.error || null;

      return e(
        "div",
        { className: "mt-4" },
        e("h5", null, "Dry Run Results"),

        pluginError &&
          e(
            "div",
            { className: "alert alert-danger" },
            `Plugin error: ${pluginError}`
          ),

        ruleResults && ruleResults.length > 0
          ? e(
              "div",
              null,
              totalCandidates !== null &&
                e(
                  "p",
                  { className: "text-muted" },
                  `Total candidates across all rules: `,
                  e("strong", null, totalCandidates)
                ),
              e(
                "table",
                { className: "table table-sm table-bordered table-hover" },
                e(
                  "thead",
                  { className: "table-light" },
                  e(
                    "tr",
                    null,
                    e("th", null, "Rule"),
                    e("th", { className: "text-center" }, "Candidates"),
                    e("th", null, "Tag applied in Stash")
                  )
                ),
                e(
                  "tbody",
                  null,
                  ruleResults.map((r) =>
                    e(
                      "tr",
                      { key: r.name || r.label },
                      e(
                        "td",
                        null,
                        r.label || r.name,
                        r.name &&
                          e(
                            "small",
                            { className: "text-muted ms-2" },
                            `(${r.name})`
                          )
                      ),
                      e(
                        "td",
                        { className: "text-center" },
                        e(
                          "span",
                          {
                            className:
                              (r.candidate_count ?? 0) > 0
                                ? "badge bg-warning text-dark"
                                : "badge bg-secondary",
                          },
                          r.candidate_count ?? "?"
                        )
                      ),
                      e(
                        "td",
                        null,
                        r.candidate_tag
                          ? e(
                              "span",
                              null,
                              e(
                                "code",
                                { className: "small" },
                                r.candidate_tag
                              ),
                              e(
                                "span",
                                { className: "text-muted small ms-2" },
                                "— filter Scenes by this tag to review"
                              )
                            )
                          : e("span", { className: "text-muted" }, "—")
                      )
                    )
                  )
                )
              )
            )
          : !pluginError &&
            e(
              "div",
              { className: "alert alert-info" },
              "Dry run completed. No rule result data returned — check the Stash task log for details."
            )
      );
    }

    // -------------------------------------------------------------------------
    // Enabled rule count (used to gate dry-run button)
    // -------------------------------------------------------------------------
    const enabledCount = config.rules.filter((r) => r.enabled).length;

    // -------------------------------------------------------------------------
    // Render
    // -------------------------------------------------------------------------
    return e(
      "div",
      { className: "container-fluid py-4", style: { maxWidth: "1000px" } },

      // --- Header ---
      e(
        "div",
        { className: "mb-4" },
        e("h2", null, "Stash Deleter"),
        e(
          "p",
          { className: "text-muted" },
          "Manage deletion rule sets and run dry runs to preview candidates."
        ),
        // Safety banner — always visible
        e(
          "div",
          { className: "alert alert-warning mb-0 d-flex gap-2" },
          e("span", { className: "fw-bold" }, "⚠ Dry Run Only."),
          e(
            "span",
            null,
            " This UI only executes dry runs — no scenes are deleted. " +
              "Deletion capability will be added in a future release after safety review."
          )
        )
      ),

      // --- Global error ---
      error &&
        e(
          "div",
          { className: "alert alert-danger alert-dismissible" },
          error,
          e("button", {
            type: "button",
            className: "btn-close",
            onClick: () => setError(null),
          })
        ),

      // --- Global Settings ---
      e(
        "div",
        { className: "card mb-4" },
        e(
          "div",
          { className: "card-header" },
          e("h5", { className: "mb-0" }, "Global Settings")
        ),
        e(
          "div",
          { className: "card-body" },
          e("label", { className: "form-label fw-bold d-block" }, "Deletion Scope"),
          e(
            "div",
            { className: "mb-1" },
            // db_only option
            e(
              "div",
              { className: "form-check form-check-inline" },
              e("input", {
                type: "radio",
                className: "form-check-input",
                id: "scope-db",
                name: "deletion_scope",
                value: "db_only",
                checked: config.deletion_scope === "db_only",
                onChange: () =>
                  setConfig((prev) => ({ ...prev, deletion_scope: "db_only" })),
              }),
              e(
                "label",
                { className: "form-check-label", htmlFor: "scope-db" },
                "db_only — Database record only"
              )
            ),
            // with_file option
            e(
              "div",
              { className: "form-check form-check-inline" },
              e("input", {
                type: "radio",
                className: "form-check-input",
                id: "scope-file",
                name: "deletion_scope",
                value: "with_file",
                checked: config.deletion_scope === "with_file",
                onChange: () =>
                  setConfig((prev) => ({
                    ...prev,
                    deletion_scope: "with_file",
                  })),
              }),
              e(
                "label",
                { className: "form-check-label", htmlFor: "scope-file" },
                "with_file — Also delete file from disk"
              )
            )
          ),
          e(
            "small",
            { className: "text-muted" },
            "Scope is saved to config but deletion is not implemented in this release."
          )
        )
      ),

      // --- Rules ---
      e(
        "div",
        { className: "card mb-4" },
        e(
          "div",
          {
            className:
              "card-header d-flex justify-content-between align-items-center",
          },
          e("h5", { className: "mb-0" }, "Deletion Rules"),
          e(
            "button",
            {
              className: "btn btn-sm btn-success",
              onClick: handleAddRule,
              disabled: editingRule !== null,
            },
            "+ Add Rule"
          )
        ),
        e(
          "div",
          { className: "card-body p-0" },

          config.rules.length === 0
            ? e(
                "p",
                { className: "text-muted p-3 mb-0" },
                'No rules defined. Click \u201c+ Add Rule\u201d to create one.'
              )
            : e(
                "table",
                { className: "table table-hover mb-0" },
                e(
                  "thead",
                  { className: "table-light" },
                  e(
                    "tr",
                    null,
                    e("th", null, "Name"),
                    e("th", null, "Label"),
                    e("th", null, "Criteria"),
                    e("th", { className: "text-center" }, "Enabled"),
                    e("th", { className: "text-end" }, "Actions")
                  )
                ),
                e(
                  "tbody",
                  null,
                  config.rules.map((rule) =>
                    e(
                      "tr",
                      { key: rule.id },
                      e("td", null, e("code", null, rule.name)),
                      e("td", null, rule.label),
                      e(
                        "td",
                        { className: "text-muted small" },
                        criteriaSummary(rule)
                      ),
                      // Enabled toggle
                      e(
                        "td",
                        { className: "text-center" },
                        e(
                          "div",
                          {
                            className:
                              "form-check form-switch d-flex justify-content-center mb-0",
                          },
                          e("input", {
                            type: "checkbox",
                            className: "form-check-input",
                            role: "switch",
                            checked: rule.enabled,
                            onChange: () => handleToggleRule(rule.id),
                          })
                        )
                      ),
                      // Edit / Delete
                      e(
                        "td",
                        { className: "text-end" },
                        e(
                          "div",
                          { className: "d-flex gap-1 justify-content-end" },
                          e(
                            "button",
                            {
                              className: "btn btn-sm btn-outline-secondary",
                              onClick: () => handleEditRule(rule),
                              disabled: editingRule !== null,
                            },
                            "Edit"
                          ),
                          e(
                            "button",
                            {
                              className: "btn btn-sm btn-outline-danger",
                              onClick: () => handleDeleteRule(rule.id),
                              disabled: editingRule !== null,
                            },
                            "Delete"
                          )
                        )
                      )
                    )
                  )
                )
              ),

          // Inline rule editor (shown below the table when active)
          editingRule &&
            e(
              "div",
              { className: "p-3 border-top" },
              e(RuleEditor, {
                rule: editingRule,
                onSave: handleSaveRule,
                onCancel: () => setEditingRule(null),
              })
            )
        )
      ),

      // --- Dry Run ---
      e(
        "div",
        { className: "card mb-4" },
        e(
          "div",
          { className: "card-header" },
          e("h5", { className: "mb-0" }, "Dry Run")
        ),
        e(
          "div",
          { className: "card-body" },
          e(
            "p",
            { className: "text-muted" },
            "Runs all enabled rules and tags matching scenes with ",
            e("code", null, "stash-deleter:candidate:{name}"),
            ". No scenes are deleted."
          ),
          e(
            "div",
            { className: "d-flex align-items-center gap-3" },
            e(
              "button",
              {
                className: "btn btn-warning",
                onClick: handleDryRun,
                disabled: running || enabledCount === 0,
              },
              running
                ? e(
                    "span",
                    null,
                    e("span", {
                      className: "spinner-border spinner-border-sm me-2",
                      role: "status",
                      "aria-hidden": "true",
                    }),
                    "Running…"
                  )
                : "Run Dry Run"
            ),
            enabledCount === 0 &&
              !running &&
              e(
                "small",
                { className: "text-muted" },
                "Enable at least one rule above to run."
              )
          ),
          renderResults()
        )
      ),

      // --- Save Configuration ---
      e(
        "div",
        { className: "card mb-4" },
        e(
          "div",
          { className: "card-body d-flex align-items-center gap-3" },
          e(
            "button",
            {
              className: "btn btn-primary",
              onClick: handleSave,
              disabled: saving,
            },
            saving
              ? e(
                  "span",
                  null,
                  e("span", {
                    className: "spinner-border spinner-border-sm me-2",
                    role: "status",
                    "aria-hidden": "true",
                  }),
                  "Saving…"
                )
              : "Save Configuration"
          ),
          saveStatus === "success" &&
            e("span", { className: "text-success fw-semibold" }, "✓ Configuration saved."),
          saveStatus === "error" &&
            e(
              "span",
              { className: "text-danger fw-semibold" },
              "✗ Save failed. See error above."
            )
        )
      )
    );
  }

  // ---------------------------------------------------------------------------
  // Register the plugin page route
  // ⚠ DRY RUN ONLY — no delete button registered anywhere
  // ---------------------------------------------------------------------------
  PluginApi.register.route("/stash_deleter", () =>
    React.createElement(RulesetManager, null)
  );
})();
