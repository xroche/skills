# Tooling setup

Goal: a working `java` and `tla2tools.jar`, with no admin rights on the first attempt, cached so
repeat runs are instant.

## Cache location

Put everything under a per-user cache so every investigation reuses it:

```
CACHE=~/.cache/what-could-go-wrong
mkdir -p "$CACHE"
```

If a portable JRE extracted there later fails with "Permission denied", the cache sits on a `noexec`
mount. Move `CACHE` to `/var/tmp/what-could-go-wrong` and redo the step. The jar itself is only read,
never executed, so it works from anywhere.

## Step 1 — Java

Check for any usable Java first. A system Java 11+ is the common case and needs nothing else:

```bash
command -v java >/dev/null && java -version
```

If none, or the version is below 11, fetch a portable Temurin JRE into the cache. No install, no
admin rights. Detect OS and architecture so the same snippet works on macOS (usually arm64) and
Linux (usually x86-64):

```bash
cd "$CACHE"
case "$(uname -s)" in Darwin) OS=mac;; Linux) OS=linux;; *) echo "unsupported OS"; exit 1;; esac
case "$(uname -m)" in
  x86_64|amd64)  ARCH=x64;;
  arm64|aarch64) ARCH=aarch64;;
  *) echo "unsupported arch $(uname -m)"; exit 1;;
esac
curl -sSL -o jre.tar.gz "https://api.adoptium.net/v3/binary/latest/21/ga/${OS}/${ARCH}/jre/hotspot/normal/eclipse"
tar xzf jre.tar.gz
# Linux layout is jdk-*-jre/bin/java; macOS layout is jdk-*-jre/Contents/Home/bin/java. Find it either way.
JAVA="$(find "$CACHE" -type f -path '*/bin/java' | head -1)"
"$JAVA" -version
```

macOS note: the first run of a downloaded JRE may be blocked by Gatekeeper. If so, clear the
quarantine attribute on the extracted dir: `xattr -dr com.apple.quarantine "$CACHE"/jdk-*-jre`.

Only if the portable download is blocked (locked-down network, no outbound to adoptium) fall back to
a system install, which needs admin rights. Ask the user to run it themselves rather than assuming
sudo:

```bash
sudo apt-get install -y openjdk-21-jre-headless   # Debian/Ubuntu
brew install openjdk@21                            # macOS with Homebrew (no sudo)
```

## Step 2 — tla2tools.jar

One self-contained jar holds both the PlusCal translator (`pcal.trans`) and the checker
(`tlc2.TLC`). Cache it:

```bash
cd "$CACHE"
curl -sSL -o tla2tools.jar https://github.com/tlaplus/tlaplus/releases/latest/download/tla2tools.jar
```

## Step 3 — smoke test, both directions

Prove the toolchain end to end before modeling anything real, and prove it in *both* directions: a
model that must go red, and the same model with a lock that must go green. A setup only ever seen to
fail one way is not verified. This is also the whole method in twelve lines.

```bash
mkdir -p "$CACHE/smoke" && cd "$CACHE/smoke"
cat > Smoke.tla <<'EOF'
---- MODULE Smoke ----
EXTENDS Naturals

(*--algorithm smoke {
  variables counter = 0, commits = 0;
  process (w \in {"a", "b"})
    variables tmp = 0;
  {
    read:  tmp := counter;
    write: counter := tmp + 1 || commits := commits + 1;
  }
}
*)

Safe == counter = commits
====
EOF
printf 'SPECIFICATION Spec\nINVARIANT Safe\n' > Smoke.cfg
"$JAVA" -cp "$CACHE/tla2tools.jar" pcal.trans Smoke.tla
"$JAVA" -cp "$CACHE/tla2tools.jar" tlc2.TLC -deadlock -config Smoke.cfg Smoke.tla
```

Expect `Error: Invariant Safe is violated` with a five-state trace: both workers read `counter = 0`,
both then write 1, so one increment is lost while `commits` reaches 2. That is the lost-update
pattern from `02-patterns.md`, and it confirms Java, the jar, and the translate-then-check loop all
work.

Now the green half. Bracket the read and the write with a lock, rerun both commands, and expect
`Model checking completed. No error has been found`:

```
  variables counter = 0, commits = 0, locked = FALSE;
  ...
    acq:   await ~locked; locked := TRUE;
    read:  tmp := counter;
    write: counter := tmp + 1 || commits := commits + 1;
    rel:   locked := FALSE;
```

`pcal.trans` will not overwrite an existing `SPECIFICATION` line in the `.cfg`; that warning is
expected and harmless.

## Running a model in general

```bash
"$JAVA" -cp "$CACHE/tla2tools.jar" pcal.trans MyModel.tla     # PlusCal -> TLA+, after every edit
"$JAVA" -cp "$CACHE/tla2tools.jar" tlc2.TLC -deadlock -config MyModel.cfg MyModel.tla
```

Notes:
- Rerun `pcal.trans` after every edit to the `(*--algorithm ... *)` block. It rewrites the region
  between `BEGIN TRANSLATION` and `END TRANSLATION`; never hand-edit that region.
- `-deadlock` disables deadlock checking. Keep it on for these models: a guarded process that
  legitimately waits is not a deadlock we care about, and the default check would report it. Pattern
  E in `02-patterns.md` is the one exception.
- If TLC warns about the garbage collector, add `-XX:+UseParallelGC` before `-cp`. Cosmetic.
- For a bigger model, give the JVM more heap: `"$JAVA" -Xmx4g -cp ...`.

## Optional: Quint, for readable syntax

Some people find TLA+ notation off-putting. Quint has the same semantics with a typed, programmer
friendly syntax, a REPL (`quint run`), and a sound checker via Apalache (`quint verify`). Install
with `npm i -g @informalsystems/quint` (needs Node). Offer it as a fallback, not the default; the
templates here are in PlusCal, and the deepest beginner materials are for TLA+.
