import Editor from "@toast-ui/editor";
import { remark } from "remark";
import remarkGfm from "remark-gfm";
import remarkPresetLintRecommended from "remark-preset-lint-recommended";

const markdownProcessor = remark()
  .data("settings", {
    bullet: "-",
    emphasis: "*",
    fences: true,
    listItemIndent: "one",
    strong: "*"
  })
  .use(remarkGfm)
  .use(remarkPresetLintRecommended);

    const filesEl = document.querySelector("#files");
    const pathEl = document.querySelector("#current-path");
    const modeWysiwygEl = document.querySelector("#mode-wysiwyg");
    const modeMarkdownEl = document.querySelector("#mode-markdown");
    const saveEl = document.querySelector("#save");
    const statusEl = document.querySelector("#status");
    const lintPanelEl = document.querySelector("#lint-panel");
    const editorEl = document.querySelector("#editor");

    let editor = null;
    let currentPath = null;
    let validPaths = new Set();
    let dirty = false;
    let suppressDirty = 0;
    let suppressHashChange = false;
    let loadingPath = null;
    const cursorStoragePrefix = "standards-editor:cursor:v1:";

    function setStatus(message, isError = false) {
      statusEl.textContent = message;
      statusEl.classList.toggle("error", isError);
    }

    function markDirty() {
      if (suppressDirty > 0) {
        return;
      }
      dirty = true;
      saveEl.disabled = !currentPath;
      setStatus("Unsaved changes");
      clearLintPanel();
    }

    function withoutDirtyTracking(action) {
      suppressDirty += 1;
      try {
        return action();
      } finally {
        setTimeout(() => {
          suppressDirty = Math.max(0, suppressDirty - 1);
        }, 0);
      }
    }

    function setActive(path) {
      for (const button of filesEl.querySelectorAll("button")) {
        button.classList.toggle("active", button.dataset.path === path);
      }
    }

    function cursorStorageKey(path) {
      return `${cursorStoragePrefix}${path}`;
    }

    function getMode() {
      if (!editor) {
        return "wysiwyg";
      }
      return editor.isMarkdownMode && editor.isMarkdownMode() ? "markdown" : "wysiwyg";
    }

    function setModeButtonsEnabled(enabled) {
      modeWysiwygEl.disabled = !enabled;
      modeMarkdownEl.disabled = !enabled;
    }

    function syncModeToggle() {
      const mode = getMode();
      modeWysiwygEl.classList.toggle("active", mode === "wysiwyg");
      modeMarkdownEl.classList.toggle("active", mode === "markdown");
    }

    function changeEditorMode(mode, options = {}) {
      const { restoreCursor = true } = options;
      if (!editor || !editor.changeMode) {
        return;
      }
      if (mode !== "markdown" && mode !== "wysiwyg") {
        return;
      }
      saveCursorState();
      withoutDirtyTracking(() => editor.changeMode(mode, true));
      syncModeToggle();
      if (restoreCursor) {
        restoreCursorState(currentPath);
      }
    }

    function glyphCount(text) {
      if (typeof Intl !== "undefined" && Intl.Segmenter) {
        return Array.from(new Intl.Segmenter(undefined, { granularity: "grapheme" }).segment(text)).length;
      }
      return Array.from(text).length;
    }

    function codeUnitIndexForGlyphColumn(text, glyphColumn) {
      if (glyphColumn <= 0) {
        return 0;
      }
      if (typeof Intl !== "undefined" && Intl.Segmenter) {
        let count = 0;
        for (const segment of new Intl.Segmenter(undefined, { granularity: "grapheme" }).segment(text)) {
          if (count >= glyphColumn) {
            return segment.index;
          }
          count += 1;
        }
        return text.length;
      }

      let index = 0;
      for (const glyph of Array.from(text)) {
        if (glyphColumn <= 0) {
          return index;
        }
        index += glyph.length;
        glyphColumn -= 1;
      }
      return text.length;
    }

    function linePointFromOffset(markdown, offset) {
      const clampedOffset = Math.max(0, Math.min(offset, markdown.length));
      const before = markdown.slice(0, clampedOffset);
      const lines = before.split("\n");
      return {
        line: lines.length,
        glyphColumn: glyphCount(lines[lines.length - 1] || "")
      };
    }

    function normalizeSelectionPoint(point, markdown) {
      if (Array.isArray(point) && point.length >= 2 && Number.isFinite(point[0]) && Number.isFinite(point[1])) {
        const lines = markdown.split("\n");
        const line = Math.max(1, Math.min(Math.trunc(point[0]), lines.length));
        const lineText = lines[line - 1] || "";
        return {
          line,
          glyphColumn: Math.max(0, Math.min(glyphCount(lineText), glyphCount(lineText.slice(0, Math.max(0, Math.trunc(point[1]))))))
        };
      }

      if (Number.isFinite(point)) {
        return linePointFromOffset(markdown, Math.trunc(point));
      }

      return null;
    }

    function selectionPointForEditor(point, markdown) {
      if (!point || !Number.isFinite(point.line) || !Number.isFinite(point.glyphColumn)) {
        return null;
      }
      const lines = markdown.split("\n");
      const line = Math.max(1, Math.min(Math.trunc(point.line), lines.length));
      const lineText = lines[line - 1] || "";
      const column = codeUnitIndexForGlyphColumn(lineText, Math.max(0, Math.trunc(point.glyphColumn)));
      return [line, column];
    }

    function getHashPath() {
      const rawHash = window.location.hash.replace(/^#/, "");
      const params = new URLSearchParams(rawHash);
      const path = params.get("file");
      return path && validPaths.has(path) ? path : null;
    }

    function setHashPath(path) {
      const hash = `#file=${path}`;
      if (window.location.hash === hash) {
        return;
      }
      suppressHashChange = true;
      history.replaceState(null, "", hash);
      queueMicrotask(() => {
        suppressHashChange = false;
      });
    }

    function getCursorState() {
      if (!editor || !currentPath) {
        return null;
      }
      try {
        const markdown = editor.getMarkdown ? editor.getMarkdown() : "";
        const selection = editor.getSelection ? editor.getSelection() : null;
        const selectionStart = Array.isArray(selection) ? selection[0] : null;
        return {
          mode: getMode(),
          selection,
          point: normalizeSelectionPoint(selectionStart, markdown),
          scrollTop: editor.getScrollTop ? editor.getScrollTop() : 0,
          updatedAt: Date.now()
        };
      } catch {
        return null;
      }
    }

    function saveCursorState(path = currentPath) {
      if (!path || !editor || loadingPath) {
        return;
      }
      const state = getCursorState();
      if (!state || (!state.selection && !state.point)) {
        return;
      }
      try {
        localStorage.setItem(cursorStorageKey(path), JSON.stringify(state));
      } catch {
        // Ignore private browsing or storage quota failures.
      }
    }

    function readCursorState(path) {
      try {
        const raw = localStorage.getItem(cursorStorageKey(path));
        return raw ? JSON.parse(raw) : null;
      } catch {
        return null;
      }
    }

    function restoreCursorState(path) {
      if (!editor || !path) {
        return;
      }
      const state = readCursorState(path);
      if (!state || (!state.selection && !state.point)) {
        return;
      }

      requestAnimationFrame(() => {
        setTimeout(() => {
          try {
            if ((state.mode === "markdown" || state.mode === "wysiwyg") && editor.changeMode) {
              withoutDirtyTracking(() => editor.changeMode(state.mode, true));
              syncModeToggle();
            }
            const markdown = editor.getMarkdown ? editor.getMarkdown() : "";
            const point = selectionPointForEditor(state.point, markdown);
            if (editor.setSelection && point) {
              editor.setSelection(point, point);
            } else if (editor.setSelection && Array.isArray(state.selection)) {
              editor.setSelection(state.selection[0], state.selection[1]);
            }
            if (editor.setScrollTop && Number.isFinite(state.scrollTop)) {
              editor.setScrollTop(state.scrollTop);
            }
          } catch {
            // Saved cursor ranges can become stale after edits; default placement is fine.
          }
        }, 0);
      });
    }

    function moveCursorToStart() {
      requestAnimationFrame(() => {
        setTimeout(() => {
          try {
            if (editor.setSelection) {
              editor.setSelection([1, 0], [1, 0]);
            }
            if (editor.setScrollTop) {
              editor.setScrollTop(0);
            }
          } catch {
            // Default editor placement is acceptable if the API rejects the position.
          }
        }, 0);
      });
    }

    function restoreInitialCursorState(path) {
      const state = readCursorState(path);
      if (state && (state.selection || state.point)) {
        restoreCursorState(path);
      } else {
        moveCursorToStart();
      }
    }

    async function requestJson(url, options = {}) {
      const response = await fetch(url, options);
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.error || `${response.status} ${response.statusText}`);
      }
      return data;
    }

    function clearLintPanel() {
      lintPanelEl.classList.remove("visible");
      lintPanelEl.textContent = "";
    }

    function focusMarkdownEditor() {
      const target = editorEl.querySelector(".cm-content")
        || editorEl.querySelector(".ProseMirror")
        || editorEl.querySelector("[contenteditable='true']")
        || editorEl.querySelector("textarea");
      if (target && target.focus) {
        target.focus({ preventScroll: true });
      } else if (editor && editor.focus) {
        editor.focus();
      }
    }

    function highlightMarkdownLine(line) {
      const previous = editorEl.querySelectorAll(".lint-target-line");
      for (const element of previous) {
        element.classList.remove("lint-target-line");
      }

      const lines = editorEl.querySelectorAll(".toastui-editor-md-container .cm-line, .toastui-editor-md-container .CodeMirror-line");
      const target = lines[Math.max(0, line - 1)];
      if (!target) {
        return;
      }
      target.classList.add("lint-target-line");
      setTimeout(() => target.classList.remove("lint-target-line"), 2500);
    }

    function textNodeAtOffset(root, offset) {
      const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
      let remaining = Math.max(0, offset);
      let node = walker.nextNode();
      while (node) {
        if (remaining <= node.nodeValue.length) {
          return { node, offset: remaining };
        }
        remaining -= node.nodeValue.length;
        node = walker.nextNode();
      }
      return { node: root, offset: root.childNodes.length };
    }

    function selectMarkdownSourceLine(line) {
      const markdown = editor.getMarkdown ? editor.getMarkdown() : "";
      const lines = markdown.split("\n");
      const targetLine = Math.max(1, Math.min(Math.trunc(line), lines.length));
      const source = editorEl.querySelector(".toastui-editor-md-container .ProseMirror[contenteditable='true']");
      if (!source) {
        return false;
      }

      source.focus({ preventScroll: true });
      const lineElement = source.children[targetLine - 1];
      if (!lineElement) {
        return false;
      }
      const start = textNodeAtOffset(lineElement, 0);
      const end = textNodeAtOffset(lineElement, lineElement.textContent.length);
      const range = document.createRange();
      range.setStart(start.node, start.offset);
      range.setEnd(end.node, end.offset);
      const selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);

      lineElement.classList.add("lint-target-line");
      lineElement.scrollIntoView({ block: "center", inline: "nearest" });
      setTimeout(() => lineElement.classList.remove("lint-target-line"), 2500);
      return true;
    }

    function jumpToMarkdownLine(line) {
      if (!editor || !Number.isFinite(line)) {
        return;
      }
      const markdown = editor.getMarkdown ? editor.getMarkdown() : "";
      const lines = markdown.split("\n");
      const targetLine = Math.max(1, Math.min(Math.trunc(line), lines.length));
      changeEditorMode("markdown", { restoreCursor: false });
      requestAnimationFrame(() => {
        setTimeout(() => {
          try {
            const selected = selectMarkdownSourceLine(targetLine);
            focusMarkdownEditor();
            if (!selected) {
              highlightMarkdownLine(targetLine);
            }
          } catch {
            // If Toast UI rejects the range, switching to Markdown mode is still useful.
          }
        }, 80);
      });
    }

    function showLintPanel(errors) {
      lintPanelEl.textContent = "";
      const title = document.createElement("strong");
      title.textContent = "Markdown lint blocked Save";
      const list = document.createElement("ul");
      for (const error of errors.slice(0, 12)) {
        const item = document.createElement("li");
        if (error.line) {
          const button = document.createElement("button");
          button.type = "button";
          button.className = "lint-jump";
          button.textContent = `Line ${error.line}: ${error.message}`;
          button.addEventListener("click", () => jumpToMarkdownLine(error.line));
          item.append(button);
        } else {
          item.textContent = error.message;
        }
        list.append(item);
      }
      if (errors.length > 12) {
        const item = document.createElement("li");
        item.textContent = `${errors.length - 12} more issue(s)`;
        list.append(item);
      }
      lintPanelEl.append(title, list);
      lintPanelEl.classList.add("visible");
    }

    function normalizeMarkdown(markdown) {
      const lines = markdown.replace(/\r\n?/g, "\n").split("\n");
      return `${lines.map((line) => line.replace(/[ \t]+$/g, "")).join("\n").replace(/\n*$/g, "")}\n`;
    }

    function lintMessageToError(message) {
      const rule = message.ruleId ? ` (${message.ruleId})` : "";
      return {
        line: message.line || null,
        column: message.column || null,
        message: `${message.reason}${rule}`
      };
    }

    async function lintAndFormatMarkdown(markdown) {
      try {
        const firstPass = await markdownProcessor.process(markdown);
        const formatted = normalizeMarkdown(String(firstPass));
        const secondPass = await markdownProcessor.process(formatted);
        return {
          markdown: normalizeMarkdown(String(secondPass)),
          errors: secondPass.messages.map(lintMessageToError)
        };
      } catch (error) {
        return {
          markdown,
          errors: [{
            line: error.line || null,
            column: error.column || null,
            message: error.reason || error.message || "Markdown processor failed."
          }]
        };
      }
    }

    function handleSaveShortcut(event) {
      const isSave = event.key && event.key.toLowerCase() === "s" && (event.metaKey || event.ctrlKey);
      if (!isSave) {
        return false;
      }
      event.preventDefault();
      event.stopPropagation();
      if (event.stopImmediatePropagation) {
        event.stopImmediatePropagation();
      }
      if (!saveEl.disabled) {
        saveCurrentFile();
      }
      return true;
    }

    async function loadFiles() {
      const data = await requestJson("/api/files");
      validPaths = new Set(data.files.map((file) => file.path));
      filesEl.textContent = "";
      for (const file of data.files) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "file-button";
        button.dataset.path = file.path;
        button.textContent = file.path;
        button.addEventListener("click", () => loadFile(file.path, { updateHash: true }));
        filesEl.append(button);
      }
      setStatus(`${data.files.length} files`);

      const hashPath = getHashPath();
      if (hashPath) {
        await loadFile(hashPath, { updateHash: false });
      }
    }

    async function loadFile(path, options = {}) {
      const { updateHash = true } = options;
      if (!validPaths.has(path)) {
        setStatus("Unknown Markdown file", true);
        return false;
      }

      if (dirty && !confirm("Discard unsaved changes?")) {
        if (currentPath) {
          setHashPath(currentPath);
        }
        return false;
      }

      saveCursorState();
      loadingPath = path;
      setStatus("Loading...");
      const data = await requestJson(`/api/file?path=${encodeURIComponent(path)}`);
      currentPath = data.path;
      pathEl.textContent = currentPath;
      setActive(currentPath);
      if (updateHash) {
        setHashPath(currentPath);
      }

      if (!editor) {
        editorEl.classList.remove("empty");
        editorEl.textContent = "";
        withoutDirtyTracking(() => {
          editor = new Editor({
            el: editorEl,
            height: "100%",
            initialEditType: "wysiwyg",
            previewStyle: "vertical",
            usageStatistics: false,
            initialValue: data.content
          });
        });
        editor.on("change", markDirty);
        editor.on("caretChange", () => saveCursorState());
        editor.on("keydown", handleSaveShortcut);
        editor.on("keyup", () => saveCursorState());
        editor.on("blur", () => saveCursorState());
        editorEl.addEventListener("mouseup", () => saveCursorState());
        editorEl.addEventListener("touchend", () => saveCursorState());
      } else {
        withoutDirtyTracking(() => editor.setMarkdown(data.content, false));
      }

      dirty = false;
      saveEl.disabled = true;
      setModeButtonsEnabled(true);
      syncModeToggle();
      clearLintPanel();
      restoreInitialCursorState(currentPath);
      setTimeout(() => {
        loadingPath = null;
        dirty = false;
        saveEl.disabled = true;
        setStatus("Loaded");
      }, 50);
      return true;
    }

    async function saveCurrentFile() {
      if (!currentPath || !editor) {
        return;
      }

      const sourceMarkdown = normalizeMarkdown(editor.getMarkdown());
      const lintResult = await lintAndFormatMarkdown(sourceMarkdown);
      const markdown = lintResult.markdown;
      const lintErrors = lintResult.errors;
      if (lintErrors.length > 0) {
        withoutDirtyTracking(() => editor.setMarkdown(markdown, false));
        showLintPanel(lintErrors);
        setModeButtonsEnabled(true);
        saveEl.disabled = false;
        setStatus("Fix Markdown lint", true);
        changeEditorMode("markdown");
        return;
      }

      saveEl.disabled = true;
      setStatus("Saving...");
      try {
        const cursorState = getCursorState();
        await requestJson(`/api/file?path=${encodeURIComponent(currentPath)}`, {
          method: "POST",
          headers: { "Content-Type": "text/markdown; charset=utf-8" },
          body: markdown
        });
        withoutDirtyTracking(() => editor.setMarkdown(markdown, false));
        if (cursorState && (cursorState.selection || cursorState.point)) {
          try {
            localStorage.setItem(cursorStorageKey(currentPath), JSON.stringify(cursorState));
          } catch {
            // Ignore private browsing or storage quota failures.
          }
          restoreCursorState(currentPath);
        }
        dirty = false;
        clearLintPanel();
        setTimeout(() => {
          dirty = false;
          setStatus("Saved");
        }, 50);
      } catch (error) {
        saveEl.disabled = false;
        setStatus(error.message, true);
      }
    }

    modeWysiwygEl.addEventListener("mousedown", (event) => event.preventDefault());
    modeMarkdownEl.addEventListener("mousedown", (event) => event.preventDefault());
    modeWysiwygEl.addEventListener("click", () => changeEditorMode("wysiwyg"));
    modeMarkdownEl.addEventListener("click", () => changeEditorMode("markdown"));

    saveEl.addEventListener("click", saveCurrentFile);
    window.addEventListener("keydown", handleSaveShortcut, true);
    document.addEventListener("selectionchange", () => {
      if (editorEl.contains(document.activeElement)) {
        saveCursorState();
      }
    });

    window.addEventListener("hashchange", () => {
      if (suppressHashChange) {
        return;
      }
      const hashPath = getHashPath();
      if (!hashPath || hashPath === currentPath) {
        return;
      }
      loadFile(hashPath, { updateHash: false });
    });

    window.addEventListener("beforeunload", (event) => {
      saveCursorState();
      if (!dirty) {
        return;
      }
      event.preventDefault();
      event.returnValue = "";
    });

    loadFiles().catch((error) => setStatus(error.message, true));
