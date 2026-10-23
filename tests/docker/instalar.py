# Roda dentro do container, como usuário comum: instala receitas de verdade e confere o resultado.
# Uso: python3 instalar.py <pasta do motor.py> <ids separados por vírgula>
import json
import subprocess
import sys

sys.path.insert(0, sys.argv[1])
import motor as M  # noqa: E402

ids = sys.argv[2].split(",")
respostas = {"git_nome": "Teste Adon", "git_email": "teste@adon.dev"}
res = M.executar(ids, respostas, lambda *a: print("  ", *a, flush=True), "/tmp/adon-dev-logs")
print("RESULTADO", json.dumps(res))

# confere como a pessoa vai usar: num terminal novo (bash interativo lê o .bashrc)
confere = {
    "git": 'git config --global user.name && git config --global user.email && test -f ~/.ssh/id_ed25519.pub',
    "node": "node --version && npm --version",
    "gh": "gh --version | head -1",
    "vscode": "code --version | head -1",
    "php": "php --version | head -1 && composer --version",
    "python": "python3 --version && uv --version",
    "docker": "docker --version && docker compose version",
}
ok = all(v == "ok" for v in res.values())
for i in ids:
    if i in confere:
        r = subprocess.run(["bash", "-ic", confere[i]], capture_output=True, text=True)
        print(f"TERMINAL {i}:", r.stdout.strip().replace("\n", " | ") or r.stderr.strip()[-200:])
        ok = ok and r.returncode == 0
if not ok:
    for i in ids:
        print(f"--- log {i}")
        print(open(f"/tmp/adon-dev-logs/{i}.log").read()[-1500:])
print("PASSOU" if ok else "FALHOU")
sys.exit(0 if ok else 1)
