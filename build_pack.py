#!/usr/bin/env python3
"""Resolve 26.2 Fabric mod releases from Modrinth and build a real .mrpack.
No third-party JARs are redistributed. A separate local-only CurseForge
import ZIP can be produced on Windows by Build-CurseForge-Pack.ps1.
"""
import hashlib
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parent
DIST = ROOT / "dist"
API = "https://api.modrinth.com/v2"
FABRIC_API = "https://meta.fabricmc.net/v2/versions/loader"
HEADERS = {"User-Agent": "Galax71-ModPack-Tests/0.1 (Minecraft pack resolver)", "Accept": "application/json"}
config = json.loads((ROOT / "mods.json").read_text(encoding="utf-8"))
GAME = config["minecraft"]
selected = {}   # keyed by canonical Modrinth project ID
failed = []
warnings = []
seen_lookup = {}

def api_get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=35) as response:
        return json.load(response)

def get_project(identifier):
    if identifier in seen_lookup:
        return seen_lookup[identifier]
    project = api_get(f"{API}/project/{urllib.parse.quote(identifier, safe='')}")
    seen_lookup[identifier] = project
    seen_lookup[project["id"]] = project
    return project

def get_version(identifier):
    query = urllib.parse.urlencode({
        "loaders": json.dumps(["fabric"]),
        "game_versions": json.dumps([GAME])
    })
    versions = api_get(f"{API}/project/{urllib.parse.quote(identifier, safe='')}/version?{query}")
    versions = [v for v in versions if v.get("version_type") != "alpha"] or versions
    versions.sort(key=lambda v: (v.get("version_type") == "release", v.get("date_published", "")), reverse=True)
    if not versions:
        raise ValueError("No Minecraft " + GAME + " Fabric version")
    for v in versions:
        files = v.get("files", [])
        good = [f for f in files if f.get("hashes", {}).get("sha512") and f.get("url") and f.get("filename", "").endswith(".jar")]
        if good:
            return v, next((f for f in good if f.get("primary")), good[0])
    raise ValueError("No downloadable JAR with SHA-512 for Minecraft " + GAME)

