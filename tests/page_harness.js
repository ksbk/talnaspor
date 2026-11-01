// Runs the chat page's own script against a minimal DOM and reports what a user would see,
// as JSON, for tests/test_page_examples.py. Usage: node page_harness.js index.html
"use strict";
const fs = require("fs");
const vm = require("vm");

class Element {
  constructor(tag) {
    this.tagName = tag.toUpperCase();
    this.children = [];
    this.attributes = {};
    this.listeners = {};
    this.dataset = {};
    this.hidden = false;
    this.className = "";
    this.text = "";
  }
  get textContent() {
    return this.text + this.children.map((child) => child.textContent).join("");
  }
  set textContent(value) {
    this.text = String(value);
    this.children = [];
  }
  append(...nodes) {
    for (const node of nodes) {
      this.children.push(typeof node === "string" ? Object.assign(new Element("#text"), { text: node }) : node);
    }
  }
  prepend(node) {
    this.children.unshift(node);
  }
  setAttribute(name, value) {
    this.attributes[name] = String(value);
  }
  getAttribute(name) {
    return name in this.attributes ? this.attributes[name] : null;
  }
  removeAttribute(name) {
    delete this.attributes[name];
  }
  addEventListener(type, listener) {
    (this.listeners[type] = this.listeners[type] || []).push(listener);
  }
  dispatch(type) {
    for (const listener of this.listeners[type] || []) listener({ preventDefault() {} });
  }
  click() {
    this.dispatch("click");
  }
  scrollIntoView() {}
}

function byId(id, tag, attributes = {}) {
  const node = new Element(tag);
  Object.assign(node.attributes, attributes);
  return [id, node];
}

const page = fs.readFileSync(process.argv[2], "utf8");
const script = page.match(/<script>([\s\S]*?)<\/script>/)[1];
const markup = page.match(/<div class="explore">([\s\S]*?)<\/div>\s*<\/div>/)[1];

const nodes = Object.fromEntries([
  byId("subtitle", "p"),
  byId("question-label", "label"),
  byId("question", "input"),
  byId("send", "button"),
  byId("ask", "form"),
  byId("log", "section"),
  // The toggle and the examples start as the page's markup declares them.
  byId("examples-toggle", "button", {
    "aria-expanded": markup.match(/aria-expanded="(\w+)"/)[1],
    "aria-controls": markup.match(/aria-controls="(\w+)"/)[1],
  }),
  byId("examples", "div"),
]);
nodes.examples.hidden = /id="examples"[^>]*\bhidden\b/.test(markup);
const languages = ["is", "en"].map((lang) => Object.assign(new Element("button"), { dataset: { lang } }));

const requests = [];
const context = vm.createContext({
  document: {
    documentElement: { lang: "is" },
    getElementById: (id) => nodes[id],
    createElement: (tag) => new Element(tag),
    querySelectorAll: (selector) => (selector === ".languages button" ? languages : []),
  },
  localStorage: { getItem: () => null, setItem() {} },
  fetch: (url, options) => {
    requests.push({ url, body: JSON.parse(options.body) });
    return new Promise(() => {});
  },
});
vm.runInContext(script, context);

const toggle = nodes["examples-toggle"];
function state() {
  return {
    hidden: nodes.examples.hidden,
    expanded: toggle.getAttribute("aria-expanded"),
    controls: toggle.getAttribute("aria-controls"),
    label: toggle.textContent,
    examples: nodes.examples.children.map((button) => button.textContent),
    lang: context.document.documentElement.lang,
  };
}
const click = (lang) => languages.find((button) => button.dataset.lang === lang).click();

const steps = {};
steps.initial = state();
toggle.click();
steps.expanded = state();
toggle.click();
steps.collapsed = state();
click("en");
steps.englishCollapsed = state();
toggle.click();
click("is");
steps.icelandicStillExpanded = state();
toggle.click();
click("en");
steps.englishStillCollapsed = state();
toggle.click();
const chosen = nodes.examples.children[2];
chosen.click();
steps.selected = { question: chosen.textContent, requests, exchanges: nodes.log.children.length };

process.stdout.write(JSON.stringify(steps));
