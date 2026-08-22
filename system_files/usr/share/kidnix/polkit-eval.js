// Evaluate a polkit rules file outside polkitd and print the verdict.
//
// Run by /usr/libexec/kidnix-polkit-check. Exists because polkit gives you no
// dry-run: the only way to find out that a rules file has a typo is to restart
// polkitd and notice that authorisations you expected to be denied are being
// granted. On a child's computer that is not an acceptable feedback loop.
//
// This is a *behavioural* harness, not a syntax check: it stubs the `polkit`
// global, loads the real rules file, and asks it what it would decide for a
// given (user, action) pair -- which is what we actually care about.
//
// CAVEAT, and it matters: polkitd on Fedora 44 embeds duktape (ECMAScript
// 5.1) while this harness runs under gjs/SpiderMonkey, which accepts far more
// modern syntax. gjs accepting the file does NOT prove duktape will. The
// ES5-compatibility grep in build_files/40-lockdown.sh and
// tests/image/test_lockdown.sh covers that half.
//
// Usage: gjs /usr/share/kidnix/polkit-eval.js <rules-file> <user> <action-id>
// Prints one of: YES NO AUTH_SELF AUTH_SELF_KEEP AUTH_ADMIN AUTH_ADMIN_KEEP
//                NOT_HANDLED

const { GLib } = imports.gi;

if (ARGV.length < 3) {
    printerr('usage: polkit-eval.js <rules-file> <user> <action-id>');
    imports.system.exit(64);
}

const rulesFile = ARGV[0];
const user = ARGV[1];
const actionId = ARGV[2];

const collected = [];

// The subset of the polkit JS API that rules are allowed to use, per
// polkit(8). Anything a rules file touches that is not here will throw, which
// is exactly what we want -- it means the rule would also fail inside polkitd.
globalThis.polkit = {
    Result: {
        YES: 'YES',
        NO: 'NO',
        AUTH_SELF: 'AUTH_SELF',
        AUTH_SELF_KEEP: 'AUTH_SELF_KEEP',
        AUTH_ADMIN: 'AUTH_ADMIN',
        AUTH_ADMIN_KEEP: 'AUTH_ADMIN_KEEP',
        NOT_HANDLED: 'NOT_HANDLED',
    },
    addRule(fn) {
        collected.push(fn);
    },
    addAdminRule() {
        // Admin-selection rules do not affect the verdict we are probing.
    },
    log() {
        // Swallowed: polkit.log goes to the journal in real life.
    },
    spawn() {
        throw new Error('polkit.spawn() is not available in the harness');
    },
    _debug() {},
};

const [ok, bytes] = GLib.file_get_contents(rulesFile);
if (!ok) {
    printerr(`cannot read ${rulesFile}`);
    imports.system.exit(66);
}

// Indirect eval, so the rules file sees the same global scope polkitd gives it.
const source = new TextDecoder().decode(bytes);
(0, eval)(source);

if (collected.length === 0) {
    printerr(`${rulesFile} registered no rules`);
    imports.system.exit(65);
}

// polkit's `wheel` membership is what 50-default.rules keys off; kidnix's
// sysusers config puts only `parent` in it.
const subject = {
    user,
    isInGroup: group => user === 'parent' && group === 'wheel',
    local: true,
    active: true,
    seat: 'seat0',
    session: '1',
    pid: 1234,
    toString: () => `[Subject user=${user}]`,
};

const action = {
    id: actionId,
    lookup: () => '',
    toString: () => `[Action id=${actionId}]`,
};

// polkitd walks the registered rules in order and stops at the first one that
// returns anything other than NOT_HANDLED (or undefined).
let verdict = 'NOT_HANDLED';
for (const rule of collected) {
    const value = rule(action, subject);
    if (value !== undefined && value !== null && value !== 'NOT_HANDLED') {
        verdict = value;
        break;
    }
}

print(verdict);