def resolve(identifier, mandatory=False, stack=()):
    try:
        p = get_project(identifier)
        pid = p["id"]
        if pid in selected:
            return pid
        if pid in stack:
            raise ValueError("Dependency cycle")
        version, jar = get_version(pid)
        if "fabric" not in version.get("loaders", []) or GAME not in version.get("game_versions", []):
            raise ValueError("Loader/version mismatch")
        for dep in version.get("dependencies", []):
            if dep.get("dependency_type") != "required":
                continue
            dep_id = dep.get("project_id")
            if dep_id:
                resolve(dep_id, mandatory=True, stack=stack + (pid,))
            elif dep.get("file_name"):
                raise ValueError("Unresolved file-only required dependency " + dep["file_name"])
        selected[pid] = {"name": p["title"], "slug": p["slug"], "project_id": pid,
                         "version_id": version["id"], "version": version["version_number"],
                         "filename": jar["filename"], "size": jar.get("size", 0), "url": jar["url"],
                         "sha1": jar["hashes"].get("sha1", ""), "sha512": jar["hashes"]["sha512"],
                         "license": p.get("license", {}).get("id", "unknown"),
                         "dependencies": version.get("dependencies", [])}
        return pid
    except (ValueError, KeyError, urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
        msg = f"{identifier}: {e}"
        if mandatory:
            raise ValueError(msg) from e
        failed.append(msg)
        return None

def fabric_loader():
    loaders = api_get(f"{FABRIC_API}/{GAME}")
    stable = [x for x in loaders if x.get("loader", {}).get("stable")]
    if not stable:
        raise RuntimeError("No official stable Fabric loader found for " + GAME)
    return stable[0]["loader"]["version"]

def build():
    DIST.mkdir(parents=True, exist_ok=True)
    for mod in config["mods"]:
        if mod.get("tier") == "experimental":
            warnings.append("Experimental renderer excluded from main pack: " + mod["slug"])
            continue
        resolve(mod["slug"], mandatory=False)
    # Exclude candidates declaring a conflict with anything already included.
    # A conflict is recorded rather than silently resolving to broken combinations.
    while True:
        clashes = []
        for pid, m in selected.items():
            for dep in m["dependencies"]:
                if dep.get("dependency_type") == "incompatible" and dep.get("project_id") in selected:
                    clashes.append((pid, dep["project_id"]))
        if not clashes:
            break
        a, b = clashes[0]
        # Preserve the earlier listed candidate where possible.
        remove = b if list(selected).index(a) < list(selected).index(b) else a
        warnings.append("Excluded incompatible mod: " + selected[remove]["name"])
        del selected[remove]
    essential = ["sodium", "lithium", "immediatelyfast", "ferrite-core", "entityculling"]
    present = {x["slug"] for x in selected.values()}
    missing_essential = [x for x in essential if x not in present]
    if missing_essential:
        raise RuntimeError("Required FPS mods missing: " + ", ".join(missing_essential) + ". Refusing partial release.")
    loader = fabric_loader()
    entries = []
    lock = []
    for m in sorted(selected.values(), key=lambda x: x["name"].casefold()):
        if not re.match(r"^[^/\\]+\.jar$", m["filename"]):
            raise RuntimeError("Unsafe JAR filename: " + m["filename"])
        hashes = {"sha512": m["sha512"]}
        if m["sha1"]:
            hashes["sha1"] = m["sha1"]
        entries.append({"path": "mods/" + m["filename"], "hashes": hashes,
                        "downloads": [m["url"]], "fileSize": m["size"],
                        "env": {"client": "required", "server": "optional"}})
        lock.append({k: v for k, v in m.items() if k != "dependencies"})
    manifest = {
        "formatVersion": 1, "game": "minecraft", "versionId": config["pack_version"],
        "name": "Galax71 Extreme FPS 26.2", "summary": "Maximum-FPS Fabric pack, no shaders; test Vulkan vs OpenGL.",
        "files": entries, "dependencies": {"minecraft": GAME, "fabric-loader": loader}
    }
    report = {
        "game": GAME, "loader": loader, "included_count": len(lock),
        "included": [{"mod": m["name"], "version": m["version"], "license": m["license"]} for m in lock],
        "unavailable_or_unresolved": failed, "warnings": warnings,
        "note": "Compatibility verified against 26.2 Fabric metadata, not runtime-tested on a gaming PC."
    }
    (DIST / "resolved-mods.json").write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
    (DIST / "BUILD_REPORT.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    with zipfile.ZipFile(DIST / "Galax71_ExtremeFPS_26.2.mrpack", "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("modrinth.index.json", json.dumps(manifest, indent=2))
        z.writestr("overrides/README.txt", "26.2 Fabric Extreme FPS. No shaders. Change renderer separately.\n")
    # Small helper ZIP deliberately contains zero mod JARs. Windows helper
    # downloads originals locally, then packages a personal-use CF import.
    with zipfile.ZipFile(DIST / "CurseForge_Personal_Installer_26.2.zip", "w", zipfile.ZIP_DEFLATED) as z:
        z.write(ROOT / "Build-CurseForge-Pack.ps1", "Build-CurseForge-Pack.ps1")
        z.write(DIST / "resolved-mods.json", "resolved-mods.json")
        z.writestr("manifest.json", json.dumps({
            "minecraft": {"version": GAME, "modLoaders": [{"id": "fabric-" + loader, "primary": True}]},
            "manifestType": "minecraftModpack", "manifestVersion": 1,
            "name": "Galax71 Extreme FPS 26.2", "version": config["pack_version"],
            "author": "Galax71", "files": [], "overrides": "overrides"
        }, indent=2))
        z.writestr("README.txt", "Run Build-CurseForge-Pack.ps1 locally to fetch and verify all mod JARs.\n"
                   "This helper ZIP itself is NOT an import-ready modpack. It creates a full import ZIP for personal use.\n"
                   "For direct launcher imports, prefer Galax71_ExtremeFPS_26.2.mrpack in Prism or Modrinth App.\n")
    print("Resolved", len(lock), "compatible mods; missing:", len(failed))
    print("Artifacts:", *(str(x) for x in DIST.iterdir()), sep="\n")
if __name__ == "__main__":
    build()
