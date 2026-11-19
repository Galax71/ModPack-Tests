# Galax71 Extreme FPS — Minecraft Java 26.2 (Fabric)

An aggressive **no-shaders** performance modpack, built for high-FPS experiments on an Intel Core Ultra 9 285K, RTX 5060 Ti 16 GB, and DDR5-6000 CL36.

## Download

**[Latest GitHub Releases](https://github.com/Galax71/ModPack-Tests/releases/latest)**

- **`Galax71_ExtremeFPS_26.2.mrpack`**: Ready to import into **Prism Launcher** or **Modrinth App**. References exact mod versions and hashes from the original Modrinth CDNs. The launcher downloads the mod files; GitHub does not rehost them.
- **`CurseForge_Personal_Installer_26.2.zip`**: For Windows + **CurseForge**. This is a **builder**, not an import-ready pack. Extract all files, right-click `Build-CurseForge-Pack.ps1` and run with PowerShell (or execute from a PowerShell terminal). The helper downloads each original mod JAR, verifies its SHA-512 hash, and creates `Downloads/Galax71_ExtremeFPS_26.2_CurseForge.zip`. Import **that newly created ZIP** into the CurseForge app. This is intended for personal use, not CurseForge publication.
- **`BUILD_REPORT.json`**: Lists exactly which candidate mods have a compatible 26.2 Fabric version and which could not be resolved.

### PowerShell command for CurseForge

After extracting the installer ZIP, open PowerShell in its folder:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Build-CurseForge-Pack.ps1
```

The script only downloads official Modrinth CDN files and checks hashes. No GitHub release contains third-party mod JARs.

## Mod selection

The config `mods.json` lists the candidate optimization mods, including Sodium, Lithium, ImmediatelyFast, FerriteCore, Entity Culling, More Culling, C2ME, Krypton, Alternate Current, VMP, BadOptimizations, lighting and rendering optimizers, and configuration dependencies.

The builder:
1. Checks the original Modrinth version metadata for **Minecraft 26.2 + Fabric**.
2. Chooses compatible releases and follows required dependencies.
3. Excludes unavailable or incompatible candidates and records them.
4. Refuses to publish an incomplete pack missing key core FPS mods.
5. Generates the Modrinth/Prism modpack and local CurseForge builder.
6. Uses GitHub Actions to publish the release files.

**Including more mods does not guarantee higher FPS.** Some improve server tick rate, RAM use, chunk loading, or background power draw rather than foreground FPS. Benchmark the same world and settings before and after changes.

## Performance testing

- Minecraft: Java Edition **26.2** / Fabric.
- Use no shaders, 2–4 render chunks, minimum particles, unlimited FPS, VSync off, and small simulation distance.
- Compare OpenGL and Vulkan independently where supported; Vulkan is not necessarily faster and may have mod incompatibilities.
- Start with **8–12 GB allocated**; compare against 20 GB rather than assuming more memory means faster.
- Target **10,000+ FPS only as a synthetic experiment**, not an achievable guarantee for real-world gameplay.
- The build workflow tests versions, hashes and ZIP structure, **not game launch or in-game stability**.

## Rebuild

Go to **Actions → Build and publish Extreme FPS 26.2 → Run workflow**. The GitHub release is refreshed with the latest compatible 26.2 files when the workflow succeeds.

The repository source and metadata are public; third-party JARs are downloaded directly from their authors' distribution URLs.
