#!/bin/bash
#
# axs04 command line tests: run from anywhere, they always use the axs script of this checkout.
# The assert functions follow the calling conventions of assert.sh (used by axs 0.2), so switching to it later is easy.

AXS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PATH="$AXS_DIR:$PATH"
TESTS_RUN=0
TESTS_FAILED=0

assert() {          # assert '<command>' '<expected output>'
    TESTS_RUN=$((TESTS_RUN+1))
    local actual
    actual="$(eval "$1" 2>&1)"
    if [ "$actual" != "$2" ]; then
        TESTS_FAILED=$((TESTS_FAILED+1))
        printf 'FAIL: %s\n  expected: %s\n  actual:   %s\n' "$1" "$2" "$actual"
    fi
}

assert_raises() {   # assert_raises '<command>' <expected exit code>
    TESTS_RUN=$((TESTS_RUN+1))
    eval "$1" >/dev/null 2>&1
    local actual=$?
    if [ "$actual" != "$2" ]; then
        TESTS_FAILED=$((TESTS_FAILED+1))
        printf 'FAIL: %s\n  expected exit code: %s\n  actual exit code:   %s\n' "$1" "$2" "$actual"
    fi
}

assert_end() {      # assert_end <name of the group of tests>
    echo "$1: done"
}

TEMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TEMP_DIR"' EXIT


assert 'axs version , count .' 2
assert 'axs noop 42' 42
assert 'axs noop 4.5' 4.5
assert 'axs noop hello' hello
assert 'axs noop "\"42\"" , zfill 4' 0042                 # stays a string: an int has no zfill()
assert_end kernel_and_scalars

assert 'axs noop --,=alpha,beta,3' "['alpha', 'beta', 3]"
assert 'axs noop --:=alpha:beta' "['alpha', 'beta']"
assert 'axs noop --\;=alpha\;beta' "['alpha', 'beta']"
assert 'axs noop --/=alpha/beta' "['alpha', 'beta']"
assert "axs noop '-- =alpha beta'" "['alpha', 'beta']"
assert 'axs noop --,' '[]'
assert 'axs noop --,:=x:10,y:20' "[['x', 10], ['y', 20]]"
assert 'axs noop --,::=x:10,y:20' "{'x': 10, 'y': 20}"
assert "axs noop ---='{\"a\": [1, null, true]}'" "{'a': [1, None, True]}"
assert_end positional_data_types

assert 'axs noop --arg=123' 123
assert 'axs noop --arg=' ''
assert 'axs noop --arg' True
assert 'axs noop --arg+' True
assert 'axs noop --arg-' False
assert 'axs noop ---arg=null' None
assert 'axs noop --arg,' '[]'
assert 'axs noop --arg,=a,b' "['a', 'b']"
assert 'axs noop --arg,:=x:10,y:20' "[['x', 10], ['y', 20]]"
assert 'axs noop --arg,::=x:10,y:20' "{'x': 10, 'y': 20}"
assert_end named_data_types

assert 'axs noop --arg.x.y=1' "{'x': {'y': 1}}"
assert 'axs noop ---arg.x=null' "{'x': None}"
assert 'axs noop --arg.x' "{'x': True}"
assert 'axs noop --arg.x-' "{'x': False}"
assert 'axs dig greek --greek,=alpha --greek+,=beta,gamma' "['alpha', 'beta', 'gamma']"
assert 'axs dig greek.1 --greek,=alpha,beta --greek.1=BETA' 'BETA'
assert 'axs byname foo , get greeting --greeting+=_and_more , , byname foo , get greeting' 'hello from foo'   # the Entry itself is untouched
assert_end editing_named_arguments

assert 'axs byname baz , get foo_only' 'inherited from foo'
assert 'axs byname baz , get greeting' 'hello from baz'
assert 'axs byname baz' 'axs byname baz'                     # an Entry is printed as the command line that loads it
assert 'axs byname no_such_entry' None
assert 'axs byname baz , get greeting , , byname foo , get greeting' 'hello from foo'
assert 'axs noop alpha-beta , split - ,- upper' 'ALPHA-BETA'
assert 'axs byname foo , get greeting ,-' 'axs byname foo'
assert 'axs noop 3 ,0 noop , __add__ 1' 4
assert 'axs noop 3 ,arg noop , __add__ 1' 4
assert_end pipelines_and_markers

axs fresh_entry "$TEMP_DIR/hello" , plant message Hello , save >/dev/null
assert "axs bypath $TEMP_DIR/hello , get message" Hello
assert "axs fresh_entry ---own_data='{\"x\": 1}'" "axs fresh_entry '---own_data={\"x\": 1}'"
assert "$(axs fresh_entry ---own_data='{"x": 1}') , get x" 1          # the printed command line works as it is
assert_end entry_creation

assert 'axs help help | grep -c "^Signature .*: help(action_name: str = None) -> str$"' 1
assert 'axs help byname | grep "^Ancestry path"' "Ancestry path                 : $(basename "$AXS_DIR") --> core_collection"
assert 'axs byname baz , help gte' "[baz] has no action 'gte'. Did you mean: get?"
assert 'axs help | head -1 | cut -d: -f1 | xargs' Entry          # piping into head must not raise a broken pipe error
assert_end help

assert_raises 'axs no_such_action' 1
assert_raises "axs 'not an action'" 1
assert_raises 'axs noop ---arg=not_json' 1
assert_raises 'axs noop --arg@=1' 1
assert_end malformed_input


# Every "Usage examples:" line in the docstrings is run from a temporary directory (so that examples saving something cannot touch
# the repository); where it states an expected result after " # => ", the output must match it, otherwise it must just succeed.
while IFS= read -r example; do
    if [[ "$example" == *" # => "* ]]; then
        command="${example%% # => *}"
        command="${command%"${command##*[![:space:]]}"}"    # without the padding before " # => "
        assert "( cd \"$TEMP_DIR\" && $command )" "${example#* # => }"
    else
        assert_raises "( cd \"$TEMP_DIR\" && $example )" 0
    fi
done < <(find "$AXS_DIR" -name '*.py' -not -path '*/__pycache__/*' -print0 | sort -z | xargs -0 grep -h -E '^[[:space:]]+axs ' | sed -E 's/^[[:space:]]+//')
assert_end docstring_examples


echo "$((TESTS_RUN-TESTS_FAILED))/$TESTS_RUN command line tests passed"
[ "$TESTS_FAILED" -eq 0 ]
