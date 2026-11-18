"use strict";

// 项目路径解析（JS 侧）：与 paths.py 同一套规则，避免两套口径。
// 1. 环境变量 QIANCHUAN_EXTERNAL_ROOT 优先；
// 2. 否则按本文件位置推算（本文件在 <外部根>\我的坚果云\AI投放工具\）；
// 3. 推算结果若找不到标志目录，再试上一级；
// 4. 结果写回环境变量，让本进程拉起的浏览器子进程看到同一份根。

const fs = require("node:fs");
const path = require("node:path");

const ROOT = __dirname;

const MARKERS = ["runtime", "models", "node_modules", "chrome-profile", "buyin-chrome-profile"];

function cleanEnv(name) {
  return String(process.env[name] || "")
    .trim()
    .replace(/^["']|["']$/g, "");
}

function looksLikeExternalRoot(candidate) {
  try {
    return MARKERS.some((marker) => fs.existsSync(path.join(candidate, marker)));
  } catch (error) {
    return false;
  }
}

function resolveExternalRoot() {
  const envValue = cleanEnv("QIANCHUAN_EXTERNAL_ROOT");
  if (envValue) {
    return { root: path.resolve(envValue), source: "环境变量" };
  }
  const primary = path.resolve(ROOT, "..", "..");
  if (looksLikeExternalRoot(primary)) {
    return { root: primary, source: "按程序位置推算" };
  }
  const secondary = path.resolve(ROOT, "..");
  if (looksLikeExternalRoot(secondary)) {
    return { root: secondary, source: "按程序位置的上一级推算" };
  }
  return {
    root: primary,
    source: "按程序位置推算（未找到 runtime/models/node_modules 等标志目录）"
  };
}

const resolved = resolveExternalRoot();
const EXTERNAL_ROOT = resolved.root;
process.env.QIANCHUAN_EXTERNAL_ROOT = EXTERNAL_ROOT;

const DATA_DIR = path.join(ROOT, "data");
const MODELS_DIR = path.join(EXTERNAL_ROOT, "models");
const RUNTIME_DIR = path.join(EXTERNAL_ROOT, "runtime");
const NODE_MODULES_DIR = path.join(EXTERNAL_ROOT, "node_modules");
const CHROME_PROFILE_DIR = path.join(EXTERNAL_ROOT, "chrome-profile");
const BUYIN_CHROME_PROFILE_DIR = path.join(EXTERNAL_ROOT, "buyin-chrome-profile");
const TOOLS_DIR = path.join(EXTERNAL_ROOT, "tools");

module.exports = {
  ROOT,
  EXTERNAL_ROOT,
  EXTERNAL_ROOT_SOURCE: resolved.source,
  DATA_DIR,
  MODELS_DIR,
  RUNTIME_DIR,
  NODE_MODULES_DIR,
  CHROME_PROFILE_DIR,
  BUYIN_CHROME_PROFILE_DIR,
  TOOLS_DIR
};
